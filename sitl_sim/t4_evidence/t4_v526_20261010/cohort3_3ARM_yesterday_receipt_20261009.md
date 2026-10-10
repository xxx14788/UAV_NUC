# cohort 3/7 收货台账：三臂昨批（2026-10-09，T4 收货验收员）

- cohort 定义：三臂昨批|29|/home/ghj/sitl_sim/t3_results/3ARM_*/vins_out.bag|10-08;=base_MA/MB r1/r2/r1b 5袋轮+A_MA d{0,±2,±5,±10,±20}r1/r2 18袋轮+A_MB d{0,±10}r1/r2 6袋轮;ta标记=A臂
- bag_count=29；received=29（实物全在）
- **scope 修正**：`3ARM_*` 全部 vins_out.bag=41（ls | wc -l 实测；先前盘点辅助的 head -40 截断曾误读为 40）。41 = 本 cohort 29（`_ta_`/`_flight` 尾标，10-08）+ bc 12（10-09 03:53-05:24，**属 cohort 4**，本单元未收未动）。grep -c '_ta_|_flight'=29、其中含 bc=0，零重叠（红线②）。
- 组成核对（与盘点精确一致）：base_MA r1b/r1/r2 + base_MB r1/r2 = 5 ✓；A_MA d{0,±2,±5,±10,±20}×r1/r2 = 18 ✓；A_MB d{0,±10}×r1/r2 = 6 ✓。任务书预期'昨18' vs 实测 29 的差=base5+MB6，与盘点备注吻合。

## 判据源核查（红线①）
- 结论：**本 cohort 无 T4 预注册收货判据 → 29 袋全部只记"收讫-待判"，不出三态。**
- 实验级判决状态（描述性）：A 臂（δ 扫描）已有判决=δ 相变实锤（D:/drone_VINS/plans/2026-10-09_T2_vins_quality_v10.7.md:6"三臂臂 A 判决（δ 相变实锤）+臂 B/C 尾欠 12 轮"，本会话已读原文；尾欠 12 轮=cohort 4 bc 批已到货）；三臂终判表=T2 任务书单元3 待办。t4-w3w5 §3 场景分门口径同 cohort1/2 核查（归属 T3 到位门域；本批 imgTopics=0，vins_out.bag 为 VINS 输出下游袋，无原始图像，不适用）。

## 台账行（格式：袋名|时长s|关键topics|md5前8(有则填'-')|臂标记|收货字段；topics 两项=/vins_estimator/imu_propagate + odometry，计 vOdom=odometry 帧数，vProp=msgs−vOdom）
3ARM_base_MA_r1_flight|13.1s|vOdom=343,vProp=6333,img=0|-|base(无ta)|收讫-待判(异常短,13.1s中止轮,r1b已补)
3ARM_base_MA_r1b_flight|354s|vOdom=4368,vProp=100382,img=0|-|base(无ta)|收讫-待判
3ARM_base_MA_r2_flight|354s|vOdom=4209,vProp=97912,img=0|-|base(无ta)|收讫-待判
3ARM_base_MB_r1_flight|358s|vOdom=6898,vProp=159712,img=0|-|base(无ta)|收讫-待判
3ARM_base_MB_r2_flight|358s|vOdom=6899,vProp=159731,img=0|-|base(无ta)|收讫-待判
3ARM_A_MA_d0_r1_ta_*|354s|vOdom=4332,vProp=100980,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d0_r2_ta_*|354s|vOdom=4113,vProp=94458,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+2_r1_ta_*|354s|vOdom=4219,vProp=97130,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-2_r1_ta_*|354s|vOdom=4471,vProp=103547,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+2_r2_ta_*|354s|vOdom=3804,vProp=88607,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-2_r2_ta_*|354s|vOdom=5059,vProp=117361,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+5_r1_ta_*|354s|vOdom=2325,vProp=54116,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-5_r1_ta_*|354s|vOdom=2325,vProp=54126,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+5_r2_ta_*|354s|vOdom=2325,vProp=54119,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-5_r2_ta_*|354s|vOdom=2325,vProp=54119,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+10_r1_ta_*|354s|vOdom=2325,vProp=54121,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-10_r1_ta_*|354s|vOdom=2325,vProp=54116,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+10_r2_ta_*|354s|vOdom=2325,vProp=54120,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-10_r2_ta_*|354s|vOdom=2325,vProp=54118,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+20_r1_ta_*|354s|vOdom=2325,vProp=54120,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-20_r1_ta_*|354s|vOdom=2325,vProp=54116,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+20_r2_ta_*|354s|vOdom=2325,vProp=54119,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-20_r2_ta_*|354s|vOdom=2325,vProp=54118,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MB_d0_r1_ta_*|358s|vOdom=6898,vProp=159698,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d0_r2_ta_*|358s|vOdom=6875,vProp=159203,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d+10_r1_ta_*|358s|vOdom=3454,vProp=80196,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d-10_r1_ta_*|358s|vOdom=3454,vProp=80199,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d+10_r2_ta_*|358s|vOdom=3454,vProp=80199,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d-10_r2_ta_*|358s|vOdom=3454,vProp=80199,img=0|-|ta(A臂,MB机型)|收讫-待判

（目录名尾部双重后缀"_ta_3ARM_…_edited"为远端原样命名，台账照录；"ta_*"为缩写）

## size+mtime（stat 实测，远端 +0800，10-08）
d0_r1 80446207B@18:34:40 | d0_r2 75300157B@20:08:47 | d±10_r1 43113414/43109599B@19:14:02/19:21:52 | d±10_r2 43112651/43111125B@20:48:01/20:55:52 | d±20_r1 43112651/43109599B@19:29:43/19:37:34 | d±20_r2 43111888/43111125B@21:03:42/21:11:32 | d±2_r1 77421119/82513815B@18:42:35/18:50:27 | d±2_r2 70595196/93510168B@20:16:39/20:24:30 | d±5_r1 43109599/43117229B@18:58:18/19:06:11 | d±5_r2 43111888×2B@20:32:20/20:40:10 | A_MB_d0_r1/r2 127244939/126849181B@19:45:21/21:19:19 | A_MB_d±10_r1 63883069/63885358B@19:53:06/20:00:51 | A_MB_d±10_r2 63885358×3B@21:27:03/21:34:47 | base_MA_r1b 80018841B@18:09:32 | base_MA_r1 5145097B@17:41:06 | base_MA_r2 78010451B@17:47:23 | base_MB_r1/r2 127255621/127270886B@17:53:43/18:00:04

## 可读性
29/29 袋 rosbag info rc=0（bash -lc 带 ROS 环境，逐袋退出码回收），chunks N/N 全部完整，imgTopics=0。topics 结构=每袋恒 2 topic：/vins_estimator/imu_propagate + /vins_estimator/odometry（nav_msgs/Odometry，样例袋 d0_r1 全 info 已核）。mtime 10-08 17:41-21:34 与"昨批"口径吻合。

## md5 决策
未做任何 md5：本 cohort 无 T4 预注册锚袋定义、29 袋全部"收讫-待判"无收口袋；红线④下不做非必要大 IO，以 size+mtime 代记。（"每轮重放登记 vins_node md5"是重放件纪律，非收货件，不适用本单元。）

## 描述性观察（不作三态）
①base_MA_r1_flight 仅 13.1s/5.1MB（中止轮），r1b 354s 已补——两袋均照收，是否采信 r1 由判读方定。②|δ|≥5 的 A_MA 袋 vOdom 恒 2325 帧、|δ|<5 与 d0 为 3800-5059 帧（MB 系 3454/6898）——帧率分档与 δ 取值强相关，仅记录数字，机理判读权在 T2/T1。

## 本单元已跑命令
1. `ssh nuc2 "ls -d …/3ARM_*/vins_out.bag | wc -l"` → 41；`grep -c -E '_ta_|_flight'` → 29；`grep _ta_|_flight | grep -c bc` → 0
2. `ssh nuc2 "stat -c '%n|%s|%y' …/3ARM_*/vins_out.bag | head -35"` → 29+袋 size/mtime
3. `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'` ×29 → rc/chunks/topics/时长；样例袋全 info 复核 topics 结构
