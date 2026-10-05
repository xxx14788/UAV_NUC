#!/usr/bin/env bash
# X 线臂配置装载/复原（T1 v11.7 单元5;cfg_streamguard 减 cauchy=X 线正源臂）
# 用法: arm_xline.sh arm|restore|status
set -u
C=~/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml
B=~/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/canonical_sim_stereo_imu_config.yaml.bak
D=~/catkin_ws/sitl_sim/t2_results/R2_dissect/cfg_streamguard/sim_stereo_imu_config.yaml
X=~/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/xline_arm_sim_stereo_imu_config.yaml
case "$1" in
  status)
    echo "canonical-now: $(grep -c t2_ "$C" 2>/dev/null || echo 0) t2 keys; cauchy=$(grep -m1 t2_cauchy_delta "$C" 2>/dev/null || echo none)"
    md5sum "$C" | cut -c1-12;;
  arm)
    [ -f "$B" ] || cp "$C" "$B"
    # X 线臂 = streamguard 全键但 cauchy 关（不入正源维持）
    sed 's/^t2_cauchy_delta: 4.0/t2_cauchy_delta: 0.0/' "$D" > "$X"
    cp "$X" "$C"
    echo "ARMED:"; grep -E "^t2_" "$C"; md5sum "$C" "$X" | cut -c1-12;;
  restore)
    [ -f "$B" ] && cp "$B" "$C" && echo "restored from backup" || echo "NO BACKUP"
    md5sum "$C" | cut -c1-12;;
esac
