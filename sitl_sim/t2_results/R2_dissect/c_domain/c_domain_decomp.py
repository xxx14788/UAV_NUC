# -*- coding: utf-8 -*-
# T2 v8.9 单元 5.4: C 域误差源分解 — 距离-误差标度律 / 误差向量场方向性 / 停驻-途中分段 / 漂移谱
# 素材 = 健康轮组（VINS 域零事件）: A1/A2 (fixface-3+案A), 040932 (fixface-2), noise-R1 (零噪声), U3PO (obstacles)
import rosbag, math, os, statistics

ROUNDS = [
    ("A1_fixface3_caseA", "/home/uav/sitl_sim/bags/t2v3_route_024006.bag"),
    ("A2_fixface3_caseA", "/home/uav/sitl_sim/bags/t2v3_route_025808.bag"),
    ("H040932_fixface2", "/home/uav/sitl_sim/bags/t2v3_route_040932.bag"),
    ("U3PO_obstacles", "/home/uav/sitl_sim/vins_smoke_runs/run_U3PO_211438/flight.bag"),
    ("NR1_noiseoff", "/home/uav/sitl_sim/bags/t2v3_route_225254.bag"),
]
MODEL = "iris_stereo_vins"
OUT = "/home/uav/sitl_sim/t2_results/R2_dissect/c_domain"
os.makedirs(OUT, exist_ok=True)

def load(bag):
    b = rosbag.Bag(bag); truth = {}; odom = {}
    for topic, msg, t in b.read_messages(topics=["/gazebo/model_states", "/vins_estimator/imu_propagate"]):
        ts = round(t.to_sec(), 1)
        if topic == "/gazebo/model_states":
            try: i = msg.name.index(MODEL)
            except ValueError: continue
            p = msg.pose[i].position; truth[ts] = (p.x, p.y, p.z)
        else:
            p = msg.pose.pose.position; odom[ts] = (p.x, p.y, p.z)
    b.close()
    ts_common = sorted(set(truth) & set(odom))
    return [(t, truth[t], odom[t]) for t in ts_common]

rows = []
for name, bag in ROUNDS:
    if not os.path.exists(bag):
        rows.append((name, "MISSING")); continue
    data = load(bag)
    if len(data) < 50:
        rows.append((name, "TOO_SHORT")); continue
    # birth anchoring
    t0, tr0, od0 = data[0]
    off = tuple(od0[k] - tr0[k] for k in range(3))
    T = []; E = []; S = [0.0]
    for i, (t, tr, od) in enumerate(data):
        oc = tuple(od[k] - off[k] for k in range(3))
        e = tuple(oc[k] - tr[k] for k in range(3))
        T.append(t); E.append(e)
        if i:
            dt = T[i] - T[i-1]
            seg = math.dist(tr, data[i-1][1])
            S.append(S[-1] + seg)
    # 1. scale law: |e| = a*s + b  (least squares)
    n = len(S)
    sm = sum(S)/n; em = sum(math.dist(e,(0,0,0)) for e in E)/n
    cov = sum((S[i]-sm)*(math.dist(E[i],(0,0,0))-em) for i in range(n))
    var = sum((S[i]-sm)**2 for i in range(n))
    a = cov/var if var else 0.0
    b0 = em - a*sm
    ss_res = sum((math.dist(E[i],(0,0,0)) - (a*S[i]+b0))**2 for i in range(n))
    ss_tot = sum((math.dist(E[i],(0,0,0)) - em)**2 for i in range(n))
    r2 = 1 - ss_res/ss_tot if ss_tot else 0.0
    # 2. directionality: mean unit vector of e(t), magnitude = constancy
    ux = sum(e[0]/math.dist(e,(0,0,0)) for e in E if math.dist(e,(0,0,0))>1e-6)/n
    uy = sum(e[1]/math.dist(e,(0,0,0)) for e in E if math.dist(e,(0,0,0))>1e-6)/n
    uz = sum(e[2]/math.dist(e,(0,0,0)) for e in E if math.dist(e,(0,0,0))>1e-6)/n
    dir_const = math.dist((ux,uy,uz),(0,0,0))
    # 3. hover vs transit split (|v_truth| < 0.05 m/s = hover)
    mags = [math.dist(e,(0,0,0)) for e in E]
    hover_err_growth = 0.0; transit_err_growth = 0.0
    hv_n = 0; tr_n = 0
    for i in range(1, n):
        dt = T[i]-T[i-1]
        if dt <= 0: continue
        v = math.dist(data[i][1], data[i-1][1])/dt
        de = mags[i]-mags[i-1]
        if v < 0.05: hover_err_growth += de; hv_n += 1
        else: transit_err_growth += de; tr_n += 1
    total_growth = abs(hover_err_growth)+abs(transit_err_growth)
    hover_share = abs(hover_err_growth)/total_growth if total_growth else 0.0
    # 4. drift spectrum: end magnitude, growth rate, and first-half vs second-half means
    em_end = mags[-1]; em_max = max(mags)
    dur = T[-1]-T[0]
    rate = (mags[-1]-mags[0])/dur if dur else 0
    rows.append((name, "dur=%.0f n=%d | scale a=%.4g m/m b=%.3g R2=%.2f | dir_const=%.2f (%.2f,%.2f,%.2f) | hover_share=%.2f (hv_n=%d tr_n=%d) | |e|end=%.3f max=%.3f rate=%.4g m/s" %
                 (dur, n, a, b0, r2, dir_const, ux, uy, uz, hover_share, hv_n, tr_n, em_end, em_max, rate)))

with open(os.path.join(OUT, "decomposition.csv"), "w") as f:
    f.write("round,reading\n")
    for r in rows: f.write("%s,\"%s\"\n" % (r[0], r[1] if len(r)>1 else ""))
print("\n".join("%s: %s" % r for r in rows))
