#!/usr/bin/env python3
"""T1-W1 px4ctrl 韧性补丁(2026-09-27)。

用法(在 ~/catkin_ws/src/px4ctrl/ 下执行,执行前 git status 必须干净;回退用 git checkout):
    python3 t1_patch_px4ctrl.py --f4-only   # 仅加 /debugPx4ctrl/fsm_state 自监视(取证插桩)
    python3 t1_patch_px4ctrl.py --all       # F1+F2+F3+F4 全部(完整修复)

修复设计(与 ~/sitl_sim/t1_evidence/w1_source_analysis.md 对应):
  F5  主循环 ros::Rate→ros::WallRate(免疫 SITL 时钟归零倒跳,W1b 实测主根因)
  F1  MANUAL_CTRL→AUTO_TAKEOFF:toggle_offboard_mode(true) 失败时回退 state
  F2  AUTO_TAKEOFF 看门狗:disarmed 且未离地超时 → 回退 MANUAL_CTRL
  F3  /mavros/state 流断 >3s 且 disarmed → FSM 重置干净 MANUAL_CTRL
  F4  /debugPx4ctrl/fsm_state 1Hz 自监视(状态名+五布尔+armed)

安全边界:armed 态行为一个字节不改;F2/F3 入口条件均含 !armed。
锚点匹配数 != 预期即 raise,绝不半改。
"""
import re
import sys
from pathlib import Path

F4_ONLY = "--f4-only" in sys.argv
ALL = "--all" in sys.argv or "--f4-only" not in sys.argv

ROOT = Path(__file__).resolve().parent  # src/px4ctrl/
TAG = "T1-W1"


def patch(path, hunks):
    """hunks: list of (name, pattern, replacement)。逐个应用,匹配数 != 1 即 raise。"""
    text = path.read_text(encoding="utf-8")
    for name, pat, rep in hunks:
        n = len(re.findall(pat, text))
        if n != 1:
            raise RuntimeError(
                f"{path.name}: hunk [{name}] matched {n} times (expect 1); abort before any write")
        text = re.sub(pat, rep, text, count=1)
    path.write_text(text, encoding="utf-8")
    print(f"patched: {path.relative_to(ROOT)}")


# ---------------- input.h / input.cpp(F3 依赖) ----------------
input_h_hunks = [
    ("state_rcv_stamp_decl",
     r"(class State_Data_t\n\{\npublic:\n  mavros_msgs::State current_state;\n  mavros_msgs::State state_before_offboard;\n)",
     r"\1  ros::Time rcv_stamp; // T1-W1: /mavros/state 到达时刻,FCU 链路活性判据\n"),
]

input_cpp_hunks = [
    ("state_feed_stamp",
     r"void State_Data_t::feed\(mavros_msgs::StateConstPtr pMsg\)\n\{\n\n    current_state = \*pMsg;\n\}",
     "void State_Data_t::feed(mavros_msgs::StateConstPtr pMsg)\n{\n"
     "    rcv_stamp = ros::Time::now(); // T1-W1: FCU 链路活性\n\n"
     "    current_state = *pMsg;\n}"),
]

# ---------------- px4ctrl_node.cpp(F4 依赖) ----------------
node_hunks = [
    ("include_string",
     r"(#include <signal\.h>\n)",
     r"\1#include <std_msgs/String.h>\n"),
    ("advertise_fsm_state",
     r"    fsm\.debug_pub = nh\.advertise<quadrotor_msgs::Px4ctrlDebug>\(\"/debugPx4ctrl\", 10\); // debug\n",
     "    fsm.debug_pub = nh.advertise<quadrotor_msgs::Px4ctrlDebug>(\"/debugPx4ctrl\", 10); // debug\n"
     "    fsm.fsm_state_pub = nh.advertise<std_msgs::String>(\"/debugPx4ctrl/fsm_state\", 10); // T1-W1: FSM 状态自监视\n"),
]

# ---------------- PX4CtrlFSM.h ----------------
fsm_h_hunks_all = [
    ("fsm_state_pub_decl",
     r"(\tros::Publisher debug_pub; //debug\n)",
     r"\1\tros::Publisher fsm_state_pub; // T1-W1: 1Hz FSM 状态自监视\n"),
    ("state2str_decl",
     r"(\tbool get_landed\(\) \{ return takeoff_land\.landed; \}\n)",
     r"\1\tstatic std::string state2str(State_t s); // T1-W1: 状态名输出,自监视用\n"),
    ("takeoff_abort_const",
     r"(\tstatic constexpr double DELAY_TRIGGER_TIME = 2\.0;  // Time to be delayed when reach at target height\n)",
     r"\1\tstatic constexpr double TAKEOFF_ABORT_TIMEOUT = 10.0; // T1-W1: 电机加速后仍 disarmed 且未离地这么久则放弃起飞\n"),
]
fsm_h_hunks_f4 = fsm_h_hunks_all[:2]  # f4-only 不引入未使用的超时常量

# ---------------- PX4CtrlFSM.cpp ----------------
STATE2STR_DEF = """
std::string PX4CtrlFSM::state2str(State_t s)
{
	switch (s)
	{
	case MANUAL_CTRL: return "MANUAL_CTRL";
	case AUTO_HOVER: return "AUTO_HOVER";
	case CMD_CTRL: return "CMD_CTRL";
	case AUTO_TAKEOFF: return "AUTO_TAKEOFF";
	case AUTO_LAND: return "AUTO_LAND";
	default: return "UNKNOWN";
	}
}
"""

F1_REPL = """			state = AUTO_TAKEOFF;
			controller.resetThrustMapping();
			set_start_pose_for_takeoff_land(odom_data);
			if (!toggle_offboard_mode(true)) // toggle on offboard before arm (T1-W1 F1: 失败必须回退,否则封死在无出口的 AUTO_TAKEOFF)
			{
				state = MANUAL_CTRL;
				takeoff_land_data.triggered = false;
				ROS_ERROR("[px4ctrl] AUTO_TAKEOFF aborted: OFFBOARD rejected (FCU link busy/rebooting), back to MANUAL_CTRL. Retry takeoff.");
				break;
			}"""

F2_REPL = """		// T1-W1 F2: 起飞看门狗 — 电机加速结束后这么久仍 disarmed 且未离地,说明起飞从未推进
		// (ARM 被拒 / FCU 重启)。回退 MANUAL_CTRL。armed 态不受影响。
		if ((now_time - takeoff_land.toggle_takeoff_land_time).toSec() >
			    AutoTakeoffLand_t::MOTORS_SPEEDUP_TIME + AutoTakeoffLand_t::TAKEOFF_ABORT_TIMEOUT &&
		    !state_data.current_state.armed &&
		    odom_data.p(2) < takeoff_land.start_pose(2) + 0.3)
		{
			state = MANUAL_CTRL;
			toggle_offboard_mode(false);
			ROS_ERROR("[px4ctrl] AUTO_TAKEOFF timeout (disarmed & not airborne), back to MANUAL_CTRL. Retry takeoff.");
			break;
		}
"""

F3_REPL = """
	// STEP0: FCU 链路活性自愈(T1-W1 F3)。
	// 上游 FSM 在 FCU 重启(state/odom 流冻结)时,AUTO_TAKEOFF/AUTO_HOVER/AUTO_LAND 无出口,
	// 对 /px4ctrl/takeoff_land 完全静默。仅当 /mavros/state 流断开 >3s 且 disarmed 时,
	// 重置到干净的 MANUAL_CTRL(armed 态一个字节不改,安全红线)。
	if (!state_data.current_state.armed &&
	    state_data.rcv_stamp != ros::Time(0) &&
	    state != MANUAL_CTRL &&
	    (now_time - state_data.rcv_stamp).toSec() > 3.0)
	{
		state = MANUAL_CTRL;
		takeoff_land_data.triggered = false;
		cmd_data.rcv_stamp = ros::Time(0); // 强制 cmd 过期,重进 AUTO_HOVER 前置检查干净
		controller.resetThrustMapping();
		set_hov_with_odom();
		// 不调 toggle_offboard_mode(false):链路已断,服务调用只会阻塞后失败
		ROS_WARN("[px4ctrl] FCU state stream lost for %.1fs while disarmed, FSM reset to MANUAL_CTRL.",
		         (now_time - state_data.rcv_stamp).toSec());
	}
"""

F4_REPL = """
	// STEP7: 1Hz FSM 自监视(T1-W1 F4)
	static ros::Time last_fsm_state_pub_time(0);
	if ((now_time - last_fsm_state_pub_time).toSec() > 1.0 && fsm_state_pub)
	{
		std_msgs::String fsm_msg;
		fsm_msg.data = state2str(state) +
		               " triggered=" + (takeoff_land_data.triggered ? "1" : "0") +
		               " state_recv=" + ((now_time - state_data.rcv_stamp).toSec() < 3.0 ? "1" : "0") +
		               " odom_recv=" + (odom_is_received(now_time) ? "1" : "0") +
		               " cmd_recv=" + (cmd_is_received(now_time) ? "1" : "0") +
		               " landed=" + (get_landed() ? "1" : "0") +
		               " armed=" + (state_data.current_state.armed ? "1" : "0");
		fsm_state_pub.publish(fsm_msg);
		last_fsm_state_pub_time = now_time;
	}
"""

fsm_cpp_hunks_all = [
    ("fsm_state_cpp_include",
     r"(#include \"PX4CtrlFSM\.h\"\n#include <uav_utils/converters\.h>\n)",
     r"\1#include <std_msgs/String.h>\n"),
    ("state2str_def",
     r"(bool PX4CtrlFSM::recv_new_odom\(\)\n\{\n\tif \(odom_data\.recv_new_msg\)\n\t\{\n\t\todom_data\.recv_new_msg = false;\n\t\treturn true;\n\t\}\n\n\treturn false;\n\}\n)",
     r"\1" + STATE2STR_DEF),
    ("f4_publish",
     r"(\ttakeoff_land_data\.triggered = false;\n)\}",
     r"\1" + F4_REPL + "}"),
    ("f1_offboard_fail_revert",
     r"\t\t\tstate = AUTO_TAKEOFF;\n\t\t\tcontroller\.resetThrustMapping\(\);\n"
     r"\t\t\tset_start_pose_for_takeoff_land\(odom_data\);\n"
     r"\t\t\ttoggle_offboard_mode\(true\);\s*// toggle on offboard before arm",
     F1_REPL),
    ("f2_takeoff_watchdog",
     r"(\tcase AUTO_TAKEOFF:\n\t\{\n)",
     r"\1" + F2_REPL),
    ("f3_state_stream_reset",
     r"(\tbool rotor_low_speed_during_land = false;\n)\n\t// STEP1: state machine runs",
     r"\1" + F3_REPL + "\n\t// STEP1: state machine runs"),
]

# ---- F5(W1b 实测真正根因):主循环 sim-time Rate → WallRate ----
# 机制:SITL 重启使 /clock 归零倒跳,ros::Rate::sleep() 的周期终点锚定在旧会话高 sim 值,
# 主循环在 0.8ms wallsleep 自旋中冻结(实测冻结 = 旧会话 sim 时长,分钟级),期间无 spinOnce,
# 一切回调停摆 → takeoff 静默无响应。WallRate 用墙钟,对 use_sim_time=false 的实机行为完全一致。
node_hunks_f5 = (
    "f5_wall_rate",
    r"    ros::Rate r\(param\.ctrl_freq_max\);\n",
    "    // T1-W1 F5: WallRate 而非 Rate —— 免疫 SITL 重启的 /clock 归零倒跳\n"
    "    // (sim-time Rate 会把周期终点锚定在旧会话高值,主循环冻结 = 旧会话 sim 时长)\n"
    "    ros::WallRate r(param.ctrl_freq_max);\n")
node_hunks_all = node_hunks + [node_hunks_f5]

fsm_cpp_hunks_f4 = [h for h in fsm_cpp_hunks_all
                    if h[0] in ("fsm_state_cpp_include", "state2str_def", "f4_publish")]


def main():
    if F4_ONLY:
        # F4 的 state_recv 读 state_data.rcv_stamp,插桩版也需要 input.h/.cpp 的被动时间戳
        patch(ROOT / "src" / "input.h", input_h_hunks)
        patch(ROOT / "src" / "input.cpp", input_cpp_hunks)
        patch(ROOT / "src" / "PX4CtrlFSM.cpp", fsm_cpp_hunks_f4)
        patch(ROOT / "src" / "PX4CtrlFSM.h", fsm_h_hunks_f4)
        patch(ROOT / "src" / "px4ctrl_node.cpp", node_hunks)
        print("mode=f4-only done. 重编: catkin_make --pkg px4ctrl(或全量)")
        return
    patch(ROOT / "src" / "input.h", input_h_hunks)
    patch(ROOT / "src" / "input.cpp", input_cpp_hunks)
    patch(ROOT / "src" / "PX4CtrlFSM.cpp", fsm_cpp_hunks_all)
    patch(ROOT / "src" / "PX4CtrlFSM.h", fsm_h_hunks_all)
    patch(ROOT / "src" / "px4ctrl_node.cpp", node_hunks_all)
    print("mode=all done. 重编 + SITL 冒烟 + 3 循环恢复测试通过后按工作单元提交。")


if __name__ == "__main__":
    main()
