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
