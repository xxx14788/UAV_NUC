#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Y1.1 W-A 解锁门机械化判据器(T3 v7.2;自测对账强制)

对 t3_replay.sh 输出目录按 W-A 统一判据(T2 v4.3 §第一部分)一键判决:
  ⓪ 存活:odom 覆盖率(odom 流跨度/袋总时长)≥ coverage_min;vins_alive 仅作旁证
     (R_CAN 早死=进程活着但输出停流,故不能用 alive 单判)
  ① Bas:|Bas| 超限帧占比 / 最长持续超限段 / 末段(tail)中位 三重口径
     —— 不用朴素 max<1.0:CTRL2(判 PASS 的对照)有 2 帧恢复型瞬态 1.402,
        而 R_CAN 死亡时 Bas=2.53 仍在爬升;占比+持续段+终态才是"全程<1.0"的
        机制忠实录(2026-09-30 校准,R_CAN/CTRL2 实测分离,见 THRESH 默认表注释)
  ② ATE:ate_post60_m ≤ baseline_ate_m ×(1+margin_pct/100)(0.144×1.1=0.1584)
  ③ 尖峰:phase=1 init_cost 对滚动中位(窗口 rollmed_win)的倍率;
        spike=倍率>spike_ratio_mult(=10,T2 v4.1 已定口径"init_cost>10×med");
        判 spike_rate ≤ rate_max 且 max_ratio ≤ max_ratio_max;
        绝对值 >1e3 计数/最大值仅报告不入判——CTRL2 滑窗中位 2116,绝对口径
        会把已知好对照打死(2026-09-30 实测;T2 书"无>1e3尖峰"的意图是
        "78→7068→16871 循环"型相对尖峰,机制口径=相对倍率)
  周期性:log10(cost) 均匀重采样后自相关,AC>ac_thresh 报主周期(供 W-A2 对账)

用法:
  t3_wa_gate.py <replay_dir> [<dir2> ...] [--src-bag BAG] [--recompute-eval]
                [--thresholds t3_wa_gate_thresholds.json] [--csv out.csv]
  t3_wa_gate.py --selftest          # R_CAN=FAIL + CTRL2=PASS 对账(强制,改工具必须重跑)
  t3_wa_gate.py --online <run_dir> [<run_dir2> ...] [--csv out.csv]
                [--skip-forensics]  # 在线轴:吃 vins_smoke_runs/run_* 目录(v7.4 等待池①,C-6)
  t3_wa_gate.py --online --selftest # WAOL5R(健康,T1-D1 域跳变) + X1_232055(爆散) 对账
输出: <dir>/wa_gate.json(回放) / <dir>/wa_gate_online.json(在线) + stdout 一行判决;
      --csv 追加一行汇总(矩阵批用)
在线判决模式(总设计师 10-01 口径:在线为主判)两层:
  xline  gate 层 = 四指标(round_result.sh RESULT.txt,不重算保判读一致)
          + J0 锚差(<0.5m) + J0 修订口径(forensics frame_jumps raw==0 且 smj≤10)
          + ENV-FAIL 三签名; j0_jump>0.5 且 vins 域健康 → 标 T1-D1-domain(不计 5/5,入回挖)
  vins  域层  = 零 failure 零 reboot(T2diag t 回退计数 + odom 断流>gap 阈计数)
          + Bas 三重口径(同回放) + ATE 出生点对齐(仅报告) + 尖峰(同回放)
          —— T2 U3 达标门("六轮零 failure 零 reboot")的机器口径即 vins 层 pass
阈值外置: 默认写 <script_dir>/t3_wa_gate_thresholds.json(不存在则生成),可改值重跑;
          供 T2/仲裁覆盖。任何阈值改动必须重跑 --selftest(--online 改动跑 --online --selftest)并记录两侧数字。
"""
import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
from bisect import bisect_left

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- 默认阈值表(2026-09-30 以 R_CAN=FAIL / CTRL2=PASS 双侧校准;改动须重跑 selftest)----
DEFAULT_THRESH = {
    "coverage_min": 0.80,          # R_CAN ~0.11 / CTRL2 ~0.96
    "bas_hard": 1.0,               # W-A 书面判据的 1.0 线(超限定义)
    "bas_over_ratio_max": 0.01,    # R_CAN 2.8% / CTRL2 0.12%
    "bas_tail_med_max": 1.0,       # R_CAN 0.361(死亡截断,靠占比判)/ CTRL2 0.110
    "bas_run_frames_max": 3,       # R_CAN 1 / CTRL2 2(恢复型瞬态容许)
    "baseline_ate_m": 0.144,       # 883c75c:CTRL2 ATE
    "ate_margin_pct": 10,          # T2 v4.3:不劣于基线超 10%
    "rollmed_win": 21,             # 滚动中位窗口(slv 帧)
    "spike_ratio_mult": 10.0,      # spike 定义:cost > 10×滚动中位
    "spike_rate_max": 0.01,        # R_CAN 5.6% / CTRL2 0.46%
    "spike_max_ratio": 50.0,       # R_CAN 215× / CTRL2 34.6×
    "spike_abs_report": 1000.0,    # 报告用绝对线(不入判)
    "ac_thresh": 0.30,             # 自相关主周期显著线
    "ac_min_lag_s": 2.0,           # 排除 lag<2s 的相邻平滑平凡解
    "tail_s": 10.0,                # Bas 末段窗口
    # ---- 在线轴增补(v7.4 等待池①;不动上方回放键) ----
    "online_reboot_fall_s": 30.0,  # T2diag t 单调性:相邻差<-此值计一次 reboot(VINS 重启 t 回零)
    "online_odom_gap_s": 3.0,      # odom 相邻时戳差>此值计断流段(对齐 forensics EARLY_DEATH_GAP)
    "online_pair_win_s": 0.2,      # ATE 最近邻配对窗
    "online_j0_rev_raw_max": 0,    # J0 修订: frame_jumps_raw_odom == 0(X1' 验收口径)
    "online_j0_rev_smj_max": 10,   # J0 修订: frame_jumps_smoothed_odom ≤ 10
}

RE_DIAG = re.compile(
    r"T2diag.*?\st=(-?[\d.]+).*?\|Bas\|=([\d.eE+-]+).*?\|Bgs\|=([\d.eE+-]+)"
    r".*?tic0=\[([^\]]+)\].*?track=(\d+)")
RE_SLV1 = re.compile(r"T2slv.*?\st=(-?[\d.]+) phase=1 init_cost=([\d.eE+-]+)")
RE_SLV0 = re.compile(r"T2slv.*?\st=(-?[\d.]+) phase=0 init_cost=([\d.eE+-]+)")
RE_DUR = re.compile(r"Duration:\s*[\d.]+\s*/\s*([\d.]+)")


def parse_vins_log(path):
    diag, slv1, slv0 = [], [], []
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = RE_DIAG.search(line)
            if m:
                diag.append((float(m.group(1)), float(m.group(2)), float(m.group(3)),
                             int(m.group(5))))
                continue
            m = RE_SLV1.search(line)
            if m:
                slv1.append((float(m.group(1)), float(m.group(2))))
                continue
            m = RE_SLV0.search(line)
            if m:
                slv0.append((float(m.group(1)), float(m.group(2))))
    return diag, slv1, slv0


def bag_total_from_playlog(path):
    """play.log 的进度行含 'Duration: x / TOTAL';取最大 TOTAL 为袋时长。"""
    best = None
    try:
        with open(path, "r", errors="replace") as f:
            for line in f:
                for m in RE_DUR.finditer(line):
                    v = float(m.group(1))
                    if best is None or v > best:
                        best = v
    except OSError:
        pass
    return best


def odom_span_from_outbag(path):
    """vins_out.bag 只录 odom/prop/feature(小袋),全读安全。返回 (n,span)。"""
    try:
        import rosbag
    except ImportError:
        return None, None
    first = last = None
    n = 0
    try:
        with rosbag.Bag(path, "r") as b:
            for topic, msg, ts in b.read_messages(topics=["/vins_estimator/odometry"]):
                t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
                if first is None:
                    first = t
                last = t
                n += 1
    except Exception:
        return None, None
    return (n, last - first) if first is not None else (0, None)


def get_eval(replay_dir, src_bag, recompute):
    """eval.json 优先;--recompute 或缺失且有 src-bag 时调 t3_replay_eval.py 重算。"""
    ej = os.path.join(replay_dir, "eval.json")
    if recompute and src_bag:
        subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "t3_replay_eval.py"),
                        replay_dir, src_bag], check=False)
    if os.path.exists(ej):
        try:
            with open(ej, "r", errors="replace") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def rolling_median_ratios(ser, win):
    ratios = []
    half = win // 2
    for i in range(len(ser)):
        lo = max(0, i - half)
        hi = min(len(ser), lo + win)
        med = statistics.median(ser[lo:hi])
        ratios.append(ser[i] / max(med, 1e-9))
    return ratios


def dominant_period(times, costs, ac_thresh, min_lag_s=2.0):
    """log10(cost) 均匀重采样→自相关;lag<min_lag_s 排除(相邻平滑性平凡解),
    显著则返回 (主周期s, AC峰值)。另算尖峰间隔中位(调用方给 spike times)。"""
    if len(costs) < 30:
        return None, None
    dt_med = statistics.median([times[i + 1] - times[i] for i in range(len(times) - 1)])
    if dt_med <= 0:
        return None, None
    y = [math.log10(max(c, 1e-9)) for c in costs]
    t0, t1 = times[0], times[-1]
    n = max(30, int((t1 - t0) / dt_med))
    if n > 20000 or n < 30:
        return None, None
    # 均匀网格线性插值
    grid = [t0 + (t1 - t0) * i / (n - 1) for i in range(n)]
    res = []
    j = 0
    for g in grid:
        while j < len(times) - 2 and times[j + 1] < g:
            j += 1
        if times[j + 1] == times[j]:
            res.append(y[j])
        else:
            w = (g - times[j]) / (times[j + 1] - times[j])
            res.append(y[j] * (1 - w) + y[j + 1] * w)
    m = statistics.mean(res)
    res = [v - m for v in res]
    var = sum(v * v for v in res) / len(res)
    if var <= 0:
        return None, None
    step = (t1 - t0) / (n - 1)
    lag_lo = max(1, int(min_lag_s / step))
    best_lag, best_ac = None, 0.0
    max_lag = min(len(res) // 3, 3000)
    for lag in range(lag_lo, max_lag):
        s = sum(res[i] * res[i + lag] for i in range(len(res) - lag))
        ac = s / ((len(res) - lag) * var)
        if ac > best_ac:
            best_ac, best_lag = ac, lag
    if best_ac > ac_thresh and best_lag:
        return round(best_lag * step, 2), round(best_ac, 3)
    return None, None


def judge_dir(replay_dir, src_bag, recompute, th):
    rep = {"dir": os.path.basename(replay_dir.rstrip("/")), "thresholds": dict(th)}
    vins_log = os.path.join(replay_dir, "vins.log")
    if not os.path.exists(vins_log):
        rep["verdict"] = "ERROR"
        rep["reason"] = "vins.log 不存在"
        return rep
    diag, slv1, slv0 = parse_vins_log(vins_log)
    ev = get_eval(replay_dir, src_bag, recompute)
    rep["eval"] = {k: ev.get(k) for k in
                   ("n_odom", "t_star_s", "frame_jumps", "frame_jumps_smoothed",
                    "stamp_back_jumps", "ate_post60_m", "ate_n_pairs", "feat_survival")}
    crit = {}

    # ---------- ⓪ 存活 ----------
    n_odom, span = odom_span_from_outbag(os.path.join(replay_dir, "vins_out.bag"))
    bag_total = bag_total_from_playlog(os.path.join(replay_dir, "play.log"))
    try:
        with open(os.path.join(replay_dir, "vins_alive.txt")) as f:
            alive = int(f.read().strip())
    except Exception:
        alive = None
    cov = (span / bag_total) if (span and bag_total) else None
    crit["survival"] = {
        "odom_n": n_odom, "odom_span_s": round(span, 1) if span else None,
        "bag_total_s": bag_total, "coverage": round(cov, 3) if cov is not None else None,
        "vins_alive": alive, "diag_n": len(diag),
        "pass": bool(cov is not None and cov >= th["coverage_min"]),
    }
    if cov is None:
        crit["survival"]["note"] = "覆盖率不可算(缺 play.log 时长或 odom 流);以 Bas/尖峰判据为准"

    # ---------- ① Bas/Bgs ----------
    bas = [b for _, b, _, _ in diag]
    bgs = [g for _, _, g, _ in diag]
    track = [tk for _, _, _, tk in diag]
    bas_stat = {"n": len(bas), "peak": round(max(bas), 4) if bas else None,
                "tail_med": None, "over_ratio": None, "longest_run_frames": 0,
                "peak_t": None, "bgs_peak": round(max(bgs), 5) if bgs else None,
                "track_med": statistics.median(track) if track else None}
    if diag:
        t_end = diag[-1][0]
        tail = sorted(b for t, b, _, _ in diag if t >= t_end - th["tail_s"])
        if tail:
            bas_stat["tail_med"] = round(tail[len(tail) // 2], 4)
        peak_t = max(diag, key=lambda r: r[1])[0]
        bas_stat["peak_t"] = round(peak_t, 1)
        hard = th["bas_hard"]
        over = [i for i, b in enumerate(bas) if b > hard]
        bas_stat["over_ratio"] = round(len(over) / len(bas), 4) if bas else None
        run = best = 0
        for b in bas:
            run = run + 1 if b > hard else 0
            best = max(best, run)
        bas_stat["longest_run_frames"] = best
    c1 = (bas_stat["over_ratio"] is not None and bas_stat["over_ratio"] <= th["bas_over_ratio_max"]
          and bas_stat["tail_med"] is not None and bas_stat["tail_med"] < th["bas_tail_med_max"]
          and bas_stat["longest_run_frames"] <= th["bas_run_frames_max"])
    crit["bas"] = dict(bas_stat)
    crit["bas"]["pass"] = bool(c1 if bas else False)
    if not bas:
        crit["bas"]["note"] = "无 T2diag(未 init 或旧二进制无插桩)"

    # ---------- ② ATE ----------
    ate = ev.get("ate_post60_m")
    ate_lim = th["baseline_ate_m"] * (1 + th["ate_margin_pct"] / 100.0)
    crit["ate"] = {"ate_post60_m": ate, "n_pairs": ev.get("ate_n_pairs"),
                   "limit": round(ate_lim, 4),
                   "pass": bool(ate is not None and ate <= ate_lim)}
    if ate is None:
        crit["ate"]["note"] = "ATE 缺失(配对<10/无真值)——不能证明达标,按 FAIL"

    # ---------- ③ init_cost 尖峰(相对倍率口径) ----------
    costs = [c for _, c in slv1]
    sp = {"n_phase1": len(slv1), "n_phase0": len(slv0),
          "phase0_max": round(max((c for _, c in slv0), default=0.0), 1),
          "abs_gt_1e3": None, "abs_max": None, "spike_n": None, "spike_rate": None,
          "max_ratio": None, "spike_times": [], "dominant_period_s": None, "ac_peak": None}
    if costs:
        ratios = rolling_median_ratios(costs, th["rollmed_win"])
        spike_idx = [i for i, r in enumerate(ratios) if r > th["spike_ratio_mult"]]
        sp["spike_n"] = len(spike_idx)
        sp["spike_rate"] = round(len(spike_idx) / len(costs), 4)
        sp["max_ratio"] = round(max(ratios), 1)
        sp["spike_times"] = [round(slv1[i][0], 1) for i in spike_idx[:12]]
        sp["abs_gt_1e3"] = sum(1 for c in costs if c > th["spike_abs_report"])
        sp["abs_max"] = round(max(costs), 1)
        per, ac = dominant_period([t for t, _ in slv1], costs, th["ac_thresh"],
                                  th["ac_min_lag_s"])
        sp["dominant_period_s"], sp["ac_peak"] = per, ac
        # 尖峰间隔统计(间隔≥1s 的相继尖峰;短簇内间隔另计)
        st = [slv1[i][0] for i in spike_idx]
        iv = [st[i + 1] - st[i] for i in range(len(st) - 1)]
        inter = [v for v in iv if v >= 1.0]
        if len(inter) >= 2:
            sp["spike_interval_med_s"] = round(statistics.median(inter), 2)
            sp["spike_interval_cv"] = round(statistics.pstdev(inter) /
                                            max(statistics.mean(inter), 1e-9), 2)
    c3 = (sp["spike_rate"] is not None and sp["spike_rate"] <= th["spike_rate_max"]
          and sp["max_ratio"] is not None and sp["max_ratio"] <= th["spike_max_ratio"])
    crit["spikes"] = dict(sp)
    crit["spikes"]["pass"] = bool(c3 if costs else False)
    crit["spikes"]["note"] = ("绝对>1e3 仅报告不入判(CTRL2 滑窗中位 2116,绝对口径误伤对照)"
                              if costs else "无 T2slv phase1")

    rep["criteria"] = crit
    keys = ["survival", "bas", "ate", "spikes"]
    fails = [k for k in keys if not crit[k].get("pass")]
    rep["failed"] = fails
    # 存活不可算时降权为三判据(survival 不入 fails)
    if crit["survival"].get("coverage") is None and "survival" in fails:
        fails.remove("survival")
    rep["verdict"] = "PASS" if not fails else "FAIL"
    return rep


# ================= 在线判决模式(v7.4 等待池①;输入=vins_smoke_runs/run_* 目录) =================

RE_RES_JUMP = re.compile(r"帧稳定性 \|pre-post\|=([\d.]+) m")
RE_RES_ARRIVE = re.compile(r"leg1 到位\(真值\) min=([\d.-]+) m \(<0.5\)->([01])")
RE_RES_AVOID = re.compile(r"避障 min_dist=([\d.-]+) m \(>0\.349\)->([01])")
RE_RES_HZ = re.compile(r"poscmd ([\d.]+) Hz \(>=50\)->([01])")
RE_RES_DISARM = re.compile(r"auto_disarm->([01])")
RE_RES_VERDICT = re.compile(r"RESULT=(PASS|FAIL|ENV-FAIL)")


def parse_result_txt(run_dir):
    """读 round_result.sh 的 RESULT.txt(轮后已算,不重算保判读一致);缺失时逐项 None。"""
    out = {"exists": False, "four": [None] * 4, "j0_jump_m": None, "result": None}
    rp = os.path.join(run_dir, "RESULT.txt")
    if not os.path.exists(rp):
        return out
    out["exists"] = True
    txt = open(rp, "r", errors="replace").read()
    out["raw"] = txt
    m = RE_RES_JUMP.search(txt)
    if m:
        out["j0_jump_m"] = float(m.group(1))
    m = RE_RES_ARRIVE.search(txt)
    if m:
        out["arrive_min_m"], out["four"][0] = float(m.group(1)), int(m.group(2))
    m = RE_RES_AVOID.search(txt)
    if m:
        out["avoid_min_m"], out["four"][1] = float(m.group(1)), int(m.group(2))
    m = RE_RES_HZ.search(txt)
    if m:
        out["poscmd_hz"], out["four"][2] = float(m.group(1)), int(m.group(2))
    m = RE_RES_DISARM.search(txt)
    if m:
        out["four"][3] = int(m.group(1))
    m = RE_RES_VERDICT.search(txt)
    if m:
        out["result"] = m.group(1)
    return out


def read_online_bag(bag_path):
    """flight.bag 过滤读 odom+truth(红线#4:带图袋只 read_messages 过滤读)。
    返回 (odom[(t,x,y,z)], truth[(t,x,y,z)], bag_span_s)。"""
    try:
        import rosbag
    except ImportError:
        return None, None, None
    odom, truth = [], []
    try:
        with rosbag.Bag(bag_path, "r") as b:
            for topic, msg, ts in b.read_messages(
                    topics=["/vins_estimator/odometry", "/gazebo/model_states"]):
                t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
                if topic == "/vins_estimator/odometry":
                    p = msg.pose.pose.position
                    odom.append((t, p.x, p.y, p.z))
                else:
                    try:
                        i = msg.name.index("iris_stereo_vins")
                    except ValueError:
                        continue
                    p = msg.pose[i].position
                    truth.append((t, p.x, p.y, p.z))
    except Exception as e:
        print(f"[t3_wa_gate] read_online_bag 异常 {bag_path}: {e!r}", file=sys.stderr)
        return [], [], None
    if not odom and not truth:
        return odom, truth, None
    first = min(odom[0][0] if odom else math.inf, truth[0][0] if truth else math.inf)
    last = max(odom[-1][0] if odom else -math.inf,
               truth[-1][0] if truth else -math.inf)
    return odom, truth, (last - first)


def online_survival_stats(diag, odom, bag_span, th):
    """零 failure 零 reboot 机器口径:T2diag t 回退计数 + odom 断流段 + 覆盖率。"""
    odom = odom or []
    reboot_n = 0
    for i in range(1, len(diag)):
        if diag[i][0] - diag[i - 1][0] < -th["online_reboot_fall_s"]:
            reboot_n += 1
    gaps, gap_max = 0, 0.0
    for i in range(1, len(odom)):
        d = odom[i][0] - odom[i - 1][0]
        if d > th["online_odom_gap_s"]:
            gaps += 1
        gap_max = max(gap_max, d)
    cov = ((odom[-1][0] - odom[0][0]) / bag_span) if (odom and bag_span) else None
    return {"reboot_n": reboot_n, "odom_gaps_gt": gaps,
            "odom_gap_max_s": round(gap_max, 2) if odom else None,
            "odom_n": len(odom),
            "odom_span_s": round(odom[-1][0] - odom[0][0], 1) if len(odom) > 1 else 0,
            "bag_span_s": round(bag_span, 1) if bag_span else None,
            "coverage": round(cov, 3) if cov is not None else None}


def online_ate_aligned(odom, truth, pair_win):
    """ATE 出生点对齐(VINS odom 原点=init 位;不对齐=+0.65m 级假误差,红线 8)。
    对齐平移=odom 首帧 vs truth 最近帧;最近邻配对窗 pair_win;全窗+后半窗双报。"""
    if not odom or not truth:
        return {"ate_rmse_m": None, "note": "缺 odom 或 truth 流"}
    t0 = odom[0][0]
    tg0 = min(truth, key=lambda r: abs(r[0] - t0))
    off = (tg0[1] - odom[0][1], tg0[2] - odom[0][2], tg0[3] - odom[0][3])
    ts_t = [r[0] for r in truth]
    errs = []
    for t, x, y, z in odom:
        j = bisect_left(ts_t, t)
        best = None
        for k in (j - 1, j):
            if 0 <= k < len(truth) and abs(truth[k][0] - t) <= pair_win:
                if best is None or abs(truth[k][0] - t) < abs(truth[best][0] - t):
                    best = k
        if best is None:
            continue
        g = truth[best]
        errs.append((t, math.dist((x + off[0], y + off[1], z + off[2]),
                                  (g[1], g[2], g[3]))))
    if not errs:
        return {"ate_rmse_m": None, "note": "配对 0 帧(时戳域分裂?查 bag 域)"}
    half = errs[len(errs) // 2][0]
    def rmse(sel):
        return round(math.sqrt(sum(e * e for _, e in sel) / len(sel)), 4) if sel else None
    return {"ate_rmse_m": rmse(errs), "ate_rmse_2ndhalf_m": rmse([e for e in errs if e[0] >= half]),
            "n_pairs": len(errs), "align_off_m": [round(v, 3) for v in off],
            "ate_peak_m": round(max(e for _, e in errs), 3)}


def envfail_scan(run_dir):
    """ENV-FAIL 证据扫描(runbook §4 三签名)。返回 (hard, soft):
    hard=轮中死亡硬证据(ENVDEAD 文件,vins_smoke 清场前活体检查写入;或 RESULT.txt
    当场判定的 ENV-FAIL——round_result 在 cleanup 前跑,时序正确);
    soft=字符串签名('Connection closed by client'/'px4 亡')——**事后扫描必含正常
    cleanup 杀 px4 的产物**(selftest 实测 WAOL5R/X1_232055 双命中),仅报告不入判。"""
    if os.path.exists(os.path.join(run_dir, "ENVDEAD")):
        return "ENVDEAD-file", None
    soft = None
    for name in ("sitl.log", "round.log"):
        p = os.path.join(run_dir, name)
        try:
            with open(p, "r", errors="replace") as f:
                txt = f.read()
        except OSError:
            continue
        if "Connection closed by client" in txt:
            soft = name + ":Connection-closed(normal-cleanup-artifact?)"
            break
        if "px4 亡,进程组整组清场" in txt:
            soft = name + ":px4-dead"
            break
    return None, soft


def forensics_fetch(run_dir, skip=False):
    """取/生成 forensics_v2 机制摘要(帧跳双口径 J0 修订数据源;默认 topics 无图像=安全)。"""
    fj = os.path.join(run_dir, "forensics_v2.json")
    if not os.path.exists(fj) and not skip:
        subprocess.run([sys.executable,
                        os.path.join(SCRIPT_DIR, "vins_divergence_forensics.py"), run_dir],
                       check=False, timeout=1800,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(fj):
        return {"available": False, "skipped": bool(skip)}
    with open(fj, "r", errors="replace") as f:
        d = json.load(f)
    v = d.get("verdict", {})
    fk = d.get("fork_odom_prop", {})
    return {"available": True, "morph": v.get("morph"), "t_star": v.get("t_star"),
            "divergence_type": v.get("divergence_type"),
            "fj_raw": d.get("frame_jumps_raw_odom"),
            "fj_smj": d.get("frame_jumps_smoothed_odom"),
            "fork_t": fk.get("t_fork"), "fork_max_m": fk.get("fork_max_m"),
            "prop_gap": d.get("prop_gap")}


def judge_online_dir(run_dir, th, skip_forensics=False):
    rep = {"dir": os.path.basename(replay_dir_safe(run_dir)), "mode": "online",
           "thresholds": {k: th[k] for k in th if k.startswith("online_")}}
    # ---- A. 四指标 + J0 锚差(RESULT.txt 权威,不重算) ----
    res = parse_result_txt(run_dir)
    four = res["four"]
    # ---- B. forensics(J0 修订轴数据源 + 机制摘要) ----
    fo = forensics_fetch(run_dir, skip_forensics)
    # ---- C. VINS 域面板(simvins.log + flight.bag) ----
    diag, slv1, slv0 = [], [], []
    vlog = os.path.join(run_dir, "simvins.log")
    if os.path.exists(vlog):
        diag, slv1, slv0 = parse_vins_log(vlog)
    odom, truth, bag_span = read_online_bag(os.path.join(run_dir, "flight.bag"))
    surv = online_survival_stats(diag, odom, bag_span, th)
    # Bas 三重口径(复用回放判据块逻辑,在线日志同格式);track_med=特征数(X7 逐轮表/runbook §2)
    bas = [b for _, b, _, _ in diag]
    bgs = [g for _, _, g, _ in diag]
    track = [tk for _, _, _, tk in diag]
    bas_stat = {"n": len(bas), "peak": round(max(bas), 4) if bas else None,
                "tail_med": None, "over_ratio": None, "longest_run_frames": 0,
                "bgs_peak": round(max(bgs), 5) if bgs else None,
                "track_med": statistics.median(track) if track else None}
    if diag:
        t_end = diag[-1][0]
        tail = sorted(b for t, b, _, _ in diag if t >= t_end - th["tail_s"])
        if tail:
            bas_stat["tail_med"] = round(tail[len(tail) // 2], 4)
        hard = th["bas_hard"]
        over = [1 for b in bas if b > hard]
        bas_stat["over_ratio"] = round(len(over) / len(bas), 4) if bas else None
        run = best = 0
        for b in bas:
            run = run + 1 if b > hard else 0
            best = max(best, run)
        bas_stat["longest_run_frames"] = best
    bas_pass = bool(bas and bas_stat["over_ratio"] <= th["bas_over_ratio_max"]
                    and (bas_stat["tail_med"] is None or bas_stat["tail_med"] < th["bas_tail_med_max"])
                    and bas_stat["longest_run_frames"] <= th["bas_run_frames_max"])
    # 尖峰(同回放口径)
    costs = [c for _, c in slv1]
    sp = {"n_phase1": len(slv1), "spike_n": None, "spike_rate": None, "max_ratio": None}
    if costs:
        ratios = rolling_median_ratios(costs, th["rollmed_win"])
        spk = [i for i, r in enumerate(ratios) if r > th["spike_ratio_mult"]]
        sp["spike_n"] = len(spk)
        sp["spike_rate"] = round(len(spk) / len(costs), 4)
        sp["max_ratio"] = round(max(ratios), 1)
    ate = online_ate_aligned(odom, truth, th["online_pair_win_s"])
    # ---- D. 判决组装 ----
    vins_pass = bool(surv["reboot_n"] == 0 and surv["odom_gaps_gt"] == 0 and bas_pass)
    if not bas:
        vins_pass = False
    j0_rev_pass = None
    if fo.get("available") and fo.get("fj_raw") is not None:
        j0_rev_pass = bool(fo["fj_raw"] <= th["online_j0_rev_raw_max"]
                           and fo["fj_smj"] <= th["online_j0_rev_smj_max"])
    four_known = all(v is not None for v in four)
    four_ok = all(four) if four_known else False
    j0_jump = res["j0_jump_m"]
    env_hard, env_soft = envfail_scan(run_dir)
    if res.get("result") == "ENV-FAIL":
        env_hard = env_hard or "RESULT.txt:ENV-FAIL"
    xline_pass = bool(four_ok and j0_jump is not None and j0_jump < 0.5
                      and j0_rev_pass is True)
    t1d1 = bool(j0_jump is not None and j0_jump >= 0.5 and vins_pass)
    if env_hard and not xline_pass:
        verdict = "ENV-FAIL"
    elif xline_pass:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    rep["xline"] = {"four": four, "four_known": four_known, "four_ok": four_ok,
                    "j0_jump_m": j0_jump, "j0_rev_pass": j0_rev_pass,
                    "fj_raw": fo.get("fj_raw"), "fj_smj": fo.get("fj_smj"),
                    "result_txt": res["result"], "env_sig": env_hard or env_soft,
                    "env_hard": env_hard, "t1d1_domain": t1d1, "pass": xline_pass}
    rep["vins"] = dict(surv, bas=bas_stat, bas_pass=bas_pass, spikes=sp, ate=ate,
                       pass_vins=vins_pass,
                       note_vins=("无 T2diag(旧二进制),Bas 轴不可判→vins 判 False"
                                  if not bas else None))
    rep["forensics"] = fo
    rep["verdict"] = verdict
    rep["failed"] = ([k for k, ok in (("four", four_ok), ("j0_jump", j0_jump is not None and j0_jump < 0.5),
                                      ("j0_rev", j0_rev_pass is True))]
                     if verdict == "FAIL" else [])
    return rep


def replay_dir_safe(d):
    return d.rstrip("/")


def one_line_online(rep):
    x = rep.get("xline", {})
    v = rep.get("vins", {})
    b = v.get("bas", {})
    fo = rep.get("forensics", {})
    four = x.get("four")
    four_s = "/".join(str(f) for f in four) if four else "?"
    return (f"{rep['dir']}: {rep.get('verdict')} "
            f"[four={four_s} j0jump={x.get('j0_jump_m')} j0rev={x.get('j0_rev_pass')}"
            f"(raw={x.get('fj_raw')},smj={x.get('fj_smj')}) "
            f"env={x.get('env_sig') or '-'}{' T1D1' if x.get('t1d1_domain') else ''} | "
            f"vins={'✓' if v.get('pass_vins') else '✗'} "
            f"reboot={v.get('reboot_n')} gaps={v.get('odom_gaps_gt')} cov={v.get('coverage')} "
            f"bas_pk={b.get('peak')} bgs_pk={b.get('bgs_peak')} "
            f"ate={v.get('ate', {}).get('ate_rmse_m')} morph={fo.get('morph')}]")


def one_line(rep):
    c = rep.get("criteria", {})
    parts = []
    for k in ("survival", "bas", "ate", "spikes"):
        v = c.get(k, {})
        mark = "✓" if v.get("pass") else "✗"
        if k == "survival":
            parts.append(f"survival{mark} cov={v.get('coverage')}")
        elif k == "bas":
            parts.append(f"bas{mark} peak={v.get('peak')} over={v.get('over_ratio')} "
                         f"run={v.get('longest_run_frames')} tail={v.get('tail_med')}")
        elif k == "ate":
            parts.append(f"ate{mark} {v.get('ate_post60_m')}/{v.get('limit')}")
        else:
            parts.append(f"spike{mark} rate={v.get('spike_rate')} maxratio={v.get('max_ratio')} "
                         f"abs>1e3={v.get('abs_gt_1e3')} max={v.get('abs_max')} "
                         f"period={v.get('dominant_period_s')}s iv_med={v.get('spike_interval_med_s')}s")
    return f"{rep['dir']}: {rep.get('verdict')} [{' | '.join(parts)}]"


# ---------------- selftest:R_CAN=FAIL / CTRL2=PASS 对账(883c75c 台账) ----------------
SELFTEST = {
    "R_CAN_flight": {
        "verdict": "FAIL",
        "expect": [
            ("ate", 1.564, 0.01),          # eval.json/台账:ATE 1.564
            ("t_star", 11.0, 0.5),         # 台账:早死复现 t*=11
            ("bas_peak_ge", 2.0, None),    # 实测 2.534(死亡时仍在爆)
            ("spike_abs_max_ge", 16000.0, None),   # 台账:16871 循环上界
            ("spike_abs_max_le", 46000.0, None),   # 实测 45430(45e3 级)
            ("spike_max_ratio_ge", 100.0, None),   # 实测 215×
            ("spike_rate_ge", 0.02, None),         # 实测 5.6%(>>1% 线)
        ],
    },
    "CTRL2_t2v3_route_112652": {
        "verdict": "PASS",
        "expect": [
            ("ate", 0.144, 0.01),          # 台账:ATE 0.144±0.01
            ("bas_tail_med", 0.11, 0.02),   # 台账:"Bas 0.11 稳"
            ("spike_rate_le", 0.01, None),  # 实测 0.46%
            ("spike_max_ratio_le", 50.0, None),  # 实测 34.6×
            ("coverage_ge", 0.8, None),     # 实测 ~0.96(全程)
            ("diag_n_ge", 1500, None),      # 实测 1723
        ],
    },
}


def run_selftest(th):
    base = os.path.expanduser("~/sitl_sim/t3_results")
    results, ok_all = [], True
    for name, spec in SELFTEST.items():
        d = os.path.join(base, name)
        rep = judge_dir(d, None, False, th)
        with open(os.path.join(d, "wa_gate.json"), "w") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        checks = []
        def chk(label, cond, got):
            checks.append({"check": label, "got": got, "pass": bool(cond)})
            return cond
        ok = chk(f"verdict=={spec['verdict']}", rep.get("verdict") == spec["verdict"],
                 rep.get("verdict"))
        c = rep.get("criteria", {})
        for item in spec["expect"]:
            key, ref, tol = item
            if key == "ate":
                v = c.get("ate", {}).get("ate_post60_m")
                got = v
                cond = v is not None and abs(v - ref) <= tol
            elif key == "t_star":
                v = rep.get("eval", {}).get("t_star_s")
                got = v
                cond = v is not None and abs(v - ref) <= tol
            elif key == "bas_peak_ge":
                got = c.get("bas", {}).get("peak")
                cond = got is not None and got >= ref
            elif key == "bas_tail_med":
                got = c.get("bas", {}).get("tail_med")
                cond = got is not None and abs(got - ref) <= tol
            elif key == "spike_abs_max_ge":
                got = c.get("spikes", {}).get("abs_max")
                cond = got is not None and got >= ref
            elif key == "spike_abs_max_le":
                got = c.get("spikes", {}).get("abs_max")
                cond = got is not None and got <= ref
            elif key == "spike_max_ratio_ge":
                got = c.get("spikes", {}).get("max_ratio")
                cond = got is not None and got >= ref
            elif key == "spike_max_ratio_le":
                got = c.get("spikes", {}).get("max_ratio")
                cond = got is not None and got <= ref
            elif key == "spike_rate_ge":
                got = c.get("spikes", {}).get("spike_rate")
                cond = got is not None and got >= ref
            elif key == "spike_rate_le":
                got = c.get("spikes", {}).get("spike_rate")
                cond = got is not None and got <= ref
            elif key == "coverage_ge":
                got = c.get("survival", {}).get("coverage")
                cond = got is not None and got >= ref
            elif key == "diag_n_ge":
                got = c.get("survival", {}).get("diag_n")
                cond = got is not None and got >= ref
            else:
                got, cond = None, False
            ok = chk(f"{key} {'~' if tol else '>=' if key.endswith('_ge') else '<='} {ref}",
                     cond, got) and ok
        results.append({"cell": name, "ok": bool(ok), "line": one_line(rep), "checks": checks})
        ok_all = ok_all and ok
    out = {"pass": bool(ok_all), "cells": results,
           "note": "对账基准=883c75c 台账(X 线根因包):R_CAN t*=11/ATE 1.564/cost>1e4 含 16871;"
                   "CTRL2 ATE 0.144/Bas 0.11 稳/滑窗 cost 收敛"}
    with open(os.path.join(SCRIPT_DIR, "t3_wa_gate_selftest.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for r in results:
        print(f"[selftest] {r['cell']}: {'PASS' if r['ok'] else 'FAIL'}")
        print("  " + r["line"])
        for ck in r["checks"]:
            if not ck["pass"]:
                print(f"  !! 未对上: {ck['check']} got={ck['got']}")
    print(f"[selftest] 总判决: {'PASS(双侧对账一致)' if ok_all else 'FAIL(修到对上为止)'}")
    return 0 if ok_all else 1


# ---------------- 在线 selftest:WAOL5R(健康,T1-D1 域跳变) + X1_232055(爆散) 对账 ----------------
# 对账基准(T2 台账/STATUS 22:33 通告 + 883c75c 根因包 + T3 forensics Y1.2):
#   WAOL5R: 全程 314.5s 零 failure 零 reboot,Bas_max 0.981<1.0,Bgs 0.002 级,
#           单次 2.45m 跳变(锚差口径 2.448,RESULT.txt 实测)→四指标到位 FAIL=T1-D1 域
#   X1_232055: 标准爆散(odom 冲 740m),forensics_v2.json 实测 frame_jumps raw=624/smj=632
SELFTEST_ONLINE = {
    "run_WAOL5R_222234": {
        "verdict": "FAIL",
        "expect": [
            ("four_arrive", 0, None),          # J0 跳变 2.448m → 到位 FAIL(T1-D1 域)
            ("j0_jump", 2.448, 0.01),          # RESULT.txt 锚差口径
            ("t1d1_domain", True, None),       # vins 域健康 + j0_jump>0.5 → T1-D1 标注
            ("reboot_n", 0, None),             # 台账:零 reboot
            ("odom_gaps", 0, None),            # 台账:零 failure(断流口径)
            ("bas_peak", 0.981, 0.03),         # 台账:Bas_max 0.981
            ("bgs_peak_le", 0.01, None),       # 台账:Bgs 0.002 级
            ("vins_pass", True, None),         # T2 U3 口径:零 failure 零 reboot + Bas 健康
        ],
    },
    "run_X1_232055": {
        "verdict": "FAIL",
        "expect": [
            ("fj_raw_ge", 100, None),          # forensics 实测 624(爆散帧跳海量)
            ("fj_smj_ge", 100, None),          # 实测 632
            ("j0_rev_pass", False, None),      # raw==0 不可达
            ("morph_diverged", True, None),    # forensics verdict:爆散
            ("vins_pass", False, None),        # 无 T2diag 旧轮→Bas 轴不可判→vins False
        ],
    },
}


def run_online_selftest(th):
    base = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
    results, ok_all = [], True
    for name, spec in SELFTEST_ONLINE.items():
        rep = judge_online_dir(os.path.join(base, name), th)
        with open(os.path.join(base, name, "wa_gate_online.json"), "w") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        x, v, fo = rep.get("xline", {}), rep.get("vins", {}), rep.get("forensics", {})
        b = v.get("bas", {})
        checks = []
        def chk(label, cond, got):
            checks.append({"check": label, "got": got, "pass": bool(cond)})
            return cond
        ok = chk(f"verdict=={spec['verdict']}", rep.get("verdict") == spec["verdict"],
                 rep.get("verdict"))
        for key, ref, tol in spec["expect"]:
            got, cond = None, False
            if key == "four_arrive":
                got = x.get("four", [None])[0]
                cond = got == ref
            elif key == "j0_jump":
                got = x.get("j0_jump_m")
                cond = got is not None and abs(got - ref) <= tol
            elif key == "t1d1_domain":
                got = x.get("t1d1_domain")
                cond = got == ref
            elif key == "reboot_n":
                got = v.get("reboot_n")
                cond = got == ref
            elif key == "odom_gaps":
                got = v.get("odom_gaps_gt")
                cond = got == ref
            elif key == "bas_peak":
                got = b.get("peak")
                cond = got is not None and abs(got - ref) <= tol
            elif key == "bgs_peak_le":
                got = b.get("bgs_peak")
                cond = got is not None and got <= ref
            elif key == "vins_pass":
                got = v.get("pass_vins")
                cond = got == ref
            elif key == "fj_raw_ge":
                got = x.get("fj_raw")
                cond = got is not None and got >= ref
            elif key == "fj_smj_ge":
                got = x.get("fj_smj")
                cond = got is not None and got >= ref
            elif key == "j0_rev_pass":
                got = x.get("j0_rev_pass")
                cond = got == ref
            elif key == "morph_diverged":
                got = fo.get("morph")
                cond = got in ("爆散", "跳变(离散大帧跳)", "小跳/渐进劣化",
                               "数值溢出型(含 extreme 帧)")
            ok = chk(f"{key} ref={ref}", cond, got) and ok
        results.append({"cell": name, "ok": bool(ok), "line": one_line_online(rep),
                        "checks": checks})
        ok_all = ok_all and ok
    out = {"pass": bool(ok_all), "cells": results,
           "note": "在线轴对账:WAOL5R=T2 22:33 通告数字(Bas 0.981/314.5s 零failure);"
                   "X1_232055=forensics_v2.json 实测(raw624/smj632/爆散)"}
    with open(os.path.join(SCRIPT_DIR, "t3_wa_gate_online_selftest.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for r in results:
        print(f"[online-selftest] {r['cell']}: {'PASS' if r['ok'] else 'FAIL'}")
        print("  " + r["line"])
        for ck in r["checks"]:
            if not ck["pass"]:
                print(f"  !! 未对上: {ck['check']} got={ck['got']}")
    print(f"[online-selftest] 总判决: {'PASS(双侧对账一致)' if ok_all else 'FAIL(修到对上为止)'}")
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*", help="t3_replay 输出目录(一个或多个)")
    ap.add_argument("--src-bag", default=None, help="源袋(仅 --recompute-eval 时用)")
    ap.add_argument("--recompute-eval", action="store_true")
    ap.add_argument("--thresholds", default=None, help="阈值 JSON(默认脚本同目录)")
    ap.add_argument("--csv", default=None, help="追加汇总 CSV(矩阵批)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--online", action="store_true",
                    help="在线判决模式:输入=vins_smoke_runs/run_* 目录")
    ap.add_argument("--skip-forensics", action="store_true",
                    help="在线模式跳过 forensics 生成(仅用已有 json)")
    args = ap.parse_args()

    tpath = args.thresholds or os.path.join(SCRIPT_DIR, "t3_wa_gate_thresholds.json")
    th = dict(DEFAULT_THRESH)
    if not os.path.exists(tpath):
        with open(tpath, "w") as f:
            json.dump(DEFAULT_THRESH, f, ensure_ascii=False, indent=1)
    else:
        with open(tpath, "r", errors="replace") as f:
            th.update(json.load(f))

    if args.online and args.selftest:
        sys.exit(run_online_selftest(th))
    if args.selftest:
        sys.exit(run_selftest(th))
    if not args.dirs:
        ap.error("需要目录或 --selftest")
    if args.online:
        rows = []
        for d in args.dirs:
            rep = judge_online_dir(d, th, args.skip_forensics)
            with open(os.path.join(d, "wa_gate_online.json"), "w") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
            print(one_line_online(rep))
            rows.append(rep)
        if args.csv:
            import csv
            newf = not os.path.exists(args.csv)
            with open(args.csv, "a", newline="") as f:
                w = csv.writer(f)
                if newf:
                    w.writerow(["dir", "verdict", "four", "j0_jump", "fj_raw", "fj_smj",
                                "j0_rev", "env_sig", "t1d1", "vins_pass", "reboot_n",
                                "gaps", "coverage", "bas_peak", "bgs_peak", "track_med",
                                "spike_rate", "ate_rmse", "morph", "t_star"])
                for r in rows:
                    x, v = r.get("xline", {}), r.get("vins", {})
                    w.writerow([r["dir"], r.get("verdict"),
                                "/".join(str(f) for f in x.get("four") or []),
                                x.get("j0_jump_m"), x.get("fj_raw"), x.get("fj_smj"),
                                x.get("j0_rev_pass"), x.get("env_sig"),
                                int(bool(x.get("t1d1_domain"))), v.get("pass_vins"),
                                v.get("reboot_n"), v.get("odom_gaps_gt"),
                                v.get("coverage"), v.get("bas", {}).get("peak"),
                                v.get("bas", {}).get("bgs_peak"),
                                v.get("bas", {}).get("track_med"),
                                v.get("spikes", {}).get("spike_rate"),
                                v.get("ate", {}).get("ate_rmse_m"),
                                r.get("forensics", {}).get("morph"),
                                r.get("forensics", {}).get("t_star")])
        fails = sum(1 for r in rows if r.get("verdict") != "PASS")
        print(f"[t3_wa_gate:online] {len(rows)} 轮,{fails} 非 PASS")
        return
    rows = []
    for d in args.dirs:
        rep = judge_dir(d, args.src_bag, args.recompute_eval, th)
        with open(os.path.join(d, "wa_gate.json"), "w") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print(one_line(rep))
        rows.append(rep)
    if args.csv:
        import csv
        newf = not os.path.exists(args.csv)
        with open(args.csv, "a", newline="") as f:
            w = csv.writer(f)
            if newf:
                w.writerow(["dir", "verdict", "failed", "coverage", "bas_peak",
                            "bas_over", "bas_run", "bas_tail", "bgs_peak", "ate",
                            "t_star", "spike_rate", "spike_maxratio", "abs_gt1e3",
                            "abs_max", "period_s", "diag_n"])
            for r in rows:
                c = r.get("criteria", {})
                w.writerow([r["dir"], r.get("verdict"), ";".join(r.get("failed", [])),
                            c.get("survival", {}).get("coverage"),
                            c.get("bas", {}).get("peak"), c.get("bas", {}).get("over_ratio"),
                            c.get("bas", {}).get("longest_run_frames"),
                            c.get("bas", {}).get("tail_med"), c.get("bas", {}).get("bgs_peak"),
                            c.get("ate", {}).get("ate_post60_m"),
                            r.get("eval", {}).get("t_star_s"),
                            c.get("spikes", {}).get("spike_rate"),
                            c.get("spikes", {}).get("max_ratio"),
                            c.get("spikes", {}).get("abs_gt_1e3"),
                            c.get("spikes", {}).get("abs_max"),
                            c.get("spikes", {}).get("dominant_period_s"),
                            c.get("survival", {}).get("diag_n")])
    fails = sum(1 for r in rows if r.get("verdict") != "PASS")
    print(f"[t3_wa_gate] {len(rows)} 目录,{fails} FAIL")


if __name__ == "__main__":
    main()
