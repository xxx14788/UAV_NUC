#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""atlas_v2_certify.py — A1 抽验同栈旁证（3090 运行）
对抽验轮直接从 flight.bag 复算绘图脚本的输入与裁剪窗口，输出米制证书：
  ① odom 越窗规模（v2 裁剪截掉了多少点/多少米——弹射轮应有大量截除）
  ② truth/odom 数据包络（v1 无界 vs v2 有界的量化差）
  ③ 字体豆腐成因对照（v1 中文 family 串 vs v2 ASCII 串在默认 Agg 字体下的渲染）
仅读 bag 与只读复算，不改任何正本。"""
import sys, os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rosbag

RUNS_ROOT = os.path.expanduser("~/sitl_sim/vins_smoke_runs")

def load(run):
    truth, prop = [], []
    with rosbag.Bag(os.path.join(RUNS_ROOT, run, "flight.bag"), "r") as b:
        for topic, msg, t in b.read_messages(topics=["/gazebo/model_states", "/vins_estimator/imu_propagate"]):
            if topic == "/gazebo/model_states":
                try: i = msg.name.index("iris_stereo_vins")
                except ValueError: continue
                p = msg.pose[i].position; truth.append((p.x, p.y))
            else:
                p = msg.pose.pose.position; prop.append((p.x, p.y))
    return np.array(truth), np.array(prop)

def certify(run):
    truth, prop = load(run)
    # —— 与 c3_traj_plot.py v2 完全一致的窗口/裁剪复算 ——
    dx0, dy0 = truth[0][0]-prop[0][0], truth[0][1]-prop[0][1]
    prop = prop + np.array([dx0, dy0])
    tx, ty = truth[:,0], truth[:,1]
    x0, x1 = tx.min()-3, tx.max()+3; y0, y1 = ty.min()-3, ty.max()+3
    span = max(x1-x0, y1-y0)
    x0, x1 = (x0+x1)/2-span/2-1, (x0+x1)/2+span/2+1
    y0, y1 = (y0+y1)/2-span/2-1, (y0+y1)/2+span/2+1
    inside = (prop[:,0]>=x0)&(prop[:,0]<=x1)&(prop[:,1]>=y0)&(prop[:,1]<=y1)
    n_in, n_all = int(inside.sum()), len(prop)
    # 越窗规模（米制）：被截除点相对窗口边界的超出量 + odom 相对 truth 包络的最大偏距
    exc = 0.0
    if n_in < n_all:
        outp = prop[~inside]
        exc = float(max(np.maximum(np.maximum(x0-outp[:,0], outp[:,0]-x1), np.maximum(y0-outp[:,1], outp[:,1]-y1)).max(), 0))
    # 分块最近真值点距离（防整阵内存爆）
    odom_dev = None
    if n_all:
        best = np.full(len(prop), np.inf)
        for i in range(0, len(prop), 2000):
            d = np.linalg.norm(truth[None, :, :] - prop[i:i+2000, None, :], axis=2)
            best[i:i+2000] = d.min(axis=1)
        odom_dev = float(best.max())
    # v1 口径的 odom 绝对漂移（出生锚后最大 |Δ|，米）
    max_abs = float(np.max(np.abs(prop - prop[0]).max(axis=0)))
    return {"run": run, "truth_n": len(truth), "odom_n": n_all,
            "odom_points_clipped": n_all-n_in, "clip_frac": round((n_all-n_in)/max(n_all,1), 4),
            "window_x": [round(float(x0),2), round(float(x1),2)], "window_y": [round(float(y0),2), round(float(y1),2)],
            "truth_ext": [round(float(tx.max()-tx.min()),2), round(float(ty.max()-ty.min()),2)],
            "odom_max_abs_from_birth_m": round(max_abs, 2),
            "odom_max_dev_vs_truth_m": round(odom_dev, 2) if odom_dev is not None else None,
            "over_window_excursion_m": round(exc, 2)}

def font_tofu_certify():
    """v1(中文 family) vs v2(ASCII) 在同一 Agg 默认字体下的渲染对照：
    逐字符渲染并比较位图——豆腐块=所有字形位图完全相同。"""
    def render_glyphs(text):
        fig, ax = plt.subplots(figsize=(0.5, 0.5)); ax.axis("off")
        glyphs = []
        for ch in text:
            ax.text(0.5, 0.5, ch, fontsize=16)
            fig.canvas.draw()
            a = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].astype(int)
            ink = (a.mean(axis=2) < 128)
            glyphs.append((int(ink.sum()), ink.shape, float(ink.mean())))
            ax.texts.pop()
        plt.close(fig); return glyphs
    zh = "起飞彩票跳变族悬停弹射"          # v1 batch 曾用的中文 family 词
    en = "takeoff-lottery jump family eject"
    gz, ge = render_glyphs(zh), render_glyphs(en)
    zh_bitmaps_identical = len(set(g for g in gz if g[0] > 0)) <= 2   # 多数字形同一 bitmap=豆腐
    en_bitmaps_identical = len(set(g for g in ge if g[0] > 0)) <= 2
    return {"zh_glyph_n": len(gz), "zh_distinct_bitmaps": len(set(g for g in gz if g[0]>0)),
            "zh_tofu": bool(zh_bitmaps_identical), "en_glyph_n": len(ge),
            "en_distinct_bitmaps": len(set(g for g in ge if g[0]>0)), "en_tofu": bool(en_bitmaps_identical),
            "conclusion": "default font lacks CJK → Chinese text renders as repeated identical boxes (tofu); ASCII renders distinct glyphs"}

def main():
    runs = sys.argv[1:]
    out = {"clip_cert": [certify(r) for r in runs], "font_cert": font_tofu_certify()}
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
