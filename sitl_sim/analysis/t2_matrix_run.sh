#!/usr/bin/env bash
# T2-WA 通用矩阵 runner: manifest 驱动,断点续跑(judge.json 存在跳过)
# manifest 格式(每行): <cell名>;<bag路径>;<yaml覆盖键值对,逗号分隔>
#   例: wa2_c1;/path/flight.bag;t2_prior_gate:1,t2_prior_cost_thr:5000
# 配置目录自动生成: ~/sitl_sim/t3_configs/<PREFIX>_<cell>/ (canonical 复制+append)
# 用法: t2_matrix_run.sh <manifest> <PREFIX>
export ROS_DISTRO=noetic
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
AN=~/catkin_ws/sitl_sim/analysis
CAN_SRC=~/catkin_ws/src/VINS-Fusion/config/sim_stereo
CFG_ROOT=~/sitl_sim/t3_configs
R=~/sitl_sim/t3_results
MANIFEST="$1"; PREFIX="$2"
[ -z "$PREFIX" ] && { echo "usage: $0 <manifest> <PREFIX>"; exit 1; }

while IFS=';' read -r CELL BAG KV; do
  [ -z "$CELL" ] && continue
  case "$CELL" in \#*) continue;; esac
  CFG="$CFG_ROOT/${PREFIX}_${CELL}"
  OUT="$R/${PREFIX}_${CELL}_$(basename "$BAG" .bag)"
  if [ -f "$OUT/judge.json" ]; then echo "[run] skip $CELL"; continue; fi
  if [ ! -d "$CFG" ]; then
    cp -r "$CAN_SRC" "$CFG"
    python3 - "$CFG/sim_stereo_imu_config.yaml" "$KV" << 'PY'
import sys, re
p, kv = sys.argv[1], sys.argv[2]
s = open(p).read()
# strip keys we are about to override (FileStorage keeps FIRST occurrence,
# so appending alone is silently ignored for keys already in canonical yaml)
s = re.sub(r"(?m)^t2_cost_trace\s*:.*\n", "", s)
s += "\n# T2 matrix cell overrides\n"
for pair in kv.split(","):
    k, v = pair.strip().split(":", 1)
    s = re.sub(r"(?m)^%s\s*:.*\n" % re.escape(k), "", s)
    s += "%s: %s\n" % (k, v)
s += "t2_cost_trace: 1\n"
open(p, "w").write(s)
PY
  fi
  echo "[run] $(date +%T) START $CELL ($(basename $BAG))"
  bash $AN/t3_replay.sh "${PREFIX}_${CELL}" "$BAG" "$CFG" 11312
  python3 $AN/t3_replay_eval.py "$OUT" "$BAG" >/dev/null 2>&1
  python3 $AN/wa_judge.py "$OUT" > "$OUT/judge.json" 2>/dev/null || true
  cat "$OUT/judge.json" 2>/dev/null
done < "$MANIFEST"
echo "[run] $(date +%T) ALL DONE"
