// T1-F3 (2026-09-30): exhaustive transition tests over the mirror decision
// functions (fsm_decision.h). Mirrors PX4CtrlFSM.cpp@HEAD including T1-W1
// self-heal guards. Documentation-grade; refactor queued (F3_fsm_audit.md).
#include "fsm_decision.h"
#include <gtest/gtest.h>

using namespace fsm_decision;

static Inputs base()
{
    Inputs i;
    i.odom_ok = true;
    i.rc_is_received = true;
    i.rc_hover = true;   // in an auto mode: hover switch engaged
    i.rc_cmd = true;     // command switch engaged
    i.landed = true;
    return i;
}

// ---------- STEP0 global self-heal (T1-W1 F3) ----------
TEST(FsmStep0, StaleStateDisarmedResetsToManual)
{
    for (State s : {AUTO_HOVER, CMD_CTRL, AUTO_TAKEOFF, AUTO_LAND})
    {
        Inputs i = base(); i.armed = false; i.fcu_state_stale = true;
        EXPECT_EQ(MANUAL_CTRL, step0_global(s, i).next) << s;
    }
}
TEST(FsmStep0, ArmedNeverResets)
{
    Inputs i = base(); i.armed = true; i.fcu_state_stale = true;
    EXPECT_EQ(CMD_CTRL, step0_global(CMD_CTRL, i).next);
}
TEST(FsmStep0, FreshStateNoReset)
{
    Inputs i = base(); i.armed = false; i.fcu_state_stale = false;
    EXPECT_EQ(AUTO_HOVER, step0_global(AUTO_HOVER, i).next);
}
TEST(FsmStep0, ManualStaysManual)
{
    Inputs i = base(); i.armed = false; i.fcu_state_stale = true;
    EXPECT_EQ(MANUAL_CTRL, step0_global(MANUAL_CTRL, i).next);
}

// ---------- MANUAL_CTRL ----------
TEST(FsmManual, HoverEntryGates)
{
    Inputs i = base(); i.enter_hover = true;
    i.odom_ok = false; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.enter_hover = true; i.cmd_ok = true; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.enter_hover = true; i.odom_v = 3.1; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.enter_hover = true; i.odom_v = 2.9;
    Outcome o = decide_manual(i);
    EXPECT_EQ(AUTO_HOVER, o.next); EXPECT_TRUE(o.offboard_on);
}
TEST(FsmManual, TakeoffGates)
{
    Inputs i = base(); i.takeoff_trigger = true;
    i.odom_ok = false; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.takeoff_trigger = true; i.cmd_ok = true; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.takeoff_trigger = true; i.odom_v = 0.2; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.takeoff_trigger = true; i.landed = false; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.takeoff_trigger = true; i.rc_hover = false; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.takeoff_trigger = true; i.rc_cmd = false; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.takeoff_trigger = true; i.rc_centered = false; EXPECT_TRUE(decide_manual(i).reject);
    i = base(); i.takeoff_trigger = true; i.rc_hover = true; i.rc_cmd = true; i.rc_centered = true;
    Outcome o = decide_manual(i);
    EXPECT_EQ(AUTO_TAKEOFF, o.next); EXPECT_TRUE(o.offboard_on); EXPECT_TRUE(o.arm);
}
TEST(FsmManual, NoRcConnectedSkipsRcGuard)
{
    Inputs i = base(); i.takeoff_trigger = true; i.rc_is_received = false;
    EXPECT_EQ(AUTO_TAKEOFF, decide_manual(i).next);  // :110 check only if RC connected
}

// ---------- AUTO_HOVER ----------
TEST(FsmHover, ExitsToManualOnRcOrOdomLoss)
{
    Inputs i = base(); i.rc_hover = false;
    Outcome o = decide_hover(i);
    EXPECT_EQ(MANUAL_CTRL, o.next); EXPECT_TRUE(o.offboard_off);
    i = base(); i.odom_ok = false;
    o = decide_hover(i);
    EXPECT_EQ(MANUAL_CTRL, o.next); EXPECT_TRUE(o.offboard_off);
}
TEST(FsmHover, EntersCmdOnlyWithOffboardConfirmed)
{
    Inputs i = base(); i.rc_cmd = true; i.cmd_ok = true;
    EXPECT_EQ(AUTO_HOVER, decide_hover(i).next);          // no OFFBOARD confirmation -> stay
    i.offboard_confirmed = true;
    EXPECT_EQ(CMD_CTRL, decide_hover(i).next);
}
TEST(FsmHover, LandTriggerFromHover)
{
    Inputs i = base(); i.land_trigger = true;
    EXPECT_EQ(AUTO_LAND, decide_hover(i).next);
}

// ---------- CMD_CTRL ----------
TEST(FsmCmd, ExitsToManualOnRcOrOdomLoss)
{
    Inputs i = base(); i.rc_hover = false;
    Outcome o = decide_cmd(i);
    EXPECT_EQ(MANUAL_CTRL, o.next); EXPECT_TRUE(o.offboard_off);
    i = base(); i.odom_ok = false;
    EXPECT_EQ(MANUAL_CTRL, decide_cmd(i).next);
}
TEST(FsmCmd, FallsBackToHoverOnCmdOrModeLoss)
{
    Inputs i = base(); i.rc_cmd = false; EXPECT_EQ(AUTO_HOVER, decide_cmd(i).next);
    i = base(); i.rc_cmd = true; i.cmd_ok = false; EXPECT_EQ(AUTO_HOVER, decide_cmd(i).next);
}
TEST(FsmCmd, LandTriggerRejectedInCmd)
{
    Inputs i = base(); i.rc_cmd = true; i.cmd_ok = true; i.land_trigger = true;
    Outcome o = decide_cmd(i);
    EXPECT_TRUE(o.reject); EXPECT_EQ(CMD_CTRL, o.next);
}

// ---------- AUTO_TAKEOFF (T1-W1 F2 watchdog) ----------
TEST(FsmTakeoff, WatchdogBackToManualWhenNeverAirborne)
{
    Inputs i = base();
    i.dt_takeoff = 3.0 + 5.0 + 0.1; i.armed = false;
    Outcome o = decide_takeoff(i, 3.0, 5.0, 1.0, 0.0, 0.2);   // dZ=0.2 < 0.3
    EXPECT_EQ(MANUAL_CTRL, o.next); EXPECT_TRUE(o.offboard_off);
}
TEST(FsmTakeoff, WatchdogRespectsArmedState)
{
    Inputs i = base();
    i.dt_takeoff = 1e9; i.armed = true;                       // armed: never abort (red line)
    EXPECT_EQ(AUTO_TAKEOFF, decide_takeoff(i, 3.0, 5.0, 1.0, 0.0, 0.0).next);
}
TEST(FsmTakeoff, WatchdogRespectsClimbProgress)
{
    Inputs i = base();
    i.dt_takeoff = 1e9; i.armed = false;
    EXPECT_EQ(AUTO_TAKEOFF, decide_takeoff(i, 3.0, 5.0, 1.0, 0.0, 0.5).next);  // dZ>=0.3
}
TEST(FsmTakeoff, SpeedupWindowHolds)
{
    Inputs i = base(); i.dt_takeoff = 2.9;
    EXPECT_EQ(AUTO_TAKEOFF, decide_takeoff(i, 3.0, 5.0, 1.0, 0.0, 0.0).next);
}
TEST(FsmTakeoff, ReachesHeightToHover)
{
    Inputs i = base(); i.dt_takeoff = 10.0; i.armed = true;
    EXPECT_EQ(AUTO_HOVER, decide_takeoff(i, 3.0, 5.0, 1.0, 0.0, 1.0).next);
}
TEST(FsmTakeoff, ClimbingStays)
{
    Inputs i = base(); i.dt_takeoff = 10.0; i.armed = true;
    EXPECT_EQ(AUTO_TAKEOFF, decide_takeoff(i, 3.0, 5.0, 1.0, 0.0, 0.5).next);
}

// ---------- AUTO_LAND ----------
TEST(FsmLand, ExitsToManualOnRcOrOdomLoss)
{
    Inputs i = base(); i.rc_hover = false;
    Outcome o = decide_land(i);
    EXPECT_EQ(MANUAL_CTRL, o.next); EXPECT_TRUE(o.offboard_off);
    i = base(); i.odom_ok = false;
    EXPECT_EQ(MANUAL_CTRL, decide_land(i).next);
}
TEST(FsmLand, CmdSwitchOffAbortsToHover)
{
    Inputs i = base(); i.rc_cmd = false;
    EXPECT_EQ(AUTO_HOVER, decide_land(i).next);
}
TEST(FsmLand, DescendingStays)
{
    Inputs i = base(); i.landed = false;
    EXPECT_EQ(AUTO_LAND, decide_land(i).next);
}
TEST(FsmLand, TouchdownDisarmsToManual)
{
    Inputs i = base(); i.landed = true; i.px4_on_ground = true;
    Outcome o = decide_land(i);
    EXPECT_EQ(MANUAL_CTRL, o.next); EXPECT_TRUE(o.disarm); EXPECT_TRUE(o.offboard_off);
}
TEST(FsmLand, LandedButNotOnGroundWaits)
{
    Inputs i = base(); i.landed = true; i.px4_on_ground = false;
    EXPECT_EQ(AUTO_LAND, decide_land(i).next);   // rotor-low-speed window (RLS paused, audit #7)
}

// ---------- composition: STEP0 preempts state logic ----------
TEST(FsmComposition, Step0PreemptsStateLogic)
{
    Inputs i = base(); i.armed = false; i.fcu_state_stale = true; i.rc_cmd = true; i.cmd_ok = true;
    Outcome s0 = step0_global(CMD_CTRL, i);
    EXPECT_EQ(MANUAL_CTRL, s0.next);
}


// ---------- U2.7 (2026-10-04): LAND in MANUAL_CTRL ----------
// Forensics: run_U3PO_211438 — odom dropout -> MANUAL_CTRL while armed,
// harness LAND (1Hz, 120s) silently ignored, armed hover until tree kill.
TEST(FsmManualLand, AcceptedNoRcArmedOdomOk)
{
    Inputs i = base(); i.land_trigger = true; i.armed = true;
    i.no_rc = true; i.odom_ok = true; i.odom_v = 0.3; i.landed = false; // airborne hover
    Outcome o = decide_manual(i);
    EXPECT_EQ(AUTO_HOVER, o.next); EXPECT_TRUE(o.offboard_on); EXPECT_FALSE(o.reject);
}
TEST(FsmManualLand, RejectedDisarmed)
{
    Inputs i = base(); i.land_trigger = true; i.armed = false; i.no_rc = true;
    Outcome o = decide_manual(i);
    EXPECT_TRUE(o.reject); EXPECT_EQ(RJ_DISARMED, o.reason); EXPECT_EQ(MANUAL_CTRL, o.next);
}
TEST(FsmManualLand, RejectedRcManualPriority)
{
    Inputs i = base(); i.land_trigger = true; i.armed = true; i.no_rc = false; // RC connected
    Outcome o = decide_manual(i);
    EXPECT_TRUE(o.reject); EXPECT_EQ(RJ_MANUAL_PRIO, o.reason);
}
TEST(FsmManualLand, RejectedNoOdom)
{
    Inputs i = base(); i.land_trigger = true; i.armed = true; i.no_rc = true; i.odom_ok = false;
    Outcome o = decide_manual(i);
    EXPECT_TRUE(o.reject); EXPECT_EQ(RJ_MANUAL_PRIO, o.reason);
}
TEST(FsmManualLand, RejectedFastOdomVel)
{
    Inputs i = base(); i.land_trigger = true; i.armed = true; i.no_rc = true; i.odom_v = 3.1;
    Outcome o = decide_manual(i);
    EXPECT_TRUE(o.reject); EXPECT_EQ(RJ_MANUAL_PRIO, o.reason);
}
TEST(FsmManualLand, TwoTickLandingPath)
{
    // accepted tick -> AUTO_HOVER; next tick with LAND still streaming goes AUTO_LAND
    Inputs i = base(); i.land_trigger = true; i.armed = true; i.no_rc = true;
    EXPECT_EQ(AUTO_HOVER, decide_manual(i).next);
    Outcome h = decide_hover(i); // hover inputs: rc_hover true, no cmd stream
    EXPECT_EQ(AUTO_LAND, h.next);
}

// ---------- F3 v2 strict-mirror fix boundary ----------
// Source else-if chain: when rc_cmd&&cmd_ok but OFFBOARD not yet confirmed,
// the request branch is consumed and LAND is NOT evaluated on that tick.
TEST(FsmHover, CmdWaitOffboardBlocksLandSameTick)
{
    Inputs i = base(); i.rc_cmd = true; i.cmd_ok = true;
    i.offboard_confirmed = false; i.land_trigger = true;
    EXPECT_EQ(AUTO_HOVER, decide_hover(i).next); // stay, do NOT take LAND yet
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
