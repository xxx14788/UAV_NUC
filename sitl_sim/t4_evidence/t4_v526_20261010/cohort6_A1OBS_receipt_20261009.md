# cohort 6/7 收货台账：候选 A1（observe 臂，2026-10-09，T4 收货验收员）

- cohort 定义：候选A1|2|/home/ghj/sitl_sim/vins_smoke_runs/run_A1OBS_N8P_r{1,2}_*/flight.bag|10-09 07:09/07:17实物落袋
- bag_count=2（盘点定义值）；**received=3（实物多出 1 袋）**：r1_070732 + r2_070959 + **r3b_072300（07:25:25 落袋，盘点 07:30 快照漏计）**。T2 判决文件自证该批设计=N8P×3 observe 轮+1 env 补轮（r3 ENV-FAIL→补 r3b），r3b 属本 cohort 家族，一并收讫（红线②内）。

## 两档口径（ask 第4条）
- **口径已寻得**：D:/drone_VINS/t4_work_20261008/t4_v524_workflow.ts:18（"M3 系紧凑腿两档收[第五坑+odom/truth 双模型名]+锚袋台账"）；:355-356（逐袋 rosbag info 三分类=紧凑零图像/带图/无袋；紧凑袋=odom/truth 机械数据段提取）；:333-336（IO 互斥门+df 门配方）。
- 本批三袋实测 imgTopics=0 → **全部分类=紧凑零图像档**（带图档六腿不触发）。
- 注记：v524 紧凑档的 odom/truth 三源深度提取（时长/pz 极值/末端差/jump 普查）非本 ask 行格式范围，未在本单元执行；且 T2 判决文件已含逐轮 jump/到位数字（见下），深度提取留判读材料单元。

## 锚袋 md5（ask 第4条：锚袋一律 md5 并记凭据）——已执行，IO 窗全程合规
- 07:51 首查进程：**T2 回放窗在飞**（rosbag play /tmp/dfs_DFS_A_MA_d4_r1_edited.bag + rosbag record 写 t3_results/DFS_A_MA_d4_r1_*，07:46 起，ps 实测 4 进程）→按红线④准备让路。
- 07:53 复核：rosbag play/record 进程=**0**（回放轮已毕/间隙）→按协议走完三步：①STATUS 预告行（中文走 scp 通道：本地 UTF-8→scp /tmp/t4_tmp_announce.txt→cat >> STATUS.md，tail -1 复核完好，RC=0，行内容"07:53 | T4 | 预告 | v5.26 | 单元3: A1OBS 锚袋md5x3 IO窗…@T2"）②复核进程仍=0（T2_ACTIVE_CHECK=0）③逐袋串行 md5sum（无并发）。
- **凭据（md5 前 8，全 32 位在案）**：
  - run_A1OBS_N8P_r1_070732/flight.bag = `782619d5`（782619d5a4be7e79c367ee9b3787d79f，rc=0）
  - run_A1OBS_N8P_r2_070959/flight.bag = `06eaaca2`（06eaaca203353cc9655fa00036735f0c，rc=0）
  - run_A1OBS_N8P_r3b_072300/flight.bag = `52483365`（524833659a87f7bc5d6b164e1dec1826，rc=0）

## 判据源核查（红线①）
- 结论：**本 cohort 无 T4 预注册收货判据 → 3 袋全部只记"收讫-待判"，不出三态。**
- A1 实验侧已由 T2 全链条收口（描述性引用，非 T4 三态）：
  - 预注册=/home/ghj/sitl_sim/t2_results/INPUTFACE/a1_observe_prereg_v1.md（v1.0 FROZEN，冻结 2026-10-09 04:1x 批跑前；判据：observe 绿率 ≥2/3→"门计算零副作用+拒帧动作独毒"定案；0/3→"门计算本身有副作用"新发现；1/3-2/3→混合带证据不足）。
  - 判决=/home/ghj/sitl_sim/t2_results/INPUTFACE/1c_runs/a1_observe_verdict_v1.md（本会话 scp 拉回全文已读）：r1 PASS(jump 0.094/到位 0.098)、r2 FAIL(5.435/9.115)、r3b FAIL(3.350/0.161)→**1/3 混合带→证据不足如实注记，扩批条款挂池**；r3 ENV-FAIL（双目话题未现）按 1 次/轮重试条款补 r3b。
  - t4-w3w5 §3 场景分门同 cohort1-5 核查（归属 T3 到位门域；本批 imgTopics=0 不适用）。

## 台账行（格式：袋名|时长s|关键topics|md5前8|臂标记|收货字段）
run_A1OBS_N8P_r1_070732|94s|odom=2829,imu_raw=21703,pcmd=4406,goal=14,vinsTopics=2,img=0|782619d5|A1-observe臂|收讫-待判(紧凑零图像档;T2判r1 PASS 0.094)
run_A1OBS_N8P_r2_070959|400s|odom=12020,imu_raw=93055,pcmd=33195,goal=17,vinsTopics=2,img=0|06eaaca2|A1-observe臂|收讫-待判(紧凑零图像档;T2判r2 FAIL jump5.435)
run_A1OBS_N8P_r3b_072300|105s|odom=3161,imu_raw=23819,pcmd=4494,goal=16,vinsTopics=2,img=0|52483365|A1-observe臂(env补轮)|收讫-待判(紧凑零图像档;T2判r3b FAIL jump3.350)
run_A1OBS_N8P_r3_071747(目录)|无flight.bag|仅hwmon/round.log/sitl.log/vins_config.md5|-|A1-observe(env失败r3)|ENV-FAIL壳目录(判决文件口径:双目话题未现),无袋可收

## size+mtime（stat 实测，远端 +0800，10-09）
r1 122444866B@07:09:45 | r2 524406530B@07:17:20 | r3b 136193672B@07:25:25

## 可读性
3/3 袋 rosbag info rc=0（bash -lc 带 ROS 环境，逐袋退出码回收），chunks N/N 完整，imgTopics=0，vinsTopics=2（observe 臂特征：flight.bag 内含 VINS 侧 topic，与 A1=报警不拒帧 observe 模式用途一致）。

## 与盘点的差异
盘点（07:30 快照）记 2 袋（r1/r2）且"A1OBS STATUS 零预告、实物先到"；实物=3 袋+1 env 失败壳目录。T2 预告文字至今未见 STATUS（判决文件已直落 1c_runs/），归属口径以判决文件为准。

## 本单元已跑命令
1. `ssh nuc2 "ls -d …/run_A1OBS_N8P_r*/flight.bag; stat; ps aux|grep -E '[p]x4|[g]zserver|[r]osbag|…'; tail -4 STATUS.md"` → 3 袋+size/mtime+T2 回放在飞证据
2. `ssh nuc2 "grep -n '紧凑' t2_experiments.md …; grep -rln 'A1OBS|报警不拒帧|observe' t2_results --include='*.md'"` → A1 预注册/判决文件定位
3. `scp nuc2:…/a1_observe_prereg_v1.md …/a1_observe_verdict_v1.md 本地` + Read 全文
4. `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'` ×3 → rc/chunks/topics/时长
5. 中文预告：本地 printf→scp /tmp→remote cat >> STATUS.md（tail 复核 RC=0）
6. `md5sum` ×3 串行（前置进程复核 T2_ACTIVE_CHECK=0）→ 三凭据 rc=0
