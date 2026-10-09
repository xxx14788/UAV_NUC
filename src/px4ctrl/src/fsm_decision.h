/*******************************************************
 * T1-F3 (2026-09-30; wired 2026-10-04 v11.0 unit 1):
 * pure decision functions for PX4CtrlFSM state transitions.
 *
 * v2 (2026-10-04): promoted from test/ mirror to src/
 * production header — PX4CtrlFSM.cpp now CALLS these
 * functions (behavior-equivalent refactor, F3 full wiring).
 * Additions vs the v1 mirror:
 *   - RejectReason codes so the FSM keeps per-cause logging
 *     (log equivalence, not only transition equivalence);
 *   - Inputs::no_rc + decide_manual() LAND branch (U2.7):
 *     LAND used to be silently dropped in MANUAL_CTRL —
 *     U3PO forensics (run_U3PO_211438): odom dropout put the
 *     FSM in MANUAL_CTRL while armed, harness LAND (1Hz,120s)
 *     was silently ignored, drone hovered armed until tree
 *     kill (auto_disarm check failed). no_RC programmatic
 *     config now accepts LAND -> AUTO_HOVER (next LAND tick
 *     -> AUTO_LAND via decide_hover, 06_land.sh -r 1
 *     pattern); RC connected keeps manual priority (explicit
 *     reject). transition table mirror of F3_fsm_audit.md.
 *   - decide_hover(): strict mirror fix — when rc_cmd&&cmd_ok
 *     but OFFBOARD not yet confirmed, the source else-if
 *     chain does NOT fall through to LAND; v1 mirror did.
 *******************************************************/
#pragma once
#include <cstdint>

namespace fsm_decision
{

enum State : int
{
    MANUAL_CTRL = 1,
    AUTO_HOVER,
    CMD_CTRL,
    AUTO_TAKEOFF,
    AUTO_LAND
};

// Per-cause reject codes (U2.7/F3 v2). The FSM maps these back to the
// original per-branch ROS_ERROR texts so logs stay behavior-equivalent.
enum RejectReason : int
{
    RJ_NONE = 0,
    RJ_NO_ODOM,       // "No odom!"
    RJ_CMD_ACTIVE,    // commands still streaming (entry gate)
    RJ_VEL,           // velocity gate (hover-entry 3.0 / takeoff 0.1 / land 3.0)
    RJ_NOT_LANDED,    // land detector says airborne (takeoff gate)
    RJ_RC_GUARD,      // RC switches/sticks not in takeoff pose
    RJ_STATE,         // CMD_CTRL LAND: must be triggered in AUTO_HOVER
    RJ_DISARMED,      // U2.7: LAND ignored, disarmed (nothing to land)
    RJ_MANUAL_PRIO,   // U2.7: RC connected / no odom / vel>3 — manual priority or unsafe
    RJ_BIRTH_MISMATCH, // P1: odom rebirth birth-offset latched (U9 1.42m family)
    RJ_CMDRESP        // P2: cmd-response divergence latched (v11.4 unit 3, u3 hover-8.5m family)
};

struct Inputs
{
    // gate primitives (queries used by the FSM cases)
    bool odom_ok = false;
    bool cmd_ok = false;
    bool rc_is_received = true;
    bool rc_hover = false;      // rc_data.is_hover_mode
    bool rc_cmd = false;        // rc_data.is_command_mode
    bool rc_centered = false;   // rc_data.check_centered()
    bool enter_hover = false;   // rc_data.enter_hover_mode edge
    bool takeoff_trigger = false;
    bool land_trigger = false;
    bool offboard_confirmed = false; // state.mode == "OFFBOARD"
    bool armed = false;
    double odom_v = 0.0;        // ‖v‖
    bool landed = true;         // get_landed()
    bool px4_on_ground = false; // extended_state LANDED_STATE_ON_GROUND
    bool fcu_state_stale = false; // STEP0: /mavros/state stream >3s stale
    double dt_takeoff = 1e9;    // now - toggle_takeoff_land_time
    bool no_rc = false;         // param.takeoff_land.no_RC (U2.7)
    bool birth_mismatch = false; // P1: rebirth birth-offset latched (cleared on disarm)
    bool cmdresp_divergent = false; // P2: cmd-response divergence latched (cleared on recover/disarm)
};

struct Outcome
{
    State next;
    bool offboard_on = false;   // toggle_offboard_mode(true) attempted
    bool offboard_off = false;  // toggle_offboard_mode(false) attempted
    bool arm = false;
    bool disarm = false;
    bool reject = false;        // transition request refused (stay)
    RejectReason reason = RJ_NONE;
};

// STEP0: FCU link-liveness self-heal (T1-W1 F3). Disarmed + state stream
// stale >3s + not already MANUAL -> clean reset. armed bytes untouched.
// NOTE: the rcv_stamp!=0 first-frame guard stays at the call site (audit #S0).
inline Outcome step0_global(State s, const Inputs &in)
{
    Outcome o;
    o.next = s;
    if (!in.armed && in.fcu_state_stale && s != MANUAL_CTRL)
        o.next = MANUAL_CTRL;
    return o;
}

// MANUAL_CTRL case. Requests, in priority order (source else-if chain):
// hover entry -> takeoff -> land (U2.7). Only one request is live per tick.
inline Outcome decide_manual(const Inputs &in)
{
    Outcome o;
    o.next = MANUAL_CTRL;
    if (in.enter_hover)
    {
        if (!in.odom_ok)     { o.reject = true; o.reason = RJ_NO_ODOM; return o; }
        if (in.birth_mismatch) { o.reject = true; o.reason = RJ_BIRTH_MISMATCH; return o; } // P1
        if (in.cmdresp_divergent) { o.reject = true; o.reason = RJ_CMDRESP; return o; } // P2
        if (in.cmd_ok)       { o.reject = true; o.reason = RJ_CMD_ACTIVE; return o; }
        if (in.odom_v > 3.0) { o.reject = true; o.reason = RJ_VEL; return o; }
        o.next = AUTO_HOVER; o.offboard_on = true; return o;
    }
    if (in.takeoff_trigger)
    {
        if (!in.odom_ok)     { o.reject = true; o.reason = RJ_NO_ODOM; return o; }
        if (in.cmdresp_divergent) { o.reject = true; o.reason = RJ_CMDRESP; return o; } // P2
        if (in.cmd_ok)       { o.reject = true; o.reason = RJ_CMD_ACTIVE; return o; }
        if (in.odom_v > 0.1) { o.reject = true; o.reason = RJ_VEL; return o; }
        if (!in.landed)      { o.reject = true; o.reason = RJ_NOT_LANDED; return o; }
        if (in.rc_is_received && (!in.rc_hover || !in.rc_cmd || !in.rc_centered))
        { o.reject = true; o.reason = RJ_RC_GUARD; return o; }
        o.next = AUTO_TAKEOFF; o.offboard_on = true; o.arm = true; return o;
    }
    // U2.7 (2026-10-04): LAND in MANUAL_CTRL — previously silently dropped.
    if (in.land_trigger)
    {
        if (!in.armed) { o.reject = true; o.reason = RJ_DISARMED; return o; }
        if (in.birth_mismatch) { o.reject = true; o.reason = RJ_BIRTH_MISMATCH; return o; } // P1
        if (in.no_rc && in.odom_ok && in.odom_v <= 3.0)
        {
            // programmatic config: accept, hand over to AUTO_HOVER; the next
            // LAND tick goes AUTO_LAND via decide_hover (06_land.sh -r 1)
            o.next = AUTO_HOVER; o.offboard_on = true; return o;
        }
        o.reject = true; o.reason = RJ_MANUAL_PRIO; return o;
    }
    return o;
}

// AUTO_HOVER case. Strict mirror of the source else-if chain: when
// rc_cmd&&cmd_ok but OFFBOARD is not yet confirmed the request branch is
// consumed and LAND is NOT evaluated on that tick (v1 mirror fell through).
inline Outcome decide_hover(const Inputs &in)
{
    Outcome o;
    o.next = AUTO_HOVER;
    if (!in.rc_hover || !in.odom_ok) { o.next = MANUAL_CTRL; o.offboard_off = true; return o; }
    if (in.rc_cmd && in.cmd_ok)
    {
        if (in.offboard_confirmed) { o.next = CMD_CTRL; }
        return o;
    }
    if (in.land_trigger) { o.next = AUTO_LAND; return o; }
    return o;
}

// CMD_CTRL case. LAND trigger in CMD_CTRL is REJECTED (source :239-246);
// note the source does not consume `triggered` (audit finding #3, kept).
inline Outcome decide_cmd(const Inputs &in)
{
    Outcome o;
    o.next = CMD_CTRL;
    if (!in.rc_hover || !in.odom_ok) { o.next = MANUAL_CTRL; o.offboard_off = true; return o; }
    if (!in.rc_cmd || !in.cmd_ok)    { o.next = AUTO_HOVER; return o; }
    if (in.land_trigger)             { o.reject = true; o.reason = RJ_STATE; return o; }
    return o;
}

// AUTO_TAKEOFF case, watchdog = T1-W1 F2
inline Outcome decide_takeoff(const Inputs &in, double speedup_time = 3.0,
                              double abort_timeout = 5.0, double height = 1.0, double start_z = 0.0,
                              double cur_z = 0.0)
{
    Outcome o;
    o.next = AUTO_TAKEOFF;
    if (in.dt_takeoff > speedup_time + abort_timeout && !in.armed && (cur_z - start_z) < 0.3)
    { o.next = MANUAL_CTRL; o.offboard_off = true; return o; }              // watchdog
    if (in.dt_takeoff < speedup_time) return o;                             // speedup window
    if ((cur_z - start_z) >= height) { o.next = AUTO_HOVER; return o; }     // reached
    return o;                                                               // climbing
}

// AUTO_LAND case (:284-336)
inline Outcome decide_land(const Inputs &in)
{
    Outcome o;
    o.next = AUTO_LAND;
    if (!in.rc_hover || !in.odom_ok) { o.next = MANUAL_CTRL; o.offboard_off = true; return o; }
    if (!in.rc_cmd)                  { o.next = AUTO_HOVER; return o; }     // abort land
    if (!in.landed)                  return o;                              // descending
    if (in.px4_on_ground)            { o.next = MANUAL_CTRL; o.disarm = true; o.offboard_off = true; return o; }
    return o;                                                               // waiting (rotor low speed)
}

// ---------- T1-v1139 P-1/P-2: HAFIX 梯②③纯决策(可测面;调用侧=PX4CtrlFSM STEP0.5) ----------
// P-1 语义常量: MAV_CMD_DO_FLIGHTTERMINATION param1 — 1=terminate / 0=cancel。
// 旧码缺省 0 = 「取消终止」反向 bug 实锤(3d 批 FAIL 侧根因之一),调用点必须用本常量。
// 二次修复(干测 run_DRILLD1_N8P_042425 实证): 400/param1=1.0 被 FC ACK 但 termination 态被
// px4ctrl 活跃 setpoint 流覆盖(mode→AUTO.LOITER 悬停 0.59m, armed 恒 True 207s)——补发
// PX4 官方 kill 语义 = MAV_CMD_COMPONENT_ARM_DISARM(179) param1=0 + param2=21196
// (commander `disarm -f` 同款 forced 路径,绕过 landed 检查,不依赖 termination 态)。
constexpr int    HAFIX_KILL_MAVCMD = 400;
constexpr double HAFIX_KILL_PARAM1_ENGAGE = 1.0;
constexpr int    HAFIX_KILL2_MAVCMD = 179;        // MAV_CMD_COMPONENT_ARM_DISARM
constexpr double HAFIX_KILL2_DISARM = 0.0;        // param1 = DISARM
constexpr double HAFIX_KILL2_FORCE_MAGIC = 21196; // param2 = force 码(空中停电机)

struct HafixInputs
{
    bool enabled = true;
    int stage = 0;             // ha_stage: 0=监视 1=watch 2=LAND 3=KILL 已发
    bool flying = false;       // armed && !landed
    double dead_elapsed = 0.0; // now - ha_dead_since
    bool landed = false;
    bool armed = false;
    double dead_s = 5.0;
    double kill_s = 15.0;
};

struct HafixAction
{
    int stage_next = 0;
    bool watch_start = false;      // 梯①入口
    bool auto_land = false;        // 梯①: 切 AUTO_LAND(盲降)
    bool kill_fire = false;        // 梯②: 本拍发 KILL(400, param1=1.0;调用侧 1Hz 限频+返回检查)
    bool disarm_postposed = false; // 梯③(P-2): landed 门开→disarm 收尾(调用侧 1Hz 重试)
    bool cleared = false;
};

inline HafixAction decide_hafix(const HafixInputs &in)
{
    HafixAction a;
    a.stage_next = in.stage;
    if (!in.enabled) return a;
    // P-2 梯③: KILL 后 landed 输入开门才 disarm;持有期(landed∧armed)不清 stage,
    // disarm 被拒不丢梯(1Hz 重试至成功,成功侧归零)。
    const bool ladder3_hold = (in.stage == 3 && in.landed && in.armed);
    if (ladder3_hold) a.disarm_postposed = true;
    if (in.flying)
    {
        if (in.stage == 0)
        { a.stage_next = 1; a.watch_start = true; }
        else if (in.stage == 1 && in.dead_elapsed >= in.dead_s)
        { a.stage_next = 2; a.auto_land = true; }
        else if (in.dead_elapsed >= in.dead_s + in.kill_s)
        { if (in.stage == 2) a.stage_next = 3; a.kill_fire = true; } // P-1: 到期即发,持续重试
    }
    else if (in.stage != 0 && !ladder3_hold)
    { a.stage_next = 0; a.cleared = true; }
    return a;
}

} // namespace fsm_decision
