# 工程任务书 v1.6 完成清账版（2026-10-11；第二十一周期收官；T1+T2+T3 合并册）

> 本件=v1.6 执行版（plans/2026-10-11_工程合并_v1.6.md）的完成清账改写；v1.6 执行版弃读存史。
> 执行会话=2026-10-11 18:21-22:4x（单线 T1ENG）；**双必达 ✓✓**；git 89dc2a1→988014d→897e4a4→8d8a224 全推（UAV_NUC main）。
> 依据终局形态声明：**本周期收工即软件侧清零态，周期任务书下发环节退役**——本件是本项目最后一份周期清账册；后续工作组织形式=用户指令驱动或专项册（不受周期制约束）。

## A. 完成账（按单元，全部可核验）

### 单元 0 开工收件+旧机巡检 ✓
- git pull main 已最新（开工基线 370ad16）；残场清理（E8PL2C 孤儿 stoploss_watch+3 空 side-lock）；catkin build 绿。
- 旧机在役巡检：五件全活（roscore/mavros/vins_to_mavros/ego_planner+traj_server/px4ctrl+watch2/kill_watch）；odom 14.97Hz+imu_prop 50.0Hz；df 29G>20G 线。
- **统一模型第四数据点=2.09GB/h**（15:16 fresh 62.9MB→18:23 6627.6MB/3.13h）。
- 5h 窗到窗处置：旧 VINS 终态 10.25GB@20:16（尾段速率 ~1.9GB/h 同带）→重启 2392357@20:18:38；watch2 RESTART 行 20:18:39 在案；odom 恢复 ~15Hz。

### 单元 1 C-1 重编译候选分离 ✓（头号件，超纲收口：分离+根因+修复+双正控+部署）
- 取证构建 F1：Commander.cpp 8 打点（loop 全字段/armdis 出入口/disarm 入口+写后回读/arm 入口/ack/发布心跳；纯打印零功能改动，锚点不唯一即中止守卫）；重编译绿（11/11）；**新指纹 px4 md5=0bac7286cf38075f8880880b1eb9c9d2**（git HEAD 仍 d6f12ad1c4，补丁未提交=构建差异如实登记）。
- 回归轮 run_C1re_183315 PASS（正常 arm/disarm 链全对+取证面六面全活 535 行）。
- 分离轮 run_C1se_184008：复现形态成立（4×179 全 ACK0+注入窗 arming 零翻转+悬停稳）∧ **候选①否证**（[loop] 面参数逐位完好 p1=0/p2=21196/src=1/240，零 generation lost）∧ **候选②否证**（[armdis] 面零进入）。
- **第三发现定案：179=MAV_CMD_DO_SET_HOME（非 ARM_DISARM；400=ARM_DISARM，185=FLIGHTTERMINATION）**——注入命令被 SET_HOME case 正确执行（设 HOME 到 (0,0,0)）→ 固件行为全程正确，"ACK 假确认断链"不存在。
- 根因坐位：px4ctrl fsm_decision.h L212-216 常量错号（注释自称 179=ARM_DISARM=错号起源；400+p1=1.0=已解锁下 ARM 空转）。v1139 册"termination 被 failsafe 覆写"勘误为幻影。
- 修复（commit 89dc2a1）：HAFIX_KILL_MAVCMD 400→185 + HAFIX_KILL2_MAVCMD 179→400 + 注释/日志/gtest 同步；catkin 绿+test_fsm_decision **51/51**。
- **双正控轮 PASS**：disarm 轮 run_C1v3_disarm_185451（悬停单发 400(0,21196)→45/45 armed False+ulog arming 2→1 翻转 t=45.252+C1FR 全链 WROTE-DISARMED 现身）=**该构建 MAVLink forced disarm 完全可用**；term 轮 run_C1v3_term_*（185(1.0)→ACK0+nav_state 14→13 TERMINATION pub+ulog 双面）。
- 旧机部署：pull+catkin build px4ctrl 绿+二进制串验证（cmd185 在/cmd179 绝迹）+px4ctrl 节点 20:08:58 重启 remap 同原。
- 判决书 c1_separation_final_verdict.md（f7c87ae5）+v1140 定位文书终局指针（错号起源文献面标定）。

### 单元 2 内存泄漏 L2 符号级取证 ✓（三事故翻案+自研探针定桩）
- 路线三折：①heaptrack 包 rosrun=4K 空文件（LD_PRELOAD 被 ROS 工具链剥离）；②heaptrack 直包二进制=符号管线通（supp 137s 单遍，trackImage:190 全栈行号）但 **loop 长窗一律 init 后停摆**（baretest 对照：裸 VINS 200s 处理 20236 行+RSS 实涨→停摆=heaptrack 插桩本身所致）；③**自研 t1_mtrace.so v4**（`__libc_*` 直连+fopen 重入守卫+≥8KB 分配 4 帧回溯+free 配对+60s still-live 按 caller 汇总；四坑迭代：dlsym 启动段错误/__thread TLS 段错误/fopen 递归爆栈/pgrep 匹配包装进程）。
- 探针窗 55min/13 实例（bag --loop SIGBUS 随机死亡由包装器自动重启；每实例 21-23k track 行=裸速零扰动）+maps 快照循环+gdb 条件断点 20 全帧（operator new if $rdi∈(9.5k,13.5k)）。
- **判决（memleak_l2_verdict.md，469e75f2）**：回放域泄漏率 **0.95GB/h**（7 实例 1620s 合并，0.85-1.11 带；实机 2.09GB/h 第四点同量级=VINS 进程内在行为，L1 段级结论获符号级确认）。
- **行号级归属（双证据面交叉）**：链A（10512B 高频线性不还，live 573→1406/120s 不封顶）=Estimator::processImage **estimator.cpp:666**+slideWindow **estimator.cpp:2188**；链B（11488-12192B 每轮求解）=**ceres::BlockJacobianWriter::CreateJacobian**←Estimator::optimization **estimator.cpp:1736**；次级滞留=vins_node 图像 buffer 900KB 族+libopencv 156KB 族。
- 处置出口（终局制）：修复面跨 VINS/Ceres/OpenCV 三层复合生命周期工程（多日量级）→**归升级路线图 W12 冻结域**；当周期核心增量已做=判决+速率模型+工具资产（探针/聚合器/gdb 条件断点法，W12 直接复用）。

### 单元 3 δ 政策 A 首应用批 ✓（机制面全验证；KEPT 无样本如实注记）
- 批=N8P 8 轮（任务书 4+短尾全清扩展 4，批跑器增 R_START 起始轮号参数）：**0/8 全 FAIL**（j0d 分型 transit 主导 6/8+mixed 2/8+轮 8 njf=31 风暴；轮 4 物理到位 0.105m 被 VINS 跳 1.783m 判负=彩票正型）。
- 绿率对照：M3' N8P base 3/3（前时代）→M3 0/3→本批 0/8→**近期实飞 0/11 彩票冷期**（A1 observe 结构性不收敛注记互证）。
- **δA 机制四件 8/8 全验**：配额门（8×img=on）/录制作业验证（8/8 ALIGNED：左右目 7.5-7.7k 帧、count_delta=0、首末时戳差 0.0ms）/非绿裁决（8×DISCARDED 删图像袋保主袋）/j0d 滚入 8/8。**KEPT 面未触发（0 绿轮）**——代码路径已由此前干测覆盖，现场触发留待自然绿轮（定性注记）。
- 图像袋规格勘误：实测 13-14G/袋（设计注释 1-3G 为 drill 短窗低估）。判决书 delta_a_verdict.md（536fea47）。

### 单元 4 旧注记清账 ✓
unit4_notes_archive_v116.md（bb161a2e）：tlock 梯度（复审条件=实机真温漂场景）/A1 observe（复审条件=格子绿率结构变化）/B3（复审条件=用户明示解冻 nuc3）——三态归属=定案注记，清账合规。

### 单元 5 收尾 ✓
- 月报廿一周期 8 条并入（35-42：控制台行宽截断伪影/MAVCmd 注释错号根案/heaptrack-rosrun LD_PRELOAD 剥离/heaptrack 1.1 三面差/setsid 掩重定向失败/bag-loop 时戳回归 SIGBUS/win32 WLAN 软关+跳板/ssh 吞 python heredoc）+A4 复发2 标注=**120→128 条**（c96e573b）。
- 夜报 night_report_v116.md（07726c14）四态对账表零第四态；STATUS 全程 12+ 行通告+收工行；收工镜像随 commit（8d8a224）。
- 开工网络事故：本机 WLAN 无线电"硬件开/软件关"（win32 软开关，非管理员不可恢复）→全程 tailscale(uav4 DERP)→旧机 LAN→3090 跳板三链执行（ssh 别名 nuc2j=ProxyJump nuc-ts 已建为常态备份）。

## B. 剩余件（全部为定案注记性/等待性/冻结域，无第四态）

1. **W-T4 收货回执未到**（本册唯一等待面）：C-1 轮 ulg×5（regress/separate/disarm/term）+δ 批 compact 袋×8+L2 判决+月报 128 条——STATUS 通告在案，T4 下会话收。
2. δA KEPT 面现场触发：无绿轮样本（0/11 冷期），等自然绿轮；机制+干测在册非待办。
3. C-1 term 轮 ulog arming 无 2→1 翻转：termination 语义下 armed 保持为正确行为（正控判据 PASS 不依赖此项），仅作证据面注记。
4. L2 深挖余量：opencv 156KB 族内部函数定位（opencv 无调试符号包，函数级受阻）——归 W12 域随修复工程做。
5. 旧机下次 5h 窗 ~01:18 无人值守（watch2 将如实记 DEAD/RESTART；到窗重启由下任会话或用户执行）。
6. 3090 PX4 树状态：带未提交的 Commander 取证补丁（8 打点纯打印）——取证在役但与"干净构建"指纹断链在案。

## C. 卡点与阻塞（客观描述，不含解决方案）

1. **本机 WLAN 无线电软关未恢复**：Windows 无线电状态"硬件开/软件关"，恢复需管理员权限（netsh interface enable/wlan 无线电开关）或物理快捷键——当前会话无提权通道。现有通路= tailscale(DERP 中继，RTT ~200-500ms)→旧机→LAN→3090 三链，任一环故障即全断；tailscale 健康检查已报 derp20d 证书拦截告警。此为用户域操作项。
2. **内存泄漏未根治（冻结域）**：符号级归属已完成（estimator.cpp:666/2188/1736+Ceres CreateJacobian+OpenCV 三层），但修复=跨 VINS 源码/Ceres/OpenCV 的复合生命周期工程，量级多日；按用户裁定（升级路线图 M0 后置）冻结在 W12 域。现实后果：实机 VINS 每小时涨 ~2.1GB RSS，运维完全依赖 5h 窗重启制；到窗无人处置则进程最终 OOM（此前已有 6.6GB 级实例在案）。
3. **N8P 彩票格绿率冷期**：近期实飞 0/11（M3 0/3+本批 0/8），格子绿率受二项噪声支配（A1 注记在册）；δA KEPT 面、绿率类对照批在此样本带内无法产出正样本，绿轮到达时间不可预测。格切换可绕开但违背"选格收窄"预注册口径。
4. **回放域两约束（工具面）**：①bag --loop 时戳回归→Ceres NaN→SIGBUS，VINS 存活随机 180-360s——回放长窗必须自动重启包装，无法单实例连续 2h；②heaptrack 与 VINS 不兼容（init 后停摆，baretest 对照定案）——第三方 heap profiler 在 VINS 上不可用，符号级取证只能走自研探针（≥8KB 门槛以下小分配不可见，<8KB 部分只有 RSS 面无归属面）。
5. **opencv 库无调试符号包**：156KB 族只能归属到 libopencv_core+偏移（addr2line 给邻近导出符号=误导），函数级定位无工具面。
6. **取证构建 F1 与基线断链**：3090 PX4 树当前=基线 d6f12ad1c4+未提交取证补丁（8 打点）；任何后续重编都会携带取证打印。恢复"干净基线构建"的时点未定（取证轮已毕，但 SITL 域后续轮是否需要干净构建无裁定）。指纹断链已在判决书登记，不构成观测面污染（纯打印）。
7. **实机 kill 链物理验证空缺**：修复版 px4ctrl（185/400 号勘定）在 SITL 双正控 PASS+旧机进程已部署，但实机 FMU v6C/PX4 v1.17.0 路径的空中 forced disarm 未实测（需动力套/实飞窗=用户域；任务书红线"动力套相关事项用户域本册无涉"）。
8. **E8P 层 2 场景原生风暴（njf=270）**：归 T2 渲染时戳域（上周期归属），修复需 T2 域工作，本册无涉未动。

## D. 资产 md5 表（关键件）

| 件 | md5 | 位置 |
|---|---|---|
| C-1 终局判决书 | f7c87ae5 | 3090 t1_evidence/v113_2026-10-11/c1_separation/c1_separation_final_verdict.md |
| 内存 L2 归属判决 | 469e75f2 | 同上 memleak_l2/memleak_l2_verdict.md |
| δ 批判读判决 | 536fea47 | 同上 delta_a/delta_a_verdict.md |
| 三注记档案 | bb161a2e | 同上 unit4_notes_archive_v116.md |
| 夜报 v1.6 | 07726c14 | 同上 night_report_v116.md |
| 月报（128 条基线） | c96e573b | 3090 t4_evidence/pit_monthly_report_v526.md（repo 双同步） |
| 修复 commit | 89dc2a1 | px4ctrl fsm_decision.h/PX4CtrlFSM.cpp/test_fsm_decision.cpp |
| 取证构建指纹 | px4=0bac7286 | 各轮 EV/build_fingerprint.txt |
| 探针 v4 源 | t1_mtrace.c | repo sitl_sim/（+t1_mtrace.so 3090 ~/sitl_sim/） |
| 本地战役归档 | 24 件 | D:\drone_VINS\t1\2026-10-11_工程合并v1.6\ |

## E. 等待登记

- **W-T4 收货回执**（C-1 轮 ulg×5+δ 袋×8+L2 判决+月报 128）——本册唯一等待面，T4 下会话收。
- 用户域事项（无预排）：本机 WLAN 提权恢复；动力套窗（实机 kill 链验证/首飞窗三件）；升级路线图解冻时点；旧机 01:18 窗处置（无人值守则 watch2 如实记录）。

## F. 坑账（本周期 8 条入月报 35-42+A4 复发2；正文见月报廿一周期节）

控制台行宽截断伪影（判决级险情，ulog 双源兜住）/MAVCmd 注释错号根案（C-1 全案根因）/heaptrack-rosrun LD_PRELOAD 剥离/heaptrack 1.1 三面差/setsid 掩外层重定向失败/bag-loop 时戳回归 SIGBUS/win32 WLAN 软关+跳板/ssh 吞 python heredoc（A2A3 家族新机理：heredoc 整体未达远端）。

## 终局声明

本周期=收官周期，收工即软件侧清零态：全部在册件=完成/定案注记/归冻结域三态之一（夜报 §7/§8 对账表）。周期任务书下发环节自本件起退役；后续工作=用户指令驱动或专项册。动力套相关（用户域）无预排。
