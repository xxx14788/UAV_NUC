# V4.1 IMU 频率差异评估（SITL 100Hz vs 实机 200Hz，R6 登记项基础设施侧闭环）

> T1-v5 V4.1（2026-09-28 离线）。R6 表差异点"VINS IMU 源：/mavros/imu/data_raw
> 100Hz(拟) vs mavcmd 511 设 200Hz"。本文量化影响面并给出基础设施侧结论。

## 0. 拓扑事实（先厘清"谁的 IMU"）

| 消费者 | 话题 | 上游流(msgid) | SITL 实测 | 实机 |
|---|---|---|---|---|
| VINS-Fusion | /mavros/imu/data_raw | HIGHRES_IMU=105 | 125.5Hz（09-28 晨 t2w5_p1 bag，511 提频后）；09-27 W2 曾钉 50Hz（默认无 511） | 511 设 200Hz |
| px4ctrl | /mavros/imu/data（px4ctrl_node.cpp:52，源码注释明令禁改 data_raw） | ATT_QUATERNION=31 | ~50Hz | 同量级（ATTITUDE 流） |
| vins_to_mavros | /mavros/imu/data_raw（仅取戳域） | 同 VINS | 同上 | 同上 |

结论 1：**100/200 差异只存在于 VINS 输入侧**；px4ctrl 的姿态桥
（controller.cpp:51 `u.q = imu.q * odom.q⁻¹ * q`，odom 系→FCU 系换桥）
消费的是 /mavros/imu/data 的 orientation，与 511 无关，两侧链路同型。

## 1. px4ctrl 影响面（数值）

- msg_timeout/imu=0.5s：/mavros/imu/data @50Hz → 余量 25 帧；data_raw 100→50 帧、
  200→100 帧。三者均远超正常抖动（bag 实测最大 gap <3 帧），无参数调整必要。
- 主循环 ctrl_freq_max=100Hz（sitl/fpv 两 yaml 同值，WallRate）：控制新鲜度由
  主循环决定，不随 IMU 流频率变化。
- odom(imu_propagate) 100→200Hz：odom 新鲜度 10ms→5ms；位置环带宽（Kp/Kv
  整定下数 Hz 量级）相位裕度变化 <2°，可忽略。

## 2. VINS 预积分 100 vs 200（基础设施侧结论，深评归 T2 域）

- 白噪声协方差：预积分噪声按单位时间 σ² 累积，采样率加倍不改变总量
  （每步 σ²dt 减半、步数加倍，相消）。
- 离散化误差：VINS processIMU 中值积分，每步 O(dt²)、全程 O(dt) →
  200Hz 比 100Hz 离散化偏差约减半；量级在 SITL 轨迹平滑段远小于噪声项。
- 采样混叠：100Hz 采样对 >50Hz 角运动内容混叠。常规机动（悬停/巡航/避障
  加减速）姿态内容 <50Hz；翻滚/急甩类不在本项目 SITL 验证范围。
- **基础设施侧结论：100Hz 对 V1（适配验证/悬停保持）与流程层验证充分；
  视觉-惯性耦合的频域深评（视差-角速度耦合等）按 R6 归 T2 域。**

## 3. V4.2 实测计划（锁窗内与 V1.2 同轮）

1. mavros connected 后 `rosrun mavros mavcmd long 511 105 5000 0 0 0 0 0`
2. `rostopic hz /mavros/imu/data_raw` 30s 窗：记录达成率+抖动（对照 5000us 请求）
3. 追加一档 `511 105 2500`（400Hz 请求）探顶——量化 14580 链路 tick 顶
4. 结果回填 R6 表（替换"SITL 传感器插件上限"的推断性依据为实测值）
5. 若 ≥100Hz 稳定：run_ctrl_sitl_vins.launch 增加 511 步骤注释与实机同构说明；
   若 <100Hz：R6 表登记理由（实测拓扑约束）

## 3b. V4.2 实测结果（2026-09-28 晚,T2 probe6 + T1 bag 双源）

| 档位 | 实测 | dt 直方图(bag 戳) |
|---|---|---|
| 默认(未 511) | 50.00Hz | W2(09-27) 钉死;mavlink ONBOARD 默认流表 |
| 511 105 5000(200Hz req) | **124.9Hz**(probe6)/125.0Hz(bag) | 中位 8ms,分布 {4:186, 8:649, 12:186} |
| 511 105 4000(250Hz req) | **223.7Hz** | 中位 4ms,分布 {0:230, 4:1200, 8:410, 12:22} |

机制定案:请求间隔被 mavlink 任务 tick(~4ms,随负载)向上量化——5000us→8ms(125Hz),
4000us→4ms(223Hz)。**SITL 可达实机 200Hz 级**(网格对齐请求);当前链路维持
5000us/125Hz(全部已验证轮次所用值),4000us 切换属 T2 域(VINS 输入特性变化)。

## 4. 验收对照

- R6 表"VINS IMU 源"行更新义务：本单元 V4.2 执行后回填。
- run_ctrl_sitl_vins.launch 同构说明：视 V4.2 结果落地（见 V1.4 提交）。
