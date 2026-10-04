# U2.5 判定文 — E-5a L-odom 帧处理差异定位（T1 v11.0 单元 2.5；2026-10-04 夜）

> 任务：mavros 1.20.1 odom 插件源码读 + pose_frame/vel_frame 默认值钉死 + 两路径行为对照表；EV 撕裂红线判定挂此。
> 素材：R3=E4R2-GOFF-D10-LODOM_100819（L-odom 臂唯一轮）；R4=E4R2-GON-D30_101723（撕裂#5 轮）；mavros 1.20.1 上游源码（dpkg 1.20.1-1focal 实装对号）。

## 1. 源码事实（mavros 1.20.1，上游 tag 对号）

### 1.1 pose_frame/vel_frame 默认值钉死

**1.20.1 odom 插件（mavros_extras/src/plugins/odom.cpp）不存在 pose_frame/vel_frame 参数**（旧版参数已删）。发向路径（odom_cb）为**运行时 TF 查找**：

```
lookup_static_transform(fcu_odom_parent_id_des+"_ned", odom->header.frame_id, tf_parent2parent_des)
lookup_static_transform(fcu_odom_child_id_des+"_frd", odom->child_frame_id,  tf_child2child_des)
```

默认值来自 px4_config.yaml odometry 段（我方 02_start_mavros.sh 用上游默认 px4.launch，无覆盖）：
- `odometry/fcu/odom_parent_id_des = "odom"` → 查找 **odom_ned ← header.frame_id**
- `odometry/fcu/odom_child_id_des = "base_link"` → 查找 **base_link_frd ← child_frame_id**
- `odometry/fcu/map_id_des = "map"`（仅收向路径用）

### 1.2 关键缺陷结构（上游代码，二连）

1. **TF 树不连通**：mavros 启动时 `UAS::setup_static_tf()` 只发三条互不连通的 static 链：`map→map_ned`、`odom→odom_ned`（均 RPY(π,0,π/2)=ENU↔NED）、`base_link→base_link_frd`（RPY(π,0,0)=FLU↔FRD）；且 px4_config 默认 `local_position.tf.send: false`（odom→base_link 不发）。**frame_id="map" 时 odom_ned←map 无路径**。
2. **失败后未初始化内存继续参与运算**：`lookup_static_transform` 捕获异常后仅 ROS_ERROR_THROTTLE 返回；调用方 `Eigen::Affine3d tf_parent2parent_des;` 保持未初始化，随后 `.linear()*position` 与 `tf_parent2parent_des*q*R_frd⁻¹` 照常执行——位置与姿态被（恒定残留的）垃圾矩阵污染。

### 1.3 vision_pose 插件对照（L-pose 路径）

vision_pose_estimate.cpp `send_vision_estimate`：**硬编码** `ftf::transform_frame_enu_ned` + `transform_orientation_baselink_aircraft`（无 TF 依赖、无帧参数），发 VISION_POSITION_ESTIMATE（x,y,z,rpy，**无速度字段**）；stamp=header.stamp（ns/1000）；PoseStamped 路径协方差零阵。行为确定、无失败路径。

## 2. 两路径行为对照表

| 维度 | L-pose（vision_pose_estimate） | L-odom（odom） |
|---|---|---|
| 订阅 | /mavros/vision_pose/pose (PoseStamped) | /mavros/odometry/out (Odometry) |
| MAVLink | VISION_POSITION_ESTIMATE（无速度） | ODOMETRY（pos+q+vel+angvel；LOCAL_FRD/BODY_FRD；estimator=VISION） |
| 帧变换 | 硬编码 ENU→NED + baselink→aircraft（确定） | TF 查找（odom_ned←frame_id, base_link_frd←child）；**frame_id="map" 必失败** |
| stamp | header.stamp→usec | header.stamp→time_usec（一致） |
| 协方差 | 零阵 | 零阵经 TF 旋转仍零（一致；EKF2 噪声参数驱动） |
| 速度语义 | 无 | twist 须 body 系（child_frame_id）；odom_fill 的 world→body 旋转数学已验证正确（q_bar·v·q 展开） |
| EKF2 EV 面 | pos+yaw（vel 无源） | pos+vel+yaw（本应全） |
| 实测 R1/R2 vs R3 | cs_ev 1.0/**0**/1.0；J1 0.019-0.023 PASS | cs_ev 1.0/**1.0**/**0**；J1 0.783 恒偏移；J4 1.12/J5 0.449 FAIL |

## 3. 实证对号（R3 轮，2026-10-03）

- mavros.log **"ODOM: Ex: Could not find a connection between 'odom_ned' and 'map' … unconnected trees"=285 条**（sim t=11.2s→310.68s 每秒 1 条 = 全程；轮长 309.7s）
- 判读面逐项对号（机理↔实测）：
  - 位置被恒定垃圾矩阵作用 → **J1 恒偏移 0.783（p95 0.766≈max=系统性非振荡）** ✓
  - G-off 下 EKF2 位置唯一源=EV → 跟随带恒偏移但自洽的 EV → innov≈0/n_active=29996 → **cs_ev_pos=1.0** ✓
  - 姿态 q 同被垃圾矩阵污染 → yaw 融合不可用 → **cs_ev_yaw 1.0→0** ✓
  - 速度链只经 child 变换（base_link_frd←base_link=static 直连成功）不碰垃圾矩阵 → **cs_ev_vel=1.0**（速度融合健康=ev_vel 悬案翻案证据链不受影响） ✓
- 反向对号：R4（撕裂#5）与 R1 轮 `ODOM: Ex:`=0（odom 插件未激活=确认 L-pose 臂）。

## 4. 出口判定（任务书三出口对号）

**出口①命中（帧/朝向 bug→修复）**：L-odom 臂"如飞版不合格"根因=mavros odom 插件 TF 不连通+未初始化矩阵污染（非配置、非 EKF2）。修复面=我方代码 vins_to_mavros/odom_fill.h（mavros 为 binary 不可改）：
- `fill_odom_msg` frame_id **"map"→"odom"**（已落码，git diff 7+2 行）：odom_cb 查找 odom_ned←odom 走通 static TF → 位置获得正确 ENU→NED（与 L-pose 硬编码同构）、姿态链 `R_enu_ned·q·R_frd⁻¹` 同构正确、语义同时满足 REP-147（odom 消息父帧=odom）。
- 验证计划（build 窗+飞轮窗）：①gtest（test_odom_fill 期望已同步）②修复轮悬停 A/B：`ODOM: Ex:` 归零 + J1/J4/J5 回 L-pose 级 + cs_ev_yaw 回 1（三重判据）③增强验证=G-on×D30 L-odom 修复臂复测（见 §5）。

**出口②命中（撕裂#5 非帧因素→坐实，红线自主定）**：撕裂形态#5（EKF2 z 98m 发散/GT 恒稳 3.7mm/D2 门 17 帧截流）发生在 **L-pose 臂**（R4 轮 Ex=0 实证），该路径硬编码帧变换无 bug 面；机理=GPS(绝对世界)×高频 EV(imu_prop@30Hz, VINS 相对世界) 双世界源冲突，帧表达修复不改变双源冲突本质。
**红线判定（自主，DECISION_LOG D-2026-10-04-02）**：实机部署 GPS 在场时禁高频 EV 源（pub_source=imu_prop 或 pub_rate≥D30 级）；G-on×D10 odometry 源健康（R2 实证）为许可形态。撕裂复测（修复臂 G-on×D30）不再现/再现均登记为红线佐证素材，不改变本判定（撕裂在 L-pose 臂已坐实）。

**出口③不适用**（两叉均有实证闭环）。

## 5. 交付与挂账

- 修复码：vins_to_mavros（odom_fill.h+test_odom_fill.cpp）随本窗 build；悬案池"L-odom 帧差异"闭案挂修复轮验证；EV 撕裂红线入 DECISION_LOG。
- 上游缺陷注记（不改但登记）：mavros 1.20.1 odom 插件 TF 失败后未初始化内存参与运算——上游健壮性缺陷，我方以 frame_id 对齐规避。
- 增强验证轮（G-on×D30 L-odom 修复臂）排修复轮验收窗内顺跑。
