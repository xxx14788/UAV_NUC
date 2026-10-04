# T4-5.5 / D9 扩样执行回执 v2-r2（2026-10-05，机械输出）

**结论先行：扩样行 k=0。smooth_lie 系列保持 n=66（v1 三件仍为唯一正本，全程未触碰，md5 见 §4）。
本轮素材=图像可行新袋 t2v3_hover_134845.bag，逐门实测后无冻结段，按任务口径如实注记跳过。
本件为执行回执，不含任何判读语（判读待主会话依预注册出）。前轮回执=d9_expansion_v2_pack.md
（2026-10-04，三 route 袋 k=0），本件为增量轮，前件不改动。**

## 1. 前置门实测

- 判据册 md5：`md5sum ~/catkin_ws/docs/t4_smooth_lie_prereg.md` →
  `6784d008bd50230cc388094c5e698d68`（前 8 位 6784d008 = 在册值，核验通过；远端 date 2026-10-05 06:08:14 CST）。
- 工具正源 md5（3090 实读核对，四件全符）：
  j3_image_metrics=`3721399e` ✓ / j3_fb_residual=`08cb8829` ✓ /
  j3_feature_density=`7f45974b` ✓ / j3_extract_frames=`18a711` ✓。
- df 门：`df -BG /` → Available 607G（≥25G 提帧门、≥20G 新轮门均满足）。
- 空窗门（odom 提取前实测）：`pgrep -cx rosbag`=0、`pgrep -cx gzserver`=0、`pgrep -cx px4`=0；
  load average 0.08；内存可用 30354M。私有 master 端口 11314/11318 实测空闲（本轮未起 roscore——提帧/重放无对象）。

## 2. 收货前置铁律（rosbag info 实测话题面）

- `rosbag info ~/sitl_sim/bags/t2v3_hover_134845.bag`：duration 2:17s (137s)，size 4.5 GB，messages 121214。
- 图像面可行：`/iris_stereo_vins/vins_cam_left/image_raw` 2604 msgs + `..._right/image_raw` 2604 msgs
  （sensor_msgs/Image）——非零图像话题，图像侧可行。
- odom 面：`/vins_estimator/odometry` 1301 msgs + `/mavros/local_position/odom` 4115 msgs。
- 素材单批 ≤24h 核对：137s ✓。

## 3. 分段（判据册 §2 机械切分；口径=前两轮先例：/vins_estimator/odometry，header.stamp 域，到达序全行，阈值 pz>5.0m）

- 提取脚本 /tmp/t4_d9r2_odom_extract.py（本地写→scp 两段式上传，两侧 md5 `08b06fe3` 一致）；
  全行 csv=/tmp/t4_d9r2_work/odom_hov134845.csv；审计件=odom_hov134845_audit.json。
- 审计值（全量）：total_rows=1301，t∈[16.568, 153.604]，
  pz∈[-0.0264, **0.8762**]（p50=0.2776, p90=0.7081），
  rows_gt5=**0**，rows_le5=1301，dup_stamp_groups=0，max_rows_per_stamp=1，row_run_max=0。
- §2 机械判定：pz>5.0m 连续窗 = **不存在**（窗首/末时刻=null，窗长=null）。
  任务口径"无冻结段袋如实注记跳过"执行。
- 事实注记面（**非切分依据**，仅事实数值，供主会话判读携带）：
  - `/gazebo/model_states` iris 机体 z：n=34290，t∈[16.592,153.744]，z∈[0.1039, 0.7018]（p50=0.1095）；
  - `/mavros/local_position/odom` z：n=4115，t∈[16.600,153.736]，z∈[-1.8348, 0.0939]（p50=-0.3093）——
    第二 odom 源同样无 >5.0m 行。
- 该袋是否属判据册 §1"机体未起飞而 odom 虚构高悬"的语义定性 = 判读面，本件不下断语，留主会话。

## 4. 扩样台账与产物处置

- **nNew=k=0，nTotal=66**（无窗内主帧可并）。
- 提帧未执行（j3_extract_frames 无对象：无冻结段→无帧子集消费者；不硬提帧）；
  六指标 /tmp 重算未执行（无对象）；D9 分箱轨迹不扩展（v1 d9_freeze_profile.csv/md 保持正本）。
- segments/perframe 的 v2 csv **不产**：无新行可并，复制 v1 冒充 v2 属伪造，不做（前轮回执同款裁定）；
  v1 三件仍为唯一正本，本轮全程未触碰，实测 md5（2026-10-05 06:19 CST）：
  - smooth_lie_segments.csv `6aaa23de11170878656ac3bae03f96f8`
  - smooth_lie_perframe.csv `fb450b04e42726a4724892a28d167b15`
  - smooth_lie_pack.md `749c8c1fb74cda21e0cc83b864079d2b`
  - d9_freeze_profile.csv `ebbf5af006ba1e045980791243e056c5`
  - d9_freeze_profile.md `b87266a3fa851329b77522ea4d65e4fb`
  - d9_expansion_v2_pack.md `edd3ce1d06f62c09d4ee9b7e15a1f899`
- odom 原始行 csv 落 /tmp/t4_d9r2_work/（易失区，重启即失；审计量已固化本件，必要时可由袋复算）。
- 判据/门值零放宽：§2 阈值 5.0m 原样机械执行，无一行为降阈入样；
  "低空贴地切分需求不立"维持，未发明任何低空切分新维度。

## 5. 新判据需求清单（上交主会话，不在本件执行）

1. （沿用前轮回执清单第 1 条，本轮 hover 袋入列）低空贴地形态（pz 全程 <5.0m 且非静置）的
   smooth-lie 型画像，现判据册 §2 的 5.0m 切分常数覆盖不到——须主会话预注册新切分规则后再执行，
   本执行员不发明阈值。本轮 hover 袋（真值 z 全程 ≤0.70m、vins pz 全程 ≤0.88m）同属该形态清单，
   是否纳入=主会话裁定。
2. W1 收货行（STATUS 05:52）已将 hover_134845 权属确认移交主会话（D-1005-T4-07 边界决策）；
   本轮回执新增事实：该袋双 odom 源全程 <5.0m、真值机体全程 ≤0.70m，无冻结段可入样。

---

执行：5.5/D9 扩样执行员（子代理），2026-10-05，3090 远端时间基准。
判读待主会话依预注册出；本件待主会话定稿。
