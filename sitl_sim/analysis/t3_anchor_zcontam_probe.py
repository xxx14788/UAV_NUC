#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X2g3 撞门机理验证(只读袋;0 锁;判读正源零触碰)。
假设:到位窗 0.849 = 物理 0.099 + anchor z 分量被 goal+5s 动态窗的 VINS z 高估污染
(全库出生偏移 z≈0.09,本轮 anchor z=0.814)。三口径对账+anchor 时变曲线。"""
import math, sys
import rosbag

D = sys.argv[1] if len(sys.argv) > 1 else "/home/ghj/sitl_sim/vins_smoke_runs/run_X2g3_025529"
GOAL = (8.0, -1.0, 1.0)

prop, truth, goals = [], [], []
with rosbag.Bag(D + "/flight.bag", "r") as b:
    for topic, msg, ts in b.read_messages(topics=[
            "/vins_estimator/imu_propagate", "/gazebo/model_states",
            "/move_base_simple/goal"]):
        t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
        if topic == "/vins_estimator/imu_propagate":
            p = msg.pose.pose.position
            prop.append((t, p.x, p.y, p.z))
        elif topic == "/gazebo/model_states":
            try:
                i = msg.name.index("iris_stereo_vins")
            except ValueError:
                continue
            p = msg.pose[i].position
            truth.append((t, p.x, p.y, p.z))
        else:
            goals.append((t, msg.pose.position.x, msg.pose.position.y, msg.pose.position.z))

g1_ts = next((g[0] for g in goals if abs(g[1]-GOAL[0]) < .01 and abs(g[2]-GOAL[1]) < .01), prop[0][0])

def near(arr, tt):
    return min(arr, key=lambda q: abs(q[0]-tt))

# round_result anchor 口径复刻:goal+5s 窗,prop 前 50 帧配 truth
pw = [p for p in prop if g1_ts <= p[0] <= g1_ts + 5]
tw = [near(truth, p[0]) for p in pw[:50]]
a_dyn = (sum(t[1] for t in tw)/len(tw) - sum(p[1] for p in pw[:50])/len(pw),
         sum(t[2] for t in tw)/len(tw) - sum(p[2] for p in pw[:50])/len(pw),
         sum(t[3] for t in tw)/len(tw) - sum(p[3] for p in pw[:50])/len(pw))
print("anchor(动态窗 goal+5s,round_result 口径复刻) = (%.3f, %.3f, %.3f) |a|=%.3f" % (*a_dyn, math.dist(a_dyn,(0,0,0))))

# 对照锚1:静止悬停段(goal 前盘旋段,取 g1_ts-15 ~ g1_ts-5)
pw0 = [p for p in prop if g1_ts-15 <= p[0] <= g1_ts-5]
tw0 = [near(truth, p[0]) for p in pw0[:50]]
a_st = tuple(sum(t[k] for t in tw0)/len(tw0) - sum(p[k] for p in pw0[:50])/len(pw0) for k in (1,2,3))
print("anchor(静止窗 goal-15~-5s)         = (%.3f, %.3f, %.3f) |a|=%.3f" % (*a_st, math.dist(a_st,(0,0,0))))
print("两锚差(动态-静止) = (%.3f, %.3f, %.3f) |d|=%.3f" % (
    a_dyn[0]-a_st[0], a_dyn[1]-a_st[1], a_dyn[2]-a_st[2],
    math.dist(a_dyn, a_st)))

# 到位三口径(goal 后全程窗,与 round_result 同窗)
t_end = truth[-1][0]
def leg_min(pts, ref, f, to):
    sel = [p for p in pts if f <= p[0] <= to]
    return min(math.dist((p[1],p[2],p[3]), ref) for p in sel)
ref_dyn = tuple(GOAL[k] + a_dyn[k] for k in range(3))
ref_st  = tuple(GOAL[k] + a_st[k]  for k in range(3))
d3_dyn  = leg_min(truth, ref_dyn, g1_ts, t_end)
d3_st   = leg_min(truth, ref_st,  g1_ts, t_end)
d_bare  = leg_min(truth, GOAL,    g1_ts, t_end)
print("到位 3D(动态锚/round_result 复刻) = %.3f  (RESULT=0.849)" % d3_dyn)
print("到位 3D(静止锚)                = %.3f" % d3_st)
print("到位 3D(裸 goal,无锚)          = %.3f  (ARRIVE_WATCH=0.099)" % d_bare)
print("锚 z 污染量化: 动态锚 z-静止锚 z = %.3f;√(d_bare²+Δz²)=%.3f (vs d3_dyn %.3f)" % (
    a_dyn[2]-a_st[2], math.hypot(d_bare, a_dyn[2]-a_st[2]), d3_dyn))

# anchor 时变(每 10s 窗均差,看动态段演化)
print("--- anchor 时变(10s 滑窗均差 x/y/z) ---")
t0 = prop[0][0]
for k in range(0, int(t_end - t0), 20):
    f, to = t0 + k, t0 + k + 10
    seg = [p for p in prop if f <= p[0] <= to]
    if len(seg) < 20:
        continue
    tg = [near(truth, p[0]) for p in seg[::10]]
    sg = seg[::10]
    ax = sum(q[1] for q in tg)/len(tg) - sum(q[1] for q in sg)/len(sg)
    ay = sum(q[2] for q in tg)/len(tg) - sum(q[2] for q in sg)/len(sg)
    az = sum(q[3] for q in tg)/len(tg) - sum(q[3] for q in sg)/len(sg)
    mark = " <-- goal+5s 动态窗" if f <= g1_ts + 5 <= to else ""
    print("t=%6.1f-%6.1f  a=(%6.3f,%6.3f,%6.3f)%s" % (f-t0, to-t0, ax, ay, az, mark))
