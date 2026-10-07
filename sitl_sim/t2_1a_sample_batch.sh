#!/usr/bin/env bash
# t2_1a_sample_batch.sh -- T2 v10.4 unit-1a cross-domain healthy sampling batch
# 10 rounds: plain x5 + obstacles x5 (healthy PASS-derived configurations)
# T2_IQG_OBSERVE=1 -> per-frame [T2IQG-METRIC] lines in simvins.log (no rejection)
# Prereg: staging/INPUTFACE/calib_domainspec/1a_methodology_v1.md (roster note:
#   S8P_L2 sampled single-leg, leg2 omitted -- annotation in roster)
set -u
L="$HOME/sitl_sim"
export T2_IQG_OBSERVE=1
CELLS=(
  "1aP1_N8P  1.010 8.980 sitl_world_plain"
  "1aP2_N8Pr 1.010 8.980 sitl_world_plain"
  "1aP3_S12P 1.010 -11.020 sitl_world_plain"
  "1aP4_W5P  -3.990 0.980 sitl_world_plain"
  "1aP5_S8P  1.010 -7.020 sitl_world_plain"
  "1aO1_E12O  13.010 0.980 sitl_world_obstacles"
  "1aO2_NE8O  6.667 6.637 sitl_world_obstacles"
  "1aO3_S8O   1.010 -7.020 sitl_world_obstacles"
  "1aO4_E8O   9.010 0.980 sitl_world_obstacles"
  "1aO5_NE12O 9.495 9.465 sitl_world_obstacles"
)
mkdir -p "$L/t2_results/INPUTFACE/calib_domainspec"
ROSTER="$L/t2_results/INPUTFACE/calib_domainspec/run_roster.md"
{
  echo "# 1a sampling roster (frozen before batch, $(date "+%F %T"))"
  echo ""
  echo "| tag | source-round | world | goal | note |"
  echo "|---|---|---|---|---|"
  echo "| 1aP1_N8P | run_X4_N8P_034553 | plain | 1.010 8.980 | |"
  echo "| 1aP2_N8Pr | run_X5_N8P_195421 | plain | 1.010 8.980 | same-cfg cross-run dispersion |"
  echo "| 1aP3_S12P | run_X5_S12P_205411 | plain | 1.010 -11.020 | |"
  echo "| 1aP4_W5P | run_X5_W5P_210249 | plain | -3.990 0.980 | |"
  echo "| 1aP5_S8P | run_X5_S8P_L2_233654 | plain | 1.010 -7.020 | leg2 omitted (single-leg approx) |"
  echo "| 1aO1_E12O | run_X5_E12O_203723 | obstacles | 13.010 0.980 | |"
  echo "| 1aO2_NE8O | run_X5_NE8O_201655 | obstacles | 6.667 6.637 | |"
  echo "| 1aO3_S8O | run_X5_S8O_192525 | obstacles | 1.010 -7.020 | |"
  echo "| 1aO4_E8O | run_X4_E8O_033233 | obstacles | 9.010 0.980 | |"
  echo "| 1aO5_NE12O | run_X4_NE12O_032330 | obstacles | 9.495 9.465 | |"
} > "$ROSTER"
echo "[$(date "+%F %T")] [T2-1a] SAMPLING FLIGHT WINDOW: 10 rounds plain x5 + obstacles x5, T2_IQG_OBSERVE=1, est ~50min, no 1c replay / T4 big-IO during window" >> "$L/STATUS.md"
for cell in "${CELLS[@]}"; do
  set -- $cell; TAG=$1; GX=$2; GY=$3; W=$4
  echo "[$(date +%H:%M:%S)] == SAMP $TAG goal=($GX,$GY) world=$W"
  bash "$L/vins_smoke.sh" --world "$W" --goal "$GX" "$GY" 1.0 \
      --tag "$TAG" --budget 300 --stoploss > "/tmp/1a_${TAG}.log" 2>&1
  rc=$?
  EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
  RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
  MET=$(grep -c "T2IQG-METRIC" "$EV/simvins.log" 2>/dev/null || echo 0)
  echo "[$(date +%H:%M:%S)] == SAMP $TAG rc=$rc RESULT=${RES:-NO-RESULT} metric_frames=$MET ev=$EV"
done
echo "[$(date "+%F %T")] [T2-1a] sampling window END" >> "$L/STATUS.md"
echo "[1a-batch] complete"
