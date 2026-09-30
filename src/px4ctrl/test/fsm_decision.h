/*******************************************************
 * T1-F3 (2026-09-30): mirror-style pure decision functions
 * for PX4CtrlFSM state transitions. Each function mirrors
 * the corresponding case block in PX4CtrlFSM.cpp (HEAD),
 * including the T1-W1 self-heal guards (F1/F2/F3) and the
 * STEP0 global recovery. Line-level comments cite source.
 *
 * MIRROR DISCLAIMER: this is documentation-grade validation
 * (duplicated logic tested exhaustively); the behavior-
 * equivalent refactor (FSM.cpp actually calling these) is
 * queued for the next session. See F3_fsm_audit.md.
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
};

struct Outcome
{
    State next;
    bool offboard_on = false;   // toggle_offboard_mode(true) attempted
    bool offboard_off = false;  // toggle_offboard_mode(false) attempted
    bool arm = false;
    bool disarm = false;
    bool reject = false;        // transition request refused (stay)
};

// STEP0: FCU link-liveness self-heal (T1-W1 F3). Disarmed + state stream
// stale >3s + not already MANUAL -> clean reset. armed bytes untouched.
inline Outcome step0_global(State s, const Inputs &in)
{
    Outcome o;
    o.next = s;
    if (!in.armed && in.fcu_state_stale && s != MANUAL_CTRL)
        o.next = MANUAL_CTRL;
    return o;
}

// MANUAL_CTRL case (PX4CtrlFSM.cpp:69-172)
inline Outcome decide_manual(const Inputs &in)
{
    Outcome o;
    o.next = MANUAL_CTRL;
    if (in.enter_hover)
    {
        if (!in.odom_ok) { o.reject = true; return o; }          // :73 No odom
        if (in.cmd_ok)   { o.reject = true; return o; }          // :77 cmd active
        if (in.odom_v > 3.0) { o.reject = true; return o; }      // :81 localization
        o.next = AUTO_HOVER; o.offboard_on = true; return o;     // :86-90
    }
    // takeoff branch: gates in the same order as :94-124
    if (in.takeoff_trigger)
    {
        if (!in.odom_ok) { o.reject = true; return o; }
        if (in.cmd_ok)   { o.reject = true; return o; }
        if (in.odom_v > 0.1) { o.reject = true; return o; }
        if (!in.landed)  { o.reject = true; return o; }
        if (in.rc_is_received && (!in.rc_hover || !in.rc_cmd || !in.rc_centered))
        { o.reject = true; return o; }                           // :119 RC guard
        o.next = AUTO_TAKEOFF; o.offboard_on = true; o.arm = true; return o;
    }
    return o;
}

// AUTO_HOVER case (:174-217)
inline Outcome decide_hover(const Inputs &in)
{
    Outcome o;
    o.next = AUTO_HOVER;
    if (!in.rc_hover || !in.odom_ok) { o.next = MANUAL_CTRL; o.offboard_off = true; return o; }
    if (in.rc_cmd && in.cmd_ok && in.offboard_confirmed) { o.next = CMD_CTRL; return o; }  // :178
    if (in.land_trigger)             { o.next = AUTO_LAND; return o; }      // :193
    return o;
}

// CMD_CTRL case (:218-248)
inline Outcome decide_cmd(const Inputs &in)
{
    Outcome o;
    o.next = CMD_CTRL;
    if (!in.rc_hover || !in.odom_ok)          { o.next = MANUAL_CTRL; o.offboard_off = true; return o; }
    if (!in.rc_cmd || !in.cmd_ok)             { o.next = AUTO_HOVER; return o; }
    // LAND trigger in CMD_CTRL is REJECTED (:243-246) -- stays in CMD_CTRL
    if (in.land_trigger)                      { o.reject = true; return o; }
    return o;
}

// AUTO_TAKEOFF case (:249-283), watchdog = T1-W1 F2
inline Outcome decide_takeoff(const Inputs &in, double speedup_time = 3.0,
                              double abort_timeout = 5.0, double height = 1.0, double start_z = 0.0,
                              double cur_z = 0.0)
{
    Outcome o;
    o.next = AUTO_TAKEOFF;
    if (in.dt_takeoff > speedup_time + abort_timeout && !in.armed && (cur_z - start_z) < 0.3)
    { o.next = MANUAL_CTRL; o.offboard_off = true; return o; }              // :255 watchdog
    if (in.dt_takeoff < speedup_time) return o;                             // speedup window
    if ((cur_z - start_z) >= height) { o.next = AUTO_HOVER; return o; }     // :265 reached
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
