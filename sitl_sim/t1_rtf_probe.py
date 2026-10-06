#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t1_rtf_probe.py — T1 v11.20 RTF 连续面探针(定因机械腿 L4 前瞻件,纯脚本面)
历史轮连续 sim/wall 曲线未录(定因表 L4 slack 注记)——本探针补齐 X4 批该面:
采样 /clock(sim) vs wall epoch,2s 一行 → <round>/rtf.tsv;离线差分 Δsim/Δwall=RTF 曲线。
vins_smoke.sh --gate 1 时随轮起/随轮清(cleanup pkill)。"""
import sys, os, time
try:
    import rospy
    from rosgraph_msgs.msg import Clock
except Exception as e:
    print("rtf_probe init fail:", e); sys.exit(0)
rd = sys.argv[1] if len(sys.argv) > 1 else "."
out = os.path.join(rd, "rtf.tsv")
state = {"sim": None}
def cb(m):
    state["sim"] = m.clock.to_sec()
rospy.init_node("t1_rtf_probe", disable_signals=True)
rospy.Subscriber("/clock", Clock, cb, queue_size=1)
with open(out, "w") as f:
    f.write("wall_epoch\tsim_t\n"); f.flush()
    r = rospy.Rate(0.5)
    while not rospy.is_shutdown():
        if state["sim"] is not None:
            f.write("%.3f\t%.3f\n" % (time.time(), state["sim"])); f.flush()
        try:
            r.sleep()
        except Exception:
            time.sleep(2)
