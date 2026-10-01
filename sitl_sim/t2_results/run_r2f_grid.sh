#!/usr/bin/env bash
# R2F discrimination grid (prereg=fixface_prereg.md af2f5d6c)
# serial, single-replay discipline, private master 11312 (inside t2_replay.sh)
set -u
R=~/sitl_sim/t2_replay.sh
B=~/sitl_sim/bags/t2_C_033818_shift.bag
G=~/sitl_sim/bags/t2v3_ground_210307.bag
O=~/sitl_sim/vins_smoke_runs/run_U3PO_211438/flight.bag
P=~/sitl_sim/bags/t2v3_route_213717.bag
md5sum ~/catkin_ws/devel/lib/libvins_lib.so ~/catkin_ws/devel/lib/vins/vins_node > ~/sitl_sim/t2_results/r2f_grid_stack_md5.txt
bash $R R2F_G0a1 $B /tmp/r2f_cfg/base  && echo GRID_G0a1_DONE
bash $R R2F_G0a2 $B /tmp/r2f_cfg/base  && echo GRID_G0a2_DONE
bash $R R2F_G1_d05 $B /tmp/r2f_cfg/d05 && echo GRID_G1_DONE
bash $R R2F_G2_d10 $B /tmp/r2f_cfg/d10 && echo GRID_G2_DONE
bash $R R2F_G3_d20 $B /tmp/r2f_cfg/d20 && echo GRID_G3_DONE
bash $R R2F_G4_ground $G /tmp/r2f_cfg/d20 && echo GRID_G4_DONE
bash $R R2F_G5_po $O /tmp/r2f_cfg/d20 && echo GRID_G5_DONE
bash $R R2F_G6_route $P /tmp/r2f_cfg/d20 && echo GRID_G6_DONE
echo GRID_ALL_DONE
