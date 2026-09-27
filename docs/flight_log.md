# 飞行 / 仿真实验记录

每次 SITL 或实机飞行后追加一行。bag 存 `~/sitl_sim/bags/`（不入库），记录入库。
格式：`日期 | bag 文件 | 时长 | 链路（仿真（SITL）/实机，必填其一）| 结果 | 异常/备注`

| 日期 | bag | 时长 | 链路 | 结果 | 备注 |
|---|---|---|---|---|---|
| 2026-09-23 | flight_2026-09-23_212510.bag | — | 仿真（SITL）控制回路（01–06） | 成功 | 起飞→悬停→降落 |
| 2026-09-23 | flight_2026-09-23_214433.bag | — | 仿真（SITL）控制回路 | 成功 | 同上 |
| 2026-09-23 | flight_2026-09-23_221002.bag | 106s | 仿真（SITL）控制回路 | 成功 | px4ctrl 100Hz 姿态控制，mavros EKF2 里程计；无 planner |
| 2026-09-26 | flight_2026-09-26_175942.bag | 231s | 仿真（SITL）控制回路（A1 复验） | 成功 | 起飞→悬停55s（xy漂移<2.2cm，z±2cm）→自动降落disarm；9-26文档提交后环境无退化 |
| 2026-09-26 | flight_2026-09-26_195352.bag | ~10min | 仿真（SITL）全链路 A4（planner 首次闭环） | 成功 | EGO-Planner→traj_server→px4ctrl 首通；goal(5,-3,1)到位误差0.10m；/position_cmd 100.6Hz；到位后悬停60s+不超时；修复grid_map边界segfault与traj_server到点停发两处上游bug |
| 2026-09-26 | flight_2026-09-26_202121.bag | ~7min | 仿真（SITL）避障 A5（3箱world，goal(7,-4,1)） | 成功 | 绕障到位0.080m;最小障碍距离0.368m>阈值0.349m;跟踪p95=0.346m延迟15ms;速度峰值0.75m/s超限观察项;分析图docs/analysis/flight_2026-09-26_202121.png |
| 2026-09-26 | flight_2026-09-26_{202121,204338,205817}.bag | 各~7min | 仿真（SITL）A6 三连飞（goal(7,-4)/(7,-4)/(8,-1)） | 3/3成功 | 到位0.080/0.080/0.072m;避障最小距离0.368/0.405/0.879m(阈值0.349);跟踪p95=0.346/0.259/0.133m;延迟15/15/16ms;速度峰值1.35m/s超限(观察项);另2次失败轮=从障碍区侧起飞致EGO初始轨迹发散(次日待议) |
| 2026-09-26 | flight_2026-09-26_220814/224815/230126.bag | — | 仿真（SITL）A7 VINS 并行验证 | 阻塞 | VINS 静止正常、运动即发散；show_track=0/在线外参均未解决；vision_pose 发散拖崩 EKF2 致机体翻转（教训：SITL 接 VINS 需健康门控）；资产已入库，卡点记录次日待议 |

| 2026-09-27 | ~/sitl_sim/t1_evidence/(无bag,现场日志) | ~6h | 仿真（SITL） | T1 排障日:px4ctrl 断连卡死根因三连实证(gdb 冻结栈/AUTO_TAKEOFF 死角/投递窗口),repro+恢复3/3 |
| 2026-09-27 | ~/sitl_sim/smoke_runs/run_2026-09-27_165340/flight.bag | ~90s | 仿真（SITL） | T1 smoke#1 FAIL:残留空场会话致避障判定全0(轨迹本身0.049m到位/100Hz/disarm均过) |
| 2026-09-27 | ~/sitl_sim/smoke_runs/run_2026-09-27_171440/flight.bag | ~110s | 仿真（SITL） | T1 smoke#3 PASS 四指标:到位0.166m/避障0.552m/poscmd 100.2Hz/自动disarm(F1-F5修复版基线) |
| 2026-09-27 | t2_A~E (t2_*.bag) | 各30-65s | W2 激励录制: 静置+起飞悬停/慢巡航/冲刺/纯yaw/降落, OFFBOARD 直控 | 传感器数据完整, 用途=W1 同步检验+W3 矩阵 |
| 2026-09-27 | t2w5_p1_210129 | ~250s | W5-1 并行 ATE: EKF2 控制+VINS 旁观 | VINS 因时间域分裂无法 init(后修复配方); goal 到位失败(7.04m, 规划链问题) |
| 2026-09-27 | t2w5_p2_215545 | ~160s | W5-2 VINS 闭环首通: sim 域统一配方 | VINS 在线 init 成功+门控转发 1320 帧; 机动段 VINS 漂移 60m; 无异常降落 |
| 2026-09-27 | ~/sitl_sim/smoke_runs/run_2026-09-27_181440/flight.bag | ~110s | 仿真（SITL） | T1 smoke5 FAIL:T3栈+relay v1;est偏航错位致穿箱(min_dist 0.214/vel 788m/s接触爆炸) |
| 2026-09-27 | ~/sitl_sim/smoke_runs/run_2026-09-27_182104/flight.bag | ~110s | 仿真（SITL） | T1 归因对照轮(HEAD栈+relay v1)FAIL:同签名→排除T3栈,relay v1存疑 |
| 2026-09-27 | ~/sitl_sim/smoke_runs/run_2026-09-27_193052/flight.bag | ~110s | 仿真（SITL） | T1 smoke10(HEAD栈+relay v2)FAIL:同穿箱签名→疑环境性致盲 |
| 2026-09-27 | ~/sitl_sim/smoke_runs/run_2026-09-27_193748/flight.bag | ~100s | 仿真（SITL） | T1 HEAD栈+relay v2:飞行机构完美(1轮起飞/40s到点/干净降落)但穿箱(B/C=0.000);终版归因=磁校准污染(est偏航错位),非relay |
| 2026-09-27 | ~/sitl_sim/smoke_runs/run_2026-09-27_194855/flight.bag | ~110s | 仿真（SITL） | T1 Xvfb重启终验FAIL:Xvfb重启不愈;夜间进一步退化为mavros连接延迟5-7分钟(22:4x三轮),认证移交次日清洁环境(runbook:t1_evidence/w4_cert_runbook.md) |
