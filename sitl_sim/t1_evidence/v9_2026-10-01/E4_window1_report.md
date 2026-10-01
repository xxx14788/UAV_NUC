# T1-E4 首窗战报（2026-10-01 19:29-19:55；设计 5dfecc8 §1-4 执行；R3 条款停跑）

## 窗场
- 入场依据：T2-R2 判别格 19:24/19:28 收口（判决=carrier_input_domain）→ T1 E-4 首窗入场（预告 18:38 异议窗零异议）。
- 计划：G-off×D10 → 回归 → G-on×D10 → 回归（4 飞设计最小集）。实际：2 试验轮全 FAIL，回归轮未飞，R3 停跑。

## 轮账（2 轮，run 目录 + ulog 均落盘）

### 轮 1 = run_E4_GOFF_D10_193039（EV_CTRL=15，GPS_CTRL=0，rcS 注入实证）
- rcS 注入回执：`param set EKF2_EV_CTRL 15 / EKF2_GPS_CTRL 0` 插在 ekf2 start（rcS:268）前；ulog initial_parameters 逐位核实（11_30_48.ulg）。
- **P0-A.2 破零：带探针在线 VINS 发散事件首次捕获**。探针出生时间线：t≤33.07s |dP| 全健康（1e-3~6e-3 基线级）→ t=33.176s |dP|=0.0290（5×基线）→ t=33.280s dP=[-0.0116,-0.0130,-0.1271]（z 主导负尖峰）→探针线止（213 行）。
- E2clamp=0 / E2gap=0：非掉帧/钳制族；正常管线内状态跳变，签名指向 init_replace/负深度注入族（与 T2-R1 解剖链吻合）。
- 事件击中起飞爬升初段：GT 证实全程 max 离地 0.358m（bag model_states 67733 帧，airborne 窗重算）；VINS |p| 虚报 7.64m/|v| 7.16 m/s（P_x 跑飞早期形态）。
- **D2 odom 门实战首验**：33.08-36.28s 拒 200+ 帧（v=1/2/3 全谱），AUTO_HOVER(L2)→MANUAL_CTRL(L1) 兜底，px4ctrl 零毒入。
- E-4 域（EKF2 域）有效数据：**EV_CTRL=15 项目首次真启用**；ev_vpos 融合活性 +（n_active=30108，innov p50=0.13，ratio p50=0.32，门内零超）；~~ev_hpos 未排程（estimator_innovations 无该字段）~~【2026-10-02 勘误：字段实在且 innov 全有限 med0.007-0.010，cs_ev_pos 激活窗 9.3-31.4s 后被 33.2s 爆走毒化熄灭；真根因=vision_pose-only 链 velocity 全 NaN（ev_vel 恒 0）——详见 v10_2026-10-02/u3u4_research_and_ev_hpos_verdict.md §B】；ev_too_fast=0（C-6 ulog 半边闭环）；G-off 臂 EKF2 水平失观测画像：XY 纯推算漂移 p50=350m/max=914m（地面态），z 通道紧（rel p50=0.074，baro+ev_vpos 在融）——J5 的 G-on/G-off z 分列首组数据。

### 轮 2（重试）= run_E4_GOFF_D10_R2_194927（同配置）
- VINS 爆走 t=32.38s（|dP|=0.474→0.482，dP=[-0.33,-0.23,+0.24]→[+0.36,+0.29,-0.13] xy 振荡=P_x 翻号族），早于/强于轮 1；探针 222 行；FAIL。
- **2/2 同因同窗（t≈32-33s，均击中爬升初段）→ 设计 §5 R3：连续 2 轮同因失败停跑转分析**。回归轮未飞（纪律优先）。

## 判读
1. **事件归属=T2-R2 input-domain 载具家族**：两枚新在线事件+探针出生数据支持 T2 判决；E-4 配置（EKF2 EV_CTRL=15/GPS_CTRL=0）无指向 VINS 的机制路径（planner odom=/vins_estimator/imu_propagate 直供核实=launch:20/91；vins_to_mavros 门控只监测 VINS 侧）。E-4 配置因果不成立、不排除——留待 R2F 修复后的复排窗检验（同 A.2/A.4/X4 依赖链）。
2. **飞行域矩阵（hover 60s）本窗不可飞**，挂起至：T2 R2F 修复面收口或 input-domain 事件率下降（登记唤醒条件）。
3. **E-4 ulog 域资产已到手**（见轮 1）——"E-4 启用域首发刻画"的 EKF2 域半边已开始产出。
4. C-6 活窗半边未取（rostopic hz/mavparam 实读）——工具坑：非交互 ssh 无 ROS 环境（source 缺失=零输出，T3-E7 夜同坑），下窗以 source 打头。

## 工具与流程整改
- e4_wheel.sh v2：rcS 快照→ekf2 前插注入→trap 恢复（两轮均恢复实证，grep 零残留）；v1 的 mavlink_shell 路线撤（14557=2018 前死约定，README §3 自记）。
- e4_judge.py v2 入 analysis/（J1-J5 快判，numpy 标量转 float 后 JSON 可序列化）。
- STATUS 自写时间戳重犯（12:47 案第二次）——已在 STATUS 原行修正并自认；后续一律留空由 status_append.py 盖远端实钟。
- smoke truth 监视器对 goal=(0,0,1) 类"出生即在目标"轮 min_truth=1e9/last=-1（两轮同现；bag 内数据无损）=smoke 侧 watcher 缺陷，登记待修（不阻塞）。

## 遗留与唤醒
| 项 | 状态 | 唤醒 |
|---|---|---|
| E-4 飞行域矩阵（D10 两态+回归） | 挂起 | T2 R2F 收口通告 or input-domain 事件率回落 |
| ev_hpos 未排程根因 | open | E-5 条件臂窗口（先读 v1.17 EV_CTRL 位表+aid 调度源码） |
| C-6 活窗半边（rostopic hz+mavparam 实值） | open | 任一活窗短轮（source ROS env 前置） |
| smoke watcher (0,0,1) 缺陷 | open | T1 队列（低优） |
| 两事件探针出生数据 | 已落袋 | @T2 消费（R2 载具家族加码）；T1 按预注册表 D1-D6 对号 |
