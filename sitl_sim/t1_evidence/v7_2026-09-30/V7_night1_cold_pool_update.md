# T1 v7 夜 1 悬案池更新总账（2026-09-30，对任务书悬案池全表）

| 悬案（任务书 §悬案池） | 夜 1 后状态 | 归属更新 | 证据 |
|---|---|---|---|
| W2 五场景全败=EKF2-EV 控制失稳@223Hz | **改写**：EV 融合从未启用（EV_CTRL=0 全历史）——层 1=VINS 发散（ATE 数字主源，归 T2-W-A）+层 2=PX4 位置环@223Hz 体制物理失控（z 超调 1.8-8.0m，OFFBOARD 链，EV/px4ctrl/VINS 均不在环） | T1-E1（重定义后）+T2-W-A（层 1） | E1_E1_threeway_archaeology_verdict.md |
| EV 供给密度因子分离 | **对象不存在**（EV 未融）——顺延至 EV_CTRL=15 启用后 | T2-A3 挂起 | 同上 §5 |
| 场景条件性发散 | 层 1 归属加固（W2 五轮 ATE 主源=obstacles VINS 发散） | T2 v4.3 W-A 主线（不变） | 同上 §4 |
| 47s 型大重锚部分补偿 | **H0 证伪+零捕获新事实**：smoother 对 47s 型事件零捕获（dP 与 legacy 逐位一致），事件走 ULS 捕获点外写点；dt_ms=8ms=ULS 覆写类，gap 类死 | T1-E2（进行中） | E2_H0H3_verdict.md |
| 病链传播加速度偏差 3-11 m²/s（→m/s²） | H3 证伪（非间隙机制）——独立留 T2-W-A 账 | T2-W-A | 同上 §2.2 |
| 外部 SIGTERM 之谜 | **三候选削弱，同名注册杀升头号**（单点杀实锤+vins_to_mavros 存活 4min+二次 roslaunch 追加痕迹）；设伏已部署（vins_kill_watch） | T1-F4（进行中） | F4_sigterm_interim_verdict.md |
| TCPROS 新建 pub 建连 ~50%（U3，M1 勘误 71.4%） | 复现器建成；双臂（私有/共享 master）各 50 轮**零失败**——失败条件不在基础链与 master 共享性；续臂（px4ctrl 本体/大消息/满栈）待做 | T1-G1（进行中） | G1_repro_two_arms.md |
| 慢连退化（boot 累积） | 快照器坏产物（nodes_dead 从未入账）+EXP-1 分配器连号（复活向待 E 实测） | T1-G2（未变） | G2_EXP0_EXP1_results.md |
| /mavros/imu/data 速率@4000us | 未测（原骑 E3 窗，未跑） | T1-G3 挂账 | — |
| px4ctrl"SITL 重启后静默卡死" | 未动（F6 清点另夜） | T1-F6 挂账 | — |
| VINS 慢漂 0.468m/3min | 未动（E4 依赖 E3 袋） | T1-E4 挂账 | — |
| **新增**：fpv yaml use_px4_position_ctrl=true 的实机架构含义 | 三路取证完成，天平倾向分支 A（PX4 侧位置环），**待用户拍板**；SITL(false)≠实机(true) 架构不同构=R6 必登项 | T1-F2+用户 | F2_conflict1_branch_verdict.md |
| **新增**：V1.3"EKF2 带视觉融合 0.087m"叙事勘误 | EV_CTRL=0 全历史 ⟹ 0.087=GPS+baro+DR 输出（非 EV 融合质量）——V1_RESULTS/记忆待勘误登记 | T1（文档勘误） | E1_E1 §3 |
| **新增**：px4ctrl FSM.cpp:303 导入源私改（迁移条件+armed/低速保持） | F1 发现，行为语义与上游不同（未 arm/降落低速期状态保持）——对 SITL/实机行为的影响未评估 | T1-F3（FSM 审计时并入） | F1_upstream_diff_ledger.md |
