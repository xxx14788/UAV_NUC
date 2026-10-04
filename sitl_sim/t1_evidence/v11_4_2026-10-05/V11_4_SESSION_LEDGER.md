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

## B. 待办（滚动）

- A1-尾：轮后 replay 微基准（img_fp 单面耗时切分）+ B 臂无探针对拍。
- img_fp 预算表补 3090 列（多轮样本汇入后落账）。
- W-A build 窗需求（P2/w2b 双流写码）挂净窗依赖不变。
- 深挖池≥3 维持。
