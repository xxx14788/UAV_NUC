# cohort 5/7 收货台账：WU_FIX 干测（2026-10-09，T4 收货验收员）

- cohort 定义：WU_FIX干测|2|/home/ghj/sitl_sim/vins_smoke_runs/run_WU_FIX_E8P_A{,_r2}_*/flight.bag|10-09 05:29/05:39;STATUS L53 T2行口径=goal修复干测WU_FIX_E8P_A_r2 PASS;非16/16批内,单列
- bag_count=2；received=2（实物全在）：run_WU_FIX_E8P_A_052657 + run_WU_FIX_E8P_A_r2_053539
- 关联：昨夜 cohort1 缺失的 E8P_A 槽由此干测腿补飞（cohort1 台账已注记）

## 判据源核查（红线①）
- 结论：**本 cohort 无 T4 预注册收货判据 → 2 袋全部只记"收讫-待判"，不出三态。**
- T2 侧干测判决已存在（描述性引用，非 T4 三态）：STATUS.md:1089（T2 05:4x 行）"单元1 干测验证轮判定=goal 修复 PASS(WU_FIX_E8P_A_r2): G3 铁证=最终 planner 实例 INIT→WAIT_TARGET→Triggered!→GEN_NEW_TRAJ→EXEC_TRAJ(mission goal 走正路被采纳)+G4 位移=tsdiag x 0.29→8.28 飞向 goal(9.01,0.98)(vel 0.47)+G2=W2 路径生效…"——判据与判决均 T2 域；t4-w3w5 §3 场景分门同 cohort1-4 核查（不适用，本批 imgTopics=0）。

## 台账行（格式：袋名|时长s|关键topics|md5前8(有则填'-')|臂标记|收货字段）
run_WU_FIX_E8P_A_052657|119s|odom=3587,imu_raw=27736,pcmd=无,goal=无,img=0|-|A-修复后干测r1(失败轮)|收讫-待判(无pcmd/goal topic=planner未出指令)
run_WU_FIX_E8P_A_r2_053539|205s|odom=6179,imu_raw=46947,pcmd=6104,goal=107,img=0|-|A-修复后干测r2|收讫-待判(T2已判PASS见STATUS:1089,非T4三态)

## size+mtime（stat 实测，远端 +0800，10-09）
r1 152956249B@05:29:36 | r2 265942796B@05:39:45

## 可读性
2/2 袋 rosbag info rc=0（bash -lc 带 ROS 环境，逐袋退出码回收），chunks N/N 完整，imgTopics=0。mtime 05:29/05:39 与盘点口径吻合。

## md5 决策
未做任何 md5：本 cohort 无 T4 预注册锚袋定义、2 袋全部"收讫-待判"无收口袋；红线④下不做非必要大 IO，以 size+mtime 代记。

## 描述性观察（不作三态）
r1 无 /position_cmd 与 /move_base_simple/goal topic（planner 未出指令=干测未过形态）；r2 两 topic 均在且 goal 计数 107（提频重发形态，与修复案"mission goal 提频重发"机制一致）。两轮差异与 T2 干测判定路径（r1 失败→r2 PASS）自洽。

## 本单元已跑命令
1. `ssh nuc2 "date +%H:%M; ls -d …/run_WU_FIX_E8P_A*/flight.bag; stat -c '%n|%s|%y' …"` → 2 袋+size/mtime
2. `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'` ×2 → rc/chunks/topics/时长
