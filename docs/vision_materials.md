# VINS 链路可视化材料规范（T4-J1，2026-09-29）

> 判读对象 = VINS 纯视觉链路全链路证据（README §0 R1-R6 架构裁定后）。
> 本文替代 v1 的"GPS 代位链路截图"清单。素材>50KB 才有效；轮次命名对齐 t3_runs/vins_smoke_runs。

## 1. 每轮截图清单（rviz 常驻，飞行会话执行）

前置（一次）: `DISPLAY=:99 nohup rviz -c ~/sitl_sim/b0_headless_vins.rviz &`
（VINS 链专用配置入库 `sitl_sim/b0_headless_vins.rviz`：/vins_estimator/feature_pts 特征点云 3px
 + /vins_estimator/imu_propagate odom + grid_map/bspline 保留；深度链判读仍用 b0_headless.rviz）

每场景轮 ≥3 张（用 `snap_rviz.sh <前缀>`，输出 vision_inputs/<前缀>_HHMMSS.png）：
| 时点 | 前缀约定 | 判读用途 |
|---|---|---|
| 起飞后 5s | `<轮名>_tk` | 特征初始化/近地面分布 |
| 巡航中段（goal 后 ~10s） | `<轮名>_cr` | 特征跟踪连续性/障碍面覆盖 |
| 到位悬停（arrive 后） | `<轮名>_ar` | 终段特征密度/轨迹一致性 |

## 2. bag 提帧管线（判读侧离线执行，不占锁）

- 时刻对齐: `analysis/bag_extract_moments.py <bag> [--tag 轮名]`
  自动定位 takeoff/goal/anchor(goal+5s,与 round_result 同口径)/land 四时刻，
  ±0.3s 窗配对双目帧 → `vision_inputs/<轮名>/moment_*.png + moments.json`
- 均布对照(跨帧同步质量/视差统计): `analysis/bag_extract_stereo.py <bag> --n 6 --out vision_inputs/<轮名>/`
- 目录规范: `vision_inputs/<轮名>/`（轮名对齐 run_ 目录名）;rviz 截图与提帧产物同目录混放,文件名前缀区分

## 3. J1.3 特征密度抽样规范（补 v1"样本不足"欠账）

- 样本: ≥5 轮带 feature_pts 的轮（X1img 类带图轮;紧凑轮无图像不可用）
- 数值化: 分区点密度统计——障碍面/地面/空域三区,输出 点/m²
  （区划分: goal 航线上障碍盒 AABB 膨胀 0.5m = 障碍面; z<0.1m 带内 = 地面; 其余 = 空域）
- 判读产物: docs/t4_verdicts_v2.md 增量章（数值锚定,禁"看起来"）

## 4. 素材就绪判据与错峰

- 就绪 = ≥5 轮 {rviz 3 张 + 带图 bag} 或 {带图 bag + moments 提帧}
- 素材未齐: T4 全力 E 线;素材到货(STATUS 通告): 24h 内出判读结论
