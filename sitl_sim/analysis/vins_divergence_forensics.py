#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3-D1 VINS 发散袋法证学:逐帧机制重建(任务书 v7.1 D1 协议固化;v7.2-Y1.2 升级)

对每轮 vins_smoke 失败袋产出:
  1. 发散时刻 t* 精确定位(odometry 与 imu_propagate 各自首条 |dp|>0.1m 帧,排除真机动)
  2. odometry(优化器窗口解) vs imu_propagate(传播解) 分叉点——两者分叉=优化器在 t* 前已病
  3. 频率画像(odom/prop/imu 分段实测 Hz,量化优化器频率崩塌)
  4. IMU 原始统计(dt 分布/加速度饱和/陀螺毛刺)
  5. 事件时间轴(takeoff/goal/position_cmd 首发)与 t* 对齐
  6. 判决行:形态 | t* | 距最近事件 | 分叉类型 | 前兆 | IMU 异常

v7.2-Y1.2 升级(2026-09-30):
  A. 溢出安全几何:全部 3D 距离改 math.dist/hypot(内部 hypot 无中间平方,1e160 级坐标
     不再 OverflowError——043355 轮 102m 跳变+数值溢出实证修复);
     非有限帧(nan/inf)丢弃并计数;|坐标|>EXTREME_M(1e6)计 extreme 帧并钳位入几何统计。
  B. 双流检测并入默认输出:各流时戳回退统计(bag ts)+ IMU header 戳回退 + /clock 回退
     (043355 轮 -13s×13726 型污染签名;imreg>1000 即注记"双流污染嫌疑")。
  C. 结构化 forensics.json 字段字典(见下)。

forensics.json 字段字典(机器口径;新增字段只加不删,改动在此登记):
  run                 轮目录名
  events              {t_takeoff|t_takeoff(armed): s, t_goals: [s], t_poscmd_first: s}
  freq                {stream: {n, hz_all, hz_1sthalf, hz_2ndhalf}}  stream=odom/prop/imu/truth
  imu                 {n, dt_p50/p99/max/min_ms, acc_peak, acc_sat_frames,
                      gyr_peak, gyr_glitch_frames, gyr_glitch_times,
                      hdr_regression_n, hdr_regression_worst_s}       (Y1.2B)
  stream_health       {stream: {n, nonfinite_dropped, extreme_frames, mag_peak,
                      stamp_regression_n, stamp_regression_worst_s}}  (Y1.2A/B)
  clock_health        {n, regression_n, regression_worst_s}           (Y1.2B;/clock 专列)
  t_star_odom/t_star_prop  {t_star, jump_m, frame_dt_ms, truth_move_m, real_motion}
                           或 {t_star:None, reason} (断流/无跳变)
  fork_odom_prop      {n_pairs, t_fork, fork_max_m, precursor_5s_max_m}
  frame_jumps_raw_odom      odom 帧间|dp|>0.1 计数(真机动排除+断流首帧排除)(Y1.3)
  frame_jumps_smoothed_odom odom 3 帧滑动均值后 |dp|>0.1 计数(平滑口径,Y1.3)
  prop_gap            {t_gap, gap_s} 或 None (早死)
  end_state           {prop/odom_bbox_diag_m, final_drift_prop_truth_m,
                      truth_z_med, truth_z_max}                    (Y1.3 距离地)
  verdict             {morph, t_star, divergence_type, nearest_event, note,
                      poisoning_suspect}                              (Y1.2B)
  morph 取值: 爆散|跳变(离散大帧跳)|小跳/渐进劣化|无帧跳变(慢劣化或未发散)|早死(VINS 停流)|数值溢出型(含 extreme 帧)

用法: python3 vins_divergence_forensics.py <run_dir> [--topics t1,t2] [--out 前缀]
      带图袋必须用 --topics 过滤(红线#4:禁全量扫)
      --selftest = Y1.2 对账(043355 溢出轮 + 232055 标准爆散轮,输出完整无异常为过)
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
EXTREME_M = 1e6        # |坐标|>此值计 extreme 帧(043355 型数值溢出),几何统计前钳位
REG_SUSPECT_N = 1000   # 时戳回退超此数→双流污染嫌疑注记


def dist3(a, b):
    """溢出安全 3D 距离(math.dist 内部 hypot,无中间平方;输入须有限)。"""
    return math.dist((a[1], a[2], a[3]), (b[1], b[2], b[3]))


def sanitize(seq, health):
    """丢弃非有限帧、计数 extreme 帧并钳位;返回净化序列(元素=(t,x,y,z[,...]))。"""
    out, nonfin, extreme, mag = [], 0, 0, 0.0
    for r in seq:
        vals = r[1:4]
        if not all(math.isfinite(v) for v in vals):
            nonfin += 1
            continue
        m = max(abs(v) for v in vals)
        mag = max(mag, m)
        if m > EXTREME_M:
            extreme += 1
            r = (r[0],) + tuple(max(-EXTREME_M, min(EXTREME_M, v)) for v in vals) + tuple(r[4:])
        out.append(r)
    health["nonfinite_dropped"] = nonfin
    health["extreme_frames"] = extreme
    health["mag_peak"] = round(mag, 1)
    return out


def regression_stats(stamps):
    """时戳回退统计:回退帧数与最劣回退量(秒)。"""
    n, worst, worst_t = 0, 0.0, None
    for i in range(1, len(stamps)):
        d = stamps[i] - stamps[i - 1]
        if d < -1e-6:
            n += 1
            if d < worst:
                worst, worst_t = d, stamps[i]
    return n, round(worst, 3), (round(worst_t, 1) if worst_t is not None else None)


def read_run(run_dir, topic_filter=None):
    import rosbag
    bag_path = os.path.join(run_dir, "flight.bag")
    data = {"odom": [], "prop": [], "imu": [], "truth": [], "goal": [],
            "poscmd": [], "takeoff_land": [], "state": [], "imu_hdr": [], "clock": []}
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
                hs = getattr(msg.header, "stamp", None)
                if hs is not None:
                    data["imu_hdr"].append((hs.to_sec(),))
            elif topic == "/clock":
                data["clock"].append((msg.clock.to_sec(),))
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
                data["state"].append((ts_sec, 1 if msg.armed else 0))
    if t0 is None:
        t0 = 0.0
    return data, t0


def nearest(arr, t):
    i = bisect_left(arr, t)
    cands = []
    if i < len(arr):
        cands.append(i)
    if i > 0:
        cands.append(i - 1)
    best = min(cands, key=lambda j: abs(arr[j] - t))
    return abs(arr[best] - t), best


def seg_hz(stamps):
    if len(stamps) < 2:
        return 0.0
    return (len(stamps) - 1) / (stamps[-1] - stamps[0])


def analyze(run_dir, topic_filter=None):
    data, t0 = read_run(run_dir, topic_filter)
    # ---------- Y1.2A/B:流健康(净化+回退统计) ----------
    stream_health = {}
    pose_streams = {}
    for name in ("odom", "prop", "truth", "goal", "poscmd"):
        h = {"n": len(data[name])}
        seq = sanitize(data[name], h)
        n_reg, worst, worst_t = regression_stats([r[0] for r in seq])
        h.update({"stamp_regression_n": n_reg, "stamp_regression_worst_s": worst,
                  "stamp_regression_at_t": worst_t})
        stream_health[name] = h
        pose_streams[name] = seq
    odom, prop, truth = pose_streams["odom"], pose_streams["prop"], pose_streams["truth"]
    ts_odom = [r[0] for r in odom]
    ts_prop = [r[0] for r in prop]
    ts_truth = [r[0] for r in truth]

    imu = data["imu"]
    imu_hdr = [r[0] for r in data["imu_hdr"]]
    clock = [r[0] for r in data["clock"]]
    hdr_n, hdr_worst, hdr_t = regression_stats(imu_hdr)
    ck_n, ck_worst, ck_t = regression_stats(clock)
    imu_health = {"n": len(imu),
                  "hdr_regression_n": hdr_n, "hdr_regression_worst_s": hdr_worst,
                  "hdr_regression_at_t": hdr_t}
    clock_health = {"n": len(clock), "regression_n": ck_n,
                    "regression_worst_s": ck_worst, "regression_at_t": ck_t}

    rep = {"run": os.path.basename(run_dir.rstrip("/")),
           "stream_health": stream_health, "clock_health": clock_health}

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

    # ---------- 频率画像 ----------
    freq = {}
    for name, seq in (("odom", odom), ("prop", prop), ("imu", imu), ("truth", truth)):
        if not seq:
            freq[name] = {"n": 0}
            continue
        n = len(seq)
        h1 = seg_hz([r[0] for r in seq[:n // 2]])
        h2 = seg_hz([r[0] for r in seq[n // 2:]])
        freq[name] = {"n": n, "hz_all": round(seg_hz([r[0] for r in seq]), 1),
                      "hz_1sthalf": round(h1, 1), "hz_2ndhalf": round(h2, 1)}
    rep["freq"] = freq

    # ---------- IMU 原始统计 ----------
    imu_stat = dict(imu_health)
    if len(imu) > 2:
        dts = sorted(imu[i + 1][0] - imu[i][0] for i in range(len(imu) - 1))
        acc_peak = max(r[1] for r in imu)
        gyr_peak = max(r[2] for r in imu)
        acc_sat_n = sum(1 for r in imu if r[1] > ACC_SAT)
        glitch_idx = [i for i in range(1, len(imu) - 1)
                      if imu[i][2] > GYR_GLITCH and imu[i - 1][2] < 2 and imu[i + 1][2] < 2]
        imu_stat.update({
            "dt_p50_ms": round(dts[len(dts) // 2] * 1000, 2),
            "dt_p99_ms": round(dts[int(len(dts) * 0.99)] * 1000, 2),
            "dt_max_ms": round(dts[-1] * 1000, 2),
            "dt_min_ms": round(dts[0] * 1000, 3),
            "acc_peak": round(acc_peak, 1), "acc_sat_frames": acc_sat_n,
            "gyr_peak": round(gyr_peak, 2), "gyr_glitch_frames": len(glitch_idx),
            "gyr_glitch_times": [round(imu[i][0] - t0, 1) for i in glitch_idx[:5]],
        })
    rep["imu"] = imu_stat

    # ---------- t* 定位 ----------
    def find_t_star(seq, seq_name):
        for i in range(1, len(seq)):
            dp = dist3(seq[i], seq[i - 1])
            if dp > JUMP_M:
                dt_frame = seq[i][0] - seq[i - 1][0]
                truth_move = None
                if truth:
                    _, j0 = nearest(ts_truth, seq[i - 1][0])
                    _, j1 = nearest(ts_truth, seq[i][0])
                    truth_move = dist3(truth[j1], truth[j0])
                real = (truth_move is not None and truth_move > JUMP_M)
                if dt_frame > EARLY_DEATH_GAP:
                    return {"t_star": None, "reason": f"{seq_name} 断流 {dt_frame:.1f}s 后首帧",
                            "t_gap_start": round(seq[i - 1][0] - t0, 1)}
                return {"t_star": round(seq[i][0] - t0, 1), "jump_m": round(dp, 3),
                        "frame_dt_ms": round(dt_frame * 1000, 1),
                        "truth_move_m": round(truth_move, 3) if truth_move is not None else None,
                        "real_motion": real}
        return {"t_star": None, "reason": "无帧跳变(劣化/未发散形态)"}
    rep["t_star_odom"] = find_t_star(odom, "odometry")
    rep["t_star_prop"] = find_t_star(prop, "imu_propagate")

    # ---------- Y1.3 增:帧跳变计数(raw 真机动排除 / smoothed 3 帧滑动均值口径) ----------
    def count_jumps_raw(seq):
        n = 0
        for i in range(1, len(seq)):
            if seq[i][0] - seq[i - 1][0] > EARLY_DEATH_GAP:
                continue  # 断流后首帧不算帧跳变
            if dist3(seq[i], seq[i - 1]) > JUMP_M:
                truth_move = None
                if truth:
                    _, j0 = nearest(ts_truth, seq[i - 1][0])
                    _, j1 = nearest(ts_truth, seq[i][0])
                    truth_move = dist3(truth[j1], truth[j0])
                if truth_move is not None and truth_move > JUMP_M:
                    continue  # 真机动
                n += 1
        return n
    sm = []
    for i in range(len(odom)):
        lo, hi = max(0, i - 1), min(len(odom), i + 2)
        sm.append(tuple(sum(odom[j][k] for j in range(lo, hi)) / (hi - lo) for k in (1, 2, 3)))
    sm_j = sum(1 for i in range(1, len(sm))
               if math.dist(sm[i], sm[i - 1]) > JUMP_M and odom[i][0] - odom[i - 1][0] <= EARLY_DEATH_GAP)
    rep["frame_jumps_raw_odom"] = count_jumps_raw(odom)
    rep["frame_jumps_smoothed_odom"] = sm_j

    # ---------- odom vs prop 分叉 ----------
    fork = {"n_pairs": 0}
    if odom and prop:
        diffs = []
        for i, o in enumerate(odom):
            dt, j = nearest(ts_prop, o[0])
            if dt < 0.05:
                diffs.append((o[0], dist3(o, prop[j])))
        fork["n_pairs"] = len(diffs)
        if diffs:
            t_first_fork = next((d[0] for d in diffs if d[1] > FORK_M), None)
            if t_first_fork is not None:
                fork["t_fork"] = round(t_first_fork - t0, 1)
                fork["fork_max_m"] = round(max(d[1] for d in diffs), 2)
                ts_ref = rep["t_star_prop"]["t_star"] or rep["t_star_odom"]["t_star"]
                if ts_ref is not None:
                    pre = [d[1] for d in diffs if ts_ref - 5 <= d[0] - t0 < ts_ref]
                    fork["precursor_5s_max_m"] = round(max(pre), 3) if pre else None
            else:
                fork["t_fork"] = None
    rep["fork_odom_prop"] = fork

    # ---------- 早死检测 ----------
    gap = None
    for i in range(1, len(prop)):
        if prop[i][0] - prop[i - 1][0] > EARLY_DEATH_GAP:
            gap = {"t_gap": round(prop[i - 1][0] - t0, 1),
                   "gap_s": round(prop[i][0] - prop[i - 1][0], 1)}
            break
    rep["prop_gap"] = gap

    # ---------- 终态量 ----------
    def bbox_diag(seq):
        if len(seq) < 2:
            return 0.0
        xs = [r[1] for r in seq]; ys = [r[2] for r in seq]; zs = [r[3] for r in seq]
        return math.hypot(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    end_state = {"prop_bbox_diag_m": round(bbox_diag(prop), 2),
                 "odom_bbox_diag_m": round(bbox_diag(odom), 2)}
    if truth:
        zs = sorted(r[3] for r in truth)
        end_state["truth_z_med"] = round(zs[len(zs) // 2], 2)
        end_state["truth_z_max"] = round(zs[-1], 2)
    if prop and truth:
        def tail_anchor(seq, tail=3.0):
            t_end = seq[-1][0]
            w = [r for r in seq if r[0] > t_end - tail]
            n = len(w) or 1
            return (sum(r[1] for r in w) / n, sum(r[2] for r in w) / n, sum(r[3] for r in w) / n)
        pa, ta = tail_anchor(prop), tail_anchor(truth)
        end_state["final_drift_prop_truth_m"] = round(math.dist(pa, ta), 2)
    rep["end_state"] = end_state

    # ---------- 判决 ----------
    verdict = {"morph": None, "t_star": None, "divergence_type": None, "note": "",
               "poisoning_suspect": None}
    tso, tsp = rep["t_star_odom"]["t_star"], rep["t_star_prop"]["t_star"]
    t_star = min([x for x in (tso, tsp) if x is not None], default=None)
    verdict["t_star"] = t_star
    jump_max = max([r.get("jump_m", 0) or 0 for r in (rep["t_star_odom"], rep["t_star_prop"])])
    extreme_total = sum(h.get("extreme_frames", 0) + h.get("nonfinite_dropped", 0)
                        for h in stream_health.values())
    poison_n = max(hdr_n, ck_n)
    if poison_n > REG_SUSPECT_N:
        verdict["poisoning_suspect"] = (f"双流污染嫌疑:IMU hdr 回退 {hdr_n} 帧/"
                                        f"/clock 回退 {ck_n} 帧(最劣 {min(hdr_worst, ck_worst)}s)")
    if extreme_total > 0:
        verdict["morph"] = "数值溢出型(含 extreme/非有限帧)"
    elif gap and (t_star is None or (tso is None and tsp is None)):
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
    evs = []
    for k in ("t_takeoff", "t_takeoff(armed)", "t_poscmd_first"):
        if k in ev:
            evs.append((k, ev[k]))
    evs += [("goal", g) for g in ev.get("t_goals", [])]
    if t_star is not None and evs:
        nearest_ev = min(evs, key=lambda e: abs(e[1] - t_star))
        verdict["nearest_event"] = f"{nearest_ev[0]}@{round(nearest_ev[1], 1)}s (Δ={round(t_star - nearest_ev[1], 1)}s)"
    rep["verdict"] = verdict
    return rep


def fmt_report(rep):
    L = []
    v = rep["verdict"]
    L.append(f"=== {rep['run']} 法证判决 ===")
    L.append(f"形态: {v['morph']} | t*={v['t_star']}s | 分叉类型: {v.get('divergence_type')}")
    if v.get("nearest_event"):
        L.append(f"最近事件: {v['nearest_event']}")
    if v.get("poisoning_suspect"):
        L.append(f"污染嫌疑: {v['poisoning_suspect']}")
    if v.get("note"):
        L.append(f"前兆注记: {v['note']}")
    L.append(f"事件轴: {rep['events']}")
    L.append("频率画像: " + " | ".join(f"{k}:{v_['hz_all']}Hz(前半{v_.get('hz_1sthalf')}/后半{v_.get('hz_2ndhalf')})" if 'hz_all' in v_ else f"{k}:{v_}"
                                        for k, v_ in rep["freq"].items()))
    sh = rep["stream_health"]
    L.append("流健康: " + " | ".join(
        f"{k}:n{h_['n']} 非有限{h_['nonfinite_dropped']} 极值{h_['extreme_frames']} "
        f"回退{h_['stamp_regression_n']}(最劣{h_['stamp_regression_worst_s']}s)" for k, h_ in sh.items()))
    ch = rep["clock_health"]
    L.append(f"/clock: n={ch['n']} 回退{ch['regression_n']}(最劣{ch['regression_worst_s']}s)")
    L.append(f"t*_odom: {rep['t_star_odom']}")
    L.append(f"t*_prop: {rep['t_star_prop']}")
    L.append(f"odom-prop 分叉: {rep['fork_odom_prop']}")
    L.append(f"prop 断流: {rep['prop_gap']}")
    L.append(f"终态: {rep['end_state']}")
    im = rep["imu"]
    L.append(f"IMU: n={im.get('n')} dt_p50/p99/max={im.get('dt_p50_ms')}/{im.get('dt_p99_ms')}/{im.get('dt_max_ms')}ms "
             f"acc_peak={im.get('acc_peak')}(饱和帧{im.get('acc_sat_frames')}) gyr_peak={im.get('gyr_peak')}(毛刺帧{im.get('gyr_glitch_frames')}) "
             f"hdr回退={im.get('hdr_regression_n')}(最劣{im.get('hdr_regression_worst_s')}s)")
    return "\n".join(L)


DEFAULT_TOPICS = ("/vins_estimator/odometry,/vins_estimator/imu_propagate,"
                  "/mavros/imu/data_raw,/gazebo/model_states,/move_base_simple/goal,"
                  "/position_cmd,/px4ctrl/takeoff_land,/mavros/state,/clock")


def run_selftest():
    """Y1.2 对账:043355(溢出轮)+ 232055(标准爆散轮),输出完整无异常为过。"""
    base = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
    cases = [("run_X1final_043355", "数值溢出/双流污染"),
             ("run_X1_232055", "标准爆散")]
    ok_all = True
    for name, _kind in cases:
        rd = os.path.join(base, name)
        try:
            rep = analyze(rd, DEFAULT_TOPICS)
            out = os.path.join(rd, "forensics_v2")
            with open(out + ".json", "w") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
            with open(out + ".txt", "w") as f:
                f.write(fmt_report(rep) + "\n")
            checks = {
                "no_exception": True,
                "verdict_present": rep["verdict"]["morph"] is not None,
                "stream_health_complete": all(
                    k in rep["stream_health"] for k in ("odom", "prop", "truth")),
                "regression_fields": "hdr_regression_n" in rep["imu"],
            }
            if name.endswith("043355"):
                checks["poisoning_flagged"] = rep["verdict"].get("poisoning_suspect") is not None
                checks["overflow_morph_or_extreme"] = (
                    "溢出" in rep["verdict"]["morph"]
                    or sum(h.get("extreme_frames", 0) + h.get("nonfinite_dropped", 0)
                           for h in rep["stream_health"].values()) > 0)
            if name.endswith("232055"):
                checks["morph_diverged"] = rep["verdict"]["morph"] in (
                    "爆散", "跳变(离散大帧跳)", "小跳/渐进劣化", "数值溢出型(含 extreme/非有限帧)")
                checks["t_star_found"] = rep["verdict"]["t_star"] is not None
            bad = [k for k, v in checks.items() if not v]
            stat = "PASS" if not bad else f"FAIL {bad}"
            print(f"[selftest] {name}: {stat} morph={rep['verdict']['morph']} "
                  f"t*={rep['verdict']['t_star']} hdr_reg={rep['imu'].get('hdr_regression_n')} "
                  f"ck_reg={rep['clock_health'].get('regression_n')}")
            ok_all = ok_all and not bad
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[selftest] {name}: FAIL exception={e!r}")
            ok_all = False
    print(f"[selftest] 总判决: {'PASS' if ok_all else 'FAIL'}")
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("--topics", default=None, help="逗号分隔;带图袋必填(只传分析所需话题)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(run_selftest())
    if not args.run_dir:
        ap.error("需要 run_dir 或 --selftest")
    rep = analyze(args.run_dir, args.topics or DEFAULT_TOPICS)
    out = args.out or os.path.join(args.run_dir, "forensics_v2")
    with open(out + ".json", "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    txt = fmt_report(rep)
    with open(out + ".txt", "w") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
