# 单元 3 研究优先件 + 单元 4 C-7 ev_hpos 源码读 — 合并产出（2026-10-02 02:0x）

## A. 经验清单一页（单元 3；检索=本地出口，NUC WAN 瘫不影响）

### A1. PX4 上游 ev_hpos（交叉验证用）
| 来源 | 结论 | 适用性 |
|---|---|---|
| PX4-Autopilot issues 搜 "ev_hpos never scheduled"/"ev_hpos" | **零直接命中**——上游无此已知问题报告 | 我们的判读术语是自造口径，上游无对应物 |
| #24298（closed） | v1.14 以 EV_CTRL 位域替代 AID_MASK；用户观察默认 15；位表=bit0 hpos/bit1 vpos/bit2 vel/bit3 yaw | 位表语义与 v1.17 源码一致（见 B）；"即使全开也需有效 EV 数据才融合"=数据触发条件的社区共识 |
| docs.px4.io tuning_the_ecl_ekf | External Vision 章节抓取截断不可用 | — |

### A2. px4ctrl/Fast-Drone-250 上游 odom 毒化社区经验（R3 控制域旁证）
| 来源 | 现象 | 回复/处理 | 适用性判断 |
|---|---|---|---|
| **#74（open，2023-12）** | out_path 稳但 `/vins_fusion/imu_propagate` 漂移明显（D435i+Jetson NX 实机） | **零回复至今** | 与我们 D1/跳变族同话题；上游无诊断无修复——**imu_propagate 流漂移是实机域同样暴露的架构级现象，非 SITL 伪影** |
| **#31（closed，2022-11）** | 起飞时 VINS 里程计大漂移（10+cm 级） | 无修复闭案 | 量级与我们悬停 0.12m 级架构属性一致；**起飞爬升段漂移与 E4 事件击中爬升初段同窗型** |
| #96（closed） | 起飞左飘+真值轨迹误差 | — | 边缘相关 |
**结论**：px4ctrl 上游对 odom 发散/跳变**无已知系统性处理**（三例零实质回复）；我们 D2 odom 门（三层依序）是超上游的自研防线，实机部署前保留=正确决策（R3 旁证落袋）。

## B. C-7 ev_hpos 源码读（v1.17.0，~/PX4-Autopilot；单元 4）

### B1. 位表与默认（源码=权威）
`src/modules/ekf2/params_external_vision.yaml`：EKF2_EV_CTRL bitmask，**bit0=水平位置/bit1=垂直位置/bit2=3D 速度/bit3=yaw，max=15，default=0**。
- 15=全启用含 hpos ⟹ "未排程"**不是参数位裁剪**
- **v1.17 上游默认=0（出厂不启用 EV 融合）**——E1 台账"EV_CTRL=0 全史"与上游默认一致；runbook 行"上游同形态"从默认值角度成立（airframe 未覆盖默认，非显式禁用）
- 注：#24298 用户观察 v1.14 默认 15 与 v1.17 源码默认 0 的差异=上游版本间默认值变更（v1.17 收紧），不影响本判

### B2. 调度条件链（ev_control.cpp + ev_pos_control.cpp，逐条钉死）
1. `ev_control.cpp:88-89`：`switch(vel_frame) default: return;` —— vel_frame 非法时**整体跳过 pos/hgt 调度**（代码级死区①）
2. `ev_pos_control.cpp` continuing 条件：`ev_ctrl & HPOS` && `tilt_align` && **`ISFINITE(ev_sample.pos(0/1))`**（数据触发条件②）
3. 帧分支：NED 需 `yaw_align`；FRD 需 `ev_yaw` 或旋转路径；**其他帧值→禁用**（③）
4. `measurement_valid`：pos+var 有限（var 有 max(0.01², evp_noise) 下限保护）

### B3. E4-R1 ulog 实测（11_30_48.ulg）——**"never scheduled"判读翻案**
| 通道 | 实测 | 原判读 | 修正 |
|---|---|---|---|
| ev_hpos innov | **全有限（31032 样本，med 0.0099/0.0069 健康量级）** | "无该字段=never scheduled" | **错误**：字段在且被调度 |
| cs_ev_pos | **置位 7.78%（激活窗 9.3-31.4s 单段 22s）** | 未提及 | 实况=**间歇激活型**：早期持续激活，33.2s VINS 爆走后毒化熄灭 |
| cs_ev_vel | **恒 0（从未 fuse）** | "ev_vpos 活性 ratio0.32"（实为 vpos 垂直位置） | 速度融合从未激活（与 vpos 是两回事） |
| vo 输入 | n=207，pose_frame=1(NED)✓ vel_frame=0(BODY_FRD)✓，**velocity/velocity_variance 全 NaN（frac=1.000）**，position 有限，**position_variance=[0,0,0]** | 未查 | **链级根因坐实** |

### B4. 根因定案（三层）
1. **ev_vel 恒 0**：`vins_to_mavros` 只发 `/mavros/vision_pose/pose`（PoseStamped，无速度无协方差；vins_to_mavros/src:416）→ mavros 转 VISION_POSITION_ESTIMATE → PX4 侧 vel=NaN → measurement_valid=false 永不 fuse。它订阅的 /vins_estimator/odometry 本带速度——**转发面丢弃了 twist**。
2. **ev_hpos 22s 后熄灭**：VINS 33.2s 爆走（E4-R1 事件）innov 毒化超门 → stopEvPosFusion——下游因果（跟随 VINS 健康），非调度缺陷。posvar=0 由下限兜底不影响此层。
3. **"参数门槛还是代码缺陷"定性**：**都不是**——是**输入链数据面不完整**（vision_pose-only 链丢速度/协方差）+ 爆走毒化（主因在 T2 input-domain 家族）。
- 死区①（vel_frame default return）在本案未触发（vel_frame=0 合法）；作为潜在坑登记（若上游改发非标准 vel_frame 会静默跳过 pos）。

### B5. E-5 条件臂设计（并入单元 5 E-4 复排矩阵）
- **E-5a 链升级臂**：vins_to_mavros 改发（或双发可选）`/mavros/odometry/out`（nav_msgs/Odometry 含 twist+协方差）→ 预期解锁 ev_vel 融合+posvar 真实化。同构性：实机 VINS 链同样可带速度发 odometry——**升级后更接近实机形态而非更远**；改动面=vins_to_mavros 发布段（launch 开关双臂，不破坏现链）。判据=复排轮 cs_ev_vel 置位率>0 且 ev_hvel innov 有限。
- **E-5b 观测臂**：不动链，R2F 修复后复排轮自然观测 ev_hpos 激活窗延长（>22s 至全程即跟随性证据）。
- G-off 特记：E4=G-off 轮，NED+yaw_align 门槛**已实证可过**（yaw_align 99.1% 置位，ev_pos 活窗在）——G-off 不构成 ev_hpos 排程障碍。

## C. 勘误义务
- E4_window1_report.md "ev_hpos 未排程（estimator_innovations 无该字段=never scheduled，开放项 E-5 条件臂）"一句需按 B3 修正——本文件即为修正凭据，报告原文加勘误注记（见 commit）。
