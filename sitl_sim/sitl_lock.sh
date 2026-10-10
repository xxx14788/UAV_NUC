#!/usr/bin/env bash
# sitl_lock.sh v2 — SITL 运行时锁统一仲裁(T4-E1 定版 2026-09-29;v1=T1-W5 09-27)
# 锁语义: ~/sitl_sim/SITL.lock → symlink, target=<流名>-<PID>-<HHMMSS>
#   取锁=原子 ln -s;已存在即拒;严禁 ln -sf 覆写(T2 20:38 clobber 实证)
#   心跳=持锁者定期 touch -h 锁文件(勿裸 touch:悬空 symlink 会建出目标实体文件)
#   (symlink 的锁龄=心跳龄:mtime 即唯一时间戳,touch 后一同刷新)
# 命令:
#   get <流名>        取锁。持有者 PID 已死→自动接管(STATUS 通告+原子 mv -T 替换);
#                     活着→拒绝 exit 1(排队等锁或按权序走 preclaim/force)
#   heartbeat <流名>  心跳 touch -h(持锁者每≤5min 一次;带属主守卫)
#   hbloop <流名>     心跳循环(每 5min;锁丢/易主自退;随属主进程组清理)
#   release [流名前缀] 释锁(属主守卫:只放匹配前缀的锁;不给前缀=任意,慎用)
#   status            锁态/属主活性/锁龄/心跳龄/权序
#   preclaim <流名>   抢占预通告:核条件①②+权序→STATUS 通告+记录时刻
#   force <流名>      抢占执行:preclaim 满 5min 无异议+①②复核+属主未变→原子接管
#   diskgate          磁盘水位线门:根分区可用<${SITL_LOCK_DISK_MIN_G:-20}G→拒 exit 3
# 抢占权序(高→低): T3-X4(100) > T2-R5/R8(90) > T1(80) > T4-E(70) > 其余(50)
#   低权不得抢高权;高权抢低权也须三条件全满足:
#   ①锁龄>30min 或 心跳超时>15min ②pgrep -xc px4 与 gzserver 双 0 ③通告≥5min 无异议
# 被抢占方回来发现锁易主→写 STATUS 排队,严禁硬抢回去。
# 死亡接管不限权序(清理非抢占);接管必留 STATUS 证据(readlink+死亡依据)。
set -u
LOCK="${SITL_LOCK_FILE:-$HOME/sitl_sim/SITL.lock}"   # 测试用 SITL_LOCK_FILE 指向侧锁文件,永不触碰生产锁(T4 02:05 事故教训)
STATUSF="$HOME/sitl_sim/STATUS.md"
PRECLAIM="$HOME/sitl_sim/.lock_preclaim"
CMD="${1:-}"; STREAM="${2:-}"

note() { # note <流名> <标题> <正文>
  [ -w "$STATUSF" ] || return 0
  printf '\n%s | %s | %s | %s | %s\n' "$(date +%H:%M)" "$1" "$2" "$3" "$4" >> "$STATUSF"
}

cur_target() { [ -L "$LOCK" ] && readlink "$LOCK" || return 1; }

target_pid() { # 从 target 取 PID:倒数第二段约定为 PID;失效则从尾向前扫数字段
  local t="$1" fs n i p
  fs="${t//-/ }"; n=$(echo $fs | wc -w)
  for i in 1 2 3; do
    p=$(echo $fs | awk -v k=$((n-i)) '{print $k}')
    case "$p" in ''|*[!0-9]*) continue;; esac
    [ ${#p} -ge 2 ] && [ ${#p} -le 7 ] && { echo "$p"; return 0; }
  done
  return 1
}

pid_alive() { [ -n "$1" ] && [ -d "/proc/$1" ]; }

owner_prio() {
  case "$1" in
    *T3-X4*) echo 100;; *T2-R5*|*T2-R8*) echo 90;;
    T1-*|*T1-*) echo 80;; *T4-E*) echo 70;; *) echo 50;; esac
}

file_age() { echo $(( $(date +%s) - $(stat -c %Y "$1") )); }

atomic_take() { # 原子替换锁指向(接管/抢占唯一合法路径;禁 ln -sf)
  local nt="$1" tmp="$LOCK.take.$$.$RANDOM.tmp"
  ln -s "$nt" "$tmp" 2>/dev/null || return 1
  mv -T "$tmp" "$LOCK" 2>/dev/null || { rm -f "$tmp"; return 1; }
}

sitl_procs() { local a b; a=$(pgrep -xc px4 2>/dev/null); b=$(pgrep -xc gzserver 2>/dev/null); echo $(( ${a:-0} + ${b:-0} )); }

diskgate() {
  local avail min=$(( ${SITL_LOCK_DISK_MIN_G:-20} * 1024 * 1024 ))
  avail=$(df -k / | awk 'NR==2{print $4}')
  if [ "$avail" -lt "$min" ]; then
    echo "磁盘水位线门: 根分区可用 $((avail/1024/1024))G < ${SITL_LOCK_DISK_MIN_G:-20}G,禁起新飞行轮(E3 水位线规定;SITL_LOCK_SKIP_DISK_GATE=1 可跳,仅限非飞行锁用途)" >&2
    return 1
  fi
}

case "$CMD" in
get)
  [ -n "$STREAM" ] || { echo "用法: $0 get <流名>(建议内嵌单元标签如 T3-X4/T2-R5/T1-WD1/T4-E1)" >&2; exit 2; }
  if [ "${SITL_LOCK_SKIP_DISK_GATE:-0}" != "1" ]; then diskgate || exit 3; fi
  local_owner="$STREAM-$$-$(date +%H%M%S)"
  if ln -s "$local_owner" "$LOCK" 2>/dev/null; then
    echo "locked owner=$local_owner"; exit 0
  fi
  cur=$(cur_target 2>/dev/null || echo unknown)
  pid=$(target_pid "$cur" 2>/dev/null || true)
  if pid_alive "$pid"; then
    echo "HELD by $cur (PID $pid 活着;等锁或按权序 preclaim/force)" >&2
    exit 1
  fi
  # 死主判定:PID 不存在(rule2) 或 target 无法解析出 PID 且三重条件(rule3: 锁龄>10min+心跳超时>5min)
  if [ -z "$pid" ]; then
    age=$(file_age "$LOCK" 2>/dev/null || echo 0); mt=$(file_age "$LOCK" 2>/dev/null || echo 0)
    if [ "$age" -le 600 ] || [ "$mt" -le 300 ]; then
      echo "HELD by $cur (target 无法解析 PID 且锁龄/心跳未达三重死锁线 10min/5min,拒)" >&2
      exit 1
    fi
  fi
  # D-1010-T2-01 修复(2026-10-10 04:30 事故): owner PID=$$=锁脚本子进程,get 返回即死
  # → 活轮锁可被"合法"接管(取锁方随后进场断言 FATAL/EXIT 清理链扫杀活栈,实证
  # run_DRILLD1_N8P_042425)。接管语义=清理死场;场忙(px4/gz 活)=有活轮在飞 → 拒
  # 死主接管(要拿锁走 preclaim/force 权序)。真死场孤儿栈同样拒=强制显式清场
  # (盲接管+盲扫杀正是事故路径;owner $$→PPID 根治另案 @T4)。
  if [ "$(sitl_procs)" -gt 0 ]; then
    echo "HELD by $cur (owner PID 死但场忙 px4+gz>0=活轮在飞;死主接管禁,等锁或 preclaim/force)" >&2
    exit 1
  fi
  note "$STREAM" "锁死主接管" "完成" "readlink=$cur PID=${pid:-无} /proc 核验=不存在 → 原子接管为 $local_owner"
  atomic_take "$local_owner" && { echo "took-over from $cur owner=$local_owner"; exit 0; }
  echo "接管失败(竞态,重试)" >&2; exit 1
  ;;
heartbeat)
  [ -n "$STREAM" ] || { echo "用法: $0 heartbeat <流名前缀>" >&2; exit 2; }
  cur=$(cur_target 2>/dev/null) || exit 1
  case "$cur" in "$STREAM"-*) touch -h "$LOCK" 2>/dev/null || exit 1; exit 0;; *)
    echo "锁易主($cur),拒绝代心跳" >&2; exit 1;; esac
  ;;
hbloop)
  [ -n "$STREAM" ] || { echo "用法: $0 hbloop <流名前缀>" >&2; exit 2; }
  while :; do
    sleep 300
    "$0" heartbeat "$STREAM" >/dev/null 2>&1 || exit 0   # 锁丢/易主即自退
  done
  ;;
release)
  if [ -L "$LOCK" ]; then
    cur=$(readlink "$LOCK")
    if [ -z "$STREAM" ] || echo "$cur" | grep -q "^$STREAM"; then
      rm -f "$LOCK" && echo "released: $cur"
    else
      echo "锁属 $cur,前缀 ${STREAM:-} 不符,拒绝释放(属主守卫)" >&2; exit 1
    fi
  else
    echo "无锁"
  fi
  ;;
status)
  if cur=$(cur_target 2>/dev/null); then
    pid=$(target_pid "$cur" 2>/dev/null || echo "?")
    if pid_alive "$pid"; then st="alive"; else st="DEAD"; fi
    echo "held by $cur | PID=$pid($st) | 锁龄=$(file_age "$LOCK")s | 权序=$(owner_prio "$cur")"
  else
    echo "free"
  fi
  ;;
preclaim)
  [ -n "$STREAM" ] || { echo "用法: $0 preclaim <流名>" >&2; exit 2; }
  cur=$(cur_target 2>/dev/null) || { echo "锁空闲,无需抢占,直接 get(退出码7)"; exit 7; }
  pid=$(target_pid "$cur" 2>/dev/null || true)
  if ! pid_alive "$pid"; then echo "持有者已死(PID=${pid:-无}),直接 get 走接管路径(退出码7)" >&2; exit 7; fi
  hp=$(owner_prio "$cur"); op=$(owner_prio "$STREAM")
  if [ "$op" -lt "$hp" ]; then echo "低权($op)不得抢高权($hp): $cur" >&2; exit 4; fi
  age=$(file_age "$LOCK"); mt=$age   # 心跳即 mtime,同一度量
  if [ "$age" -le 1800 ] && [ "$mt" -le 900 ]; then
    echo "条件①未满足: 锁龄=${age}s(需>1800) 心跳龄=${mt}s(需>900)" >&2; exit 1
  fi
  n=$(sitl_procs)
  if [ "$n" != "0" ]; then echo "条件②未满足: 有 $n 个 SITL 活进程(px4/gzserver)" >&2; exit 2; fi
  printf 'claimer=%s\ntarget=%s\nts=%s\n' "$STREAM" "$cur" "$(date +%s)" > "$PRECLAIM"
  note "$STREAM" "锁抢占预通告" "进行中" "目标=$cur(权序$hp<$op) 条件①锁龄${age}s/心跳龄${mt}s✓ 条件②双0✓;异议窗 5min,到期 force"
  echo "preclaim 记录: target=$cur 权序$op>$hp 条件①②✓;5min 后可 force"
  ;;
force)
  [ -n "$STREAM" ] || { echo "用法: $0 force <流名>(须先 preclaim)" >&2; exit 2; }
  [ -f "$PRECLAIM" ] || { echo "无 preclaim 记录,先 preclaim(三条件前置)" >&2; exit 5; }
  claimer=$(grep '^claimer=' "$PRECLAIM" | cut -d= -f2)
  ptarget=$(grep '^target='  "$PRECLAIM" | cut -d= -f2-)
  [ "$claimer" = "$STREAM" ] || { echo "preclaim 属 $claimer,非 $STREAM" >&2; exit 5; }
  pw=$(( $(date +%s) - $(stat -c %Y "$PRECLAIM") ))   # 文件 mtime=preclaim 时刻(测试可 touch 伪造)
  [ "$pw" -ge 300 ] || { echo "异议窗未满: ${pw}s < 300s" >&2; exit 5; }
  cur=$(cur_target 2>/dev/null || echo GONE)
  [ "$cur" = "$ptarget" ] || { echo "属主守卫: 锁已易主($cur ≠ preclaim 时 $ptarget),中止" >&2; exit 6; }
  pid=$(target_pid "$cur" 2>/dev/null || true)
  if pid_alive "$pid"; then
    age=$(file_age "$LOCK")
    if [ "$age" -le 1800 ]; then echo "条件①失效复核: 锁龄=${age}s" >&2; exit 1; fi
    n=$(sitl_procs)
    [ "$n" = "0" ] || { echo "条件②失效复核: $n 个 SITL 活进程" >&2; exit 2; }
  fi
  nt="$STREAM-$$-$(date +%H%M%S)"
  note "$STREAM" "锁抢占完成" "完成" "被抢=$cur(异议窗${pw}s无异议) → 新属主=$nt;被抢占方请写 STATUS 排队,严禁硬抢回去"
  atomic_take "$nt" && { rm -f "$PRECLAIM"; echo "forced owner=$nt"; exit 0; }
  echo "抢占原子替换失败(竞态)" >&2; exit 1
  ;;
diskgate)
  diskgate; exit $?
  ;;
"")
  sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
  ;;
*)
  echo "未知命令: $CMD (get/heartbeat/hbloop/release/status/preclaim/force/diskgate)" >&2; exit 2
  ;;
esac
