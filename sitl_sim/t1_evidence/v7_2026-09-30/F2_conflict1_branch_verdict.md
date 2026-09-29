# T1-F2 冲突①双分支裁决报告：实机位置环归属（2026-09-30 夜）

状态：三路取证（blame/上游对照/启动链实证）全部完成，按任务书纪律提请用户拍板。
执行者：T1 v7 夜 1。全部 0 锁（git 考古 + GitHub 上游只读 + 本仓 launch 实读）。

## 0. 结论摘要（先读）

**核心事实（新发现，改写冲突①的前提）**：`use_px4_position_ctrl` 开关**不是上游 Fast-Drone-250 的东西**——
GitHub 全域代码搜索仅本仓 6 处命中；上游 yaml 无此 key、上游 px4ctrl_node.cpp 无 PositionTarget publisher、
上游 readme 无 PX4 位置环/EV 融合概念。它是**本仓导入源（1a069ca，私有改版，作者不可考）自带的架构改动**，
且与 vins_to_mavros（EV 转发链）同源配套。

**双方都无法完全排除，但证据天平向分支 A 倾斜**（改版作者有意选择 PX4 侧位置环，非手滑误配），
理由见 §4。同时该发现使 **SITL(false) vs 实机(true) 的位置控制架构不同构成为 R6 必登项**（与哪分支胜出无关）。

## 1. 证据表（全部可复算）

### 1.1 本仓 git 层（blame）

| # | 证据 | 命令/位置 | 含义 |
|---|---|---|---|
| B1 | fpv yaml `use_px4_position_ctrl: true` 自导入至今**零改动** | `git log --oneline -- src/px4ctrl/config/ctrl_param_fpv.yaml` 仅 1a069ca | true 非本仓引入 |
| B2 | 导入 commit 已含全套改版 | `git show 1a069ca:src/px4ctrl/src/px4ctrl_node.cpp` :80 PositionTarget pub、:86 `nh.param(...,true)` | 改版随导入而来，非 2026-06 后加 |
| B3 | 代码默认 true | px4ctrl_node.cpp:88（当前）、PX4CtrlFSM.h:52 `{true}` | 改版作者基线意图=true |
| B4 | sitl `false` 是 T1 新建 | a01ef22 "add SITL launch and params (separate from real-machine config)" | SITL 配置时显式选 false（当时选择理由无记录） |
| B5 | c3c57ea 只含 rosparam dump 文档行 | git show | 非改动 |

### 1.2 上游对照层（ZJU-FAST-Lab/Fast-Drone-250@master，2022-11-09 后冻结）

| # | 证据 | 位置 | 含义 |
|---|---|---|---|
| U1 | 上游 ctrl_param_fpv.yaml **无该 key** | src/realflight_modules/px4ctrl/config/ctrl_param_fpv.yaml | 上游无此概念 |
| U2 | 上游 px4ctrl_node.cpp **只 advertise AttitudeTarget**，无 PositionTarget | 同路径 src/（全文实读） | 上游架构=机载串级 PID（位置环必然在 px4ctrl） |
| U3 | 上游 yaml gain 注释 "Cascade PID controller. Recommend to read the code"（Kp/Kv=1.5, KAng=20） | U1 文件 | 上游位置+姿态环增益全在机载侧 |
| U4 | 上游 readme（en）无 PositionTarget/setpoint_raw/local/PX4 位置控制/EV 融合任何提法；VINS=imu_propagate 直供 px4ctrl；**无 vins_to_mavros 概念** | readme_en.md（20K 实读） | 上游 EV 不进飞控 |
| U5 | GitHub 全域搜索 `use_px4_position_ctrl`：仅本仓 6 处（yaml×2+源码×3+证据日志×1） | search_code | **本仓导入源是孤例改版**，公开仓库无先例 |
| U6 | 上游仓库 2022-11 后冻结（最后 commit "remove v5 carbon board"），本仓导入 2026-06 | list_commits | 无"上游后来删了该 key"的演化可能（冻结期早于导入） |

### 1.3 启动链实证层（实机链）

| # | 证据 | 位置 | 含义 |
|---|---|---|---|
| L1 | full_vins_px4.launch（实机感知栈）= mavros(/dev/pixhawk:921600) + RealSense + vins + **vins_to_mavros**；**不含 px4ctrl** | src/launch/full_vins_px4.launch | px4ctrl 由 run_ctrl.launch 单独起 |
| L2 | run_ctrl.launch（唯一实机 px4ctrl launch）: odom→imu_propagate 直供 + 加载 fpv yaml(true) | src/px4ctrl/launch/run_ctrl.launch | 若实机即用此链：**true 生效，PX4 位置环在环** |
| L3 | **vins_to_mavros 在导入 commit 即存在**（1a069ca，3 文件） | git 考古 | EV 供给链与开关同源配套设计 |
| L4 | 实机链含 EV 供给（L3）+ 开关 true（L2）+ 代码默认 true（B3）三处自洽 | 综合 | 改版是一套完整架构（PX4 侧融合+位置环），非孤立一行 |

## 2. 分支 A 论据集（yaml=true 是真实意图，实机位置环在 PX4 侧）

1. **改版三处自洽**（B3 默认 true + B1 fpv true + L3 EV 链配套）——误配论需要解释"为什么手滑恰好滑成一套完整架构"
2. **能力账（若 true）**：px4ctrl 位置环被旁路（Kp/Kv 1.5 不参与巡航外环），发 PositionTarget；
   PX4 pos/vel PID 消费 EKF2 local_position（EV 融合供）——**vins_to_mavros 在此架构下有功能必要性**
3. odom 直供（imu_propagate）在 true 下仍用于：need_direct_thrust 窗（降落/怠速直推力）、
   FSM 模式判定、D2 门（is_odom_valid 层，与位置环归属无关，仍有效）、RLS（直推力窗仍用）
4. factsheet"位置环在机载侧"叙事无仓库证据支撑（叙事来源待考——可能继承上游架构印象 U2-U4）

## 3. 分支 B 论据集（"位置环在机载侧"叙事正确，yaml 为误配/遗留）

1. **上游架构=机载侧**（U2 PositionTarget 缺席 + U3 增益注释 + U4 readme）——叙事与上游原始设计一致
2. **改版无来源背书**：作者不可考（U5 孤例）、无注释说明动机、上游 issues/readme 均无讨论
3. 改版者的 PX4 位置环选择可能是实验性/特定硬件妥协（如机载算力紧张时期），未必适配本机复现目标
4. 若 true 生效但 EKF2-EV 融合质量差（W2 现象的同族风险），PX4 位置环反而比机载环更暴露于 EV 故障——
   与"实机首飞安全"诉求冲突，支持首飞前改回 false（须用户批准，本册不动）

## 4. 权重评估（如实呈现，拍板归用户）

- 分支 A 的强点：三处自洽的完整架构证据（L4）难以用"误配"解释；EV 链的功能必要性。
- 分支 B 的强点：与上游架构的一致性；改版来源不可考的不确定性。
- **裁决天平：A > B**（证据密度与自洽性），但**不闭合**——"改版作者身份/动机"是不可考项，
  按任务书纪律报用户拍板。用户可能掌握导入源的来历（谁给的包/哪来的压缩包），可一句话定案。
- **无论 A/B 哪个胜出**：`SITL(false) ≠ 实机(true)` 的**位置控制架构不同构**已是既成仓库事实 →
  **R6 同构差距表必登项**；F2 三账的架构层按双假设标记书写（C10 X5 规则）；C09 sim2real 六维基线联动。

## 5. 对 R6 同构声明的具体影响（待拍板后落 README §0）

- 若 A：登记"SITL 验证的位置环行为（px4ctrl 串级 PID）与实机（PX4 pos/vel PID）不同构；
  SITL 全绿战绩不可直接外推实机位置控制品质"；实机首飞前建议 X5b 式 ulog 验证（C10 P12）
- 若 B：出勘误案（实飞前修正 fpv yaml，须用户批准）；factsheet 叙事维持

## 6. 与其他单元的联动

- C01/E1：若 A 成立，实机架构=PX4 位置环+EKF2-EV 融合在环——W2 的 EKF2-EV@223Hz 失稳研究
  对实机架构的重要性**升级**（不是 SITL 临时方案的问题，是实机主链问题）
- C10/F2 三账：架构层第一句待本裁决；延迟账/裕度账的增益数值层可先行（双假设标记）
- C09（sim2real 六维）：位置控制架构维度的差距项

## 7. 产物

- 本文件：t1_evidence/v7_2026-09-30/F2_conflict1_branch_verdict.md
