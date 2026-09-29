# T4-J3 E1/E2 证据落盘 — 口径两方锁 + 代位物落地（2026-09-30）

> 依据: plans/directions/C09_sim2real-vision-sixdim-baseline/DOSSIER.md（红队二轮修订版）
> 执行: T4-J3 线, 0 锁纯离线; HEAD=65674ab 时点（E1 两方实读）。
> 六维表合成与 runbook 勘误归 E8 收口（本文为其数字正源）。

## E1 口径两方锁（CF-1/CF-2 消解）【P1 预言成立】

**第一方（驱动配置）**：NUC HEAD 实读 `src/VINS-Fusion/config/realsense_d435/rs_camera_vins.launch`：
- infra1/infra2（VINS 双目消费流）: **640×480@30fps**
- depth 流: **640×480@30fps**（同样非 848×480）
- color: 关闭; **emitter_enabled=0**（结构光关闭 → R12 点阵伪纹理污染源在我方实机配置下不存在）

**第二方（VINS 消费内参）**：`realsense_d435/left.yaml` = `right.yaml`：
- 640×480, PINHOLE, 零畸变(k1=k2=p1=p2=0)
- fx=fy=387.507751464844, cx=323.501403808594, cy=232.691726684570

**两方一致 → 口径锁定**：
- VINS 消费口径 = **640×480 双目 @30fps**, fx=387.508（像素域统计基准 387.51; 门 4/5 的 460-focal 换算基准 1.25px@384.4→1.252px@387.5）
- runbook §1「848×480@30Hz(D435 双目红外)」为**能力口径误写**（CF-1 实锤）: 当前驱动配置 infra 与 depth 均为 640×480; 848×480 是 D435 全宽视口能力（对应 87°×58° 规格），非本链路消费口径
- CF-2 分行: README R6 表 sim fx=454.68 仅深度流侧（EGO-Planner 848×480 入口, README:110）; VINS 双目侧 sim fx=467.7427 未在表——六维表双目/深度**分行落账**，fx 行修正是「VINS 双目 sim 467.74 vs real 387.51（比 1.2071）」
- 勘误动作（CF-1/CF-2/CF-6 三处）随 E8 收口 commit 入 runbook/README，本文先立数字正源

## E2 代位物落地 + 公开源普查

### 2.1 已落地代位物（vision_inputs/ext_proxy/）

| 物件 | 大小 | 流 | 元数据落账 |
|---|---|---|---|
| stairs.bag (D435 pre-production, librealsense sample-data, 2020-10-07 版) | 409MB | Depth 1280×720@14.3Hz + Color 1920×1080@7.35Hz, **无 infra** | Depth sensor: **Exposure=8000μs 手动(AE=0)**, Gain=16, Emitter=1, LaserPower=240; Color: Exposure=-6 档 |
| d435i_walk_around.bag / d435i_walking.bag (D435i pre-production, 2018-11 版) | 1.56GB | Depth+Color 各 ~30Hz + IMU, **无 infra** | 室外行走场景 |

- 样张自身口径单列登记（代位物不与我方一致, 0.2b 条款）: depth fx=636.073@1280×720, color fx=1367.573@1920×1080
- **帧实测方法有效性侧证（P2 判据的换算分支）**: color 1080p HFOV=2·atan(960/1367.573)=**70.14°**/VFOV=43.09° vs D435 color 模块规格 69.4°×42.5° → 差 0.7°/0.6° **<1° ✓**; depth 720p=90.35°/59.02° vs depth 规格 87°×58° → 差 3.35°/1.02°（pre-production+2018 旧固件, 登记边界）。camera_info fx 直读换算法在样张上与规格互证成立。

### 2.2 公开代位源 infra 双目普查（E3 实机侧素材面, 四源全阴）

| 源 | 结论 | 证据 |
|---|---|---|
| librealsense 官方样张 ×3 | 无 infra 流 | rosbag info 实读（本机 02:11-02:15） |
| M2DGR (SJTU, RA-L22) | 无 infra 流（仅 color+depth+IMU） | GitHub README WebFetch 09-30 |
| M2DGR-plus / M3DGR (IROS25) | 无 infra 流（color+aligned_depth+IMU; M3DGR 仓库 404→sjtuyinjie/M3DGR 实查） | GitHub README WebFetch 09-30 |
| OpenLORIS-Scene | 无 raw infra（D435i 仅 color/depth/aligned; 双目用户被指向 T265 fisheye——异型成像器代位无效） | 官网 dataset 页 WebFetch 09-30 |

**裁决**: E3①（实机 infra 平坦区 σ̂）/ E3②（FPN 立体-时序尾部对照 H6）的实机侧=**数据缺口挂账**（非静默省略; 解锁条件=我方实机 D435 帧到位或含 infra 双目的新代位源）。dossier E2 止损链走到底档: FOV 行以配置换算+规格锚+样张侧证立表。

## E3① 实机侧现有数字（三重边界登记, 上界非正源）

D12 双口径（16×16 patch 平坦=梯度幅值最低 25% 分位; pool=全 patch 池 σ̂; **P25=patch σ̂ 分布 25 分位, 抗运动污染**）:

| 序列 | 口径 | σ̂ P50 | σ̂ P90 | 边界 |
|---|---|---|---|---|
| stairs color 36 帧×3 段 | pool | 3.01 | 3.33 | color≠infra 成像器; 移动手持序列 |
| stairs color | **P25** | （含在池内, 见 metrics json） | | 同上 |
| d435i_walk_around color 36 帧×3 段 | pool | 2.21 | 5.99 | color 成像器; 强运动(走动) |
| d435i_walk_around color | **P25** | 1.16 | 1.45 | 同上 |
| stairs depth(720p) | pool / **P25** | 6.56 / **0.044** | 7.42/0.14 | mm 域 α=0.05 缩放; Z 未配平(σ_z∝Z²); **P25 口径抗运动有效性两数量级实证** |

- 结论: ①实机 color 流 σ̂ 上界 1.2-3.0 gray counts, 但 **infra 成像器正源缺**（挂账, 禁以 color 填表正源）; ②**P25 口径方法论发现**: 移动序列下 pool 口径被运动伪差分抬高 1-2 个数量级, P25 口径恢复纯噪声量级——T3-D0 四件套后袋 sim 侧 σ̂ 复验（袋年代门通道二）**强制用 P25 口径**（袋内静止段若存在, pool=P25 互证; 袋年代门 σ 直筛同栈）
- γ 帧间增益: stairs/d435i 手动曝光下 γ_pair P50=1.0（零假设通过, 03 §4.1 增益不变性口径）

## E2 FOV 行落表数字（配置换算立骨 + 样张侧证）

| 口径 | HFOV | VFOV | 立体角(Ω=4·arcsin(sin(H/2)sin(V/2))) |
|---|---|---|---|
| **sim** (sim_stereo yaml fx=467.7427, SDF hfov=1.2rad 自洽) | **68.75°** | **54.32°** | 1.042 sr |
| **real** (realsense_d435 yaml fx=387.508, 实机标定) | **79.10°** | **63.54°** | 1.368 sr |
| 规格锚 (D435 datasheet, 848×480 全宽口径) | 87° | 58° | 1.361 sr |
| 640×480 等效裁切口径（D08） | 79.5° | 63.9° | 1.382 sr |

- **fx 比 sim/real = 1.2071**（H7 迁移尺度风险一阶 ~20%: 用实机经验反推 sim 深度将系统性偏差 +20.7%）
- 立体角形状差注记（03 §5）: 全宽口径总立体角几乎相等（1.361 vs 1.382 sr）, **FOV 差距的实体是纵横比重分配**（sim 4:3 vs 实规格 16:9 全宽/4:3 裁切），非总视场损失; 我方 640×480 口径下 sim 比 real 视场窄 10.35°H/9.22°V（−13.1%/−14.5%）、立体角 −22.4%
- 帧级交叉复核（极线法）缺: 四公开源均无 infra 双目（§2.2）, 显式登记「帧实测缺」

## 证据文件清单

- 帧目录: ~/sitl_sim/vision_inputs/ext_proxy/{fr_stairs_color, fr_stairs_depth, fr_d435i_color}/（各 69-70 帧, manifest 含 camera_info+property）
- 指标: 同目录 metrics_*.json（分位数+D11 CI+分段）
- 脚本（入库 sitl_sim/analysis/）: j3_extract_frames.py / j3_image_metrics.py / j3_fb_residual.py（FB 残差脚本待双目素材解锁后首跑）
- X1img_015950 sim 侧提帧: 避让 T2-WA 基线复读 IO 窗, 排队执行（E7 sim 侧零假设待其完成）

## sim 侧零假设数据（X1img_015950, 2026-09-30 补; 边界=注入前袋）

**σ 直筛裁决读数（M4 调和注记: C12-EXP2 步骤 0 挂本测量, 两簇引用同读数）**: X1img_015950 平坦区帧间 σ̂ pool=P25=**0.0 gray counts（n=67 pair, P90=0.0）**; 平坦区梯度幅值中位=**0.0**（T2-R3无噪声合成图弱纹理梯度严格 0的图像侧直接证据）→ **袋年代门通道二裁决: 注入前袋实锤**（与 dossier 推定一致, 噪声/深度 sim 侧正源挂账维持, E7 曝光/模糊 sim 零假设+纹理对照边界放行口径成立）。

| 指标 | sim（X1img 72 帧双目, 640×480） | 实机参照（样张 color） | 备注 |
|---|---|---|---|
| p_sat | P50=0.0 / P90=0.0 | 0~1.15%(P90) | sim 渲染无削顶 ✓ |
| γ 帧间 | P50=1.0 | 1.0（手动曝光） | 曝光常数零假设**两侧通过**（P6） |
| hist_range P1-P99 | P50=139（帧间恒定） | 112/205（stairs/d435i） | sim 常数序列 ✓ |
| corners_gFT | P50=37/帧 | 117-150/帧@1080p | 分辨率与场景类双重差异, 禁跨类比; sim 123/kpx vs real 56-117/kpx（重正化参考） |
| 梯度方向集中度 | P50=0.200 | 0.098-0.113 | sim 纹理本底方向性 2×（箱阵正交边缘主导, 非运动模糊——H8 实机检验待双目素材） |
| D12 σ̂ | 0.0（注入前实锤） | color 上界 1.16-3.0; IR 正源缺 | |
| FB 时序 pool P90 | 30.7px（爬升瞬态运动主导） | —（待实机双目） | 运动伪差分又一实证, 支持帧间统计必须 P25/静止段口径 |
| FB 立体 pool P90 | 0.71px | — | H6 方向预检: sim 侧时序尾>>立体尾（无 FPN 时反向）, 实机 FPN 检验挂账 |

证据文件: vision_inputs/X1img_j3/（139 帧双目+manifest）; metrics_X1img_sim.json; fb_X1img_sim.json。
工具修正记录: j3_extract_frames 双目同 ts 键碰撞(右目丢失)与 short_of 命名覆盖两 bug 修复; j3_fb_residual OpenCV (N,1,2) 点形状 norm(axis=1) 形状 bug 修复(原输出逐分量绝对值矩阵, 残差虚大 2 倍维度)。
