# 工程任务书 v1.6 夜报——第二十一周期收官（2026-10-11；T1+T2+T3 合并册单线执行）

> 执行域=3090（ssh nuc2j）+旧机 NUC（ssh nuc）。
> 开工 18:21 / 收工 22:4x；会话全程在场（L2 探针窗轮询值守）。
> 双必达达成判定：**C-1 分离验证轮+终局判决 ✓** ∧ **（内存 L2 归属判决 ✓ + δ 首应用批执行含录制作业验证 ✓）= 双必达 ✓✓**。

## 0. 开工网络事故与通路恢复（对账）

- 事故：本机 WLAN 无线电"硬件开/软件关"（win32 软开关态，netsh 需管理员无法本地恢复）→ 192.168.0.x 双机直连全失联。
- 恢复：Tailscale（uav4 active DERP hkg）→ 旧机 LAN → 3090 免密（旧机→3090 BatchMode 实证可用）三跳；
  本机 ssh config 增 ProxyJump 别名 nuc2j，全程经跳板执行，零功能损失。
- 注记：WLAN 无线电开关需用户物理/提权恢复（非本会话可解）；跳板通路已常态化备份（月报 41 条）。

## 1. 单元 0 开工收件+旧机巡检 ✓

- git pull main 已最新（370ad16）；残场清理（E8PL2C 孤儿 stoploss_watch + 3 空 side-lock）；catkin build 绿（1.2s 零失败）。
- 旧机在役五件全活（roscore/mavros/vins_to_mavros/ego_planner+traj_server/px4ctrl+watch2+kill_watch）；
  odom 14.97Hz + imu_prop 50.0Hz；df 29G>20G 线。
- **统一模型第四数据点=2.09GB/h**（15:16 fresh 62.9MB→18:23 6627.6MB，3.13h；模型标称 2.18GB/h×健康占比≈1 带内）。
- **5h 窗到窗处置（20:15）**：旧 VINS 终态 10.25GB@20:16（全窗 5h，尾段速率 ~1.9GB/h 与第四点一致）→ 重启
  （新 PID 2392357@20:18:38，watch2 RESTART 行 20:18:39 在案，odom ~15Hz 恢复）。首射失败一例
  （非交互 ssh 缺 LD_LIBRARY_PATH→libxmlrpcpp.so 载入失败；DEAD 行如实记录，带 env 重发成功）。

## 2. 单元 1 C-1 重编译候选分离——**第三发现定案+当周期修复+双正控**（头号件超纲收口）✓

### 2.1 取证构建 F1

- 补丁 8 打点（t1_c1_forensic_patch.py：loop 全字段/armdis 出入口/disarm 入口+写后回读/arm 入口/ack/发布心跳，
  纯打印零功能改动，锚点不唯一即中止守卫）→ 重编译绿（11/11 零错误）→
  **新构建指纹 px4 md5=0bac7286cf38075f8880880b1eb9c9d2**（git HEAD 仍 d6f12ad1c4，补丁未提交=构建差异如实登记；
  二进制 11 处 C1FR 印记）。
- 回归轮 run_C1re_183315 **PASS**（正常 arm/disarm 链全对+取证面六面全活 535 行；枚举映射勘定 DENIED=-1/NOT_CHANGED=0/CHANGED=1）。

### 2.2 分离判决（run_C1se_184008，判据轮前预注册）

- 复现形态成立（4×179 全 ACK0+注入窗 arming 零翻转+悬停稳，五元组与 v1/08_24_40 同构）。
- **候选①（uORB 拷贝异常）否证**：[loop] 面 4×179 参数逐位完好（p1=0/p2=21196/src=1/240，零 generation lost 零 COPY-FAILED）。
- **候选②（Commander 线程窗）否证**：[armdis] 面零进入——ARM_DISARM case 从未执行，无窗可言。
- **真因=第三发现：MAVCmd 号错位**——179=DO_SET_HOME（非 ARM_DISARM）、400=ARM_DISARM、185=FLIGHTTERMINATION；
  注入命令被 SET_HOME case 正确接受并执行（设 HOME 到(0,0,0)）→ **固件行为全程正确，"ACK 假确认断链"不存在**。
- 途中险情与兜底：控制台行宽截断伪影（src=1/240 显示为 src=1/2）一度指向"component2 改写"假说——ulog 全字段
  双源核对+ACK target 反推勘误（月报 35 条）。
- 根因坐位：px4ctrl fsm_decision.h 常量（注释自称 179=ARM_DISARM=错号起源；400+p1=1.0=ARM 空转）；
  v1139"termination 被 failsafe 覆写"勘误为幻影。

### 2.3 处置条款执行（终局制：≤1 人日 → 当周期落码+回归+验证轮）

- 修复（commit **89dc2a1**）：HAFIX_KILL_MAVCMD 400→185 + HAFIX_KILL2_MAVCMD 179→400 + 注释/日志/gtest 同步；
  catkin 绿 + test_fsm_decision **51/51**。
- **正控轮 ×2 双 PASS**：
  - disarm（run_C1v3_disarm_185451）：悬停单发 400(0,21196) → 45/45 armed False（在线）+ ulog arming 2→1 翻转
    t=45.252 + C1FR 链 armdis-enter-forced1→WROTE-DISARMED→res=1(CHANGED)→ack0——**该构建 MAVLink forced disarm 完全可用**。
  - term（run_C1v3_term_*）：185(1.0) → ACK0 + nav_state 14→13(TERMINATION)（pub 心跳+ulog 双面）+ armed 语义正确保持；
    终止后 simulator poll timeout=坠落副产物注记。
- 旧机部署（20:08）：pull 89dc2a1 + catkin build px4ctrl 绿 + 二进制串验证（cmd185 在/cmd179 绝迹）+ px4ctrl 节点重启 remap 同原。
- 判决书：c1_separation_final_verdict.md（f7c87ae5）；v1140 定位文书加终局指针（错号起源文献面标定）。

## 3. 单元 3 δ 政策 A 首应用批 ✓（机制全验证；KEPT 面无绿轮样本如实注记）

- 批=N8P 8 轮（任务书 4+短尾全清扩展 4，批跑器增 R_START 参数）：**0/8 全 FAIL**（轮 4 物理到位 0.105m 被
  VINS 跳 1.783m 判负=彩票正型；轮 8 njf=31 风暴；j0d 滚入 8/8 available=true）。
- 绿率对照：M3' N8P base 3/3（前时代）→ M3 0/3（10-08）→ 本批 0/8 → **近期实飞 0/11 彩票冷期**（A1 observe
  结构性不收敛注记互证）。
- **δA 机制四件 8/8 全验**：配额门（8×img=on）/录制作业验证（8/8 ALIGNED：左右目 7.5-7.7k 帧、count_delta=0、
  首末时戳差 0.0ms）/非绿裁决（8×DISCARDED 删图像袋保主袋）/j0d 滚入。**KEPT 面未触发（0 绿轮）**——代码路径
  已由此前干测覆盖，现场触发留待自然绿轮（定性注记，非待办）。
- 图像袋规格勘误：实测 13-14G/袋（设计注释 1-3G 为 drill 短窗低估）；盘门 23G 单袋制有效。
- 判决书：delta_a_verdict.md（536fea47）。

## 4. 单元 4 三注记定案档案化 ✓

unit4_notes_archive_v116.md（bb161a2e）：tlock 梯度（复审=实机真温漂）/A1 observe（复审=绿率结构变化）/
B3（复审=用户明示解冻 nuc3）——三态归属=定案注记，清账合规。

## 5. 单元 2 内存泄漏 L2 符号级取证 ✓（三事故翻案+自研探针定桩；判决 469e75f2）

- **执行链三折**：heaptrack 包 rosrun=4K 空文件（LD_PRELOAD 被剥离）→ 直包二进制=符号管线通但 **loop 长窗一律 init 后停摆**（baretest 对照定案=heaptrack 插桩本身所致）→ **自研 t1_mtrace.so v4 轻探针**（`__libc_*` 直连+fopen 重入守卫；≥8KB 分配记 4 帧+free 配对+60s 汇总；探针四坑入月报 37/38）+bag --loop SIGBUS 随机死亡由包装器自动重启（13 实例累计 21-23k track 行/实例=裸速零扰动）。
- **速率**：回放域探针实测 **0.95GB/h**（7 实例 1620s 合并，0.85-1.11 带）——与实机 2.09GB/h（第四数据点）同量级=**VINS 进程内在行为**，L1 段级结论获符号级确认。
- **符号级归属（双证据面交叉）**：gdb 条件断点 20 全帧+探针 13 实例配对时序——
  链 A（10512B 高频线性不还，live 573→1406/120s 不封顶）=**Estimator::processImage estimator.cpp:666 + slideWindow estimator.cpp:2188**；
  链 B（11488-12192B 每轮求解）=**ceres::BlockJacobianWriter::CreateJacobian ← Estimator::optimization:1736**；
  次级滞留=vins_node 图像 buffer 900KB 族+libopencv 156KB 族。40KB/帧量子构成定案。
- **处置出口**：修复面跨 VINS/Ceres/OpenCV 三层复合生命周期工程（多日量级）→ **归升级路线图 W12 冻结域**（禁悬挂）；当周期核心增量已做=判决+速率模型+工具资产（探针/聚合器/gdb 条件断点法，W12 直接复用）。
- 判决书：memleak_l2_verdict.md（469e75f2）。

## 6. 单元 5 收尾件

- 月报廿一周期 8 条并入（120→128，c96e573b）+A4 复发2 标注；STATUS 全程通告 12+ 行；收工镜像随 commit。
- git：89dc2a1（C-1 修复+工具族）→ 988014d（单元 3/4 证据+月报+工具修）→ [[收工 commit]]。
- STATUS 收工镜像随收工 commit；T4 收货通告（C-1 轮 ulg×5+δ 批 compact 袋×8+L2 判决+本夜报）已入 STATUS 等待登记。

## 7. 《可做而未做清单》+四态对账（终局对账——本册一切件三态之一，禁第四态）

| 件 | 终态 | 凭据 |
|---|---|---|
| C-1 重编译+分离轮+终局判决+处置出口 | **完成** | 89dc2a1+f7c87ae5+双正控轮+旧机部署 |
| 内存 L2 执行+归属判决+处置出口 | **完成**（修复归冻结域 W12） | 469e75f2 |
| δ 首应用批+录制作业验证 | **完成**（机制面；KEPT 无样本如实注记）| 536fea47 |
| 旧机巡检+统一模型第四数据点+5h 窗处置 | **完成** | watch2 csv+STATUS 20:17-20:19 |
| 三注记定案档案化 | **完成** | bb161a2e |
| STATUS 诚实夜报+四态对账清单 | **完成** | 本件+收工镜像 |
| W∈{5,20} tlock 梯度轮 | **定案注记**（归档 N-1） | unit4_notes_archive |
| A1 observe 证据面 | **定案注记**（归档 N-2） | 同上 |
| B3 筛选统计章 | **定案注记**（归档 N-3，冻结域） | 同上 |
| δA-KEPT 面现场触发 | **定案注记**（无绿轮样本，机制+干测在册） | delta_a_verdict §2 |
| 升级路线图方向件（M0 后置+内存修复 W12） | **归冻结域**（用户裁定①+L2 处置出口） | 任务书头注+本件 §5 |
| E8P 层 2 场景原生风暴 | **归冻结域**（T2 渲染域跨域件维持归属注记） | v112 册 |

### 可做而未做（诚实清单）

1. δA KEPT 面现场触发（无绿轮样本；等自然绿轮，机制在册非待办）。
2. C-1 判决书遗留小项：term 轮 ulog arming 翻转缺失注记（termination 语义正确，不影响判决）。
3. L2 深挖余量：三家族中 opencv 156KB 族内部函数定位（opencv 无调试包，归 W12 域随修复工程做）。
4. 月报 43 条候选：探针 v4 四坑已并入 37/38/40/42，无散件。

## 8. 全库清零对账表（收官周期）

- **完成**：本册单元 0-5 全链（含超纲：C-1 根因修复+旧机部署+heaptrack 事故翻案+自研探针体系）。
- **定案注记**：三注记（N-1/2/3）+ δA-KEPT 无样本注记。
- **归冻结域**：升级路线图（M0 后置+内存修复 W12=E8P 层 2 亦在其域）；nuc3 相关。
- **等待面**：W-T4 收货回执（C-1 轮 ulg×5+δ 批 compact 袋×8+L2 判决+月报 128 条——STATUS 通告在案，T4 下会话收）。
- 动力套事项（用户域）本册无涉；**周期任务书下发环节退役**（收官周期声明生效）。

## 9. 坑账（本周期 8 条入月报 35-42+A4 复发2；详见月报廿一周期节）

行宽截断伪影（判决级险情）/MAVCmd 注释错号根案/heaptrack-rosrun LD_PRELOAD 剥离/heaptrack 1.1 三面差/
setsid 掩重定向失败/bag-loop 时戳回归 SIGBUS/win32 WLAN 软关+跳板/ssh 吞 python heredoc。

## 10. 旧机终态

VINS fresh 2392357@20:18:38（5h 窗制）+ px4ctrl 修复版（kill 号勘定 185/400 已在役）+ 五件流率健（odom~15Hz）
+ watch2 连续采集中 + df 29G。下次到窗=~01:18（无人值守由 watch2 记 DEAD/RESTART 如实）。

## 11. 双必达终判

**C-1 分离验证轮+终局判决 ✓**（run_C1se_184008 分离+第三发现+修复 89dc2a1+双正控+判决 f7c87ae5）
∧ **（内存 L2 归属判决 ✓[469e75f2]+δ 首应用批执行[含录制作业验证] ✓[536fea47]）= 双必达 ✓✓**。
穷尽面：短尾全清制执行（δ 批 4→8 轮、C-1 修复当周期落码+双正控+旧机部署、L2 三事故翻案到自研探针定桩）；
四态对账表零第四态。收官周期收工。
