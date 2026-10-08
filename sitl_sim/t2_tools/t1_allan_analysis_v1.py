#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t1_allan_analysis_v1.py -- Allan variance analysis for mavros IMU bag (2a-3, note-A)
Usage: t1_allan_analysis_v1.py <bag> [--topic /mavros/imu/data_raw] [--skip-head 1500] [--out outdir]
Outputs: allan curves (tau, sigma) per axis + fitted noise params vs upstream quadruple.
Upstream quadruple (config v0): acc_n=0.1 gyr_n=0.01 acc_w=0.001 gyr_w=0.0001
Fit model: sigma(tau) = sqrt(C0/tau^2 + C/tau + R)  (quantization/white-noise/rate-random-walk
linearized on log-log via 3 anchor slopes: -1 (angle RW->noise density), +1/2 missing -> use
standard anchors: white noise at slope -1/2, bias instability at min, RW at +1/2).
"""
import sys, os, argparse
import numpy as np


def load_imu(bag_path, topic, t0_skip_s):
    import rosbag
    t, w, a = [], [], []
    with rosbag.Bag(bag_path, "r") as b:
        for tp, msg, ts in b.read_messages(topics=[topic]):
            if hasattr(msg, "angular_velocity"):
                t.append(msg.header.stamp.to_sec() if msg.header.stamp.to_sec() > 1e9 else ts.to_sec())
                w.append([msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z])
                a.append([msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z])
    t = np.array(t); w = np.array(w); a = np.array(a)
    i0 = np.searchsorted(t, t[0] + t0_skip_s)
    return t[i0:], w[i0:], a[i0:]


def allan_dev(x, t, taus):
    """Overlapping Allan deviation of rate samples (x) with timestamps t."""
    dt = np.median(np.diff(t))
    n = len(x)
    ad = np.empty(len(taus)); ad[:] = np.nan
    # cluster counts m for each tau
    for i, tau in enumerate(taus):
        m = max(1, int(round(tau / dt)))
        if 2 * m > n:
            continue
        # average over clusters of m samples (rectangular)
        c = np.cumsum(np.insert(x, 0, 0.0))
        means = (c[m:] - c[:-m]) / m          # n-m+1 block means
        d = np.diff(means)[::1]               # successive block-mean differences (stride 1 = overlapping)
        if len(d) < 2:
            continue
        ad[i] = 0.5 * np.sqrt(np.mean(d ** 2) / (m * dt) ** 2) * np.sqrt(m * dt)  # = sqrt(0.5*mean(d^2))/tau? keep standard: sigma(tau)=sqrt(0.5*<d^2>)
        ad[i] = np.sqrt(0.5 * np.mean(d ** 2)) / (tau)
    return ad


def fit_params(taus, ad):
    """Anchor-based fit: white noise density N at slope -1/2, RW K at +1/2, bias instability B at min."""
    valid = np.isfinite(ad)
    tau, s = np.array(taus)[valid], np.array(ad)[valid]
    if len(tau) < 5:
        return None
    i_min = int(np.argmin(s))
    B = s[i_min]
    # white noise: sigma = N / sqrt(tau)  -> N = sigma*sqrt(tau) at the -1/2 band
    half = slice(0, max(2, i_min))
    N = float(np.median(s[half] * np.sqrt(tau[half])))
    # random walk: sigma = K*sqrt(tau/3)  -> K = sigma*sqrt(3/tau) at +1/2 band
    rw = slice(min(len(s) - 1, i_min + 1), len(s))
    K = float(np.median(s[rw] * np.sqrt(3.0 / tau[rw])))
    return {"noise_density": N, "bias_instability": B, "rate_random_walk": K}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag")
    ap.add_argument("--topic", default="/mavros/imu/data_raw")
    ap.add_argument("--skip-head", type=float, default=1500.0, help="seconds to skip (parallel-load window)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or os.path.dirname(os.path.abspath(args.bag))
    t, w, a = load_imu(args.bag, args.topic, args.skip_head)
    dur = t[-1] - t[0]
    print("loaded N=%d dur=%.0fs rate=%.2fHz skip=%.0fs" % (len(t), dur, len(t) / dur, args.skip_head))
    taus = np.array([0.04, 0.1, 0.3, 1, 3, 10, 30, 60, 120, 300, 600, 900])
    taus = taus[taus < dur / 4]
    res = {"duration_s": dur, "n_samples": len(t), "rate_hz": len(t) / dur, "tau": taus.tolist()}
    lines = []
    for name, data, unit, up_n in (("gyr", w, "rad/s", 0.01), ("acc", a, "m/s^2", 0.1)):
        for ax in range(3):
            ad = allan_dev(data[:, ax], t, taus)
            res["%s_allan_ch%d" % (name, ax)] = np.nan_to_num(ad).tolist()
        ads = [allan_dev(data[:, ax], t, taus) for ax in range(3)]
        avg = np.nanmean(np.array(ads), axis=0)
        res["%s_allan_avg" % name] = np.nan_to_num(avg).tolist()
        fp = fit_params(taus, avg)
        res["%s_fit" % name] = fp
        lines.append("%s: noise_density=%.3g %s/sqrt(Hz) (upstream %g, ratio %.2f) bias_instab=%.3g RW=%.3g" %
                     (name, fp["noise_density"], unit, up_n, fp["noise_density"] / up_n, fp["bias_instability"], fp["rate_random_walk"]))
    import json
    with open(os.path.join(out, "allan_analysis.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\n".join(lines))
    print("[note-A] ratio>3 on any quadruple member -> REPORT to swap config (config v0 note A)")


if __name__ == "__main__":
    main()
