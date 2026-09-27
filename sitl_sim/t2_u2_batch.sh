#!/usr/bin/env bash
# T2b-U2 复审批:干净 init(平移 bag)下重审 td/ext 判决 + mono 复测
# 依赖 U1 修复后的 vins 二进制与 t2_[BCDE]_shift.bag
set -u
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
C=~/sitl_sim/t2_configs
R=~/sitl_sim/bags

# stereo 复审: E01(ext2)/E03(ext1)/E06(td_off)/E20(final) × B/C/E(shift)
for bag in t2_B_shift t2_C_shift t2_E_shift; do
  bash ~/sitl_sim/t2_w3_batch.sh "$R/${bag}.bag" \
    $C/E01_baseline $C/E03_ext1 $C/E06_td_off $C/E20_ext1_td0
done

# mono 复测: E04(left)/E05(right) × A(原始,sim域) / B_shift / C_shift
for bag in t2_A_173156 t2_B_shift t2_C_shift; do
  bash ~/sitl_sim/t2_w3_batch.sh "$R/${bag}.bag" \
    $C/E04_mono_left $C/E05_mono_right
done
echo "U2 BATCH DONE"
