#!/usr/bin/env bash
# E1.6 sitl_lock.sh v3 owner-契约新失效模式用例(T4 v5.31 单元5;承 e1_lock_test.sh 风格)
# 用法: bash e1_lock_test_v3.sh | tee e1_lock_tests_v3_<HHMM>.log
set -u
export SITL_LOCK_FILE="$HOME/sitl_sim/t4_evidence/TEST.lock"
LOCK="$SITL_LOCK_FILE"
SL="$HOME/sitl_sim/sitl_lock.sh"
PASS=0; FAIL=0
ck() {
  if [ "$2" = "$3" ]; then echo "PASS $1 (exit=$3) :: $4"; PASS=$((PASS+1));
  else echo "FAIL $1 (期望exit=$2 实际=$3) :: $4"; FAIL=$((FAIL+1)); fi
}
L() { echo "---- $* ----"; }

pidmax=$(cat /proc/sys/kernel/pid_max); deadpid=$((pidmax-3))
while [ -d "/proc/$deadpid" ]; do deadpid=$((deadpid-1)); done
sleep 600 & LIVEPID=$!
echo "v3 测试窗开始 $(date +%F\ %T) | deadpid=$deadpid livepid=$LIVEPID"
rm -f "$LOCK"

L "CASE-V3-1 显式活 owner get 成功+target 嵌该 PID"
out=$(bash "$SL" get V3TEST "$LIVEPID" 2>&1); rc=$?
tgt=$(readlink "$LOCK")
case "$tgt" in "V3TEST-$LIVEPID-"*) emb=Y;; *) emb=N;; esac
[ "$rc" = 0 ] && [ "$emb" = Y ] && rc2=0 || rc2=1
ck "显式活owner get+嵌入" 0 $rc2 "out=$out|target=$tgt|嵌入=$emb"

L "CASE-V3-2 活轮不可被合法接管(事故形状复验:他方 get 拒)"
out=$(bash "$SL" get V3TEST 2>&1); rc=$?
ck "活轮他方get拒" 1 $rc "out=$out|lock未易主=$([ "$(readlink $LOCK)" = "$tgt" ] && echo yes)"
bash "$SL" release V3TEST >/dev/null 2>&1

L "CASE-V3-3 显式死 owner PID 拒绝"
out=$(bash "$SL" get V3TEST2 "$deadpid" 2>&1); rc=$?
ck "死owner PID拒" 2 $rc "out=$out"

L "CASE-V3-4 非数字 owner PID 拒绝"
out=$(bash "$SL" get V3TEST2 'abc;rm' 2>&1); rc=$?
ck "非数字owner拒" 2 $rc "out=$out"

L "CASE-V3-5 默认 \$PPID 契约:包裹壳存活期持锁,target PID=包裹壳 PID"
bash -c "bash $SL get V3PPID \$\$ >/dev/null 2>&1; sleep 4" & WPID=$!
sleep 1
wtgt=$(readlink "$LOCK" 2>/dev/null)
case "$wtgt" in "V3PPID-$WPID-"*) emb3=Y;; *) emb3=N;; esac
[ -d "/proc/$WPID" ] && alive3=Y || alive3=N
[ "$emb3" = Y ] && [ "$alive3" = Y ] && rc2=0 || rc2=1
ck "默认PPID=包裹壳PID(存活期核验)" 0 $rc2 "wrapper=$WPID|target=$wtgt|嵌入=$emb3|活=$alive3"
kill $WPID 2>/dev/null; wait $WPID 2>/dev/null
bash "$SL" release V3PPID >/dev/null 2>&1

L "CASE-V3-6 死主可检测:包裹壳死后另一 get 原子接管"
# 找到 CASE-V3-5 的包裹壳已退出的 PID:重演——起后台 bash -c 长持锁,杀之,再 get
bash -c "bash $SL get V3DEAD \$\$ >/dev/null 2>&1" & WPID=$!
sleep 1
deadtgt=$(readlink "$LOCK")
kill $WPID 2>/dev/null; wait $WPID 2>/dev/null
out=$(bash "$SL" get V3NEW 2>&1); rc=$?
newtgt=$(readlink "$LOCK" 2>/dev/null)
case "$newtgt" in V3NEW-*) took=Y;; *) took=N;; esac
[ "$rc" = 0 ] && [ "$took" = Y ] && rc2=0 || rc2=1
ck "死主接管(场闲)" 0 $rc2 "旧=$deadtgt|out=$out|新=$newtgt"

L "CASE-V3-7 force 显式 owner 参数"
rm -f "$LOCK"; ln -s "V3LOW-$LIVEPID-010101" "$LOCK"
touch -h -d '-40 minutes' "$LOCK"
bash "$SL" preclaim V3FT >/dev/null 2>&1
touch -d '-6 minutes' "$HOME/sitl_sim/.lock_preclaim" 2>/dev/null
out=$(bash "$SL" force V3FT "$LIVEPID" 2>&1); rc=$?
ftgt=$(readlink "$LOCK" 2>/dev/null)
case "$ftgt" in V3FT-$LIVEPID-*) emb2=Y;; *) emb2=N;; esac
[ "$rc" = 0 ] && [ "$emb2" = Y ] && rc2=0 || rc2=1
ck "force显式owner嵌入" 0 $rc2 "out=$out|target=$ftgt"
bash "$SL" release V3FT >/dev/null 2>&1

rm -f "$LOCK" "$HOME/sitl_sim/.lock_preclaim" 2>/dev/null
kill $LIVEPID 2>/dev/null
echo "==== v3 测试窗结束 $(date +%T): PASS=$PASS FAIL=$FAIL ===="
[ "$FAIL" = "0" ]
