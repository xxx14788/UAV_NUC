#!/usr/bin/env python3
# t2_prodrome_scan.py — 跳变族前兆窗第一段粗扫(prereg 5583f526 冻结口径)
# usage: t2_prodrome_scan.py <round_dir>  → prodrome_scan.csv + stdout 摘要
import sys, os, re, struct, collections
rd = sys.argv[1]; bag = os.path.join(rd, "flight.bag")
log = os.path.join(rd, "simvins.log")
out = os.path.join(rd, "prodrome_scan.csv")
B = 5.0  # 桶宽 s
rows = collections.defaultdict(lambda: collections.defaultdict(list))
jumps = []
# --- bag 面: feature_pts + imu_propagate ---
import rosbag
last_p = None; last_t = None
with rosbag.Bag(bag) as b:
    for tp, msg, _ in b.read_messages(topics=["/vins_estimator/feature_pts", "/vins_estimator/imu_propagate"]):
        t = msg.header.stamp.to_sec()
        tb = int(t // B) * B
        if tp.endswith("feature_pts"):
            pts = []
            d = msg.data
            step = msg.point_step
            for off in range(0, len(d), step):
                x, y, z = struct.unpack_from("fff", d, off + msg.fields[0].offset if msg.fields[0].offset else off)
                pts.append((x, y, z))
            rows[tb]["M1_track"].append(len(pts))
            if pts:
                rows[tb]["M2_depth"].append(sorted((x*x+y*y+z*z) ** 0.5 for x, y, z in pts)[len(pts)//2])
                rows[tb]["M2_depth_p10"].append(sorted((x*x+y*y+z*z) ** 0.5 for x, y, z in pts)[max(0, len(pts)//10)])
            rows[tb]["_pts"].append(pts)
        else:
            p = (msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z)
            if last_p is not None and t > last_t:
                dj = sum((a-b)**2 for a, b in zip(p, last_p)) ** 0.5
                if dj >= 0.5:
                    jumps.append((t, dj))
            last_p, last_t = p, t
# --- log 面: [T2slv] cost + T2diag |Bas| ---
if os.path.exists(log):
    for line in open(log, errors="replace"):
        m = re.search(r"\[T2slv\] t=([0-9.]+).*init_cost=([0-9.e+-]+)", line)
        if m:
            rows[int(float(m.group(1)) // B) * B]["M4_cost"].append(abs(float(m.group(2))))
        m2 = re.search(r"\[T2diag\] t=([0-9.]+).*\|Bas\|=([0-9.e+-]+)", line)
        if m2:
            rows[int(float(m2.group(1)) // B) * B]["M5_bas"].append(float(m2.group(2)))
# M3 parallax proxy: 帧间特征云最近邻位移 p50(相邻帧桶内首末两帧)
def pctl(v, q):
    if not v: return ""
    v = sorted(v); return v[min(len(v)-1, int(q*len(v)))]
keys = sorted(rows)
with open(out, "w") as f:
    f.write("t,M1_track_p50,M1_track_p10,M2_depth_p50,M2_depth_p10,M3_para_p50,M4_cost_p50,M5_bas_p50,M6_jump_max,n_jumps_ge1m\n")
    for k in keys:
        r = rows[k]
        para = ""
        pl = r.get("_pts", [])
        if len(pl) >= 2:
            a, b_ = pl[0], pl[-1]
            if a and b_:
                ds = []
                for x, y, z in b_[:80]:
                    dmin = min((x-X)**2+(y-Y)**2+(z-Z)**2 for X, Y, Z in a[:80]) ** 0.5
                    ds.append(dmin)
                para = "%.4f" % pctl(ds, 0.5)
        f.write("%d,%.1f,%.1f,%.3f,%.3f,%s,%.6g,%.4f,%.3f,%d\n" % (
            k, pctl(r.get("M1_track", []), .5) or -1, pctl(r.get("M1_track", []), .1) or -1,
            pctl(r.get("M2_depth", []), .5) or -1, pctl(r.get("M2_depth_p10", []), .5) or -1,
            para, pctl(r.get("M4_cost", []), .5) or -1, pctl(r.get("M5_bas", []), .5) or -1,
            max([j for t, j in jumps if k <= t < k+B] or [0]), len([1 for t, j in jumps if k <= t < k+B])))
print("SCAN %s buckets=%d jumps_ge1m=%d" % (os.path.basename(rd), len(keys), len(jumps)))
for t, j in jumps[:6]: print("  jump %.3fm @t=%.2f (t%%1000=%.2f)" % (j, t, t % 1000))
