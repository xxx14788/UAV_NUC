#!/bin/bash
# t3_md5_reconcile.sh — 双 NUC 筛选判读链一致性四件 md5 对账（T3 v10.6 单元 1 就绪件）
# 依据: T1 v11.28 2d —— "双机栈/config/判读器/world 文件四 md5 逐位对账=同栈前提,
#       不对齐禁开批"; T3 v10.6 单元 1 —— "跨机器判读链一致性前提=T1 部署时 md5 对齐,
#       差异=判读前呈报"。
# 用法:
#   t3_md5_reconcile.sh ref                 # 本机生成参照清单 -> stdout + 可存文件
#   t3_md5_reconcile.sh ref -o <file>       # 参照清单落盘
#   t3_md5_reconcile.sh cmp <manifest>      # 与对侧清单比对(四行逐位); 差异=非零退出+呈报表
# 纪律:
#   - 四件任一路径解析失败 = 显式 FAIL 退出 3(禁部分清单——部分对账=假对账)
#   - 清单带 hostname+生成时刻+脚本自身 md5(自指校验,防清单格式漂移)
#   - CRLF 防御: 比对前 strip \r
set -u

# ---- 四件路径解析(候选序=先精确后发现; 全失败才 FAIL) ----
CW="$HOME/catkin_ws"

resolve_one() {  # $1=键名(仅报错用) $2...=候选; 只走显式候选, 不做静默发现——
                  # 对账件路径必须显式可复核, 候选缺失=FAIL 让部署方补
  local key="$1"; shift
  for c in "$@"; do
    if [ -f "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  echo "resolve_one: $key 无命中候选" >&2
  return 1
}

# 1) 栈 = vins_node 二进制(每轮重放登记 vins_node md5 纪律同源)
STACK_CANDIDATES=(
  "$CW/devel/lib/vins/lib/vins_node"
  "$CW/devel/lib/vins/vins_node"
)
# 2) config = 当前在用 VINS stereo config(部署对齐正源)
CONFIG_CANDIDATES=(
  "$CW/src/VINS-Fusion/config/iris_stereo/iris_stereo_config.yaml"
  "$CW/src/VINS-Fusion/config/iris_stereo_config.yaml"
)
# 3) 判读器 = round_result 脚本(7e907b7d 系; 位置以 repo sitl_sim 为准)
JUDGE_CANDIDATES=(
  "$CW/sitl_sim/t3_tools/round_result.py"
  "$CW/sitl_sim/scripts/round_result.py"
  "$CW/sitl_sim/round_result.py"
)
# 4) world = plain world(我方自造, 必须对齐——T1 2d 明示此前遗漏项)
WORLD_CANDIDATES=(
  "$CW/src/sitl_gazebo/worlds/plain.world"
  "$CW/src/mavlink_sitl_gazebo/worlds/plain.world"
)

miss=0
STACK=$(resolve_one stack "${STACK_CANDIDATES[@]}" 2>/dev/null) || { echo "FAIL: vins_node 未解析(候选:${STACK_CANDIDATES[*]})"; miss=1; }
CONFIG=$(resolve_one config "${CONFIG_CANDIDATES[@]}" 2>/dev/null) || { echo "FAIL: config 未解析(候选:${CONFIG_CANDIDATES[*]})"; miss=1; }
JUDGE=$(resolve_one judge "${JUDGE_CANDIDATES[@]}" 2>/dev/null) || { echo "FAIL: 判读器未解析(候选:${JUDGE_CANDIDATES[*]})"; miss=1; }
WORLD=$(resolve_one world "${WORLD_CANDIDATES[@]}" 2>/dev/null) || { echo "FAIL: plain world 未解析(候选:${WORLD_CANDIDATES[*]})"; miss=1; }
[ "$miss" -eq 0 ] || { echo "ABORT: 四件对账禁部分执行——请补候选路径后重跑"; exit 3; }

SELF_MD5=$(md5sum "$0" | awk '{print $1}')
emit() {
  echo "# t3_md5_reconcile manifest v1"
  echo "# host=$(hostname) ts=$(date '+%F %T') self_md5=$SELF_MD5"
  echo "stack=$(md5sum "$STACK" | awk '{print $1}')  path=$STACK"
  echo "config=$(md5sum "$CONFIG" | awk '{print $1}')  path=$CONFIG"
  echo "judge=$(md5sum "$JUDGE" | awk '{print $1}')  path=$JUDGE"
  echo "world=$(md5sum "$WORLD" | awk '{print $1}')  path=$WORLD"
}

case "${1:-}" in
ref)
  if [ "${2:-}" = "-o" ] && [ -n "${3:-}" ]; then emit | tee "$3"; else emit; fi
  ;;
cmp)
  M="${2:-}"
  [ -f "$M" ] || { echo "FAIL: 清单不存在: $M"; exit 2; }
  local_out=$(emit)
  # 逐键比对(strip CR; 键=stack/config/judge/world 四行首字段)
  rc=0
  for k in stack config judge world; do
    a=$(printf '%s\n' "$local_out" | grep "^$k=" | tr -d '\r')
    b=$(grep "^$k=" "$M" | tr -d '\r')
    if [ "$a" = "$b" ]; then
      echo "MATCH  $k  $(printf '%s' "$a" | awk '{print $1}')"
    else
      echo "DIFF   $k"
      echo "  本机: $a"
      echo "  对侧: $b"
      rc=1
    fi
  done
  if [ $rc -eq 0 ]; then
    echo "RESULT: 四件全一致 —— 判读链跨机一致性前提成立(P1 PASS)"
  else
    echo "RESULT: 存在差异 —— 差异=判读前呈报(T3 v10.6 单元 1), 禁带差判读/禁开批"
  fi
  exit $rc
  ;;
*)
  echo "用法: $0 ref [-o <file>] | $0 cmp <manifest>" >&2; exit 64 ;;
esac
