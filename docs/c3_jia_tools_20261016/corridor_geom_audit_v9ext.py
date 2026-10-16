#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""corridor_geom_audit.py — ③C 避障几何审计（单元3 试录判读门 + 单元4 正式批证书）
输入: rosbag（vins_smoke 产物：/gazebo/model_states 真值 + /vins_estimator/imu_propagate VINS odom
      + /move_base_simple/goal 航点）
输出: JSON+人读行——
  per-lane: path_len(真值), straight_len, ratio,
            box_min_dist_center/surface/inflated(全箱最小),
            max_lat_dev(相对走廊中线), lat_dev_signed 序列统计,
            detour_segments[{box, t_start, t_end, peak_dev, side, vflip}],
            vins_cross(VINS odom 帧对齐后同口径交叉列)
口径:
  - 箱坐标=gazebo 帧正源（world_design_rationale.md §8）; odom=gazebo-(1.01,0.98)
  - 主度量=真值(gazebo 帧) vs 箱(gazebo 帧)——物理正源, 零帧对齐假设;
    VINS odom 侧经出生锚对齐(首帧差)后同算 = 交叉列(帧对齐纪律③A topic_binding 精神,
    不共享帧假设, 差值入报告)
  - 门(单元3 预注册): 膨胀边界距<0.2 ∧ ratio≥1.25 ∧ 幅值≥0.8 ∧ 绕行弧目视确认
用法: python3 corridor_geom_audit.py <bag> [--lane E|NE] [--json out.json]
"""
import sys, math, json, argparse

# ---- 箱正源（gazebo 帧; odom = gazebo - (1.01,0.98)）---- 正源=gen_corridor_world.py 表1 输出
# v4=RC-1b standoff(E4.5/NE4.0,d=0.20); v5=迫S形迭代(d=0.45, md5 191b06de)
WORLD_TABLES = {  # name: {box: (gx, gy, half, z0, sz)}
    "v4": {
        "cB1": (5.482, 1.517, 0.5, 0.0, 1.8), "cB2": (8.005, 1.306, 0.5, 0.0, 1.8),
        "cB3": (10.468, 1.893, 0.5, 0.0, 1.8), "cB4": (12.991, 1.682, 0.5, 0.0, 1.8),
        "cN1": (3.702, 3.946, 0.5, 0.0, 1.8), "cN2": (5.755, 5.427, 0.5, 0.0, 1.8),
        "cN3": (7.243, 7.476, 0.5, 0.0, 1.8),
    },
    "v5": {
        "cB1": (5.463, 1.767, 0.5, 0.0, 1.8), "cB2": (8.024, 1.057, 0.5, 0.0, 1.8),
        "cB3": (10.449, 2.142, 0.5, 0.0, 1.8), "cB4": (13.010, 1.433, 0.5, 0.0, 1.8),
        "cN1": (3.525, 4.123, 0.5, 0.0, 1.8), "cN2": (5.931, 5.250, 0.5, 0.0, 1.8),
        "cN3": (7.066, 7.653, 0.5, 0.0, 1.8),
    },
    "v6": {
        "cB1": (5.467, 1.717, 0.5, 0.0, 1.8), "cB2": (8.020, 1.107, 0.5, 0.0, 1.8),
        "cB3": (10.452, 2.092, 0.5, 0.0, 1.8), "cB4": (13.005, 1.482, 0.5, 0.0, 1.8),
        "cN1": (3.554, 4.080, 0.5, 0.0, 1.8), "cN2": (5.885, 5.275, 0.5, 0.0, 1.8),
        "cN3": (7.087, 7.602, 0.5, 0.0, 1.8),
    },
    "v7": {
        "cB1": (5.452, 1.916, 0.5, 0.0, 1.8), "cB2": (10.528, 1.095, 0.5, 0.0, 1.8),
        "cB3": (12.931, 2.480, 0.5, 0.0, 1.8),
        "cN1": (3.419, 4.229, 0.5, 0.0, 1.8), "cN2": (6.037, 5.144, 0.5, 0.0, 1.8),
        "cN3": (6.960, 7.759, 0.5, 0.0, 1.8),
    },
    "v8": {
        "cB1": (2.959, 1.729, 0.5, 0.0, 1.8),
        "cB2": (5.542, 0.720, 0.5, 0.0, 1.8),
        "cB3": (7.945, 2.104, 0.5, 0.0, 1.8),
        "cB4": (10.528, 1.095, 0.5, 0.0, 1.8),
        "cB5": (12.931, 2.480, 0.5, 0.0, 1.8),
        "cN1": (2.357, 3.170, 0.5, 0.0, 1.8),
        "cN2": (4.975, 4.085, 0.5, 0.0, 1.8),
        "cN3": (5.898, 6.700, 0.5, 0.0, 1.8),
        "cN4": (8.516, 7.615, 0.5, 0.0, 1.8),
        "cN5": (9.439, 10.230, 0.5, 0.0, 1.8),
    },
    # v9 实验室尺度(2026-10-16 预注册锁定, gen_corridor_world_v9.py 表1 正源; md5 5f3d48eb)
    "v9": {
        "cL1": (2.4384, 2.6629, 0.3, 0.0, 1.5),
        "cL2": (4.4607, 4.1761, 0.3, 0.0, 1.5),
    },
}
# v9 S 形门推导值(跑前锁定, 预注册 §4; 源=gen_corridor_world_v9.py 数值路径积分)
V9_GATE = {"ratio": 1.07, "maxlat": 0.32, "ndetour": 2, "thr": 0.32,
           "s1": 2.2, "s2": 4.7, "infl_half": 0.723}
BOXES_G = WORLD_TABLES["v6"]  # 默认 v6(在役); --world 参数可切
INFL = 0.299
LANES = {  # name: (x0,y0,x1,y1) gazebo 帧; 真航线=spawn+goal_raw 位移(RC-1 帧系定案)
    "E":  (1.01, 0.98, 14.02, 1.96),
    "NE": (1.01, 0.98, 10.505, 10.445),
    # v9 实验室尺度对角 lane: spawn gazebo(1.01,0.98)→goal gazebo(5.21,5.18)=odom(4.2,4.2) z0.8
    "LAB": (1.01, 0.98, 5.21, 5.18),
}
OX, OY = 1.01, 0.98

def lane_frame(lane, x, y):
    """航线坐标系: along=沿中线里程, lat=横向(左侧为正)"""
    (x0, y0, x1, y1) = LANES[lane]
    dx, dy = x1-x0, y1-y0
    L = math.hypot(dx, dy)
    ux, uy = dx/L, dy/L
    px, py = -uy, ux
    rx, ry = x-x0, y-y0
    return rx*ux + ry*uy, rx*px + ry*py

def dist_box(x, y, z, b):
    gx, gy, h, z0, sz = b
    dx = max(abs(x-gx)-h, 0.0); dy = max(abs(y-gy)-h, 0.0)
    dz = max(max(z0-z, z-(z0+sz)), 0.0)
    return math.hypot(dx, dy, dz), max(math.hypot(dx, dy, dz)-INFL, 0.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag"); ap.add_argument("--lane", default="E", choices=list(LANES))
    ap.add_argument("--world", default="v6", choices=list(WORLD_TABLES),
                    help="箱表版本(v4/v5 迭代期, v6=在役)")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    global BOXES_G
    BOXES_G = WORLD_TABLES[args.world]
    import rosbag
    truth, prop, goals = [], [], []
    with rosbag.Bag(args.bag, "r") as b:
        for topic, msg, t in b.read_messages():
            ts = t.to_sec()
            if topic == "/gazebo/model_states":
                try: i = msg.name.index("iris_stereo_vins")
                except ValueError: continue
                p = msg.pose[i].position; truth.append((ts, p.x, p.y, p.z))
            elif topic == "/vins_estimator/imu_propagate":
                p = msg.pose.pose.position; prop.append((ts, p.x, p.y, p.z))
            elif topic == "/move_base_simple/goal":
                p = msg.pose.position; goals.append((ts, p.x, p.y, p.z))
    if len(truth) < 10:
        print("AUDIT=FAIL no truth"); sys.exit(1)
    x1, y1 = LANES[args.lane][2], LANES[args.lane][3]
    g1 = next((g for g in goals if abs(g[1]-x1) < 0.01 and abs(g[2]-y1) < 0.01), None)
    if g1:
        truth = [p for p in truth if p[0] >= g1[0] - 1.0]   # 起飞后航线窗(含 goal 前1s)
    L_straight = math.hypot(LANES[args.lane][2]-LANES[args.lane][0],
                            LANES[args.lane][3]-LANES[args.lane][1])
    # ---- 真值主度量 ----
    path_len = sum(math.hypot(truth[i+1][1]-truth[i][1], truth[i+1][2]-truth[i][2])
                   for i in range(len(truth)-1) if math.hypot(truth[i+1][1]-truth[i][1],
                                                              truth[i+1][2]-truth[i][2]) < 1.0)  # 防重锚尖峰>1m 帧污染
    min_c = min_s = min_i = 9e9; min_c_box = min_s_box = min_i_box = None
    per_box = {bn: {"min_surf": 9e9, "min_infl": 9e9} for bn in BOXES_G}  # v1.5 判据②: 逐箱交互证明
    lats = []
    for (ts, x, y, z) in truth:
        for bn, b in BOXES_G.items():
            gx, gy, h, z0, sz = b
            dx = max(abs(x-gx)-h, 0.0); dy = max(abs(y-gy)-h, 0.0)
            dz = max(max(z0-z, z-(z0+sz)), 0.0)
            d_surf = math.hypot(dx, dy, dz)
            d_ctr = math.hypot(x-gx, y-gy)
            d_inf = max(d_surf - INFL, 0.0)
            if d_surf < per_box[bn]["min_surf"]: per_box[bn]["min_surf"] = d_surf
            if d_inf < per_box[bn]["min_infl"]: per_box[bn]["min_infl"] = d_inf
            if d_ctr < min_c: min_c, min_c_box = d_ctr, bn
            if d_surf < min_s: min_s, min_s_box = d_surf, bn
            if d_inf < min_i: min_i, min_i_box = d_inf, bn
        lats.append(lane_frame(args.lane, x, y)[1])
    ratio = path_len / L_straight if L_straight else 0
    for bn in per_box:  # 未接近过的箱保持 None(未交互)
        for k in ("min_surf", "min_infl"):
            per_box[bn][k] = round(per_box[bn][k], 3) if per_box[bn][k] < 9e8 else None
    n_interact = sum(1 for v in per_box.values()
                     if v["min_infl"] is not None and v["min_infl"] < 0.2)  # 判据②: 膨胀边界距<0.2 的箱数
    min_surf_all = min((v["min_surf"] for v in per_box.values() if v["min_surf"] is not None), default=None)
    max_lat = max(abs(l) for l in lats) if lats else 0
    # ---- 绕行段检测: lat 序列越过 ±(0.799-STAGGER 余量) 的连续段 ----
    THR = 0.55   # 横向偏离阈值(进入有效绕行; 强制几何下限0.599 之下取识别阈)
    if args.world == "v9":
        THR = V9_GATE["thr"]   # v9 推导阈=A-0.10=0.32(预注册 §4; 旧版本 0.55 不变)
    segs, cur = [], None
    for i, (ts, x, y, z) in enumerate(truth):
        lat = lats[i]
        if abs(lat) > THR:
            if cur is None or (lat > 0) != cur["side"]:
                if cur: segs.append(cur)
                cur = {"side": lat > 0, "t0": ts, "t1": ts, "peak": abs(lat)}
            cur["t1"] = ts; cur["peak"] = max(cur["peak"], abs(lat))
        else:
            if cur:
                segs.append(cur); cur = None
    if cur: segs.append(cur)
    # 每段横向速度符号翻转(真值相邻帧 lat 差符号变化, 平滑后)
    flips = []
    for s in segs:
        w = [lats[i] for i, p in enumerate(truth) if s["t0"] <= p[0] <= s["t1"]]
        f = sum(1 for i in range(1, len(w)-1)
                if (w[i]-w[i-1]) * (w[i+1]-w[i]) < 0 and abs(w[i+1]-w[i-1]) > 0.02)
        flips.append(f)
    # ---- VINS odom 交叉列(出生锚对齐: 首帧 truth-prop 差) ----
    xv = "-"
    if prop:
        a = (truth[0][1]-prop[0][1], truth[0][2]-prop[0][2], truth[0][3]-prop[0][3])
        mc = 9e9
        for (ts, px, py, pz) in prop:
            xg, yg = px + a[0], py + a[1]
            for bn, b in BOXES_G.items():
                dx = max(abs(xg-b[0])-b[2], 0.0); dy = max(abs(yg-b[1])-b[2], 0.0)
                dz = max(max(b[3]-(pz+a[2]), (pz+a[2])-(b[3]+b[4])), 0.0)
                mc = min(mc, math.hypot(dx, dy, dz) - INFL)
        xv = max(mc, 0.0)
    out = {
        "bag": args.bag, "lane": args.lane, "n_truth": len(truth),
        "path_len": round(path_len, 3), "straight_len": round(L_straight, 3),
        "ratio": round(ratio, 4),
        "box_min_center": round(min_c, 3), "box_min_center_box": min_c_box,
        "box_min_surface": round(min_s, 3), "box_min_surface_box": min_s_box,
        "box_min_inflated": round(min_i, 3), "box_min_inflated_box": min_i_box,
        "max_lat_dev": round(max_lat, 3),
        "detour_segments": [{"side": "N" if s["side"] else "S",
                             "t0": round(s["t0"], 2), "t1": round(s["t1"], 2),
                             "peak": round(s["peak"], 3), "vflip": flips[i]}
                            for i, s in enumerate(segs)],
        "n_detours": len(segs),
        "per_box": per_box,
        "n_boxes_interact_lt0.2": n_interact,
        "min_surf_all": min_surf_all,
        "gate_interact_ge3_infl_lt0.2": bool(n_interact >= 3),
        "gate_no_collision_surf_gt0": bool(min_surf_all is None or min_surf_all > 0.0),
        "vins_cross_min_inflated": round(xv, 3) if isinstance(xv, float) else xv,
        # 单元3 预注册门
        "gate_min_inflated_lt_0.2": bool(min_i < 0.2),
        "gate_ratio_ge_1.25": bool(ratio >= 1.25),
        "gate_maxlat_ge_0.8": bool(max_lat >= 0.8),
        "gate_ndetour_ge_3": bool(len(segs) >= 3),
    }
    # ---- v9 S 形推导门(预注册 §4 五项; additive, 旧版本不产生这些键) ----
    if args.world == "v9":
        alternating = bool(len(segs) >= 2 and all(
            segs[i]["side"] != segs[i+1]["side"] for i in range(len(segs)-1)))
        g1v9 = bool(min_i < 0.2)
        g2v9 = bool(len(segs) >= V9_GATE["ndetour"])
        g3v9 = bool(max_lat >= V9_GATE["maxlat"])
        g4v9 = bool(ratio >= V9_GATE["ratio"])
        out.update({
            "gate_v9_infl_lt_0.2": g1v9, "gate_v9_ndetour_ge_2": g2v9,
            "gate_v9_maxlat_ge_0.32": g3v9, "gate_v9_ratio_ge_1.07": g4v9,
            "gate_v9_alternating": alternating,
            "gate_v9_sform_all": bool(g1v9 and g2v9 and g3v9 and g4v9 and alternating),
            "v9_detour_thr": THR,
        })
        # 进出场余量实证面(预注册 §9): onset=首个避障决策点(|lat|>0.10), converge=末次偏出后回中线
        onset_s = next((lane_frame(args.lane, x, y)[0]
                        for (ts, x, y, z) in truth
                        if abs(lane_frame(args.lane, x, y)[1]) > 0.10), None)
        tail = [(lane_frame(args.lane, x, y) and (lane_frame(args.lane, x, y)[0], lane_frame(args.lane, x, y)[1]))
                for (ts, x, y, z) in truth]
        converge_s = None
        for (s_, lat_) in reversed(tail):
            if abs(lat_) > 0.10:
                break
            converge_s = s_
        out["v9_onset_s"] = round(onset_s, 3) if onset_s is not None else None
        out["v9_margin_in"] = round(onset_s - (V9_GATE["s1"] - V9_GATE["infl_half"]), 3) if onset_s is not None else None
        out["v9_converge_s"] = round(converge_s, 3) if converge_s is not None else None
        out["v9_converge_after_last_box"] = (round(converge_s - V9_GATE["s2"], 3)
                                             if converge_s is not None and converge_s > V9_GATE["s2"] else None)
        out["v9_remaining_to_goal"] = round(L_straight - converge_s, 3) if converge_s is not None else None
    print("lane=%s path_len=%.3f ratio=%.4f | box_min ctr/surf/infl=%.3f/%.3f/%.3f (%s/%s/%s) | max_lat=%.3f | detours=%d %s"
          % (args.lane, path_len, ratio, min_c, min_s, min_i, min_c_box, min_s_box, min_i_box,
             max_lat, len(segs),
             "".join("[%s p%.2f f%d]" % (("N" if s["side"] else "S"), s["peak"], flips[i])
                     for i, s in enumerate(segs))))
    print("GATES: infl<0.2=%s ratio>=1.25=%s maxlat>=0.8=%s ndetour>=3=%s | vins_cross_infl=%s | interact>=3box=%s n=%d min_surf_all=%s"
          % (out["gate_min_inflated_lt_0.2"], out["gate_ratio_ge_1.25"],
             out["gate_maxlat_ge_0.8"], out["gate_ndetour_ge_3"], xv,
             out["gate_interact_ge3_infl_lt0.2"], n_interact, min_surf_all))
    if args.world == "v9":
        print("GATES-V9: infl<0.2=%s ndetour>=2=%s maxlat>=0.32=%s ratio>=1.07=%s alternating=%s | SFORM_ALL=%s | onset_s=%s margin_in=%s converge_s=%s after_last_box=%s remain_to_goal=%s"
              % (out["gate_v9_infl_lt_0.2"], out["gate_v9_ndetour_ge_2"], out["gate_v9_maxlat_ge_0.32"],
                 out["gate_v9_ratio_ge_1.07"], out["gate_v9_alternating"], out["gate_v9_sform_all"],
                 out.get("v9_onset_s"), out.get("v9_margin_in"), out.get("v9_converge_s"),
                 out.get("v9_converge_after_last_box"), out.get("v9_remaining_to_goal")))
    if args.json:
        with open(args.json, "w") as f: json.dump(out, f, indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
