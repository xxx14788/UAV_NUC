#!/usr/bin/env python3
"""左右图像流互相关滞后估计（T2-W0-2，比 stamp 更硬的同步证据）。

原理: stamp 相同不代表渲染内容来自同一仿真步。对连续 N 帧构造
  (l_t, r_t)   —— 标称同步对
  (l_t, r_{t+1}) —— 右目滞后一帧的对
先按整幅 phase-correlation 视差把右目对齐到左目（消基线水平位移），
再计算去均值 NCC。若 corr(l_t, r_{t+1}) > corr(l_t, r_t)，第 t 帧存在
一帧错拍。逐帧投票 + 汇总错拍率/位置，输出 JSON 与投票时序 PNG。

用法:
  python3 stereo_xcorr.py <bag文件> [--left-topic T] [--right-topic T]
                          [--max-frames 600] [--out JSON] [--plot PNG]
  python3 stereo_xcorr.py --live --duration 20 [...]

依赖: ROS Noetic python3 + cv2/numpy/matplotlib(Agg)
"""
import argparse
import json

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import cv2
except ImportError:
    raise SystemExit("需要 opencv-python (cv2)")

LEFT_TOPIC_DEF = "/iris_stereo_vins/vins_cam_left/image_raw"
RIGHT_TOPIC_DEF = "/iris_stereo_vins/vins_cam_right/image_raw"


def to_gray(msg):
    """sensor_msgs/Image → 灰度 uint8（降采样到宽 320 提速）。"""
    enc = msg.encoding.lower()
    if enc in ("rgb8", "bgr8"):
        arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width, 3)
        g = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY if enc == "bgr8"
                         else cv2.COLOR_RGB2GRAY)
    elif enc == "mono8":
        g = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width)
    elif enc == "32FC1":
        arr = np.frombuffer(msg.data, dtype=np.float32).reshape(
            msg.height, msg.width)
        g = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    else:
        raise ValueError(f"不支持的编码: {enc}")
    if g.shape[1] > 320:
        k = 320.0 / g.shape[1]
        g = cv2.resize(g, (320, int(g.shape[0] * k)))
    return g


def ncc(a, b):
    """去均值归一化互相关。"""
    a = a.astype(np.float64) - np.mean(a)
    b = b.astype(np.float64) - np.mean(b)
    d = np.sqrt(np.sum(a * a) * np.sum(b * b))
    if d < 1e-9:
        return np.nan
    return float(np.sum(a * b) / d)


def align_x(dst_shape, src, shift_x):
    """水平平移对齐（双线性 warpAffine）。"""
    M = np.float32([[1, 0, -shift_x], [0, 1, 0]])
    return cv2.warpAffine(src, M, (src.shape[1], src.shape[0]))


def estimate_disparity(l, r):
    """phase correlation 估计整幅水平相对位移（基线视差近似）。"""
    try:
        (dx, _), _ = cv2.phaseCorrelate(np.float32(l), np.float32(r))
        return float(dx)
    except cv2.error:
        return 0.0


def lag_votes(frames):
    """frames=[(t,l,r)] → 每帧 (t, ncc_same, ncc_next, vote, margin)。"""
    # 滚动中位视差（场景深度变化时缓慢跟踪）
    disps = [estimate_disparity(l, r) for _, l, r in frames[: min(30, len(frames))]]
    base = float(np.median(disps))
    out = []
    for i in range(len(frames) - 1):
        t, lt, rt = frames[i]
        _, _, rtn = frames[i + 1]
        rt_a = align_x(rt.shape, rt, base)
        rtn_a = align_x(rtn.shape, rtn, base)
        c0 = ncc(lt, rt_a)
        c1 = ncc(lt, rtn_a)
        if np.isnan(c0) or np.isnan(c1):
            continue
        out.append({"t": t, "ncc_same": c0, "ncc_next": c1,
                    "vote": int(c1 > c0), "margin": c1 - c0})
    return out, base


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bagfile", nargs="?")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--duration", type=float, default=20)
    ap.add_argument("--left-topic", default=LEFT_TOPIC_DEF)
    ap.add_argument("--right-topic", default=RIGHT_TOPIC_DEF)
    ap.add_argument("--max-frames", type=int, default=600)
    ap.add_argument("--out", default=None)
    ap.add_argument("--plot", default=None)
    args = ap.parse_args()

    frames = []
    if args.live:
        import rospy
        from sensor_msgs.msg import Image
        rospy.init_node("stereo_xcorr_live", anonymous=True,
                        disable_signals=True)
        buf = {"l": None, "r": None, "n": [0, 0]}

        def on_l(m):
            buf["l"] = (m.header.stamp.to_sec(), to_gray(m))
            buf["n"][0] += 1

        def on_r(m):
            buf["r"] = (m.header.stamp.to_sec(), to_gray(m))
            buf["n"][1] += 1

        rospy.Subscriber(args.left_topic, Image, on_l, queue_size=2)
        rospy.Subscriber(args.right_topic, Image, on_r, queue_size=2)
        rate = rospy.Rate(50)
        t_end = rospy.get_time() + args.duration
        while rospy.get_time() < t_end and not rospy.is_shutdown():
            if buf["l"] and buf["r"] and abs(buf["l"][0] - buf["r"][0]) < 0.005:
                frames.append((buf["l"][0], buf["l"][1], buf["r"][1]))
                buf["l"] = buf["r"] = None
                if len(frames) >= args.max_frames:
                    break
            rate.sleep()
        print(f"live 采样: {len(frames)} 对")
    else:
        if not args.bagfile:
            ap.error("需要 bag 文件或 --live")
        import rosbag
        from collections import deque
        pend_l, pend_r = deque(), deque()
        TOL, STALE = 0.005, 0.5

        def try_match(now):
            while pend_l and pend_r:
                dt = pend_l[0][0] - pend_r[0][0]
                if abs(dt) <= TOL:
                    t, lg = pend_l.popleft()
                    _, rg = pend_r.popleft()
                    frames.append((t, lg, rg))
                elif dt > 0:
                    if now - pend_r[0][0] > STALE:
                        pend_r.popleft()
                    else:
                        break
                else:
                    if now - pend_l[0][0] > STALE:
                        pend_l.popleft()
                    else:
                        break

        with rosbag.Bag(args.bagfile, "r") as bag:
            for topic, msg, _t in bag.read_messages(
                    topics=[args.left_topic, args.right_topic]):
                ts = msg.header.stamp.to_sec()
                if topic == args.left_topic:
                    pend_l.append((ts, to_gray(msg)))
                else:
                    pend_r.append((ts, to_gray(msg)))
                try_match(ts)
                if len(frames) >= args.max_frames:
                    break
        print(f"bag 读取: {len(frames)} 对")

    if len(frames) < 20:
        raise SystemExit("帧对不足 20，无法投票")

    votes, base = lag_votes(frames)
    v = np.array([x["vote"] for x in votes], dtype=float)
    m = np.array([x["margin"] for x in votes], dtype=float)
    t0 = votes[0]["t"]
    ts = np.array([x["t"] - t0 for x in votes])
    rate = float(np.mean(v))
    # 连续错拍段（≥3 连号）定位
    runs, i = [], 0
    while i < len(v):
        if v[i] == 1:
            j = i
            while j + 1 < len(v) and v[j + 1] == 1:
                j += 1
            if j - i + 1 >= 3:
                runs.append((float(ts[i]), float(ts[j])))
            i = j + 1
        else:
            i += 1
    summary = {
        "n_votes": len(votes),
        "lag_frame_rate": rate,
        "align_disp_px": base,
        "ncc_same_mean": float(np.mean([x["ncc_same"] for x in votes])),
        "ncc_next_mean": float(np.mean([x["ncc_next"] for x in votes])),
        "margin_mean": float(np.mean(m)),
        "margin_abs_mean": float(np.mean(np.abs(m))),
        "lag_runs_ge3": runs,
    }
    print("=" * 60)
    print(f"互相关滞后投票  n={len(votes)}  对齐视差={base:.1f}px")
    print(f"  NCC(l_t,r_t)   = {summary['ncc_same_mean']:.4f}")
    print(f"  NCC(l_t,r_t+1) = {summary['ncc_next_mean']:.4f}")
    print(f"  错拍帧率 = {rate:.3f}（≥3 连号段 {len(runs)} 处）")
    for s, e in runs[:10]:
        print(f"    错拍段 t=[{s:.2f}, {e:.2f}]s")
    print("=" * 60)

    out = args.out or ((args.bagfile + ".xcorr.json") if args.bagfile
                       else "stereo_xcorr.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "votes": votes}, f,
                  ensure_ascii=False, indent=2)
    print(f"JSON: {out}")

    plot = args.plot or out.replace(".json", ".png")
    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax[0].plot(ts, [x["ncc_same"] for x in votes], "b-", lw=0.8,
               label="NCC(l_t, r_t)")
    ax[0].plot(ts, [x["ncc_next"] for x in votes], "r-", lw=0.8,
               label="NCC(l_t, r_{t+1})")
    ax[0].legend(); ax[0].set_ylabel("NCC"); ax[0].grid(alpha=0.3)
    ax[1].step(ts, v, where="mid", color="k", lw=0.8)
    ax[1].set_ylim(-0.1, 1.1); ax[1].set_ylabel("lag vote")
    ax[1].set_xlabel("t (s)"); ax[1].grid(alpha=0.3)
    fig.suptitle(f"stereo xcorr lag  rate={rate:.3f}  align={base:.1f}px")
    fig.tight_layout()
    fig.savefig(plot, dpi=110)
    plt.close(fig)
    print(f"PNG: {plot}")


if __name__ == "__main__":
    main()
