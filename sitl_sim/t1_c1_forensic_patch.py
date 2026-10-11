#!/usr/bin/env python3
# t1_c1_forensic_patch.py — C-1 取证面补丁（工程合并 v1.6 单元1）
# 设计: unit4_c1_killpath_source_v1140.md §2 断链分离点 + c1_verdict_v1.md §4 候选①②
# 打点 6 处, 全部 PX4_INFO 打印(纯观测, 零功能改动), 前缀 C1FR 便于 grep:
#   [loop]   命令循环 copy 成功后全字段打印(候选①: 参数损坏/陈旧拷贝签名) + copy 失败分支
#   [armdis] ARM_DISARM case 入口/出口(arming_res, isArmed 前后)
#   [disarm] disarm() 入口/NOT_CHANGED/DENIED/写后回读(候选②: 写点分离)
#   [arm]    arm() 入口+already-armed 返回(陈旧 arm 拷贝假说直接签名)
#   [ack]    answer_command 入口(cmd+result)
#   [pub]    vehicle_status 发布点 2Hz 心跳(arming/actuator_armed/nav)
# 运行: python3 t1_c1_forensic_patch.py <Commander.cpp 路径>
# 幂等: 已打过(含 C1FR)则拒跑; 任一锚点不唯一匹配则整体失败不动文件(RC=1)
import sys

path = sys.argv[1]
src = open(path, encoding="utf-8").read()

if "C1FR" in src:
    print("FATAL: C1FR already present (idempotency guard)"); sys.exit(1)

T = "\t"
patches = []  # (name, old, new)

# ---- S1 命令循环 ----
old = (
    "\t\t\tif (_vehicle_command_sub.copy(&cmd)) {\n"
    "\t\t\t\tif (_vehicle_command_sub.get_last_generation() != last_generation + 1) {\n"
    "\t\t\t\t\tPX4_ERR(\"vehicle_command lost, generation %u -> %u\", last_generation, _vehicle_command_sub.get_last_generation());\n"
    "\t\t\t\t}\n"
    "\n"
    "\t\t\t\tif (handle_command(cmd)) {\n"
    "\t\t\t\t\t_status_changed = true;\n"
    "\t\t\t\t}\n"
    "\t\t\t}\n"
)
new = (
    "\t\t\tif (_vehicle_command_sub.copy(&cmd)) {\n"
    "\t\t\t\tPX4_INFO(\"C1FR[loop] cmd=%lu p1=%.4f p2=%.4f p3=%.4f p4=%.4f p5=%.4f p6=%.4f p7=%.4f tgt=%u/%u src=%u/%u ext=%d gen=%u->%u ts=%lu\", \\\n"
    "\t\t\t\t\t (unsigned long)cmd.command, (double)cmd.param1, (double)cmd.param2, (double)cmd.param3, (double)cmd.param4, \\\n"
    "\t\t\t\t\t (double)cmd.param5, (double)cmd.param6, (double)cmd.param7, \\\n"
    "\t\t\t\t\t (unsigned)cmd.target_system, (unsigned)cmd.target_component, (unsigned)cmd.source_system, (unsigned)cmd.source_component, \\\n"
    "\t\t\t\t\t (int)cmd.from_external, last_generation, _vehicle_command_sub.get_last_generation(), (unsigned long)cmd.timestamp);\n"
    "\n"
    "\t\t\t\tif (_vehicle_command_sub.get_last_generation() != last_generation + 1) {\n"
    "\t\t\t\t\tPX4_ERR(\"vehicle_command lost, generation %u -> %u\", last_generation, _vehicle_command_sub.get_last_generation());\n"
    "\t\t\t\t}\n"
    "\n"
    "\t\t\t\tif (handle_command(cmd)) {\n"
    "\t\t\t\t\t_status_changed = true;\n"
    "\t\t\t\t}\n"
    "\t\t\t} else {\n"
    "\t\t\t\tPX4_INFO(\"C1FR[loop] COPY-FAILED gen=%u\", last_generation);\n"
    "\t\t\t}\n"
)
patches.append(("S1-loop", old, new))

# ---- S2 ARM_DISARM case 入口 ----
old = (
    "\t\t\t\tconst bool forced = (static_cast<int>(lroundf(cmd.param2)) == 21196);\n"
    "\n"
    "\t\t\t\ttransition_result_t arming_res = TRANSITION_DENIED;\n"
)
new = (
    "\t\t\t\tconst bool forced = (static_cast<int>(lroundf(cmd.param2)) == 21196);\n"
    "\n"
    "\t\t\t\tPX4_INFO(\"C1FR[armdis] enter action=%d forced=%d ext=%d isArmed=%d st=%u hrt=%lu\", \\\n"
    "\t\t\t\t\t (int)arming_action, (int)forced, (int)cmd.from_external, (int)isArmed(), \\\n"
    "\t\t\t\t\t (unsigned)_vehicle_status.arming_state, (unsigned long)hrt_absolute_time());\n"
    "\n"
    "\t\t\t\ttransition_result_t arming_res = TRANSITION_DENIED;\n"
)
patches.append(("S2-armdis-enter", old, new))

# ---- S3 ARM_DISARM case 出口 ----
old = (
    "\t\t\t\tif (arming_action == vehicle_command_s::ARMING_ACTION_ARM) {\n"
    "\t\t\t\t\tarming_res = arm(arm_disarm_reason, cmd.from_external || !forced);\n"
    "\n"
    "\t\t\t\t} else if (arming_action == vehicle_command_s::ARMING_ACTION_DISARM) {\n"
    "\t\t\t\t\tarming_res = disarm(arm_disarm_reason, forced);\n"
    "\n"
    "\t\t\t\t}\n"
)
new = (
    "\t\t\t\tif (arming_action == vehicle_command_s::ARMING_ACTION_ARM) {\n"
    "\t\t\t\t\tarming_res = arm(arm_disarm_reason, cmd.from_external || !forced);\n"
    "\n"
    "\t\t\t\t} else if (arming_action == vehicle_command_s::ARMING_ACTION_DISARM) {\n"
    "\t\t\t\t\tarming_res = disarm(arm_disarm_reason, forced);\n"
    "\n"
    "\t\t\t\t}\n"
    "\n"
    "\t\t\t\tPX4_INFO(\"C1FR[armdis] res=%d isArmed=%d st=%u hrt=%lu\", \\\n"
    "\t\t\t\t\t (int)arming_res, (int)isArmed(), (unsigned)_vehicle_status.arming_state, (unsigned long)hrt_absolute_time());\n"
)
patches.append(("S3-armdis-exit", old, new))

# ---- S4 disarm() 入口+NOT_CHANGED ----
old = (
    "transition_result_t Commander::disarm(arm_disarm_reason_t calling_reason, bool forced)\n"
    "{\n"
    "\tif (!isArmed()) {\n"
    "\t\treturn TRANSITION_NOT_CHANGED;\n"
    "\t}\n"
)
new = (
    "transition_result_t Commander::disarm(arm_disarm_reason_t calling_reason, bool forced)\n"
    "{\n"
    "\tPX4_INFO(\"C1FR[disarm] enter forced=%d isArmed=%d st=%u hrt=%lu\", \\\n"
    "\t\t (int)forced, (int)isArmed(), (unsigned)_vehicle_status.arming_state, (unsigned long)hrt_absolute_time());\n"
    "\n"
    "\tif (!isArmed()) {\n"
    "\t\tPX4_INFO(\"C1FR[disarm] ret NOT_CHANGED (not armed)\");\n"
    "\t\treturn TRANSITION_NOT_CHANGED;\n"
    "\t}\n"
)
patches.append(("S4-disarm-enter", old, new))

# ---- S5 disarm() 写后回读(锚定 flight_uuid commit, 与 arm() 尾部区分) ----
old = (
    "\t_param_com_flight_uuid.commit_no_notification();\n"
    "\n"
    "\t_status_changed = true;\n"
    "\n"
    "\treturn TRANSITION_CHANGED;\n"
)
new = (
    "\t_param_com_flight_uuid.commit_no_notification();\n"
    "\n"
    "\t_status_changed = true;\n"
    "\n"
    "\tPX4_INFO(\"C1FR[disarm] WROTE DISARMED st_now=%u status_changed=%d hrt=%lu\", \\\n"
    "\t\t (unsigned)_vehicle_status.arming_state, (int)_status_changed, (unsigned long)hrt_absolute_time());\n"
    "\n"
    "\treturn TRANSITION_CHANGED;\n"
)
patches.append(("S5-disarm-wrote", old, new))

# ---- S6 arm() 入口 ----
old = (
    "transition_result_t Commander::arm(arm_disarm_reason_t calling_reason, bool run_preflight_checks)\n"
    "{\n"
    "\tif (isArmed()) {\n"
    "\t\treturn TRANSITION_NOT_CHANGED;\n"
    "\t}\n"
)
new = (
    "transition_result_t Commander::arm(arm_disarm_reason_t calling_reason, bool run_preflight_checks)\n"
    "{\n"
    "\tPX4_INFO(\"C1FR[arm] enter preflight=%d isArmed=%d st=%u hrt=%lu\", \\\n"
    "\t\t (int)run_preflight_checks, (int)isArmed(), (unsigned)_vehicle_status.arming_state, (unsigned long)hrt_absolute_time());\n"
    "\n"
    "\tif (isArmed()) {\n"
    "\t\tPX4_INFO(\"C1FR[arm] ret NOT_CHANGED (already armed)\");\n"
    "\t\treturn TRANSITION_NOT_CHANGED;\n"
    "\t}\n"
)
patches.append(("S6-arm-enter", old, new))

# ---- S7 answer_command 入口 ----
old = (
    "void Commander::answer_command(const vehicle_command_s &cmd, uint8_t result)\n"
    "{\n"
    "\tswitch (result) {\n"
)
new = (
    "void Commander::answer_command(const vehicle_command_s &cmd, uint8_t result)\n"
    "{\n"
    "\tPX4_INFO(\"C1FR[ack] cmd=%lu result=%u\", (unsigned long)cmd.command, (unsigned)result);\n"
    "\n"
    "\tswitch (result) {\n"
)
patches.append(("S7-ack", old, new))

# ---- S8 发布点心跳 ----
old = (
    "\t\t\t_vehicle_status.timestamp = hrt_absolute_time();\n"
    "\t\t\t_vehicle_status_pub.publish(_vehicle_status);\n"
)
new = (
    "\t\t\t_vehicle_status.timestamp = hrt_absolute_time();\n"
    "\t\t\t_vehicle_status_pub.publish(_vehicle_status);\n"
    "\n"
    "\t\t\tPX4_INFO(\"C1FR[pub] arming=%u act_armed=%d nav=%lu hrt=%lu\", \\\n"
    "\t\t\t\t (unsigned)_vehicle_status.arming_state, (int)_actuator_armed.armed, \\\n"
    "\t\t\t\t (unsigned long)_vehicle_status.nav_state, (unsigned long)hrt_absolute_time());\n"
)
patches.append(("S8-pub-hb", old, new))

fail = 0
for name, o, n in patches:
    c = src.count(o)
    if c != 1:
        print(f"FATAL anchor {name}: match count={c} (expect 1); ABORT no changes written"); fail = 1
if fail:
    sys.exit(1)

for name, o, n in patches:
    src = src.replace(o, n, 1)
    print(f"OK {name}")

open(path, "w", encoding="utf-8").write(src)
print(f"PATCHED {path}: {len(patches)} sites")
