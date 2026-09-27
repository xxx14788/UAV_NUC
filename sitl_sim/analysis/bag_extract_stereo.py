#!/usr/bin/env python3
"""bag 双目抽帧导出（T2-W0-4，给 T4 视觉线目视判读；本任务无视觉能力）。

用法: python3 bag_extract_stereo.py <bag文件> [--n 6] [--out 目录]
                                    [--left-topic T] [--right-topic T]

输出到 --out（默认 ~/sitl_sim/vision_inputs/）:
  stereo_pair_<bag名>_<idx>.png   左右并排（上左下右带标签）
  diff_map_<bag名>_<idx>.png      对齐视差后 |L-R| 差分热力图（colorbar）
  overlay_<bag名>_<idx>.png       对齐后 R 通道红 / L 通道青 叠加对比
  summary.json                    每帧 stamp/均值/std/NCC/相位相关位移
依赖: ROS Noetic python3 + cv2/numpy/matplotlib(Agg)
"""
import argparse
import json
import os

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
    enc = msg.encoding.lower()
    if enc in ("rgb8", "bgr8"):
        arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width, 3)
        return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY if enc == "bgr8"
                            else cv2.COLOR_RGB2GRAY)
    if enc == "mono8":
        return np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width)
    raise ValueError(f"不支持的编码: {enc}")


def label_bar(img, text):
    bar = np.full((28, img.shape[1], 3), 30, np.uint8)
    cv2.putText(bar, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bagfile")
    ap.add_argument("--n", type=int, default=6, help="抽帧数（均布全 bag）")
    ap.add_argument("--out", default=os.path.expanduser(
        "~/sitl_sim/vision_inputs"))
    ap.add_argument("--left-topic", default=LEFT_TOPIC_DEF)
    ap.add_argument("--right-topic", default=RIGHT_TOPIC_DEF)
    args = ap.parse_args()

    import rosbag
    os.makedirs(args.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.bagfile))[0]
    pairs = []  # (stamp, L, R)
    last_l = last_r = None  # (t, gray)，单帧回看配对，兼容 L/R 任一先到
    TOL = 0.005

    with rosbag.Bag(args.bagfile, "r") as bag:
        info = bag.get_type_and_topic_info().topics
        n_est = info[args.left_topic].message_count \
            if args.left_topic in info else 100
        idx_pick = set(np.linspace(0, max(n_est - 2, 0),
                                   max(args.n, 1)).round().astype(int))
        got = set()
        i = 0
        for topic, msg, _t in bag.read_messages(
                topics=[args.left_topic, args.right_topic]):
            ts = msg.header.stamp.to_sec()
            if topic == args.left_topic:
                cur = (ts, to_gray(msg))
                if i in idx_pick and i not in got and last_r is not None \
                        and abs(last_r[0] - ts) <= TOL:
                    pairs.append((ts, cur[1], last_r[1]))
                    got.add(i)
                    last_r = None
                else:
                    last_l = cur
                i += 1
            else:
                cur = (ts, to_gray(msg))
                if last_l is not None and abs(last_l[0] - ts) <= TOL \
                        and (i - 1) in idx_pick and (i - 1) not in got:
                    pairs.append((last_l[0], last_l[1], cur[1]))
                    got.add(i - 1)
                    last_l = None
                else:
                    last_r = cur
            if len(pairs) >= args.n:
                break
    if not pairs:
        raise SystemExit("未抽到任何配对帧")

    summary = []
    for k, (ts, lt, rt) in enumerate(pairs):
        try:
            (dx, dy), _ = cv2.phaseCorrelate(np.float32(lt), np.float32(rt))
        except cv2.error:
            dx = dy = 0.0
        M = np.float32([[1, 0, -dx], [0, 1, 0]])
        rt_a = cv2.warpAffine(rt, M, (rt.shape[1], rt.shape[0]))
        a = lt.astype(np.float64); b = rt_a.astype(np.float64)
        ncc = float(np.sum((a - a.mean()) * (b - b.mean())) /
                    np.sqrt(np.sum((a - a.mean()) ** 2) *
                            np.sum((b - b.mean()) ** 2)))
        diff = np.abs(lt.astype(np.int16) - rt_a.astype(np.int16))

        side = np.vstack([
            label_bar(cv2.cvtColor(lt, cv2.COLOR_GRAY2BGR), f"L  t={ts:.3f}"),
            label_bar(cv2.cvtColor(rt, cv2.COLOR_GRAY2BGR), "R"),
        ])
        fn = os.path.join(args.out, f"stereo_pair_{base}_{k:02d}.png")
        cv2.imwrite(fn, side)

        fn_d = os.path.join(args.out, f"diff_map_{base}_{k:02d}.png")
        fig, ax = plt.subplots(figsize=(7, 5))
        im = ax.imshow(diff, cmap="viridis")
        ax.set_title(f"|L-R| aligned dx={dx:.1f}px  NCC={ncc:.3f}")
        fig.colorbar(im, ax=ax, label="abs diff")
        fig.tight_layout()
        fig.savefig(fn_d, dpi=100)
        plt.close(fig)

        ov = np.zeros((lt.shape[0], lt.shape[1], 3), np.uint8)
        ov[:, :, 0] = rt_a   # 右目 → 红
        ov[:, :, 1] = lt     # 左目 → 绿
        ov[:, :, 2] = lt     # 左目 → 蓝（青）
        fn_o = os.path.join(args.out, f"overlay_{base}_{k:02d}.png")
        cv2.imwrite(fn_o, ov)

        summary.append({
            "idx": k, "stamp": ts,
            "L_mean": float(lt.mean()), "L_std": float(lt.std()),
            "R_mean": float(rt.mean()), "R_std": float(rt.std()),
            "phase_dx": float(dx), "phase_dy": float(dy),
            "ncc_aligned": ncc, "diff_mean": float(diff.mean()),
        })
        print(f"[{k}] t={ts:.3f} L {lt.mean():.1f}±{lt.std():.1f} "
              f"R {rt.mean():.1f}±{rt.std():.1f} dx={dx:.1f}px "
              f"NCC={ncc:.3f} diff_mean={diff.mean():.1f}")

    js = os.path.join(args.out, f"summary_{base}.json")
    with open(js, "w", encoding="utf-8") as f:
        json.dump({"bag": os.path.abspath(args.bagfile),
                   "n_extracted": len(pairs), "frames": summary},
                  f, ensure_ascii=False, indent=2)
    print(f"输出 {len(pairs)} 组 → {args.out}\n汇总: {js}")


if __name__ == "__main__":
    main()
