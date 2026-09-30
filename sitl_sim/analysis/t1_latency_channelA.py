#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# T1-P0D.1 / C10-X2 通道A：袋原生戳差延迟账（rosbag API 直读，禁 echo/禁回放域）
# 口径：diff = bag记录时刻 − header.stamp（逐条）；域自检：bag_t 若为 sim 域则
# clock-RTF≈1.000（此时 diff=RTF×真实墙延迟，须另取 gazebo RTF 归一，账内双列）。
import rosbag, json, sys, math

def pct(a, p):
    if not a: return None
    a = sorted(a); k = (len(a)-1) * p / 100.0
    f, c = int(math.floor(k)), int(math.ceil(k))
    return a[f] if f == c else a[f] + (a[c]-a[f]) * (k-f)

def stats_ms(vals_ms):
    if not vals_ms: return {"n": 0}
    return {"n": len(vals_ms),
            "p50": round(pct(vals_ms,50),3), "p90": round(pct(vals_ms,90),3),
            "p95": round(pct(vals_ms,95),3), "p99": round(pct(vals_ms,99),3),
            "max": round(max(vals_ms),3), "min": round(min(vals_ms),3)}

def gaps_ms(bts):
    return [(bts[i]-bts[i-1])*1000.0 for i in range(1,len(bts)) if bts[i] > bts[i-1]]

bag_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else None
TOP = {'prop':'/vins_estimator/imu_propagate', 'odom':'/vins_estimator/odometry',
       'lp':'/mavros/local_position/odom', 'imu':'/mavros/imu/data_raw', 'clock':'/clock'}
D = {k:[] for k in ('prop','odom','lp','imu')}
clock = []
with rosbag.Bag(bag_path) as bag:
    for topic, msg, t in bag.read_messages():
        bt = t.to_sec()
        if topic == TOP['clock']:
            cs = msg.clock.to_sec()
            if cs > 1.0: clock.append((bt, cs))
            continue
        for k, tp in TOP.items():
            if topic == tp and k != 'clock':
                st = msg.header.stamp.to_sec()
                if st > 1.0: D[k].append((bt, st))
                break

res = {"bag": bag_path, "streams": {}}
for k in ('prop','odom','lp','imu'):
    rows = D[k]
    if not rows: res["streams"][k] = {"n": 0}; continue
    bts = [r[0] for r in rows]; sts = [r[1] for r in rows]
    diffs = [(b-s)*1000.0 for b,s in rows]           # 采集项①: 戳差 ms
    g = gaps_ms(bts)                                  # 采集项④: 到达间隔
    sdt = gaps_ms(sts)                                # 戳域 dt（域自检对照）
    res["streams"][k] = {
        "n": len(rows),
        "span_stamp_s": round(sts[-1]-sts[0],3) if len(sts)>1 else 0,
        "stamp_dt_ms": stats_ms(sdt),
        "diff_ms": stats_ms(diffs),                   # 主分布（袋原生域）
        "arrival_gap_ms": stats_ms(g),
    }
# 采集项③: RTF（域自检：≈1.000 ⟹ bag_t 为 sim 域，账须双列）
if len(clock) > 10:
    b0,b1 = clock[0][0], clock[-1][0]; s0,s1 = clock[0][1], clock[-1][1]
    res["clock"] = {"n": len(clock),
                    "rtf_bagtime_sim": round((s1-s0)/(b1-b0), 4) if b1>b0 else None,
                    "clock_dt_ms": stats_ms(gaps_ms([c[1] for c in clock]))}
# 采集项⑤: 解龄代理 = prop 戳相对"录制序中已见最新 IMU 戳"的滞后（离线可测代理，口径注明）
imu_rows = D['imu']; prop_rows = D['prop']
if imu_rows and prop_rows:
    merged = sorted([(b,'imu',s) for b,s in imu_rows] + [(b,'prop',s) for b,s in prop_rows])
    latest = None; ages = []
    for b, kind, s in merged:
        if kind == 'imu': latest = s if latest is None else max(latest, s)
        elif latest is not None:
            a = (latest - s)*1000.0
            if a >= 0: ages.append(a)
    res["sol_age_proxy_ms"] = stats_ms(ages)

txt = json.dumps(res, indent=1, ensure_ascii=False)
print(txt[:3500])
if out_path:
    open(out_path,'w').write(txt)
    print("...written:", out_path)
