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

### A7. 对审 v1.3（预注册冻结 b79279a；执行挂 T3 长间隙）

- H=MACH3/MACH8（T2 定案指认带图轮，中漂移带）×C=X1final；判据逐字 v1.2+W_drift 窗（truth−goal 误差峰±10s）；跨机混杂防线（双 obstacles world 已核+Gazebo 同 11.15.1 T3 勘误）。
- **违规自查在案（02:56 通告 @T3）**：预检 launch 误发（ROUND-LIVE 态 31G 读）——pkill 即杀，进程死于 import 错（rosbag 未打开=零实际 IO），T3 取证未受冲击；根因=driver 误放运行区目录（xa 库在 git 树）+预检未过 pgrep。修正后待 T3 X 线轮（X2g 系连发中）长间隙执行。
- img_fp 微基准终判 PASS（p99=4.66ms≤5ms；v1 版 OVER 系 rosbag 惰性反序列化混入，deser 已分离计）——预算表 3090 列终稿（c1064c8）。

### A8. C-17 敌对态消费（02:45 T2 定案）

- D-1005-T1-02 落 DECISION_LOG：H-machine 强支持（敌对 17%≤25% 门）→ 三刀降级档案件；**B 路 HF 面判别价值重标议题**（w2bb 告警 10/12 vs 敌对 2/12 不对应——坍缩在风暴/中漂移轮常态存在）；候选②表述修正（进程内呈现维持×根因归机器层诱发，两级因果相容）；敏感性口径（大漂移跨机恒在 92%）采纳=消费侧防线价值不降。

## B. 待办（滚动）

- 对审 v1.3 执行（T3 长间隙；driver 已就位 git 树 analysis/）→ 终章合并 v1.1/1.2/1.3。
- P2 A/B 飞轮（净窗依赖；MACH8/12 候选确认后）。
- B 路 HF 面判别重标（@T2 形态学交叉）。
- 深挖池维持：EXP3 长窗/P0-A.5/F4b/栈号跟随（栈号=新 px4ctrl 0e832aa7 已按实读制登记）。


