#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3_traj_plot.py v2 — ③C 单元5 轨迹图集生成器（英文标注版：matplotlib 无中文字体）
v2 修复(2026-10-14 逐张真看图判定后): ①标注全 ASCII(中文曾渲染为方块)
②odom 轴按 truth 包络+8m 裁剪(暴走 odom 喧宾夺主) ③裁剪时注记 odom-clipped
用法: python3 c3_traj_plot.py <run_dir> <world v4|v5|v6> <lane E|NE> <family_ASCII_note> [out.png]
"""
import sys, os, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rosbag

WORLD_TABLES = {
    "v4": {"cB1": (5.482, 1.517), "cB2": (8.005, 1.306), "cB3": (10.468, 1.893),
           "cB4": (12.991, 1.682), "cN1": (3.702, 3.946), "cN2": (5.755, 5.427), "cN3": (7.243, 7.476)},
    "v5": {"cB1": (5.463, 1.767), "cB2": (8.024, 1.057), "cB3": (10.449, 2.142),
           "cB4": (13.010, 1.433), "cN1": (3.525, 4.123), "cN2": (5.931, 5.250), "cN3": (7.066, 7.653)},
    "v6": {"cB1": (5.467, 1.717), "cB2": (8.020, 1.107), "cB3": (10.452, 2.092),
           "cB4": (13.005, 1.482), "cN1": (3.554, 4.080), "cN2": (5.885, 5.275), "cN3": (7.087, 7.602)},
    # v7 表=audit WORLD_TABLES v7 正源(箱位≡v7.3, C66); F73 批(真 v7.3)与 C-5/C-6 批(实载 v7.0)共用
    "v7": {"cB1": (5.452, 1.916), "cB2": (10.528, 1.095), "cB3": (12.931, 2.480),
           "cN1": (3.419, 4.229), "cN2": (6.037, 5.144), "cN3": (6.960, 7.759)},
    # v9 表=audit WORLD_TABLES v9 正源(gazebo 系薄板箱等效中心; 2026-10-17 v8.6 图集支持面扩展)
    "v9": {"cL1": (2.4384, 2.6629), "cL2": (4.4607, 4.1761)},
}
LANE_GOAL = {"E": (14.02, 1.96), "NE": (10.505, 10.445), "LAB": (5.21, 5.18)}
LANE_START = (1.01, 0.98)
HALF, INFL = 0.5, 0.299
def box_dims(world):
    return (0.301, 0.15) if world == "v9" else (HALF, INFL)

def main():
    run_dir, world, lane, family = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    out = sys.argv[5] if len(sys.argv) > 5 else os.path.join(run_dir, "traj_xy.png")
    boxes = WORLD_TABLES[world]
    truth, prop = [], []
    with rosbag.Bag(os.path.join(run_dir, "flight.bag"), "r") as b:
        for topic, msg, t in b.read_messages(topics=["/gazebo/model_states", "/vins_estimator/imu_propagate"]):
            if topic == "/gazebo/model_states":
                try: i = msg.name.index("iris_stereo_vins")
                except ValueError: continue
                p = msg.pose[i].position; truth.append((p.x, p.y))
            else:
                p = msg.pose.pose.position; prop.append((p.x, p.y))
    if len(truth) < 10:
        print("SKIP %s (no truth)" % run_dir); return 1
    # odom 出生锚平移 + truth 包络裁剪(8m 余量)
    if prop and truth:
        dx0, dy0 = truth[0][0]-prop[0][0], truth[0][1]-prop[0][1]
        prop = [(p[0]+dx0, p[1]+dy0) for p in prop]
    tx = [p[0] for p in truth]; ty = [p[1] for p in truth]
    x0, x1 = min(tx)-3, max(tx)+3; y0, y1 = min(ty)-3, max(ty)+3
    span = max(x1-x0, y1-y0)
    x0, x1 = (x0+x1)/2-span/2-1, (x0+x1)/2+span/2+1
    y0, y1 = (y0+y1)/2-span/2-1, (y0+y1)/2+span/2+1
    prop_in = [(p[0], p[1]) for p in prop if x0 <= p[0] <= x1 and y0 <= p[1] <= y1]
    clipped = len(prop_in) < len(prop)
    fig, ax = plt.subplots(figsize=(9, 9))
    HALF_W, INFL_W = box_dims(world)
    for bn, (gx, gy) in boxes.items():
        if not (x0-1 <= gx <= x1+1 and y0-1 <= gy <= y1+1): continue
        ax.add_patch(plt.Rectangle((gx-HALF_W, gy-HALF_W), 2*HALF_W, 2*HALF_W, fc="saddlebrown", ec="k", alpha=0.85, zorder=3))
        ax.add_patch(plt.Rectangle((gx-HALF_W-INFL_W, gy-HALF_W-INFL_W), 2*(HALF_W+INFL_W), 2*(HALF_W+INFL_W),
                                   fc="none", ec="orange", ls="--", lw=0.8, alpha=0.7, zorder=2))
        ax.text(gx, gy, bn, ha="center", va="center", color="w", fontsize=8, zorder=4)
    ax.plot(tx, ty, "b-", lw=1.2, label="truth (gazebo)", zorder=5)
    if prop_in:
        ax.plot([p[0] for p in prop_in], [p[1] for p in prop_in],
                "c-", lw=0.5, alpha=0.45, label="VINS odom (birth-anchored%s)" % (", clipped" if clipped else ""), zorder=4)
    ax.plot(*LANE_START, "g^", ms=12, zorder=6, label="spawn")
    g = LANE_GOAL[lane]
    if x0 <= g[0] <= x1 and y0 <= g[1] <= y1:
        ax.plot(*g, "r*", ms=16, zorder=6, label="goal")
    gj = None
    for cand in ("/home/ghj/sitl_sim/c3_corridor_20261013/trial_rejudge_v2/geom_%s.json" % os.path.basename(run_dir),
                 "/home/ghj/sitl_sim/c3_corridor_20261013/trial_v5/geom_%s.json" % os.path.basename(run_dir)):
        if os.path.exists(cand):
            gj = json.load(open(cand)); break
    min_surf = gj.get("min_surf_all") if gj else None
    seg_txt = "; ".join("%s%.2f" % (s["side"], s["peak"]) for s in gj.get("detour_segments", [])[:6]) if gj else "no-geom"
    note = "family: %s\nmin_surf=%s m%s\ndetours: %s\nn_interact=%s" % (
        family, ("%.3f" % min_surf) if isinstance(min_surf, float) else min_surf,
        " (>0 no collision)" if isinstance(min_surf, float) and min_surf > 0 else "",
        seg_txt, gj.get("n_boxes_interact_lt0.2") if gj else "?")
    ax.text(0.02, 0.98, note, transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(fc="lightyellow", ec="gray", alpha=0.9), zorder=7)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("%s [%s | world-table=%s lane=%s]" % (os.path.basename(run_dir), family, world, lane), fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
    print("PLOT %s -> %s" % (os.path.basename(run_dir), out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
