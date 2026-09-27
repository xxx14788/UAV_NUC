#!/usr/bin/env bash
# teleport_stats.sh — EKF2 传送重锚质量统计（T3-W8-4，0 飞行轮地面试验）。
# 背景: 2026-09-27 返程腿轮次人工传送后 EKF2 重锚质量随机（z 偏差
# 0.003~1.18m 波动，V2j 爆估计），是返程腿两大伪影之一。
# 做法: SITL 起好（不起飞），循环 N 次传送 iris 至障碍区侧出生点
# (gazebo (7.91,-3.02,0.08), yaw -40°)，每次等 settle 后记录
# /mavros/local_position/odom 与 /gazebo/model_states 真值差，
# 输出 XY/z/yaw 三轴误差分布。t3_verify_flight.sh 的 settle 校验
# 阈值以此分布（P95）为依据。
# 用法: 先起 SITL+深度链(start_sitl_depth.sh 流程), 后跑本脚本 [N=20] [settle_s=10]
set -u
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash" 2>/dev/null || true
N="${1:-20}"; SETTLE="${2:-10}"
OUT="$HOME/sitl_sim/t3_runs/teleport_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

echo "== teleport_stats N=$N settle=${SETTLE}s out=$OUT =="
# 前置检查：gazebo 服务 + odom 活着
timeout 10 rosservice list 2>/dev/null | grep -q /gazebo/set_model_state \
    || { echo "FAIL: gazebo 服务不可达(先起 SITL)"; exit 1; }
timeout 10 rostopic list 2>/dev/null | grep -q local_position/odom \
    || { echo "FAIL: mavros odom 不可达"; exit 1; }

# 测量探针：单次采样 odom 与真值（gazebo 系），写一行 CSV
python3 - "$OUT/probe.py" <<'PYEOF'
import sys
probe = r'''
import rospy, math
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelStates
rospy.init_node("tp_probe", anonymous=True)
got = {}
def cb_odom(m):
    got["odom"] = (m.pose.pose.position.x, m.pose.pose.position.y,
                   m.pose.pose.position.z,
                   m.pose.pose.orientation.w, m.pose.pose.orientation.x,
                   m.pose.pose.orientation.y, m.pose.pose.orientation.z)
def cb_ms(m):
    if "iris" in m.name:
        i = m.name.index("iris")
        p = m.pose[i]
        got["truth"] = (p.position.x, p.position.y, p.position.z,
                        p.orientation.w, p.orientation.x,
                        p.orientation.y, p.orientation.z)
rospy.Subscriber("/mavros/local_position/odom", Odometry, cb_odom)
rospy.Subscriber("/gazebo/model_states", ModelStates, cb_ms)
t0 = rospy.Time.now()
while not rospy.is_shutdown() and ("odom" not in got or "truth" not in got) \
        and (rospy.Time.now() - t0).to_sec() < 5.0:
    rospy.sleep(0.05)
if "odom" not in got or "truth" not in got:
    sys.exit(1)
def yaw(w, x, y, z):
    return math.atan2(2 * (x * y + w * z), 1 - 2 * (y * y + z * z))
BIRTH = (1.01, 0.98)  # iris 出生 gazebo 偏移（odom = gazebo - BIRTH）
ox, oy, oz, ow, oxx, oyy, ozz = got["odom"]
gx, gy, gz, gw, gxx, gyy, gzz = got["truth"]
dx = ox - (gx - BIRTH[0])
dy = oy - (gy - BIRTH[1])
print("%.4f,%.4f,%.4f" % (
    math.hypot(dx, dy), oz - gz,
    math.degrees(yaw(ow, oxx, oyy, ozz) - yaw(gw, gxx, gyy, gzz))))
'''
open(sys.argv[1], "w").write(probe)
PYEOF

CSV="$OUT/teleport_stats.csv"
echo "run,dxy_m,dz_m,dyaw_deg" > "$CSV"
YAW=-0.698  # -40 deg
for i in $(seq 1 "$N"); do
    rosservice call /gazebo/set_model_state "{model_state: {model_name: 'iris', \
        pose: {position: {x: 7.91, y: -3.02, z: 0.08}, \
        orientation: {z: $(python3 -c "import math;print(math.sin($YAW/2))"), \
                      w: $(python3 -c "import math;print(math.cos($YAW/2))")}}, \
        twist: {linear: {x:0,y:0,z:0}, angular: {x:0,y:0,z:0}}, reference_frame: 'world'}}" >/dev/null 2>&1
    sleep "$SETTLE"
    line=$(timeout 8 python3 "$OUT/probe.py" 2>/dev/null) || line="ERR,ERR,ERR,ERR"
    echo "$i,$line" >> "$CSV"
    echo "  [$i/$N] $line"
done

python3 - "$CSV" <<'PYEOF'
import sys, numpy as np
rows = [l.strip().split(',') for l in open(sys.argv[1]) if l[0].isdigit()]
ok = [r for r in rows if r[1] != 'ERR']
print("\n== teleport 重锚误差分布 (%d/%d 成功) ==" % (len(ok), len(rows)))
if not ok:
    print("全部采样失败"); sys.exit(1)
a = np.array([[float(x) for x in r[1:]] for r in ok])
# 列: dxy(欧氏) / dz / dyaw(deg)——probe 已把 dxy 算成欧氏距离
for j, name in ((0, 'dxy[m]'), (1, 'dz[m]'), (2, 'dyaw[deg]')):
    col = np.abs(a[:, j])
    print("%-12s mean=%.3f P95=%.3f max=%.3f" %
          (name, float(col.mean()), float(np.percentile(col, 95)), float(col.max())))
PYEOF
echo "原始数据: $CSV"
