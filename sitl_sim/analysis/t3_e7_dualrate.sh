#!/usr/bin/env bash
# E7 同袋双频回放编排(v7.4 等待池⑤;窗口纪律=T2 U2 队列间隙或 STATUS 协调小窗)
# 用法: t3_e7_dualrate.sh <tag> <bag223> <cfg_dir> [port=11313]
# 流程: prepare(223→125 降采样袋) → 串行两遍 t3_replay.sh → 自动 judge
# 红线: 单机一路 vins_node 回放(起跑前 pgrep 全场);私有 master;跑前 STATUS 预告
set -u
TAG="${1:?tag}"; BAG223="$(readlink -f "${2:?bag223}")"; CFG="$(readlink -f "${3:?cfg_dir}")"
PORT="${4:-11313}"
A="$HOME/catkin_ws/sitl_sim/analysis"

# ---- 单机一路回放红线:起跑前 pgrep 全场(有 vins_node/回放在跑=退出) ----
RUNNING=$(pgrep -a -f 'vins_nod[e]|rosbag pla[y]' 2>/dev/null | grep -v $$ | head -3)
[ -z "$RUNNING" ] || { echo "FATAL 回放窗被占: $RUNNING —— 按 STATUS 协调,勿硬抢"; exit 1; }

# ---- prepare:降采样袋(已存在且 manifest 匹配则复用) ----
BAG125="${BAG223%.bag}_125hz.bag"
if [ ! -f "$BAG125" ]; then
  python3 "$A/t3_e7_dualrate.py" prepare "$BAG223" --out "$BAG125" || exit 1
fi

# ---- 串行两遍回放(t3_replay.sh 自带私有 master/清理) ----
echo "[e7-run] pass1: 223Hz 原生"
bash "$A/t3_replay.sh" "${TAG}_e7a223" "$BAG223" "$CFG" "$PORT" || exit 1
sleep 5
RUNNING=$(pgrep -a -f 'vins_nod[e]|rosbag pla[y]' 2>/dev/null | head -3)
[ -z "$RUNNING" ] || { echo "WARN pass1 残留进程: $RUNNING"; sleep 10; }

echo "[e7-run] pass2: 125Hz 降采样"
bash "$A/t3_replay.sh" "${TAG}_e7b125" "$BAG125" "$CFG" "$PORT" || exit 1

# ---- 自动 judge ----
D223="$HOME/sitl_sim/t3_results/${TAG}_e7a223_$(basename "$BAG223" .bag)"
D125="$HOME/sitl_sim/t3_results/${TAG}_e7b125_$(basename "$BAG125" .bag)"
echo "[e7-run] judge: $D223 vs $D125"
python3 "$A/t3_e7_dualrate.py" judge "$D223" "$D125" --csv "$A/e7_dualrate.csv"
echo "[e7-run] acc 重标系数原料(两源袋各一次):"
python3 "$A/t3_e7_dualrate.py" accstats "$BAG223"
python3 "$A/t3_e7_dualrate.py" accstats "$BAG125"
