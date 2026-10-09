#!/usr/bin/env python3
# T1 v11.39 单元4 — 旧批病理标本特征化(升正式件): Bas 爆精确时间线 vs USB 断链 23:09:39 对齐
# 判读面(实机袋无 VINS bias 话题,爆时刻以 odom 流形态代理): 帧位移>0.1m 时刻序列(雪崩袋)+
# 断流时刻(最后有效帧)。结论: 爆起早于 23:09:39 = USB 劣化渐进期数据污染链深化; 晚/同步 = 另有诱因需重开。
import rosbag, os, datetime

BAGDIR = os.path.expanduser("~/sitl_sim/t4_evidence/realmachine_pre_record/bags")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_39_2026-10-09")
BAGS = [
    ("old_scen1_microshake(雪崩)", "scen1_handheld_microshake.bag"),
    ("old_scen2_slowmove(轻度)", "scen2_handheld_slowmove.bag"),
    ("old_scen3_walk(断流)", "scen3_handheld_walk.bag"),
    ("old_scen4_slide(断流)", "scen4_desktop_slide.bag"),
]
USB_DOWN = "23:09:39"  # 预录会话在案断链时刻

def lt(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")

lines = [f"# 旧批病理标本特征化(vs USB 断链 {USB_DOWN} 对齐)", ""]
for name, fn in BAGS:
    path = os.path.join(BAGDIR, fn)
    if not os.path.isfile(path):
        lines.append(f"## {name}: BAG_MISSING"); continue
    b = rosbag.Bag(path)
    pts = []
    for topic, msg, t in b.read_messages(topics=["/vins_estimator/odometry", "/vins_estimator/imu_propagate"]):
        p = msg.pose.pose.position
        pts.append((t.to_sec(), p.x, p.y, p.z))
    b.close(); pts.sort()
    if len(pts) < 3:
        lines.append(f"## {name}: 断流袋(有效帧 n={len(pts)});odom 末帧 {lt(pts[-1][0]) if pts else '-'}")
        continue
    jumps = [(pts[i][0], ((pts[i][1]-pts[i-1][1])**2 + (pts[i][2]-pts[i-1][2])**2 + (pts[i][3]-pts[i-1][3])**2)**0.5)
             for i in range(1, len(pts))]
    big = [(t, d) for t, d in jumps if d > 0.1]
    t_start, t_end = pts[0][0], pts[-1][0]
    lines.append(f"## {name}")
    lines.append(f"- 袋窗: {lt(t_start)} → {lt(t_end)} (dur {t_end-t_start:.0f}s, n={len(pts)})")
    if big:
        first_t = big[0][0]
        rel = first_t - t_start
        vs = "早于" if first_t < datetime.datetime.strptime(USB_DOWN, "%H:%M:%S").replace(
            year=datetime.datetime.fromtimestamp(t_start).year, month=datetime.datetime.fromtimestamp(t_start).month,
            day=datetime.datetime.fromtimestamp(t_start).day).timestamp() else "晚于/同步"
        mx = max(d for _, d in jumps)
        lines.append(f"- 首跳(>0.1m): {lt(first_t)} (袋起+{rel:.0f}s) 幅 {big[0][1]:.3f}m | 大跳总数 {len(big)} | maxde {mx:.2f}m")
        lines.append(f"- **vs 断链 {USB_DOWN}: 爆起 {vs} 断链**")
    else:
        lines.append(f"- 零大跳帧(maxde {max(d for _,d in jumps):.4f}m)")
    lines.append("")
open(os.path.join(OUT, "oldbatch_pathology_timeline_v1139.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
