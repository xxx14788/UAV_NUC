#!/usr/bin/env python3
# T2-U2 逐袋法证提取 (2026-10-01): 消费 t3_replay 产出目录, 输出汇总 JSON+CSV
import json, os, re, subprocess, sys

RES = os.path.expanduser("~/sitl_sim/t3_results")
DIRS = [
    "Y4_X1final_173345_flight",
    "Y4_X1img_015950_flight",
    "Y4B_CTRL2_route112652_t2v3_route_1126252",  # placeholder, fixed below
    "Y4B_CTRL2_route112652_t2v3_route_112652x",
]
# 用 glob 精确定位
import glob
targets = []
for tag in ["Y4_X1final_173345", "Y4_X1img_015950", "Y4B_CTRL2_route112652",
            "Y4B_hover_203248", "Y4W_t2w5_p1b_shift", "Y4W_t2w5_p2_215545", "Y4W_t2v3_w2b_121141"]:
    g = glob.glob(os.path.join(RES, tag + "_*"))
    if g:
        targets.append((tag, g[0]))

RE_BGS = re.compile(r"Bgs=\[([-0-9.e]+) ([-0-9.e]+) ([-0-9.e]+)\]")
RE_BAS = re.compile(r"\|Bas\|=([-0-9.e]+)")

rows = []
for tag, d in targets:
    row = {"tag": tag, "dir": os.path.basename(d)}
    alive_f = os.path.join(d, "vins_alive.txt")
    row["alive"] = open(alive_f).read().strip() if os.path.exists(alive_f) else "?"
    log = os.path.join(d, "vins.log")
    fails, bas_max, bgs_frames_gt01, diag_last, n_diag = [], 0.0, 0, "", 0
    if os.path.exists(log):
        for line in open(log, errors="replace"):
            if "failure detection" in line:
                m = re.search(r"(\d+\.\d+)\]?: failure", line)
                fails.append(m.group(1) if m else "?")
            m = RE_BAS.search(line)
            if m:
                bas_max = max(bas_max, abs(float(m.group(1))))
            m = RE_BGS.search(line)
            if m and any(abs(float(x)) > 0.01 for x in m.groups()):
                bgs_frames_gt01 += 1
            if line.startswith("[T2diag]"):
                diag_last = line.strip(); n_diag += 1
    row["failure_n"] = len(fails)
    row["failure_ts"] = ",".join(fails[:8])
    row["bas_max"] = round(bas_max, 4)
    row["bgs_gt01_frames"] = bgs_frames_gt01
    row["diag_n"] = n_diag
    row["diag_last"] = diag_last[-160:]
    # odom 覆盖
    out_bag = os.path.join(d, "vins_out.bag")
    if os.path.exists(out_bag):
        try:
            y = subprocess.run(["rosbag", "info", "--yaml", out_bag],
                               capture_output=True, text=True, timeout=120).stdout
            msgs = dur = end = None
            for ln in y.splitlines():
                if ln.startswith("duration:"): dur = float(ln.split()[1])
                if "odometry" in ln and "msgs" in ln:
                    msgs = int(re.search(r"(\d+) msgs", ln).group(1))
                if ln.startswith("end:"):
                    m = re.search(r"\(([-0-9.]+)\)", ln); end = m and float(m.group(1))
            row["odom_msgs"], row["out_dur_s"], row["out_end_t"] = msgs, dur, end
        except Exception as e:
            row["odom_msgs"] = f"ERR:{e}"
    rows.append(row)

out_json = os.path.expanduser("~/sitl_sim/t2_u2_forensics.json")
json.dump(rows, open(out_json, "w"), ensure_ascii=False, indent=1)
hdr = ["tag", "alive", "failure_n", "failure_ts", "bas_max", "bgs_gt01_frames",
       "odom_msgs", "out_dur_s", "out_end_t", "diag_n"]
print("\t".join(hdr))
for r in rows:
    print("\t".join(str(r.get(h, "")) for h in hdr))
print(f"[u2-forensics] -> {out_json}")
