# px4ctrl

PX4 位置控制器：读 VINS 里程计 + `PositionCommand`，输出 `AttitudeTarget`（本机跑位置环）
或 `PositionTarget`（PX4 跑位置环，`use_px4_position_ctrl` 选择），并把起飞/降落/接力
做成一个五态状态机（`MANUAL_CTRL / AUTO_HOVER / CMD_CTRL / AUTO_TAKEOFF / AUTO_LAND`）。

## 怎么跑

```bash
# 实机（里程计 = /vins_estimator/imu_propagate，参数 = config/ctrl_param_fpv.yaml）
roslaunch px4ctrl run_ctrl.launch

# SITL（里程计 = mavros EKF2 本地位置，无 VINS）
roslaunch px4ctrl run_ctrl_sitl.launch

# SITL + 仿真 VINS（里程计 = /vins_estimator/imu_propagate）
roslaunch px4ctrl run_ctrl_sitl_vins.launch
```

三个 launch 的 **node name 必须都是 `px4ctrl`**：源码里用 `nh("~")` 解析私有话题
（`~takeoff_land`、`~odom`、`~cmd`），改名会改私有话题名。

## 参数在哪

| 文件 | 用途 |
|---|---|
| `config/ctrl_param_fpv.yaml` | 实机 |
| `config/ctrl_param_sitl.yaml` | SITL |

两份必须保持**键集一致**（值可不同）。检查：

```bash
python3 tools/ci/param_face_diff.py          # 差集必须 ⊆ config/params_diff_allowlist.yaml
python3 tools/ci/param_consumption_audit.py  # 每个键必须有消费点，输出 0 ZOMBIE
```

## 话题

| 方向 | 话题 |
|---|---|
| 订阅 | `~odom`、`~cmd`、`~takeoff_land`、`/mavros/state`、`/mavros/extended_state`、`/mavros/imu/data`、`/mavros/imu/data_raw`、`/mavros/rc/in`、`/mavros/battery`、`/vins_estimator/camera_pose`、`/vins_estimator/reboot_notify` |
| 发布 | `/mavros/setpoint_raw/attitude`、`/mavros/setpoint_raw/local`、`/debugPx4ctrl`、`/debugPx4ctrl/fsm_state`、`/traj_start_trigger` |

## 已删除的配置键（2026-11-10，整改 F-06）

下列键**曾被读取但全仓无消费点**，即改它们对飞行毫无影响。已从参数读出代码与两份 yaml
一并删除。若在旧文档/旧 yaml 里见到，请按此表理解为"不存在"：

| 键 | 为什么删 |
|---|---|
| `low_voltage` | 低压门从未实现。**不要以为有低压保护**——起飞前用外部电压表确认（≥14.0 V） |
| `pose_solver` | 姿态解算已固化为几何法（`attitude_utils.h`），"三选一"不存在 |
| `thrust_model/accurate_thrust_model`、`K1`、`K2`、`K3` | 推力模型已简化为 `hover_percentage` + RLS |
| `rotor_drag/x,y,z,k_thrust_horz` | 控制律无桨阻项 |
| `gain/Kvi0..2` | legacy 路径无积分；v2 的积分在 `ctrl_core.h` 内部 |
| `gain/Kvd0..2` | 从未读入 |
| `gain/KAngR/P/Y` | bodyrate 控制器未实现（见下） |
| `msg_timeout/bat` | 唯一消费者 `bat_is_received()` 无调用者，一并删除（电压本身仍用于 debug 回显） |

同时删除了两个无调用者的函数：`PX4CtrlFSM::bat_is_received()`、`PX4CtrlFSM::recv_new_odom()`。

## 已知限制

- **bodyrate 控制器未实现**：`LinearControl` 从不产生角速度指令，`use_bodyrate_ctrl=true`
  会让节点在启动时直接拒绝运行（2026-11-10 起）。要实现请另立任务。
- **`ctrl_core.h` 里 8 个函数未接线**：`shapeRef / refSettled / takeoffRef / takeoffArrived /
  landStep / slewTilt / eqHeight / maxHoverableThrust`（W6 起飞/降落参考整形与解析式）。
  有 gtest 覆盖，但**不参与控制**；改它们不影响飞行。
- **实机 `odom_gate/enabled_v2` 缺省关闭**：SITL yaml 显式开，实机 yaml 未写键（= false）。
  即实机的里程计 v2 门比 SITL 弱，这是已知的不对称（整改 F-03 已显式化，未改行为）。

## 测试

```bash
catkin build px4ctrl && catkin run_tests px4ctrl --no-deps
```

8 个 gtest 目标：`test_controller_attitude`、`test_odom_sanity`、`test_odom_sanity_v2`、
`test_fsm_decision`、`test_cmdresp_gate`、`test_ctrl_core`、`test_ground_lock`、
`test_reinit_reset`（2026-11-10 起新增 `test_rc_centered`、`test_pose_jump`）。
