#!/bin/bash
# c3a_cam_rate.sh — Phase A 相机 sensor update_rate 切换器（③C-甲 §二；SDF 级参数域）
# 用法: c3a_cam_rate.sh <rate|restore>
#   <rate>   = 双目 sensor <update_rate> 设为该值（只动 sensor 级 <update_rate>N</update_rate>，
#              禁触 plugin <updateRate>——不同标签名天然防误伤；两处同步改=单参数单变量）
#   restore  = 还原备份原值（30）
# 指纹纪律: 首次备份 → stereo_vins_rig.sdf.bak_jia；每次操作后 md5+grep 校验回显。
set -u
SDF="$HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/stereo_vins_rig/stereo_vins_rig.sdf"
BAK="${SDF}.bak_jia"
if [ ! -f "$BAK" ]; then cp "$SDF" "$BAK"; echo "backup created: $(md5sum "$BAK")"; fi
if [ "$1" = "restore" ]; then
  cp "$BAK" "$SDF"
else
  sed -i "s|<update_rate>[0-9]*</update_rate>|<update_rate>$1</update_rate>|g" "$SDF"
fi
n=$(grep -c "<update_rate>" "$SDF")
vals=$(grep -o "<update_rate>[0-9]*</update_rate>" "$SDF" | tr '\n' ' ')
plug=$(grep -o "<updateRate>[0-9]*</updateRate>" "$SDF" | sort -u | tr '\n' ' ')
echo "NOW: md5=$(md5sum "$SDF" | cut -d' ' -f1) sensor_update_rate(n=$n): $vals plugin_updateRate: $plug"
[ "$n" = "2" ] || { echo "FATAL: sensor update_rate count != 2"; exit 9; }
