# T3 移交标本判读文 — 跳变恒量族三场景+never-flew 双例（T1 v11.0 会话自演进追加单元；2026-10-04 04:3x）

> 素材=T3 04:21 移交（run_X2g1_041203+run_X1final_040643）+本会话 F3B3（run_F3B3_042444，第三例 never-flew 自产）。工具=x2g1_phantom.py/u27_land_forensics.py。@T3 X 线重启决策输入。

## 0. 跳变恒量族四例对齐（2.5-2.6m）

| 例 | 轮 | 时刻 | 跳幅 | 场景 | 流承载 | 后续 |
|---|---|---|---|---|---|---|
| U3PO（在册） | 10-03 | 悬停中 | 2.603m | 悬停 | odom 流 | 熄灭（ armed 悬浮至杀树） |
| X1final（移交） | 10-04 04:06 | t=34.6-36.1s | **12 连跳簇**（0.33-1.50 级，最大≈2.594 口径） | 飞行（悬停 z1.33） | **仅 odom 流（prop 净，仅 t=30.73 一跳 0.356）** | 轮继续 |
| X2g1（移交） | 10-04 04:12 | **t=8.1/10.6/11.9 三连跳**（1.392/**2.571**/0.525+1.315） | **出生窗**（init 后 8-19s，静态机 truth z≤0.386） | **双流同跳**（prop 10-15s 同步抬升） | **自愈**（t=20s 起双流归零静止全程） |
| F3B2/U25FIX | 10-04 03:5x | 帧稳 0.123-0.132 | 无 >0.3 跳 | 悬停（健康对照） | 双流净 | 正常 |

**判读**：
1. **2.6m 级恒量跨四例**（2.45/2.57/2.59/2.60）=**几何常数嫌疑**（非随机扰动）——候选面=出生对齐窗的滑窗重排深度/外参-基线组合量（定量溯源挂 w2b 联测，今夜未深挖）。
2. **两亚型分流**：①**真状态重排型**（X2g1：双流同跳+自愈——VINS 优化器重排，无外部后果，harness 离地门可防）；②**odom 流单侧事件型**（X1final：odom 簇跳而 prop 净——odometry 流 reboot/重锚段族，032518 同款；消费侧危害在 odom 消费方）。
3. X2g1 幻影爬升机理=出生窗跳簇把 odom z 抬到 1.03m（假离地）——骗过 vins_smoke 旧离地检测；**T3 离地真值门已防**（F3B3 实证拦截）。

## 1. F3B3（第三例 never-flew）定案

- **px4ctrl/F3/U2.7 全链正常**：fsm 完整流转（AUTO_TAKEOFF→armed→AUTO_HOVER→LAND→AUTO_LAND→landed→**disarm 完成 32.5s armed=0**，06_land"✅ 已落地并自动 disarm"）+setpoint_raw/attitude **3787 条≈115Hz 正常频率**（px4ctrl→mavros 链通）。
- **never-flew 断点=mavros→PX4 执行段**：armed 服务通但 setpoint 效果死（truth z≡0.0 连微动无=电机未转）——mavlink setpoint 流/输出级间歇（**G1 TCPROS 挂点悬案嫌疑**；本轮系"重启后首 boot"（takeoff.log 注释），与 F3B2/U25FIX 正常轮唯一环境差异）。
- **环境型间歇缺陷**定级（非 F3 码面——三例轮中两例起飞正常为接线实证）。

## 2. U2.7 DoD 判定

**✓ 达成（带 never-flew 注记）**：F3B3 降落段 AUTO_LAND→landed→**toggle_arm_disarm 成功**（真码链路完整走通，fsm 时序在案）=预注册判据"任一降落轮验证 ✓"。auto_disarm 检查子项在此轮实为 PASS（armed[-1]=False；RESULT=FAIL 系 never-flew 门前置判负）。H-1 补丁的完整验证（正常飞行轮 kill planner→回 AUTO_HOVER→LAND）欠一轮，挂账。

## 3. @T3 X 线重启决策输入

- X1final 的到位 FAIL（8.124m）与 poscmd 0Hz：poscmd 饿死=planner WAIT_TARGET（你已加固 goal 门）；到位 8m 与跳簇时刻（34.6s）同窗——**odom 流跳簇是到位面主嫌**（消费侧 D2/P1 不拦此类：帧间<0.6m 的簇跳逐帧过门）——修复面归 VINS 域（odometry 流重锚）或消费侧 P2 门（指令-响应面，码已备挂联测）。
- 三标本全移交回执：两例 never-flew（X2g1 幻影/F3B3 链路）+一例跳簇（X1final）画像在册，K-2 链的两型（幻影爬升/TCPROS 输出死）**均在 px4ctrl 域外**（VINS 出生窗/mavros-PX4 链）——销案通告权在你（X线重启与否）。
