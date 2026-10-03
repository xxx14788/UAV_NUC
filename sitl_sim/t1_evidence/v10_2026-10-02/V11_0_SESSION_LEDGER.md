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

