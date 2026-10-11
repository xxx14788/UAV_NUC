#!/usr/bin/env bash
# T4 v5.33 hbloop 属主守护面单测 v1.0（2026-10-11；侧锁制——SITL_LOCK_FILE 指向 /tmp，永不触碰生产锁）
# 被测件=~/catkin_ws/sitl_sim/sitl_lock.sh v3（d7b3efa0，零改动）；测试对象=heartbeat 属主守卫 + hbloop 易主自退
set -u
L=/tmp/t4_hbloop_test_v533.lock
S=/home/ghj/catkin_ws/sitl_sim/sitl_lock.sh
export SITL_LOCK_FILE=$L
export SITL_LOCK_SKIP_DISK_GATE=1   # 非飞行锁用途，跳 diskgate（脚本头注许可）
rm -f "$L"; pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "PASS $1 (rc=$3)"; pass=$((pass+1)); else echo "FAIL $1 (期望rc=$2 实际rc=$3)"; fail=$((fail+1)); fi; }

# T1 空场 get（v3 owner 契约：显式 $$=测试壳全程存活）
bash "$S" get T4-EHB533A $$ >/dev/null 2>&1; rc=$?
chk "T1 get 空场 owner=显式\$\$" 0 $rc
echo "  lock=$(readlink "$L" 2>/dev/null)"

# T2 heartbeat 属主守卫-阳性：匹配前缀 → rc=0 且 symlink mtime 刷新
m1=$(stat -c %Y "$L"); sleep 2
bash "$S" heartbeat T4-EHB533A >/dev/null 2>&1; rc=$?
m2=$(stat -c %Y "$L")
chk "T2 heartbeat 匹配前缀 rc" 0 $rc
if [ "$m2" -gt "$m1" ]; then echo "PASS T2b mtime 刷新($m1→$m2)"; pass=$((pass+1)); else echo "FAIL T2b mtime 未刷新($m1→$m2)"; fail=$((fail+1)); fi

# T3 heartbeat 属主守卫-阴性：非属主前缀代心跳 → rc=1 且 mtime 不变（拒绝代心跳）
m3=$(stat -c %Y "$L"); sleep 2
bash "$S" heartbeat T4-OTHER533 >/dev/null 2>&1; rc=$?
m4=$(stat -c %Y "$L")
chk "T3 非属主 heartbeat 拒绝 rc" 1 $rc
if [ "$m3" = "$m4" ]; then echo "PASS T3b mtime 未被代刷"; pass=$((pass+1)); else echo "FAIL T3b mtime 被改动!"; fail=$((fail+1)); fi

# T4 hbloop 易主自退：起 hbloop(属主A) → 5s 后释放+他主 get → 等 320s（跨一个 300s 心跳周期）→ hbloop 应自退且锁归新主
bash "$S" hbloop T4-EHB533A >/dev/null 2>&1 &
HBPID=$!
sleep 5
bash "$S" release T4-EHB533A >/dev/null 2>&1
bash "$S" get T4-EHB533B $$ >/dev/null 2>&1; rcB=$?
chk "T4b 易主后新主 get rc" 0 $rcB
sleep 320
if kill -0 "$HBPID" 2>/dev/null; then echo "FAIL T4 hbloop 未自退(易主后仍在跑)"; fail=$((fail+1)); kill "$HBPID" 2>/dev/null; else echo "PASS T4 hbloop 易主自退"; pass=$((pass+1)); fi
bash "$S" heartbeat T4-EHB533B >/dev/null 2>&1; chk "T4c 新主 heartbeat 不受旧 hbloop 影响" 0 $?

# 收尾
bash "$S" release T4-EHB533B >/dev/null 2>&1
rm -f "$L"
echo "== hbloop 属主守护面单测结果: PASS=$pass FAIL=$fail ="
[ "$fail" -eq 0 ]
