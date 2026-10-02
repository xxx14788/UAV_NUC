#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""受控层边界单测补充(T3 池件 P-L):多 fire/钟缺失/袋缺失三条合成反例。
在 SYN 生成器(t3_synth_controlled_test.py 的 make_bag/make_run 复用思路)上扩三例:
  SYN_MULTI : 两次 fire(50/80s),odom 全程健康 → 期望 controlled(首触发定窗;fires_n=2)
  SYN_NOTC  : fire 行存在但 WARN 头损坏(无 sim 钟可提取) → t_fire=None → 窗不可建
              → 跳转全计窗外=0、L2a/L2b 无窗可判(None/False) → triggered-no-recovery
  SYN_NOBAG : fire 行正常但 flight.bag 缺失 → 袋面不可判 → triggered-no-recovery(证据=无袋)
判读走 wa_gate --online --skip-forensics;产线=SYN_CTRL 族同款。"""
import json
import os
import subprocess
import sys

BASE = os.path.expanduser("~/sitl_sim/t3_results/x11_dryrun_v11")


def main():
    # 复用已验证的生成器内部(同目录导入)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "synthctl", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "t3_synth_controlled_test.py"))
    # 该脚本 import rosbag 需 ROS 环境——直接内联三例构造(bag 复用 SYN_CTRL 的即可)
    import shutil
    cases = []
    # 例1: 双 fire(日志层叠加一行), 袋=SYN_CTRL 的健康袋
    d1 = os.path.join(BASE, "SYN_MULTI")
    os.makedirs(d1, exist_ok=True)
    if not os.path.exists(os.path.join(d1, "flight.bag")):
        os.link(os.path.join(BASE, "SYN_CTRL", "flight.bag"),
                os.path.join(d1, "flight.bag"))
    with open(os.path.join(d1, "simvins.log"), "w") as f:
        f.write("[33m[WARN] [1790880000.0, 50.000000000]: "
                "cost gate: streak=5 over 10.0x short-window median, reboot[0m\n")
        f.write("[33m[WARN] [1790880000.0, 80.000000000]: "
                "cost gate: streak=6 over 12.0x short-window median, reboot[0m\n")
    open(os.path.join(d1, "round.log"), "w").write(
        "[00:00:01] SITL up (sitl_world_obstacles)\n")
    shutil.copy(os.path.join(BASE, "SYN_CTRL", "RESULT.txt"),
                os.path.join(d1, "RESULT.txt"))
    cases.append(("SYN_MULTI", "controlled"))
    # 例2: fire 行 WARN 头无 sim 钟(手写畸形头)
    d2 = os.path.join(BASE, "SYN_NOTC")
    os.makedirs(d2, exist_ok=True)
    if not os.path.exists(os.path.join(d2, "flight.bag")):
        os.link(os.path.join(BASE, "SYN_CTRL", "flight.bag"),
                os.path.join(d2, "flight.bag"))
    with open(os.path.join(d2, "simvins.log"), "w") as f:
        f.write("[33m[WARN]: cost gate: streak=5 over 10.0x "
                "short-window median, reboot[0m\n")
    open(os.path.join(d2, "round.log"), "w").write(
        "[00:00:01] SITL up (sitl_world_obstacles)\n")
    shutil.copy(os.path.join(BASE, "SYN_CTRL", "RESULT.txt"),
                os.path.join(d2, "RESULT.txt"))
    cases.append(("SYN_NOTC", "triggered-no-recovery"))
    # 例3: fire 正常但无袋
    d3 = os.path.join(BASE, "SYN_NOBAG")
    os.makedirs(d3, exist_ok=True)
    with open(os.path.join(d3, "simvins.log"), "w") as f:
        f.write("[33m[WARN] [1790880000.0, 50.000000000]: "
                "cost gate: streak=5 over 10.0x short-window median, reboot[0m\n")
    open(os.path.join(d3, "round.log"), "w").write(
        "[00:00:01] SITL up (sitl_world_obstacles)\n")
    shutil.copy(os.path.join(BASE, "SYN_CTRL", "RESULT.txt"),
                os.path.join(d3, "RESULT.txt"))
    cases.append(("SYN_NOBAG", "triggered-no-recovery"))
    ok_all = True
    for name, want in cases:
        d = os.path.join(BASE, name)
        r = subprocess.run([sys.executable,
                            os.path.expanduser("~/catkin_ws/sitl_sim/analysis/t3_wa_gate.py"),
                            "--online", "--skip-forensics", d],
                           capture_output=True, text=True)
        j = json.load(open(os.path.join(d, "wa_gate_online.json")))
        c = j["controlled"]
        got = c["state"]
        ok = got == want
        ok_all = ok_all and ok
        print("%s: state=%s fires_n=%s t=%s L2a=%s L2b=%s jumps=%s/%s → %s"
              % (name, got, c["fires_n"], c["first_fire_t"], c["l2a_pass"],
                 c["l2b_pass"], c["jumps_in"], c["jumps_out"],
                 "MATCH" if ok else "MISMATCH-want-%s" % want))
    print("[P-L] %s" % ("PASS" if ok_all else "FAIL"))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
