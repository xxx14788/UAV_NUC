#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Y1.3 全库法证扫描器(T3 v7.2):跨战役发散数据库构建

枚举库内全部轮次袋并逐袋扫描(只读数字话题,红线#4;带图袋 topics 过滤):
  A. ~/sitl_sim/vins_smoke_runs 全部轮(flight.bag;simvins.log 供 T2diag 解析)
  B. ~/sitl_sim/t2_results 下全部回放产物袋(vins_out.bag;vins.log 供 T2diag)
  C. ~/sitl_sim/bags 白名单袋(ground/hover/route/w2b 系;t2_A-E 矩阵袋属 T2-W-B2
     镜像域,本库不入,见 docs/t3_cross_campaign_mining.md 范围声明)
每袋一行入跨战役发散数据库(CSV+JSON 双落盘,增量追加,重跑跳过已扫键)。

行字段:轮名/类别/年代/场景/配置代/形态/t*/距离地/分叉类型/Bas峰/Bgs峰/track_med/
  odom_Hz/prop_Hz/imu 摘要(dt_p50/acc_peak/hdr回退)/终态漂移/帧跳变(平滑口径)/
  污染嫌疑/RESULT_txt/DB判决/缺失原因/证据路径/扫描时刻。
元数据三源合成:时代段表(台账知识,ERAS)+ 目录名编码 + RESULT.txt 解析;
  未登记者如实标"未登记",不猜。

复用:vins_divergence_forensics.analyze(symlink flight.bag 技巧,全库一致口径)+
  t3_wa_gate.RE_DIAG(T2diag 解析)。

用法:
  t3_library_forensics.py scan [--only 子串]     # 增量扫描(nohup 串行队列跑法见台账)
  t3_library_forensics.py selftest               # 232055=FAIL-发散 + t2v3_ground=健康
输出: <script_dir>/t3_library_forensics_db.csv + .json
"""
import argparse
import csv
import datetime
import json
import math
import os
import re
import shutil
import sys
import tempfile

import vins_divergence_forensics as vf
import t3_wa_gate as gate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
T2RES = os.path.expanduser("~/sitl_sim/t2_results")
BAGS = os.path.expanduser("~/sitl_sim/bags")
DB_CSV = os.path.join(SCRIPT_DIR, "t3_library_forensics_db.csv")
DB_JSON = os.path.join(SCRIPT_DIR, "t3_library_forensics_db.json")
WORKROOT = "/tmp/t3lib_scan"

# 白名单袋匹配(ground/hover/route/w2b 系;含早期 flight_ 直录)
WHITELIST_PAT = re.compile(
    r"^t2v3_(ground|hover|route|w2b)_.*\.bag$|^flight_2026-09-2[0-9].*\.bag$")

# 时代段(台账知识;[起始时间戳, 结束, 场景, 配置代];时间取轮名 HHMMSS)
ERAS = [
    ("202609282200", "202609290030", "obstacles(X1 验收)", "旧观测层(SDF无噪声/FB0.5/ext1/acc_n0.1)"),
    ("202609290130", "202609290500", "obstacles(D0/D1 取证)", "旧观测层+带图取证(ext1)"),
    ("202609290220", "202609290300", "悬停 smoke(T1 WD/E2FAIL)", "T1 平滑重锚+odom门二进制"),
    ("202609291000", "202609291200", "obstacles(X1' F 线)", "canonical四件套+噪声基线;104445起ext0"),
    ("202609291700", "202609291900", "obstacles(X 线)", "canonical ext0+精确外参+acc_n0.2"),
]


def ts_of(name):
    m = re.search(r"_(\d{6})$", name)
    return m.group(1) if m else None


def era_of(name, default_scene="未登记", default_cfg="未登记"):
    t = ts_of(name)
    if not t:
        return default_scene, default_cfg
    # 轮名时间戳按目录内日期归属:22-23 点=09-28,00-19 点=09-29
    day = "28" if t >= "220000" else "29"
    key = "202609" + day + t
    for lo, hi, scene, cfg in ERAS:
        if lo <= key <= hi:
            return scene, cfg
    return default_scene, default_cfg


def parse_result_txt(run_dir):
    """RESULT.txt → {result, min_truth, poscmd_hz}。"""
    p = os.path.join(run_dir, "RESULT.txt")
    if not os.path.exists(p):
        return {}
    out = {}
    for line in open(p, errors="replace"):
        m = re.search(r"RESULT=(\w+)", line)
        if m:
            out["result"] = m.group(1)
        m = re.search(r"min=([\d.]+) m", line)
        if m and "min_truth" not in out:
            out["min_truth"] = float(m.group(1))
        m = re.search(r"poscmd ([\d.]+) Hz", line)
        if m:
            out["poscmd_hz"] = float(m.group(1))
    return out


def parse_t2diag_log(log_path):
    """simvins.log/vins.log → Bas/Bgs/track 摘要。"""
    if not log_path or not os.path.exists(log_path):
        return {}
    bas, bgs, track = [], [], []
    with open(log_path, errors="replace") as f:
        for line in f:
            m = gate.RE_DIAG.search(line)
            if m:
                bas.append(float(m.group(2)))
                bgs.append(float(m.group(3)))
                track.append(int(m.group(5)))
    if not bas:
        return {}
    bas_sorted = sorted(bas)
    return {"bas_peak": round(max(bas), 4), "bas_tail_med": round(bas_sorted[len(bas) // 2], 4),
            "bgs_peak": round(max(bgs), 5),
            "track_med": sorted(track)[len(track) // 2] if track else None,
            "diag_n": len(bas)}


def scan_bag(bag_path, log_path, key, cat, scene, cfg):
    """symlink 技巧复用 vf.analyze;返回 DB 行(dict)。"""
    work = os.path.join(WORKROOT, key)
    os.makedirs(work, exist_ok=True)
    link = os.path.join(work, "flight.bag")
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(os.path.abspath(bag_path), link)
    missing = []
    try:
        rep = vf.analyze(work, vf.DEFAULT_TOPICS)
    except Exception as e:
        return {"轮名": key, "类别": cat, "DB判决": "SCAN-ERROR",
                "缺失原因": f"analyze 异常: {e!r}", "证据路径": bag_path,
                "扫描时刻": datetime.datetime.now().isoformat(timespec="seconds")}
    v = rep["verdict"]
    sh, im, es = rep["stream_health"], rep["imu"], rep["end_state"]
    diag = parse_t2diag_log(log_path)
    if not diag:
        missing.append("T2diag(无日志或旧二进制无插桩)")
    res = parse_result_txt(os.path.dirname(bag_path)) if cat == "smoke_run" else {}
    # 污染
    poison = v.get("poisoning_suspect") or ""
    # DB 判决
    morph = v.get("morph") or "未知"
    if poison:
        dbv = "判废-双流污染"
    elif morph.startswith("数值溢出"):
        dbv = "FAIL-数值溢出"
    elif morph in ("爆散",) or (morph.startswith("跳变")):
        dbv = f"FAIL-发散({morph.split('(')[0]})"
    elif rep.get("prop_gap"):
        dbv = "FAIL-早死(VINS 停流)"
    elif morph == "小跳/渐进劣化":
        dbv = "FAIL-劣化"
    elif morph == "无帧跳变(慢劣化或未发散)":
        dbv = "健康-无帧跳变"
        if res.get("result") == "FAIL":
            dbv = "FAIL(RESULT)-非发散类(到位/避障指标)"
    else:
        dbv = f"形态:{morph}"
    if res.get("result"):
        dbv += f"|RESULT={res['result']}"
    row = {
        "轮名": key, "类别": cat, "年代": datetime.date.fromtimestamp(
            os.path.getmtime(bag_path)).isoformat() if os.path.exists(bag_path) else "?",
        "场景": scene, "配置代": cfg, "形态": morph,
        "t*_s": v.get("t_star"), "分叉类型": v.get("divergence_type") or "",
        "Bas峰": diag.get("bas_peak"), "Bas中位": diag.get("bas_tail_med"),
        "Bgs峰": diag.get("bgs_peak"), "track_med": diag.get("track_med"),
        "diag_n": diag.get("diag_n"),
        "odom_Hz": rep["freq"].get("odom", {}).get("hz_all"),
        "prop_Hz": rep["freq"].get("prop", {}).get("hz_all"),
        "imu_n": im.get("n"), "imu_dt_p50_ms": im.get("dt_p50_ms"),
        "imu_acc_peak": im.get("acc_peak"), "imu_hdr回退": im.get("hdr_regression_n"),
        "clock回退": rep["clock_health"].get("regression_n"),
        "终态漂移_m": es.get("final_drift_prop_truth_m"),
        "距离地_max_m": es.get("truth_z_max"), "距离地_med_m": es.get("truth_z_med"),
        "prop包络_m": es.get("prop_bbox_diag_m"),
        "帧跳变_raw": rep.get("frame_jumps_raw_odom"),
        "帧跳变_smoothed": rep.get("frame_jumps_smoothed_odom"),
        "分叉t": rep["fork_odom_prop"].get("t_fork"),
        "污染嫌疑": poison or "",
        "RESULT_min_truth": res.get("min_truth"), "RESULT_poscmd_hz": res.get("poscmd_hz"),
        "DB判决": dbv, "缺失原因": ";".join(missing), "证据路径": bag_path,
        "扫描时刻": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    return row


def enumerate_targets(only=None):
    """[(key, bag, log, cat, scene, cfg)] 全库枚举;无袋轮也入账。"""
    out = []
    if os.path.isdir(RUNS):
        for name in sorted(os.listdir(RUNS)):
            if only and only not in name:
                continue
            rd = os.path.join(RUNS, name)
            bag = os.path.join(rd, "flight.bag")
            if not os.path.isdir(rd):
                continue
            scene, cfg = era_of(name, "未登记(smoke_run)", "未登记")
            if name.startswith("run_WD1") or name.startswith("run_E2FAIL"):
                scene, cfg = "悬停 smoke(T1)", "T1 平滑重锚+odom门二进制"
            if not os.path.exists(bag):
                out.append((name, None, None, "smoke_run", scene, cfg))
                continue
            out.append((name, bag, os.path.join(rd, "simvins.log"), "smoke_run", scene, cfg))
    if os.path.isdir(T2RES):
        for name in sorted(os.listdir(T2RES)):
            if only and only not in name:
                continue
            rd = os.path.join(T2RES, name)
            bag = os.path.join(rd, "vins_out.bag")
            if not os.path.isdir(rd):
                continue
            if not os.path.exists(bag):
                out.append((name, None, None, "replay_product", "回放(场景=源袋)", "目录名编码"))
                continue
            out.append((name, bag, os.path.join(rd, "vins.log"), "replay_product",
                        "回放(场景=源袋)", "目录名编码"))
    if os.path.isdir(BAGS):
        for name in sorted(os.listdir(BAGS)):
            if only and only not in name:
                continue
            if name.endswith(".bag") and WHITELIST_PAT.match(name):
                base = name[:-4]
                scene = ("ground" if "ground" in name else "hover" if "hover" in name
                         else "route" if "route" in name else "w2b" if "w2b" in name
                         else "早期直录")
                out.append((base, os.path.join(BAGS, name), None, "whitelist_bag", scene,
                            "T2 白名单源袋(在线配置)"))
    return out


def load_db():
    if os.path.exists(DB_JSON):
        with open(DB_JSON, errors="replace") as f:
            return json.load(f)
    return []


def save_db(rows):
    with open(DB_JSON, "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    if not rows:
        return
    cols = list(rows[0].keys())
    with open(DB_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def cmd_scan(only):
    rows = load_db()
    done = {r["轮名"] for r in rows}
    targets = enumerate_targets(only)
    print(f"[lib] 枚举 {len(targets)} 目标,已完成 {len(done)}", flush=True)
    for key, bag, log, cat, scene, cfg in targets:
        if key in done:
            continue
        if bag is None:
            rows.append({"轮名": key, "类别": cat, "场景": scene, "配置代": cfg,
                         "DB判决": "无袋", "缺失原因": "目录无 flight.bag/vins_out.bag(以无袋行入账)",
                         "证据路径": os.path.join(RUNS if cat == 'smoke_run' else T2RES, key),
                         "扫描时刻": datetime.datetime.now().isoformat(timespec="seconds")})
            save_db(rows)
            print(f"[lib] {key}: 无袋行入账", flush=True)
            continue
        t0 = datetime.datetime.now()
        row = scan_bag(bag, log, key, cat, scene, cfg)
        rows.append(row)
        save_db(rows)
        dt = (datetime.datetime.now() - t0).total_seconds()
        print(f"[lib] {key}: {row.get('DB判决')} t*={row.get('t*_s')} "
              f"Bas峰={row.get('Bas峰')} smj={row.get('帧跳变_smoothed')} ({dt:.0f}s)", flush=True)
    # 覆盖率验收
    n_bag = sum(1 for k, b, *_ in targets if b)
    n_row = sum(1 for r in rows)
    print(f"[lib] 库={len(targets)}(有袋 {n_bag}) DB={n_row} 行;"
          f"覆盖率 {'OK' if n_row >= len(targets) else '不足'}", flush=True)


def cmd_selftest():
    """已知样本对账:232055=FAIL-发散(爆散 t*=6.9,Y1.2 实测)+ ground 白名单袋=健康。"""
    ok = True
    r1 = scan_bag(os.path.join(RUNS, "run_X1_232055", "flight.bag"),
                  os.path.join(RUNS, "run_X1_232055", "simvins.log"),
                  "SELFTEST_232055", "smoke_run", "obstacles(X1 验收)",
                  "旧观测层(SDF无噪声/FB0.5/ext1/acc_n0.1)")
    c1 = [("判决含FAIL-发散", "FAIL-发散" in r1["DB判决"]),
          ("形态=爆散", r1["形态"] == "爆散"),
          ("t*=6.9±1", r1["t*_s"] is not None and abs(r1["t*_s"] - 6.9) <= 1.0)]
    gb = os.path.join(BAGS, "t2v3_ground_202520.bag")
    r2 = scan_bag(gb, None, "SELFTEST_ground", "whitelist_bag", "ground",
                  "T2 白名单源袋(在线配置)")
    c2 = [("判决=健康", "健康" in r2["DB判决"]),
          ("无污染", r2["污染嫌疑"] == ""),
          ("零时戳回退", (r2["imu_hdr回退"] or 0) == 0 and (r2["clock回退"] or 0) == 0)]
    for label, rows_, checks in (("232055", r1, c1), ("ground", r2, c2)):
        bad = [l for l, okc in checks if not okc]
        print(f"[selftest] {label}: {'PASS' if not bad else 'FAIL ' + str(bad)} "
              f"判决={rows_['DB判决']} t*={rows_['t*_s']} smj={rows_['帧跳变_smoothed']}")
        ok = ok and not bad
    print(f"[selftest] 总判决: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "selftest"])
    ap.add_argument("--only", default=None, help="只扫轮名含此子串者")
    args = ap.parse_args()
    os.makedirs(WORKROOT, exist_ok=True)
    if args.cmd == "selftest":
        sys.exit(cmd_selftest())
    cmd_scan(args.only)


if __name__ == "__main__":
    main()
