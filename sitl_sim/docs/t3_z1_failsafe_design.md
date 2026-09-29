# T3 Z1.2/Z1.3:毒 odom 消费侧防护门 v2 设计与双轨验证(2026-09-30 夜)

依据:`plans/directions/C07_odom-poison-failsafe-paradigm/DOSSIER.md`(r3)执行;
外部盘点=C07 §2(40 条经验+7 项未找到空白区:GitHub 全站 px4ctrl failsafe 0 命中等,
不重复引,检索账在 C07);内部衔接=T1-D2 三层门(`odom_sanity.h`,WD1b 实战拒 200+ 帧)。

## 1. 现状与增量(读码六项=C07-E1,详见 docs/t3_z1_px4ctrl_replay.md §1)

D2 门(v1)=vel5/acc10/jump0.6 三层,feed() 内拒帧→冻结→既有 0.5s 停流降级链,**SITL 现役 enabled**。
v2 增量(本设计,`src/px4ctrl/src/odom_sanity_v2.h` **已入库未接线**,enabled_v2 默认 false=v1 逐位不变):

| 层 | 判据 | 阈值 | 依据 |
|---|---|---|---|
| STAMP-BACK | header.stamp 回退 | 严格单调 | 043355 实证 hdr 回退 16135 帧(双流污染签名);PX4 同构 C07-02 S17 |
| STAMP-AGE | 戳龄 t_now−stamp | 0.2s | 健康链路 max gap 20ms×10;外锚 EV_MAX_INTERVAL=0.2s(C07-02 S14);τ_age 数据源=在线双戳(v2 自带)——库袋无 rcv_stamp(C07 勘误④,Px4ctrlDebug 无双戳字段已实读) |
| ACC(沿用) | 帧间 dv/dt | 10 m/s² | v1 实战值;差分型→223Hz 噪声上界重标注挂 E7(C07-H12) |
| JUMP(沿用) | 帧间 \|dp\| | 0.6m | T1-D4 反哺值;**已知盲区:速度爬坡 223Hz 下 50m/s×4.5ms≈0.22m/帧(Z1.1 F2)** |
| **R(新)** | 运动学残差 ‖P_k−P_{k−1}−½(V_{k−1}+V_k)Δt‖ | **0.08m** | 健康当前层(imu_propagate,route_112652)p999=0.025×3 夹 C07 带[0.02,0.1];补 K4 缺口(v1 漏 0.5m 干净阶跃) |
| VEL(沿用) | \|v\| | 5 m/s | **速度爬坡形态唯一防线**(105449:r 中位 0/p99 1.15=协调漂移 r 盲实证) |

**标定账(`analysis/t3_r_scan.json`)**:当前层健康=route_112652 prop p50/p99/p999/max=0.00013/0.0124/0.0251/0.0398;
旧层对照=ground 0.0078/hover 0.027(max 0.235=31.3s 重锚族);换代证据=105449 发散轮 p99 1.146;
**回放域 CTRL2 vins_out 双发布者+r p999=1.01(撕裂)——回放 odom 流不可用于标定**(红线 7 r 域证据);
实机(odom 流@低 Hz)p999 0.26 量级(r_scan route odom)→实机阈值须另标,本 0.08 仅适用 223Hz 直供流。

## 2. 层序与动作链(层序=WD1b 实战次序)

STAMP-BACK→STAMP-AGE→ACC→JUMP→R→VEL(先值域连续层,后幅值层);拒帧→状态冻结(上一 ACCEPT 帧)
→**既有** 0.5s 停流降级链(v1 语义不变)。v2 不新增状态机(C07 方向 5:复用 rcv_stamp 冻结)。

**升级动作(设计登记,接线另议)**:Z1.1-F5 实证(104720:px4ctrl 冻结但 planner 同吃毒,des_pos 跑飞
→倾角 175.8°→GT 34.4m)——**门冻结语义对"上游同毒"不充分**。升级链=C07-B2/B3:
62 连拒(223Hz×0.28s;125Hz 原值 62 连拒=0.5s 语义按频换算)→锁存**锚点**(≠当前毒位)→AUTO_HOVER
在该锚点→LAND 分级;迟滞 2.5×+恢复试用期 ≥1s。姿态指令限幅(max_angle=25° 接线)与 thrust [0,1]
饱和属输出侧防线(C07 方向 4),与 D8/EKF2 消费方式联动(0.5 接线分叉,C01),**在 T1-E1 裁决后一并接线**。

## 3. gtest 注入矩阵(`test/test_odom_sanity_v2.cpp`,C07-E3 全档+方向 6 增补)

| 档 | 期望 | 层归 |
|---|---|---|
| 健康悬停 5000 帧 | 零误伤 | — |
| 慢漂 0.1m/s | 门内泄漏(√T 律;泄漏上界声明验收) | 全层不触发(登记) |
| 阶跃 0.5/2/10m 水平 | 全拦 | 0.5→R(v2 补 K4;v1 漏=复现);≥2→JUMP |
| 垂直 10m(负油门线域) | 拦 | JUMP |
| 速度爬坡 6.7m/s² 至 >5 | 拦 | **VEL(唯一防线实证)** |
| 平滑协调跳慢速 2m/s(<VEL 帽) | **全层门盲(H13,如实登记)** | 防线=慢漂泄漏上界/E6 漂移率门(后续) |
| 瞬时协调跳(2Δ/Δt−V 构造,r≡0) | 拦 | 首触=ACC(C07-P3 'VEL 检出'在 ACC 前置层序下归层 ACC,拦截等价,如实登记) |
| 陈旧突发(3s 前片段) | 首帧 STAMP-BACK→后续 STAMP-AGE;值完全健康 | STAMP 双层 |
| 时戳回退 −13s(043355 型) | 拦 | STAMP-BACK |
| 停流 0.5/3s 复流 | 零误伤(reboot_gap 跳连续性) | — |
| 占空比 90% 间歇毒 | 毒帧零摄入 | JUMP |

构建/运行:`catkin build px4ctrl --no-deps && catkin run_tests px4ctrl --no-deps`
(STATUS 已发 15min 异议窗预告;只增测试工件,节点二进制零改动;注意 catkin run_tests 吞 gtest
退出码的坑——以 test 结果文件为准,夜战工具链五坑)。

## 4. bag 验收轨(Z1.3,`analysis/t3_gate_sim.py`)

协议(C07-E4a):043355/105449 毒流(源袋 rosbag play --clock,私有 master 11315,真实 ROS 队列
100 深,harness 订阅 imu_propagate 直供流)×门全开(v1+v2);判读=剔双流后毒帧零入控制链
(AcCEPT 且 |v|>5 或 |p|>1e3 计漏入=0)+分层拒帧账+首拒时刻;对照=ground 健康袋零误伤
(E5 结果层判据:零拒帧)。**执行窗口**:避让 T2 W-A 回放(单机一路重回放红线;bag 轨不含
vins_node 但含一路 bag play IO,与 T2 回放错峰执行)。结果(跑后回填):见 §6。

## 5. 已知盲区与不解决项(如实账)

1. **协调慢漂/慢速协调位移 r+VEL 全盲**(2m/s 档 gtest 实证+105449 r 中位 0):防线=10s 窗漂移率门
   (C07 方向 7/E6,外锚 EKF2_REQ_HDRIFT=0.1m/s)——属泄漏上界声明范畴,非本 v2 范围。
2. 实机 odom 流(低 Hz)p999 量级不同→实机阈值另标(无实机袋,声明)。
3. 输入侧姿态门(q 盲区,C07-A3/D9):挂 E3 指令级符号表(P8a)与 E4b 植物级(P8b),不在 v2。
4. K1(failureDetection reboot 动作语义)移交 T2/W-A 评审(C07 修正一;动作语义非阈值)。

## 6. 双轨结果(执行后回填)

- gtest:待 build 窗执行(预告已发)。
- bag 轨:待 T2 回放间隙执行。
