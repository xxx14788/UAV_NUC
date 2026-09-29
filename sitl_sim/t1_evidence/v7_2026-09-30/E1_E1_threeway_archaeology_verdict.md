# T1-E1 取证#0 三合一考古裁决（E-1）：EKF2-EV 融合从未启用——W2 悬案问题定义整体改写（2026-09-30 夜）

状态：E-1 完成（读参/launch 快照/V1 档位/场景对应表/EV 帧计数五项全出，含 C01 判据外的新事实）。
执行者：T1 v7 夜 1。全部 0 锁（ulog/参数文件/脚本/git 只读）。

## 0. 结论摘要（三句话）

1. **EKF2_EV_CTRL=0 全时线恒定（09-22→09-29 全部 90+ ulg 零例外）且 cs_ev_pos/vel/hgt/yaw 整轮 n_true=0**
   ——EV 融合在这台 NUC 的整个 SITL 历史上**从未启用过**；vision 数据全程健康到达 PX4（9.6Hz）被完全忽略。
2. **"W2 五场景全败=EKF2-EV 控制失稳@223Hz"叙事死亡**：W2 链路实为 OFFBOARD flyer 直控 PX4 位置环
   （px4ctrl 不在环，t2v3_flight.sh case 分支实证）+EKF2（GPS+baro+mag，非 EV）反馈。
3. **W2 失效=双层叠加**：层 1=VINS 发散（obstacles 场景条件性，T2-W-A 域，ATE 36.8-53.7m 数字主源）；
   层 2=飞机物理失控（z 通道主导超调 1.8-8.0m，EKF2/GPS 反馈正常，GT-local 恒差 1.4m=出生点），
   125Hz 轮 1 健康史 ⟹ **223Hz 条件性保留，机制面改写为纯 PX4 内部域**（位置环@223Hz 体制）。

## 1. 读参落表（C01 E-1 判据项 1；H1/H2 三叉裁决）

来源：ulog initial_parameters（轮级快照，W1.3 r2=03_26_35.ulg 与 w2b=04_11_30.ulg 完全一致；
时间线扫描 09-22/23/26/28/29 共 90+ ulg 全部 EV_CTRL=0）。

| 参数 | 实值 | C01 假设面判读 |
|---|---|---|
| EKF2_EV_CTRL | **0** | bit0-3 全关：EV 数据零融合（数据面实锤见 §3） |
| EKF2_PREDICT_US | 10000 | 非三叉任一预期焦点；但 EV 不融 ⟹ 抽稀假设（H1/H2）无对象 |
| EKF2_EV_DELAY / EV_NOISE_MD | 0 / 0 | 未启用 |
| EKF2_EVP_NOISE / EVP_GATE | 0.1 / 5.0 | 未启用 |
| EKF2_EVV_NOISE / EVV_GATE | 0.1 / 3.0 | 未启用 |
| EKF2_TAU_POS / TAU_VEL | 0.25 / 0.25 | M2 增补项落表（输出平滑延迟，D8 相关） |
| EKF2_GPS_CTRL / BARO_CTRL | 7 / 1 | GPS 全融合+baro 在融（W2 实际反馈源） |
| EKF2_GYR_B_NOISE | 0.001 | C10 项落表 |

**裁决：H1/H2（PREDICT_US 限幅抽稀→融合失稳）前提死亡**——抽稀机制（estimator_interface.cpp 的
_min_obs_interval）作用于 EV 融合管线，融合不存在则无失稳通道。EV 速率限幅签名（"EV data too fast"）
机制上仍可能打印（数据注入层），但无控制后果。

## 2. 0.5 接线裁决 + launch 快照还原（C01 E-1 判据项 2）

重建依据：`/home/uav/sitl_sim/t2v3_flight.sh`（T2 W1/W2 统一编排，git 外运行时副本）+ repo launch 实读。

| 项 | W1.3 route（PASS） | W2 五场景（全败） | 分界含义 |
|---|---|---|---|
| px4ctrl | **在环**（run_ctrl_sitl_vins.launch，case hover\|route 分支） | **不在环**（w2* 分支不启动） | 04 C1"px4ctrl 直供 vs EKF2-EV 支路"的分界表述作废 |
| 控制器 | px4ctrl 串级 PID（odom=imu_propagate 直供） | **PX4 内部位置环**（flyer 发 /mavros/setpoint_raw/local PositionTarget@10Hz OFFBOARD） | W2=纯 PX4 域 |
| 位置反馈 | VINS 直供（不经 EKF2） | EKF2 local_position（GPS+baro+mag，**无 EV**） | — |
| world | sitl_world_obstacles（:29 写死） | 同左 | **H13（场景混淆作分界）出局**；但 obstacles 的 VINS 发散是 W2 ATE 数字主源（层 1） |
| VINS/vins_to_mavros | sim_vins.launch（vins+vins_to_mavros 在跑） | 同左 | vision_pose 供给存在但 EKF2 不融（§3） |
| IMU 档 | 4000us/223Hz（511-105-4000） | 同左 | 同栈 |

**裁决：0.5 = "W2 无 px4ctrl、无 EV 融合、OFFBOARD 直控 PX4"**——C01 因子树 D 线（消费面）的
D1/D2/D5/D8 条件结论全部失效（前提拓扑不存在）；A1.1（EV 桥负载悬崖）对象不存在（桥在跑但输出无人消费，
负载恒定存在于两轮，非分界变量）。

## 3. EV 融合从未启用实锤（C01 E-1 判据项 5 + E-2 前置）

| 轮 | ulg | EV_CTRL | cs_ev_* n_true | vvo 到达 |
|---|---|---|---|---|
| V1.3 悬停源（t2v3_hover） | 09-28/12_32_34 | 0 | **0/130** | 1064 样本@110s 健康 |
| W1.3 r2 PASS | 09-29/03_26_35 | 0 | **0/206** | 1837@188s 健康 |
| w2b 全败 | 09-29/04_11_30 | 0 | **0/126** | 1008@105s（9.6Hz，iv_max 0.176s） |
| 全历史扫描 | 09-22/23/26/28/29 计 90+ | **全 0** | 抽验全 0 | — |

- **H10（EV 断流/TCPROS 协商失败影响 W2）出局**：PX4 侧到达率满率健康（P-2 判据的强证据形态）。
- **V1_RESULTS.md "EKF2 带视觉融合 0.087m" 归因证伪**：0.087 = EKF2（GPS+baro+DR）输出在飞机被
  px4ctrl（VINS 直供）稳住时的漂移，与 EV 融合质量无关。V1.2 表"EKF2 有 vision_pose 融合"同源错误
  （书面假设，从未验过融合位）。
- **airframe 层根因**：iris_stereo_vins 是 sitl_targets_gazebo-classic.cmake 的标准 iris 系 make target，
  挂基础 iris airframe（不设 EKF2_EV_CTRL）；对比 iris_vision airframe（1013）显式
  `param set-default EKF2_EV_CTRL 15`。**EV_CTRL=0 是模型选择的副作用，从未有人显式配置/审查**。
  （C10-H3/H 线"参数现值"列同时清偿。）

## 4. W2 失效双层分解（新事实，重定义 E1 对象）

### 层 1：VINS 发散（T2-W-A 域，ATE 数字主源）

T2 表的 36.8/53.7/40.2/12.1-90.1/46.6m 为 **ATE rmse（VINS-vs-GT 口径）**。obstacles world 的
场景条件性 VINS 发散（883c75c 定性、T2 v4.3 W-A 主线）在此五轮复现；w2d 二次 376m 与 X 线
X1final 471m/890m 同族。**此层与 223Hz 无关（X 线同栈 125Hz 时代亦有），归 T2-W-A。**

### 层 2：飞机物理失控（PX4 内部域，223Hz 条件性保留）

EKF2 local_position（=GPS 锚定）实测（五轮飞行 ulg 族谱）：

| 轮 | ulg | max z（目标） | max x/y | 判读 |
|---|---|---|---|---|
| w2a 悬停 | 04_09_48 | **1.81**（0.75） | 0.09/0.11 | z 超 2.4× |
| w2b 慢巡 | 04_11_30 | **3.76**（1.2） | 0.23/**4.14** | z 超 3.1×+y 漂 |
| w2c 冲刺 | 04_13_45 | **8.00**（1.2） | **4.66/8.07** | z 超 6.7×+xy 大漂 |
| w2d | 04_16_24 | 1.08 | 0.36/0.28 | EKF2 口径温和（失控主在层 1） |
| w2e | 04_18_17 | 1.03 | 0.08/0.22 | 同上 |

交叉验证：w2b 袋 GT-vs-local 逐时刻对齐（bag 直读）= **delta_xy 恒 1.33-1.43m（出生点 (+1.01,+0.98)
平移假象，t2b-u9 已知）**，z 同步（local 3.66 ↔ GT 3.75）——EKF2/GPS 没有骗位置环，**飞机真的物理失控**；
失控形态=z 通道主导超调+xy 漂移（w2c 最烈）。

**层 2 的条件性**：125Hz 时代 w2b 轮 1 曾 0.119m（T2 台账:977）⟹ 223Hz（或同变的伴随量）为分界候选。
但注意：511-105-5000→4000 改的是 ATT_QUATERNION/IMU 流率（125→223Hz），同变伴随量=
EKF2 主环输入率、mavlink 链路负载、（lockstep 网格量化）——分界归因需 E-2/E-4 重做（C01 推论二
"多变量混淆"警告在此同样适用，只是混淆轴从"IMU 率×EV 供给"变为"IMU 率×EKF2 输出率×链路负载"）。

## 5. 对 C01/任务书下游的改写清单

| 项 | 原设计 | 改写 |
|---|---|---|
| E-4 主臂（EV_CTRL 0↔实值恒负载复现对） | 切 EV_CTRL"实值" | **作废重设计**：实值=0（切了等于没切）。新设计须含 ①223 vs 125Hz 条件复现（同 OFFBOARD 链，先复现层 2）②EV_CTRL=15 启用轮（全新未知域：启用后行为无任何历史数据） |
| E-5 密度轴（EV 速率 30/60/223+GT） | 三方归因分配 | 对象不存在（EV 未融）→整轴顺延至 EV_CTRL=15 启用后；W-A 绿灯条件不变 |
| E-6 修复面 | EV 参数级 | 层 2 修复面=PX4 位置环@223Hz 体制（MPC_*/EKF2 输出消费）——"哪行/哪个参数"待 E-2 取证 |
| 三方握手（T2-A3/T3-Z1/T1-E1） | EV 密度/px4ctrl 消费/EKF2 参数 | 三面全部不在 W2 环内！Z1（px4ctrl 消费面）对 W2 无对象；A3 供给面对层 2 无对象（层 1 归 W-A）——**STATUS 通告 T2/T3 按新定义重握手** |
| R6 同构 | — | W2 链（OFFBOARD 直控 PX4）与实机链不同构（无论 F2 冲突①哪分支胜）——W2"鲁棒场景"作为验收场景的资格存疑，需重构或重命名 |
| 悬案池行"W2 五场景全败=EKF2-EV 控制失稳@223Hz" | 归 T1-E1 | 改写："W2 层 2=PX4 位置环@223Hz 体制失控（OFFBOARD 链，EV/px4ctrl/VINS 均不在环）"归 T1（重定义 E1）；层 1=VINS 发散归 T2-W-A（既有） |
| 历史叙事修正 | — | ①V1_RESULTS "带视觉融合 0.087"行 ②C01 §1.1 现象锚 ③记忆 t1-v5 同表述——均需勘误登记 |

## 6. 遗留开放点（E-2 对象）

1. 层 2 机制定位：z 通道为何超调（EKF2 输出@223Hz 更新率？MPC_Z 增益？baro/gps_hgt 融合动态？
   OFFBOARD setpoint 10Hz×位置环的交互）——三时刻表对象改为"层 2 失效的 ulog 侧取证"
   （estimator_status 时间线/控制模式切换/local_position 输出率）
2. 前置 5 个 55s 未起飞 ulg（03_57_58-04_02_54，nav 恒 4）= w2batch RETRY 的失败链——
   与层 2 的关系（是否 arm/offboard 拒绝）待查
3. w2d 12.1/90.1m 与 w2e 46.6m 的 GT 口径复核（层 1/层 2 占比分解，GT 数据在袋内）
4. cs_gps_hgt=124 与 cs_gnss_pos=120 的 SITL GPS 流来源确认（iris_stereo_vins 模型带 GPS 传感器？——
   若带，注意 GPS 流与 EV 流的融合优先级关系对后续 EV_CTRL=15 启用实验的影响）

## 7. 产物清单

- 本文件：t1_evidence/v7_2026-09-30/E1_E1_threeway_archaeology_verdict.md
- 数据：全部 ulog 时间线扫描输出（§1/§3 表内数字可复算：pyulog initial_parameters + estimator_status_flags）
