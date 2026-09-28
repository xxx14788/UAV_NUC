# T1-V1 实测结果（V1.2 地面 + V1.3 悬停 + V4.2 提频）— 2026-09-28 夜

> 数据源三袋：`v1_ground_salvage_2115.bag`（本会话挽救轮，68.7s 静置，栈=obstacles world
> +511@5000us）、`~/sitl_sim/bags/t2v3_ground_202520.bag`（T2 W1.1 轮，45.3s）、
> `~/sitl_sim/bags/t2v3_hover_203248.bag`（T2 W1.2 轮，138s，悬停窗 63.5s）。
> 频率探针两轮独立一致（rate511.txt + v1_ground_run2.log）。

## V1.2 地面静止（px4ctrl 常驻 VINS odom，不起飞）

| 指标 | 挽救轮(68.7s) | T2 轮(45.3s) | 判读 |
|---|---|---|---|
| imu_propagate 频率 | 125.0Hz | 125.0Hz | =IMU 流逐帧发布实证 |
| 发布最大间隙 | 0.020s（2.5 帧） | 0.016s（2.0 帧） | **无丢帧窗口**；0.5s 超时余量 25 倍，msg_timeout 不调 |
| 静止漂移率（自锚首条） | 0.049 m/min（XY max 0.130m） | 0.025 m/min（XY max 0.022m） | 两轮同阶 0.02-0.05；z 均 ≤0.029m |
| gazebo 真值底噪 | 0.0000m | 0.0002m | 漂移纯估计侧 |
| EKF2 odom 同轮漂移 | 0.045m/72s | 0.081m/45s | 同量级（EKF2 有 vision_pose 融合，磁残留污染 yaw） |
| fsm 稳定性 | 69/71 帧 MANUAL_CTRL odom_recv=1；2 帧 recv=0 | （T2 未录 fsm） | recv=0 两帧在 bag 末尾=清场杀 VINS 伪影，非真丢帧 |
| init 真瞬态（首条后 2s |v|） | （bag 始于 init 后，见尖峰行） | **0.016 m/s** | 远低于 FSM 静止门 0.1——起飞时序无忧 |
| **重锚尖峰（新发现）** | \|v\| 峰 1.15 m/s@stamp306/314，伴随 XY 偏移 0.13m | 未见（窗短） | 优化器视觉更新对 latest_P/V 的修正尖峰；静止真值 0 证明非真实运动。对 FSM 静止门构成瞬时威胁（起飞重试环可吸收），对悬停为扰动源 |

## V1.3 悬停保持（T2 W1.2 袋，悬停窗 63.5s，7937 帧）

| 口径 | XY mean | XY max | σx/σy | z mean/max | 3D rms/max |
|---|---|---|---|---|---|
| VINS 系（控制口径） | 0.115m | 0.125m | 0.084/0.079 | 0.020/0.205m | 0.118/0.228m |
| gazebo 真值系（绝对） | 0.125m | 0.133m | 0.096/0.081 | 0.016/0.194m | 0.127/0.226m |
| 对照 GPS 代位链 | ≤0.03m 量级 | — | — | — | — |

判读：
- **契约安全**：起飞→悬停→降落全程无发散、无 fsm 降级（T2 轮记录）。
- **精度等级退化 0.03→0.12m class**：两口径同量级=真实保持退化非估计假象。
  主导因素=飞行激励下 VINS 漂移升至 0.153 m/min（窗内真值系锚点位移 dx0.093/dy-0.079/dz-0.196）
  + 重锚尖峰扰动。纯视觉无回环的物理预期，非缺陷。
- **下游影响**：EGO 导航（~0.3m 级精度需求）充足；精密悬停/精准降落不足——R6 登记
  sim-real 预期 + T2 域（回环选项/漂移抑制）评估项。

## V4.2 mavcmd 511 提频实测（两轮独立一致）

| 档 | 请求 | 实测 |
|---|---|---|
| 默认（无 511） | — | **50.0Hz**（W2"50Hz 顶"结论实锤；R6 旧表"SITL 100Hz"系误记，待改） |
| 511 105 5000 | 200Hz | **125.0Hz**（过 T2 preflight 100Hz 门；受 mavlink 流调度/RTF 节流） |
| 511 105 2500 | 400Hz | **215-220Hz**（证明 125 非链路硬顶；该档带宽浪费不采用） |

- px4ctrl 姿态桥 /mavros/imu/data：33Hz（V4.1 评估记 ~50Hz，实测下修；msg_timeout 余量 16 帧，不调）
- 结论：**五件套编排内 511@5000 是必须且充分的实机同构步骤**（T2 t2v3_flight.sh 已内置；
  v1_flight.sh 同；R6 表回填实测值）。

## 附带发现与遗留

1. **CAL_MAG0_ID=197388 / CAL_MAG1_ID=197644 非零残留**（env_health 第 1 项在线检出，
   w4 磁污染残留仍在 SITL PX4 参数区）。复位尝试因 master 已亡未遂——**遗留：下次 SITL
   起栈后 `rosservice call /mavros/param/set "{param_id: 'CAL_MAG0_ID', integer: 0}"`
   （CAL_MAG1 同），env_health 复验。对 VINS 直供链路无害（EKF2 不在控制链），
   但污染 local_position（T2 route 监视器用的正是它——T2 请知悉）。
2. v1_flight.sh 的 init 门 80s 偏短（本轮 obstacles world 冷 init 实测 ~119s），建议 40→90
   循环（180s）；FATAL 路径不清场（锁残留+孤儿栈，本夜两次实证）——建议 FATAL 分支补
   t3_clean 调用。两处修复归并行实例（脚本 owner）或下次提交。
3. 空 world 无法 VINS init（无特征无视差）——v1_flight.sh 默认 empty world 已证不可用，
   需 SITL_WORLD=sitl_world_obstacles 覆盖或改默认值。

## 证据索引

- 挽救轮：`t1_evidence/v1_2026-09-28/{v1_ground_salvage_2115.bag, record_salvage.log,
  v1_ground_run2.log, rate511.txt(前轮), simvins_ground.log}`
- V3 在线回归：`~/sitl_sim/t1_evidence/v3_withsitl_regression.log`（六项全出=修复生效；
  两项 FAIL=真实磁残留，检出正确）
- 分析脚本：`sitl_sim/analysis/{v1_ground_analysis.py, v1_hover_refine.py}`

## V1.3 口径调和（21:2x 双实例数字差异裁决）

| 口径 | 定义 | VINS | EKF2(同窗) | 参考语义 |
|---|---|---|---|---|
| 绝对保持（对悬停锚点，63.5s 窗） | dev from held point | **median 0.117 / mean 0.115 / max 0.125** | median 0.087 / max 0.144 | **≤0.03m 基线即此口径**（T1 v4 smoke 悬停保持语义） |
| 短期稳定（滚动锚/噪声底） | 相邻段内抖动 | ~0.005（并行实例口径，真实） | ~0.050 | 噪声底，非保持质量 |

判读：V1.3 双口径并存——绝对保持 ~0.12m class（对 0.03m 基线 4×），且 **EKF2 带视觉融合同窗同
0.087 级**→差距是纯视觉架构属性（视觉锚定游走 vs GPS 锚定），非 px4ctrl/VINS 缺陷；短期噪声底
5mm 优。结论维持：契约安全 PASS（导航级），精密保持不达 GPS 代位级，R6 登记预期+T2 域改进项。
