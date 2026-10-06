#!/bin/bash
# T2 v10.1 单元0: X5 随轮四件数据完整性核查 (59轮全扫)
OUT=~/catkin_ws/sitl_sim/t2_results/gate_science_v1/x5_integrity.tsv
printf "round\tgreen\tbag_mb\tpx4_params\tcfg_md5\thwmon_tsv\thwmon_rows\tgoal_trace\tsimvins_mb\tRESULT_verdict\n" > $OUT
for R in ~/sitl_sim/vins_smoke_runs/run_X5_*; do
  n=$(basename $R)
  # green 判定从 passmap 权威: 后续 join; 这里先记录 RESULT.txt 终态
  bag=$(du -m $R/flight.bag 2>/dev/null | cut -f1); bag=${bag:-0}
  px=$(ls $R/px4_params_*.txt 2>/dev/null | wc -l)
  pxs=MISS; [ "$px" -ge 1 ] && pxs=OK
  cfg=MISS; [ -s $R/vins_config.md5 ] && cfg=OK
  hw=MISS; [ -s $R/hwmon.tsv ] && hw=OK
  hwr=0; [ -s $R/hwmon.tsv ] && hwr=$(wc -l < $R/hwmon.tsv)
  gt=MISS; [ -s $R/goal_trace.tsv ] && gt=OK
  sv=0; [ -f $R/simvins.log ] && sv=$(du -m $R/simvins.log | cut -f1)
  rv=$(grep -o "VERDICT=[A-Za-z_-]*" $R/RESULT.txt 2>/dev/null | head -1 | cut -d= -f2); rv=${rv:-NOFILE}
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$n" "?" "$bag" "$pxs" "$cfg" "$hw" "$hwr" "$gt" "$sv" "$rv"
done
echo "rounds=$(wc -l < $OUT)"
column -t -s$'\t' $OUT | head -8
