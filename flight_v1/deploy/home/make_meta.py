#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_meta.py -- 生成判据要求的 meta.json（2026-11-06）

为什么要有它：G2 要 `params_sha256` 一致、G7 要 `purpose`，判据里
`meta_schema.required` 缺一个字段整轮就不可判。手写必然填错或漏填。

用法（每飞完一轮跑一次）：
    ~/make_meta.py --round A --purpose v2_g1 --hover-s 65 \
                   --bat-before 16.62 --bat-after 15.91 --out ~/flight_data/20261107_101500

参数全部来自实测/现场，脚本只负责**如实记录**，不做任何推断。
`--purpose` 允许值见 `acceptance_v1.json` 的 meta_schema.purpose_values。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys

YAML = os.path.expanduser("~/catkin_ws/src/px4ctrl/config/ctrl_param_fpv.yaml")
GITDIR = os.path.expanduser("~/catkin_ws")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def params_hashes(path):
    """整文件哈希 + 去掉 ctrl_v2.enabled 之后的哈希。

    为什么两个都要：G2 要求"全程不改参数"，但 v2 轮与 legacy 轮的 enabled 天生不同。
    用 excl_v2 版本做跨轮比较，整文件哈希留作审计。
    """
    raw = open(path, "rb").read()
    full = sha256_bytes(raw)
    # 把 ctrl_v2 段里的 enabled 行统一成占位符再算一次
    out, in_v2 = [], False
    for line in io.open(path, encoding="utf-8").read().splitlines():
        if line.startswith("ctrl_v2:"):
            in_v2 = True
            out.append(line)
            continue
        if in_v2 and line and not line[0].isspace():
            in_v2 = False
        if in_v2 and line.strip().startswith("enabled:"):
            out.append("  enabled: <EXCLUDED>")
        else:
            out.append(line)
    excl = sha256_bytes(("\n".join(out) + "\n").encode("utf-8"))
    return full, excl


def git_head():
    try:
        return subprocess.check_output(["git", "-C", GITDIR, "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True, help="轮次代号，如 A / B / C / D")
    ap.add_argument("--purpose", required=True,
                    help="用途标签，必须与 acceptance_v1.json 的 purpose_values 一致")
    ap.add_argument("--hover-s", type=float, required=True, help="实际悬停时长（秒）")
    ap.add_argument("--bat-before", type=float, required=True, help="起飞前电压（V，万用表或地面站读数）")
    ap.add_argument("--bat-after", type=float, required=True, help="落地后电压（V）")
    ap.add_argument("--out", required=True, help="输出目录（与 flight.bag 同级）")
    ap.add_argument("--aborted", action="store_true")
    ap.add_argument("--abort-reason", default="")
    ap.add_argument("--yaml", default=YAML)
    a = ap.parse_args()

    if not os.path.exists(a.yaml):
        sys.exit("找不到 yaml: %s" % a.yaml)
    import yaml
    d = yaml.safe_load(io.open(a.yaml, encoding="utf-8"))
    full, excl = params_hashes(a.yaml)

    meta = {
        "round": a.round,
        "date": subprocess.check_output(["date", "+%Y-%m-%d"]).decode().strip(),
        "ctrl_v2_enabled": bool(d.get("ctrl_v2", {}).get("enabled", False)),
        "hover_percentage": float(d["thrust_model"]["hover_percentage"]),
        # 2026-11-06（AMENDMENT-008）：判据 G1 的 z 阈值是相对 aim=height+0.05 表达的，
        # 所以每轮必须记录本轮的目标高度，否则判据不知道按哪个高度算。
        "takeoff_height_m": float(d["auto_takeoff_land"]["takeoff_height"]),
        "battery_before_v": a.bat_before,
        "battery_after_v": a.bat_after,
        "params_sha256": full,
        "params_sha256_excl_v2": excl,
        "git_commit": git_head(),
        "purpose": a.purpose,
        "hover_target_s": a.hover_s,
        "aborted": bool(a.aborted),
        "abort_reason": a.abort_reason,
    }

    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, "meta.json")
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n")

    print("wrote %s" % p)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if a.bat_before < 15.0:
        print("\n⚠ 起飞前电压 %.2f < 15.0 V：G2 的 battery_min_v 会判 FAIL" % a.bat_before)
    if a.hover_s < 65.0:
        print("\n⚠ 悬停 %.1f s < 65 s：G3 的 60 s 窗口取不到，本轮 G3 记 NOT_EVALUABLE" % a.hover_s)


if __name__ == "__main__":
    main()
