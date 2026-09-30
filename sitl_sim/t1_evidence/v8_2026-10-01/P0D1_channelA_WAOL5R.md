# P0-D.1：通道A 袋戳差延迟账·WAOL5R 袋（T1 v8.0 夜1，2026-10-01）

素材：run_WAOL5R_222234/flight.bag（148MB，272.6s，在线录制，全图 use_sim_time=true）。
工具：sitl_sim/analysis/t1_latency_channelA.py（rosbag API 直读；禁 echo/禁回放域均守）。
原始数：WAOL5R_channelA_latency.json。C10-X2 采集项①③④⑤⑧落地；⑦桥对齐因袋内无
/mavros/imu/data（仅 data_raw）登记缺口；②链B=lp 流已测。

## 1. 主结果（袋原生域=sim 域；rtf_bagtime_sim=1.000 实证）

| 流 | n | 率 | 戳差 p50/p95/p99/max (ms) | 到达间隔 p50/p95/max (ms) |
|---|---|---|---|---|
| prop 直供链 /vins_estimator/imu_propagate | 57027 | 209Hz | **12 / 36 / 40 / 52**（min=−8） | 4 / 44 / 52（正间隔仅 18551/57027） |
| odom /vins_estimator/odometry | 2621 | 9.6Hz | 52 / 76 / 88 / 100 | 104 / 140 / 188 |
| 链B /mavros/local_position/odom | 8179 | **31.25Hz**（stamp dt p50=32ms） | 0 / …（stamp 在源头生成 ⇒ 假零，E13 警戒态，不作延迟证据） | — |
| imu /mavros/imu/data_raw | 57028 | 209Hz | 12 / 20（max 20） | — |
| /clock | 68157 | 250Hz | dt 全程精确 4.0ms（lockstep 网格完美均匀） | — |

解龄代理（prop 戳落后"已见最新 IMU 戳"）：p50=12/p95=36/max=52ms——与 prop 戳差同分布
（同量化世界支配，独立信息量有限，如实登记）。

## 2. 测量效度判定（P3 方法自检线的执行）

1. **bag 时间=sim 域**（clock-RTF=1.000 精确 + lp 假零 + 全部值 4ms 网格化）⟹ 全表为
   sim 域读数；控制环自身运行在 sim 域，PM 公式代入用 sim 域口径正确，无需墙钟归一
   （墙侧 RTF 无袋内通道，round.log 粗估 ~0.9-1.0 量级，仅记档）。
2. **录制侧批处理污染（主效度限制）**：prop 正到达间隔仅 18551/57027（32.5%），且
   戳差 min=−8ms（物理不可能为负 ⟹ 纯量化伪影）；bag_t 有效推进率 ~68Hz << /clock 250Hz
   ⟹ recorder 以批处理节拍打戳，**测量地板 ≈15ms（272.6s/18551）**。
3. 结论：**p50=12ms 处于地板量级（真值区间约 4-12ms）；p95=36ms 无法据此认证**
   （区间 8-36ms）。P2 判据线（p95≤15ms ⇒ PM≥30°）**本袋不可判**——非数据矛盾，
   是通道A 在该录制管线下分辨力不足。
4. 拥塞签名缺席（P3）：无丢最老/无 /clock 回退/IMU dt p99=12ms 健康 ⟹ 传输面无病态，
   尾部形状归 recorder 批处理而非网络拥塞。

## 3. 判读与去向

- **τ_pipe 终裁升级通道B**（P0-D.2：Px4ctrlDebug.msg 加 odom_delay/odom_staleness，与
  T3-Z1.2 接线合并 build 窗）——px4ctrl 消费侧逐条真实延迟，不受 recorder 批处理污染。
- **意外收获（供 C01/E1-D4，X3 共享勿双做）**：链B local_position/odom 实测 31.25Hz
  ≈30Hz 整 ⟹ C10-P6 预言的"S12 限流折扣至 ~20Hz"**未生效**，须查 mavros
  SET_MESSAGE_INTERVAL 实值（X3 三件套：rostopic hz+param show+ulog "EV data too fast"计数）。
- odom 流 52/76ms（solver 输出滞后）为 VINS 侧解龄账输入，供 C02 慢漂三分解共享。
- RTF 同窗记录义务：袋内无墙钟通道（上述 §2.1），round.log 粗估已记，正式 RTF 待
  通道B 轮（debug 流墙钟戳）补齐。

## 4. 供给面登记

- 后续 W-C2/X 线新栈袋：同脚本一行复算（脚本入库）；建议 T2/T3 录制清单补
  /mavros/imu/data（33Hz 姿态臂）以解锁采集项⑦桥延迟对齐。
