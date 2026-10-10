# C-1 MAVLink kill 路径源码级定位文书 v1.0（2026-10-11 01:1x——工程合并册单元 4B）

任务书原文：「179+21196 ACK-无操作断链的 Commander 源码定位（事件面 vs 函数体
断链分离点）+源码级结论（可软件复现则 SITL 验证轮）；盲降已兜住，此件=备份梯
闭环+呈报件加硬」。

## 1. 静态源码穷举（PX4 d6f12ad1c4，二进制=源码实证一致）

ulog ver_sw=d6f12ad1c4f70ad3230afd7d86e971421e02fef4=树 HEAD；工作区 Commander
侧干净（仅 airframe/gazebo 配置本地改动）；08_24_40.ulg 原始数据本件复验：

- vehicle_command：412× 179（param1=0/param2=21196，t=114.2-526.9s，
  target=1/1，source=1/240 mavros，from_external=1）
- vehicle_command_ack：412× result=0（ACCEPTED），from_external=0，
  target=1/240（回 mavros）
- vehicle_status.arming_state：1→2 @t=27.3（唯一翻转），179 全窗恒 2
  （1468 样本，含变更触发发布）
- actuator_armed.armed：窗口内 1235/1235 全 true；nav_state=4（AUTO_LOITER
  failsafe 悬停——VINS 死后 offboard 断流 SITL 兜底形态）
- 全 src 树 arming_state=ARMED 唯一写点=arm() 自身（L622）

### ACK 源穷举（vehicle_command_ack 全部 8 个发布点逐一裁决）

| 发布点 | 179 裁决 |
|---|---|
| Commander::answer_command（L2680） | **唯一可能**（target=source 回程+from_external=0 签名吻合） |
| calibration_routines（L362） | 仅校准命令 |
| mavlink_main IRIDIUM（L2647） | 仅 MAVLINK_MODE_IRIDIUM+HIGH_LATENCY |
| MavlinkReceiver::acknowledge（L133） | 179 走 else 分支 send_ack=false（L720-756 实读：通用命令只 `_cmd_pub.publish` 转发 uORB） |
| MavlinkReceiver 相机 ACK 回声（L827） | from_external=1（与观测 0 不符） |
| FailureInjector（L101-108） | 仅 MAV_CMD_INJECT_FAILURE（L60 起 continue 门） |
| EKF2（L531/565/581） | 仅 EXTERNAL_POSITION/WIND/ATTITUDE_ESTIMATE |
| uxrce_dds | DDS 桥未启用 |

### 179 处理链源码路径（全部实读）

MavlinkReceiver（转发 uORB，不 ACK）→ Commander Run() 命令循环（L1890-1898）
→ handle_command L947-976（ARM_DISARM case）→ `disarm(command_external,
forced=true)` → ACK 条件 `arming_res != TRANSITION_DENIED → ACCEPTED`。
disarm()（L638-）逐行正确：`!isArmed()→NOT_CHANGED`；forced 跳过 landed 检查
直设 DISARMED+`Disarmed by`事件+`_status_changed`。

## 2. 断链分离点定案（源码级矛盾证明）

观测三元组：{412× ACK-ACCEPTED} ∧ {arming_state 零翻转（含变更触发发布，
若执行必入 ulog）} ∧ {actuator_armed 全 true（isArmed() 恒真）}。

按 d6f12ad1c4 源码：forced disarm 在 isArmed()=true 时**无第三种返回路径**
（CHANGED 必翻转状态+发事件；DENIED 不可能因 forced 跳过 landed 门；NOT_CHANGED
要求 isArmed()=false 与 actuator_armed 矛盾）。**三事实互斥=观测行为偏离静态
语义**——「ACK-无操作」不是任何合法代码路径的输出。

分离点精确定位：**answer_command 的发射条件（arming_res≠DENIED）与 disarm()
返回值语义之间**——ACK 层"逐次如实报告返回值"，返回值本身却与执行体物理效果
脱钩。运行时偏差候选（静态不可再收敛，按嫌疑序）：①uORB 订阅代际/拷贝异常
（command 循环 PX4_ERR generation 校验路径，console 主题未采样无法排除）
②Commander 线程数据不一致窗口（ulog 无 events 主题无法取证）③未知构建差异
（ver_sw+树干净已排除大半）。

## 3. 与既有定案的关系（勘误+加硬）

- 上周期 kill_dig §1.2「唯一 handler=commander 的 ACK 链无懈可击，但函数体
  零痕」表述**勘误**：ACK 链经本件穷举后**矛盾实存**（非"无懈可击"）——
  ACK 层与执行体的断链是源码级可证的不可能行为，非审计遗漏。
- 工程结论**加硬**：该构建 179(21196) 空中 forced disarm 不可依赖（原定案
  维持）且**其 ACK 主动撒谎**（ACCEPTED 无执行）——kill 梯②的 disarm 层
  不可用性从"未生效"升级为"未生效+假确认"。梯①盲降为主路径的设计决策
  获得额外正据（已实现：修复版梯③等 px4_on_ground/extended_state 独立
  确认，不信 ACK——设计前瞻正确）。
- 呈报件§④加硬行：SITL 域 179+21196=「ACK 假确认型断链（源码级矛盾在案，
  本件）」；实机 FMU v6C/v1.17.0 路径未测维持（台架动力套窗专项=用户域）。

## 4. SITL 验证轮（就绪待批窗）

设计：起飞→悬停→单发 179(0,21196)→观测五元组{ACK result, arming_state,
actuator_armed, 电机输出, events}：
- 复现（ACK=0+零翻转）→ 运行时偏差定案→下一级取证（gdb attach 或加日志
  重编译轮）；
- 不复现（disarm 生效）→ 08_24_40 轮特有状态依赖（failsafe LOITER 态嫌疑
  已注记：nav_state=4）→ 补 LOITER 态专项复验。
排程：HAFIX 终验批+A1 扩批毕后的批间隙窗（不占飞行批）。

## 5. 证据索引

- 08_24_40.ulg 原始字段全量（本件 §1，pyulog 直读）
- 源码行号全录：Commander.cpp L549/638/743/947-976/1890-1898/2680；
  mavlink_receiver.cpp L122-133/462/480/516/720-756/827；
  mavlink_main.cpp L2598-2647；FailureInjector.cpp L60-108；
  EKF2.cpp L529-581；marginalization 无关件另册
- ver_sw 树比对+git status 干净度+bin mtime 2026-09-29（实读）
- kill_dig 交叉：hafix_kill_dig_v1139.md §1.2（勘误对象）
