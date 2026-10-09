#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_online_delta_stats.py — 在线域双目时戳差 δ 分布离线统计 v1.0
T3 v11.1 单元 4（2026-10-10）：回答 T3 C.3 开口关键一问——在线域 δ 分布是否压在危险带
（δc∈(3,4]ms / 跳变瀑布带 ≤2ms）。

【样本域口径（如实注记）】
- sim 在线域含图像在线轮全集=13 轮（vins_smoke_runs 全库 flight.bag 含 sensor_msgs/Image
  实测盘点），**全部为 FAIL/跳变族轮**——绿轮袋未录图像（X5/X4 四绿轮袋 50-60M 无图像，
  X4 四绿五轮袋已清理 NOBAG）→ sim 绿组 δ 分布 bag 直读物理不可得=样本域开口，X7 收敛
  声明带此限定。
- 对照组=实机 r2 批四袋（D435 硬同步双目，健康流形态=实机域绿对照；域差注记：D435 结构性
  δ≈0 vs sim 渲染域，不可互换，仅作结构参照）。
- δ 定义=同序号配对 t_left[i] - t_right[i]（带符号，ms）；统计面=带符号分位+|δ| 分位+分带占比。
  sim 双目 topic=/iris_stereo_vins/vins_cam_{left,right}/image_raw；实机=/camera/infra{1,2}/image_rect_raw。

输出：repo 正源 t3_results/online_delta_stats_<date>.{csv,md}
用法（须 source ROS）：python3 t3_online_delta_stats.py [--date YYYYMMDD]
"""
import argparse
import csv
import datetime
import os

HOME = os.path.expanduser("~")
OUTDIR = HOME + "/catkin_ws/sitl_sim/t3_results"
GEN_VERSION = "t3_online_delta_stats_v1.0 (T3 v11.1 单元4; bag直读·绿组不可得注记内嵌)"

SIM_L = "/iris_stereo_vins/vins_cam_left/image_raw"
SIM_R = "/iris_stereo_vins/vins_cam_right/image_raw"
RM_L = "/camera/infra1/image_rect_raw"
RM_R = "/camera/infra2/image_rect_raw"

# sim 在线域含图像轮全集(13/13 全 FAIL=跳变族;combo 350 池判定面)
SIM_ROUNDS = [
    ("run_X4_1e_HVNET1_040009", "FAIL 慢淋跳(MB/MA 标本源,j0=4.119)"),
    ("run_T2MACH3_011804",      "FAIL 中漂移带 H1 锚(arrive 8.026)"),
    ("run_T2MACH8_015411",      "FAIL 中漂移带 H2(T2fail=0,j0 FAIL)"),
    ("run_X2g1_024637",         "FAIL njf=0 mixed(j0d_jump 0.396)"),
    ("run_X2g4_030233",         "FAIL 跳(njf=269,j0d_jump 67.5)"),
    ("run_X4_S8O_033810",       "FAIL 跳(njf=4,j0d_jump 0.864,arrive 6.009)"),
    ("run_F3B16_191620",        "FAIL(F3 线出生失败静默面)"),
    ("run_X3l2a_031040",        "FAIL 跳(njf=12,transit 0.545)"),
    ("run_F3B11_155643",        "FAIL(F3 线)"),
    ("run_X1final_040643",      "FAIL 跳(njf=19)"),
    ("run_X4_1e_E8P_035301",    "FAIL 巨跳格(j0=2.291,回放 njf=409)"),
    ("run_X2g3_025529",         "FAIL(jmp1e 素材,njf=0,j0d_jump 0.111)"),
    ("run_X3l2b_032653",        "FAIL 跳(njf=560,j0d_jump 226.5)"),
]
RM_BAGS = [
    ("r2_scen1_microshake.bag", "实机 r2 手持微抖(流净对照)"),
    ("r2_scen2_slowmove.bag",   "实机 r2 手持缓动(流净对照)"),
    ("r2_scen3_walk.bag",       "实机 r2 手持走动(流净对照)"),
    ("r2_scen4_slide.bag",      "实机 r2 桌面平移(流净对照)"),
]
BANDS = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0), (5.0, float("inf"))]


def pct(sorted_vals, q):
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def stats_bag(path, ltopic, rtopic):
    import rosbag
    tl, tr = [], []
    with rosbag.Bag(path, "r") as bag:
        avail = set(bag.get_type_and_topic_info()[1].keys())
        for topic, msg, ts in bag.read_messages(topics=[ltopic, rtopic]):
            t = msg.header.stamp
            sec = t.to_sec() if t.to_sec() > 0 else ts.to_sec()
            (tl if topic == ltopic else tr).append(sec)
    n = min(len(tl), len(tr))
    if n < 10:
        return None
    deltas = [(tl[i] - tr[i]) * 1000.0 for i in range(n)]  # ms, 带符号
    absd = sorted(abs(d) for d in deltas)
    sgn = sorted(deltas)
    out = dict(n_pairs=n, n_left=len(tl), n_right=len(tr))
    out["sgn_p05"] = round(pct(sgn, 0.05), 3)
    out["sgn_p50"] = round(pct(sgn, 0.50), 3)
    out["sgn_p95"] = round(pct(sgn, 0.95), 3)
    out["abs_p50"] = round(pct(absd, 0.50), 3)
    out["abs_p95"] = round(pct(absd, 0.95), 3)
    out["abs_p99"] = round(pct(absd, 0.99), 3)
    out["abs_max"] = round(absd[-1], 3)
    for lo, hi in BANDS:
        cnt = sum(1 for a in absd if lo <= a < hi)
        out["band_%g_%gms" % (lo, hi if hi != float("inf") else 99)] = round(cnt / len(absd), 4)
    return out


def main():
    ap = argparse.ArgumentParser(description="在线域双目 δ 分布统计; " + GEN_VERSION)
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--out-dir", default=OUTDIR)
    a = ap.parse_args()

    rows = []
    for rd, note in SIM_ROUNDS:
        path = HOME + "/sitl_sim/vins_smoke_runs/%s/flight.bag" % rd
        if not os.path.exists(path):
            print("[SKIP] no bag:", rd)
            continue
        st = stats_bag(path, SIM_L, SIM_R)
        row = dict(round=rd, group="sim在线跳组", note=note)
        row.update(st or {"n_pairs": 0, "unreadable": 1})
        rows.append(row)
        if st:
            print("[OK] %-28s n=%-5d sgn_p50=%-8.3f abs_p95=%-7.3f abs_max=%-9.3f b34=%s" % (
                rd, st["n_pairs"], st["sgn_p50"], st["abs_p95"], st["abs_max"], st["band_3_4ms"]))
        else:
            print("[WARN]", rd, "unreadable/too-few")
    for fn, note in RM_BAGS:
        path = HOME + "/sitl_sim/t4_evidence/realmachine_pre_record/bags/" + fn
        st = stats_bag(path, RM_L, RM_R)
        row = dict(round=fn, group="实机r2对照组", note=note + "; 域差注记:D435硬同步vs sim渲染域")
        row.update(st or {"n_pairs": 0, "unreadable": 1})
        rows.append(row)
        if st:
            print("[OK] %-28s n=%-5d sgn_p50=%-8.3f abs_p95=%-7.3f abs_max=%-9.3f b34=%s" % (
                fn, st["n_pairs"], st["sgn_p50"], st["abs_p95"], st["abs_max"], st["band_3_4ms"]))

    out_csv = os.path.join(a.out_dir, "online_delta_stats_%s.csv" % a.date)
    fieldns = ["round", "group", "note", "n_pairs", "n_left", "n_right", "sgn_p05", "sgn_p50",
               "sgn_p95", "abs_p50", "abs_p95", "abs_p99", "abs_max",
               "band_0_1ms", "band_1_2ms", "band_2_3ms", "band_3_4ms", "band_4_5ms", "band_5_99ms"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("[OUT] %s (%d rows)" % (out_csv, len(rows)))


if __name__ == "__main__":
    main()
