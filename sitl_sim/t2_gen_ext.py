#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U3 扩展网格配置生成: E15(IMU 噪声)/E16(特征)/E17(求解×关键帧)。
基座一律 E20(ext:1+td:0), 单变量网格; 幂等(目录存在跳过)。
用法: python3 t2_gen_configs_ext.py
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/sitl_sim"))
import t2_gen_configs as G  # 复用 read_base/sub/write


def make(base_e20):
    n = 0
    # E15 IMU 噪声网格 acc_n × gyr_n(现值 0.1/0.01 为保守假设, 仿真真值远小)
    for acc_n in (0.005, 0.02, 0.05, 0.1, 0.2):
        for gyr_n in (0.001, 0.004, 0.01, 0.02):
            name = "E15_acc%03d_gyr%03d" % (round(acc_n * 1000), round(gyr_n * 1000))
            if os.path.isdir(os.path.join(G.OUT_ROOT, name)):
                continue
            t = G.sub(base_e20, r"acc_n: [-0-9.eE]+", "acc_n: %g" % acc_n)
            t = G.sub(t, r"gyr_n: [-0-9.eE]+", "gyr_n: %g" % gyr_n)
            G.write(name, t)
            n += 1
    # E16 特征 2D 网格 max_cnt × min_dist
    for mc in (150, 200, 250, 300):
        for md in (15, 20, 30):
            name = "E16_cnt%03d_md%02d" % (mc, md)
            if os.path.isdir(os.path.join(G.OUT_ROOT, name)):
                continue
            t = G.sub(base_e20, r"max_cnt: \d+", "max_cnt: %d" % mc)
            t = G.sub(t, r"min_dist: \d+", "min_dist: %d" % md)
            G.write(name, t)
            n += 1
    # E17 求解预算 × 关键帧视差
    for st in (0.04, 0.06, 0.08):
        for kp in (5.0, 10.0, 20.0):
            name = "E17_st%03d_kp%02d" % (round(st * 1000), round(kp))
            if os.path.isdir(os.path.join(G.OUT_ROOT, name)):
                continue
            t = G.sub(base_e20, r"max_solver_time: [-0-9.]+", "max_solver_time: %g" % st)
            t = G.sub(t, r"keyframe_parallax: [-0-9.]+", "keyframe_parallax: %g" % kp)
            G.write(name, t)
            n += 1
    print("E15-E17 生成 %d 个新变体 → %s" % (n, G.OUT_ROOT))


if __name__ == "__main__":
    base = G.read_base()
    b = G.sub(base, r"estimate_extrinsic: \d", "estimate_extrinsic: 1")
    b = G.sub(b, r"estimate_td: \d", "estimate_td: 0")
    make(b)
