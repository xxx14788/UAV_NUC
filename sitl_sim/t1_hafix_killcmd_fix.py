#!/usr/bin/env python3
# t1_hafix_killcmd_fix.py — HAFIX 梯② kill 命令号勘定修复（C-1 终局判决执行件, 工程 v1.6 单元1）
# 真因: MAV_CMD 号错位 — 179=DO_SET_HOME(非 ARM_DISARM), 400=ARM_DISARM(非 FLIGHTTERMINATION),
#       185=DO_FLIGHTTERMINATION。旧双命令[400+p1=1.0=ARM 空转]+[179=SET_HOME]均非停电机。
# 修复: HAFIX_KILL_MAVCMD 400→185; HAFIX_KILL2_MAVCMD 179→400; 注释/日志/gtest 断言同步。
# 运行: python3 t1_hafix_killcmd_fix.py <repo根=/home/ghj/catkin_ws>
# 幂等: 已含 185 勘定则拒跑; 锚点不唯一即整体失败(RC=1)
import sys

root = sys.argv[1]
patches = []

fd = root + "/src/px4ctrl/src/fsm_decision.h"
src = open(fd, encoding="utf-8").read()
if "HAFIX_KILL_MAVCMD = 185" in src:
    print("FATAL: fix already present (idempotency guard)"); sys.exit(1)

old_h = """// 二次修复(干测 run_DRILLD1_N8P_042425 实证): 400/param1=1.0 被 FC ACK 但 termination 态被
// px4ctrl 活跃 setpoint 流覆盖(mode→AUTO.LOITER 悬停 0.59m, armed 恒 True 207s)——补发
// PX4 官方 kill 语义 = MAV_CMD_COMPONENT_ARM_DISARM(179) param1=0 + param2=21196
// (commander `disarm -f` 同款 forced 路径,绕过 landed 检查,不依赖 termination 态)。
constexpr int    HAFIX_KILL_MAVCMD = 400;
constexpr double HAFIX_KILL_PARAM1_ENGAGE = 1.0;
constexpr int    HAFIX_KILL2_MAVCMD = 179;        // MAV_CMD_COMPONENT_ARM_DISARM
constexpr double HAFIX_KILL2_DISARM = 0.0;        // param1 = DISARM
constexpr double HAFIX_KILL2_FORCE_MAGIC = 21196; // param2 = force 码(空中停电机)"""
new_h = """// 三次修复(C-1 终局判决 run_C1se_184008, 2026-10-11): MAV_CMD 号勘定——179=DO_SET_HOME、
// 400=COMPONENT_ARM_DISARM、185=DO_FLIGHTTERMINATION。旧双命令[400+p1=1.0=已解锁下 ARM 空转,
// NOT_CHANGED→ACK0]与[179(0,21196)=SET_HOME 到(0,0,0), ACCEPTED 零电机效果]均非停电机;
// 二次修复注释"179=COMPONENT_ARM_DISARM"为错号起源, "termination 被 setpoint 流覆盖"为幻影
// (400p1=1 从未携带 termination 意图)。固件行为全正确, 案卷宗=c1_separation/。
constexpr int    HAFIX_KILL_MAVCMD = 185;         // MAV_CMD_DO_FLIGHTTERMINATION(终止语义)
constexpr double HAFIX_KILL_PARAM1_ENGAGE = 1.0;
constexpr int    HAFIX_KILL2_MAVCMD = 400;        // MAV_CMD_COMPONENT_ARM_DISARM(真身)
constexpr double HAFIX_KILL2_DISARM = 0.0;        // param1 = DISARM
constexpr double HAFIX_KILL2_FORCE_MAGIC = 21196; // param2 = force 码(空中停电机)"""
if src.count(old_h) != 1:
    print(f"FATAL fsm_decision.h anchor count={src.count(old_h)}"); sys.exit(1)
src = src.replace(old_h, new_h, 1)
open(fd, "w", encoding="utf-8").write(src)
print("OK fsm_decision.h constants 400->185, 179->400")

fc = root + "/src/px4ctrl/src/PX4CtrlFSM.cpp"
src = open(fc, encoding="utf-8").read()
T = "\t"
old_c1 = (T + T + "// P-1 梯②: KILL 到期即发,双命令: ①cmd400 param1=1.0(MAV_CMD_DO_FLIGHTTERMINATION\n"
         + T + T + "// 终止语义;缺省 0=取消,旧码反向 bug)②cmd179 param1=0+param2=21196(PX4 官方\n"
         + T + T + "// forced kill=停电机;二次修复——干测实证 400 单发被活跃 setpoint 流覆盖成\n"
         + T + T + "// AUTO.LOITER 悬停,armed 恒 True)。返回检查+1Hz 限频重试+失败 FAIL 行;成功行仅返回后打。\n")
new_c1 = (T + T + "// P-1 梯②: KILL 到期即发,双命令(三次修复 C-1 终局, 号勘定 185/400——旧 400p1=1=ARM\n"
         + T + T + "// 空转与旧 179=SET_HOME 均非停电机, 详 fsm_decision.h 注): ①cmd185 param1=1.0\n"
         + T + T + "// (MAV_CMD_DO_FLIGHTTERMINATION 终止语义) ②cmd400 param1=0+param2=21196\n"
         + T + T + "// (真 forced disarm=停电机,绕过 landed 检查)。返回检查+1Hz 限频重试+失败 FAIL 行;成功行仅返回后打。\n")
if src.count(old_c1) != 1:
    print(f"FATAL PX4CtrlFSM.cpp comment anchor count={src.count(old_c1)}"); sys.exit(1)
src = src.replace(old_c1, new_c1, 1)

old_c2 = '"[HAFIX] %.1fs post-AUTO_LAND still flying -> KILL cmd400 p1=1.0 + cmd179 p2=21196 ACCEPTED"'
new_c2 = '"[HAFIX] %.1fs post-AUTO_LAND still flying -> KILL cmd185 p1=1.0 + cmd400 p2=21196 ACCEPTED"'
if src.count(old_c2) != 1:
    print(f"FATAL PX4CtrlFSM.cpp logline anchor count={src.count(old_c2)}"); sys.exit(1)
src = src.replace(old_c2, new_c2, 1)
open(fc, "w", encoding="utf-8").write(src)
print("OK PX4CtrlFSM.cpp comment + log line")

tf = root + "/src/px4ctrl/test/test_fsm_decision.cpp"
src = open(tf, encoding="utf-8").read()
old_t = """    // P-1 核心: MAV_CMD_DO_FLIGHTTERMINATION, param1=1.0=engage(0=cancel 反向 bug)
    EXPECT_EQ(400, HAFIX_KILL_MAVCMD);
    EXPECT_DOUBLE_EQ(1.0, HAFIX_KILL_PARAM1_ENGAGE);
    // 二次修复(干测 run_DRILLD1_N8P_042425 实证 400 被活跃 setpoint 流覆盖):
    // 补发 179+param2=21196 forced kill(disarm -f 同款,空中停电机)
    EXPECT_EQ(179, HAFIX_KILL2_MAVCMD);"""
new_t = """    // P-1 核心: MAV_CMD_DO_FLIGHTTERMINATION=185, param1=1.0=engage(0=cancel 反向 bug)
    // 三次修复(C-1 终局 run_C1se_184008): 号勘定 185=FLIGHTTERMINATION/400=ARM_DISARM/179=SET_HOME
    EXPECT_EQ(185, HAFIX_KILL_MAVCMD);
    EXPECT_DOUBLE_EQ(1.0, HAFIX_KILL_PARAM1_ENGAGE);
    // 真身 forced kill = 400(0,21196)(disarm -f 同款,空中停电机)
    EXPECT_EQ(400, HAFIX_KILL2_MAVCMD);"""
if src.count(old_t) != 1:
    print(f"FATAL test anchor count={src.count(old_t)}"); sys.exit(1)
src = src.replace(old_t, new_t, 1)
open(tf, "w", encoding="utf-8").write(src)
print("OK test_fsm_decision.cpp assertions 185/400")
print("PATCHED all 3 files")
