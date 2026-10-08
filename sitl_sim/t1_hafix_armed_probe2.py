#!/usr/bin/env python3
# T1 v11.34 — PASS 轮对照: armed 跳变/真值 z 落地轨迹 + FAIL 轮 armed 尾时间连续性
import rosbag

RUNS = {
    "PASS_S1_r1_214206": "214206", "PASS_S1_r3_221950": "221950",
    "PASS_S3_r5_230621": "230621", "PASS_S4_r4_225546": "225546",
    "FAIL_S2_r3_222406": "222406",
}
BASE = "/home/ghj/sitl_sim/vins_smoke_runs/run_DRILLD1_N8P_%s/flight.bag"

for tag, suffix in RUNS.items():
    bag = rosbag.Bag(BASE % suffix)
    zs, armed = [], []
    iris_idx = None
    t0 = bag.get_start_time(); t1 = bag.get_end_time()
    for topic, msg, t in bag.read_messages(topics=["/gazebo/model_states", "/mavros/state"]):
        if topic == "/gazebo/model_states":
            if iris_idx is None:
                iris_idx = next((i for i, n in enumerate(msg.name) if "iris" in n), 0)
            zs.append((t, msg.pose[iris_idx].position.z))
        else:
            armed.append((t, msg.armed))
    bag.close()
    zs.sort(); armed.sort()
    jumps = [(armed[i][0], armed[i-1][1], armed[i][1]) for i in range(1, len(armed)) if armed[i][1] != armed[i-1][1]]
    tail_z = " ".join(f"{z:.2f}" for _, z in zs[-8:])
    z_min_late = min(z for t, z in zs[-2000:])  # 末 8s 最低
    a_tail = " ".join(f"{int(a)}@{t.to_sec()-t1:+.1f}s" for t, a in armed[-4:])
    jtxt = "; ".join(f"{'%.1f' % (jt.to_sec()-t0)}s:{b}->{a}" for jt, b, a in jumps) or "NO-JUMP"
    print(f"{tag}: jumps[{jtxt}] z_tail8[{tail_z}] z_min_last8s={z_min_late:.2f} armed_tail[{a_tail}] truth_n={len(zs)}")
