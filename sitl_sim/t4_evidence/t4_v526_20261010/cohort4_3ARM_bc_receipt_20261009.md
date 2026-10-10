# cohort 4/7 收货台账：三臂今补批（2026-10-09，T4 收货验收员）

- cohort 定义：三臂今补批|12|/home/ghj/sitl_sim/t3_results/3ARM_{B_drop3,B_drop10,B_down15,B_reord2,C_ctr,C_full}_r{1,2}_bc_*/vins_out.bag|10-09 03:53-05:24;bc标记=B/C臂;与任务书'今补12'精确一致
- bag_count=12；received=12（实物全在）；B 8 袋（drop3/drop10/down15/reord2×r1/r2）+C 4 袋（ctr/full×r1/r2），与 T2 任务书单元3"臂 B 8 轮+臂 C 4 轮（editor dry 双 PASS 已验）"（D:/drone_VINS/plans/2026-10-09_T2_vins_quality_v10.7.md:24，本会话已读原文）精确一致
- scope：与 cohort 3 零重叠（bc 尾标 12 袋，grep 实测；`3ARM_*` 总 41=ta/flight 29+bc 12）

## 判据源核查（红线①）
- 结论：**本 cohort 无 T4 预注册收货判据 → 12 袋全部只记"收讫-待判"，不出三态。**
- 实验级流程状态（描述性）：本批 12 轮=T2 任务书单元3 的"三臂补跑"尾欠（B/C 臂 editor 修复后），完成即入 T2 三臂完整判决表（A 时间戳[已判]+B 节奏+C 内容）——判决权在 T2，含 C 臂命中=场景改造立项条款。t4-w3w5 §3 场景分门口径同 cohort1-3 核查（归属 t3_experiments.md 到位门域；本批 imgTopics=0 不适用）。

## 台账行（格式：袋名|时长s|关键topics|md5前8(有则填'-')|臂标记|收货字段；topics=imu_propagate+odometry 双 topic，vOdom=odometry 帧数）
3ARM_B_drop3_r1_bc_*|354s|vOdom=3488,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop3_r2_bc_*|354s|vOdom=3490,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop10_r1_bc_*|354s|vOdom=4062,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop10_r2_bc_*|354s|vOdom=3976,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_down15_r1_bc_*|354s|vOdom=3692,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_down15_r2_bc_*|354s|vOdom=3614,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_reord2_r1_bc_*|354s|vOdom=4161,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_reord2_r2_bc_*|354s|vOdom=3874,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_C_ctr_r1_bc_*|354s|vOdom=4001,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_ctr_r2_bc_*|354s|vOdom=4108,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_full_r1_bc_*|354s|vOdom=4101,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_full_r2_bc_*|354s|vOdom=4106,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判

（目录名尾部双重后缀"_bc_3ARM_…_edited"为远端原样命名，照录）

## size+mtime（stat 实测，远端 +0800，10-09）
B_drop3_r1/r2 75300721/75076644B@03:53:38/04:18:10 | B_drop10_r1/r2 78380369/76562709B@04:01:32/04:26:03 | B_down15_r1/r2 74770984/73751146B@04:09:32/04:34:02 | B_reord2_r1/r2 76841656/72132220B@05:24:30/04:41:58 | C_ctr_r1/r2 73931560/75686035B@04:49:42/05:05:12 | C_full_r1/r2 76013148/75919426B@04:57:27/05:12:58

## 可读性
12/12 袋 rosbag info rc=0（bash -lc 带 ROS 环境，逐袋退出码回收），chunks N/N 全部完整，imgTopics=0，全部 354s，ntopics=2（imu_propagate+odometry，与 cohort 3 同构）。mtime 10-09 03:53-05:24 与盘点口径吻合。

## md5 决策
未做任何 md5：本 cohort 无 T4 预注册锚袋定义、12 袋全部"收讫-待判"无收口袋；红线④下不做非必要大 IO，以 size+mtime 代记。

## 描述性观察（不作三态）
B_reord2 对的 r1 mtime（05:24:30）晚于 r2（04:41:58）——该对命名序与落袋时间倒挂（其余 5 对均 r1 先于 r2），照录供判读方留意。C 臂 4 袋 vOdom 4001-4108 帧、B 臂 3488-4161 帧，量级正常。

## 本单元已跑命令
1. `ssh nuc2 "date +%H:%M; ls -d …/3ARM_{B_drop3,B_drop10,B_down15,B_reord2,C_ctr,C_full}_r{1,2}_bc_*/vins_out.bag | wc -l; stat -c '%n|%s|%y' …"` → 12 袋+全袋 size/mtime
2. `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'` ×12 → rc/chunks/topics/时长
