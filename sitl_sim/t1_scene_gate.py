#!/usr/bin/env python3
"""t1_scene_gate.py — 场景分门脚本 v1.0 (T1 v11.25 M2 腿A; INPUTFACE-SCREEN 58a4a027 §2)

零栈改动(纯袋侧): 三键 → 轮级风险三档(绿/慎/禁),供批编排发射前咨询+替补顺位联动。
  S1 world×direction 交互项: plain×E/SE 主嫌(T2 门科学包:E×plain 全 A 型)
  S2 gyr_peak 档: /mavros/imu/data_raw 峰值(≥2.5 高危带=T2 替补规避带;绿格全 ≤2.44)
  S3 图像供给面: 角点配额 supply_frac(中位角点/150)+grid4x4 占用(采样帧)
档规则(prereg v1,判据门值与批判读零涉):
  禁 = S1 命中(plain×{E,SE}) 或 gyr_peak≥2.5
  慎 = 1.7≤gyr_peak<2.5 或 supply_frac<0.5 或 grid_occ<0.5
  绿 = 其余
用法:
  t1_scene_gate.py <run_dir> [--sample 30] [--json out.json]
  t1_scene_gate.py --selftest
"""
import os, sys, json, math, argparse


def tier_rules(world, direction, gyr_peak, supply_frac, grid_occ):
    """纯逻辑(gtest/selftest 面): 返回 (档, 命中键列表)"""
    hits = []
    forbidden = False; caution = False
    if world == "sitl_world_plain" and direction in ("E", "SE"):
        hits.append("S1:plain×%s" % direction); forbidden = True
    if gyr_peak is not None and gyr_peak >= 2.5:
        hits.append("S2:gyr_peak=%.2f≥2.5" % gyr_peak); forbidden = True
    elif gyr_peak is not None and gyr_peak >= 1.7:
        hits.append("S2:gyr_peak=%.2f∈[1.7,2.5)" % gyr_peak); caution = True
    if supply_frac is not None and supply_frac < 0.5:
        hits.append("S3:supply_frac=%.2f<0.5" % supply_frac); caution = True
    if grid_occ is not None and grid_occ < 0.5:
        hits.append("S3:grid_occ=%.2f<0.5" % grid_occ); caution = True
    return ("禁" if forbidden else ("慎" if caution else "绿")), hits


def compass(x, y):
    if x == 0 and y == 0:
        return "HOV"
    a = math.degrees(math.atan2(y, x))
    names = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    return names[int(((a + 22.5) % 360) // 45)]


def analyze_run(run_dir, sample):
    import rosbag
    # S1 元数据: goal.txt + round.log world 行(t3_endorse_rerun 同口径)
    gx = gy = None
    try:
        with open(os.path.join(run_dir, "goal.txt")) as f:
            for ln in f:
                if ln.startswith("goal:"):
                    p = ln.split()
                    gx, gy = float(p[1]), float(p[2])
                    break
    except OSError:
        pass
    world = ""
    try:
        with open(os.path.join(run_dir, "round.log"), errors="replace") as f:
            for ln in f:
                if "SITL up (" in ln:
                    world = ln.split("SITL up (")[1].split(")")[0]
                    break
    except OSError:
        pass
    direction = compass(gx, gy) if gx is not None else None
    # S2/S3 袋读: IMU 峰值 + 图像采样角点
    gyr_peak = None; supply_fracs = []; grid_occs = []
    img_ts = []
    bag = os.path.join(run_dir, "flight.bag")
    corners_per_frame = []
    with rosbag.Bag(bag, "r") as b:
        imu_topics = [t for t, _ in b.get_type_and_topic_info().topics.items()
                      if t.endswith("/imu/data_raw")]
        cam_topics = sorted(t for t in b.get_type_and_topic_info().topics
                            if t.endswith("/image_raw"))
        for topic, msg, ts in b.read_messages(topics=imu_topics[:1]):
            g = msg.angular_velocity
            v = math.sqrt(g.x * g.x + g.y * g.y + g.z * g.z)
            if gyr_peak is None or v > gyr_peak:
                gyr_peak = v
            if cam_topics:
                img_ts.append(ts.to_sec())
        if cam_topics:
            n = len(img_ts)
            idxs = sorted(set(int(i * (n - 1) / max(sample - 1, 1)) for i in range(sample)))
            cur = 0
            import numpy as np
            import cv2
            with rosbag.Bag(bag, "r") as b2:
                for topic, msg, ts in b2.read_messages(topics=[cam_topics[0]]):
                    if cur >= len(idxs):
                        break
                    if abs(ts.to_sec() - img_ts[idxs[cur]]) < 1e-4:
                        cur += 1
                        try:
                            arr = np.frombuffer(msg.data, dtype=np.uint8).copy()
                            if msg.encoding in ("bgr8", "rgb8", "mono8"):
                                img = arr.reshape(msg.height, msg.width, -1)
                                if img.shape[2] == 3:
                                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            else:
                                continue
                        except Exception:
                            continue
                        corners = cv2.goodFeaturesToTrack(
                            img, maxCorners=150, qualityLevel=0.01,
                            minDistance=10, blockSize=7)
                        nc = 0 if corners is None else len(corners)
                        corners_per_frame.append(nc)
                        supply_fracs.append(nc / 150.0)
                        if corners is not None and len(corners):
                            occ = set()
                            for c in corners:
                                gx_ = min(int(c[0][0] * 4 / msg.width), 3)
                                gy_ = min(int(c[0][1] * 4 / msg.height), 3)
                                occ.add((gx_, gy_))
                            grid_occs.append(len(occ) / 16.0)
    supply_frac = sorted(supply_fracs)[len(supply_fracs) // 2] if supply_fracs else None
    grid_occ = sorted(grid_occs)[len(grid_occs) // 2] if grid_occs else None
    tier, hits = tier_rules(world, direction, gyr_peak, supply_frac, grid_occ)
    return {
        "run": os.path.basename(run_dir.rstrip("/")), "world": world,
        "direction": direction, "goal": ([gx, gy] if gx is not None else None),
        "gyr_peak": round(gyr_peak, 3) if gyr_peak else None,
        "supply_frac": round(supply_frac, 3) if supply_frac is not None else None,
        "grid4x4_occ": round(grid_occ, 3) if grid_occ is not None else None,
        "n_sampled_frames": len(corners_per_frame), "tier": tier, "hits": hits,
    }


def selftest():
    cases = [
        ("绿-健康", tier_rules("sitl_world_obstacles", "N", 1.0, 0.8, 0.8), "绿"),
        ("禁-plain×E", tier_rules("sitl_world_plain", "E", 1.0, 0.8, 0.8), "禁"),
        ("禁-plain×SE", tier_rules("sitl_world_plain", "SE", 1.0, 0.8, 0.8), "禁"),
        ("绿-plain×N", tier_rules("sitl_world_plain", "N", 1.0, 0.8, 0.8), "绿"),
        ("禁-gyr 高危带", tier_rules("sitl_world_obstacles", "E", 2.5, 0.8, 0.8), "禁"),
        ("慎-gyr 中带", tier_rules("sitl_world_obstacles", "E", 1.7, 0.8, 0.8), "慎"),
        ("慎-供给低", tier_rules("sitl_world_obstacles", "N", 1.0, 0.4, 0.8), "慎"),
        ("慎-占用低", tier_rules("sitl_world_obstacles", "N", 1.0, 0.8, 0.4), "慎"),
        ("禁优先于慎", tier_rules("sitl_world_plain", "E", 0.5, 0.2, 0.2), "禁"),
        ("方位-悬停", tier_rules("sitl_world_obstacles", "HOV", 0.1, 0.8, 0.8), "绿"),
    ]
    ok = 0
    for name, (tier, _), expect in cases:
        mark = "PASS" if tier == expect else "FAIL"
        ok += (tier == expect)
        print("  [%s] %-14s tier=%s expect=%s" % (mark, name, tier, expect))
    print("selftest %d/10" % ok)
    return 0 if ok == 10 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("--sample", type=int, default=30)
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.run_dir:
        ap.error("需要 run_dir 或 --selftest")
    r = analyze_run(os.path.abspath(a.run_dir), a.sample)
    out = json.dumps(r, ensure_ascii=False)
    print(out)
    if a.json:
        open(a.json, "w").write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
