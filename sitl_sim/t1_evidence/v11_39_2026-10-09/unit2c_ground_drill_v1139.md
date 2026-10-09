# 2c 地面版演练（不解锁版）证据件（T1 v11.39；2026-10-10 06:00-06:05）

> 台账=旧机 `10_physwin_pre_record/drill_2c_v1139/`（baseline_odom_hz/baseline_state/inject_kill_time/monitor_v1_events.log/odom_alarm.flag）。
> 环境=2a 复苏栈全活（mavros 50Hz IMU+infra 30Hz+depth 30Hz+VINS+px4ctrl 修复版二进制+planner 2e 适配稿）。

## 演练序与观察

| 步 | 时刻 | 动作/观察 | 结果 |
|---|---|---|---|
| 基线 | 06:00 | odom=15.16Hz；**armed=False（不解锁态）** | ✓ 不 arm 不怠速 |
| 注入 | 06:01:00 | kill -9 vins_node(pid 93718)（地面态杀 VINS） | ✓ |
| 观察① | 06:01-06:02（65s 窗） | px4ctrl [HAFIX] 行计数 | **0 行**（见判读 A） |
| 观察② | 06:02-06:04 | 监控 v1 告警链 | **TIMEOUT NEW(no-odom>30s)+TIMEOUT PERSIST #1+odom_alarm.flag 置位** ✓ |
| 复苏 | 06:05 | 重起 VINS | odometry 14.86Hz ✓（健康态回归） |

## 判读 A：watch 零触发=地面态 flying 门设计边界（非输入链缺陷）

- 订阅链核查（rosnode info /px4ctrl）：**/vins_estimator/imu_propagate（odom 直供）+/mavros/extended_state（landed 源）+/mavros/state（armed 源）全订阅**——输入链完备；
- HAFIX watch 判定=flying（armed&&!landed）∧odom 死。本演练 armed=False→flying=False→watch 不启动=**设计边界实证**（地面态 VINS 死不构成飞行安全事件）；
- **失效面核查定论**：昨晚（10-09）实机 odom 断链全程 watch 0 触发=同因（地面态），**非 watch 输入链缺陷**——T1 域新发现解除（预判的"输入链缺陷"分支不成立，登记为设计边界+兜底层如下）；
- 地面态 VINS 死的双兜底=①L2 拒飞门（RJ_NO_ODOM：起飞请求被拒，SITL gtest 在案）②监控 v1 TIMEOUT 告警（本演练实证 60s 内触发+flag 置位）。

## 判读 B：修复链实机首次验证（覆盖面如实注记）

- 本演练=**HAFIX 修复版（P-1 400+179 双 kill/P-2 landed 门）二进制的实机进程内首跑**：watch 判定面在实机确认（零误触发+订阅链活）；
- **梯②③（KILL/disarm）需飞行态，本不解锁版未覆盖**——梯②③验证面=SITL 20 轮复验批（干测 1 已实证时序链：watch→AUTO_LAND→KILL cmd400 ACCEPTED；179 生效验证=干测 6/复验批）。

## 覆盖面注记（降级版）

不解锁降级版：不 arm 不怠速→飞行态 HAFIX 全梯（AUTO_LAND 盲降/KILL/disarm landed 门）不在本演练覆盖面；完整怠速版待动力套修复后补（动力套三项=用户裁定跳过注记维持）。M1 行 4 半件收口带降级注记。
