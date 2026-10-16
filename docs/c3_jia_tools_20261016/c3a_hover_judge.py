#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3a_hover_judge.py — Phase A 悬停轮判读薄包装（③C-甲 §二）
口径=tools_b4/c1_drift_rate.py hover_rate 函数逐字复制（判读器语义禁改红线⑤；
本件仅参数化输入 bag 路径，公式零改动）+ 面1 stereo_r p50（simvins.log T2IQG-METRIC）。
用法: c3a_hover_judge.py <rundir>   → 打印一行 + 写 <rundir>/hover_judge.json
"""
import sys, os, json, re, statistics


def hover_rate(bagp):
    import rosbag
    truth = []
    with rosbag.Bag(bagp, "r") as b:
        for topic, msg, t in b.read_messages():
            if topic == "/gazebo/model_states":
                try: i = msg.name.index("iris_stereo_vins")
                except ValueError: continue
                p = msg.pose[i].position
                truth.append((t.to_sec(), p.x, p.y, p.z))
    truth.sort()
    seg, best = [], []
    for fr in truth:
        if fr[3] >= 0.9: seg.append(fr)
        else:
            if len(seg) > len(best): best = seg
            seg = []
    if len(seg) > len(best): best = seg
    t0 = best[0][0]; span = best[-1][0] - t0
    x0, y0 = best[0][1], best[0][2]
    x1, y1 = best[-1][1], best[-1][2]
    full = ((x1-x0)**2 + (y1-y0)**2) ** 0.5
    w25 = [fr for fr in best if fr[0] - t0 <= 25.0]
    d25 = ((w25[-1][1]-w25[0][1])**2 + (w25[-1][2]-w25[0][2])**2) ** 0.5
    rate = full / span * 60
    return rate, d25, span, full


def stereo_r_p50(rundir):
    log = os.path.join(rundir, "simvins.log")
    if not os.path.exists(log):
        return None, 0
    txt = open(log, encoding="utf-8", errors="ignore").read()
    srs = [float(m.group(1)) for m in re.finditer(
        r"\[T2IQG-METRIC\] t=[0-9.]+ corners=\d+ depth_r=[0-9.]+ stereo_r=([0-9.]+)", txt)]
    if not srs:
        return None, 0
    return statistics.median(srs), len(srs)


def main():
    rundir = sys.argv[1]
    bag = os.path.join(rundir, "flight.bag")
    rate, d25, span, full = hover_rate(bag)
    sr50, srn = stereo_r_p50(rundir)
    out = {"rundir": rundir, "drift_rate_m_per_min": round(rate, 3),
           "w25_xy_m": round(d25, 3), "main_span_s": round(span, 1),
           "main_xy_m": round(full, 3),
           "stereo_r_p50": None if sr50 is None else round(sr50, 4), "stereo_r_n": srn}
    with open(os.path.join(rundir, "hover_judge.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{os.path.basename(rundir)}: 漂移率={rate:.3f}m/min | 25s窗XY={d25:.3f}m | 主段{span:.1f}s/{full:.3f}m"
          f" | stereo_r p50={'NA' if sr50 is None else f'{sr50:.3f}'}(n={srn})")


if __name__ == "__main__":
    main()
