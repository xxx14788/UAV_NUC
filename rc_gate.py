#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RC 闸门的**唯一实现**（2026-11-08 用户令④）。

preflight.sh §9 与 flight_mission.py 都走这一份：判据（四杆居中容差、CH5 下限、
通道数）全部读契约 runtime.rc，不再各写一遍。

用法：python3 rc_gate.py            # 读 /mavros/rc/in 判一次，0=过 1=不过
      python3 rc_gate.py 1500 1501 ...   # 直接判给定的通道值（测试用）
"""
import os
import re
import subprocess
import sys


def load_thresholds():
    fv = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(fv, "contract", "flight_contract.yaml")
    try:
        import yaml
        with open(path, encoding="utf-8") as fh:
            rc = (yaml.safe_load(fh) or {}).get("runtime", {}).get("rc", {})
        return (int(rc.get("channels", 8)), int(rc.get("centered_tol", 125)),
                int(rc.get("ch5_min", 1750)))
    except Exception:
        return 8, 125, 1750


def read_channels():
    try:
        out = subprocess.run(["rostopic", "echo", "-n1", "/mavros/rc/in"],
                             capture_output=True, text=True, timeout=8).stdout
    except Exception:
        out = ""
    m = re.search(r"channels:\s*\[([^\]]*)\]", out)
    if not m:
        return None
    return [float(x) for x in m.group(1).replace(" ", "").split(",") if x]


def main():
    need, tol, ch5_min = load_thresholds()
    if len(sys.argv) > 1:
        ch = [float(x) for x in sys.argv[1:]]
    else:
        ch = read_channels()
        if not ch:
            print("  [FAIL] 读不到 /mavros/rc/in 的 channels（RC 未上电？）")
            return 1
    bad = []
    if len(ch) < need:
        bad.append("通道数 %d < %d" % (len(ch), need))
    elif any(x < 800 or x > 2200 for x in ch[:need]):
        bad.append("通道值超出 800-2200")
    else:
        if any(abs(x - 1500) > tol for x in ch[:4]):
            bad.append("四杆未居中 %s（容差 ±%d，OFFBOARD 要求）"
                       % ([round(x) for x in ch[:4]], tol))
        if ch[4] <= ch5_min:
            bad.append("CH5 不在悬停档（%.0f <= %d）" % (ch[4], ch5_min))
    if bad:
        print("  [FAIL] " + "；".join(bad))
        return 1
    print("  [ OK ] RC %d 通道有效、四杆居中(±%d)、CH5=%.0f > %d（CH6 不参与）"
          % (need, tol, ch[4], ch5_min))
    return 0


if __name__ == "__main__":
    sys.exit(main())
