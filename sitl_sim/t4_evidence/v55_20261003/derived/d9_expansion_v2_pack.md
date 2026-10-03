# T4-5.5 / D9 扩样执行回执 v2（2026-10-04，机械输出）

**结论先行：扩样行 k=0。smooth_lie 系列保持 n=66（v1 三件 segments/perframe/pack 仍为正本，未触碰）。
本次无新冻结段素材可入样，三新袋逐袋实测证据如下。本件为执行回执，不含任何判读语（判读待主会话依预注册出）。**

## 1. 前置门实测

- 判据册 md5：`md5sum ~/catkin_ws/docs/t4_smooth_lie_prereg.md` →
  `6784d008bd50230cc388094c5e698d68`（前 8 位 6784d008 = 在册值，核验通过；远端 date 2026-10-04 05:44:49 CST）。
- df 门：`df -BG` → Available 68G（≥25G 提帧门、≥20G 新轮门均满足；基线 51G 口径下亦充裕）。
- 空窗门：`pgrep -cx rosbag`=0、`pgrep -cx gzserver`=0（双 0，提帧前置满足；本轮实际未进入提帧）。
- staging：`/tmp/t4_d9_staging/` 三袋 `ln -s`（bags/ 直下袋先链接再喂工具，铁律执行）。

## 2. 逐袋实录（收货前置铁律：rosbag info 实测话题面；odom 提取 /vins_estimator/odometry 全行）

### 2.1 t2v3_route_024006.bag —— 无冻结段，跳过（如实注记）

- rosbag info：duration 2:57s (177s)，size 6.1 GB，messages 169234；
  图像面可行：`/iris_stereo_vins/vins_cam_left/image_raw` 3475 msgs + `..._right/image_raw` 3475 msgs；
  odom 面：`/vins_estimator/odometry` 1737 msgs。
- odom 提取（脚本 /tmp/t4_d9_work/d9_odom_extract.py，header.stamp 域，到达序全行落
  /tmp/t4_d9_work/odom_t2v3_route_024006.csv）：
  total_rows=1737，rows_gt5=**0**，rows_le5=1737，dup_stamp_groups=0，max_rows_per_stamp=1，
  row_run_max=0，t∈[19.360, 196.924]，pz∈[-0.006, **1.023**]（p50=0.958, p90=0.974）。
- §2 机械判定：pz>5.0m 连续窗 = **不存在**（rows_gt5=0，全程贴地 ~1m 高度）。任务口径"无冻结段袋如实注记跳过"执行。

### 2.2 t2v3_route_024434.bag —— 原袋缺位 + compact 残余零图像话题，图像侧不可行，注记挂账

- 原始袋 `t2v3_route_024434.bag` 在 bags/ 不存在；`find ~/sitl_sim ~/catkin_ws -maxdepth 4 -name "*024434*"`
  全盘仅命中 `/home/uav/sitl_sim/bags/compact_t2v3_route_024434.bag`（282.8 MB，compact 残余）。
- rosbag info（compact 残余）：duration 10:53s (653s)，**零图像话题**（话题面仅
  `/gazebo/model_states` 163354 + nav_msgs/Odometry[cd5e73d1] + `/vins_estimator/imu_propagate` 133362
  + `/vins_estimator/odometry` 6281）。EX-FAIL 第五坑登记面口径：零图像话题（compact）=图像侧不可行，
  注记挂账，禁硬提帧（未提帧）。
- 注：STATUS 05:23 行（腾位完成回执）已载明 W1 列管 3 袋权属未决；本袋原袋缺位与 compact 残余的存在形态
  为本轮回执新实测事实，处置权（是否补原袋/是否入 EX-FAIL 消费台账）留主会话。

### 2.3 t2v3_route_025808.bag —— 无冻结段，跳过（如实注记）

- rosbag info：duration 2:56s (176s)，size 6.0 GB；
  图像面可行：L/R image_raw 各 3420 msgs；`/vins_estimator/odometry` 1709 msgs。
- odom 提取（同 2.1 工具，csv=odom_t2v3_route_025808.csv）：
  total_rows=1709，rows_gt5=**0**，rows_le5=1709，dup_stamp_groups=0，max_rows_per_stamp=1，
  row_run_max=0，t∈[19.288, 195.884]，pz∈[-0.003, **1.193**]（p50=0.959, p90=0.968）。
- §2 机械判定：pz>5.0m 连续窗 = **不存在**。如实注记跳过。

## 3. 扩样台账与产物处置

- **nNew=k=0，nTotal=66**（无窗内主帧可并，六指标重算/D9 分箱扩展均无对象，未执行——非跳过执行）。
- segments/perframe 的 v2 csv **不产**：无新行可并，复制 v1 冒充 v2 属伪造，不做；v1 三件仍为唯一正本。
- D9 分箱轨迹不扩展（v1 d9_freeze_profile.csv/md 保持正本；其复刻对账工作因无新袋数据未启动）。
- odom 原始行 csv 两份落 /tmp/t4_d9_work/（易失区，重启即失；本回执已固化全部审计量，必要时可由袋复算）。
- 三袋均为 T2 线 route 袋（024006/025808 双解结构不存在，dup_stamp_groups=0，与 U3PR2 双解交错形态不同——
  纯结构事实记录）。"route 袋 pz≈1m 全程"是否属判据册 §1"机体未起飞而 odom 虚构高悬"的语义定性问题，
  属判读面，本件不下断语，留主会话。
- 判据/门值零放宽：§2 阈值 5.0m 原样机械执行，无一袋人为降阈入样。

## 4. 新判据需求清单（上交主会话，不在本件执行）

1. 若需对"低空贴地 route 袋（pz 全程 <5.0m 但非静置）"做 smooth-lie 型画像，现判据册 §2 的 5.0m 切分常数
   覆盖不到该形态——如需纳入须主会话预注册新切分规则后再执行，本执行员不发明阈值。
2. W1 列管袋（024006/025808）图像面已被 rosbag info 实证可行（各 ~3450 双目帧）且权属未决在册——
   若主会话裁定 route 贴地段有判读价值，建议明确权属与保全口径，防被 §8 腾位链误删。

---

执行：5.5/D9 扩样执行员（子代理），2026-10-04，NUC 远端时间基准。
判读待主会话依预注册出；本件待主会话定稿。
