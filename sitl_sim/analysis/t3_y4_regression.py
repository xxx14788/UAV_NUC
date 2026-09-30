#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Y4 W-A 修复版全库回归门执行器(T3 v7.2;T2 绿灯后一键开跑)

素材(Y1.3 DB 自动枚举,任务书 Y4 节口径):
  A. 全部历史失败袋:smoke_run 有袋行中 DB判决∈{FAIL-发散,FAIL-数值溢出,FAIL-劣化}
     (判废-双流污染剔除——P0 素材剔除纪律,W-P4)
  B. 双基线不劣化:CTRL2(route_112652)+hover(t2v3_hover_203248)
  C. W2 五场景袋(借用域):默认排除,--with-w2 显式开启(需 T2 同意,任务书原文)
回放:t3_replay.sh 串行队列(私有 master 11313,单机一路重回放红线;轮间等待+RESULT 落盘)
判决:t3_wa_gate 四轴;汇总 CSV+预言表 W-P1..P7 勾销表(docs/t3_wa_fullregression.md 骨架)
纪律:任何历史失败形态漏网→登记+回挖+通知 T2,X 线不启动(任务书 Y4 原文)。

用法:
  t3_y4_regression.py --dry-run              # 只列队列+预估时长(现在可用)
  t3_y4_regression.py --cfg <T2修复版配置目录> [--port 11313] [--with-w2]
  t3_y4_regression.py --prophecy             # 对已跑完的 Y4 目录出预言勾销表
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
BAGS = os.path.expanduser("~/sitl_sim/bags")
T3RES = os.path.expanduser("~/sitl_sim/t3_results")
DB = os.path.join(SCRIPT_DIR, "t3_library_forensics_db.json")
OUT_CSV = os.path.join(SCRIPT_DIR, "t3_y4_regression.csv")

FAIL_VERDICTS = ("FAIL-发散", "FAIL-数值溢出", "FAIL-劣化")


def load_db():
    with open(DB, encoding="utf-8") as f:
        return json.load(f)


def build_queue(with_w2=False):
    """[(tag, bag, note)] — DB 驱动;去重;污染轮剔除。"""
    q = []
    seen = set()
    for r in load_db():
        if r.get("类别") != "smoke_run":
            continue
        v = r.get("DB判决") or ""
        if not any(v.startswith(f) for f in FAIL_VERDICTS):
            continue
        if "判废" in v:
            continue  # P0 剔除(W-P4:污染轮不作 W-A 回归判读)
        bag = os.path.join(RUNS, r["轮名"], "flight.bag")
        if not os.path.exists(bag) or r["轮名"] in seen:
            continue
        seen.add(r["轮名"])
        q.append((f"Y4_{r['轮名'][4:]}", bag, f"DB:{v.split('|')[0]}"))
    # 双基线
    for tag, bag, note in (
            ("Y4B_CTRL2_route112652", os.path.join(BAGS, "t2v3_route_112652.bag"),
             "无障碍基线 0.144m 不回退门"),
            ("Y4B_hover_203248", os.path.join(BAGS, "t2v3_hover_203248.bag"),
             "悬停基线不劣化门")):
        if os.path.exists(bag):
            q.append((tag, bag, note))
    if with_w2:
        for name in sorted(os.listdir(BAGS)):
            if name.startswith("t2w5_") and name.endswith(".bag"):
                q.append((f"Y4W_{name[:-4]}", os.path.join(BAGS, name), "W2 借用域(T2 已同意)"))
    return q


def bag_seconds(bag):
    try:
        out = subprocess.run(["rosbag", "info", "--yaml", bag],
                             capture_output=True, text=True, timeout=60).stdout
        for line in out.splitlines():
            if line.startswith("duration:"):
                return float(line.split()[1])
    except Exception:
        pass
    return None


def cmd_dryrun(with_w2):
    q = build_queue(with_w2)
    total = 0.0
    print(f"[y4] 队列 {len(q)} 袋(污染轮已剔除;W2 {'含' if with_w2 else '不含'}):")
    for tag, bag, note in q:
        d = bag_seconds(bag)
        total += (d or 0) + 60
        print(f"  {tag:36s} {os.path.basename(bag):32s} {d or '?':>6.0f}s  {note}")
    print(f"[y4] 预估回放总时长 ≈ {total / 60:.0f} min(串行,单机一路红线)")


def cmd_run(cfg, port, with_w2):
    if not os.path.isdir(cfg):
        sys.exit(f"[y4] 配置目录不存在: {cfg}")
    q = build_queue(with_w2)
    print(f"[y4] 开跑 {len(q)} 袋;先决=T2 三判据绿灯通告(若无,--i-know-unlocked 强制需人工加)")
    rows = []
    for i, (tag, bag, note) in enumerate(q):
        print(f"\n[y4] ({i + 1}/{len(q)}) {tag} …", flush=True)
        r = subprocess.run(["bash", os.path.join(SCRIPT_DIR, "t3_replay.sh"),
                            tag, bag, cfg, str(port)], timeout=3600)
        time.sleep(3)
        out_dir = os.path.join(T3RES, f"{tag}_{os.path.basename(bag)[:-4]}")
        g = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "t3_wa_gate.py"),
                            out_dir], capture_output=True, text=True)
        print("  " + (g.stdout or g.stderr).strip().splitlines()[0] if (g.stdout or g.stderr).strip() else "  no-verdict")
        try:
            with open(os.path.join(out_dir, "wa_gate.json"), encoding="utf-8") as f:
                rep = json.load(f)
            rows.append({"tag": tag, "bag": os.path.basename(bag), "note": note,
                         "verdict": rep.get("verdict"),
                         "failed": ";".join(rep.get("failed", [])),
                         "ate": rep.get("criteria", {}).get("ate", {}).get("ate_post60_m"),
                         "bas_peak": rep.get("criteria", {}).get("bas", {}).get("peak"),
                         "coverage": rep.get("criteria", {}).get("survival", {}).get("coverage"),
                         "spike_rate": rep.get("criteria", {}).get("spikes", {}).get("spike_rate")})
        except Exception as e:
            rows.append({"tag": tag, "bag": os.path.basename(bag), "note": note,
                         "verdict": "NO-GATE-JSON", "failed": repr(e)})
        with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    n_pass = sum(1 for r in rows if r.get("verdict") == "PASS")
    print(f"\n[y4] 汇总: {n_pass}/{len(rows)} PASS → {OUT_CSV}")
    print(f"[y4] 判定: {'回归门通过(可启动 X 线)' if n_pass == len(rows) else '存在漏网→登记+回挖+通知 T2,X 线不启动'}")


def cmd_prophecy():
    """W-P1..P7 勾销表:读 Y4 汇总 CSV。"""
    P = [
        ("W-P1", "init_cost 尖峰循环+Bas 爬升(obstacles 发散行)", "消失",
         "全部 obstacles 失败袋重放 spike_rate≤1% 且 maxratio≤50"),
        ("W-P2", "速度爬坡顶格 49.9-50(prop 流)", "消失",
         "重放录制 prop 流 v_max<5(可从 vins_out.bag 事后验)"),
        ("W-P3", "goal 瞬态簇 Bas 爆", "消失", "t3_wa_gate Bas 轴过(占比+持续+终态)"),
        ("W-P4", "双流污染(043355/X1img2)", "不消失(环境)", "素材已剔除,不适用勾销"),
        ("W-P5", "慢漂未到位(架构属性)", "不消失", "到位判据按 runbook §3,不因慢漂判 W-A 失败"),
        ("W-P6", "EKF2-EV 域(route215016/w2b)", "不消失", "归 T1-E1;不入本门素材"),
        ("W-P7", "旧回放行代差", "不适用", "Y4 一律修复版二进制重放,旧行仅对照"),
    ]
    print("| 预言 | 内容 | 预期 | 勾销判据 | 状态 |")
    print("|---|---|---|---|---|")
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        obs_ok = all(r.get("verdict") == "PASS" for r in rows if r["tag"].startswith("Y4_"))
        base_ok = all(r.get("verdict") == "PASS" for r in rows if r["tag"].startswith("Y4B_"))
    else:
        obs_ok = base_ok = None
    for pid, content, expect, how in P:
        if pid == "W-P1" or pid == "W-P3":
            st = "待勾销" if obs_ok is None else ("✅ 已勾销" if obs_ok else "❌ 漏网")
        elif pid == "W-P2":
            st = "待勾销(prop 流 v_max 事后验)"
        elif pid in ("W-P4", "W-P5", "W-P6", "W-P7"):
            st = "—(按定义不适用勾销)"
        else:
            st = "待勾销"
        print(f"| {pid} | {content} | {expect} | {how} | {st} |")
    if base_ok is False:
        print("\n!! 双基线劣化=修复引入回归,立即通知 T2")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cfg", default=None, help="T2 修复版配置目录")
    ap.add_argument("--port", default="11313")
    ap.add_argument("--with-w2", action="store_true")
    ap.add_argument("--prophecy", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        cmd_dryrun(args.with_w2)
    elif args.prophecy:
        cmd_prophecy()
    elif args.cfg:
        cmd_run(args.cfg, args.port, args.with_w2)
    else:
        ap.error("需要 --dry-run / --cfg / --prophecy 之一")


if __name__ == "__main__":
    main()
