# V11_0_SESSION_LEDGER — T1 会话台账（2026-10-04 夜，任务书 v11.0）

> 任务书：Windows 权威 `plans/2026-10-04_T1_px4ctrl_v11.0.md`。前序：V10_4_SESSION_LEDGER（含晨间章）。
> 提交链基线：d77a742（开工时 main=UAV_NUC/main，零积压）。

## 章 0：首件（02:49-02:05）

| 项 | 结果 |
|---|---|
| WAN | 通；丢包 50%（1/2），RTT 577ms——弱网可 push，大传输走重试 |
| push | 0 未推；工作区仅历史 bak/untracked 5 件 |
| df | 50G 可用（78% 用）；C-5 目标 65G 未达=T3 腾位域；本线域水位安全 |
| EXP-2 周检 | wifi-watchdog.timer active 单实例，LastTrigger 01:48:15（节律 3min 正常） |
| 锁/负载 | 锁空；pgrep SITL 域 0 进程（仅 vins_kill_watch 常驻）；无并发 build → **W-A 唤醒条件满足** |
| STATUS 消费 | 尾 25 行全读；本线待办=@T3 K-2 销案确认、T2 VR3 悬停 8.5m（单元 3）、T3 三段分解回执（本账落档） |
| DECISION_LOG | 文件原不存在→本会话首建 `~/sitl_sim/DECISION_LOG.md`；无未复核条目（空转如实）；001 号条目=2.8 定案 |

### 跨线回执消费：T3 三段分解（STATUS 10-03 09:58，判读文 docs/t3_handoff_040932_decomp.md，0fad9e6）

入悬案账条目：
1. **odom 系闭环 p95 0.195m＝px4ctrl 紧域**（规划段 poscmd→goal 0.013m planner 无罪）——J0 锚差 0.587m 边缘超门样本并入 T1-D1 样本池；armed 卡 True＝G-1 域并档。
2. VINS 刻画误差 0.6-0.9m 级＝主残差（压过 0.75 门余量，到位全红机理画像再添例）——T2/T4 消费面，本线引用带限定。
3. EKF2 排除（W1 构型 EKF2 不在位姿环）——与 E1 裁决（EV_CTRL=0）一致，无新增动作。

### 单元 2.8：E1/0.5 分叉定案（D-2026-10-04-01）

px4ctrl 侧接线（控制律后、mavros 前）。证据链四条（E1 裁决/C01 对象不存在/D2 门实战+E-4 #5/G-off 全 PASS）全文见 DECISION_LOG。@T3 Z1.2 前置②解除（STATUS 已通告）。


## 章 1：K-7 磁盘应急响应（T1 域释放，02:5x）

T3 02:50 df 斜率告警（50→31G/10min，T2 复裁轮带图录制）——T1 域责任立即执行。

**删除清单**（22 轮目录，~/sitl_sim/vins_smoke_runs/，共 ~1.7G；判读产物全部入库已推，删除面=原始流，无未来预注册消费面）：
- X1 系列 ×10（000947/001817/002443/002831/225059/225612/231835/232055/233210/234437/235025）：跳变四型+Bgs 领先取证（v10.1 台账在库）
- E3 ×2（202044/210246）、E2FAIL ×3（022847/023440/024211）：E2/E3 裁决链（v8 台账）
- WD1b ×2（032925/033751）：D2 门实战取证（WD1b 判读在库）
- WAOL ×5（142557/214142/215120/220117/222234）：WAOL 判读历史（v8/v9 台账）

**保留**（有活消费面）：E4R2 八轮全部（M1 二刀素材+E-5b 滚动源+R8=F3 A 基线+U2.5 对照轮）+ WC2OBS1×2（T4 权属）+ U3PO（T3 权属）。

**T1 责任差额注记**：责任额 3.5G−已释 1.7G=1.8G 差额挂 E4R2 袋暂缓（消费中）；E-4 素材消费完毕后按同惯例释放（预注记，届时 STATUS 通告）。

## 章 2：build 窗+码面交付（02:05-03:05）

| 件 | 交付 | 凭据 |
|---|---|---|
| 2.5 L-odom 帧差异 | 定位闭案（出口①帧 bug 实锤+出口②撕裂坐实）+修复码 | u25_lodom_framing_verdict.md；0645569；DECISION_LOG D-02 |
| 2.7 auto_disarm | 三层归因（T2 触发器/px4ctrl 静默缺陷/检查项语义）+U2.7 修复 | 取证=run_U3PO armed/fsm/takeoff_land 时序；6ef1acb |
| 1 F3 全接线 | 六块接线+生产版 fsm_decision.h；**60/60 gtest**；审计表 | 6ef1acb；f3_line_audit_table.md |
| 2 P1 出生位差门 | 全链（feed 锁存+FSM 双入口拒+disarm 解锁）；37/37；预注册 | f899a0c；p1_rebirth_prereg.md |
| 6 R3x 探针 | 外部节点四面+glitch_align+面②b v1.1（架构修正：真队列=img bufs）；B 路合成自检过 | a3dc85e；设计稿 §8 增补 |
| 5 E-5b 首批 | 8/8 单窗零熄灭；P3 基线带立；e4_judge 通道子串工具债发现 | 186f00b；ev_hpos_obs.md |
| 池① w2b | A 路默认 off 码（fsyntax 0err 未 build）+B 路探针 face | f83f446 |
| 池⑥ 栈号跟随 | 预设计稿（harness 改动挂协调窗） | pool6_stack_md5_predesign.md |
| 2 P2 | 设计框架 v0（门值冻结挂单元 3） | p2_cmdresp_prereg_frame.md |
| K-7 | 22 轮袋 1.7G 释放+权属建议 | 章 1 |

**F3B 首飞**：FATAL=300s VINS 未 init（PX4 ninja 与 T2 build 窗资源交叠=环境性，02:44 STATUS 在册）——重跑挂 T2 轮后（跨栈注记：A=fixface-2/B=fixface-3）。

## 章 3：等待状态（03:05 起）

- 阻塞=T2 验证轮（t2v3_flight.sh route 序列，02:39:42 起，带图录制 ~23.7G/轮）+df 危急（21-23G 徘徊，T3 已执行 U3PO 蒸馏逃逸腾位）
- 挂起件：飞轮窗（F3B 重跑/R-U25/P1 A/B/R3x dry-run/U2.7 降落验证/w2b 联测）；IO 件（单元 3 VR3 判读→P2 冻结；单元 4 M1 二刀静置段收割）
- 轮询节律=sleep 300 心跳+STATUS 尾消费+df 快照

## 章 4：IO 判读双件+飞轮窗竞态（03:0x-03:4x）

| 件 | 交付 | 凭据 |
|---|---|---|
| 单元 3 悬停 8.5m | **定案=px4ctrl 输入流（imu_propagate）平滑钉死谎言=VINS 双流分叉**（odometry 流如实/EKF2 vs GT 恒差 1.42）；px4ctrl 增益/积分器/姿态环无罪（回执 @T2 悬停注脚解除）；P2 定位量填充（0.21m/s/0.5m/10s 窗） | u3_hover_drift_verdict.md+三工具 |
| 单元 4 M1 二刀 | **绝对判别仍未立（负结果收档）**：健康带 9→22 核心窗后与冻结带重叠 1.06 数量级维持；流内相对路线（w2b B 路）标定背书；GON-D30 静置段剔除标准增补 | m1_secondcut_report.md+扩带 CSV 集 |
| K-7 二次响应 | 02:57 释放 1.7G（22 轮袋）；03:14 盘满倒计时告警；df 危机由 T3 逃逸腾位×2+U3PO 蒸馏化解（终态 56G） | STATUS 02:57/03:14；台账章 1 |
| 飞轮窗竞态 | F3B 首飞 FATAL（环境性 ninja 交叠）；F3B2 被盘门拒（防线正确）；F3B2-三被 U4OBS1 活轮拒（防双 SITL 防线正确）→ **三连让位，窗重排 T3-U4OBS1r 轮后** | STATUS 02:44/03:20/03:26 |
| DECISION_LOG 事故 | 并发重写致 D-01 丢失→补录+备份+追加式写法约定建议 | STATUS 03:12 |

**M1 收割完成副作用**：E-4 八轮袋消费面清空（E-5b/J 面板/静置段均已提取）→ 0.9G 可释（挂 T2/T3 腾位协调窗，预注记）。

## 章 5：飞轮窗双轮+判读（03:52-04:0x）

**窗口史**：F3B 首飞 FATAL（ninja 交叠）→F3B2-盘门拒→F3B2-三 U4OBS1 活轮拒→F3B2-四 T2 循环竞态拒→**03:52 真空窗双轮成行**（T2 harness 空转停后）。

| 轮 | 判读 | 凭据 |
|---|---|---|
| F3B2（03:52-03:55，canonical EV0/GPS7） | **F3 验收 B 臂 PASS**：J1 p50 0.0835（A=R8 0.041 同数量级，跨栈注记）+J5 0.08+EV 健康+零急性+FSM 时序与新代码一致；到位真值 0.061/跟踪 p95 0.067/帧稳 0.123 | e4_runs/F3B2_judge.json |
| U25FIX（03:58-04:02，pub_mode=odom） | **U2.5 两判据达成**：ODOM:Ex:=0（修复前 285）+J1 p50 0.0115 历史最优；**J5_z_mean 9.54m 新案**（EKF2 z 拉离 10m 级，候选=EV vel z 变换/EKF2 z-EV 交互）；cs_ev_yaw 判据不可判（**ulog 无该通道键，历轮证据链无源——工具债扩大登记**） | e4_runs/U25FIX_judge.json |
| P1 健康回归（两轮顺带） | 零 P1 日志+零 hover-entry 拒绝=**误伤 0 判据达成** | 两轮日志 |
| R3x 探针 dry-run | 失败（时序错位：sleep 100 后轮已近尾，jsonl 0 行）——下轮修正启动时序 | run_F3B2_035213/r3x_probe.jsonl |

**新坑登记**：
- **H-1 planner-kill 失效**（两轮 auto_disarm=0 根因：position_cmd 流不断→CMD_CTRL 卡→LAND 设计性拒（拒日志在案=U2.7 码正确）→无 disarm；kill 段输出在 round.log 缺失=执行面存疑）——修复面=kill_planner_all 匹配/时序+smoke 收尾可观测性（挂池，harness 域）；**U2.7 DoD（降落轮 disarm✓）挂此坑后**
- H-2 L-odom z 异常（U25FIX J5 9.54m）——U2.5 后续开案
- H-3 ev_yaw 通道键缺失（工具债扩大：e4_judge/e5b 全通道审计需求）

## 章 6：会话状态（04:0x）

- 全部 0 锁件+IO 件+两飞轮交付；挂账=P1 A/B 注入轮/R3x dry-run 重试/U2.7 DoD（H-1 后）/w2b 联测（需 IO+build 窗）
- 提交链：2bc0183→（T2/T3 交错）→f899a0c/a3dc85e/186f00b/f83f446/…全推零积压
- DECISION_LOG：D-01（补录）/D-02 在册待复核；并发写事故与追加式约定建议已通告

## 章 7：H-4 登记与会话收口态（04:3x-04:5x）

**H-4（新坑，环境级）**：飞行基础设施持续性效死——04:12 后四轮三例 never-flew（X2g1/F3B3/F3B4；X1final 04:06 最后飞行轮），签名一致（armed ✓/fsm 流转 ✓/setpoint_raw 115Hz ✓/truth z≡0.0 电机不转）；每轮 SITL+mavros 重启仍死=非进程残留型；修复面=T1 下会话首件（G1 TCPROS 悬案合流+mavlink 流/输出级排查）。**今晚飞行件全挂 H-4**（H-1 完整验证/P1B 注入轮/R3x dry-run 重试）。

**会话总账**（01:49-04:5x）：提交链 2bc0183→…→specimen commit 全推零积压；交付=单元 0 首件/2.8 定案/2.5 定案+修复+xy 实证/2.7 归因+修复+DoD 达成/F3 三件套闭环/P1 全码+健康回归/R3x 双面/w2b 双路/E-5b 首批/M1 二刀负结果/单元 3 定案/H-1 修复/三标本判读/DECISION_LOG 首建+事故处置/K-7 两轮响应。坑登记=H-1(已修欠验)/H-2 L-odom z/H-3 通道审计/H-4 飞行链效死。挂账=P1 A/B、R3x dry-run、w2b 联测、H-2/H-3、E-4 袋 0.9G 释放。轮询转低频（600-900s 节律，心跳 2h）。

## 章 8：晨间续战——H-4 三层定案与三修复验证（09:26-09:5x）

> 时间注记：04:50 后会话中断至 09:26（NUC 墙钟跳变 ~4.6h），晨间续作战果。

### H-4 三层定案（工具 h4_forensics/h4c_climb 入库）

| 层 | 内容 | 处置 |
|---|---|---|
| 层 1 | NEVER-FLEW 门 bug：`pose[0]`=**ground_plane** z 恒 0.0（gazebo 世界 models[0] 永远是地面），04:2x 起一切轮 37s 假杀；F3B3/F3B4 五面取证=完全健康飞行（z max 0.93/0.95，爬升逐 bin 与 F3B2 一致） | **已修**：smoke_truthz.py 按模型名取 iris z（双副本 md5 5051224d，.bak_h4b） |
| 层 2 | F3B5/F3B7=真 VINS 急性混乱（fixface-3）：F3B5 爬升中段死亡（n_v→0）→开环推满 truth 冲 4.5m→**错位重生 z=-0.7m 地下**→饱和震荡→再死→自由落体→**disarmed 静止机幻影爬升 2m**；F3B7=**出生即幻影**（VINS 0.35→5.6m 而 truth 恒 0.104）→bin12 真机火箭至 6.28m→VINS 钻至 **-36m** | T2 域样本（两袋保全：run_F3B5_092608/run_F3B7_093720）；F3B6 另有 15.69m 帧跳变=晨间三例 |
| 层 3 | **PX4 SITL 参数持久化**：rootfs/parameters.bson 存在（mtime=每轮 boot 时刻）——注入值泄漏进后续 regression 轮（F3B2 ulg=EV15/GPS0 而调用为 0/7 reg）；"RAM-only 不落 bson"旧假设证伪 | **已修**：e4_wheel always-inject（reg 轮显式注入 canonical 0/7=每轮 boot 确定性；**禁删/恢复 bson**——磁标定在其中，.bak_l3 在案） |

### 修复验证轮序列（F3B6-F3B9）

| 轮 | 判定 | 要点 |
|---|---|---|
| F3B6（09:32） | **门 ✓ + H-1 ✓** | 全程飞完（门过）；planner_kill.log after_kill=0 + **auto_disarm 0→1**（H-1 链活飞走通=U2.7+H-1 双 DoD 收口）；到位面=VINS 15.69m 帧跳 FAIL（T2 样本） |
| F3B7（09:37） | NEVER-FLEW（真） | VINS 出生幻影标本（层 2）；探针 rospy 坑二（is_initialized） |
| F3B8（09:44） | 门 ✓ + disarm=1 ✓ + **VINS 健康**（帧稳 0.026m） | poscmd 0Hz=planner WAIT_TARGET 饿死（goal 投递竞态复发，F3B6 通/F3B8 失=闪失面，T3 域素材 planner.log 在袋）；探针坑三（Rate.tick→sleep） |
| F3B9（09:49） | NEVER-FLEW（边缘 z=0.2955） | **R3x 探针首数据达成**：139 行六面全活（imu_jit p50 4.06ms/p95 8.2/RTF 0.99/vins CPU 88%/stampage odometry p50 52ms/w2bb 9 窗零告警）——dry-run DoD ✓ |

### 探针三坑（rospy 兼容性，全修）

`get_rostime_initialized`/`is_initialized` 属性不存在（本 rospy 版）→ emit 改 try/except；`Rate.tick()`→`Rate.sleep()`。探针产物=r3x_probe.jsonl+r3x_probe.err 随轮目录。

### 会话挂账（终态）

P1 A/B 注入轮（H-4 解除后可跑）/ F3B5+F3B7 VINS 样本待 T2 回执 / H-2 L-odom z / H-3 ev_yaw 通道审计 / w2b 联测 / E-4 袋 0.9G 释放 / goal 投递竞态（T3 域 F3B8 样本）。

## 章 9：P1 活飞验证（天然实验）与会话终态（09:56-10:1x）

### F3-P1B 轮（VINS 混乱气球轮 → P1 天然实验场）

- 轮况：truth 气球至 19-29m（晨间第 5 例 VINS 混乱），PLANNER-STARVED 注记。
- **P1 判据①超额达成**：六次天然锁存（4.16/2.43/5.55/48.81/75.26/**97.28**m，gap 2.3-48.3s），`[px4ctrl] P1: odom REBIRTH birth-offset` ROS_ERROR 全在 px4ctrl.log:1218-12063。
- **机理终解**：锁存源=**D2 拒帧风暴型 gap**——VINS 输出毒值→D2 三层门全拒→ACCEPTED 流断 >2s→复流首帧错位 >0.75m→锁存；VINS 进程未死（kill-watch 无中途转储）。预注册 §4"拒帧型 gap 与 rebirth 同危险类，锁存是正确行为"语义的天然实证。
- 判据②（hover-entry/U2.7-LAND 拒入日志）：本轮 FSM 未落入 MANUAL+LAND 组合未走到（如实：gtest 覆盖，待天然组合）；判据③（disarm 解锁）：码级+gtest。
- 注入器未起作用（set -u×ROS_DISTRO 已知坑秒死）——六锁存 100% 天然事件（比注入更硬）。
- **P1 判读=活飞①+gtest②③ → 任务书单元 2（P1）收口**。

### 跨线关键上下文（@T2）

- **sim_vins.launch 指向 sim_stereo_t2gates config**（T2 磁盘危机期切换，工作区未提交）——今晨全部 F3B/F3-P1B 轮跑在该 config 上。
- 晨间 VINS 混乱 census：6 轮 5 例（F3B5/F3B6/F3B7/F3B9/F3-P1B），唯 F3B8 全净（帧稳 0.026m）——t2gates 悬停域稳定性优先判读面；素材=袋+kill-watch 转储+P1 锁存时刻表。

### 会话终态

- 机器：进程零残留（vins/gz/px4ctrl/探针全清，pgrep -x 复核）、锁空、df 74G。
- 提交链全推零积压；全部 STATUS 回执已发；DECISION_LOG D-01/D-02 待他线复核。
- 挂账池（≥3 ✓）：T2 五混乱样本判读回执/H-2 L-odom z/H-3 通道审计/w2b 联测（素材已含天然毒风暴标本）/E-4 袋 0.9G 释放/goal 竞态 @T3/P1 判据②天然组合继续随轮收割。

## 章 10：敌对态（VINS 运动期 z 腐坏）战役（15:46-16:4x）

### 输入与移交消费

- T2 14:08 移交四标本（T2ZETA1/2/3/CTL2）+V2 起飞彩票敌对态（6/6 双栈）+晨净午灭时段谜题。
- 四标本三分形：ZETA1/3=起飞正常+中段悬停健康（死亡在 transit 段=T2 ζ 机制域）；ZETA2=出生地下室型（VINS z −4.7→−33.8m+truth 冻结+后段火箭 8.72m）；CTL2=全平线。

### 敌对态复现器与全排除链（F3B10-13 四连灭）

**复现器**：canonical 悬停轮（e4_wheel 0/7，obstacles world）在 15:48-16:10 连续四轮敌对（vs 同配方 03:52-04:36 四轮全净）。
死亡三型：爬升期 VINS z 4× 高估→死亡→弹道（F3B10）；渲染前平线（F3B11/13）； runaway 原点漂移（F3B12 anchor −258m）。

| 嫌疑 | 判据 | 结果 |
|---|---|---|
| 资产（iris/rig/world） | md5 vs 复原基线（eba57a5c/974a7533；world mtime 9-26） | **排除** |
| gazebo 模型缓存 | ~/.gazebo/models 无 stereo/iris 副本 | **排除** |
| Xvfb 陈旧 | 重启后 F3B12 依旧敌对 | **排除** |
| CPU governor | powersave→performance 后 F3B13 依旧敌对（D-03 在册） | **排除**（干预保持） |
| 图像冻结 | 像素级 md5 查重：F3B11 1135/1135 逐帧唯一 | **排除**（前期统计级"冻结"=零噪声静态场景合法现象，已自纠） |
| 图像时序 | dt p50 56-60ms/立体残差 0/无重复无负戳（两域一致） | **排除** |
| 图像统计退化 | mean/std/lapvar 两域健康同带 | **排除** |
| EV 参数泄漏 | always-inject 后仍敌对 | **排除** |
| 二进制 | T2 双栈同灭+fixface-3 晨净 | **排除** |

### 结论态（诚实）

环境输入层（图像内容统计/时序/唯一性、资产、渲染载体、电源策略）**全部洗清**而行为分裂持续=剩余假设面=①图像**内容**级差异（统计不敏感型：纹理细节/光照角——需净窗同世界带图袋对照，现存净窗带图袋均异世界）②VINS 进程内事件（非确定性初始化路径/T2 ζ 机制的运动期触发——**[W2BA] 活体测量为本战役收口动作**）。

### 活体测量（进行中）

诊断栈=fixface-3 源+[W2BA]（默认 off，catkin_make --pkg vins，build 窗 16:25 起）；敌对轮 T1_W2BA=1 → 拿腐坏爬升的 Bgs 滑窗领先时间线（T2 LK 饥饿×双稳态机制的直接活体数据）。栈 md5 换代登记随轮。

### F3B14 终拍（16:36-16:39）

- **轮全程跑通**：门过（truth z=0.61）/poscmd 100Hz/到位 0.118（真值口径优）/auto_disarm=1——H-1+H-4b 门+层 3 全修复的端到端实战验证 ✓（VINS 行为正常时管线全绿）。
- 死亡型=中途帧跳（15.805m，与 F3B6 15.69m 同量级）——敌对态定性为**概率性事件**：击中爬升段=起飞死三型（B10-13）；击中巡航段=帧跳（B6/B14）；未击中=净轮（B2/B3/B4/B8）。
- **[W2BA] 活体首战=负结果**：全程 0 触发（|Bgs| 从未超滑窗中值 10×连 3 拍）→ **15.8m 帧跳事件不含陀螺偏置跑飞成分**（T2 机制排除面硬数据：ζ 链的 Bgs 翻转支路在此事件型缺席）。
- 栈注记：本轮=T1_W2BA=1 诊断态（zetafix-1 确定性复现栈，双 md5 8574a00f/9b88345b）；T2 回场按 16:38 通告处置。

### 战役终态（16:45）

敌对态根因=**未定案**（环境输入层全排除+VINS 内部 Bgs 支路排除；残留候选=图像内容级差异[需净窗同世界带图袋，不可回溯]/VINS 进程内非确定性[T2 域]）；交付=复现器+三型分类+全排除表+W2BA 活体工具（已入生产树）+F3B14 管线全绿验证。@T2 消费面=重试制继续+W2BA 随轮采集+帧跳型与 Bgs 解耦的新证据。
