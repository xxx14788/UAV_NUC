# U3′ 矩阵重跑预注册（prereg_u3p）

- 写表时刻：2026-10-01 21:05（实钟），五轮全部开跑之前（零 U3′ 数据产生）
- 前置自检：①R2 定案（04d1a73）✓ ②C-5 实质=三重验证在册（vins_smoke.sh:144-145 命令行+T3 20:59 确认 18:36 双副本落地 md5 对齐+今日 U7OL1 袋实证 imu/data 17753 msgs/attitude 35624 msgs）；T1 形式签认因其 20:55 收口离场未到，按用户「解锁即继续」指令起飞，**签认追溯条款：T1 归位后一字补签入 STATUS 即闭合** ③磁盘 df 70G≥65G ✓
- 栈与口径：**凭据栈=285278cc（U7 已证无害，README §3 登记）**；GPS 口径=无任何 EKF2 注入（SITL 默认 GPS 喂 EKF2 保持）；全带图（VINS_SMOKE_IMAGES=1 / t2v3_flight.sh 带图已补）+探针链默认（REANCHOR_DEBUG=1）；袋保全=帧包正源+tag 轮保全（用户裁定）

## 轮次规格（5 轮，顺序=风险递增）

| # | tag | 载具 | 规格 |
|---|---|---|---|
| U3PG | ground | t2v3_flight.sh ground | 静置 40s 不起飞 |
| U3PH | hover | vins_smoke | --world sitl_world_obstacles --goal 0 0 1 --budget 120 |
| U3PO | obstacles | vins_smoke | --world sitl_world_obstacles --goal 7 -4 1 --budget 180 |
| U3PR1 | route leg1+leg2 | t2v3_flight.sh route | goal(3,-2,1)→(0,0,1) |
| U3PR2 | route 重跑 | 同上 | 同上 |

## 判据（写死，先于飞行）

1. **VINS 域（生死主判据）**：每轮 simvins.log/vins.log 零 `[T2fail]` 且零 reboot=PASS；有 fail=FAIL-VINS（记时刻/形态；按 R2 框架归类：场景载体型〔P 跑飞+平静偏置+落历史时点带〕vs 新形态〔即刻停跑转分析〕）。
2. **四指标双口径**：round_result.sh RESULT 正源（T3 e7120e0 场景自动分门：obstacles 门 0.75/其余 0.5；J0 锚差恒门 0.5 不分门）。
3. **J0 修订口径**：raw==0 且 smj≤10（/position_cmd 链数据落袋供 T3 判读，非本轮现场判）。
4. **出生点对齐**：VINS odom vs /gazebo/model_states 平移对齐（U9 口径）后算 ATE；未对齐原始值并列上报。
5. **到位统计（场景分门供 X 线）**：每轮 truth/VINS 双口径 min_d 入表；CI 不足自动 +6 轮（同场景族，禁无目的加轮）。
6. **跳变计数 @T1**：袋内 imu_propagate/odometry 流的 dP 尖峰与 |v|>1.15 计数（交付件，不卡本轮门）。
7. **ENV-FAIL 三签名**：gazebo 崩（Connection closed 类）/时钟回退/mavros 断连 → 不计预算原样重跑；**连续 2 轮同因 ENV 失败即停跑转分析**（今夜 20:47 已有一来历不明 route 轮 gazebo 崩前科，route 两轮为 ENV 风险高点）。
8. **U3′ 达标门**：5 轮 VINS 域全零 failure → U4 通告条件成立；任一轮 FAIL-VINS=如实上报（场景载体型按分门口径入统计，新形态=停矩阵转 R3 分析）。
