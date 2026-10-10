# T1 任务书 v11.39 完成清账版（2026-10-10 20:1x；四线第十八周期收官账）

> 你是 **T1（px4ctrl/基础设施+实机工程线）**。本件=v11.39 执行版（2026-10-09_T1_px4ctrl_v11.39.md）的完成清账版；**原执行版弃读存史**（历史文件不动）。
> 台账=3090 `~/sitl_sim/t1_evidence/v11_39_2026-10-09/`（本周期账正源）+旧机 `~/sitl_realmachine/`。本件 Windows 权威+3090 双份 md5 三处一致（部署行见文末）。
> 通用纪律全沿用（红线 1-24+等待协议 v2+穷尽制收工+会话驻留四条）；nuc3 冻结维持；STATUS 双文件机制（正源=HOME，收工 cp 镜像随 commit）遵照执行。

## 双必达终判：✓✓

- **①20 轮复验批执行完+重判终判表落盘 ✓**：批 15:55:13-18:08:24 干净跑完（20 轮+单次重试制），六环判读器出 `hafix_reverify/verdict_v1139.csv`+终判表——**3/20 PASS、批终判 NOT-PASS（诚实入册）**；FAIL 分支回挖报告（`hafix_kill_dig_v1139.md`）+二次修复+10 轮增量批（`hafix_increment10/`）全部落地。飞行窗物理不可行条款未触发（窗口空闲即跑）。
- **②2b+2c 落地+《实机域估计质量报告 v2》出稿+首飞呈报件出件 ✓**：`unit2b_postcal_v1139.md`+`unit2c_ground_drill_v1139.md`+`est_quality_report_v2.md`+`firstflight_gonogo_v1139.md` 四件全落台账。
- 达成后继续穷尽（FAIL 分支二次修复+增量批亦毕，见 A）。

## 保底清单六项对账

| # | 保底项 | 结果 |
|---|---|---|
| ① | 20 轮复验批执行完+重判终判表落盘（含 FAIL 分支回挖报告） | ✓（3/20 NOT-PASS+回挖三层机理定案） |
| ② | HAFIX 三案落码+干测（过程件） | ✓（干测链 8 发+gtest 51/51） |
| ③ | 2b 参数复测+2c 不解锁演练落地 | ✓（均落台账件） |
| ④ | 场景批五袋判读入册+《实机域估计质量报告 v2》出稿 | ✓（五袋全 IN-EXPECT+报告 v2） |
| ⑤ | 留守件消费+M1 终态行+首飞呈报件无条件出 | ✓（static_watch 判读 v2+病理报告 v1.2 追加节+呈报件五节） |
| ⑥ | STATUS 诚实夜报+《可做而未做清单》 | ✓（`night_report_v1139.md` §A-F 全） |

## A. 完成账（按单元）

### 单元 0 开工收件+留守件消费
- 开工：git 同步（behind=0/ahead=0）；3090 残场零进程/df 48%；旧机会话初 ssh 超时+ping 50% 丢包（04:27 复活，全晚稳定）；旧机栈全停态核验+`vins_kill_watch`（纯取证看门）保留在役。
- **留守件消费**：旧机 `static_watch/` 123 件 ALERT+快照（9.3MB）tar 回拉 3090 归档；判读两版——v1 勘误（ALERT 件=同一累积 vins log 每 5-6.5min 全量重解析，非独立周期；t*=347s 全同为证）→v2 重构（末件 60s 段 |Bas| med 时间线 679 段=11.3h）：**4 个病理周期**、首周期发作 t*=347s（跨日稳定）、重启后发作滞后 min=1020s/p50=3900s/p90=13230s、周期长度 p50=2760s、**无一周期自然恢复**（回落=重启事件）；04:44-04:48 断段污染注记维持。产物 `static_watch_judge_v2_v1139.md`+`static_watch_cycles_v1139.csv`，并入《实机静态病理报告》v1.2 追加节（`static_pathology_v12_append.md`，正本=v11_34 目录报告已追加+镜像 v11_39 目录）。

### 单元 1 HAFIX 修复战役（本周期头号件，全程走完「三案→复验证伪→回挖→二次修复→增量复验」）
1. **三案落码**：P-1（KILL=MAV_CMD_DO_FLIGHTTERMINATION 400/param1=1.0 终止语义+返回检查+FAIL 行）+P-2（disarm 后置 landed 门）+P-3（drill 批编排：EV 权威行提取/轮间强清断言/单次重试制/注入前 flying 门）；fsm_decision.h 新增 HafixInputs/decide_hafix 纯决策层（可测面）。gtest 全绿。
2. **干测链 8 发**（关键三发）：run_042425=时序链全对（watch→5s→AUTO_LAND→15s→KILL 20.0s 首发）但 **400 单命令 ACK 后被活跃 setpoint 流覆盖成 AUTO.LOITER 悬停**（armed 恒 True 207s 实测）→二次修复补 cmd179/param2=21196 双命令；run_040715=T2 并发编译复测重链接 libvins_lib.so 瞬态致 vins_node exit 127（共享树协同注记，非本线缺陷）；run_182423=**六环全链闭环**（详下）。
3. **20 轮复验批**（15:55:13-18:08:24，S1 hover_1m/S2 hover_3m/S3 transit/S4 land_1m 各 5 轮，批前环境检查单+P-3 强清生效验证在册）：六环终判=**3/20 PASS、批 NOT-PASS**。S1/S2/S3 全 15 轮同构画像：r1 watch/r2 AUTO_LAND/r3 KILL(双命令全 ACK) 触发全对，但 **armed 恒 True、z_min 0.58-1.08m 悬停到 bag 终、landed=0、auto_disarm=0**（无人机不落地）；S4 5 轮=落地边界轮（r1/r3 注入时已落地=HAFIX 零行正确静默；r2/r4/r5 踩线 PASS）。
4. **FAIL 分支回挖报告**（`hafix_kill_dig_v1139.md`，ulog+源码级三层机理，详 C-1）：①400 被 failsafe 覆写；②179+21196 ACK-无操作；③**梯①盲降被 decide_land 的 `!odom_ok→MANUAL` 一拍弹回（px4ctrl 域根因）**+SITL GPS 兜底勘误（iris 模型带 GPS 插件→VINS 死≠PX4 位置盲）。
5. **梯①盲降结构二次修复**：decide_land odom 门旁路（ha_blind_land）+HAFIX 切 AUTO_LAND 时双锚（set_start_pose+toggle_time，get_takeoff_land_des=时基开环下降对陈旧 odom 免疫）+OFFBOARD 重入+idle 门（px4_on_ground||odom_ok，防冻结 odom 伪满足 land_detector C1/C2 高位误 idle）+cleared 语义改「仅 disarmed 终态」+stage1 流恢复复位保留+弹回重断言保险层。**gtest 51/51**（37 旧+9 HAFIX+5 盲降/复位）；干测 run_182423 六环闭环（watch@101.5→AUTO_LAND@106.5→盲降 9s 触地→**disarm OK@117.6（P-2 梯③，PX4 未加 force 接受=其自身落地检测确认真触地）**→cleared，RESULT=PASS）。
6. **10 轮增量批**（18:30-19:36，S1×4/S2×3/S3×3）：**物理链 10/10 全达成**（每轮 r1 watch+r2 AUTO_LAND+r4 armed drop@111-114s+r5 z_min=0.10 触地+disarm），预注册判据 9/10 PASS（S1 r4 FAIL=harness RESULT 缺 LANDING 行的格式缺漏，物理链完整在案）；**r3 KILL 全零=设计行为**（盲降平均 15s 内触地，先于 KILL 死线 dead_s+kill_s=20s，KILL 为带弹零依赖）；S1 r4 注入前 51-58s VINS 流拍脸段=watch 流恢复复位零误触实证。对照：修复前 15/15 悬停不落→修复后 10/10 落地+disarm。
- 事故登记：**D-1010-T1-01 批多实例连环互杀**（发射期 kill 未验尸→旧批存活→双批并发→force_clean 互杀+孤儿 drill 跨批注入，两实例俱亡后残留进程泄漏）——根治=PID 文件单例守卫（pgrep 方案自噬见 F-1）；三次发射重启（set-u 崩/互杀/守卫版干净起）全程如实入 summary。

### 单元 2 物理窗执行（远程件全落）
- **2a 复苏+depth 判定**：正源脚本起栈（IMU 默认 50Hz——203Hz 行 [10-10 停用] 注记在正源脚本，遵照）；FC 无需重插（断电后正常枚举 ttyACM0）；**depth 复活**（aligned_depth 30.06Hz 在役；hwmon "HW not ready" 仅启动期 4 次）——预注册「Asic 持久故障」分支未触发；磁盘按 1.1GB/min 管理（旧机袋已迁 3090，r2_scen2 md5 锚 a218893a 抽验一致）。
- **2b 校准复测**：GYRO 三轴带内 PASS；ACC 重校真写入（X -0.2409/**Y +0.2808（vs 重校前 -0.2583=翻号级）**/Z +0.2214）；**mag XOFF 首次非零 0.4066**（Y -0.0171/Z +0.1257）；固件 **v1.17.0**（Flight software 011100ff）+**FC=Auterion PX4 FMU v6C.x**（lsusb）入硬件矩阵；battery=0.0V（未插电池态）；自检终判 NO-GO 唯一 FAIL=battery（正源 `preflight_v1_postcal_20261010.txt`）。
- **2c 地面版演练（不解锁版）**：armed=False 全程；杀 VINS 后 HAFIX 零行=**flying 门设计边界实证**（订阅链核验完备：imu_propagate/state/battery/extended_state 全订阅——非输入链缺陷；昨晚断链窗 watch 0 触发=同因）；监控 v1 告警链实证（TIMEOUT NEW→PERSIST→flag 置位）；VINS 复苏 14.86Hz；勘误订正：演练时旧机 px4ctrl=旧二进制（修复 06:1x 才 pull+rebuild），订阅链/watch 判定面结论不受影响（该面逻辑两版逐位同），**修复版实机进程内首跑=06:47 起**（pid 687939，源码 md5 与 3090 一致 8ada48fd）。
- **2d 五袋判读**（T1 odom 面×T3 j0d 流分解双工具逐袋互证）：五袋**全部 IN-EXPECT 零异常分型**——静置 184s 端点漂移 0.003m（0.001 m/min）/微抖 maxjump 0.0003m（微动不触发爆=USB 劣化单一根因对照闭合）/缓动漂移率 0.214 m/min（coh=0.175 混合型=实机 transit/慢淋首观测，与 SITL 定向慢淋 coh≈1.0 三数量级谱系分离）/走动 30m 往返差 0.058m/平移多趟散布 0.0705m；|Bas| 全程收敛 0.013-0.022 零发作；《实机域估计质量报告 v2》出稿（=首飞呈报件§②直接输入）。
- **2e depth→planner 贯通（输入链面）**：适配稿 `run_planner_realmachine_vins.launch` 落码部署（基=SITL 同构入口，差异三处：depth 话题=aligned_depth/D435 factory 内参 387.508/yaw 基准经 odom）；实跑验证=grid_map 订阅 depth 29.9Hz+odom 直供、FSM WAIT_TARGET 无错、include 全参校验补齐 point1-4。**执行面（goal→poscmd→真实飞行）未测**（需动力，见 B-4）。
- M1 状态行随件更新（v11.39 更新段已入 M1_GATE_CHECKLIST.md）。

### 单元 3 M1 终态盘点+首飞呈报件（无条件出件）
- `firstflight_gonogo_v1139.md` 五节固定结构：①M1 11 行逐行（**10/11 全 PASS+行 5 FAIL 侧收口带二次修复**；行 3 收口带动力套跳过注记/行 4 收口带降级注记/行 9 净面待电池）②实机估计质量画像（五袋定量表）③失效安全链二值盘点（除行 5 外全在役）④已知风险清单（动力套未验/KILL 实机未验/静置病理/电池/depth 边界态/IMU 50Hz 带宽）⑤go/no-go 判定框架（硬红=行 5——**增量批 10/10 后硬红解除→go 候选**；黄=动力套跳过下人工接管依赖+首飞现场项；结论按数据落、授权=用户物理授权域）。
- 呈报件已随增量批结果更新行 5 与§⑤。

### 单元 4 池件（全落）
- 监控 v1.2 四注记落码（D 检测器双口径 m/min/phase 横跳 vz 迟滞≥1s/SIGTERM 受控收尾 dump/P-2 TERMINAL 面 armed-drop 判 SAFE_LANDED/AIRBORNE_KILL/UNKNOWN）；py_compile 过+双副本 md5 一致。
- **VINS 内存泄漏定案**：两进程实测 0.6GB/h（1.0→6.9GB/9.6h）与 1.45GB/h（137MB→5.92GB/4h）——速率非平稳未归因；odom 15.0→5.73Hz 劣化@9.4h/7GB（重启即回 15.08Hz）；队列面排除（发布器 1+订阅 3 无堆积）；跨重启复现=进程内泄漏。工程边界=实机连续在役保守 5h（NUC 15GB RAM）；watch2 在役续采（pid 变化记 RESTART 行续采）。`unit4_vins_memleak_v1139.md`。
- 旧批病理标本特征化（升正式件）：雪崩袋首跳 23:04:34（袋起+27s）/轻度袋首跳 23:08:22——**爆起全部早于 USB 断链 23:09:39**（早 5min/1min）；断流袋 odom 零有效帧——单一根因（USB 劣化渐进期数据污染）证据链深化，无需重开归因。
- .gitignore test/ 条目根除（第四次复发源=VINS-Fusion/.gitignore L5 上游自带；目录现空、行已注释保留死码）。
- p1 五件动态栈基准补测：IMU 49.8/infra 29.99+29.98/depth 30.08/imu_propagate 49.86/odom 15.13 全绿（`p1_5piece_bench_v1139.txt`）。
- 旧机磁盘水位注记维持（87%/31G free）。

### 收工链
- STATUS 五行（03:4x 开工/06:3x 中期/15:3x 批发射/17:0x 回挖+事故/19:5x 收官）+镜像 cp+md5 一致（29768231）；commit ee15996（修复+证据主体）→22d8aa9（收官）→a09d549（STATUS 镜像）全推 UAV_NUC。

## B. 剩余清单（未做/未竟，客观）

1. **S4 降落段注入时序**：近点 goal 起飞→落地全程实测 ≈74s（poscmd-live 起），下降段仅约 20-30s，postgate=40 注入点在 20 轮批中 2/5 落在落地后——中段下降注入的时序精度未达成（增量批以 S1-S3 覆盖盲降验证面，S4 未入）。
2. **179+21196 与 400 的实机行为验证**：实机 FMU v6C/固件 v1.17.0 的 MAVLink kill 路径零数据（需电池/动力台架；被动力套跳过裁定拦截）。
3. **2c 完整怠速版演练**（不 arm 不怠速降级版已毕；升级版同被动力套拦截）。
4. **planner 实机执行面**：输入链贯通已验，goal→poscmd→真实飞行的执行面零实测。
5. **400 在 setpoint 持续流下的生效实证**：修复后 10 轮 KILL 全零（盲降先于死线落地），「盲降流不断→failsafe 不活→termination 意图可应用」当前为源码推演，未实测。
6. **VINS 内存泄漏 root-cause**：速率非平稳（0.6↔1.45GB/h）归因未开；工程边界+重启规程已先行。
7. **增量批判读生成器 20 槽位表头失真**：修正终判块已附于 `hafix_increment10/final_verdict_v1139.md`；生成器场景/轮数参数化未做。
8. **A1 扩批**：授权在 T2/用户（未动）。
9. **p1 五件基准正式文书化**：数据已收（txt），未出正式基准文书。
10. **晨间旧机 VINS 重启**：当前在役进程按 1.45GB/h 外推过夜 ~03:00 触 15GB 顶；晨间首件=按处置手册重启规程起 VINS（运维必办）。

## C. 卡点与阻塞（客观问题面描述；不含解决方案）

- **C-1 PX4 SITL 构建的 MAVLink 空中停电机路径失效**：复验批 15 轮实测——px4ctrl 1Hz 连发 cmd400(param1=1.0)+cmd179(param1=0,param2=21196) 各 413/412 次，FC 全部 ACK ACCEPTED（ulog result=0、ACK-命令延迟 8ms），同时 armed 恒 True（vehicle_status 2.78Hz×490s 零翻转）、电机输出恒定（actuator_outputs 5299 样本 1714-1728 零波动）、z 悬停全轮不落。已查明子机理：400 的 termination 意图被 failsafe 每周期覆写（Commander.cpp:2383 `nav_state=modeFromAction(failsafe.selectedAction(), intention)`；setpoint 断流期间 LOITER failsafe 恒活，nav_state=13 从未进入）。未查明子机理：179+21196 的 ACK 与执行断链——`Commander::disarm(forced)` 源码逐行正确（force 跳过 landed 检查直设 DISARMED），但 ulog 事件面 23 条零 disarm 事件、console 零「Disarmed by」行、arming_state 零变化；ACK 来源与函数体未执行之间的断链源码级未定位。边界：以上=SITL 构建 d6f12ad1c4（commander 零本地改动核验）的实测；实机同路径行为未知。现状：px4ctrl 梯①盲降已在零 KILL 依赖下 10/10 落地（A-1.6），但「该构建/该实机上 MAVLink kill 是否可用」这一问题未关闭。
- **C-2 动力套三项零实证（用户裁定跳过）**：怠速/急停拨测/压测未做，电机/电调/油门响应零实测数据。被拦截件：B-2/B-3/B-4 及首飞本身。
- **C-3 battery 0.0V**：FC 当前 USB 供电、电池未插；自检 v1 终判 NO-GO 的唯一 FAIL 项；插电池+复跑前无法转净面。
- **C-4 VINS 内存泄漏**：0.6-1.45GB/h 非平稳线性涨势（速率相关因素未归因）；7GB 附近 odom 输出率 15→5.7Hz（内存压力，重启可逆）；RAM 15GB 下连续在役受硬约束（保守 5h）；root-cause 未开。
- **C-5 静置病理**：首周期 t*=347s 跨日稳定；重启后发作滞后 min 1020s（4 周期样本，p50 3900s）；无一周期自然恢复；与 C-4 是否同源未查。
- **C-6 S4 降落段注入窗口窄**（同 B-1 事实）：非机制问题，窗口本身窄。
- **C-7 旧机磁盘 87%**（31G free）：录袋前须复核。
- **C-8 nuc3 冻结维持**（用户指令）。
- **C-9 首飞授权未决**：呈报件已出（硬红解除/黄项在列），授权=用户物理授权域。

## D. 资产

- **台账** `t1_evidence/v11_39_2026-10-09/`：hafix_reverify/{summary,ev_index,20 轮 log,verdict_v1139.csv,final_verdict_v1139.md,batch_env_checklist.md}；hafix_increment10/{summary,ev_index,10 轮 log,verdict_v1139.csv,final_verdict_v1139.md（含修正终判块）}；hafix_kill_dig_v1139.md；est_quality_v1139.{csv,md}+est_quality_report_v2.md；static_watch/{9.3MB 原档}+static_watch_judge_v2_v1139.md+static_watch_cycles_v1139.csv；static_pathology_v12_append.md（正本已并入 v11_34 报告+镜像 v12 副本）；oldbatch_pathology_timeline_v1139.md；unit2b_postcal_v1139.md；unit2c_ground_drill_v1139.md；unit4_vins_memleak_v1139.md；firstflight_gonogo_v1139.md；night_report_v1139.md；p1_5piece_bench_v1139.txt。
- **代码**：px4ctrl（P-1/P-2/P-3+梯①盲降二次修复+decide_hafix/ha_blind_land 纯决策层+gtest 51/51）；t1_odom_monitor_v1.py v1.2；t1_drill_run.sh 门 v4；t1_hafix_reverify_v1139.sh（PID 守卫）+t1_hafix_increment10_v1139.sh；t1_rejudge_hafix_v1139.py（参数化）；t1_static_watch_judge2_v1139.py；run_planner_realmachine_vins.launch（旧机 planner 适配稿）；VINS-Fusion/.gitignore 根除。
- **M1 门检查单**：v11.39 更新段已入（v11_28/local_staging/M1_GATE_CHECKLIST.md）。
- **commit**：ee15996→22d8aa9→a09d549（全推 UAV_NUC）。
- 旧机在役件：栈全活（mavros/rs/VINS fresh/px4ctrl 修复版/planner）+vins_mem_watch_v1139.csv 续采+vins_kill_watch。

## E. 等待登记

- W-首飞授权（用户物理授权域；呈报件=输入）。
- W-动力套窗/物理配合（用户；解锁 B-2/B-3/B-4 与电池复核 C-3）。
- W-T3 影子重判消费（复验 20 轮+增量 10 轮的 --pattern 一键面在册）。
- W-晨间旧机 VINS 重启（B-10 运维必办）。

## F. 坑账（本周期新增八条，全文=night_report_v1139.md §F）

1. **批多实例连环互杀（D-1010-T1-01）**：kill 未验尸→旧批存活→双批并发→force_clean 互杀+孤儿 drill 跨批注入；守卫 v1 pgrep 方案自噬（$( ) 替换子壳继承父 cmdline 被自身匹配）→v2 PID 文件根治。
2. set -u 遇 ROS 链复发（批脚本 source 前未 export ROS_DISTRO；drill 有正解模式未复用）。
3. pkill -f 自匹配第三次（匹配远程 bash -c 自身命令行秒杀会话；-x 精确名解）。
4. 近点 goal 落地边界（到达+降落≈poscmd-live+30-70s，固定 sleep 注入窗必落地面→flying 门 v4 双门+postgate 从 armed 起算）。
5. land_detector 冻结 odom 伪落地（C1+C2 伪满足→高位误 idle 坠落风险→idle 门）。
6. ulog 时间戳=UTC（rootfs/log 目录名比本地 -8h）。
7. catkin build 不重建 gtest 二进制（--make-args tests 拖累全依赖链；build/px4ctrl 直接 make 单目标解）。
8. 长 ssh 前台命令超时截断外层循环（两轮补登实证；轮编排必须 setsid 后台+轮询登账）。

## 附：M1 门检查单 11 行终态（正源=M1_GATE_CHECKLIST.md v11.39 更新段）

| # | 行 | 终态 |
|---|---|---|
| 1 | 台架环境+全栈基准 | PASS（p1 五件补测全绿） |
| 2 | 实机 config+审签 | PASS 带注记（+固件 v1.17.0/FC v6C 版本行） |
| 3 | 硬件矩阵+物理窗 | PASS 带注记（2a/2b/2e 收口；动力套三项=用户裁定跳过） |
| 4 | 演练五案+实机地面版 | PASS 收口带降级注记（2c 不解锁版；完整怠速版待动力套） |
| 5 | HAFIX 多场景+复标 | FAIL 侧收口（复验 3/20 NOT-PASS→梯①二次修复→增量批物理链 10/10） |
| 6 | 基线=旧机 | PASS |
| 7 | OS 调优 | PASS |
| 8 | failsafe 残件+P3 | PASS（G-1 低优先注记） |
| 9 | 自检脚本 v1 | PASS（净面待电池插电复核） |
| 10 | 处置手册 | PASS |
| 11 | 止损实机语义 | PASS |

——完。下任首件=B-10（晨间 VINS 重启）+W 面消费；正式排程件=待用户下一版任务书。
