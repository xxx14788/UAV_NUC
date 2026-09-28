#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3-D1 VINS 发散袋法证学:逐帧机制重建(任务书 v7.1 D1 协议固化)

对每轮 vins_smoke 失败袋产出:
  1. 发散时刻 t* 精确定位(odometry 与 imu_propagate 各自首条 |dp|>0.1m 帧,排除真机动)
  2. odometry(优化器窗口解) vs imu_propagate(传播解) 分叉点——两者分叉=优化器在 t* 前已病
  3. 频率画像(odom/prop/imu 分段实测 Hz,量化优化器频率崩塌)
  4. IMU 原始统计(dt 分布/加速度饱和/陀螺毛刺)
  5. 事件时间轴(takeoff/goal/position_cmd 首发)与 t* 对齐
  6. 判决行:形态 | t* | 距最近事件 | 分叉类型 | 前兆 | IMU 异常

用法: python3 vins_divergence_forensics.py <run_dir> [--topics t1,t2] [--out run_dir/forensics]
      带图袋必须用 --topics 过滤(红线#4:禁全量扫)
输出: <out>.json(机器) + <out>.txt(人读判决)
"""
import sys, os, json, math, argparse
from bisect import bisect_left

JUMP_M = 0.10          # t* 判据:帧间位置跳变阈值(任务书 D1)
FORK_M = 0.20          # odom-prop 分叉判据
PRECURSOR_M = 0.30     # t* 前 5s 窗内 odom-prop 差前兆判据
TRUE_MOTION_MS = 2.0   # 真值速度超过此值视为真机动,不作病征
ACC_SAT = 50.0         # 加速度模长饱和阈 m/s^2 (gazebo IMU 量级)
GYR_GLITCH = 8.0       # 陀螺毛刺阈 rad/s(单帧)
EARLY_DEATH_GAP = 3.0  # prop/odom 断流>3s 判早死


def read_run(run_dir, topic_filter=None):
    import rosbag
    bag_path = os.path.join(run_dir, "flight.bag")
    data = {"odom": [], "prop": [], "imu": [], "truth": [], "goal": [],
            "poscmd": [], "takeoff_land": [], "state": []}
    with rosbag.Bag(bag_path, "r") as b:
        t0 = None
        topics = None
        if topic_filter:
            topics = topic_filter.split(",")
        for topic, msg, ts in b.read_messages(topics=topics):
            ts_sec = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            if t0 is None:
                t0 = ts_sec if hasattr(msg, "header") else ts_sec
            if topic == "/vins_estimator/odometry":
                p = msg.pose.pose.position
                data["odom"].append((ts_sec, p.x, p.y, p.z))
            elif topic == "/vins_estimator/imu_propagate":
                p = msg.pose.pose.position
                data["prop"].append((ts_sec, p.x, p.y, p.z))
            elif topic == "/mavros/imu/data_raw":
                a = msg.linear_acceleration
                w = msg.angular_velocity
                am = math.sqrt(a.x**2 + a.y**2 + a.z**2)
                wm = math.sqrt(w.x**2 + w.y**2 + w.z**2)
                data["imu"].append((ts_sec, am, wm))
            elif topic == "/gazebo/model_states":
                for name, pose in zip(msg.name, msg.pose):
                    if "iris" in name:
                        p = pose.position
                        data["truth"].append((ts_sec, p.x, p.y, p.z))
                        break
            elif topic == "/move_base_simple/goal":
                p = msg.pose.position
                data["goal"].append((ts_sec, p.x, p.y, p.z))
            elif topic == "/position_cmd":
                p = msg.position
                data["poscmd"].append((ts_sec,
                                       getattr(p, "x", 0), getattr(p, "y", 0), getattr(p, "z", 0)))
            elif topic == "/px4ctrl/takeoff_land":
                data["takeoff_land"].append((ts_sec, msg.takeoff_land_cmd))
            elif topic == "/mavros/state":
                data["state"].append((ts_sec,
                                      1 if msg.armed else 0))
    # 若无一帧带头时间戳(理论不会),回退 ts
    if t0 is None:
        t0 = 0.0
    return data, t0


def nearest(arr, t):
    """arr 按时间升序;返回 (dt, index)。"""
    i = bisect_left(arr, t)
    cands = []
    if i < len(arr):
        cands.append(i)
    if i > 0:
        cands.append(i - 1)
    best = min(cands, key=lambda j: abs(arr[j] - t))
    return abs(arr[best] - t), best


def dist3(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)


def seg_hz(stamps):
    """消息时间戳列表 -> 实测 Hz(总时长/条数)。"""
    if len(stamps) < 2:
        return 0.0
    return (len(stamps) - 1) / (stamps[-1] - stamps[0])


def analyze(run_dir, topic_filter=None):
    data, t0 = read_run(run_dir, topic_filter)
    odom, prop, imu, truth = data["odom"], data["prop"], data["imu"], data["truth"]
    ts_odom = [r[0] for r in odom]; ts_prop = [r[0] for r in prop]
    ts_truth = [r[0] for r in truth]
    rep = {"run": os.path.basename(run_dir.rstrip("/"))}

    # ---------- 事件时间轴 ----------
    ev = {}
    tos = [r for r in data["takeoff_land"] if r[1] == 1]
    if tos:
        ev["t_takeoff"] = tos[0][0] - t0
    armed = [r for r in data["state"] if r[1] == 1]
    if armed and "t_takeoff" not in ev:
        ev["t_takeoff(armed)"] = armed[0][0] - t0
    ev["t_goals"] = [round(g[0] - t0, 1) for g in data["goal"]]
    if data["poscmd"]:
        ev["t_poscmd_first"] = data["poscmd"][0][0] - t0
    rep["events"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in ev.items()}

    # ---------- 频率画像(前/后 1/2 对比) ----------
    freq = {}
    for name, seq in (("odom", odom), ("prop", prop), ("imu", imu), ("truth", truth)):
        if not seq:
            freq[name] = {"n": 0}
            continue
        n = len(seq)
        h1 = seg_hz([r[0] for r in seq[:n//2]])
        h2 = seg_hz([r[0] for r in seq[n//2:]])
        freq[name] = {"n": n, "hz_all": round(seg_hz([r[0] for r in seq]), 1),
                      "hz_1sthalf": round(h1, 1), "hz_2ndhalf": round(h2, 1)}
    rep["freq"] = freq

    # ---------- IMU 原始统计 ----------
    imu_stat = {"n": len(imu)}
    if len(imu) > 2:
        dts = sorted(imu[i+1][0] - imu[i][0] for i in range(len(imu)-1))
        acc_peak = max(r[1] for r in imu)
        gyr_peak = max(r[2] for r in imu)
        acc_sat_n = sum(1 for r in imu if r[1] > ACC_SAT)
        glitch_idx = [i for i in range(1, len(imu)-1)
                      if imu[i][2] > GYR_GLITCH and imu[i-1][2] < 2 and imu[i+1][2] < 2]
        imu_stat.update({
            "dt_p50_ms": round(dts[len(dts)//2]*1000, 2),
            "dt_p99_ms": round(dts[int(len(dts)*0.99)]*1000, 2),
            "dt_max_ms": round(dts[-1]*1000, 2),
            "dt_min_ms": round(dts[0]*1000, 3),
            "acc_peak": round(acc_peak, 1), "acc_sat_frames": acc_sat_n,
            "gyr_peak": round(gyr_peak, 2), "gyr_glitch_frames": len(glitch_idx),
            "gyr_glitch_times": [round(imu[i][0]-t0, 1) for i in glitch_idx[:5]],
        })
    rep["imu"] = imu_stat

    # ---------- t* 定位(各自首条 |dp|>JUMP_M,排除真机动) ----------
    def find_t_star(seq, seq_name):
        for i in range(1, len(seq)):
            dp = dist3(seq[i][1:4], seq[i-1][1:4])
            if dp > JUMP_M:
                dt_frame = seq[i][0] - seq[i-1][0]
                # 同窗真值位移(两帧之间真值走多远)——真机动排除
                truth_move = None
                if truth:
                    _, j0 = nearest(ts_truth, seq[i-1][0])
                    _, j1 = nearest(ts_truth, seq[i][0])
                    truth_move = dist3(truth[j1][1:4], truth[j0][1:4])
                real = (truth_move is not None and truth_move > JUMP_M)
                # 断流后首帧(大 dt)不算帧跳变,记为断流
                if dt_frame > EARLY_DEATH_GAP:
                    return {"t_star": None, "reason": f"{seq_name} 断流 {dt_frame:.1f}s 后首帧",
                            "t_gap_start": round(seq[i-1][0]-t0, 1)}
                return {"t_star": round(seq[i][0]-t0, 1), "jump_m": round(dp, 3),
                        "frame_dt_ms": round(dt_frame*1000, 1),
                        "truth_move_m": round(truth_move, 3) if truth_move is not None else None,
                        "real_motion": real}
        return {"t_star": None, "reason": "无帧跳变(劣化/未发散形态)"}
    rep["t_star_odom"] = find_t_star(odom, "odometry")
    rep["t_star_prop"] = find_t_star(prop, "imu_propagate")

    # ---------- odom vs prop 分叉(优化器窗口解 vs 传播解) ----------
    fork = {"n_pairs": 0}
    if odom and prop:
        diffs = []  # (t, dist(odom, nearest prop))
        for i, o in enumerate(odom):
            dt, j = nearest(ts_prop, o[0])
            if dt < 0.05:  # 对齐窗 50ms
                diffs.append((o[0], dist3(o[1:4], prop[j][1:4])))
        fork["n_pairs"] = len(diffs)
        if diffs:
            t_first_fork = next((d[0] for d in diffs if d[1] > FORK_M), None)
            if t_first_fork is not None:
                fork["t_fork"] = round(t_first_fork - t0, 1)
                fork["fork_max_m"] = round(max(d[1] for d in diffs), 2)
                # t* 前前兆:t_star 前 5s 窗内 diff 是否 > PRECURSOR_M
                ts_ref = rep["t_star_prop"]["t_star"] or rep["t_star_odom"]["t_star"]
                if ts_ref is not None:
                    pre = [d[1] for d in diffs if ts_ref - 5 <= d[0]-t0 < ts_ref]
                    fork["precursor_5s_max_m"] = round(max(pre), 3) if pre else None
            else:
                fork["t_fork"] = None
    rep["fork_odom_prop"] = fork

    # ---------- 早死检测(prop 断流) ----------
    gap = None
    for i in range(1, len(prop)):
        if prop[i][0] - prop[i-1][0] > EARLY_DEATH_GAP:
            gap = {"t_gap": round(prop[i-1][0]-t0, 1), "gap_s": round(prop[i][0]-prop[i-1][0], 1)}
            break
    rep["prop_gap"] = gap

    # ---------- 终态量(形态判据用行程包络,不依赖首跳幅度) ----------
    def bbox_diag(seq):
        if len(seq) < 2:
            return 0.0
        xs = [r[1] for r in seq]; ys = [r[2] for r in seq]; zs = [r[3] for r in seq]
        return math.sqrt((max(xs)-min(xs))**2 + (max(ys)-min(ys))**2 + (max(zs)-min(zs))**2)
    end_state = {"prop_bbox_diag_m": round(bbox_diag(prop), 2),
                 "odom_bbox_diag_m": round(bbox_diag(odom), 2)}
    if prop and truth:  # 末段 3s 均值锚差(prop vs 真值)
        def tail_anchor(seq, tail=3.0):
            t_end = seq[-1][0]
            w = [r for r in seq if r[0] > t_end - tail]
            n = len(w) or 1
            return (sum(r[1] for r in w)/n, sum(r[2] for r in w)/n, sum(r[3] for r in w)/n)
        pa, ta = tail_anchor(prop), tail_anchor(truth)
        end_state["final_drift_prop_truth_m"] = round(dist3(pa, ta), 2)
    rep["end_state"] = end_state

    # ---------- 判决 ----------
    verdict = {"morph": None, "t_star": None, "divergence_type": None, "note": ""}
    tso, tsp = rep["t_star_odom"]["t_star"], rep["t_star_prop"]["t_star"]
    t_star = min([x for x in (tso, tsp) if x is not None], default=None)
    verdict["t_star"] = t_star
    jump_max = max([r.get("jump_m", 0) or 0 for r in (rep["t_star_odom"], rep["t_star_prop"])])
    if gap and (t_star is None or (tso is None and tsp is None)):
        verdict["morph"] = "早死(VINS 停流)"
        verdict["t_star"] = gap["t_gap"]
    elif end_state["prop_bbox_diag_m"] > 10:
        verdict["morph"] = "爆散"
    elif t_star is not None and jump_max > 1.0:
        verdict["morph"] = "跳变(离散大帧跳)"
    elif t_star is not None:
        verdict["morph"] = "小跳/渐进劣化"
    else:
        verdict["morph"] = "无帧跳变(慢劣化或未发散)"
    # 分叉类型
    if tsp is not None and tso is not None:
        if tsp < tso - 1.0:
            verdict["divergence_type"] = "prop先病(传播域:IMU积分/偏置/外参-偏置耦合)"
        elif tso < tsp - 1.0:
            verdict["divergence_type"] = "odom先病(优化器窗口解先毒)"
        else:
            verdict["divergence_type"] = "同时跳变(共同上游:优化器解毒化传播)"
    elif tsp is not None:
        verdict["divergence_type"] = "仅prop跳变(odom已停/未对齐)"
    elif tso is not None:
        verdict["divergence_type"] = "仅odom跳变(传播解尚稳:窗口解单侧毒)"
    fk = rep["fork_odom_prop"]
    if fk.get("t_fork") is not None and t_star is not None:
        if fk["t_fork"] < t_star - 1.0:
            verdict["note"] += f"分叉({fk['t_fork']}s)先于t*({t_star}s)≥1s=优化器先病 "
    if fk.get("precursor_5s_max_m") is not None and fk["precursor_5s_max_m"] > PRECURSOR_M:
        verdict["note"] += f"t*前5s窗odom-prop差已达{fk['precursor_5s_max_m']}m "
    # 事件相关
    evs = []
    for k in ("t_takeoff", "t_takeoff(armed)", "t_poscmd_first"):
        if k in ev:
            evs.append((k, ev[k]))
    evs += [("goal", g) for g in ev.get("t_goals", [])]
    if t_star is not None and evs:
        nearest_ev = min(evs, key=lambda e: abs(e[1] - t_star))
        verdict["nearest_event"] = f"{nearest_ev[0]}@{round(nearest_ev[1],1)}s (Δ={round(t_star-nearest_ev[1],1)}s)"
    rep["verdict"] = verdict
    return rep


def fmt_report(rep):
    L = []
    v = rep["verdict"]
    L.append(f"=== {rep['run']} 法证判决 ===")
    L.append(f"形态: {v['morph']} | t*={v['t_star']}s | 分叉类型: {v.get('divergence_type')}")
    if v.get("nearest_event"):
        L.append(f"最近事件: {v['nearest_event']}")
    if v.get("note"):
        L.append(f"前兆注记: {v['note']}")
    L.append(f"事件轴: {rep['events']}")
    L.append("频率画像: " + " | ".join(f"{k}:{v_['hz_all']}Hz(前半{v_.get('hz_1sthalf')}/后半{v_.get('hz_2ndhalf')})" if 'hz_all' in v_ else f"{k}:{v_}"
                                        for k, v_ in rep["freq"].items()))
    L.append(f"t*_odom: {rep['t_star_odom']}")
    L.append(f"t*_prop: {rep['t_star_prop']}")
    L.append(f"odom-prop 分叉: {rep['fork_odom_prop']}")
    L.append(f"prop 断流: {rep['prop_gap']}")
    L.append(f"终态: {rep['end_state']}")
    im = rep["imu"]
    L.append(f"IMU: n={im.get('n')} dt_p50/p99/max={im.get('dt_p50_ms')}/{im.get('dt_p99_ms')}/{im.get('dt_max_ms')}ms "
             f"acc_peak={im.get('acc_peak')}(饱和帧{im.get('acc_sat_frames')}) gyr_peak={im.get('gyr_peak')}(毛刺帧{im.get('gyr_glitch_frames')})")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--topics", default=None, help="逗号分隔;带图袋必填(只传分析所需话题)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    default_topics = "/vins_estimator/odometry,/vins_estimator/imu_propagate,/mavros/imu/data_raw,/gazebo/model_states,/move_base_simple/goal,/position_cmd,/px4ctrl/takeoff_land,/mavros/state"
    rep = analyze(args.run_dir, args.topics or default_topics)
    out = args.out or os.path.join(args.run_dir, "forensics")
    with open(out + ".json", "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    txt = fmt_report(rep)
    with open(out + ".txt", "w") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
