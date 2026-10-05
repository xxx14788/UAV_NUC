#!/usr/bin/env bash
# X 线臂配置装载/复原（T1 v11.7 单元5;v2 修复=D-1006-T1-09/boot_diff_report §9）
# v1 设计错误在案：vision_loss=1+cauchy_delta=0.0 → ceres::CauchyLoss(0.0)=NaN（风暴 5/5 根因）。
# v2 X 线正源臂 = streamguard 减 vision_loss（Huber 路径），保留 cost_gate/staged/guard=原口径 gates 防线。
# 用法: arm_xline.sh arm|restore|status
set -u
C=~/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml
B=~/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/canonical_sim_stereo_imu_config.yaml.bak
D=~/sitl_sim/t2_results/R2_dissect/cfg_streamguard/sim_stereo_imu_config.yaml
X=~/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/xline_arm_sim_stereo_imu_config.yaml
case "$1" in
  status)
    echo "canonical-now: $(grep -c t2_ "$C" 2>/dev/null || echo 0) t2 keys; loss=$(grep -m1 t2_vision_loss "$C" 2>/dev/null || echo none); cauchy=$(grep -m1 t2_cauchy_delta "$C" 2>/dev/null || echo none)"
    md5sum "$C" | cut -c1-12;;
  arm)
    [ -f "$B" ] || cp "$C" "$B"
    # X 线臂 v2 = streamguard 全键但 vision_loss 关（NaN 源移除；sed 源值守卫在案）
    sed -e 's/^t2_vision_loss: 1/t2_vision_loss: 0/' "$D" > "$X"
    grep -q '^t2_vision_loss: 0' "$X" || { echo "ARM-FAIL: vision_loss!=0 (source $D drifted?)"; md5sum "$D" | cut -c1-12; exit 3; }
    grep -q '^t2_cauchy_delta: 4.0' "$X" || echo "WARN: cauchy not 4.0 (inert under loss=0, tolerable)"
    cp "$X" "$C"
    echo "ARMED (v2 loss=0):"; grep -E "^t2_" "$C"; md5sum "$C" "$X" | cut -c1-12;;
  restore)
    [ -f "$B" ] && cp "$B" "$C" && echo "restored from backup" || echo "NO BACKUP"
    md5sum "$C" | cut -c1-12;;
esac
