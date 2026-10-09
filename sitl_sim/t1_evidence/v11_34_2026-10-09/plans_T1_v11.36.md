# T1 任务书 v11.36 — 完成清账版（2026-10-09 白天落盘；v11.34 夜班执行后；v11.34 册弃读）

> 你是 **T1（px4ctrl/基础设施+实机工程线）**。执行域=3090（`ssh nuc2`）+旧机 NUC（`ssh nuc`，已上电、栈活、监控留守中）。
> **通用纪律（四册同源，全沿用）**：红线 1-24+等待协议 v2（轮询等待制醒来不靠人/池自补给恒 3 件/合法收工仅三种）+默认案推进制；**穷尽制收工**（双必达=下限/可动面穷尽/《可做而未做清单》进夜报/窗口穷尽编排）；**会话驻留四条完整版**：①在途件（批/链/build/采集/判读材料/IO 窗）禁结束会话，前台轮询保持在场；②轮询间隙=穿插件时间；③收工唯一条件=任务书全部单元完成 ∧ 在途件毕且结果全消费 ∧ 穷尽制三条件；④外因断开=事故而非收工模式，重启首件=消费在途件产物+STATUS 补行；判据/门值零变动；nuc3 冻结维持。
> 用户两裁定维持：失联不处置（关闭）/EV 不立项（同构维持）。
> 台账=3090 `~/sitl_sim/t1_evidence/`（本周期账=`v11_34_2026-10-09/`）+旧机 `~/sitl_realmachine/`（本周期=`09_reboot_stack_2026-10-09/`）。
> 四线分工下一周期由用户四册排程定；本册只载 T1 面。

---

## A. v11.34 完成账（夜班 03:31-04:55；双必达 ✓✓；commit 92e29e8+9d66a9c 已推远端）

### A1 night_chain 三消费（单元 0，全毕）
| 件 | 结果 | 证据 |
|---|---|---|
| 2d HAFIX 批统一重判 | **3d FINAL FAIL**（预注册判据照批脚本文末原文） | 批 summary HAFIX 列全零=grep 错文件 bug（判 drill stdout，[HAFIX] 行实在 ev/px4ctrl.log）→按正源（px4ctrl.log [HAFIX] 行+RESULT.txt LANDING/auto_disarm 行）重判 20 轮：**13 有效/7 无效**（6 FATAL[5"SITL 未清"+1"双目话题未出现"]+1 never-flew）；有效轮分型=4 PASS/5 悬空 FAIL/4 无触发 FAIL；**KILL 行 8 轮仅 3 轮落地（37.5%）**；ev 差一秒 2 例回退匹配；gatehit.json 在 drill-D1 轮全部不存在（harness 产物面，landed 改由 RESULT.txt 收） | hafix_multiscene_verdict_v1134.md + hafix_rejudge_v1134.csv + 双 bag 探针脚本 |
| D5 L2 | **PASS（监控 v1 链路级）** | 注入 23:17:43→TIMEOUT NEW@silence5.0s→PERSIST×4→odom_alarm.json 落盘全通；三注记=D 检测器压线命中（0.302>0.300+pursuit 段 15.5s RECOVERED）/phase CRUISE↔TAKEOFF 横跳 8 次/栈收尾后 pub_poll_err 刷屏（监控退出晚于 roscore） |
| P3 build | **失败→修复→全绿** | 失败三因：vins CMakeLists 主 include 组缺 src 跃点（estimator/p3_notify_codec.h 解析不到）+test_p3_notify 缺配对 target_include_directories 与 gtest main+PX4CtrlFSM.h P3 插入块在原 public 段前留 stray `private:`（把 traj_start_trigger_pub/State_t/构造函数埋进 private）；修复后 catkin 6/6+gtest 5/5+消费侧验证（生产 reboot_notify latched↔消费订阅绝对名一致+feed 解码+ha_stage≤1 才重置 HAFIX watch=契约一致） |
| 残场 | 44 个僵尸 t1_stoploss_watch（指向昨日已毕轮次）精确 PID 清零 | pgrep 自匹配 1 例辨明非残留 |

### A2 安全链收官（单元 1，全毕）
- **自检脚本 v1 落地实弹**（t1_preflight_check_v1.py，双端）：修 v0 实弹 bug（mavparam 子命令 fetch→get，v0 在实机全 None 的根因）；实机参数填齐（gyro 带 0.005——实测 XYZ=-0.0024/+0.0011/-0.0007 全过；4S min-v 14.0——BAT1_N_CELLS=4/V_EMPTY=3.6 实证；ACC 三轴注记行 vs 基准偏离<0.05）；新增第 6 项 |Bas|/cost 病理带（120s 窗中位）。**实弹首跑全项工作：battery 0.0V 真实 FAIL（台架未插电池）+|Bas|med=1.31>0.8 病理 FAIL（与 2d 采集窗互证）→NO-GO 正确**。json 落盘 preflight_v1_firstlive_20261009.json。
- **E5P CAL 考古池件消费**：实机 CAL 对照实测 addendum v1.1 入 e5p 评估件——实役机 gyro 三轴全在带内（E5P 型 -0.040 异常的 1/17 以下）=现役健康实证；ACC Y/Z 偏大转 P1 核对项（见 C-6）。
- **OS 调优持久化默认案落地**（旧机）：/etc/rc.local 三项（governor performance/swappiness 10/usb power on）+rc-local 服务 active=断电重放；setserial 行不适用注记（ttyACM0 无 latency_timer）。

### A3 实机主线（单元 2，2a/2d 毕、2b 降级收口、其余挂 C 节卡点）
- **2a 复苏序列全落地**：mavros connected=True+armed=False（FC 链路通）/rs infra1 29.98Hz/VINS imu_propagate 49.84-50.5Hz/v2m+px4ctrl PID 齐/Allan 袋断电后复验（md5 a4018158+rosbag info 8399s/419978 消息 RC=0）/df 32G 可用（86% 偏高注记）/开机自启 vins_kill_watch 看门查明为纯取证型无害件。**planner 勘误**：single_run_in_exp.launch 在旧机 planner 包内不存在（plan_manage/launch 无此文件）→v11.31 p1 全栈基准的 planner 件从未起（p1 日志同款 RLException）→**p1 实为四件动态栈，负载面欠估计注记（时延结论方向不变）**。
- **2d 静态病理深挖（头号产出）**：51min 静置窗（03:59-04:50）**两周期同构循环实证**——周期一完整闭合：|Bas| 收敛 0.0011→0.4249（0-60s）→逐位冻结（静态不可观，60-347s）→首破 0.8@347s（0.8682）→阶梯漂移 0.30→1.31（每级逐位冻结）→发射 1.31→**2.50 峰**@540.8s（1.2s 爬升）→**单帧塌落软重置 0.0031**@542.9s→周期二同构复现：0.0158 冻结 12min→解冻 0.46→0.0815 台阶→**29min 再破 0.8**→1.39→1.4650 冻结+T2diag 打印稀疏化（15Hz→稀疏；进程活+imu_propagate 50.5Hz 持续），至窗闭合未发射。cost 全程未爆（峰值 901；两周期带 205-901/212-648）；v11.31"三症状链"修订=**发射后至少两种结局（软重置自愈[本窗] vs Eigen 崩[v11.31]），cost 爆非必经**；发作时刻非确定（周期一 9min 走完/周期二 51min 未发射）。**任务含义四条已落码**：任务间隔>5min 须重启 VINS（预热=NOT-EFFECTIVE v11.31 定案故重启优先）/自检 v1 第 6 项入列/首破 0.8→发射有 ~3.2min 真实预警窗/HAFIX 管断流-监控 v1 管变质分工定案（静置病理不触发 HAFIX——odom 流活）。报告 v1.1 双端落盘。
- **2b 台架批（降级实况如实收口）**：用户不在场（凌晨）→降级方案中"桌面平移"亦需人动桌面→**本批=纯静置域**；《实机域估计质量报告 v1》出稿（流面全优 PASS[odom 50Hz/时延 p50 3.0ms 复标引用/链路 True/CAL 带]；质量面=静态病理 FAIL 带注记；场景覆盖注记四件挂物理窗）。**rs depth Asic 硬件卡死收卷**（详 C-2）。首飞 go/no-go 输入已写在报告 §4（条件 GO=自检 v1 全 PASS+间隔重启规程）。
- M1 状态行 5/11→**9/11**（检查单 v11.34 更新段已追加正源）。

### A4 收工件
STATUS 诚实夜报+可做而未做清单七件+坑账九条（v11_34 台账）；记忆存档 t1-v1134-realmachine-closure-night；留守件健康（static_watch 循环快照中+VINS 51Hz）。

### A5 本夜坑账（九条，客观登记）
①批脚本 grep 错文件（drill stdout vs ev/px4ctrl.log）→summary 列全零型假象；②批轮 ev= 时间戳与实际目录差 1s×2 例；③.gitignore 吃 test/ 第四次复发（git add 整体失败→force-add 例行动作）；④P3 埋雷形态=.h public 段前插 private: 块埋掉原 public 成员（报错远在调用点）；⑤mavparam 子命令=get 非 fetch；⑥热杀 rs 进程→IR/depth 硬件启动失败（USB 设备态卡死；sysfs authorized 重置救 IR 救不了 depth Asic）；⑦多层引号转义灾难（\$c/\$d 被 eat；Write+scp 即愈——禁远端 heredoc 教训再验证）；⑧STATUS 硬编码时间戳超前（中段时刻感知漂移，夜报已按 date 实测勘误）；⑨pgrep -f 自匹配两现（查询串必避自身路径）。

---

## B. 剩余单元（下一执行面）

- **B1 HAFIX 缺陷处置**：呈报件 P-HAFIX-1/2/3（verdict 报告 §四）待用户批复；批复前栈代码零擅动（判据/门值零变动纪律）；批复后=修复+20 轮量级多场景复验批（占 3090 飞行窗，与 T2 互杀铁律串行）。
- **B2 实机批剩余场景**：微动注入对照（2d②对照臂）/桌面平移/手持缓动/手持走动——全挂物理窗（C-3）。
- **B3 depth→planner 贯通**：depth 断电复位（C-2）→depth 流复活验证→planner 实机 launch 适配稿落码（depth 话题+内参，C-5）→贯通面补进质量报告 v2。
- **B4 物理窗四项（2c）+2e 地面版**：磁力计重校[P1]/固件版本 QGC 直读/不装桨怠速/急停拨测+电池压测；2e 不装桨怠速态杀 VINS/毒 odom 注入观察 HAFIX 梯+监控告警链（清单 v1 在 3090 v11_28/local_staging/04_safety_chain/PHYSICAL_WINDOW_CHECKLIST_v1.md）。
- **B5 首飞 go/no-go 呈报**：M1 行 3/行 5 收口后触发（依赖 B1-B4）。
- **B6 池件（无阻塞可动面）**：①第三周期静态数据消费（留守循环自动累积；**注记：04:44-04:48 rs 重启窗=数据断段污染，之后为新段**）；②监控 v1.2 候选三注记（D 检测器阈值口径/phase 横跳/收尾退出时序）——均为登记注记非阻塞；③p1 五件动态栈基准补测（planner 件修复后可选，四件栈勘误已注记在案）；④低优例行修：drill 脚本 ev 差一秒目录名生成 bug+.gitignore test 条目根除。

---

## C. 卡点（客观描述——只述事实/证据/依赖，方案归批复件）

- **C-1 HAFIX KILL 链缺陷（阻 M1 行 5 收口）**：源码 PX4CtrlFSM.cpp L138-152 三项事实——①kill_srv.command=400 但 param1 未设（缺省 0，MAV_CMD 400 param1=0 语义=**重启自驾仪**而非终止飞行）；②ROS_ERROR"[HAFIX]...KILL+disarm fallback"行打在两个服务调用**之前**，call 返回值不检查（5 轮"打了 KILL 行但机体保持悬停 armed=True、真值 z 冻结 0.91-1.44m 至 bag 末"=请求未生效的直接观测）；③空中 disarm 请求被 PX4 拒（全部 KILL 轮 armed 恒 True；4 个 PASS 轮 disarm 亦未生效，唯一 armed 1→0 跳变在 S4r4@96.0s=FC AUTO_DISARM 参数路径非 HAFIX）。连带事实：FC reboot 副作用使 px4 SITL 进程残留→紧邻下轮"SITL 未清(px4=1 gz=1)"FATAL——6 FATAL 中 5 对名对映射紧跟 KILL 结尾轮+1 例相邻（214206→214621，形态=双目话题未出现）。**影响**：多场景判据 FAIL（4/20）；v11.28 D1 单轮复验（落地 z=0.10）属生效路径偶然侧，代表性被证伪。**依赖**：修复须动 px4ctrl 栈代码=须用户批复（P-HAFIX-1/2/3 呈报件）；复验批须 3090 飞行窗。
- **C-2 rs depth Asic 硬件卡死（阻 M1 行 3 深度面+B3 贯通）**：时间线——04:44 热杀 rs 进程（修 depth_width 漏参）→第一次 relaunch 报 IR stream start failure（Hardware Error）+USB control_transfer Resource unavailable 刷屏→sysfs authorized 0/1 USB 设备级重置→第二次 relaunch IR 恢复（infra1/2 双流 30Hz，VINS 链无损）但 **Depth stream start failure, Hardware Error 持续**→depth 模组未复活。v11.31 同族事件（2c Asic ERROR）当时=**整机重启后消失**。**依赖**：解除手段只剩整机断电再上电=物理操作（物理窗）；远程手段已穷尽（进程级 kill/重置与 sysfs authorized 重置两法均试）。
- **C-3 物理窗缺席（最大面阻塞）**：手持缓动/手持走动（2b 主场景，任务书明示"必须人手持机体=用户在场"）/微动对照（2d②）/桌面平移（需人动桌面）/2c 四项/2e 地面版/depth 断电复位——全部依赖用户在场或物理操作；凌晨时段已按任务书降级条款执行静置域并如实注记。
- **C-4 电池未插**：mavros battery 全窗 0.0V（自检 v1 正确拒飞）；后续台架正式批需插电池（物理操作）或在报告中注记供电态。
- **C-5 planner 件两面**（阻 p1 基准补测+B3）：①launch 缺失=旧机 planner 包内无 single_run_in_exp.launch（正源考证：plan_manage/launch 全列+git ls-files+p1 日志 RLException 三证）→p1 基准负载面欠估计已成勘误注记；②适配未落=可复用 run_planner_sitl_vins.launch（odom 同 topic /vins_estimator/imu_propagate）但 depth 话题与内参适配需 depth 流活（阻于 C-2）方能验证。
- **C-6 CAL 侧注记项（归 P1 物理窗）**：ACC Y=-0.2583/Z=-0.0925 m/s² 偏大（≈2.6%/0.9% g，机理=E5P 评估 §2 corrected 流假加速度族）+mag XOFF=0（零校定嫌疑，v11.31 已登记）——远程无验证/标定手段，物理窗与磁力计重校同窗核对。
- **C-7 静置病理样本边界（客观注记非阻塞）**：两周期样本内结局=软重置×1+未发射×1；v11.31 观测的 cost 3.3e8 爆+Eigen 断言崩在本窗未复现——**结局分布未定**（样本 2）；cost 爆与崩的发生条件未知；微动对照臂缺（C-3）。留守循环持续累积中（含 C 节 B6①的断段污染注记）。
- **C-8 旧机磁盘**：df 86%（32G 可用）——高于 20G 红线但偏高，若后续录袋须先盘水位。
- **C-9 共享 git 树交错**：3090 catkin_ws 为四线共享树，本周期观察到本方 commit 被并线推送/推送区间含他线提交（属常态非事故）；逐件 add+提交前查 staged 列纪律维持。

---

## D. 资产（本周期新增可复用件）

- 3090 `t1_evidence/v11_34_2026-10-09/`：重判 CSV+HAFIX 终判报告（含 P-HAFIX-1/2/3 呈报件§四）+静态病理报告 v1.1+估计质量报告 v1+STATUS 夜报（含可做未做/坑账）。
- 旧机 `sitl_realmachine/09_reboot_stack_2026-10-09/`：vins_035850.log（51min T2diag/T2slv/T2gate 全量）+static_watch 快照循环（**留守中**，STOP 文件=~/sitl_realmachine/09_reboot_stack_2026-10-09/STOP_STATIC_WATCH）+双报告副本+复苏 boot 面六件 log。
- 工具（双端）：t1_rejudge_hafix_v1134.py / t1_hafix_landed_probe.py / t1_hafix_armed_probe2.py（bag 真值+armed 判读探针）/ t1_static_pathology_probe.py（病理段谱）/ t1_static_watch_loop.sh（留守循环）/ t1_preflight_check_v1.py（起飞前自检 v1）。
- 旧机 /etc/rc.local（OS 调优持久化，rc-local active）+ t1_preflight_check_v1 实弹 json。
- 记忆：t1-v1134-realmachine-closure-night（全账+坑账九条）。

## E. 等待登记

- **W-物理窗（用户在场）**：2c 四项（磁力计重校 P1/固件 QGC 直读/不装桨怠速/急停拨测+电池压测）+手持两场景+微动对照+桌面平移+2e 地面版+depth 断电复位。
- **W-HAFIX 修复批复（用户）**：P-HAFIX-1/2/3 呈报件（verdict 报告 §四）。
- **W-M1**：行 3（深度面，阻于 C-2）/行 5（多场景，阻于 C-1）收口后→首飞 go/no-go 呈报。
- **留守件**：static_watch 循环（旧机）持续快照——下任首件消费（含 rs 重启断段注记）。

## 保底清单（下一周期候选；主面全阻于物理窗/批复，可动面=池件）

①留守件消费（第三周期数据判读+STATUS 补行+循环处置）②HAFIX 若批复=修复+复验批首件（否则如实挂起）③物理窗若开=四项+场景批+B3 优先（否则如实挂起）④池件推进（监控 v1.2 三注记落码/p1 五件栈补测前置件/ev 差一秒+.gitignore 根除两例行修）⑤诚实夜报+M1 状态行。**双必达候选：留守件消费完毕 ∧（批复件处置或池件其一有果）——物理窗不开且无批复时如实记为外因等待，不算未达。**

## 附：M1 门检查单 11 行现状（正源=3090 v11_28/local_staging/M1_GATE_CHECKLIST.md v11.34 更新段）

| # | 行 | 状态 | 残项依赖 |
|---|---|---|---|
| 1 | 台架环境+全栈基准 | PASS（四件栈勘误注记） | 五件栈补测可选（C-5） |
| 2 | 实机 config+审签 | PASS 带注记 A/B | — |
| 3 | 硬件矩阵+物理窗 | **半成**（相机 3/3+飞控参数面 5/9；深度面阻） | C-2（depth 复活）+物理窗行项 |
| 4 | 演练五案+实机地面版 | PASS（D5 L2 链路级） | 2e 地面版=物理窗顺带件（注记） |
| 5 | HAFIX 多场景+复标 | **半成（FAIL 侧）**：复标 ✓；多场景 3d FINAL FAIL | C-1（批复+修复+复验批） |
| 6 | 基线=旧机 | PASS | — |
| 7 | OS 调优 | PASS（持久化件闭合） | — |
| 8 | failsafe 残件+P3 | PASS（P3 build+gtest 5/5+消费侧验证） | G-1 低优先注记收尾（C-6 同窗） |
| 9 | 自检脚本 v1 | PASS（实弹验证） | — |
| 10 | 处置手册 | PASS（参数适配 ✓） | — |
| 11 | 止损实机语义 | PASS | — |
