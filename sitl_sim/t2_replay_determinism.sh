#!/usr/bin/env bash
# T2-U1 确定性回归 harness: 同一 bag×配置×N 次重放, odometry 内容 md5 必须一致。
# 用法: t2_replay_determinism.sh <bag> <配置目录> [N=3]
# 输出: /tmp/t2_det_<tag>/ 与终端 PASS/FAIL
set -u
source /opt/ros/noetic/setup.bash 2>/dev/null || export ROS_DISTRO=noetic && source /opt/ros/noetic/setup.bash
BAG="$(readlink -f "${1:?bag}")"
CFG="$(readlink -f "${2:?cfg}")"
N="${3:-3}"
TAG="det_$(basename "$BAG" .bag)_$(date +%H%M%S)"
DIR="$HOME/sitl_sim/t2_results/$TAG"
mkdir -p "$DIR"

for i in $(seq 1 "$N"); do
  echo "[det] run $i/$N ..."
  bash "$HOME/sitl_sim/t2_replay.sh" "${TAG}_r${i}" "$BAG" "$CFG" >/dev/null 2>&1
  python3 - "$HOME/sitl_sim/t2_results/${TAG}_r${i}_$(basename "$BAG" .bag)/vins_out.bag" "$DIR/md5_r${i}.txt" <<'PYEOF'
import sys, hashlib
import rosbag
bag = rosbag.Bag(sys.argv[1], "r")
h = hashlib.md5()
n = 0
for topic, msg, _ in bag.read_messages(topics=["/vins_estimator/odometry"]):
    p = msg.pose.pose.position; q = msg.pose.pose.orientation
    t = msg.twist.twist.linear
    s = msg.header.stamp.to_sec()
    h.update(("%.6f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f" %
              (s, p.x, p.y, p.z, q.x, q.y, q.z, q.w, t.x, t.y, t.z)).encode())
    n += 1
bag.close()
open(sys.argv[2], "w").write("%s  n=%d\n" % (h.hexdigest(), n))
PYEOF
  cat "$DIR/md5_r${i}.txt"
done

MD5S=$(cat "$DIR"/md5_r*.txt | awk '{print $1}' | sort -u | wc -l)
if [ "$MD5S" -eq 1 ]; then
  echo "[det] PASS: $N 次重放 odometry md5 一致"; exit 0
else
  echo "[det] FAIL: $N 次重放 md5 不一致"; cat "$DIR"/md5_r*.txt; exit 1
fi
