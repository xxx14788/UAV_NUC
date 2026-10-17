# 失控族根因定案（B 轨交付；帧级三源证据=G1 flight.bag；2026-10-17 夜）

## 一、旧判证伪

v8.3/tune_diag_report 初判"悬停膨胀推挤族"——**证伪**：position_cmd 全程钉死 (4.20,4.11,1.00)（planner 零推挤零重发）；grid_map 膨胀域未作用于悬停定点。悬停时长亦非触发因子（干净轮 F1/F4/F5 悬停 58-62s 降落成功）。

## 二、帧级时序链（G1 标本，bag t0=truth 首帧）

| t | 事件 | 证据 |
|---|---|---|
| 70.64 | 到位→planner 停发 cmd（cmd_recv 1→0）→px4ctrl AUTO_HOVER | /debugPx4ctrl/fsm_state |
| ~79.1 | vins_smoke 发 LAND→px4ctrl AUTO_LAND；**thrust 单帧 0.709→0.655** | setpoint_raw/attitude 帧级（79.128） |
| 79.18 | 下降开始（vz 转折，终端 -0.5m/s=降推平衡非自由落体） | imu_propagate 帧级 |
| 81-82 | 近地（truth z 0.2-0.6） | model_states |
| 83.09 | 固件 OFFBOARD→AUTO.LOITER（setpoint 断>0.5s） | mavros/state |
| 83.76-85.78 | MANUAL_CTRL(1s)→AUTO_HOVER→再 AUTO_LAND（降落中断闪断） | fsm_state |
| 85+ | **VINS odom z 负漂**（0.2→-8.7m）与 truth（飞逃→+12.8m）分叉 | imu_propagate vs model_states |
| 90-160 | 正反馈飞逃：px4ctrl 追 odom 系定点（cmd 钉 1.0 vs odom -8.7）→物理拉高+水平漂（-610m/z72m，物理求解爆域 vmax 80km/s） | tune_diag 分段 |

## 三、机制定案

**失控=降落段近地 VINS 崩溃放大链**：AUTO_LAND 下降至近地（z<0.6）→视场退化（地面占视野+贴箱面 0.4m 级巨视差）→VINS z 负漂→降落中断闪断→AUTO_HOVER 追漂移 odom 目标→闭环正反馈飞逃。触发面=**降落过程**（非悬停窗/非导航栈/非 inflation）；概率族 6/11（G1 悬停点 box_min surf=0.375-0.476 与干净轮无清晰分离=边缘态概率触发）。

## 四、批内验证面（pilot/确证批对照）

1. 失控轮 FSM 序列同型性（AUTO_LAND→中断→AUTO_HOVER→飞逃）应 6/6 复现
2. VINS 漂移起点应在 AUTO_LAND 后 z<0.6 段（非悬停段）
3. 干净轮降落段 odom 全程稳（对照）

## 五、修复面登记（跨域禁顺手修；本会话不动栈）

- 候选 A：px4ctrl 漂移看门（现有 HAFIX=odom 死流看门；本族=流活漂移爆——需 |odom-truth| 型或加速度门，实机同益）
- 候选 B：LAND 段 VINS 保护（近地 odom 门/降落直接 kill 短路径——实机手册 LAND 坑同源）
- 候选 C：goal 微调远离箱面（杠杆 3 ±0.2m 授权域内效果存疑，箱距 0.4→0.6 级）

## 六、批内对照验证（pilot V86P3，2026-10-17 夜）

- **FSM 序列同型 7/7 关键节点**：到位 70.65 cmd 停→AUTO_HOVER→79.73 AUTO_LAND→83.76 MANUAL_CTRL 中断（odom_recv=0 一闪）→86.78 AUTO_HOVER（追漂移目标）→87.80 再 AUTO_LAND→183.60 MANUAL（VINS 死流）→飞逃 z_max=95.06m。与 G1 标本时点特征一致（到位后 ~9s 降落链启动）。
- 假说 H-RUN 批内成立：触发面=降落段（非悬停窗）。
