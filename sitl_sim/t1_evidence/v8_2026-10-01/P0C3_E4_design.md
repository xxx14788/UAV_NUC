# E-4 设计文档：EKF2-EV 启用域实验（EV_CTRL=15）+供给率复现对（T1 v8.0 P0-C.3；2026-10-01 夜1 成稿待审）

> 状态：**设计稿——过审才排飞**（任务书反盲试条款）。审阅人=用户/T2/T3 任意一位拍板即入 P1 窗 2。
> 依据：C01 DOSSIER v3（46+ 外部经验）+ P0-C.2 五场景 ulg 取证（522ade2，F 系实锤全部入设计前提）。

## 0. 前提基座（P0-C.2 新实锤对 E-4 的改写）

| # | 前提（实锤） | 对设计的强制 |
|---|---|---|
| P1 | EKF2_EV_CTRL=0 全史（六轮参数级）——"223Hz EKF2-EV 失稳"命题对象不存在 | E-4 不是"复现失稳"，是**启用域首发刻画**：EV_CTRL=15 从未跑过，一切结果都是新知识 |
| P2 | EKF2_GPS_CTRL=7 且 SITL GPS（3D/10星/~1Hz）一直在融 | **GPS×EV 并融竞争是 E-4 第一设计面**（C01 未知面升级为实锤面）；两臂必含 GPS_CTRL 处置 |
| P3 | EV 供给实速=9.1-9.6Hz（vins_to_mavros@odometry 10Hz 流），从无 223Hz EV 供给 | "223 vs 125"原表述不成立；供给率臂改为**目标 10/30/60Hz**（见 §2 A3 撤销改并） |
| P4 | VINS 尾段发散被 EKF2 门控拒收（ev 创新峰 48/157）=门控工作正常 | 判据面加"EKF2 拒收率"作健康指标（毒供入袋证据） |
| P5 | 纯视觉红线：定位层验证走 VINS；GPS 链路仅流程验证用 | E-4 属流程验证+架构知识获取实验，**非定位层验证**；EV_CTRL 改动属 SITL 域 EKF2 参数（STATUS 预告 15min 异议窗纪律），实验后回滚 |

## 1. 实验矩阵（三面正交，最小充分集 8 轮 + 回归 2 轮）

**面一（GPS 处置，2 态）**：G-on=现状 GPS_CTRL=7｜G-off=GPS_CTRL=0（纯视觉域，EKF2 只剩
baro+EV——与实机无 GPS 架构同构性最高的域）。
**面二（EV 供给密度，3 档）**：D10=现状（odometry@10Hz 经 vins_to_mavros）｜D30｜D60
（vins_to_mavros 增 rate 参数或 rosrun topic throttle 实现；**禁动 VINS 侧发布率**——毒槽位教训）。
外部锚：官方设计率 30Hz 带协方差（01 L2）；60Hz 良好/180Hz 失败唯一外部同构（01 D1，存在性参照）。
**面三（IMU 档，2 档）**：I223=511@4000us（现状）｜I125=511@5000us（lockstep 网格伪影档，红线 6
已定案其机制；仅作 EV 供给不变时的 IMU 域对照，**不做因果归因**——C01 推论二多变量混淆警戒）。

主矩阵：{G-on, G-off} × {D10, D30} × {I223} = 4 轮；+{G-off × D60 × I223}、{G-off × D30 × I125}
= 2 轮补充；共 6 轮数据 + 每态悬停回归（见 §4）。**飞行剖面统一悬停 60s**（w2a 型，最简失稳面；
机动剖面留 E-5/E-6 条件臂）。排飞顺序：先 G-off×D10（最接近纯视觉架构的启用域基线）。

## 2. 供给面实现（A3 撤销改并的落点）

- 原 T2-A3（EV 密度 30/60/223 矩阵）按任务书撤销，其密度臂=本设计面二；223 档因 P3（EV 从无
  223Hz 供给）改为"若 D60 稳则补 imu_propagate→vision_pose 直通实验臂"（单列，需 vins_to_mavros
  改造，**过审后另册**）。
- 密度实现三选一（设计留档，实现前定）：a) vins_to_mavros 加 republish-rate 参数（首选，改一处）；
  b) topic_tools throttle（零代码但引入 relay 进程时延）；c) mavros SET_MESSAGE_INTERVAL（若
  vision_pose 经 mavros 限流——顺带裁 P0-D.1 的 31.25Hz 悬案）。**排飞前完成 c) 的只读实值读取。**

## 3. 参数变更面（全部 SITL 域，预告纪律）

| 参数 | 现值 | E-4 值 | 说明 |
|---|---|---|---|
| EKF2_EV_CTRL | 0 | 15（pos+vpos+vel+yaw 全启） | 首发启用；yaw 位与磁面（SYS_HAS_MAG=1+CAL_MAG 解锁依赖，红线 5）交互入判读 |
| EKF2_GPS_CTRL | 7 | 0 或 7（面一） | G-off 臂与纯视觉架构同构 |
| EKF2_EV_DELAY | 0 | 0（不动） | 外部锚 D3：先零档，缓冲炸（"messages broken"）再入 E-5 条件臂 |
| EKF2_EVP/EVV_NOISE | 0.1/0.1 | 不动 | VINS 协方差全零→参数下限（C01 A6），入判读注记 |
| EKF2_PREDICT_US | 10000 | 不动 | P0-C.2 F-I 实值已入账 |

回滚：全部经 param set 实验后 save 前对照快照回写（磁残留教训：只 save 实验前基线，实验值不 save）。

## 4. 判据预埋（过审后禁改；全部悬停 60s 剖面）

- **J1 稳定性主判**：GT 悬停保持 ≤1m、无振荡（C01 外部验收卡同口径）+ EKF2 XY 创新比 p95<1（门内）。
- **J2 EV 融合活性**：ev_hpos/ev_vpos 创新非零且 ratio p95<1（真在融且门内）；EV_CTRL=15 生效证据=
  estimator_aid_src/innovation 中 ev 通道活跃（ulog 2Hz 采样，C01-D2 口径注记）。
- **J3 拒收率**：ev ratio>1 计数（P4：门控工作=健康指标非缺陷）；与 VINS 健康度（T2diag 心跳）分列。
- **J4 对照不变量**：px4ctrl 直供链（imu_propagate）全程健康（悬停 ≤0.15m 级，V1 基线口径）——
  分离"EKF2-EV 实验"与"直供链回归"双失败形态。
- **J5 z 通道分列**：EKF2 z vs GT z（P0-C.2 F-D 的延续观测——G-on/G-off 两臂对 z 发散形态的
  差异本身是 L2-H1 的判别数据，E-4 顺带出数）。
- **回归门**：每态实验后悬停回归 1 轮（canonical 参数）全绿才进下一态；任一回归红 ⟹ 立即回滚参数面。
- **录制清单**（E3 轮清单基础上增）：/mavros/setpoint_raw/attitude + /mavros/setpoint_raw/local
  （P0-C.2 F-G 判别遗留）+ /mavros/imu/data（33Hz 姿态臂，P0-D.1 采集项⑦）+ ulog（px4 日志全开）。

## 5. 风险与止损

- R1 GPS_CTRL=0 臂可能触 arming 检查链（GPS 依赖）⟹ 排飞前 GECO/COM_ARM 系只读核对；拒解锁则
  该臂降级"arm 后 set"流程或撤销该臂（登记不硬闯）。
- R2 EV_CTRL=15 × 磁融合 yaw 竞态（红线 5 合法面）⟹ J2 分列 yaw 融合位；疯转形态即停该臂。
- R3 连续 2 轮同因失败停跑转分析（总纲条款）；每轮磁盘水位 df<20G 门（E 线纪律）。
- R4 vins_to_mavros 改造若引入回归 ⟹ 只走参数化路径（默认值=现状零行为差），gtest 先行。

## 6. 与邻线握手

- @T2：供给密度实现若选 a) 动 vins_to_mavros ⟹ STATUS 预告+15min（你的包）；VINS 侧零改动。
- @T3：E-4 全部悬停剖面，不占 X 线场景；判据轮产出的 ulog/袋全量入 t1_evidence/v8_2026-10-01/。
- @用户：§0-P2 的 GPS 并融事实=纯视觉红线的相邻面（EKF2 内部 GPS 融合与"定位层走 VINS"架构并行
  存在），E-4 的 G-off 臂即对其的首次显式处置；拍板点=本设计过审与否。

## 7. 审阅签核栏

- [ ] 用户：设计过审（P1 窗 2 解锁条件）
- [ ] T2：供给面实现路径无异议
- [ ] T3：场景/录制清单无冲突
