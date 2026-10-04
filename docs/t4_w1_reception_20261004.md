# T4-W1 收货链判读行草稿（2026-10-04 夜）

**状态：草稿·待主会话定稿。** 本文件所有判读行均为"草稿·待主会话定稿"，三态判定与定稿=主会话件。

- SLA 起点：21:16 T2 并轮战役收口通告。
- 执行人：T4 视觉验收线 W1 收货链执行员。
- 收货对象：T2 route/ground 袋 3 只（**J2 阈值表 v1 cohort 外袋**——在册 cohort=8 注入代袋，j2_threshold_table_v1.json bags 字段；本次袋均不在册，判读行只出数值化画像，对照门值仅供参考行）。
- 开工核验（远端 21:2x）：四工具 md5 前 8 位 j3_image_metrics=3721399e / j3_fb_residual=08cb8829 / j3_feature_density=7f45974b / j3_extract_frames=18a71153 全符正源；三门 df=59G、rosbag=0、gzserver=0；verdicts 正本 docs/t4_verdicts_v2.md md5 前 8=2f4323f1（相符）。
- 工具链：j3_extract_frames（--segments 3 --per-seg 24 --pairs，双目 2 话题，对齐同族先例 U3PR1_212450 参数）→ j3_image_metrics / j3_fb_residual → j3_feature_density --mode offset。staging 符号链接 /tmp/t4_w1_staging，输出 /tmp/t4_w1_work，重放输出 /tmp/t4_w1_work/replay（易失区）。
- 重放栈：t2_replay.sh 改造版（master 11312→11314，输出根→/tmp/t4_w1_work/replay），私有 rosmaster -p 11314，nice -n 10 + timeout 1200 包裹，config=E01_baseline（~/sitl_sim/t2_configs/E01_baseline/sim_stereo_imu_config.yaml），每袋前三门复查（df≥25G 且 rosbag/gzserver 双 0）。
- devel 栈重放前登记（md5 实测）：vins_node=9b88345b（devel/lib/vins/vins_node，全值 9b88345b4f1114e2516f778c78470a50）；libvins_lib.so=eea4cb2e（全值 eea4cb2e276aa6d37af7fd5d5ce49a91）——**eea4cb2e 正对 W2BB eea4cb2e 等价代（C-18 裁定允许的 devel 栈），注记：本次重放栈=W2BB eea4cb2e 等价代，vins_node=9b88345b 一并登记**。

---

## 袋 1：t2v3_route_024006.bag（6.1G，177s，双目带图 2 话题）

- 话题面：/iris_stereo_vins/vins_cam_left|right/image_raw 各 3475 帧，总消息 169234。
- 提帧：284 帧（主帧 n_primary=144，含 _next 对帧），manifest md5 前 8=9bad0eae。
- offset 实测：shift(gazebo-vins)=[0.9705, 0.9743, 0.1077]（offset json 前 8=c4221592）。
- **判读行（草稿·待主会话定稿）**：
  - M1 supply_frac：n=144，袋级 P50=0.620（med_ci [0.473, 0.660]），帧级分布 P10=0.122 / P50=0.620 / P90=0.778。
  - M2 grid4x4_occupancy_frac：n=144，袋级 P50=0.625（med_ci [0.625, 0.688]），帧级 P10=0.375 / P50=0.625 / P90=0.938。
  - σ̂P25（d12_sigma_p25）：n=140，袋级 P50=1.0286（med_ci [1.02769, 1.02934]），帧级 P10=1.0205 / P50=1.0286 / P90=1.0327。σ̂ 只认 P25——本行即 P25 统计的袋级转录。
  - med_gray：n=144，袋级 P50=83.0（med_ci [81, 83]），帧级 P10=39 / P50=83 / P90=176（夜间明暗跨度大）。
  - 对照门值参考行（**判据对象域外·不构成三态判定**）：M1 门 P10/P50=0.562/0.823（本袋 P50=0.620 低于门 P50 参考）；M2 门 P10/P50=0.588/0.844（本袋 P50=0.625 低于门 P50 参考）。
- 重放（W1REC_024006，成功，vins_alive=1）：odom n=1666，duration 176.54s；end_drift=0.042m；path_len=1533.04m；max_step=634.29m @t=133.440（dt=1.172s——1.17s 输出空窗后 634m 级跳变，另见 22.62m@123.088 / 22.59m@123.788 / 17.32m@119.788）。**机械转录，不判读**。
- metrics json 前 8=59f37c79；fbres json 前 8=73241f90（pools：temporal n=5503 p50=0.0107；stereo n=5595 p50=0.0150，h6 尾重注记在册）。

## 袋 2：t2v3_route_025808.bag（6.0G，176s，双目带图 2 话题）

- 话题面：同族双目 2 话题（3475 帧级与 024006 同族；总画像见 manifest）。
- 提帧：283 帧（主帧 n_primary=144），manifest md5 前 8=8ad1c9b8。
- offset 实测：shift=[1.0134, 0.9780, 0.1044]（offset json 前 8=30b69d9c）。
- **判读行（草稿·待主会话定稿）**：
  - M1 supply_frac：n=144，袋级 P50=0.607（med_ci [0.527, 0.640]），帧级 P10=0.173 / P50=0.607 / P90=1.000。
  - M2 grid4x4_occupancy_frac：n=144，袋级 P50=0.625（med_ci [0.625, 0.750]），帧级 P10=0.456 / P50=0.625 / P90=1.000。
  - σ̂P25（d12_sigma_p25）：n=139，袋级 P50=1.0278（med_ci [1.0269, 1.0285]），帧级 P10=1.0220 / P50=1.0278 / P90=1.0327。
  - med_gray：n=144，袋级 P50=85.0（med_ci [84, 87]），帧级 P10=42.3 / P50=85 / P90=176。
  - 对照门值参考行（**判据对象域外·不构成三态判定**）：M1 门 P10/P50=0.562/0.823（本袋 P50=0.607 低于门 P50 参考）；M2 门 P10/P50=0.588/0.844（本袋 P50=0.625 低于门 P50 参考）。
- 重放（W1REC_025808，成功，vins_alive=1）：odom n=1688，duration 175.56s；end_drift=2.479m；path_len=96.71m；max_step=4.61m @t=57.596（dt=1.300s），次级 3.20m@44.432 / 3.14m@44.540。**注意：path_len=96.71m 与 024006 的 1533m 量级差异悬殊，xyz 范围仅 x[-3.53,0.95] y[-3.58,0.83] z[-1.30,2.81]——差异照实转录，不判读**。
- metrics json 前 8=96016101；fbres json 前 8=d508ac37。

## 袋 3：t2v3_ground_205302.bag（1.5G，44.8s，双目带图 2 话题，登记画像级；重放亦已补做）

- 提帧：284 帧（主帧 n_primary=144），manifest md5 前 8=1f03c6c4。
- offset 实测：shift=[1.0090, 0.9870, 0.1033]（offset json 前 8=01cc7a2d）。
- **判读行（草稿·待主会话定稿）**：
  - M1 supply_frac：n=144，袋级 P50=0.543（med_ci [0.480, 0.613]），帧级 P10=0.442 / P50=0.543 / P90=0.640。
  - M2 grid4x4_occupancy_frac：n=144，袋级 P50=0.625（med_ci [0.625, 0.625]），帧级 P10=0.563 / P50=0.625 / P90=0.688。
  - σ̂P25（d12_sigma_p25）：n=140，袋级 P50=1.0298（med_ci [1.0292, 1.0304]），帧级 P10=1.0249 / P50=1.0298 / P90=1.0347。
  - med_gray：n=144，袋级 P50=82.0（med_ci [81, 83]），帧级 P10=81 / P50=82 / P90=83——灰度分布极窄（ground 场景均匀）。
  - 对照门值参考行（**判据对象域外·不构成三态判定**）：M1 门 P10/P50=0.562/0.823（本袋 P50=0.543 低于门 P10 参考下沿附近）；M2 门 P10/P50=0.588/0.844（本袋 P50=0.625 低于门 P50 参考）。
- 重放（W1REC_ground_205302，可选级已补做，成功，vins_alive=1）：odom n=398，duration 43.74s；end_drift=0.025m；path_len=79.0m；max_step=26.85m @t=55.692（dt=1.100s），次级 3.19m@54.224；xyz z 范围 [-16.59, 1.77]（含深负 z 段——照实转录，不判读）。
- metrics json 前 8=dc9089b1；fbres json 前 8=795c6a4c。

---

## 挂账面确认

- run_T2BL1..12 紧凑袋 12 只：四袋抽样 rosbag info 实测零图像话题（只含 control/IMU/odom/vins 面）——**EX-FAIL 第五坑登记面，图像侧收货不可行，只登记不提帧**。维持。
- compact_t2v3_route_024434.bag（283M，零图像）挂账维持。

## 入账 md5 清单（~/sitl_sim/vision_inputs/）

| 袋 | manifest | metrics | fbres | offset |
|---|---|---|---|---|
| t2v3_route_024006 | 9bad0eae | 59f37c79 | 73241f90 | c4221592 |
| t2v3_route_025808 | 8ad1c9b8 | 96016101 | d508ac37 | 30b69d9c |
| t2v3_ground_205302 | 1f03c6c4 | dc9089b1 | 795c6a4c | 01cc7a2d |

（均为 md5 前 8 位；全值以远端 md5sum 为准。）

## 过程异常与偏离（如实）

1. j3_extract_frames.py 直跑报 ModuleNotFoundError: rosbag——首次未 source ROS 环境；按纪律 `set +u; source /opt/ros/noetic/setup.bash; set -u` 后正常。非阻断。
2. rospack find vins_estimator / vins 在仅 source /opt/ros/noetic 下均 not found（catkin_ws devel 未入环境）；devel 产物改用文件系统实测路径 devel/lib/vins/vins_node 与 devel/lib/libvins_lib.so 直取 md5。非阻断。
3. 025808 重放 path_len=96.71m 与 024006 的 1533m 量级差异悬殊；024006 重放含 634.29m 级单步跳变、ground 重放含 26.85m 跳变（均伴 ~1.1-1.3s odom 输出空窗）。全部照实机械转录，未做任何修补或剔除，不判读。
4. t2_replay.sh 正本未改动；改造版（master 11314、输出根 /tmp/t4_w1_work/replay）落 /tmp/t4_w1_work/t4_w1_replay.sh。
5. 重放后各次 pgrep -x rosmaster 均清零，无私有 master 残留。
6. 无其他异常。全程未出现 df<25G（最低 58G）、未出现锁非零、未硬闯任何阻断项。

（本文件由 W1 收货链执行员起草，2026-10-04 夜；全部行=草稿·待主会话定稿。）
