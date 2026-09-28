#!/usr/bin/env bash
# T2b-U3 矩阵补全+扩展批(接 U2 之后跑; 依赖 shift bag 与 U1 修复二进制)
source /opt/ros/noetic/setup.bash
set -u
C=~/sitl_sim/t2_configs
R=~/sitl_sim/bags

# ---- 3b 深挖网格: 先全部 × bag-C(冲刺, 26.7s, 区分度最大) ----
# E15 IMU 噪声 20 点
E15_DIRS=$(ls -d $C/E15_* | sort)
bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_C_shift.bag" $E15_DIRS
# E16 特征 12 点
bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_C_shift.bag" $(ls -d $C/E16_* | sort)
# E17 求解×关键帧 9 点
bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_C_shift.bag" $(ls -d $C/E17_* | sort)

# ---- 3a v1 遗欠原矩阵组 ----
# G1 补: E02 × A、B
bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_A_173156.bag" $C/E02_ext0_zfix
bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_B_shift.bag" $C/E02_ext0_zfix
# G3 补: E07 td 扫描(±40/±20, +00 与 E20 等价跳过) × B/C/E
for ms in -40 -20 +20 +40; do
  for bag in t2_B_shift t2_C_shift t2_E_shift; do
    bash ~/sitl_sim/t2_w3_batch.sh "$R/${bag}.bag" "$C/E07_td_${ms}ms"
  done
done
# G6 补: E12 平移扰动 6 向 + E13 旋转 6 向 × A、B
for e in $(ls -d $C/E12_* $C/E13_* | sort); do
  bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_A_173156.bag" "$e"
  bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_B_shift.bag" "$e"
done

# ---- E14b 工具验证: bagA 净化副本 × E20 与原 bag 对照 ----
if [ ! -f "$R/t2_A_clean.bag" ]; then
  python3 ~/catkin_ws/sitl_sim/analysis/bag_clean_imu.py "$R/t2_A_173156.bag" "$R/t2_A_clean.bag" 2>&1 | tail -2
fi
bash ~/sitl_sim/t2_w3_batch.sh "$R/t2_A_clean.bag" $C/E20_ext1_td0
echo "U3 BATCH CORE DONE"
