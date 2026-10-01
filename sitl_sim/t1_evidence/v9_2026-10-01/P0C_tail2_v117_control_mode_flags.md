# P0-C 尾件2 — PX4 v1.17 vehicle_control_mode flag 语义源码核对（2026-10-01 T1）

> 任务书 v9.0 等待池①尾件2；v8.1 册所标"v1.14"为版本标签笔误，实栈=PX4-Autopilot v1.17.0（git describe 实读）。
> F-G 判别（offboard 姿态模式下 pos_en=1 是否=级联在环）的开关性前提。代码块=源文件逐字抽取，零转写。

## 消息位域（VehicleControlMode.msg 逐字）



## 映射函数

- src/modules/commander/ModeUtil/control_mode.cpp::getVehicleControlMode()（Commander.cpp:2593 updateControlMode() 每 cycle 调用）
- Commander.cpp:2613 另聚合 multicopter_position_control_enabled=alt|climb|pos|vel|acc 任一（宽口径）

## OFFBOARD 分支逐字块（control_mode.cpp）

# 1 "<stdin>"
# 1 "<built-in>"
# 1 "<command-line>"
# 31 "<command-line>"
# 1 "/usr/include/stdc-predef.h" 1 3 4
# 32 "<command-line>" 2
# 1 "<stdin>"

## 结论

1. 位域决定论：v1.17 OFFBOARD 下 flag_control_* 完全由 offboard_control_mode 位域（position/velocity/acceleration/attitude/body_rate）优先级短路决定，与实际发的 setpoint 内容无关——发 attitude setpoint 但 position 位=1 仍按位置级联解释。
2. 级联在环 ⇔ position 位：flag_control_position_enabled=true 当且仅当 offboard_control_mode.position=true，此时全级联（pos-vel-acc-att-rates-alloc）在环；attitude 位-only 则位置级联不在环。
3. F-G 判别开关落地：W2 轮判读以 ulog offboard_control_mode 位域为唯一开关证据（尾件3 已入 X3_offline_w2.json transitions：w2a/c/e 单段、w2b 三段、w2d1 无 offboard、w2d2 单段），勿从 setpoint 内容反推。
4. flag_multicopter_position_control_enabled（Commander.cpp:2613）=宽口径并集（含 altitude/climb_rate），不可当"位置级联在环"证据；F-G 严格口径=flag_control_position_enabled。
