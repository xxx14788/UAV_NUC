#!/usr/bin/env python3
"""四指标时刻对齐的双目提帧管线(T4-J1.2,2026-09-29)。

对 vins_smoke 轮 bag 自动定位四个时刻: takeoff(首次 armed)/goal(首个 goal)/
anchor(goal+5s 锚窗,与 round_result 同口径)/land(末次 armed→disarm),
在每个时刻 ±0.3s 窗内配对左右目帧导出,供 J1.3/J2 特征密度判读与对照。

用法: python3 bag_extract_moments.py <bag> [--out 目录] [--tag 轮名]
输出: <out>/<tag>/moment_<名>.png + moments.json(每时刻 stamp/配对信息)

依赖: rosbag/cv2/numpy;话题缺项自动降级(缺 goal 时只出 takeoff/land)。
"""
import argparse, json, os, sys
import rospy
import numpy as np

try:
    import rosbag
except ImportError:
    raise SystemExit("需要 ROS Noetic python3(rosbag)")
try:
    import cv2
except ImportError:
    raise SystemExit("需要 opencv-python (cv2)")

L_T = "/iris_stereo_vins/vins_cam_left/image_raw"
R_T = "/iris_stereo_vins/vins_cam_right/image_raw"
STATE_T = "/mavros/state"
GOAL_T = "/move_base_simple/goal"

def to_gray(msg):
    enc = msg.encoding.lower()
    if enc in ("rgb8", "bgr8"):
        arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY if enc == "bgr8" else cv2.COLOR_RGB2GRAY)
    if enc == "mono8":
        return np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width)
    raise ValueError(f"编码不支持: {enc}")

def label_bar(img, text):
    bar = np.full((28, img.shape[1], 3), 30, np.uint8)
    cv2.putText(bar, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([bar, img])

def moments_from_bag(bag):
    """从 bag 元话题推导四时刻(sim 域秒)。"""
    armed_ts, goal_ts = [], []
    for topic, msg, t_rec in bag.read_messages(topics=[STATE_T, GOAL_T]):
        if topic == STATE_T:
            # mavros state 的 header.stamp 在个别 boot 有 0 戳,统一用 bag 接收时间
            armed_ts.append((t_rec.to_sec(), bool(msg.mode), msg.armed))
        else:
            goal_ts.append(t_rec.to_sec())  # rostopic pub 的 goal header.stamp=0,用接收时间
    arms = [t for t, _m, a in armed_ts if a]
    if not arms:
        return None, "无 armed 段(非飞行轮?)"
    moms = {"takeoff": arms[0]}
    last_t, _m, last_armed = armed_ts[-1]
    # land=末态时刻;FAIL 轮未降落时=末态(如实标注)
    moms["land"] = last_t if not last_armed else arms[-1]
    if goal_ts:
        g = max(t for t in goal_ts if t > arms[0])  # 取起飞后的首个 goal(滤掉 0 戳/发射前噪声)
        moms["goal"] = g
        moms["anchor"] = g + 5.0
    return moms, None

def pair_at(bag, t, win=0.3, tol=0.005):
    """取 t±win 内时间戳最近的一对 L/R 帧。"""
    best = None  # (|ts-t|, ts, L, R)
    last = {}   # topic -> (ts, gray)
    start = rospy.Time.from_sec(max(t - win, 0.0))
    end = rospy.Time.from_sec(t + win)
    for topic, msg, _ in bag.read_messages(topics=[L_T, R_T], start_time=start, end_time=end):
        ts = msg.header.stamp.to_sec()
        last[topic] = (ts, to_gray(msg))
        if L_T in last and R_T in last:
            lt, lg = last[L_T]; rt, rg = last[R_T]
            if abs(lt - rt) <= tol:
                d = abs(lt - t)
                if best is None or d < best[0]:
                    best = (d, lt, lg, rg)
    return best

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bagfile")
    ap.add_argument("--out", default=os.path.expanduser("~/sitl_sim/vision_inputs"))
    ap.add_argument("--tag", default=None, help="轮名目录(缺省=bag 名)")
    a = ap.parse_args()
    tag = a.tag or os.path.splitext(os.path.basename(a.bagfile))[0]
    outdir = os.path.join(a.out, tag)
    os.makedirs(outdir, exist_ok=True)
    bag = rosbag.Bag(a.bagfile, "r")
    moms, err = moments_from_bag(bag)
    if moms is None:
        raise SystemExit(f"时刻定位失败: {err}")
    meta = {"bag": a.bagfile, "tag": tag, "moments": {}}
    for name, t in moms.items():
        p = pair_at(bag, t)
        if p is None:
            meta["moments"][name] = {"t": t, "paired": False}
            print(f"[{name}] t={t:.3f} 无配对帧(跳过)")
            continue
        _d, ts, lg, rg = p
        side = np.vstack([
            label_bar(cv2.cvtColor(lg, cv2.COLOR_GRAY2BGR), f"L {name} t={ts:.3f}"),
            label_bar(cv2.cvtColor(rg, cv2.COLOR_GRAY2BGR), "R"),
        ])
        fn = os.path.join(outdir, f"moment_{name}.png")
        cv2.imwrite(fn, side)
        meta["moments"][name] = {"t": t, "paired": True, "frame_ts": ts, "file": fn}
        print(f"[{name}] t={t:.3f} 帧t={ts:.3f} -> {fn}")
    bag.close()
    with open(os.path.join(outdir, "moments.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"完成: {outdir}(moments.json)")

if __name__ == "__main__":
    main()
