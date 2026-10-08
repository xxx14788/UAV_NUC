#!/usr/bin/env python3
# T1 v11.34 — landed=0 五轮落地真相探针: bag 真值 z 尾序列 + armed 尾态
# 判定: KILL+disarm 后自由落体是否在 bag 窗内触地 (z→~0) 或 bag 先停 (悬空截断)
import rosbag, sys

RUNS = {
    "S1_r2": "215653", "S2_r3": "222406", "S2_r4": "224313",
    "S3_r2": "220927", "S4_r3": "223339",
}
BASE = "/home/ghj/sitl_sim/vins_smoke_runs/run_DRILLD1_N8P_%s/flight.bag"

for tag, suffix in RUNS.items():
    path = BASE % suffix
    try:
        bag = rosbag.Bag(path)
    except Exception as e:
        print(f"{tag} ({suffix}): BAG-OPEN-FAIL {e}")
        continue
    zs = []   # (t, z) truth
    armed = []  # (t, armed)
    iris_idx = None
    for topic, msg, t in bag.read_messages(topics=["/gazebo/model_states", "/mavros/state"]):
        if topic == "/gazebo/model_states":
            if iris_idx is None:
                for i, n in enumerate(msg.name):
                    if "iris" in n or "uav" in n.lower():
                        iris_idx = i; break
                if iris_idx is None:
                    iris_idx = 0
            zs.append((t, msg.pose[iris_idx].position.z))
        else:
            armed.append((t, msg.armed))
    bag.close()
    zs.sort(); armed.sort()
    tail_z = zs[-12:]
    last_t = zs[-1][0] if zs else 0
    z_min_tail = min(z for _, z in zs[-60:]) if len(zs) >= 60 else min(z for _, z in zs)
    a_last = armed[-1][1] if armed else None
    # disarm 时刻: armed 从 1→0 的最后跳变
    disarm_t = None
    for i in range(1, len(armed)):
        if armed[i-1][1] and not armed[i][1]:
            disarm_t = armed[i][0]
    # bag 末端真值 z 序列(去重打印)
    seq = " ".join(f"{z:.2f}" for _, z in tail_z)
    z_at_disarm = None
    if disarm_t is not None:
        cand = [z for t, z in zs if t <= disarm_t]
        z_at_disarm = cand[-1] if cand else None
    print(f"{tag} ({suffix}): bag_z_tail[{seq}] z_tail_min60={z_min_tail:.2f} "
          f"armed_last={a_last} disarm_t={'%.1f' % ((disarm_t-last_t)/1e9) if disarm_t else 'NO'}s(rel_end) "
          f"z@disarm={('%.2f' % z_at_disarm) if z_at_disarm is not None else 'NA'} "
          f"truth_n={len(zs)}")
