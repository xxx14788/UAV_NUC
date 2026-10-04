#!/usr/bin/env python3
# h5_actuators.py — PX4-side truth: actuator_outputs + status flags timeline
import sys

from pyulog import ULog

u = ULog(sys.argv[1], None)
dl = u.data_list


def get(name):
    return [d for d in dl if d.name == name]


ao = get("actuator_outputs")
print("actuator_outputs instances:", [d.multi_id for d in ao])
if ao:
    d = ao[0].data
    ts = [float(x) for x in d["timestamp"]]
    t0 = ts[0]
    # motor channels typically output[0..3] for quad
    print("bin  n  out0_p50  out0_max  out1_p50  (per 5s)")
    bins = {}
    for i, t in enumerate(ts):
        bins.setdefault(int((t - t0) / 5e6), []).append(i)
    for b in sorted(bins)[:14]:
        idx = bins[b]
        try:
            o0 = sorted(float(d["output[0]"][i]) for i in idx)
            o1 = sorted(float(d["output[1]"][i]) for i in idx)
            print("%3d %4d %8.1f %8.1f %8.1f" % (
                b * 5, len(idx), o0[len(o0) // 2], o0[-1], o1[len(o1) // 2]))
        except KeyError:
            ks = [k for k in d.keys() if "output" in k][:4]
            print("keys:", ks)
            break
vs = get("vehicle_status")
if vs:
    d = vs[0].data
    ts = [float(x) for x in d["timestamp"]]
    t0 = ts[0]
    for i, t in enumerate(ts):
        armed = d["arming_state"][i]
        nav = d["nav_state"][i]
        if i == 0 or (i > 0 and (armed != d["arming_state"][i - 1] or nav != d["nav_state"][i - 1])):
            print("status t=%.1fs arming=%d nav=%d" % ((t - t0) / 1e6, armed, nav))
