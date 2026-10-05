#!/usr/bin/env bash
# 全库 init 普查: 每轮一行 TSV. 用法: bash init_census.sh <vins_smoke_runs_dir>
set -u
D="${1:-/home/ghj/sitl_sim/vins_smoke_runs}"
printf "round\tinit_first_s\tinit_n\tloss\tcauchy\tstaged\tguard\tresult\tj0\tphase0\tslv_nan\treboots\tscene\n"
for r in "$D"/run_*/; do
  name=$(basename "$r")
  L="$r/simvins.log"
  [ -f "$L" ] || { printf "%s\tNOLOG\t0\t\t\t\t\t\t\t0\t0\t0\t\n" "$name"; continue; }
  # first Initialization finish sim-time (ros line [, t]: )
  fin=$(grep -m1 'Initialization finish' "$L" | grep -oE ', [0-9.]+\]' | tr -d ',]')
  finn=$(grep -c 'Initialization finish' "$L")
  # knobs
  knobs=$(grep -m1 'T2 knobs' "$L" | grep -oE 'loss=[0-9]+ cauchy=[0-9.]+')
  loss=$(echo "$knobs" | grep -oE 'loss=[0-9]+' | cut -d= -f2)
  cauchy=$(echo "$knobs" | grep -oE 'cauchy=[0-9.]+' | cut -d= -f2)
  staged=$(grep -m1 'T2RFIXCFG' "$L" | grep -oE 'staged=[0-9]' | cut -d= -f2)
  guard=$(grep -m1 'T2SGCFG' "$L" | grep -oE 'guard=[0-9]' | cut -d= -f2)
  res=$(head -1 "$r/RESULT.txt" 2>/dev/null | cut -c1-46 | tr -d '\t\n')
  # j0 from j0_decomp.json (any j0-like key)
  j0=""
  if [ -f "$r/j0_decomp.json" ]; then
    j0=$(python3 -c "import json;d=json.load(open('$r/j0_decomp.json'));print(d.get('j0', d.get('j0_frame_stability', d.get('j0_rev',''))))" 2>/dev/null | head -1)
  fi
  ph0=$(grep -c 'T2slv.*phase=0' "$L")
  slvnan=$(grep -c 'T2slv.*-nan' "$L")
  rb=$(grep -c 'cost gate: streak' "$L")
  # scene from name/goal
  scene=""
  case "$name" in
    *gnd*|*GND*) scene=ground;;
    *hov*|*HOV*) scene=hover;;
    *route*|*RA1[0-9]|*MACH*) scene=route;;
    *X2*|*X3*|*X1*) scene=xline;;
  esac
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$name" "${fin:-never}" "$finn" "${loss:-?}" "${cauchy:-?}" "${staged:-?}" "${guard:-?}" "${res:-?}" "${j0:-?}" "$ph0" "$slvnan" "$rb" "$scene"
done
