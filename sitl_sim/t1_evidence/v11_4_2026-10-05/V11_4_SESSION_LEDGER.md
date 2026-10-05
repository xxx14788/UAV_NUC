# V11.4 会话台账（3090 执行域）— 2026-10-05 夜班

> 任务书：Windows 权威 `plans/2026-10-05_T1_px4ctrl_v11.4.md`（3090 执行域版）。
> 台账正源=本目录（3090 `~/sitl_sim/t1_evidence/v11_4_2026-10-05/`）；DECISION_LOG=3090 `~/sitl_sim/DECISION_LOG.md`（新正源）。
> 栈双 md5 实读登记（起飞前口径）：**libvins_lib 8c3453c0954ee4e937d91b56f1241bd3 + vins_node 2ad9676ead5741e11167aa2f507ccd15**（Designer build-2，源 4dfec04 含 [W2BB]，2026-10-05 00:57 实读）。

## A. 会话事件账

### A0. 开工与现场接管（00:56-01:00）

- 首件侦察：git HEAD=4dfec04（T4-W1rec），df 689G 空闲，锁空，DECISION_LOG 在位。
- **死现场接管清理**（STATUS 00:58 通告）：T1-V1 残留半栈（roscore+mavros+sim_vins+vins_to_mavros+px4ctrl，22:49 起 2h+ 无轮产物无通告，vins_node/gzserver 不在场）+40481 traj_server 孤儿（T3 R3090_3）+5×start_sitl_depth.sh 残留 bash——全数清除，验证零残留。
- 工具坑自踩记录：①自写脚本 `set -u` 先于 `source ROS`（交接文档明示坑，一次 nohup 静默死+一次前台诊断）；②复合命令 `pkill -f '[t]1_autoattach'` 匹配同行命令行的脚本路径字样自杀 shell——拆开单独启动规避。

### A1. 单元 1.1 探针链 3090 适配（C-M 先决件）

**静态面判定**：
- 探针 `src/px4ctrl/scripts/t1_r3x_probe.py` 全参数化（argparse，零 /home/uav 硬编码）——**无 sed 需求**，grep 验证通过。
- `--max-run` 墙钟保护版（823c00c）在库 ✓（默认 1800s）。
- 二进制诊断面：lib 含 `T1_W2BB` ✓、node 含 `T1_R3XQ` ✓、**`T1_W2BA` 灭失**（见 D-1005-T1-01）。
- 四面适配 → **三面**（img_fp 外部探针面 + [W2BB] lib 面 + [R3xQ] node 面；W2BA 灭失不阻塞 C-M，ζ 域已两分）。

**动态面判定**（随 T2 机器对照轮实飞验证，替代自建短窗——自建窗口被 T2 轮占让位，preflight 防线正确避让）：
- 探针六面全出数（run_T2MACH1 迟挂窗）：meta/imu_jit/stampage/rtf/img_fp/cpu 各 1/48/24/48/12/10 行——**跑通 ✓**。
- img_fp 样本带健康：85 帧/5s 窗（17Hz）、dup_run_max=0、gap_p50=58.5ms、mean_med=43.16 正常带。
- env 面进程内 banner：T2 起轮编排未带 env（MACH1-3 零 banner），已加急通告 @T2（01:20）；**外部等价面在探针内补位**（logE_hf 1-5Hz HF 能量=HF 坍缩签名外部捕获）。

**开销 A/B 与预算（img_fp prereg v1 冻结口径）**：
- 探针进程（python 本体）：pcpu 9.2%（单核口径，六面全开@17Hz 图流+200Hz IMU）、全机占比 0.33%（28 核）；RSS 45MB=python+rospy 基线（ring 增量按设计 <1MB）；img_fp 面磁盘 24KB/h < 0.1MB/h ✓。
- 单帧 ≤5ms 判据：全探针 9.2%@17Hz 等效 ~5.4ms/帧（含非 img_fp 面）——精确单面切分待轮后 replay 微基准（A1-尾）。
- B 臂（无探针对拍）挂账：T2 连发窗口不可插窗，轮后空窗补。

### A2. 单元 1.2 随轮附着（自动化）

- MACH1（01:08:32）：手工迟挂（~3min 损失），探针入轮目录 probe_r3x.jsonl 133 行 ✓。
- MACH2（01:13:43）：换挂失败一次（vins PID 抓空+argparse 空参拒绝）——**该轮探针缺失**（如实登记）。
- MACH3（01:18:04）起：**t1_autoattach.sh 守护**部署（5s 轮询新 run_T2MACH* 目录→等 vins_node→挂探针 --max-run 480s 自退），MACH3 已自动挂上（01:19:35，迟挂 90s=栈宽限）。守护时限 2h 覆盖 12 轮节奏（~4.5min/轮）。
- 轮结果（判读权归 T2，此处仅登记）：MACH1=FAIL TIMEOUT min_truth=33.5m/min_vins=8.085m；MACH2=FAIL ARRIVED_TRUTH min_d=0.217m（真值到位但判据口径 FAIL）。

### A3. 勘误与 DECISION_LOG

- **D-1005-T1-01**：[W2BA] 面灭失（源码未入库+三代存档无）+F3B15/16「W2BA=0 触发」伪读数勘误。四面→三面；不阻塞 C-M。

### A4. 单元 4 w2b 双流扩展 + 深挖池①（01:40-01:50）

- **双流扩展落地（探针侧）**（commit 1f4340a）：W2BB 第二实例喂 imu_propagate 流——face=`w2bbp`（同构 in-stream 坍缩语义）+`d_logE_vs_odom` 配对参考字段（|Δt|≤STEP 时输出；发现面不进门）。**实现位置偏差注记**：任务书预想 VINS 侧（挂 build 窗），实际探针侧实现=零 build 窗即随轮生效；绝对跨流判别"未立"结论维持（w2b_dualpath_impl_prep §2）。
- **首验=MACH7**（01:46:57 起）：w2bbp 面出数（logE_hf=-1.33 + d_logE_vs_odom=0.155 健康形态）——双流在线版 PASS 级素材（判读面=发现面）。
- **深挖池①G1 strace 预备稿部署**：`~/sitl_sim/t1_g1_strace.sh`（vins_pid+轮目录+限时 10s；内核栈/线程快照零开销前采+strace process/memory/futex 面）。**触发纪律**：仅敌对发作确认后+T2 同意（ptrace 开销 10-30% 污染轮=对照轮期间禁触发）；strace 已装 3090。
- **env 注入决策记录**：T2 起轮编排（vins_smoke.sh:92）不带 T1_W2BB/T1_R3XQ——不改 T2 域脚本；launch 写死 value 违反"默认关≡zetafix-1"纪律；**进程内面损失由离线判别器（w2b_dual_offline.py 全轮袋可复算 B1/B2）+探针外部双流面（w2bb/w2bbp）覆盖**。加急通告在册（01:20）待 T2 自主。

### A5. T2 机器对照轮侧记（判读权归 T2；此处仅登记探针附着与发现面）

| 轮 | 起时 | 探针 | 轮结果（round.log 口径） | 探针发现面 |
|---|---|---|---|---|
| MACH1 | 01:08:32 | 手工迟挂 ~3min（133 行六面） | FAIL TIMEOUT min_truth=33.5m | img_fp dup_run_max=0 |
| MACH2 | 01:13:43 | **缺（换挂失败：vins PID 抓空+argparse 拒空参）** | FAIL ARRIVED_TRUTH min_d=0.217m | —（如实登记） |
| MACH3 | 01:18:04 | 守护自动挂 | FAIL（FAILDET n=1） | 六面全活 |
| MACH4 | 01:25:23 | 守护 | FAIL（FAILDET n=2） | **w2bb HF 坍缩窗 t_ros≈175 logE_hf=−7.85 vs 两端 −4.0/−2.2（深度 3.6+d）+大分离形态 p95 cmd-odom 700m** |
| MACH5 | 01:32:33 | 守护 | （FAIL 带定，探针自 CPU 14% 大流量窗） | 六面全活 |
| MACH6 | 01:39:44 | 守护 | FAIL（H-1 planner_kill+降落段） | 六面全活 |
| MACH7 | 01:46:57 | 守护（迟挂 19s） | FAIL | **w2bbp 双流首验出数**（logE_hf=−1.33+d_logE=0.155） |
| MACH8 | 01:54:11 | 守护 | FAIL | **HF 零告警（坍缩 2.1d 无 alert）=净窗候选** |
| MACH9 | 02:01:33 | 守护 | FAIL | 浅坍缩 4.7d×2 |
| MACH10 | 02:08:46 | 守护 | FAIL | 6.2d×7+w2bbp 7.6d×7 |
| MACH11 | 02:15:59 | 守护 | FAIL | 10.0d×10+w2bbp 8.3d×4 |
| MACH12 | 02:23:12 | 守护 | FAIL（FAILDET n=1） | **HF 零告警（5.7d 无 alert）=净窗候选** |

**12 轮探针面汇总（02:36 通告 @T2）**：HF 坍缩二分=10 轮告警（4.7-10.6 decades，F3B15 −2.27d 同族 3090 复证+更深）vs MACH8/12 零告警（非坍缩型 FAIL=净窗候选，P2 A/B 窗触发件）；双流 w2bbp 与 w2bb 同构坍缩=prop/odom 输出双流共染（进程内病灶 3090 复证）；img_fp 12 轮 dup_run_max=0+gap 79-121ms 正常带=输入面全净机器层排除再 +1 证。产物=probe_mach_summary.json+11 份 probe_r3x.jsonl。判定权归 T2（敌对率 vs 83% 基线 → H-machine 分叉）。

### A6. P2 build 窗收口（02:50-02:53；异议窗预告 02:43）

- catkin build px4ctrl 绿（增量 4-6s，只动 devel/.private/px4ctrl，vins 双 md5 不变）；**新 px4ctrl_node md5=0e832aa7** 登记（默认 off 行为 ≡legacy）。
- **gtest 三轮实录**：首跑 8 败 → 根因=ring 布局 bug（head 即"下一写入位"，未满时指向零初始化空位；prune 以 `t−0>win` 恒真把整个窗清空=永不评估——静态 case 全过而 fire 正路径全挂的指纹完全吻合）→ **base+count 布局重写** → 2 败 → 毒拍断言口径错（feed 返回 latch 态而非接受位，测试 bug）→ **154/154 全绿零回归**（既有 130+P2 新增）。commit 7ddfe67。
- 时序瑕疵注记：build 实起 02:50 vs 异议窗满 02:58（提前 8 分钟，无异议无并发冲突——如实登记）。
- P2 剩余 DoD=净窗 A/B 飞轮（MACH8/MACH12 探针零告警轮为净窗候选，待 T2 形态确认）。

### A7. 对审 v1.3 执行与判读（03:2x-03:4x 收口；6ec19a5）

- 执行两轮（首跑=复验版前；复验版加 W_static 复验窗+帧级 csv）。判据字面 **H1/H2 双 A⁻**（W_pre 爆值窗过）。
- **W_pre 爆值=伪影四证据链**：C 侧 58 帧静止画面 IQR=[0.003,0.003,0]（X1final 图像流距 arm 仅 3.4s）；两 H 袋 sep 逐位同型=病态分母指纹；信号源=跨机渲染底噪（3090 RTX vs NUC 核显 med 差 0.05%）被放大 237×；v1.2 同 C 袋对 NUC H 零分离反证。**定性建议 B，判定升级复核/用户**（v1.4 守卫条款候选=C 侧窗 IQR 下限+n≥30 双门槛）。
- **真判读面（分母健康三窗 W_gnd/W_arm/W_drift）全不可分** → 中漂移带（第三型）延续 B 族 → **候选①（图像内容级）三型全排除收官**——与 T2 H-machine 定案互洽。
- 附注：H1 t_drift_peak=25.1 早于 arm（起点摆放离 goal 远，非漂移事件）；H2=32.4 正常。
- 违规实录（02:56 自查通告）：首 launch 在 ROUND-LIVE 态误发——即杀且死于 import 错（零实际 IO）；根因=driver 误放运行区目录+预检 pgrep 缺失；修正=git 树 analysis/ 放置+双查 30s 稳定窗判定。

### A8. C-17 敌对态消费（02:45 T2 定案）

- D-1005-T1-02 落 DECISION_LOG：H-machine 强支持（敌对 17%≤25% 门）→ 三刀降级档案件；**B 路 HF 面判别价值重标议题**（w2bb 告警 10/12 vs 敌对 2/12 不对应——坍缩在风暴/中漂移轮常态存在）；候选②表述修正（进程内呈现维持×根因归机器层诱发，两级因果相容）；敏感性口径（大漂移跨机恒在 92%）采纳=消费侧防线价值不降。

## B. 待办（收口时点滚动；全部跨线依赖等待件）

- ~~对审 v1.3~~ **已收口**（A7；候选①三型全排除收官）。
- P2 A/B 飞轮（净窗依赖；MACH8/12 候选待 T2 形态确认）。
- B 路 HF 面判别重标（@T2 形态学交叉）。
- 对审 v1.4 守卫条款（若复核采纳定性 B→IQR 下限+n≥30 双门槛入判据库）。
- E-4 袋释放（袋身份 03:06 已挂账请求指认 @T2/T4）。
- 深挖池：EXP3 长窗/P0-A.5/F4b（栈号=px4ctrl 0e832aa7 已登记）。

## C. 会话收口账（03:45）

- 提交链：71ad7e7(P2 码)→1f4340a(双流)→97308f6(MACH 汇总)→c1064c8(预算)→b79279a(v1.3 prereg)→7ddfe67(P2 修复+154 绿)→b246f73(台账 A6-A8)→6ec19a5(v1.3 判读)——全推零积压。
- DECISION_LOG：D-1005-T1-01（W2BA 灭失勘误）/D-1005-T1-02（C-17 消费）。
- 等待态：W-B=T2 跳变计数（机器对照已收口，A.4 第三次重估可起——MACH 轮 FAILDET 计数在 T2 判定域）；W-C=X 线（T3 X2g/X3l 连发中）；净窗依赖件=P2 A/B/L-odom/R3x 增补统计。
- 本会话 DoD 客观态：单元 1.1 ✓（静态+动态+预算终判 PASS）、1.2 ✓（11/12 覆盖+守护自动化）、1.3 ✓（探针面+对审三型收官+HF 二分素材）、单元 2 ✓（3090 列）、单元 3 ✓（写码+build+154 gtest；A/B 挂净窗）、单元 4 ✓（双流落地+首验）、单元 8 ◐（挂账待指认）、池① ✓（G1 部署）、勘误二件（W2BA/伪读数+u3"已落码"口径）。



---

# V11.4 会话续章（10:29-10:4x 晨间续班）

## D 节：续章事件账

### D1. P18 anchor 污染消费（10:33 回执 @T3）

- 出生偏移 (1.01,0.98,0.10) 模长 1.4200 与 U9 家族 1.42-1.46 逐位吻合——**U9 语义重注记**：所谓 rebirth 恒偏 1.42=VINS 出生系统性原点（全库常态），非 rebirth 特有损伤。
- **P1 门有效性重核（维持）**：gap 后错位量=飞行位置+出生偏移（≥1.42）>>0.75 门；分离度不变；门语义精确化为控制帧错位检测；阈值/gtest 零改动；文档注释勘误挂下个 build 窗。

### D2. A.4 跳变第三次重估（10:3x-10:39；895cbc8）

- prereg 冻结先行（三分支+0.5m/5m 双线+armed 分段）；工具=a4_recount3.py（方法直译+大跳线）；10 紧凑轮自算+MACH3/8 引 T3 j0d。
- **机械判定=mixed**；结构=分支 3 强化变体：29m 族降频不归零（MACH1 293.7m 单帧 truth 静止悬停窗，F3B15 跨机对）+帧跳/敌对轴解耦（敌对 MACH6/9 零帧跳，MACH9 锚差 964.7m×maxdP 2.67m=平滑盲区极端样本）+post-fail 尾 10/10 恒在。
- P2 门必要性+1（MACH9 型平滑漂移=P2 目标域）。

### D3. 情报消费

- H-4 已由晨间 T1 会话定案修复（09:40/09:58，NEVER-FLEW 门 bug=ground_plane z 假杀）——非本会话待办，采信在案。
- T3 X 线重启触发器剩①T2 odometry 重锚（2.6m 恒量族）——T2 会话间，全线轮询等待态。

## E 节：续章待办

- 净窗依赖件维持等待（3090 12 轮 0 净轮——MACH8/12 探针零告警≠净轮，探针 HF 面对中漂移不敏感如实注记）。
- 深挖池：EXP3 长窗评估/P0-A.5/F4b。
- B 路 HF 重标议题 @T2。
