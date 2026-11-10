#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stream_health.py - 门触发时判定"VINS 流是否还值得信"，决定中止走哪条降级路径。

用途：vins_smoke.sh 的前兆门/止损门触发后，中止链路要二选一：
      ① odom 仍可信 -> 用正常 LAND 让它自己降下来
      ② 流已断/滞后 -> 悬停后杀电机（LAND 不可靠）
      判据 = 证据 json 里的 vins_stream.gap_s 是否 > 10 s。

为什么单独成文件（2026-11-10 整改 F-02）：
      原实现是 shell 里的 heredoc，`python3 - "$EV"` 只传了 1 个实参却读 sys.argv[3]
      -> IndexError 被 $(...) 吞掉 -> 输出为空 -> 条件恒假 -> **降级① 从未执行过一次**，
      每一轮门触发都直接杀电机。抽成文件 + argparse 后参数错会立刻报错，不可能静默。

用法：stream_health.py --ev <证据目录> --prefix <gatehit|stoploss> [--json] [--selftest]
输出：stdout 仅 "1"（流可信 -> 走 LAND）或 "0"（流断 -> 走 KILL）
退出码：0 = 判定成功（结果在 stdout）；2 = 输入错误（目录不存在/参数错）。
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GAP_LIMIT_S = 10.0


def read_gaps(ev_dir, prefix):
    """返回 (gaps, files)：从 <ev>/<prefix>_*.json 里取 vins_stream.gap_s。"""
    gaps, files = [], []
    for path in sorted(glob.glob(os.path.join(ev_dir, prefix + "_*.json"))):
        files.append(os.path.basename(path))
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue  # 单文件坏了不影响其它证据
        stream = doc.get("vins_stream") or {}
        gap = stream.get("gap_s")
        if isinstance(gap, (int, float)):
            gaps.append(float(gap))
    return gaps, files


def verdict(ev_dir, prefix):
    if not os.path.isdir(ev_dir):
        raise ValueError("证据目录不存在: %s" % ev_dir)
    gaps, files = read_gaps(ev_dir, prefix)
    # 没有任何证据 -> 保持**旧语义**返回 1（尝试 LAND）。
    # 2026-11-10（盲评修复）：我一度改成 0(KILL)，但"证据缺失"不等于"流已断"；
    # 空中优先尝试受控降落（HAFIX 梯①的设计意图），杀电机是最后手段，不该由缺证据触发。
    if not files:
        return 1, {"gaps": [], "files": [], "reason": "no evidence files -> attempt LAND (legacy)"}
    bad = [g for g in gaps if g > GAP_LIMIT_S]
    if bad:
        return 0, {"gaps": gaps, "files": files, "reason": "gap %.1fs > %.1fs" % (max(bad), GAP_LIMIT_S)}
    return 1, {"gaps": gaps, "files": files, "reason": "all gaps <= %.1fs" % GAP_LIMIT_S}


def selftest():
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".stream_health_selftest")
    shutil.rmtree(tmp, ignore_errors=True)
    passed = total = 0
    failures = []

    def check(name, cond, detail):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
        else:
            failures.append("%s: %s" % (name, detail))

    def run(args):
        return subprocess.run([sys.executable, os.path.abspath(__file__)] + args,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    # 用例 1: 流健康（gap 2s）-> 1
    d1 = os.path.join(tmp, "healthy")
    os.makedirs(d1)
    with open(os.path.join(d1, "gatehit_t.json"), "w", encoding="utf-8") as fh:
        json.dump({"vins_stream": {"gap_s": 2.0}}, fh)
    p = run(["--ev", d1, "--prefix", "gatehit"])
    check("healthy/rc", p.returncode == 0, "rc=%d stderr=%s" % (p.returncode, p.stderr.strip()))
    check("healthy/out", p.stdout.strip() == "1", "stdout=%r" % p.stdout.strip())

    # 用例 2: 流断（gap 30s）-> 0
    d2 = os.path.join(tmp, "broken")
    os.makedirs(d2)
    with open(os.path.join(d2, "gatehit_t.json"), "w", encoding="utf-8") as fh:
        json.dump({"vins_stream": {"gap_s": 30.0}}, fh)
    p = run(["--ev", d2, "--prefix", "gatehit"])
    check("broken/out", p.stdout.strip() == "0", "stdout=%r" % p.stdout.strip())

    # 用例 3: 无证据文件 -> 1（保持旧语义：尝试 LAND，不因缺证据就杀电机）
    d3 = os.path.join(tmp, "empty")
    os.makedirs(d3)
    p = run(["--ev", d3, "--prefix", "gatehit"])
    check("empty/out", p.stdout.strip() == "1", "stdout=%r" % p.stdout.strip())

    # 用例 4: 目录不存在 -> exit 2（不许静默）
    p = run(["--ev", os.path.join(tmp, "nope"), "--prefix", "gatehit"])
    check("missing/rc", p.returncode == 2, "rc=%d" % p.returncode)

    # 用例 5: 坏 json 被跳过，其它证据仍生效
    d5 = os.path.join(tmp, "mixed")
    os.makedirs(d5)
    with open(os.path.join(d5, "gatehit_bad.json"), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    with open(os.path.join(d5, "gatehit_ok.json"), "w", encoding="utf-8") as fh:
        json.dump({"vins_stream": {"gap_s": 1.0}}, fh)
    p = run(["--ev", d5, "--prefix", "gatehit"])
    check("mixed/out", p.stdout.strip() == "1", "stdout=%r" % p.stdout.strip())

    shutil.rmtree(tmp, ignore_errors=True)
    if failures:
        print("SELFTEST FAIL %d/%d" % (total - passed, total))
        for item in failures:
            print("  - " + item)
        return 1
    print("SELFTEST PASS %d/%d" % (passed, total))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="门触发时判定 VINS 流可信度：1=可信(走 LAND) / 0=流断(走 KILL)")
    ap.add_argument("--ev", help="证据目录（含 <prefix>_*.json）")
    ap.add_argument("--prefix", default="gatehit", help="证据前缀：gatehit 或 stoploss")
    ap.add_argument("--json", action="store_true", help="附带一行 JSON 细节到 stderr")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.ev:
        print("ERROR: --ev 必填", file=sys.stderr)
        return 2
    if args.prefix not in ("gatehit", "stoploss"):
        print("ERROR: --prefix 只接受 gatehit/stoploss，收到 %r" % args.prefix, file=sys.stderr)
        return 2
    try:
        code, detail = verdict(args.ev, args.prefix)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    print(code)
    if args.json:
        print(json.dumps(detail, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
