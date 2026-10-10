# cohort 2/7 收货台账：预热复验批（2026-10-09，T4 收货验收员）

- cohort 定义：预热复验批|16|/home/ghj/sitl_sim/vins_smoke_runs/run_WU2_*_{A,B}_*/flight.bag|今晨10-09 05:48-07:04实物到货;含E12P_A_r2_070112补轮
- bag_count=16；received=16（实物 16 袋全部在，E12P_A 槽由 r2_070112 补齐）
- **第 17 个 run_WU2_* 目录=run_WU2_E12P_A_063516：无 flight.bag**（仅 hwmon_dmesg.log/hwmon.tsv/round.log/sitl.log/vins_config.md5，ls 实测）——即 T2 口径"16+1 env 补轮"中被 r2 替换的 env 失败轮壳目录，无袋可收。与 STATUS.md:1095（T2 06:5x 行"复验批 8/8 对完整执行(16+1 env 补轮,05:45-06:50)终判 NOT-EFFECTIVE"）吻合。
- 对照 cohort 1 缺失注记：昨夜缺失的 E8P_A 槽在本批由 run_WU2_E8P_A_054552 补上（实物在）。

## 判据源核查（红线①）
- 结论：**本 cohort 无 T4 预注册收货判据 → 16 袋全部只记"收讫-待判"，不出三态。**
- 本批实验级判据存在且已由 T2 用毕：冻结口径"≥15pp+方向一致 ≥6/8"=T2 任务书 D:/drone_VINS/plans/2026-10-09_T2_vins_quality_v10.7.md:19（单元2，本会话已读原文）；判决已落=STATUS.md:1095 NOT-EFFECTIVE(A 12.5% vs B 50%,-37.5pp,方向一致 3/8<6/8)。该判据属 T2 实验判决域，非 T4 收货三态依据；t4-w3w5 §3 场景分门口径同 cohort 1 核查结论（归属 t3_experiments.md 到位门域+本批 imgTopics=0 不适用）。

## 台账行（格式：袋名|时长s|关键topics|md5前8(有则填'-')|臂标记|收货字段）
run_WU2_E12P_A_063516(目录)|无flight.bag|仅hwmon/round.log/sitl.log/vins_config.md5|-|A-复验(env失败r1)|env失败壳目录-被r2替换,无袋可收
run_WU2_E12P_A_r2_070112|131s|odom=3950,imu_raw=29596,pcmd=6111,goal=95,img=0|-|A-复验-修复后(env补轮r2)|收讫-待判
run_WU2_E8P_A_054552|131s|odom=3945,imu_raw=30085,pcmd=6103,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_E12O_A_061543|424s|odom=12751,imu_raw=97385,pcmd=36039,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_N8P_A_063157|143s|odom=4291,imu_raw=32277,pcmd=7261,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_NE8O_A_062352|137s|odom=4122,imu_raw=30971,pcmd=7262,goal=92,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S12P_A_055841|159s|odom=4793,imu_raw=36005,pcmd=7699,goal=95,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S8O_A_060217|145s|odom=4367,imu_raw=32732,pcmd=7259,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S8P_A_064155|427s|odom=12811,imu_raw=97830,pcmd=33174,goal=94,img=0|-|A-复验-修复后|收讫-待判
run_WU2_E12O_B_061302|108s|odom=3252,imu_raw=24383,pcmd=5795,goal=14,img=0|-|B-复验-修复后|收讫-待判
run_WU2_E12P_B_063712|89s|odom=2674,imu_raw=20449,pcmd=3260,goal=15,img=0|-|B-复验-修复后|收讫-待判
run_WU2_E8P_B_054850|73s|odom=2216,imu_raw=16757,pcmd=3261,goal=15,img=0|-|B-复验-修复后|收讫-待判
run_WU2_N8P_B_062929|94s|odom=2827,imu_raw=21306,pcmd=4415,goal=14,img=0|-|B-复验-修复后|收讫-待判
run_WU2_NE8O_B_062703|94s|odom=2823,imu_raw=21361,pcmd=4415,goal=14,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S12P_B_055049|404s|odom=12128,imu_raw=93542,pcmd=33195,goal=17,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S8O_B_060537|382s|odom=11463,imu_raw=87395,pcmd=33185,goal=15,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S8P_B_063927|94s|odom=2839,imu_raw=21879,pcmd=4427,goal=14,img=0|-|B-复验-修复后|收讫-待判

## size+mtime（stat 实测，远端 +0800）
E12O_A 248612568B@10-09 06:23:27 | E12P_A_r2 166447115B@07:04:04 | E8P_A 170482472B@05:48:43 | N8P_A 185082824B@06:35:00 | NE8O_A 78756414B@06:26:49 | S12P_A 206545018B@06:02:01 | S8O_A 83254558B@06:05:22 | S8P_A 556372083B@06:49:42 | E12O_B 62099179B@06:15:30 | E12P_B 112447149B@06:39:21 | E8P_B 92599657B@05:50:43 | N8P_B 121930145B@06:31:43 | NE8O_B 53981739B@06:29:17 | S12P_B 528694638B@05:58:13 | S8O_B 223483222B@06:12:38 | S8P_B 122996660B@06:41:41

## 可读性
16/16 袋 rosbag info rc=0（bash -lc 带 ROS 环境，逐袋退出码回收），chunks N/N 全部完整，imgTopics=0；mtime 10-09 05:48-07:04 与盘点口径一致。

## md5 决策
未做任何 md5：本 cohort 无 T4 预注册锚袋定义、16 袋全部"收讫-待判"无收口袋；红线④下不做非必要大 IO，以 size+mtime 代记。

## 描述性观察（不作三态）
A 臂 6/8 袋 131-159s（短），2/8 全长（E12O_A 424s/S8P_A 427s）；B 臂 6/8 短（73-108s），2/8 全长（S12P_B 404s/S8O_B 382s）。goal 计数 A 臂 92-95 vs B 臂 14-17，与昨夜对照批形态同族。实验级解读权在 T2（其 NOT-EFFECTIVE 判决已落 STATUS.md:1095）。

## 本单元已跑命令
1. `ssh nuc2 "date +%H:%M; ls -d …/run_WU2_*_{A,B}_*/flight.bag | head -40; ls -d …/run_WU2_* | wc -l; stat -c '%n|%s|%y' …"` → 16 袋+17 目录+全袋 size/mtime
2. `ssh nuc2 "ls -d …/run_WU2_*; ls run_WU2_E12P_A_*/"` → 定位第17目录=E12P_A_063516 无 flight.bag
3. `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'` ×16 → rc/chunks/topics/时长
