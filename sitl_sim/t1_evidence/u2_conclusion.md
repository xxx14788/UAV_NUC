# U2 慢连接根因深挖 — 结论(2026-09-28 夜,T1 v4)

证据目录:u2_2026-09-28/ u2v2_2026-09-28/ u2loop_2026-09-28/ + diag_230400/(09-27 夜)
解码器:u2_decode_pcap.py;累积曲线:u2loop_2026-09-28/connect_curve.csv

## a) 洪流解码(flood_live_r11.pcap,21.2s,6000 帧,链活态 283 帧/s)

PX4→mavros(14580→14540)全表(节拍折扣后实测速率 | ONBOARD 默认表值):
ATTITUDE 65.7/s|100, GLOBAL_POSITION_INT 30.5/s|50, HIGHRES_IMU 35.4/s|50,
ATT_QUATERNION 32.8/s|50, LOCAL_POSITION_NED 20.4/s|30, ODOMETRY 20.4/s|30(=232B
协方差大帧的来源,协方差在无 vision 融合前为无效大值), TIMESYNC 8.2/s|10,
~7/s 族(ALTITUDE/ESC_INFO/ESC_STATUS/SERVO_OUTPUT/ATT_TARGET/POS_TARGET/VFR_HUD,表 10),
~3.5/s 族(EXT_SYS_STATE/SYS_STATUS,表 5), ~1Hz 族(GPS_RAW/EST_STATUS/PING/
SYS_TIME/HEARTBEAT/ODID...)。
**归属**:px4-rc.mavlink 对 14580 实例只 `mavlink start -m onboard` 无任何 `mavlink
stream` 配置 → mavlink_main.cpp:1474 configure_streams_to_default() 的 ONBOARD 表
全开。洪流=PX4 默认行为非错配;频率=表值×~0.66(20ms mavlink 节拍折扣,与 W2 一致)。
23:04 退化态 448/s vs 现在 283/s:mavros 未连上时 PX4 全速(不受 partner 协商影响),
连上后部分流被 mavros 请求降频——速率差是连接状态的表征不是病根。
HEARTBEAT 恒在流中(~1Hz)→ 慢连时 mavros 必收得到心跳,**停滞在 mavros 进程侧处理链**。

## b) 端口拓扑(v1.17 实测+源码)

px4-rc.mavlink:GCS=18570(-f 谁来学谁)、offboard=14580 监听→固定发 14540、
payload=14280→14030、gimbal=13030→13280。
**14557 溯源**:2018-09-10 7f016b5fd4 之前 PX4 offboard local=14557+instance、
GCS=14556;该提交改 14580/18570(多机端口防重叠)。sitl_sim/02 的
`udp://:14540@127.0.0.1:14557` 抄的是 2018 前老约定(mavros 官方 px4.launch 默认是
/dev/ttyACM0:57600,14557 亦非 mavros 默认)。
**为何"碰巧能用"**:libmavconn udp.cpp do_recvfrom 用 boost async_receive_from 的
in-out endpoint,收到 PX4 首包后 remote_ep 被内核覆写为 127.0.0.1:14580 并打
"Remote address" 日志,此后全部上行直达 14580。首包前(实测 29 包)上行全进黑洞。
tcpdump 23:04 实证:mavros→14580 5196 包 vs mavros→14557 29 包。
**修复**:fcu_url 全量改 14580(sitl_sim 02/smoke/t3_verify/test×10 处,含仓库拷贝)。

## c) Time jump 机制(伴生症状,不阻塞连接)

sys_time.cpp add_timesync_observation():filter 收敛后连续 max_cons_high_deviation(5)
次偏差>max_deviation_sample(100ms)→ "TM : Time jump detected. Resetting"→reset_filter
→ 重收敛需 convergence_window=500 样本 @timesync_rate 10Hz = 50s + 5 次违规 0.5s
= **50.6s 周期,与 16:35 PASS 轮五连跳间隔 50.600s 完全吻合**。PASS 轮同样刷屏 →
与 connected 无因果(它只 set_time_offset,connected 判定在 sys_status handle_heartbeat
→ UAS::update_connection_status,sys_time 不参与)。sim-time lockstep 下 RTT/偏差
估计系统性超标是常态,刷屏是噪音不是病。

## d) 二态性(同 master 第二 boot 复发)——干净环境不可复现

今晚数据:v1(纯 PX4+mavros)4 boot 1.1-2.0s;v2(深度 SITL+mavros+px4ctrl,kill -9
清场复刻白天)5 boot 2.7-3.0s;u2loop(同 v2 拓扑,单 master 40 连 boot)曲线平稳
(见 connect_curve.csv,r10 为 gzserver 偶发起慢,与 connect 无关)。
**结论修正**:09-27 的"同 master 第二 boot 复发"观察全部来自当日 70+ boot 的 NUC
(当天 master 进程+Xvfb+多 agent 会话的累积态);23:16 NUC 重启后未再复现,今晚
~50 连 boot 亦不复现。病根载体=重启才可清的全局状态(进程内累积,非注册表单独),
按"每卡 30 分钟换略"纪律不再盲试复现;fresh-master 清场保留为 smoke 标配兜底,
但 README_runtime 注明其真实边界(见 e)。

## e) 修复清单

1. fcu_url 14557→14580(已改,待验收 u2_verify_fix:连续 3 boot ≤10s)。
2. 洪流不治理:ONBOARD 默认表是 PX4 设计行为,283 帧/s × 平均 ~60B 对 NUC lo 无压力;
   若未来要提频(200Hz IMU 走 mavlink)按 W2 结论仍不可达,与洪流无关。
3. fresh-master(smoke 清场)保留;04_takeoff 20s 长窗保留为保险(U3 定案后复核降级)。
