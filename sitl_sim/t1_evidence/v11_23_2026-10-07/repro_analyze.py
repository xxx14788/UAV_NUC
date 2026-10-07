#!/usr/bin/env python3
"""1e 回放复现判读器 v1.0 (T1 v11.23 阶段1;判据=x4_bagench_design_v1 §3 预注册冻结逐字)
复现判定双指标: 跳变时刻对齐(±2s 或同里程±5%) + 跳幅量级带(>3x 幅差=形态漂移)
输入: 在线标本 flight.bag vs 回放 vins_out.bag; 10Hz odom |dP|>1m = 跳变事件(设计件原文)
"""
import sys, json
import rosbag

def read_stream(bag_path, topic):
    out = []
    with rosbag.Bag(bag_path, "r") as b:
        for t, m, ts in b.read_messages(topics=[topic]):
            p = m.pose.pose.position
            tt = ts.to_sec() if hasattr(ts, "to_sec") else ts/1e9
            out.append((tt, p.x, p.y, p.z))
    return out

def jumps(stream, th_m=1.0):
    """逐帧 |dP|>th_m 事件(10Hz odom 口径);返回 (max_jump, events[(t,i,dp)])"""
    ev = []
    mx = 0.0; mx_t = None
    for i in range(1, len(stream)):
        dt = (stream[i][1]-stream[i-1][1])**2 + (stream[i][2]-stream[i-1][2])**2 + (stream[i][3]-stream[i-1][3])**2
        dp = dt**0.5
        if dp > mx: mx, mx_t = dp, stream[i][0]
        if dp > th_m:
            ev.append((stream[i][0], i, round(dp,3)))
    return mx, mx_t, ev

def main():
    online_bag, replay_bag = sys.argv[1], sys.argv[2]
    r = {}
    on_odom = read_stream(online_bag, "/vins_estimator/odometry")
    rp_odom = read_stream(replay_bag, "/vins_estimator/odometry")
    on_mx, on_mxt, on_ev = jumps(on_odom)
    rp_mx, rp_mxt, rp_ev = jumps(rp_odom)
    r["online"] = {"n_odom": len(on_odom), "max_dP_m": round(on_mx,3), "t_max": on_mxt,
                   "n_events_gt1m": len(on_ev), "events": on_ev[:20],
                   "start": [round(v,3) for v in on_odom[0][1:]],
                   "end": [round(v,3) for v in on_odom[-1][1:]]}
    r["replay"] = {"n_odom": len(rp_odom), "max_dP_m": round(rp_mx,3), "t_max": rp_mxt,
                   "n_events_gt1m": len(rp_ev), "events": rp_ev[:20],
                   "start": [round(v,3) for v in rp_odom[0][1:]],
                   "end": [round(v,3) for v in rp_odom[-1][1:]]}
    # 轨迹复现度: 同 bag 时刻近配对 (在线 odom vs 回放 odom) 位置差
    import bisect
    ts_on = [q[0] for q in on_odom]
    diffs = []
    for q in rp_odom:
        j = bisect.bisect_left(ts_on, q[0])
        if j >= len(ts_on): break
        d = ((q[1]-on_odom[j][1])**2+(q[2]-on_odom[j][2])**2+(q[3]-on_odom[j][3])**2)**0.5
        diffs.append((q[0]-rp_odom[0][0], d))
    if diffs:
        dv = [d for _,d in diffs]
        r["traj_diff"] = {"n": len(dv), "p50": round(sorted(dv)[len(dv)//2],3),
                          "p95": round(sorted(dv)[int(len(dv)*0.95)-1],3),
                          "max": round(max(dv),3)}
        # 尾段(最后20%)均值差 = 终态漂移复现面
        tail = diffs[int(len(diffs)*0.8):]
        tv = [d for _,d in tail]
        r["traj_diff"]["tail_mean"] = round(sum(tv)/len(tv),3)
    print(json.dumps(r, indent=1))

if __name__ == "__main__":
    main()
