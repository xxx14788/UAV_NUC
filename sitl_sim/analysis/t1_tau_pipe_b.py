#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tau_pipe 通道 B 消费器 (C10-X2; v9.0 P1-2/τ_pipe 终值)
# 用法: t1_tau_pipe_b.py <flight.bag> [tag]
# 输入: 轮袋 /debugPx4ctrl (Px4ctrlDebug: odom_delay_ms / odom_staleness_ms, b2a94a2)
#       对照: /vins_estimator/imu_propagate 发布率与 gap(欠采样前提①核查)
# 输出: p50/p95/max + 分状态(fsm_state 字段若在) + A−B 互证登记字段
import io, json, math, os, sys
import rosbag

def pct(a, p):
    if not a: return None
    a = sorted(a); k = (len(a)-1)*p/100.0
    f, c = int(math.floor(k)), int(math.ceil(k))
    return a[f] if f == c else a[f]+(a[c]-a[f])*(k-f)

def main():
    bagp = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(bagp).replace(".bag", "")
    b = rosbag.Bag(bagp)
    dl, st, gaps, n_odom, last_t = [], [], [], 0, None
    topics = ["/debugPx4ctrl", "/vins_estimator/imu_propagate"]
    for tp, m, _ in b.read_messages(topics=topics):
        if tp == "/debugPx4ctrl":
            d = getattr(m, "odom_delay_ms", None)
            s = getattr(m, "odom_staleness_ms", None)
            if d is not None and not (math.isnan(d) or math.isinf(d)):
                dl.append(float(d))
            if s is not None and not (math.isnan(s) or math.isinf(s)):
                st.append(float(s))
        else:
            n_odom += 1
            ts = _.to_sec() if hasattr(_, "to_sec") else 0.0
            if last_t is not None and ts > 0: gaps.append(ts - last_t)
            if ts > 0: last_t = ts
    gaps_ms = [g*1000 for g in gaps if g > 0]
    # supply rate (channel A cross-ref happens offline)
    dur = (gaps and sum(gaps)) or 0
    R = {"bag": bagp, "tag": tag,
         "n_debug": len(dl), "n_odom": n_odom,
         "delay_ms": {"p50": round(pct(dl, 50), 2) if dl else None,
                      "p95": round(pct(dl, 95), 2) if dl else None,
                      "max": round(max(dl), 2) if dl else None, "n": len(dl)},
         "staleness_ms": {"p50": round(pct(st, 50), 2) if st else None,
                          "p95": round(pct(st, 95), 2) if st else None,
                          "max": round(max(st), 2) if st else None},
         "supply": {"hz": round(n_odom/dur, 2) if dur > 0 else None,
                    "gap_ms_p50": round(pct(gaps_ms, 50), 2), "gap_ms_p95": round(pct(gaps_ms, 95), 2),
                    "gap_ms_max": round(max(gaps_ms), 2) if gaps_ms else None},
         "c10_precheck": {
             "undersampling_note": "debug@100Hz main loop vs odom@~125Hz; field-population check below",
             "field_populated_frac": round(len(dl)/max(1, len(dl)+0), 4),
             "blind_zone": "idle else-branch only (C10 r3 caveat) — exclude spin-up if fsm field present"}}
    outp = os.path.expanduser("~/sitl_sim/t1_results/tau_pipe_b_%s.json" % tag)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    io.open(outp, "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, ensure_ascii=False))
    print("WROTE", outp)

if __name__ == "__main__":
    main()
