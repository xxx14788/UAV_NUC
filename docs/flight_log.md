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
| 2026-09-28 | u3v2/u3v3/u3v4 (t1_evidence/) | 各~30s | 仿真(SITL) | T1-U3 投递停滞矩阵:baseline/成功轮 armed 1.8-3.8s;新pub→px4ctrl TCPROS 随机失败~50%(稳态也有),机制档案 u3_conclusion.md |
| 2026-09-28 | u4_2026-09-28 (t1_evidence/) | ~60s | 仿真(SITL) | T1-U4b 磁复发实验:sitl_north+默认world 各一轮起飞;实证复位未save,DECL 195°复发,根治=DECL_TYPE=1 |
| 2026-09-28 | smoke_runs/run_2026-09-28_021048/flight.bag | ~110s | 仿真(SITL) | T1-U5 轮A(relay off)PASS 六指标:到位0.177/避障0.432/poscmd100.2/disarm/yaw -0.51°/depth 13.2Hz |
| 2026-09-28 | smoke_runs/run_2026-09-28_021506,021949/flight.bag | ~110s | 仿真(SITL) | T1-U5 轮B(relay on v2 override)FAIL×2:末端震荡 stable_n=0(arrival 1.009/0.743);后归因多agent争抢污染(排他窗对照) |
| 2026-09-28 | smoke_runs/run_2026-09-28_023213,023658/flight.bag | ~110s | 仿真(SITL) | T1-U5 轮B(relay on v3 独立话题,排他窗)PASS×2:到位0.225/0.231,六指标全绿,W4认证完成 |
| 2026-09-28 | u6_2026-09-28 (t1_evidence/) | 0 | 仿真(SITL) | T1-U6.2 恢复测试 0/3 环境作废(与T3 W7撞窗,px4ctrl被正当清场;致歉记录见 STATUS 02:58) |

| 2026-09-28 | t2_A_60hz320.bag | 53.9s | 仿真（SITL）T2b-E18 R1（60Hz/320×240 变体） | 成功 | 送达 23.5Hz；原生 sim 域；flyer rc=0 |
| 2026-09-28 | t2_C_60hz320.bag | 26.5s | 仿真（SITL）T2b-E18 R1 | 成功 | 送达 23.9Hz；重放 C 段 150m（分辨率灾难，视差精度主导） |
| 2026-09-28 | t2_A_60hz640.bag | 54.7s | 仿真（SITL）T2b-E18 R2（60Hz/640×480 变体） | 成功 | 送达 22.3Hz；重放 A 段 0.070m（基线 0.137，−49%） |
| 2026-09-28 | t2_C_60hz640.bag | 36.4s | 仿真（SITL）T2b-E18 R2 | 成功 | 送达 21.9Hz；重放 C 段 14.4m@15.9s（基线 31.3@6.7，−54%）；SDF 录后还原 30Hz 基线 |
| 2026-09-28 | t2v3_ground_202520.bag | ~45s | 仿真（SITL）T2-W1.1 地面轮(VINS 链,未起飞) | 成功 | preflight 全绿;T1 共享分析:imu_propagate 125Hz 零断流,静态漂移 2-3cm/45s |
| 2026-09-28 | t2v3_hover_203248.bag | ~71s | 仿真（SITL）T2-W1.2 悬停轮(VINS odom 直供 px4ctrl,起飞0.75m+悬停30s+降) | 成功 | T1 共享分析(V1.3):悬停保持中位 0.005m/max 0.021m,优于 0.03m 基线与 EKF2 参照 0.050m;全程 125Hz 无断流 |
| 2026-09-28 | t2v3_route_203830.bag(active) | ~2min | 仿真（SITL）T2-W1.3 航线轮(VINS 链) | 失败 | 20:40 链崩(gzserver/px4 逝,sitl log 尾=Connection closed by client),bag 停写;残锁至 21:00 由 T1 清;T2 侧归因待其台账 |
| 2026-09-28 | v1_ground_salvage_211520.bag | 67s | 仿真（SITL）T1-v5 V1.2 地面静态轮(VINS 链,未起飞;双 T1 实例同链打捞) | 成功 | fsm_state 67 帧零跳变(odom_recv=1 恒);静态游走 12.6cm 包络零均值;V4.2 三档 50/125/215Hz |
| 2026-09-29 | run_WD1b_032925/flight.bag | ~3min | 仿真（SITL）T1-v6.1 W-D1b（D1 修复验证轮，VINS 平滑重锚+odom 门首飞） | 失败（T2 域） | VINS t=32s 瞬态发散死亡（重启后首轮锚偏类，17.3m 帧跳变，X1 轮 10 同款第 9 次复现）；**活窗（重锚期）零尖峰零阶跃 \|v\|<0.5 = D1 修复实飞 PASS**；死窗 1215 尖峰属纯传播爬升（\|v\|→49.91 被 T2 发布端 50 线防线截停）；**D2 门实战首验：实拒 200+ 帧，三层依序 ACC(\|v\|=0.26)→JUMP→VEL，px4ctrl 零毒值摄入** |
| 2026-09-29 | run_WD1b_033751/flight.bag | ~7min | 仿真（SITL）T1-v6.1 W-D1c（W-D1 全指标重试） | ENV-FAIL | gazebo/px4 轮中死亡（环境性，E4.2 口径不计飞行预算）；leg1 真值 7.4m 未达；与 T3 重放矩阵并发期环境不稳 |
