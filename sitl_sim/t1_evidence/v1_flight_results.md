# V1.2/V1.3 实测结果（T2 W1.1/W1.2 bag 共享分析,2026-09-28 晚）

> 数据源（一方执行结论共享,任务书授权）:
> - V1.2 地面静态: t2v3_ground_202520.bag（T2 W1.1 第二轮,obstacles world,45s 静置,511 提频后）
> - V1.3 悬停: t2v3_hover_203248.bag（T2 W1.2,起飞0.75m 悬停30s 降落,px4ctrl VINS odom 直供）
> 分析器: t1_evidence/v1_ground_analysis.py / v1_hover_analysis.py（口径双份:px4ctrl 视角+gazebo 真值）

## V1.2 地面静态（结论:无超时抖动风险,静态漂移量级合格）

| 指标 | 实测 | 判定 |
|---|---|---|
| imu/data_raw（511 105 5000 后） | **125.0Hz**, maxgap 12ms, n=5660 | V4.2 5000us 档=125Hz（14580 链路,请求 200Hz） |
| imu_propagate | 125.0Hz 同条数逐帧,maxgap 12ms | 与 IMU 同频零断流;0.5s 超时余量 60+ 帧 |
| EKF2 odom（参照） | 30.0Hz, maxgap 40ms | 契约表 30Hz 复证 |
| vision_pose（vins_to_mavros） | 9.5Hz | EV 融合喂入率参考 |
| VINS 静态漂移(45s) | 幅度 0.010/0.025/0.018m,首末差最差 0.017m | ~2-3cm/min 量级,远小于 0.5s 超时语义,悬停尺度合格 |
| 真值静止(gazebo) | 幅度 ≤0.0003m | 漂移全部来自 VINS 侧（视觉估计）,非机体移动 |
| VINS 原点 vs 出生点 | 首条 prop=(0,-0.023,-0.001) vs gt 出生=(1.010,0.980,0.104) | T2b U9 出生点平移假象(+1.01,+0.98)复现确认,登记不改判 |

待补（另一 T1 实例 ground 轮）: /debugPx4ctrl/fsm_state 全程稳定性(px4ctrl 静置态无 odom 超时态跳变)、511 默认档与 2500us 档实测、init 时长计时。

## V1.3 悬停保持（结论:PASS,优于 GPS 代位基线一个量级）

悬停段=takeoff+12s~+42s（settle 12s + hold 30s）:

| 口径 | 中位偏差 | p95 | max | σ_xyz (m) |
|---|---|---|---|---|
| A: imu_propagate（px4ctrl 消费源） | **0.005m** | 0.015m | 0.021m | (0.006,0.004,0.004) |
| B: gazebo 真值 | 0.006m | 0.020m | 0.021m | (0.007,0.004,0.005) |
| C: EKF2 odom（参照,GPS 代位旧源） | 0.050m | 0.085m | 0.090m | (0.026,0.018,0.043) |

- 判定: 口径A 0.005m ≪ 0.03m 基线 → **PASS**（VINS odom 直供下悬停保持优于 GPS 代位链,
  且 A<C: px4ctrl 直接锚 VINS 系比 EKF2 融合输出更稳）。
- 30s 悬停 125Hz 持续无断流: 若 odom 断 >0.5s,px4ctrl 回 MANUAL_CTRL 掉高——未发生
  （行为级 fsm 稳定证据;fsm_state 话题级证据待另一实例轮）。
- VINS hold 中位=(0.146,0.296,0.720) vs 真值=(1.208,1.299,0.843): 差 ≈(1.06,1.00)=出生点
  平移假象（同上）,相对保持不受影响。

## 补充:T1 自跑 salvage 轮(21:15,接管条款)+ V4.2 三档终值(2026-09-28 21:1x)

数据源: v1_ground_salvage_211520.bag(T1 ground 轮打捞;链=run2 的 obstacles world 会话,
VINS 已 init 后录制 67s 静置,preflight ALL_GREEN,fsm_state 双话题在内)。

| 指标 | 实测 | 备注 |
|---|---|---|
| fsm_state 稳定性 | **67 帧全程 MANUAL_CTRL(state_recv=1 odom_recv=1),0 跳变** | V1.2 fsm 稳定性证据闭环:静置全程 odom 健康位恒 1,无超时态闪跳 |
| imu_propagate | 124.8Hz,maxgap 20ms,n=8380 | 与 T2 bag 一致(125Hz 档) |
| ekf odom / vision_pose | 30.0Hz / 9.7Hz | 复证 |
| 静态游走(67s,VINS 龄~150-215s 窗) | 幅度 0.079/0.126/0.032m,**首末差 0.001/0.004/-0.005m** | 零均值游走非漂移;比 T2 早期窗(2.5cm)大——近地相机几何差/视觉优化重锚微跳嫌疑,长窗影响归 T2 域(W2);悬停实测 0.5cm 不受影响 |
| VINS 原点 vs 出生点 | (-0.035,0.053,-0.010) vs (1.010,0.980,0.104) | 出生点平移假象第三次复现 |

### V4.2 三档终值(run2 21:12,14580 链路,obstacles world)

| 档位 | 实测 |
|---|---|
| 默认(未 511) | **50.000Hz** |
| 511 105 5000 | **125.000Hz** |
| 511 105 2500(400Hz req) | **215.1Hz**(与 probe6 的 4000us=223Hz 合并:网格量化 ~4ms tick) |

### 工具教训(跨会话保留)

1. **rostopic echo 字段路径(/topic/field)订阅假阴性**:报 "does not appear to be published"
   而裸话题 hz 正常——本环境两度误杀活链;判流必须裸话题 echo 或 hz。
2. v1_flight.sh 原版 FATAL 路径不清理(链+锁泄漏)——salvage 教训,编排脚本 FATAL 前须
   走清场段(已修:门探针改裸话题;FATAL 清场责任在使用者,脚本尾部正常路径含 t3_clean)。
3. empty world 无纹理→VINS 走 T2-W3 已立案的"无条件 init"劣化路径;VINS 链路一律用
   sitl_world_obstacles(脚本默认已改)。
