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

} // namespace fsm_decision
