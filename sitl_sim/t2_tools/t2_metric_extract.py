#!/usr/bin/env python3
"""t2_metric_extract.py -- extract [T2IQG-METRIC] lines to CSV (T2 v10.4 1a).
usage: t2_metric_extract.py <run_dir>... > out.csv
columns: run,t,corners,depth_r,stereo_r
"""
import csv, glob, os, re, sys
RE = re.compile(r"\[T2IQG-METRIC\] t=([\d.]+) corners=(\d+) depth_r=([\d.]+) stereo_r=([\d.]+)")
w = csv.writer(sys.stdout)
w.writerow(["run", "t", "corners", "depth_r", "stereo_r"])
for rd in sys.argv[1:]:
    run = os.path.basename(rd.rstrip("/"))
    for line in open(os.path.join(rd, "simvins.log"), errors="replace"):
        m = RE.search(line)
        if m:
            w.writerow([run] + list(m.groups()))
