#!/bin/bash
# realflight_verify_v1.sh (v1.3 2026-10-18: 分卷兼容+口径修正——仅传感器/odom 五项为必要；命令类话题按上下文注记)
source /opt/ros/noetic/setup.bash
DIR=$(ls -td ~/flight_data/*/ 2>/dev/null | head -1)
if [ -z "$DIR" ] || ! ls "$DIR"flight*.bag >/dev/null 2>&1; then echo "❌ 未找到 bag（$DIR）"; exit 1; fi
BAGS=$(ls "$DIR"flight*.bag)
echo "=== 数据包目录: $DIR ==="
echo "=== 分卷 $(echo "$BAGS" | wc -l) 个, 共 $(du -ch $BAGS | tail -1 | cut -f1) ==="
INFO=$(for b in $BAGS; do rosbag info "$b" 2>/dev/null; done)
FAIL=0
for t in "/camera/infra1/image_rect_raw" "/camera/infra2/image_rect_raw" "/camera/depth/image_rect_raw" "/mavros/imu/data" "/vins_estimator/odometry"; do
  if echo "$INFO" | grep -q "$t"; then
    C=$(echo "$INFO" | grep "$t" | awk '{s+=$2} END{print s}')
    echo "✓ $t（总 $C msgs）"
  else echo "❌ 缺必要话题: $t"; FAIL=1; fi
done
for t in "/px4ctrl/takeoff_land" "/mavros/setpoint_raw/attitude" "/position_cmd"; do
  echo "$INFO" | grep -q "$t" && echo "✓ $t（本轮用过自主命令）" || echo "○ $t 无（手持/A式手动轮属预期）"
done
for t in "/camera/rgb/image_rect_color" "/vins_estimator/feature_pts" "/tf"; do
  echo "$INFO" | grep -q "$t" && echo "✓ $t" || echo "⚠ 可选缺: $t"
done
INFRA1=$(echo "$INFO" | grep "infra1/image_rect_raw" | awk '{s+=$2} END{print s}')
[ "${INFRA1:-0}" -lt 100 ] && echo "⚠ 双目消息数偏低($INFRA1)——检查录制起始时机"
RSS=$(ls "$DIR"vins_rss.csv 2>/dev/null); [ -n "$RSS" ] && echo "✓ VINS RSS 采样: $(wc -l < "$RSS") 行" || echo "⚠ VINS RSS 采样缺失"
echo ""
if [ $FAIL -eq 0 ]; then echo "✅ 数据完整性: PASS"; else echo "❌ 数据完整性: FAIL"; fi
