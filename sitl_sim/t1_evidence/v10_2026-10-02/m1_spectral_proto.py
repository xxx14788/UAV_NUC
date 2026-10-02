#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M1 spectral method offline prototype (T1 v10.4 deep-pool item 7).

First-cut freeze/smooth-lie vs healthy-static discriminator on position
streams (~10Hz odom). No training; window features + margin report.

Registered hypotheses (u73_pr2_smoothlie_readout.md §3, refined pre-run):
  H-M1a  frozen-lie windows have collapsed high-band noise floor
         (logE in [1,5]Hz far below healthy static)
  H-M1b  frozen windows carry measurable linear creep (trend slope),
         healthy static creep smaller
  Falsifier: feature distributions overlap -> honest negative.

Usage: python3 m1_spectral_proto.py <out.json> <label=csv> [<label=csv> ...]
"""
import csv
import json
import sys

import numpy as np

import os

WIN_S = float(os.environ.get("M1_WIN_S", "20.0"))
STEP_S = float(os.environ.get("M1_STEP_S", "10.0"))
FS_DEFAULT = 10.0
BANDS = {"lf": (0.0, 0.05), "mf": (0.05, 1.0), "hf": (1.0, 5.0)}


def load(csv_path):
    t, x, y, z = [], [], [], []
    with open(csv_path) as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            t.append(float(row[0]))
            x.append(float(row[1]))
            y.append(float(row[2]))
            z.append(float(row[3]))
    return np.array(t), np.array(x), np.array(y), np.array(z)


def resample_uniform(t, v, fs):
    t0, t1 = t[0], t[-1]
    tu = np.arange(t0, t1, 1.0 / fs)
    return np.interp(tu, t, v), tu


def window_features(v, fs):
    """v: uniformly sampled window. Returns feature dict."""
    n = len(v)
    tt = np.arange(n) / fs
    # linear detrend (trend slope = creep rate)
    A = np.vstack([tt, np.ones(n)]).T
    coef, *_ = np.linalg.lstsq(A, v, rcond=None)
    slope = coef[0]
    resid = v - A @ coef
    # periodogram (Bartlett, 4 segments)
    nseg = n // 4
    if nseg < 16:
        return None
    psds = []
    for i in range(4):
        seg = resid[i * nseg:(i + 1) * nseg]
        w = np.hanning(nseg)
        psd = np.abs(np.fft.rfft(seg * w)) ** 2 / np.sum(w ** 2)
        psds.append(psd)
    psd = np.mean(psds, axis=0)
    freqs = np.fft.rfftfreq(nseg, 1.0 / fs)
    band_e = {}
    for name, (f0, f1) in BANDS.items():
        m = (freqs >= f0) & (freqs < f1)
        band_e[name] = float(np.sum(psd[m]))
    total = sum(band_e.values()) + 1e-30
    centroid = float(np.sum(freqs * psd) / (np.sum(psd) + 1e-30))
    return {
        "trend_m_per_s": float(slope),
        "res_std_m": float(np.std(resid)),
        "logE_hf": float(np.log10(band_e["hf"] + 1e-30)),
        "lf_ratio": float(band_e["lf"] / total),
        "centroid_hz": centroid,
    }


def main():
    out_path = sys.argv[1]
    results = {}
    for spec in sys.argv[2:]:
        label, path = spec.split("=", 1)
        t, x, y, z = load(path)
        feats = []
        for ax_name, v_raw in (("x", x), ("y", y), ("z", z)):
            v, tu = resample_uniform(t, v_raw, FS_DEFAULT)
            n_win = int((len(v) / FS_DEFAULT - WIN_S) // STEP_S) + 1
            for i in range(n_win):
                s = int(i * STEP_S * FS_DEFAULT)
                e = s + int(WIN_S * FS_DEFAULT)
                if e > len(v):
                    break
                f = window_features(v[s:e], FS_DEFAULT)
                if f:
                    f["t0"] = float(tu[s] - tu[0])
                    f["axis"] = ax_name
                    feats.append(f)
        results[label] = feats
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)

    # margin report: per feature, separation between first label (suspect)
    # and each other label (controls), per axis pooled
    labels = list(results.keys())
    print(f"windows per label: " + ", ".join(f"{l}={len(v)}" for l, v in results.items()))
    suspect = labels[0]
    feat_keys = [k for k in results[suspect][0] if k not in ("t0", "axis")]
    for fk in feat_keys:
        s_all = np.array([w[fk] for w in results[suspect]])
        line = [f"{fk}: {suspect} [{s_all.min():.4g},{s_all.max():.4g}]"]
        for ctrl in labels[1:]:
            c_all = np.array([w[fk] for w in results[ctrl]])
            gap_hi = s_all.min() - c_all.max()  # suspect below ctrl
            gap_lo = c_all.min() - s_all.max()  # suspect above ctrl
            sep = max(gap_hi, gap_lo)
            direction = "below" if gap_hi >= gap_lo else "above"
            line.append(
                f"{ctrl} [{c_all.min():.4g},{c_all.max():.4g}] sep={sep:.4g}({direction})"
            )
        print(" | ".join(line))


if __name__ == "__main__":
    main()
