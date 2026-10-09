#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_realmachine_j0d_odom.py — 实机袋 odom 流 j0d 分解+谱系面 v1.0
T3 v11.1 单元 1a/1b（2026-10-10）；素材=~/sitl_sim/t4_evidence/realmachine_pre_record/bags/

【口径声明（先行，任务书 v11.1 单元 1a 原文要求）】
1. 实机袋无 truth → 分型面用 odom 流分解（/vins_estimator/imu_propagate，与 sim 域
   j0_decomp 同流型口径——sim 样本 HVNET1 n_prop=79539/355.5s=223.8Hz 即本流）；
   与 sim 域 j0d 双锚（truth vs odom）口径【不可互换】：
   - 静置袋（scen0，机体静止=truth 近似不动）：j0_total_odom=终点-起点位移≈绝对漂移，
     分解语义与 sim j0_total 同构（同族可比）；
   - 动袋（r2 批 scen1-4 手持/平移）：truth 未知，odom 轨迹=真实运动×漂移耦合，
     j0_total_odom=行程量【非漂移】；分解面=流形态（跳变事件/帧位移分布），仅作
     流健康刻画与 USB 劣化对照，不进漂移判读。
2. jump 帧=单帧位移>0.1m（sim 域反推阈值：HVNET1 样本 4 jump 帧累计 0.4089m，
   max_frame_de=0.115m，均值 0.1022m 全带自洽）；dominant 判型：jump_frac<1/3→transit，
   >2/3→jump，中带→mixed；净轮=j0_total<0.5（承 hover_lineage_verdict_v1 冻结谱系口径）。
3. 频率域注记：sim=223Hz 固定域；实机 scen0=50Hz 时代；r2 批=202-222Hz 满流——
   同一 0.1m/帧阈值在不同频率下等效速度界不同（223Hz≈22.4m/s；50Hz≈5m/s；202Hz≈20.2m/s），
   判读面以帧位移绝对值为准。

输出：repo 正源 t3_results/realmachine_j0d_odom_<date>.{csv,md}
用法（须 source ROS）：python3 t3_realmachine_j0d_odom.py [--date YYYYMMDD]
"""
import argparse
import csv
import datetime
import math
import os

BAGDIR = os.path.expanduser("~/sitl_sim/t4_evidence/realmachine_pre_record/bags")
OUTDIR = os.path.expanduser("~/catkin_ws/sitl_sim/t3_results")
GEN_VERSION = "t3_realmachine_j0d_odom_v1.0 (T3 v11.1 单元1a/1b; odom流分解·口径声明内嵌)"

# 袋清单：(文件名, 批次, 场景, 判读地位)  正源=R2_MANIFEST.md
BAGS = [
    ("scen0_static_baseline.bag",      "批0",  "静置基线", "判读(静置单锚近似)"),
    ("r2_scen1_microshake.bag",        "r2",   "手持微抖", "判读正源(流形态)"),
    ("r2_scen2_slowmove.bag",          "r2",   "手持缓动", "判读正源(流形态)"),
    ("r2_scen3_walk.bag",              "r2",   "手持走动", "判读正源(流形态)"),
    ("r2_scen4_slide.bag",             "r2",   "桌面平移", "判读正源(流形态)"),
    ("scen1_handheld_microshake.bag",  "旧批", "手持微抖", "对照禁判读(USB劣化标本)"),
    ("scen2_handheld_slowmove.bag",    "旧批", "手持缓动", "对照禁判读(USB劣化标本)"),
    ("scen3_handheld_walk.bag",        "旧批", "手持走动", "对照禁判读(USB劣化标本)"),
    ("scen4_desktop_slide.bag",        "旧批", "桌面平移", "对照禁判读(USB劣化标本)"),
]

JUMP_FRAME_M = 0.1      # jump 帧阈值（sim 域反推；口径声明第 2 条）
NET_ROUND_M = 0.5       # 净轮界（hover_lineage_verdict_v1 冻结）
ODOM_TOPICS = ["/vins_estimator/imu_propagate", "/vins_estimator/odometry"]  # r2 批预录无前者→fallback
AUX_TOPICS = ["/mavros/imu/data_raw",
              "/camera/infra1/image_rect_raw", "/camera/infra2/image_rect_raw"]


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def family_of(j0_total, dominant, static, n_jf=None, max_de=None, path_len=None):
    """谱系面：静置袋=同族可比（漂移语义）；动袋=流形态如实降格（无漂移语义）。

    方向一致度 coh=j0_total/path_len：终态位移与累计路程之比——
    静置健康态=噪声抖动型（coh→0，sim scen0 实测 0.0007）；定向慢淋=coh→1
    （sim HVNET1 复刻 transit 3.719+jump 0.409≈终态 4.118，coh≈1.0）。
    """
    coh = ""
    if j0_total is not None and path_len:
        coh = round(j0_total / path_len, 4)
    if not static:
        tail = "流形态(njf=%s,maxde=%s m)——非漂移语义不进同族面" % (n_jf, max_de)
        if n_jf == 0 and (max_de is not None and max_de < JUMP_FRAME_M):
            return "动袋流净(零跳帧,帧位移<0.1m); " + tail, coh
        if dominant == "transit":
            return "动袋流形态(transit 主导); " + tail, coh
        return "动袋流形态(%s); " % dominant + tail, coh
    # 静置袋：漂移语义成立，进谱系面
    if j0_total is not None and j0_total < NET_ROUND_M:
        return "净轮(无跳变病理; 噪声抖动型慢淋 coh=%s)" % coh, coh
    if dominant == "transit":
        return "transit 慢淋主导族(与 sim 悬停自跳/导航 B 型同族可比; coh=%s)" % coh, coh
    if dominant == "mixed":
        return "脉冲复合族(与 E8P 巨跳格同族可比; coh=%s)" % coh, coh
    return "jump 主导(单帧族——谱系两支外, 如实登记; coh=%s)" % coh, coh


def decompose(points):
    """odom 流分解：返回 dict（口径声明第 1/2 条）。"""
    n = len(points)
    if n < 3:
        return None
    des = [dist(points[i], points[i + 1]) for i in range(n - 1)]
    des_sorted = sorted(des)
    k95 = des_sorted[int(math.ceil(0.95 * len(des_sorted))) - 1]
    k99 = des_sorted[int(math.ceil(0.99 * len(des_sorted))) - 1]
    jump_frames = [d for d in des if d > JUMP_FRAME_M]
    jump_m = sum(jump_frames)
    transit_m = sum(des) - jump_m
    denom = jump_m + transit_m
    frac = (jump_m / denom) if denom > 0 else 0.0
    j0_total = dist(points[0], points[-1])
    # dominant=纯流形态判型（不掺 net——net 是漂移语义判定，仅静置袋在 family_of 里做）
    if frac < 1.0 / 3.0:
        dom = "transit"
    elif frac > 2.0 / 3.0:
        dom = "jump"
    else:
        dom = "mixed"
    return dict(
        n_prop=n,
        j0_total_m=round(j0_total, 4),
        jump_m=round(jump_m, 4),
        transit_m=round(transit_m, 4),
        jump_frac=round(frac, 4),
        n_jump_frames=len(jump_frames),
        max_frame_de_m=round(max(des), 4),
        p95_frame_de_m=round(k95, 4),
        p99_frame_de_m=round(k99, 4),
        path_len_m=round(sum(des), 4),
        dominant=dom,
    )


def main():
    ap = argparse.ArgumentParser(description="实机袋 odom 流 j0d 分解; " + GEN_VERSION)
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--bags", default=BAGDIR)
    ap.add_argument("--out-dir", default=OUTDIR)
    a = ap.parse_args()

    import rosbag  # 须 source ROS（坑：非交互 ssh 无 env=静默空）
    import rospy

    rows = []
    for fn, batch, scene, role in BAGS:
        path = os.path.join(a.bags, fn)
        if not os.path.exists(path):
            print("[SKIP] missing bag: %s" % path)
            continue
        pts, aux_counts, t0, tN = [], {}, None, None
        topic_used = ""
        with rosbag.Bag(path, "r") as bag:
            bag_topics = set(bag.get_type_and_topic_info()[1].keys())
            for cand in ODOM_TOPICS:
                if cand in bag_topics:
                    topic_used = cand
                    break
            if not topic_used:
                topic_used = ODOM_TOPICS[-1]
            for topic, msg, ts in bag.read_messages(topics=[topic_used] + AUX_TOPICS):
                if topic == topic_used:
                    p = msg.pose.pose.position
                    pts.append((p.x, p.y, p.z))
                    stamp = msg.header.stamp.to_sec() if msg.header.stamp.to_sec() > 0 else ts.to_sec()
                    t0 = stamp if t0 is None else t0
                    tN = stamp
                else:
                    aux_counts[topic] = aux_counts.get(topic, 0) + 1
        dur = (tN - t0) if (t0 is not None and tN is not None) else float("nan")
        d = decompose(pts)
        static = (scene == "静置基线")
        imu_hz = aux_counts.get("/mavros/imu/data_raw", 0) / dur if dur and dur > 0 else None
        img_hz = aux_counts.get("/camera/infra1/image_rect_raw", 0) / dur if dur and dur > 0 else None
        odom_hz = len(pts) / dur if dur and dur > 0 else None
        row = dict(
            bag=fn, batch=batch, scene=scene, role=role,
            dur_s=round(dur, 1) if dur == dur else "",
            topic_used=topic_used.replace("/vins_estimator/", ""),
            odom_topic_hz=round(odom_hz, 1) if odom_hz else "",
            imu_raw_hz=round(imu_hz, 1) if imu_hz else "",
            infra1_hz=round(img_hz, 1) if img_hz else "",
        )
        if d:
            row.update(d)
            fam, coh = family_of(d["j0_total_m"], d["dominant"], static,
                                 d["n_jump_frames"], d["max_frame_de_m"], d["path_len_m"])
            row["dir_cohesion"] = coh
            row["family"] = fam
        else:
            row.update(dict(n_prop=len(pts)))
            row["dir_cohesion"] = ""
            row["family"] = "不可分解(odom 流帧数<3——断流病理标本)"
        rows.append(row)
        print("[OK] %-34s j0_total=%-9s dom=%-8s njf=%-4s maxde=%-8s imu=%sHz" % (
            fn, row.get("j0_total_m", "-"), row.get("dominant", "-"),
            row.get("n_jump_frames", "-"), row.get("max_frame_de_m", "-"),
            row.get("imu_raw_hz", "-")))

    out_csv = os.path.join(a.out_dir, "realmachine_j0d_odom_%s.csv" % a.date)
    fieldnames = ["bag", "batch", "scene", "role", "dur_s", "topic_used", "odom_topic_hz", "imu_raw_hz",
                  "infra1_hz", "n_prop", "j0_total_m", "jump_m", "transit_m", "jump_frac",
                  "n_jump_frames", "max_frame_de_m", "p95_frame_de_m", "p99_frame_de_m",
                  "path_len_m", "dir_cohesion", "dominant", "family"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("[OUT] %s (%d rows)" % (out_csv, len(rows)))


if __name__ == "__main__":
    main()
