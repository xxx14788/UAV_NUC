# R3 规划域证据包（T3 v8.3 单元 1）— U3′ route 双轮

> 取证人：T3 ｜ 2026-10-02 01:1x-01:2x ｜ 预注册判据冻结于执行前（脚本头注释，md5 352afaf6）
> 分工条款：本包只出规划域证据（ego_planner 行为/poscmd 质量）；VINS 域/消费域归因归 T2，禁代改。
> 素材：compact_U3PR1_212450.bag（309M 紧凑，poscmd 全量）+ t2v3_route_213717.bag（PR2 全袋 22G，无 poscmd）
> 工具：analysis/t3_r3_planner_domain.py（预注册：G1-G4 四门+签名三分类+漂移首漂档）

## 0. 摘要（结论行）

| 轮 | poscmd | 规划域签名 | 机体真值结局 | odom 漂移 |
|---|---|---|---|---|
| PR1 | 59105 条@100Hz | **sig-C 混合**：健康到达悬停段（68.4-78s）→ odom 爆漂后输出病态（G1/G2/G3 违，追漂框架+甩飞） | 80-86s 被甩飞三次砸地，趴于 (8.37,2.25) | 首漂 75.0s(>0.5m)，80-110s 急性冲 274m 后冻结 |
| PR2 | **0 条（全程缺席）** | **规划域缺席，G 门 N/A**——漂移由 VINS 域单独主导 | **全程未离地**（truth_z 恒 0.1） | 起飞后 3.3s 即爆（29.6s），10s 内虚构爬至 z=37m，冻结 54.55m |

**PR2 的"机体漂离 121.9m"系 odom 虚构漂移——机体物理上原地趴地全程**（truth_z=0.1 恒定，v_p95=0.023m/s）。@T2：到位指标与 ATE 的"机体漂离"表述对 PR2 建议改"odom 虚构漂移、机体未起飞"。

## 1. PR1 画像（compact_U3PR1_212450）

### 1.1 时间轴（bag 相对秒；起飞 26.44s）
- 26.4-54.3s：TAKEOFF 连发（1Hz×28）；30.0s armed=True
- 40-68s：悬停 0.72m，drift 0.15m（轻微）
- **68.4s**：goal1=(3,-2,1) 发出 → planner 开始 replan（traj_id 1 起，每 0.5s/条）
- **70.3s**：首个 vel_p50>0.55 段（id5=0.598；早期轻度超限段共 3-4 个，峰 0.632）
- **74-78s**：truth 稳于 (3.76..3.8, -0.8..-1.16, ~1.0) 距 goal1 最小 1.16m，pcmd_vm=0（到达悬停指令）——**规划域健康工作证据**
- **75.0s**：odom drift 首超 0.5m（急性爆漂启动）
- **80s**：drift 跳 2.17m；truth z 异常涨至 1.36，px4ctrl 依漂移 odom 剧烈修正
- **82s**：机体甩至 (2.71,2.63) 砸地 z=0.11（**无任何 land 指令，armed 保持=True=失控坠机**）
- 84s：弹回空中 (5.82,3.29,1.28)（pcmd_vm=0.729 仍在拽）→ 86s 再砸地 → 趴定 (8.37,2.25)
- **84.3s**：最后一条新轨迹（traj_id=33）；此后 traj_id=33 悬停指令持续 575.2s（traj_server 独立存活）
- **344.9s**：goal2=(0,0,1) 发出 → **无新轨迹响应（ego 主节点死/卡实锤）**
- 80-110s：odom 爆漂 2.2→44→136→274m 后冻结（趴地静止 IMU 无增量）
- 618.5-646s：LAND 连发（轮次收尾流程）

### 1.2 poscmd 质量四门（预注册，活跃段=段 vel_p50>0.05）
- 频率：100Hz p50，gap p95=12ms / max=32ms —— **稳定** ✓
- G1 限幅(|vel|>0.55 占比>5% 违)：活跃帧 41.76% 超限，8 个段 vel_p50>0.55（峰 0.738）→ **违**（其中 3-4 段为 70.3-72s 早期轻度超限 0.598-0.632，其余为 80s 后失控段）
- G2 goal 指向(cos<0.5 违)：cos p50=-0.953 / p10=-0.987 → **违**——poscmd 位置超前爆漂机体、速度沿"追漂移框架"方向背离 goal（min-jerk 轨迹起点随 replan 重置到漂移 odom）
- G3 前瞻(p95>5m 违)：活跃段 ahead p95=9.82m（全程含悬停段 p95=276.6m 系 odom 漂移所致）→ **违**
- G4 跳变(>1/min 违)：1 次/10min → 不违 ✓
- **sig_B_viol=True（G1+G2+G3）**——但病态窗与 odom 爆漂窗（75s 起）重叠，且 74-78s 存在健康到达悬停段 → 综合判 **sig-C 混合**：odom 爆漂（VINS 域病）驱动的追漂病态 + 早期轻度超限（规划域自身软限幅小病）

### 1.3 planner 进程面
- traj_server 与 ego_planner_node 分进程：84.3s 后 traj_id 冻结+新 goal 无反应 = **ego 主节点死亡/卡死，traj_server 独活**（与上游 issues #57/#85 exit -11 形态同族）
- console 证据灭失：t2v3_planner_route.log 零字节（午夜 truncate），死因无法定案——**登记，非本包可判**

## 2. PR2 画像（t2v3_route_213717 全袋）

### 2.1 时间轴
- 26.29s：TAKEOFF 指令
- **29.61s**：odom drift 首超 0.5m（起飞后 3.3s 即爆）
- 30-42s：odom 虚构爬升 (0.22,1.03?)→(15.4,42.1)，**truth 全程趴地 (1.14,1.12,0.1) 纹丝不动**——机体从未离地
- 44s：truth 被拖动一下 (-0.13,1.45,0.13)（px4ctrl 全舵修正拖动趴地机体；truth_vmax=4.26 即此）
- 60s 后：odom 冻结 54.55m 偏差至轮末；truth 趴地不动
- poscmd：**0 条**（录制清单含 /position_cmd 而袋中无该话题=发布者从未发布）；goal 97 条照发无消费者

### 2.2 规划域缺席的机理链（源码考证）
- traj_server 收首条 bspline 前不发布 poscmd（have_target_ 门）
- px4ctrl cmd 超时 0.5s（PX4CtrlFSM.cpp:579 is_cmd_timeout）→ 全程无 CMD_TRACK
- planner 未出首条轨迹的**原因**（未起/瞬死/规划全败）console 已 truncate，**无法定案，登记**
- 候选先例：上游 #57/#85 ego_planner_node exit -11；#129 规划失败循环（但该形态下 traj_server 亦无输出，与本轮一致）

## 3. 慢漂时间轴（五线对齐 T3 侧：poscmd/odom 两线）

| 事件 | PR1 | PR2 |
|---|---|---|
| odom 首漂(>0.5m) | 75.0s | 29.61s |
| poscmd 首迹 | 68.4s（先于漂移 6.6s） | 无 |
| poscmd 病态首迹 | 70.3s（轻度超限）/ 80s（全面病态） | 无 |
| 机体异常首迹 | 80s | 30s（微动）/44s（拖动） |
| planner 链死亡 | 84.3s（ego 主节点） | <30s（或从未活） |
| 机体终态 | 趴地 (8.37,2.25) | 趴地出生点旁 (-0.13,1.45) |

**T3 侧结论**：poscmd 首漂晚于 odom 首漂（PR1：poscmd 80s 全面病态 vs odom 75.0s 启动、80s 爆发）——**odom 漂移先行，poscmd 病态是下游**；PR2 规划域全程不在场，无时间轴可对。

## 4. 上游经验清单（研究优先件，单元 1.4）

检索面：ZJU-FAST-Lab/ego-planner + robin-shaun/XTDrone issues（2026-10-02 检索）。

| # | 案号 | 现象 | 与本案关系 |
|---|---|---|---|
| U1 | ego#85（XTDrone+VINS） | 机体初始位置与 odom 框架不一致 → ego 启动后机体猛冲回(0,0,0)附近、**速度明显超 max_vel** | 同族：odom 框架错位下 planner 输出超速指令；本案 PR1 G1 超限的机理参照（另：本案出生偏移 -1.0,-1.0 与 T2b-U9 出生点假象同源） |
| U2 | ego#106（实机 T265+D435i） | 毒 odom（漂移/坐标系错）→ "body's visualization moves much faster than actual system, follows weird trajectories, random directions" | 同族：PR1 80s 后 poscmd 追漂框架的"怪异轨迹+随机方向"上游实录 |
| U3 | ego#57/#85 | XTDrone+VINS 下 ego_planner_node **exit code -11 段错误**死、traj_server 存活 | PR1 84.3s ego 主节点死+traj_server 独活 575s 的先例形态 |
| U4 | ego#129 | terminal point in obstacle → skip planning、`last_progress_time_ ERROR` 循环 | 规划失败循环形态（bspline 不出→poscmd 不出）；PR2 全程无 poscmd 的候选解释之一 |
| U5 | XTDrone 侧 | 无"route 慢漂/planner 追漂移系"直接案例；vins 相关 issue 集中在建图/编译/坐标系 | 无上游直接判例，本案为新形态贡献 |

**上游共性结论**：ego-planner 对 odom 输入无健康检查（无漂移门/无一致性校验），odom 框架错位时输出表现为超速+怪异轨迹+追框架；planner 主进程死亡后 traj_server 会以最后轨迹持续发悬停指令（这正是 09-26 我们改掉 return 行为的同一段代码）。

## 5. @T2 对账点（合流判读以交叉点为准）

1. **数字对号**：PR1 odom_drift p95=274.05 ↔ T2 报 ATE_p95 274；PR2 54.55 ↔ 54.6。✓
2. **表述修正建议**：PR2"机体漂离"实为"机体未起飞、odom 虚构漂移"（truth_z 恒 0.1）；PR1"慢漂"实为"急性爆漂 30s 冲 274m"（80-110s）+冻结。R3 定因的漂移动力学请以本时间轴为准。
3. **交叉点归属**：px4ctrl 无 poscmd/依漂移 odom 的控制行为（甩飞/拖动）=消费域，归 T2；ego 主节点死亡原因=planner 域，console 灭失登记，若 T2 有进程级证据（roscore log/重启记录）请合流。
4. **failureDetection 零 fail 盲区**（T2 22:08 新机理）在两轮均成立：PR1 爆漂至 274m、PR2 虚构 42m 高全程无 fail——规划域侧无补充证据（planner 无自检面）。

## 6. 残余风险与注记

- 对齐口径=出生段平移对齐（一阶，慢漂主分量平移）；yaw 漂移未入 drift 口径（若 VINS 存在 yaw 漂移，drift 为下界）。
- PR1 truth_vmax=31.4m/s 为单帧尖峰（82-84s 甩飞窗），非持续速度。
- PR2 odom 在 44s 有一次跳变（-1.77,37.39←15.39,42.09）=VINS 帧跳变族。
- 本包不判 VINS 域根因（归属 T2-R3）；不判 px4ctrl 参数问题（消费域）。

## 数据文件
- ~/sitl_sim/t3_results/r3pr1_plannerdom_{summary.json,timeline.csv}
- ~/sitl_sim/t3_results/r3pr2_plannerdom_{summary.json,timeline.csv}
- 判读脚本：catkin_ws/sitl_sim/analysis/t3_r3_planner_domain.py（预注册于文件头）
