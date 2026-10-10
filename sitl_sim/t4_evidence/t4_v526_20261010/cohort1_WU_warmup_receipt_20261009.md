# cohort 1/7 收货台账：预热对照批（2026-10-09，T4 收货验收员）

- cohort 定义：预热对照批|16|/home/ghj/sitl_sim/vins_smoke_runs/run_WU_{E8P,S12P,S8O,E12O,NE8O,N8P,E12P,S8P}_{A,B}_*/flight.bag|昨夜10-08 16:12-17:28；A/B臂标记在文件名后缀
- bag_count=16（cohort 定义值）；received=15（实物）；**缺 1：run_WU_E8P_A_*（glob 0 命中，ls run_WU_E8P* 仅 E8P_B_160512）**
- 缺失注记：今晨 WU_FIX_E8P_A{,_r2}（cohort5，10-09 05:29/05:39）为 E8P_A 腿 goal 修复补飞，STATUS.md:1089（T2 05:4x 行）判 WU_FIX_E8P_A_r2 干测 PASS；T2 台账 /home/ghj/sitl_sim/t2_experiments.md grep 'E8P_A'=0 命中(rc=1)，原始 E8P_A 无收货/判决记录。缺失事实交汇总步骤，cohort 内不下三态。

## 判据源核查（红线①）
- 结论：**本 cohort 无预注册收货判据 → 全部袋只记"收讫-待判"，不出三态。**
- 已查：①t4-w3w5 §3 场景分门口径（无障碍 0.5m/障碍 0.75m 连续 3s）——阈值原文"连续 3s"命中文件=/home/ghj/catkin_ws/sitl_sim/t3_experiments.md（T3 实验到位门域）、t2_results/R2_dissect/prereg_online_u3pp.md 等，均非 T4 对 WU 控制袋的收货判据；且该稿在 10-01 时点为"建议稿待 T3 核签"（记忆线索 t4-w3w5-waiting-batch.md）。②本 cohort 15 袋 rosbag info 实测 imgTopics=0（flight.bag=控制/状态流，无 sensor_msgs/Image），场景分门（视觉到位门）对象不适用。③本批实验级判决已有 T1 定案：STATUS.md:1065"1c 预热对照批 8 对全执行+判决定案 NOT-EFFECTIVE(-50pp…A 0%/B 50%,到位 0/8 vs 5/8,poscmd 活=FSM 不采 mission goal)"——属 T1/T2 实验判决，非 T4 收货三态。

## 台账行（格式：袋名|时长s|关键topics|md5前8(有则填'-')|臂标记|收货字段）
run_WU_E8P_A_*|-|-|-|A(预期,未到货)|未到货-缺失注记(见上)
run_WU_E8P_B_160512|379s|odom=11379,imu_raw=87460,pcmd=32323,goal=15,img=0|-|B|收讫-待判
run_WU_S12P_A_161957|391s|odom=11738,imu_raw=87646,pcmd=34172,goal=92,img=0|-|A|收讫-待判
run_WU_S12P_B_161217|392s|odom=11770,imu_raw=90549,pcmd=33197,goal=18,img=0|-|B|收讫-待判
run_WU_S8O_A_162735|390s|odom=11729,imu_raw=87394,pcmd=34172,goal=92,img=0|-|A|收讫-待判
run_WU_S8O_B_163510|104s|odom=3131,imu_raw=23596,pcmd=4415,goal=15,img=0|-|B|收讫-待判
run_WU_E12O_A_164025|391s|odom=11734,imu_raw=87243,pcmd=34171,goal=93,img=0|-|A|收讫-待判
run_WU_E12O_B_163747|105s|odom=3172,imu_raw=24023,pcmd=5575,goal=14,img=0|-|B|收讫-待判
run_WU_NE8O_A_164759|399s|odom=11973,imu_raw=88613,pcmd=34172,goal=93,img=0|-|A|收讫-待判
run_WU_NE8O_B_165541|158s|odom=4763,imu_raw=35743,pcmd=4416,goal=28,img=0|-|B|收讫-待判
run_WU_N8P_A_170142|391s|odom=11744,imu_raw=89534,pcmd=34170,goal=92,img=0|-|A|收讫-待判
run_WU_N8P_B_165914|94s|odom=2838,imu_raw=21928,pcmd=4416,goal=14,img=0|-|B|收讫-待判
run_WU_E12P_A_170921|391s|odom=11740,imu_raw=86776,pcmd=34173,goal=92,img=0|-|A|收讫-待判
run_WU_E12P_B_171659|89s|odom=2673,imu_raw=20024,pcmd=3260,goal=15,img=0|-|B|收讫-待判
run_WU_S8P_A_172142|391s|odom=11733,imu_raw=86900,pcmd=34170,goal=92,img=0|-|A|收讫-待判
run_WU_S8P_B_171914|94s|odom=2834,imu_raw=21223,pcmd=4404,goal=14,img=0|-|B|收讫-待判

## size+mtime（stat 实测，远端 +0800）
E8P_B 474009042B@10-08 16:12:11 | S12P_A 508868707B@16:27:08 | S12P_B 513040937B@16:19:29 | S8O_A 226416238B@16:34:46 | S8O_B 59610598B@16:37:34 | E12O_A 226289761B@16:47:36 | E12O_B 60799554B@16:40:12 | NE8O_A 230257758B@16:55:18 | NE8O_B 89961158B@16:59:00 | N8P_A 511211063B@17:08:53 | N8P_B 122964266B@17:01:29 | E12P_A 508010489B@17:16:32 | E12P_B 112064825B@17:19:08 | S8P_A 507873912B@17:28:53 | S8P_B 122051997B@17:21:28

## 可读性
15/15 袋 rosbag info rc=0（bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info …'，逐袋退出码回收），chunks N/N 全部完整（643/643、638/638、594/594、280/280 等），索引可读=袋可读；mtime 均为 10-08 16:12-17:28（>14h 前，无在写迹象）。

## md5 决策
本 cohort 未做任何 md5：无预注册锚袋定义（任务书"工具正源 md5 前 8"指工具源非袋；E4 六袋锚属既往 cohort），且全部"收讫-待判"无收口袋；红线④下不做非必要大 IO，以 size+mtime 代记。全袋 md5 栏='-'。

## 描述性观察（不作三态）
B 臂多袋时长显著短于 A 臂（S8O_B 104s vs A 390s；E12O_B 105s；N8P_B/E12P_B/S8P_B 89-94s vs A ~391s），goal 计数 B 臂 14-18 vs A 臂 92-93——与 STATUS.md:1065 定案"NOT-EFFECTIVE(A 0%/B 50%,FSM 不采 mission goal)"形态一致；仅记录，判读权在 T1/T2。

## 本单元已跑命令
1. `ssh nuc2 "ls -d /home/ghj/sitl_sim/vins_smoke_runs/run_WU_{…8场景…}_{A,B}_*/flight.bag"` → 15 袋
2. `ssh nuc2 "ls -d …/run_WU_E8P*; stat -c '%n|%s|%y' …"` → E8P_A 不存在+15 袋 size/mtime
3. `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'` ×15 → rc/chunks/topics/时长
4. `ssh nuc2 "grep -n -E 'WU|A1OBS|NOT-EFFECTIVE|预热|复验|对照' STATUS.md | tail -25"` → L1065/L1089/L1095
5. `ssh nuc2 "grep -c 'E8P_A' ~/sitl_sim/t2_experiments.md"` → 0(rc=1)；`grep -rln '连续 3s' ~/catkin_ws/sitl_sim --include='*.md'` → t3_experiments.md 等
