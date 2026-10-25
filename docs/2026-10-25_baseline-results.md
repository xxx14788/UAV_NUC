# 本机基线结果（2026-10-25）

运行批次：`20261025T124429Z`；容器镜像：`sha256:4197b842d1bed9baed20e1cf5c943e29a245f392157fdd3d8a34e3a51fbf2bb3`；代码 HEAD：`525e4c2380966956fd5fa11ad0694f112d7af811`。默认 headless、Gazebo 深度、无 GPU 配置变更、无 SGBM 桥接、无 R7；每类只跑 1 次，结果是本机锚行，不是成功率估计。

## 结果

| 工况 | 采样窗 | 测量窗 | 关键结果 | 起降/任务判定 |
|---|---:|---|---|---|
| 静态地面 | 40s wall | 完整，RTF=0.9995 | 左右图像各 19.16Hz；stamp dt p50=64ms、p95=68ms；精确双目配对率 100%；标称30Hz周期缺帧估计约35.95%；IMU arrival 214.02Hz | 不解锁；仅测传感器 |
| 纯悬停 | 40s wall | 完整，RTF=0.9994 | 左右图像各 19.14Hz；精确双目配对率 100%；真值相对窗首位移 max=0.026m、p95=0.021m；窗口内保持 armed | 起飞观察到 zmax=0.990m；正常降落 z_end=0.105m；disarm；`HOVER-BASELINE-PASS` |
| 导航 | 180s wall | 完整，RTF=0.9993 | 左右图像 19.22Hz；精确双目配对率 100%；完整收到 180s 采样；目标 `(7,-4,1)` 的真值最小距离 5.386m | 正常降落 z_end=0.105m、disarm；导航任务 `RESULT=FAIL`（未到位），不是测量窗失败 |

## 解释边界

- 图像实际送达/时间戳约 19.1–19.2Hz，而模型参数标称 30Hz；这已经是当前默认 headless 基线的实测差异。其原因尚未归因到某个单独环节。
- 左右图像在本轮完全同戳配对；这只说明观测到的两路消息 stamp 一致，不证明真实曝光、渲染和投递链完全同构。
- IMU 与 `/vins_estimator/imu_propagate` 观测到 4ms 主周期，但有重复时间戳；因此消息到达率不能直接当作独立时间采样率，后续应把重复戳作为单独指标。
- `clock - stamp` 只作同机观测年龄代理，不解释成端到端物理延迟。RTF 约 1 表示本次仿真跟随 wall clock，不能推出 GPU 加速收益。
- 导航失败只证明本次默认目标在当前基线下未到位；不能据单轮确定 VINS、规划器或某一个组件是唯一病因。历史判读的 `min_dist` 不是本次独立安全结论。

## 证据位置

- 摘要与指纹：`runtime/baselines/20261025T124429Z/`（gitignored）
- 静态轮：`runtime/sitl_sim/vins_smoke_runs/run_BASELINE_20261025T124429Z_static_124457/`
- 悬停轮：`runtime/sitl_sim/vins_smoke_runs/run_BASELINE_20261025T124429Z_hover_124610/`
- 导航轮：`runtime/sitl_sim/vins_smoke_runs/run_BASELINE_20261025T124429Z_nav_124829/`
- 预注册协议：`docs/2026-10-25_baseline-protocol.md`

本轮结论：默认 headless 仿真器 RTF 接近 1，但双目消息实际约 19Hz；纯悬停在 40 秒窗内保持稳定并完成起降；默认长目标导航本轮未到位。下一步仍应先分析这组基线的测量口径与时序数据，再决定是否单独做仿真器 GPU 加速对照。
