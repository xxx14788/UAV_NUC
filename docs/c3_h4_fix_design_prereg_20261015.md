# H4 修复面预注册设计文档（阶段 B-B1；2026-10-15；先文档后动手）

> 授权来源：终局册 v2.1 解禁面一（用户裁定 2026-10-13~15）——px4ctrl 推力斜坡/姿态限幅接口 + PX4 飞行/姿态 PID 等参数域；固件源码仍禁改。
> 红线遵循：⑤例外两条解禁面互不越界；⑦指纹与快照制（px4ctrl 修复换代=新指纹注记；PX4 参数变更=param dump 快照+md5）；⑩本修复栈在阶段 C 冻结。
> 本文档=预注册件：B2 彩排判据/B2.5 监测带/B3 零退化门基线全部跑前锁定，动手写码在其后。

## 1. 机理链（代码级，H4 定案的实现面定位）

**起飞推力指令生成路径**（px4ctrl，3090 `~/catkin_ws/src/px4ctrl/src/`）：

- FSM `AUTO_TAKEOFF` 态（PX4CtrlFSM.cpp:397-433）：电机加速段 `dt < MOTORS_SPEEDUP_TIME` 用 `get_rotor_speed_up_des`，之后 `get_takeoff_land_des(speed)`。
- **起步低推力的来源**（PX4CtrlFSM.cpp:672-691）：
  `des_a_z = exp((delta_t - MOTORS_SPEEDUP_TIME)*6.0)*7.0 - 7.0`，锚定起飞触发时刻。
  delta_t=0 时 des_a_z≈-7 → des_acc_z = g-7 = 2.81 → **thrust = 2.81/(9.81/0.71) ≈ 0.20**（观测 0.23-0.26 的构成=此项+odom 速度反馈微差）——低起步不是 bug 而是设计的电机缓启。
- **爬坡段**（PX4CtrlFSM.cpp:693-712）：`des.p.z = start_z + 0.5·dt'`、`des.v.z=0.5`、`des.a=0`；控制器（controller.cpp:34-37）`des_acc = g + Kv2(0.5-v_z) + Kp2(Δz)`，`u.thrust = clamp(des_acc_z/thr2acc, 0, 1)`，SITL 冻结映射 `thr2acc = 9.81/0.71 = 13.82`。
- **分叉的代数**：机体躺地（z≈0.10，姿态非水平）期间 des.z 以 0.5m/s 前进，Δz 每卡 2s 即累积 1.0m → Kp2·Δz = 1.5 m/s²/轮；卡 4s → des_acc_z ≈ 9.81+3.0(+Kv2·v_z 噪声) → thrust ≈ (12.8+)/13.82 ≈ **0.93-1.0 饱和**。同时 odom 横向慢漂喂 Kp0/Kp1 → des_acc 横向分量 → `attitudeFromAccel` 构造倾斜姿态（护栏仅 zb.z≥0.1g≈84°）→ 饱和推力×倾斜矢量=斜向合力 → **弹射（39-67m+水平 50-120m）**；若姿态误差收敛先于饱和→正常爬到 0.71 悬停带。NF 型（爬坡失败温和结局）与爆型共享前段=同族两结局（H4 报告六问 §6.4 在册）。
- **观测对账**：爆轮 221911 thrust@+2s=0.261→@+8s=0.983→1.000 满推（exp 缓启起步值+Kp 积累到饱和）；正常轮 hover5b 0.232→0.714（悬停带=hover_percentage 0.71 本身）——代码路径与 H4 双型时序逐点吻合。

## 2. 修复设计（单一机制组=起飞控制包络；任务书原文"推力斜坡限幅+姿态输出限幅"）

**H4-F1 起飞推力上限（thrust cap）**：
- 接口：`auto_takeoff_land/takeoff_thrust_cap`（新参数，默认 0.0=关闭=行为与现状逐位一致）；生效窗=`state==AUTO_TAKEOFF 且 (odom_z - start_z) < takeoff_cap_release_z`（默认 0.30m）；出窗或转 AUTO_HOVER 即释放，悬停/导航/降落零影响。
- 实现位置：PX4CtrlFSM.cpp STEP3（`controller.calculateControl(...)` 调用后，:513 邻域）对 `u.thrust` 取 min(cap)。
- 取值：**0.80**（hover 0.71+0.09 余量；垂直方向净上加速度 ≈ (0.80·13.82-9.81)/1 = 1.25 m/s²，0.4s 内可加速到 0.5m/s 爬升速度——爬升能力保持）。
- 机理假设：饱和-倾斜正反馈环的放大器是"无界推力"；封顶后即使 Δz 误差持续积累，推力矢量模长有界，弹射能量有上界；配合 F2 倾角限幅后垂直分量 ≥ 0.80·cos20° = 0.75 > 0.71 = 起飞判据→两结局（NF/爆）都被收敛到受控爬升。
- 预期曲线形态：thrust 0.20 →（exp 缓启）→ 0.71 带 → 爬升段封顶平台 ≤0.80（若卡地则快速到 0.80 平台并保持）→ 出窗释放 → 悬停带 0.71±。**禁止出现的形态：0.9-1.0 平台**。

**H4-F2 起飞倾角限幅（tilt clamp）**：
- 接口：`auto_takeoff_land/takeoff_tilt_max_deg`（默认 -1.0=关闭）；生效窗同 F1。
- 实现位置：controller.cpp `calculateControl` 增加带默认参的重载/尾参 `tilt_max_deg=-1`；在 `u.thrust` 计算后、`attitudeFromAccel` 构造前对 `des_acc` 横向分量缩放至 `|xy| ≤ tan(限角)·max(des_acc_z, ε)`。**thrust 只取 z 分量，横向缩放不改推力**；其余调用方（无测试调用者，仅 FSM 一处）零影响。
- 取值：**20.0°**（cos20°=0.940；起飞机动不需要横向加速度，织行横向加速度发生在出窗后的正常控制域）。
- 机理假设：躺地期 odom 慢漂喂出的横向指令是倾斜矢量放大的入口；限制构造姿态的倾角=把推力矢量钉在近垂直锥内，垂直分量占比 ≥94%。
- 预期曲线形态（ulog attitude 侧）：起飞窗内 roll/pitch |倾角| ≤20°+2° 容差；出窗后恢复全权限（织行需要时可达现有护栏 84°）。

**组合纪律**：F1+F2 为同一机制组（起飞包络）一次性预注册，同窗生效同窗释放；不与 PX4 参数变更混窗（分开实验，见 §3 P-2）。

## 3. PX4 参数域候选表（盘点自 v6 批 ulg 快照 0b0ba9c9；本批不首选动）

| 参数 | 现值 | 候选值 | 机理假设 | 预期形态 | 状态 |
|---|---|---|---|---|---|
| MC_PITCHRATE_I / MC_ROLLRATE_I | 0.20 | 0.15 | 躺地饱和期角速率积分器 windup→倾角缓增是分叉放大器之一；降 I 减 windup | 倾角增长率下降 | P-2b 储备：仅 F1+F2 不足时 |
| MPC_TILTMAX_AIR | 45.0 | 35.0 | FCU 侧倾角硬限（对 AttitudeTarget 外环限幅生效路径须彩排实证，标注不确定性） | 全程倾角 ≤35° | P-2a 储备 |
| MC_PITCHRATE_P / MC_ROLLRATE_P | 0.15 | — | 姿态环带宽主旋钮；无证据指向——不动 | — | 不动（无假设支持） |
| MPC_THR_MIN/MAX | 0.12/1.0 | — | 直推通道旁路 PX4 高度控制，不经过 MPC_THR_* | — | 不动 |
| MPC_TKO_RAMP_T / MPC_TKO_SPEED | 3.0/1.5 | — | PX4 内部起飞状态专用；px4ctrl 走 setpoint_raw 直推，不经此路径 | — | 不动（路径无关） |
| MC_PITCH_P | 4.0 | — | 角度环 P；无异动证据 | — | 不动 |

## 4. 负面清单（禁碰族——影响判读科学面的参数禁调）

- **EKF2_EV 权重类**（EKF2_EV_POS_X/Y/Z、EKF2_EV_VEL_*、EKF2_EV_DELAY、EKF2_EV_CTRL、EKF2_EV_QMIN 等）：判读面 odom 源语义，快照 6f4537f8 在案冻结。
- **mavlink 流控类**（MAV_*, SER_TEL*, BW_*, MAVX_*）：链路时序=δ 探针/时戳配对判据的底座。
- **导航判读依赖话题流参数族**：任何改变话题频率/队列/超时的参数（msg_timeout 族、odom 门参数、VINS 配置）——判读器 v1.5h 语义依赖现有流形状。
- px4ctrl 域内：`Kp/Kv` 增益、`hover_percentage`、`thr2acc` 钳位、`takeoff_land_speed`、`MOTORS_SPEEDUP_TIME`——这些动了对悬停/判读面的连带面大，且不属"推力斜坡/姿态限幅接口"授权 wording；如 F1+F2 不足再走设计文档增补流程。

## 5. B2 彩排协议（预注册）

- **对照样本**：修复前=在册 forensics（221911 爆型/215820 爆型/hover5b 正常型）+ **新采 ≥3 对**（修复前后各 ≥3 轮短飞：起飞→0.75m→悬停 20s→降落；同 world v6 同栈同窗）。
- **取证**：每轮 ulog（thrust 曲线+bias 时序，H4 取证协议复用）+ truth z/水平时序 + px4ctrl log。
- **判据（跑前锁定）**：①修复后爬坡段 thrust 峰值 ≤ cap+0.02 容差（0.82）；②无弹射形态=起飞窗（armed→AUTO_HOVER）内 truth z 峰 ≤1.5m ∧ 水平位移 ≤2m；③≥3 对曲线形态一致（起步带 0.20-0.30/爬坡斜率同号/封顶平台同带）——对照对间一致性防单轮彩票噪声。
- **失败处置**：任一判据不过=回炉（禁放宽判据）；F1+F2 不足→启用 P-2a/P-2b（单独实验制）。

## 6. B2.5 副作用监测面（预注册）

| 监测项 | 正常带（来源） | 超带处置 |
|---|---|---|
| 爬升时间（armed→z≥0.71） | 在册正常轮 3-6s（hover5b 同带；N2 面 armed 3s 内+悬停到位） | >10s=回炉（欠推） |
| 悬停高度保持（20s 窗 \|z-0.75\|） | ≤0.10m（N3 在册 0.0245m 的 4 倍包络） | 超带=回炉 |
| cmd 跟踪误差（悬停段 odom-des） | ≤0.30m | 超带=回炉 |

## 7. B3 零退化门（基线预注册，修复后同条件复测全在带内才放行）

- N1 五件套活（mavros/VINS/px4ctrl/planner/SITL）；N2 armed 3s 内+真值 z≈0.71+AUTO_HOVER；N3 悬停 60s 真值 maxdrift ≤0.075m（在册 0.0245m 的 3 倍带）；N4/N5 goal 往返到位 ≤0.75m 门（odom 域）。
- 悬停漂移带（j0d 净轮）：在册 j0d 净轮带同数量级（复测轮 j0 总 ≤0.7m/hover 窗）。
- 复测窗=彩排同窗（不额外烧批：B2 新采对本身即 N 面复测载体——起飞/悬停/降落链全覆盖）。

## 8. 指纹与快照制（红线⑦执行细则）

- px4ctrl 修改后：`px4ctrl_node`/相关目标 md5 新指纹注记（对照在册 cac140b0 域外——px4ctrl 二进制独立指纹）+ gtest 全绿（px4ctrl 包测试+新建接口单测）。
- PX4 参数：本批**零变更**（P-2 储备未启用）；param dump 基线快照三件已落战役目录（FULL e0093708/prefix 0b0ba9c9/负面清单 6f4537f8）。
- VINS config：零触碰。
- 终版结论绑定件（B5 移交四件）由此节生成。

## 9. 实现清单（B2 执行序）

1. controller.h/.cpp：`calculateControl` 尾参 `tilt_max_deg`（默认 -1）+ 横向缩放逻辑 + 单测用例（限角构造/不限角构造/thrust 不变性）。
2. PX4CtrlParam.cpp/.h + ctrl_param_sitl.yaml：三参数（takeoff_thrust_cap 0.80 / takeoff_tilt_max_deg 20.0 / takeoff_cap_release_z 0.30；代码默认=关闭保旧行为，yaml 显式开启）。
3. PX4CtrlFSM.cpp STEP3：生效窗判定+F1 封顶+传递 F2 限角；窗内 ROS_INFO_THROTTLE 痕迹。
4. gtest 回归（px4ctrl 全测试）+ catkin 编译 + 新指纹 md5。
5. 彩排（§5）→ B2.5/B3 面复测 → B4 验证批。

## 10. 预注册判决点

- B4 主证据=thrust 曲线前后对照（分叉消失可复现，≥8 轮全证书链）；佐证=彩票发生率 ≤1/8（8 轮统计区分度弱，不单独定案——在册二项噪声教训）。
- 若 NF 型残留（推力封顶后仍不起飞）：登记=修复部分成功（爆型消除），NF 亚型归 H1 接触域/出生姿态域另立注记，禁在 B 内顺手扩修复面。
