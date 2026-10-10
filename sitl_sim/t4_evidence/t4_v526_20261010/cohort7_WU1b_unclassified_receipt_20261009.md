# cohort 7/7 收货台账：未归类单袋 run_WU1b_E8P_A1_154907（2026-10-09，T4 收货验收员）

- cohort 定义：未归类|1|/home/ghj/sitl_sim/vins_smoke_runs/run_WU1b_E8P_A1_154907/flight.bag|10-08 15:56;名含'A1'字样但'WU1b'更像预热1b试飞,预热首试还是A1首飞无法从命名+STATUS判定,列未归类待T2口径
- bag_count=1；received=1（实物在）

## 归属证据采集（未定案——归属权在 T2，本台账只陈列证据）
- **候选 A1 首飞已另有序列**：候选 A1=observe 臂，预注册 a1_observe_prereg_v1.md（FROZEN 10-09 04:1x）明文格子=N8P（M3' 饥饿复现格），轮次命名=A1OBS_N8P_r1/r2/r3b（cohort 6 已收，判决文件=N8P×3+1 env 补轮，无 E8P 槽）。本袋=E8P 格、10-08 15:56 落袋（早于 A1 预注册冻结约 12 小时）——**与候选 A1 结构性不符**。
- **预热首试形态证据**：①目录构成=goal.txt/goal_trace.tsv/arrive_watch.txt/hwmon_*/j0_decomp.json，与预热 smoke 管道一致（对照 cohort2 r2 目录同款）；②goal.txt="goal: 9.010 0.980 1.0"=E8P 标准任务点（与 WU_FIX 干测 STATUS:1089 同点）；③落袋 15:56:30，早于预热对照批首袋（E8P_B 16:12:11）16 分钟=WU 试飞时序；④arrive_watch.txt="TIMEOUT min_truth=8.918 last=8.927"=该轮未到位超时（首试 FAIL 形态）——试飞后 16 分钟即开对照批，符合"先试后批"。
- **文字口径缺位**：grep 'WU1b' 于 STATUS.md/t2_experiments.md/t3_experiments.md 全库=0 命中（唯一命中=T4 自己 07:30 盘点心跳行 STATUS:1097）→T1/T2 无 WU1b 收货或判决文字。
- **T3 消费痕迹**：j0_decomp.json（10-09 04:06 生成）=T3 j0d 工具已把本 run 入组合矩阵数据面：j0_total 3.5751m/jump 0.1587m(n_jump=1)/transit 3.4176m 主导/jump_frac 4.44%。
- 结论：**归属维持"未归类待 T2 口径"**；结构性证据指向预热 1b 试飞（E8P A 臂 r1 时点），非候选 A1。

## 判据源核查（红线①）
- 结论：**无预注册收货判据 → 只记"收讫-待判"，不出三态；且 cohort 归属未定（红线②：不属已确认 cohort，不做任何三态）。**
- t4-w3w5 §3 场景分门同 cohort1-6 核查（归属 T3 到位门域；本袋 imgTopics=0 不适用）。

## 台账行（格式：袋名|时长s|关键topics|md5前8(有则填'-')|臂标记|收货字段）
run_WU1b_E8P_A1_154907|402s|odom=12084,imu_raw=90065,pcmd=34161,goal=94,vinsProp=90056,vinsOdom=3814,img=0|-|无(未归类:结构证据指预热试飞,A1字样待T2口径)|收讫-待判(未归类-归属待T2;TIMEOUT未到位8.918m;T3 j0d已消费)

## size+mtime（stat 实测，远端 +0800）
flight.bag 523419451B@2026-10-08 15:56:30（目录内 j0_decomp.json@10-09 04:06）

## 可读性
rosbag info rc=0（bash -lc 带 ROS 环境），656/656 chunks 完整，索引可读=袋可读；imgTopics=0，vins_estimator 双 topic 在流（imu_propagate 90056/odometry 3814）。

## md5 决策
未做 md5：本袋无预注册锚袋定义；未归类袋非"将要收口的袋"（不出三态）；候选 A1 的锚袋 md5 义务已在 cohort 6（A1OBS 三袋凭据 782619d5/06eaaca2/52483365）履行完毕——若 T2 后续口径改判本袋属 A1 序列，md5 可按 IO 窗协议补算。红线④下不做非必要大 IO。

## 本单元已跑命令
1. `ssh nuc2 "ls -la …/run_WU1b_E8P_A1_154907/; stat …/flight.bag; grep -n 'WU1b' STATUS.md t2_experiments.md t3_experiments.md"` → 目录构成+size/mtime+文字口径 0 命中
2. `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'` → rc=0/402s/topics
3. `cat goal.txt arrive_watch.txt j0_decomp.json`（远端小文件直读）→ goal 点/TIMEOUT 证据/T3 消费数据
