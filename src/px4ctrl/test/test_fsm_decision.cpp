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


// ---------- P1 (2026-10-04): rebirth birth-offset gate ----------
// Latch semantics live in Odom_Data_t::feed (gap>gap_sec, offset>birth_thresh)
// and clear on disarm; these tests cover the pure-decision face.
TEST(FsmP1BirthMismatch, HoverEntryRejectedOnMismatch)
{
    Inputs i = base(); i.enter_hover = true; i.odom_ok = true; i.birth_mismatch = true;
    Outcome o = decide_manual(i);
    EXPECT_TRUE(o.reject); EXPECT_EQ(RJ_BIRTH_MISMATCH, o.reason);
}
TEST(FsmP1BirthMismatch, HoverEntryOkWhenClean)
{
    Inputs i = base(); i.enter_hover = true; i.odom_ok = true; i.birth_mismatch = false;
    EXPECT_EQ(AUTO_HOVER, decide_manual(i).next);
}
TEST(FsmP1BirthMismatch, U27LandRejectedOnMismatch)
{
    Inputs i = base(); i.land_trigger = true; i.armed = true; i.no_rc = true;
    i.odom_ok = true; i.odom_v = 0.3; i.birth_mismatch = true;
    Outcome o = decide_manual(i);
    EXPECT_TRUE(o.reject); EXPECT_EQ(RJ_BIRTH_MISMATCH, o.reason);
}
TEST(FsmP1BirthMismatch, U27LandAcceptedWhenClean)
{
    Inputs i = base(); i.land_trigger = true; i.armed = true; i.no_rc = true;
    i.odom_ok = true; i.odom_v = 0.3; i.birth_mismatch = false;
    EXPECT_EQ(AUTO_HOVER, decide_manual(i).next);
}
TEST(FsmP1BirthMismatch, PassiveManualNotBlocked)
{
    // no request in flight: mismatch latch alone does not force anything
    Inputs i = base(); i.birth_mismatch = true;
    Outcome o = decide_manual(i);
    EXPECT_EQ(MANUAL_CTRL, o.next); EXPECT_FALSE(o.reject);
}

// ---------- T1-v1139 P-1/P-2: HAFIX 梯②③语义(KILL=DO_FLIGHTTERMINATION param1=1.0;disarm 后置 landed 门) ----------
static HafixInputs habase()
{
    HafixInputs h;
    h.enabled = true;
    h.dead_s = 5.0; h.kill_s = 15.0;
    return h;
}
TEST(HafixP1, KillSemanticsConstants)
{
    // P-1 核心: MAV_CMD_DO_FLIGHTTERMINATION, param1=1.0=engage(0=cancel 反向 bug)
    EXPECT_EQ(400, HAFIX_KILL_MAVCMD);
    EXPECT_DOUBLE_EQ(1.0, HAFIX_KILL_PARAM1_ENGAGE);
    // 二次修复(干测 run_DRILLD1_N8P_042425 实证 400 被活跃 setpoint 流覆盖):
    // 补发 179+param2=21196 forced kill(disarm -f 同款,空中停电机)
    EXPECT_EQ(179, HAFIX_KILL2_MAVCMD);
    EXPECT_DOUBLE_EQ(0.0, HAFIX_KILL2_DISARM);
    EXPECT_DOUBLE_EQ(21196, HAFIX_KILL2_FORCE_MAGIC);
}
TEST(HafixP1, KillFiresAtDeadlineWhileFlying)
{
    HafixInputs h = habase(); h.stage = 2; h.flying = true;
    h.dead_elapsed = 20.0; // >= dead_s+kill_s=20
    HafixAction a = decide_hafix(h);
    EXPECT_TRUE(a.kill_fire);
    EXPECT_EQ(3, a.stage_next);
}
TEST(HafixP1, KillRetriesWhileStage3Flying)
{
    HafixInputs h = habase(); h.stage = 3; h.flying = true;
    h.dead_elapsed = 25.0; h.landed = false; h.armed = true;
    HafixAction a = decide_hafix(h);
    EXPECT_TRUE(a.kill_fire);   // 持续重掷(调用侧 1Hz 限频)
    EXPECT_EQ(3, a.stage_next); // 不复位
}
TEST(HafixP1, KillNotFiredBeforeDeadline)
{
    HafixInputs h = habase(); h.stage = 2; h.flying = true;
    h.dead_elapsed = 19.9; // < 20
    HafixAction a = decide_hafix(h);
    EXPECT_FALSE(a.kill_fire);
    EXPECT_FALSE(a.disarm_postposed);
    EXPECT_EQ(2, a.stage_next);
}
TEST(HafixP2, DisarmNeverFiresAirborne)
{
    // P-2 反向 bug 用例: KILL 已发但未落地 → 绝不 disarm(空中 disarm 必被 PX4 拒)
    HafixInputs h = habase(); h.stage = 3; h.flying = true;
    h.landed = false; h.armed = true; h.dead_elapsed = 30.0;
    HafixAction a = decide_hafix(h);
    EXPECT_FALSE(a.disarm_postposed);
    EXPECT_TRUE(a.kill_fire);   // KILL 梯独立持续
}
TEST(HafixP2, DisarmPostposedOnLandedGate)
{
    // landed 门开且仍 armed → disarm 收尾梯激活;持有期不清 stage(disarm 被拒不丢梯)
    HafixInputs h = habase(); h.stage = 3; h.flying = false;
    h.landed = true; h.armed = true;
    HafixAction a = decide_hafix(h);
    EXPECT_TRUE(a.disarm_postposed);
    EXPECT_FALSE(a.cleared);
    EXPECT_EQ(3, a.stage_next);
}
TEST(HafixP2, ClearedWhenDisarmedAfterKill)
{
    // KILL 后 FC 已 disarm(armed=false,landed=true) → cleared 复位
    HafixInputs h = habase(); h.stage = 3; h.flying = false;
    h.landed = true; h.armed = false;
    HafixAction a = decide_hafix(h);
    EXPECT_FALSE(a.disarm_postposed);
    EXPECT_TRUE(a.cleared);
    EXPECT_EQ(0, a.stage_next);
}
TEST(HafixP2, LadderFlowWatchLandKill)
{
    // 全梯序: watch(0→1) → AUTO_LAND(1→2) → KILL(2→3) → disarm(landed 门) → cleared
    HafixInputs h = habase(); h.flying = true; h.landed = false; h.armed = true;
    HafixAction a1 = decide_hafix(h);                     // stage 0
    EXPECT_TRUE(a1.watch_start); EXPECT_EQ(1, a1.stage_next);
    h.stage = 1; h.dead_elapsed = 5.0;
    HafixAction a2 = decide_hafix(h);
    EXPECT_TRUE(a2.auto_land); EXPECT_EQ(2, a2.stage_next);
    h.stage = 2; h.dead_elapsed = 20.0;
    HafixAction a3 = decide_hafix(h);
    EXPECT_TRUE(a3.kill_fire); EXPECT_EQ(3, a3.stage_next);
    h.stage = 3; h.dead_elapsed = 22.0; h.flying = false; h.landed = true;
    HafixAction a4 = decide_hafix(h);
    EXPECT_TRUE(a4.disarm_postposed); EXPECT_EQ(3, a4.stage_next);
    h.armed = false;
    HafixAction a5 = decide_hafix(h);
    EXPECT_TRUE(a5.cleared); EXPECT_EQ(0, a5.stage_next);
}
TEST(HafixP2, DisabledIsNoop)
{
    HafixInputs h = habase(); h.enabled = false; h.stage = 2; h.flying = true; h.dead_elapsed = 99.0;
    HafixAction a = decide_hafix(h);
    EXPECT_FALSE(a.kill_fire); EXPECT_FALSE(a.auto_land); EXPECT_FALSE(a.cleared);
    EXPECT_EQ(2, a.stage_next); // stage 原样
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
