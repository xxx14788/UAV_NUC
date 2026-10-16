#!/bin/bash
# c3_atlas_batch_f73.sh — 甲合流 §六: F73 批(13m v7.3 真形态 25 轮)+v7.0 历史层 S 样例(5)
source /opt/ros/noetic/setup.bash 2>/dev/null
CAMP="$HOME/sitl_sim/c3_corridor_20261013"
RUNS="$HOME/sitl_sim/vins_smoke_runs"
ATLAS="$CAMP/traj_atlas_f73"
PLOT="$CAMP/c3_traj_plot.py"
mkdir -p "$ATLAS"
L13="LAYER=13m-v7.3-trueform(world-load-verified)"
L70="LAYER=v7.0-historical(C66-erratum-world;tag=crossplane-form)"
plot() { local r="$1" w="$2" l="$3" f="$4"
  local d="$RUNS/$r"
  if [ -f "$d/flight.bag" ]; then
    python3 "$PLOT" "$d" "$w" "$l" "$f" "$ATLAS/${r}.png" 2>&1 | tail -1
    echo "PLOT $r"
  else echo "SKIP $r no-bag"; fi
}
# F73 批 25 轮(13m v7.3 层; 归族=layer_rounds.csv)
plot run_C3F73E1_054246  v7 E "$L13 clean-nos miss9.12"
plot run_C3F73E2_054832  v7 E "$L13 clean-nos miss9.13 drift29"
plot run_C3F73E3_055402  v7 E "$L13 jump miss7.83"
plot run_C3F73E4_055933  v7 E "$L13 jump miss4.09"
plot run_C3F73E5_060503  v7 E "$L13 jump miss9.15"
plot run_C3F73E6_061032  v7 E "$L13 jump miss4.10"
plot run_C3F73E7_061600  v7 E "$L13 jump miss9.13"
plot run_C3F73E8_062132  v7 E "$L13 jump miss9.16 drift30"
plot run_C3F73E9_062704  v7 E "$L13 clean-nos miss4.21"
plot run_C3F73E10_063235 v7 E "$L13 jump miss1.42 best-approach"
plot run_C3F73E11_063805 v7 E "$L13 clean-nos miss9.05"
plot run_C3F73E12_064351 v7 E "$L13 clean-nos miss9.32"
plot run_C3F73E13_064937 v7 E "$L13 S-FORM-PASS jump miss9.12"
plot run_C3F73NE1_065525 v7 NE "$L13 clean-nos miss8.59"
plot run_C3F73NE2_070109 v7 NE "$L13 clean-nos miss7.61"
plot run_C3F73NE3_070718 v7 NE "$L13 jump miss7.50 drift30"
plot run_C3F73NE4_071246 v7 NE "$L13 clean-nos miss9.62"
plot run_C3F73NE5_071832 v7 NE "$L13 clean-nos miss5.38"
plot run_C3F73NE6_072418 v7 NE "$L13 clean-nos miss7.58 slowdrift0.3"
plot run_C3F73NE7_073029 v7 NE "$L13 S-FORM-PASS jump miss1.83"
plot run_C3F73NE8_073558 v7 NE "$L13 jump miss8.01 drift30"
plot run_C3F73NE9_074129  v7 NE "$L13 S-FORM-PASS jump miss8.84 STAR-CANDIDATE-13m(v9-pending)"
plot run_C3F73NE10_074851 v7 NE "$L13 clean-nos miss10.18"
plot run_C3F73NE11_075437 v7 NE "$L13 clean-nos miss4.29 drift35"
plot run_C3F73NE12_080009 v7 NE "$L13 jump miss7.27"
# v7.0 历史层 S 样例 5
plot run_C3V7NE2_005129  v7 NE "$L70 S-FORM-PASS ratio2.41-strongest-historical"
plot run_C3V7NE4_010318  v7 NE "$L70 S-FORM-PASS"
plot run_C3VFE5_020247   v7 E  "$L70 S-FORM-PASS"
plot run_C3VFNE1_023101  v7 NE "$L70 S-FORM-PASS"
plot run_C3VFNE8_031027  v7 NE "$L70 S-FORM-PASS"
N=$(ls "$ATLAS"/*.png 2>/dev/null | wc -l)
S=$(grep -c "^SKIP" /dev/stdin <<< "" 2>/dev/null || true)
echo "ATLAS-F73-DONE $N pngs"
