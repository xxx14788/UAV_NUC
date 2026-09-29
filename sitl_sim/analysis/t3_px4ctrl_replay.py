#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z1.1 X 轮 px4ctrl 消费面逐帧重建(C01-E3 执行版;T3 v7.2 Z1.1)

对每轮 X 族袋重建 毒 odom → px4ctrl 中间量 → 真值输出 三段对账:
  输入段  /vins_estimator/imu_propagate(p/v/q;px4ctrl SITL 直供流,run_ctrl_sitl_vins.launch:17)
          t*(首条 |dp|>0.5m 且真值同窗不动) + 毒窗内 dp_max/|v|max/odom-yaw-vs-GT 误差(P-7 判别子)
  门段    px4ctrl.log "[px4ctrl] odom sanity gate REJECTED" 行计数+首拒时刻(门代差:X1 早轮无门)
  中间段  /debugPx4ctrl:des_a 水平幅值/des_q 倾角/des_thr(负油门直测)/des_v;
          /mavros/setpoint_raw/attitude 倾角交叉核
  输出段  /gazebo/model_states:GT 位移(t*→+3s/+10s)/GT 最大偏离/armed 降落时刻
  放大量  Δp→指令倾角(理论 atan(1.5·Δp/g),Kp=1.5=C07-E1-⑥ 实读)→GT 位移;
          传递比 |GT|/Δp 仅登记(K3 警告:爆散袋 sane 跟踪缺席,传递比≠H2 判据)
  分型    跳变型(GT 偏离<10m 且 20s 内 disarm/降级)vs 持续型(W2 族:持续方向性失控)vs 无发散

用法: t3_px4ctrl_replay.py <run_dir> [<run_dir2> ...] | --selftest
输出: <run_dir>/px4ctrl_replay.json + 汇总 md 行(stdout);--all 扫 vins_smoke_runs 全 X 族
"""
import argparse
import json
import math
import os
import re
import sys

G = 9.81
KP = 1.5                 # C07-E1-⑥ 实读(SITL=fpv=1.5,C10 悬案关账)
JUMP_POISON = 0.5        # 毒输入判据(m,任务书 K4 口径:现行 jump0.6 拦不住 0.5m 干净阶跃)
WIN_PRE, WIN_POST = 5.0, 15.0
TOPICS = ["/vins_estimator/imu_propagate", "/debugPx4ctrl",
          "/mavros/setpoint_raw/attitude", "/gazebo/model_states",
          "/mavros/state", "/px4ctrl/takeoff_land", "/vins_estimator/odometry"]


def yaw_of(qx, qy, qz, qw):
    return math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))


def tilt_of(qx, qy, qz, qw):
    """机体 z 轴与世界 z 夹角(度)。R22=1-2(x²+y²)。"""
    r22 = 1 - 2 * (qx * qx + qy * qy)
    return math.degrees(math.acos(max(-1.0, min(1.0, r22))))


def wrap180(a):
    while a > 180:
        a -= 360
    while a < -180:
        a += 360
    return a


def read_streams(bag_path):
    import rosbag
    prop, dbg, sp, truth, state, tols, odom = [], [], [], [], [], [], []
    with rosbag.Bag(bag_path, "r") as b:
        for topic, msg, ts in b.read_messages(topics=TOPICS):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            if topic == "/vins_estimator/imu_propagate":
                p = msg.pose.pose.position
                q = msg.pose.pose.orientation
                v = msg.twist.twist.linear
                prop.append((t, p.x, p.y, p.z, q.x, q.y, q.z, q.w,
                             math.hypot(v.x, v.y, v.z)))
            elif topic == "/debugPx4ctrl":
                dbg.append((t, math.hypot(msg.des_a_x, msg.des_a_y),
                            tilt_of(msg.des_q_x, msg.des_q_y, msg.des_q_z, msg.des_q_w),
                            msg.des_thr,
                            math.hypot(msg.des_v_x, msg.des_v_y, msg.des_v_z)))
            elif topic == "/mavros/setpoint_raw/attitude":
                q = msg.orientation
                sp.append((t, tilt_of(q.x, q.y, q.z, q.w), msg.thrust))
            elif topic == "/gazebo/model_states":
                for name, pose in zip(msg.name, msg.pose):
                    if "iris" in name:
                        p, q = pose.position, pose.orientation
                        truth.append((t, p.x, p.y, p.z,
                                      math.degrees(yaw_of(q.x, q.y, q.z, q.w))))
                        break
            elif topic == "/mavros/state":
                state.append((t, 1 if msg.armed else 0))
            elif topic == "/px4ctrl/takeoff_land":
                tols.append((t, msg.takeoff_land_cmd))
            elif topic == "/vins_estimator/odometry":
                p = msg.pose.pose.position
                odom.append((t, p.x, p.y, p.z))
    return dict(prop=prop, dbg=dbg, sp=sp, truth=truth, state=state,
                tols=tols, odom=odom)


def nearest(arr, t):
    from bisect import bisect_left
    i = bisect_left(arr, t)
    c = [j for j in (i - 1, i) if 0 <= j < len(arr)]
    j = min(c, key=lambda k: abs(arr[k] - t))
    return j


def parse_gate_log(run_dir):
    """px4ctrl.log REJECTED 行:门代证据。"""
    p = os.path.join(run_dir, "px4ctrl.log")
    n, first_t = 0, None
    if not os.path.exists(p):
        return {"rejected": None, "note": "无 px4ctrl.log"}
    pat = re.compile(r"odom sanity gate REJECTED.*total_rejected=(\d+)")
    stamp = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
    for line in open(p, errors="replace"):
        m = pat.search(line)
        if m:
            n = max(n, int(m.group(1)))
            if first_t is None:
                s = stamp.search(line)
                first_t = s.group(1) if s else "?"
    if n == 0:
        return {"rejected": 0, "note": "零拒绝(门关代或无毒帧)"}
    return {"rejected": n, "first_reject_wall": first_t}


def analyze(run_dir):
    bag = os.path.join(run_dir, "flight.bag")
    S = read_streams(bag)
    prop, truth, dbg, sp = S["prop"], S["truth"], S["dbg"], S["sp"]
    rep = {"run": os.path.basename(run_dir.rstrip("/")),
           "n_prop": len(prop), "n_dbg": len(dbg), "n_truth": len(truth)}
    rep["gate"] = parse_gate_log(run_dir)
    if len(prop) < 10 or not truth:
        rep["error"] = "流不足(prop/truth)"
        return rep
    t0 = prop[0][0]
    ts_p = [r[0] for r in prop]
    ts_t = [r[0] for r in truth]

    # ---- t*:首条毒跳(|dp|>JUMP_POISON 且真值同窗不动) ----
    t_star, dp_star = None, None
    for i in range(1, len(prop)):
        dp = math.dist(prop[i][1:4], prop[i - 1][1:4])
        if dp > JUMP_POISON:
            j0, j1 = nearest(ts_t, prop[i - 1][0]), nearest(ts_t, prop[i][0])
            gt_move = math.dist(truth[j1][1:4], truth[j0][1:4])
            if gt_move > JUMP_POISON:
                continue  # 真机动
            t_star, dp_star = prop[i][0], dp
            break
    if t_star is None:
        rep["type"] = "无发散(无 >0.5m 毒跳)"
        return rep
    w0, w1 = t_star - WIN_PRE, t_star + WIN_POST
    win = [r for r in prop if w0 <= r[0] <= w1]
    rep["t_star_s"] = round(t_star - t0, 1)
    rep["dp_star_m"] = round(dp_star, 2)

    # ---- 输入段:毒窗画像 ----
    dp_max = max((math.dist(win[i][1:4], win[i - 1][1:4])
                  for i in range(1, len(win))
                  if win[i][0] - win[i - 1][0] < 1.0), default=0.0)
    # 全 run 暴力跳(真值排除;爆散主跳可能在 +15s 窗外)
    dp_run = 0.0
    for i in range(1, len(prop)):
        if prop[i][0] - prop[i - 1][0] >= 1.0:
            continue
        dp = math.dist(prop[i][1:4], prop[i - 1][1:4])
        if dp > dp_run:
            j0, j1 = nearest(ts_t, prop[i - 1][0]), nearest(ts_t, prop[i][0])
            if math.dist(truth[j1][1:4], truth[j0][1:4]) <= JUMP_POISON:
                dp_run = dp
    # 累计漂移(harness"帧跳变=锚差"口径的真身:速度爬坡积分,非帧间跳)
    i_star_prop = min(range(len(prop)), key=lambda k: abs(prop[k][0] - t_star))
    p_star = prop[i_star_prop][1:4]
    prop_runaway = max((math.dist(r[1:4], p_star) for r in prop[i_star_prop:]), default=0.0)

    v_max = max(r[8] for r in win)
    # 优化器 odom 流暴力跳交叉指标(帧间口径;台账锚差 890m 属累计漂移非此值)
    odom_run = 0.0
    for i in range(1, len(S["odom"])):
        if S["odom"][i][0] - S["odom"][i - 1][0] < 1.0:
            odom_run = max(odom_run, math.dist(S["odom"][i][1:4], S["odom"][i - 1][1:4]))
    yaw_err_max, yaw30_t, yaw60_t = 0.0, None, None
    for r in win:
        j = nearest(ts_t, r[0])
        if abs(ts_t[j] - r[0]) < 0.1:
            e = abs(wrap180(math.degrees(yaw_of(r[4], r[5], r[6], r[7])) - truth[j][4]))
            yaw_err_max = max(yaw_err_max, e)
            if yaw30_t is None and e > 30:
                yaw30_t = round(r[0] - t0, 1)
            if yaw60_t is None and e > 60:
                yaw60_t = round(r[0] - t0, 1)
    rep["input"] = {"dp_max_m": round(dp_max, 2), "dp_run_max_m": round(dp_run, 2),
                    "odom_run_max_m": round(odom_run, 2),
                    "prop_runaway_m": round(prop_runaway, 1),
                    "v_max_ms": round(v_max, 1),
                    "yaw_err_max_deg": round(yaw_err_max, 1),
                    "yaw30_t": yaw30_t, "yaw60_t": yaw60_t}

    # ---- 中间段:指令画像(毒窗内) ----
    dw = [r for r in dbg if w0 <= r[0] <= w1]
    sw = [r for r in sp if w0 <= r[0] <= w1]
    pre_d = [r for r in dbg if t_star - 5 <= r[0] < t_star]
    tilt_base = max((r[2] for r in pre_d), default=0.0)
    mid = {"des_a_xy_max": round(max((r[1] for r in dw), default=0.0), 2),
           "tilt_cmd_max_deg": round(max((r[2] for r in dw), default=0.0), 1),
           "tilt_base_deg": round(tilt_base, 1),
           "des_thr_min": round(min((r[3] for r in dw), default=0.0), 3),
           "des_v_max": round(max((r[4] for r in dw), default=0.0), 2),
           "sp_tilt_max_deg": round(max((r[1] for r in sw), default=0.0), 1),
           "sp_thrust_min": round(min((r[2] for r in sw), default=0.0), 3)}
    # 理论放大量(单步阶跃+跟踪维持假设,C07 §2.4 口径)
    mid["tilt_theory_deg"] = round(math.degrees(math.atan(KP * dp_max / G)), 1)
    mid["tilt_excess_deg"] = round(mid["tilt_cmd_max_deg"] - mid["tilt_theory_deg"], 1)
    rep["middle"] = mid

    # ---- 输出段:GT 响应 ----
    j_star = nearest(ts_t, t_star)
    anchor = truth[j_star][1:4]
    gtw = [r for r in truth if w0 <= r[0] <= t_star + 30]
    dev = [(r[0], math.dist(r[1:4], anchor)) for r in gtw]
    dev3 = max((d for t, d in dev if t <= t_star + 3), default=0.0)
    dev10 = max((d for t, d in dev if t <= t_star + 10), default=0.0)
    dev30 = max((d for t, d in dev), default=0.0)
    disarm_t = None
    armed = [s for s in S["state"] if s[0] >= t_star]
    for i in range(1, len(armed)):
        if armed[i][1] == 0 and armed[i - 1][1] == 1:
            disarm_t = round(armed[i][0] - t0, 1)
            break
    land_cmd = [t for t, c in S["tols"] if c in (2, 4) and t >= t_star]
    rep["output"] = {"gt_dev_3s_m": round(dev3, 2), "gt_dev_10s_m": round(dev10, 2),
                     "gt_dev_30s_m": round(dev30, 2),
                     "transfer_10s": round(dev10 / max(dp_max, 1e-9), 4),
                     "disarm_after_t_star_s": disarm_t,
                     "land_cmd_after_t_star_s": round(land_cmd[0] - t0, 1) if land_cmd else None}

    # ---- 分型 ----
    if dev10 < 10 and (disarm_t is not None or land_cmd or dev30 < 15):
        rep["type"] = "跳变型(有限偏离+降级/降落)"
    elif dev10 >= 10:
        rep["type"] = "持续型(毒窗 10s 内 GT 偏离≥10m)"
    else:
        rep["type"] = "中间型"
    rep["k3_note"] = "传递比≠H2 判据(爆散袋 sane 跟踪缺席,C07-K3)"
    return rep


def md_row(rep):
    if "error" in rep or rep.get("type") == "无发散(无 >0.5m 毒跳)":
        return (f"| {rep['run']} | {rep.get('type', rep.get('error'))} | - | - | "
                f"拒帧={rep.get('gate', {}).get('rejected')} | - | - | - |")
    i, m, o = rep.get("input", {}), rep.get("middle", {}), rep.get("output", {})
    return (f"| {rep['run']} | {rep['type']} | t*={rep['t_star_s']}s Δp={rep['dp_star_m']}m "
            f"v_max={i.get('v_max_ms')}m/s odom跳={i.get('odom_run_max_m')}m "
            f"yaw_err={i.get('yaw_err_max_deg')}°(>60°@{i.get('yaw60_t')}) | "
            f"拒帧={rep['gate'].get('rejected')} | "
            f"tilt {m.get('tilt_base_deg')}→{m.get('tilt_cmd_max_deg')}° "
            f"(理论 {m.get('tilt_theory_deg')}°/超 {m.get('tilt_excess_deg')}°) "
            f"thr_min={m.get('des_thr_min')} | "
            f"GT 3s/10s={o.get('gt_dev_3s_m')}/{o.get('gt_dev_10s_m')}m "
            f"传递={o.get('transfer_10s')} disarm+{o.get('disarm_after_t_star_s')}s |")


def selftest():
    base = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
    # 对账口径:t*=首个 >0.5m 毒跳(爬升起点),量级判据用毒窗 dp_max(非首跳值)
    cases = [("run_X1_232055", {"type_contains": "跳变型", "dp_max_ge": 1.0,
                                "yaw60_expected": True}),
             ("run_X1final_105449", {"v_max_ge": 20.0, "gate_rejected_ge": 1000,
                                     "prop_runaway_ge": 100.0})]
    ok = True
    for name, exp in cases:
        rep = analyze(os.path.join(base, name))
        with open(os.path.join(base, name, "px4ctrl_replay.json"), "w") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        good = "error" not in rep
        if good and "type_contains" in exp:
            good = exp["type_contains"] in rep.get("type", "")
        if good and "dp_max_ge" in exp:
            good = (rep.get("input", {}).get("dp_max_m") or 0) >= exp["dp_max_ge"]
        if good and "dp_run_max_ge" in exp:
            good = (rep.get("input", {}).get("dp_run_max_m") or 0) >= exp["dp_run_max_ge"]
        if good and "odom_run_max_ge" in exp:
            good = (rep.get("input", {}).get("odom_run_max_m") or 0) >= exp["odom_run_max_ge"]
        if good and "prop_runaway_ge" in exp:
            good = (rep.get("input", {}).get("prop_runaway_m") or 0) >= exp["prop_runaway_ge"]
        if good and "v_max_ge" in exp:
            good = (rep.get("input", {}).get("v_max_ms") or 0) >= exp["v_max_ge"]
        if good and "gate_rejected_ge" in exp:
            good = (rep.get("gate", {}).get("rejected") or 0) >= exp["gate_rejected_ge"]
        if good and exp.get("yaw60_expected"):
            good = rep.get("input", {}).get("yaw60_t") is not None
        print(f"[selftest] {name}: {'PASS' if good else 'FAIL'} {md_row(rep)}")
        ok = ok and good
    print(f"[selftest] 总判决: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*")
    ap.add_argument("--all-x", action="store_true", help="扫 vins_smoke_runs 全 X 族")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    base = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
    dirs = args.dirs
    if args.all_x:
        dirs = [os.path.join(base, d) for d in sorted(os.listdir(base))
                if d.startswith("run_X1") and os.path.exists(os.path.join(base, d, "flight.bag"))]
    rows = []
    for d in dirs:
        try:
            rep = analyze(d)
        except Exception as e:
            rep = {"run": os.path.basename(d.rstrip("/")), "error": f"analyze 异常: {e!r}"}
        out = os.path.join(d, "px4ctrl_replay.json")
        if "error" not in rep:
            with open(out, "w") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
        rows.append(rep)
        print(md_row(rep), flush=True)
    print(f"\n共 {len(rows)} 轮;跳变型 "
          f"{sum(1 for r in rows if '跳变型' in r.get('type', ''))} / "
          f"持续型 {sum(1 for r in rows if '持续型' in r.get('type', ''))} / "
          f"无发散 {sum(1 for r in rows if '无发散' in r.get('type', '') or 'error' in r)}")


if __name__ == "__main__":
    main()
