# p1 五件动态栈基准正式文书 v1.0（2026-10-11 01:3x——工程合并册单元 5）

数据正源：旧机 `~/sitl_realmachine/09_reboot_stack_2026-10-09/p1_5piece_bench_v1139.txt`
（2026-10-10T16:09:15 实测）+ 本周期 00:17 复测（VINS 重启后五件抽验）。
用途：五件栈（rs/mavros/VINS/v2m/px4ctrl[+planner]）健康判定的正式基准与
巡检规程——首飞前检查单与在役巡检共用本表。

## 1. 基准表（标称值+实测两纪元+判定门）

| 件 | 话题/证据 | 标称 | 实测 16:09（10-10） | 实测 00:17（10-11，重启后） | 判定门 |
|---|---|---|---|---|---|
| rs 相机 | /camera/infra1/image_rect_raw | 30 Hz | 29.989 | 29.937 | ≥28 Hz |
| rs 右目 | /camera/infra2/image_rect_raw | 30 Hz | 29.978 | — | ≥28 Hz |
| rs 深度 | /camera/aligned_depth_to_color/image_raw | 30 Hz | 30.079 | — | ≥28 Hz |
| mavros IMU | /mavros/imu/data_raw | 50 Hz | 49.775 | 49.565 | ≥47 Hz |
| mavros 链路 | /mavros/state | ~5 Hz | 4.898 | — | connected=1 |
| VINS odom | /vins_estimator/odometry | 15 Hz | 15.125 | 15.010 | ≥13 Hz |
| VINS 传播 | /vins_estimator/imu_propagate | 50 Hz | 49.857 | — | ≥47 Hz |
| v2m 视觉位姿 | /mavros/vision_pose/pose | 15 Hz | — | 15.268 | ≥13 Hz |
| px4ctrl | 日志新鲜度（odom/IMU 处理行持续写入） | 持续 | ✓ | ✓（00:17:36 实时写） | 写入龄<60s |
| planner | FSM 心跳（WAIT_TARGET 等状态行） | 持续 | ✓ | ✓（00:17:35 实时写） | 写入龄<60s |

注：px4ctrl/planner 无固定频率发布面（idle 态 setpoint/optimal_list 静默为
设计行为）——活性判据=日志新鲜度（非话题率）。

## 2. 巡检规程（在役/起飞前共用）

```
ssh nuc "source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash
timeout 8 rostopic hz /camera/infra1/image_rect_raw -w 8 | grep -m1 average
timeout 8 rostopic hz /mavros/imu/data_raw -w 8 | grep -m1 average
timeout 8 rostopic hz /vins_estimator/odometry -w 8 | grep -m1 average
timeout 8 rostopic hz /mavros/vision_pose/pose -w 8 | grep -m1 average
ls -la --time-style=+%T <px4ctrl.log> <planner.log>; date +%T   # 新鲜度对照"
```
判定：全部门过=五件活；任一门失=按件处置（VINS 重启规程/相机重起等）。

## 3. 数据勘误注记

- p1_5piece_bench_v1139.txt 的 "vins_node pid=701397 rss_kb=2308" 行：该 PID
  实为 vins 启动壳 bash（真 vins_node=701399）——RSS 值无效（非 vins 本体）；
  本表不采用该行；PID 取数规程改用 `pgrep -x vins_node`。
- RSS 基准（健康态，重启后 5min 内）：VINS≈95-150MB/mavros≈50MB/rs≈43MB/
  v2m≈13MB/px4ctrl≈11MB（16:09 纪元值+00:3x 复核）；VINS 高 RSS 阈值见
  内存泄漏归因报告（unit4_vins_memleak_v1140.md：健康相 2.18GB/h，保守 5h）。

## 4. 变更史

- v1139（10-10 16:09）：首次五件基准补测（p1_5piece_bench_v1139.txt）
- v1140（本件）：正式文书化+判定门+巡检规程+两纪元对照+PID 勘误+00:17
  重启后复测入册
