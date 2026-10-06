#!/usr/bin/env python3
# t1_x5_passmap.py — X5 剂量-稳定性 passmap 构建器(任务书 v11.17 §4.1;设计文 §C v1.1 列集)
# usage: python3 t1_x5_passmap.py  → x5_passmap.csv(全 X5 轮:方向/距离/world/门/四指标/jump/j0
#   /gyr_peak/acc_peak[T2diag 同源袋侧 IMU 峰值]/名义剖面/跳变前兆签名行)
import glob, os, re, csv, subprocess, sys, collections
import rosbag
ROOT = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv")
DIRS = {"E":(1,0),"W":(-1,0),"N":(0,1),"S":(0,-1),"SE":(0.7071067811865476,-0.7071067811865476),"NE":(0.7071067811865476,0.7071067811865476)}
def parse_tag(tag):
    m = re.match(r"X5_([A-Z]+)(\d+)([OP])(?:_(R2|L2H))?", tag)
    if not m: return None
    return m.group(1), int(m.group(2)), m.group(3), m.group(4) or ""
def peak_imu(bagp):
    gmax = amax = 0.0
    with rosbag.Bag(bagp) as b:
        for tp, msg, _ in b.read_messages(topics=["/mavros/imu/data_raw"]):
            w = msg.angular_velocity; a = msg.linear_acceleration
            g = (w.x*w.x+w.y*w.y+w.z*w.z)**.5; ac = (a.x*a.x+a.y*a.y+a.z*a.z)**.5
            if g > gmax: gmax = g
            if ac > amax: amax = ac
    return gmax, amax
rows = []
for d in sorted(glob.glob(os.path.join(ROOT, "run_X5_*"))):
    tag = os.path.basename(d)[4:].rsplit("_", 1)[0]
    m = parse_tag(tag)
    res = os.path.join(d, "RESULT.txt")
    if not m or not os.path.exists(res): continue
    dn, dist, ws, suffix = m
    txt = open(res, errors="replace").read()
    def g1(pat, default=-1):
        mm = re.search(pat, txt)
        return float(mm.group(1)) if mm else default
    jump = g1(r"pre-post\|=[0-9.]+")
    arr = g1(r"leg1 到位\(真值\) min=([0-9.-]+)")
    avd = g1(r"避障 min_dist=([0-9.-]+)")
    hz = g1(r"poscmd ([0-9.]+) Hz")
    dis = g1(r"auto_disarm->([01])")
    resv = "PASS" if "RESULT=PASS" in txt else ("FAIL" if "RESULT=FAIL" in txt else "?")
    world = "obstacles" if ws == "O" else "plain"
    gate = 0.75 if ws == "O" else 0.5
    gy = ac = -1
    bagp = os.path.join(d, "flight.bag")
    if os.path.exists(bagp):
        try: gy, ac = peak_imu(bagp)
        except Exception: pass
    pro = "mild" if (dn in ("E","W","N") and world=="plain") else ("std" if (dn in ("SE","S") and world=="obstacles") else "-")
    rows.append([tag, dn, dist, world, gate, suffix, resv, arr, jump, avd, hz, dis, "%.2f"%gy, "%.2f"%ac, pro, os.path.basename(d)])
rows.sort(key=lambda r: (r[1], r[2], r[3]))
with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["tag","direction","distance_m","world","gate","variant","result","arrive_truth","jump_prepost","avoid_mindist","poscmd_hz","disarm","gyr_peak","acc_peak","profile","run_dir"])
    w.writerows(rows)
print("PASSMAP rows=%d -> %s" % (len(rows), OUT))
