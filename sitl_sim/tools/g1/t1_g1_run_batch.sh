#!/bin/bash
# T1-G1 reproducer batch runner. Usage: t1_g1_run_batch.sh <rounds> <outfile>
# Private master on 11399 to avoid touching shared graph (lesson: multi-agent).
source /opt/ros/noetic/setup.bash
set -u
N=${1:-50}
OUT=${2:-/tmp/g1_pilot.log}
export ROS_MASTER_URI=http://localhost:11399
# master
roscore -p 11399 >/tmp/g1_roscore.log 2>&1 &
CORE=$!
sleep 3
rosparam set /use_sim_time false 2>/dev/null || true
# long-lived roscpp sub
/tmp/g1_sub > /tmp/g1_sub.log 2>&1 &
SUB=$!
sleep 1.5
PASS=0; FAIL=0
for i in $(seq 1 $N); do
  BEFORE=$(grep -c '^GOT' /tmp/g1_sub.log 2>/dev/null || echo 0)
  timeout 8 python3 /tmp/t1_g1_pub_once.py $i >/dev/null 2>&1
  # message-arrival window: poll up to 3s
  GOT_NOW=$BEFORE
  for w in 1 2 3 4 5 6; do
    sleep 0.5
    GOT_NOW=$(grep -c '^GOT' /tmp/g1_sub.log 2>/dev/null || echo 0)
    [ "$GOT_NOW" -gt "$BEFORE" ] && break
  done
  if [ "$GOT_NOW" -gt "$BEFORE" ]; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1))
    echo "round $i FAIL (no delivery in 3s)" >> $OUT
  done
done
echo "BATCH N=$N PASS=$PASS FAIL=$FAIL rate=$(python3 -c "print('%.3f' % ($FAIL/$N))")" >> $OUT
kill $SUB $CORE 2>/dev/null; sleep 1; kill -9 $SUB $CORE 2>/dev/null
