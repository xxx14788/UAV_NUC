#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
t2_bias_probe.py -- T2 unit-1b step-0 probe: mavros bias topic validity (v1.0)

Taskbook: 2026-10-07_T2_vins_quality_v10.4.md unit 1b / unit 4.
Question (preregistered): does SITL mavros expose VALID EKF2 IMU-bias data
that a future IMU-CAL-FEED bridge could consume?

Validity = EXISTENCE + NONZERO + RATE + PLAUSIBILITY, all four, on at least
one carrier topic:
  carriers probed (in order):
    /mavros/imu/data                     (fused imu; some stacks zero bias)
    /mavros/imu/data_raw                 (raw; bias NOT subtracted -> baseline)
    /mavros/estimator_status             (if mavros exposes it)
    any topic whose type carries bias-ish fields (enumerated dynamically)

Usage (on 3090, with a live SITL+mavros running):
  ROS_MASTER_URI=... python3 t2_bias_probe.py [--duration 10] [--out json]

Exit codes: 0 = VALID bias data found (report written)
            1 = probed, NO valid carrier (negative result, still written)
            3 = hard error (no roscore / no mavros at all)

ASCII-only logs (CN-mojibake lesson).
"""

import argparse
import json
import sys
import time
from collections import defaultdict

BIAS_FIELD_HINTS = (
    "bias", "b_a", "b_g", "_ba", "_bg", "accel_bias", "gyro_bias",
)
# NOTE: bare 'ba'/'bg' matched 'battery' (sys_status false positive, 10-08
# step-0 lesson) -> hints now require word-ish boundaries.


def get_msg_class(type_str):
    """ROS1 noetic: rostopic has no get_message_class; use roslib."""
    from roslib.message import get_message_class as _gmc

    cls = _gmc(type_str)
    if cls is None:
        raise RuntimeError("cannot load type %s" % type_str)
    return cls


def ros_imports():
    import rospy
    import rostopic
    return rospy, rostopic


def topic_rate_and_samples(topic, msg_type, duration):
    """Subscribe, count messages, keep last sample per bias-ish field path."""
    import rospy

    counts = defaultdict(int)
    last_msg = {"t": None, "msg": None}
    sub = rospy.Subscriber(topic, msg_type, _mk_cb(counts, last_msg),
                           queue_size=50)
    t0 = time.time()
    while time.time() - t0 < duration and not rospy.is_shutdown():
        time.sleep(0.2)
    sub.unregister()
    dt = time.time() - t0
    return counts, last_msg, dt


def _mk_cb(counts, last_msg):
    def cb(msg):
        counts["n"] += 1
        last_msg["t"] = time.time()
        last_msg["msg"] = msg
    return cb


def extract_biasish(msg, prefix=""):
    """Return {field_path: value} for numeric leaves whose name hints bias."""
    out = {}
    slots = getattr(msg, "__slots__", [])
    for slot in slots:
        val = getattr(msg, slot, None)
        path = prefix + slot
        name = slot.lower()
        if any(h in name for h in BIAS_FIELD_HINTS):
            if isinstance(val, (int, float)):
                out[path] = val
            elif hasattr(val, "x") and hasattr(val, "y"):
                out[path] = [val.x, val.y, getattr(val, "z", None)]
        elif hasattr(val, "__slots__") and not isinstance(val, (int, float, str)):
            out.update(extract_biasish(val, path + "."))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=10.0)
    ap.add_argument("--out", default="t2_bias_probe_report.json")
    args = ap.parse_args()

    rospy, rostopic = ros_imports()
    rospy.init_node("t2_bias_probe", anonymous=True, disable_signals=True)

    try:
        import rosgraph
        master = rosgraph.Master("/t2_bias_probe")
        topics = master.getTopicTypes()
    except Exception as e:
        print("[hard] cannot reach roscore: %s" % e)
        return 3

    mavros_topics = sorted(
        [(t, ty) for (t, ty) in topics if "/mavros" in t])
    print("[info] %d mavros topics visible" % len(mavros_topics))
    if not mavros_topics:
        print("[result] NO mavros topics at all -- mavros not running?")
        return 1

    # candidate carriers: fixed list + dynamic (bias-ish slots via one sample)
    fixed = [
        "/mavros/imu/data",
        "/mavros/imu/data_raw",
        "/mavros/estimator_status",
    ]
    report = {"probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "duration_s": args.duration, "carriers": {}, "verdict": None}

    candidates = [ft for ft in mavros_topics if ft[0] in fixed]
    # dynamic scan: any /mavros topic of a type with bias-ish fields
    import rospy.msg
    for t, ty in mavros_topics:
        if (t, ty) in candidates:
            continue
        try:
            dummy = get_msg_class(ty)()
        except Exception:
            continue
        if extract_biasish(dummy):
            candidates.append((t, ty))

    any_valid = False
    for topic, ty in candidates:
        print("[probe] %s (%s)" % (topic, ty))
        try:
            msg_class = get_msg_class(ty)
        except Exception as e:
            report["carriers"][topic] = {"error": "type load: %s" % e}
            continue
        counts, last, dt = topic_rate_and_samples(topic, msg_class,
                                                  args.duration)
        n = counts["n"]
        hz = n / dt if dt > 0 else 0.0
        biasish = extract_biasish(last["msg"]) if last["msg"] else {}
        nonzero = any(
            (isinstance(v, list) and any(abs(x) > 1e-9 for x in v if x))
            or (isinstance(v, (int, float)) and abs(v) > 1e-9)
            for v in biasish.values())
        plausible = True
        for k, v in biasish.items():
            vals = v if isinstance(v, list) else [v]
            for x in vals:
                if x is None:
                    continue
                if "gyro" in k or k.endswith((".bg", ".b_g")) or "b_g" in k:
                    plausible = plausible and abs(x) < 0.05
                elif "accel" in k or "b_a" in k or k.endswith(".ba"):
                    plausible = plausible and abs(x) < 0.5
        valid = bool(biasish) and nonzero and hz >= 10.0 and plausible
        report["carriers"][topic] = {
            "type": ty,
            "rate_hz": round(hz, 2),
            "samples": n,
            "bias_fields": biasish,
            "nonzero": nonzero,
            "plausible": plausible,
            "valid": valid,
        }
        if valid:
            any_valid = True
        print("       hz=%.1f n=%d bias_fields=%d nonzero=%s valid=%s"
              % (hz, n, len(biasish), nonzero, valid))

    report["verdict"] = "VALID" if any_valid else "NO_VALID_CARRIER"
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)
    print("[result] %s -> %s" % (report["verdict"], args.out))
    return 0 if any_valid else 1


if __name__ == "__main__":
    sys.exit(main())
