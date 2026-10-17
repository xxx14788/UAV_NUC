#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C3-v88 landing drift guard wiring patch (exact-match, fail-loud).
Run from ~/catkin_ws/src/px4ctrl. Every patch asserts exactly one hit."""
import io, sys

def patch(path, pairs):
    with io.open(path, encoding='utf-8') as f:
        src = f.read()
    for old, new in pairs:
        n = src.count(old)
        assert n == 1, 'FAIL %s: anchor x%d: %r' % (path, n, old[:80])
        src = src.replace(old, new)
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    print('OK %s (%d patches)' % (path, len(pairs)))

# ---------- PX4CtrlParam.h ----------
patch('src/PX4CtrlParam.h', [(
"""\tHaFix_t ha_fix;
""",
"""\tHaFix_t ha_fix;
\t// C3-v88 (2026-10-17): landing-episode perception drift guard
\t// (runaway_root_cause.md B/A candidate rungs; red-40 sim-domain scope;
\t// prereg = tuning_v82/fix_design_prereg_v88.md). Defaults OFF = legacy
\t// bit-exact; real-machine yaml carries no key (no auto deploy).
\tstruct LandGuard_t
\t{
\t\tbool enabled;
\t\tdouble z_floor;
\t\tdouble z_down_extra;
\t\tdouble z_up;
\t\tdouble xy_cap;
\t\tdouble alarm_thresh;
\t\tdouble alarm_sustain;
\t\tbool rung_b2_land_xy_freeze;
\t\tbool rung_b3_descent_cap;
\t\tdouble b3_cap_mps;
\t\tbool rung_a_drift_hold;
\t};
\tLandGuard_t land_guard;
""")])

# ---------- PX4CtrlParam.cpp ----------
patch('src/PX4CtrlParam.cpp', [(
"""\tnh.param("ha_fix/p3_max_recovery_s", ha_fix.p3_max_recovery_s, 30.0); // T1 v11.31 2f P3 契约默认
""",
"""\tnh.param("ha_fix/p3_max_recovery_s", ha_fix.p3_max_recovery_s, 30.0); // T1 v11.31 2f P3 契约默认
\t// C3-v88: landing drift guard (defaults OFF = legacy; SITL yaml enables)
\tnh.param("land_guard/enabled", land_guard.enabled, false);
\tnh.param("land_guard/z_floor", land_guard.z_floor, -0.10);
\tnh.param("land_guard/z_down_extra", land_guard.z_down_extra, 1.20);
\tnh.param("land_guard/z_up", land_guard.z_up, 0.30);
\tnh.param("land_guard/xy_cap", land_guard.xy_cap, 1.50);
\tnh.param("land_guard/alarm_thresh", land_guard.alarm_thresh, 0.40);
\tnh.param("land_guard/alarm_sustain", land_guard.alarm_sustain, 1.0);
\tnh.param("land_guard/rung_b2_land_xy_freeze", land_guard.rung_b2_land_xy_freeze, false);
\tnh.param("land_guard/rung_b3_descent_cap", land_guard.rung_b3_descent_cap, false);
\tnh.param("land_guard/b3_cap_mps", land_guard.b3_cap_mps, 0.35);
\tnh.param("land_guard/rung_a_drift_hold", land_guard.rung_a_drift_hold, false);
""")])

# ---------- input.h ----------
patch('src/input.h', [
(
"""#include "odom_sanity_v2.h"  // Z1.2 (v11.17 2.2)
""",
"""#include "odom_sanity_v2.h"  // Z1.2 (v11.17 2.2)
#include "land_drift_guard.h"  // C3-v88 (2026-10-17) landing drift guard
"""),
(
"""  bool birth_mismatch = false;

  Odom_Data_t();
""",
"""  bool birth_mismatch = false;

  // C3-v88: landing-episode drift guard (clamp-not-reject tube; see
  // land_drift_guard.h). Episode latched by the FSM at AUTO_LAND entries.
  LandGuardConfig land_guard_cfg;
  LandGuardState land_guard_st;
  bool land_guard_alarm_reported = false;

  void land_guard_begin(const Eigen::Vector3d &anchor, double t)
  {
    ::land_guard_begin(land_guard_st, anchor, t);
    land_guard_alarm_reported = false;
  }
  void land_guard_end() { ::land_guard_end(land_guard_st); }
  bool land_guard_active() const { return land_guard_st.active; }
  bool land_guard_alarm() const { return land_guard_st.alarm_latched; }

  Odom_Data_t();
""")])

# ---------- input.cpp ----------
patch('src/input.cpp', [(
"""        msg = *pMsg;
""",
"""        // C3-v88 B1: landing-episode perception tube clamp (clamp-not-reject;
        // placed after P1 so the rebirth gate keeps raw-domain semantics).
        // Wall-contact frames zero the poisoned axis velocity (drift vz
        // ~-0.49 m/s would otherwise keep a 0.74 m/s^2 climb command alive
        // through the Kv damping term).
        if (land_guard_cfg.enabled && land_guard_st.active)
        {
            bool zc = false, xyc = false;
            const Eigen::Vector3d p_g = land_guard_clamp(land_guard_cfg, land_guard_st,
                                                         p_in, now.toSec(), zc, xyc);
            if (zc || xyc)
            {
                if (land_guard_st.clamped == 1 || land_guard_st.clamped % 200 == 0)
                    ROS_ERROR("[LANDDRIFT] tube clamp #%ld raw z=%.2f -> %.2f (anchor z=%.2f), excursion_max=%.2f%s",
                              land_guard_st.clamped, p_in(2), p_g(2), land_guard_st.anchor(2),
                              land_guard_st.excursion_max,
                              land_guard_st.alarm_latched ? " ALARM-LATCHED" : "");
                p_in = p_g;
                if (zc) v_in(2) = 0.0;
                if (xyc) { v_in(0) = 0.0; v_in(1) = 0.0; }
            }
            if (land_guard_st.alarm && !land_guard_alarm_reported)
            {
                land_guard_alarm_reported = true;
                ROS_ERROR("[LANDDRIFT] ALARM latched: excursion %.2fm > %.2fm sustained %.1fs (runaway signature; rung-A consumers take over)",
                          land_guard_st.excursion_max, land_guard_cfg.alarm_thresh,
                          land_guard_cfg.alarm_sustain);
            }
        }
        msg = *pMsg;
""")])

# ---------- px4ctrl_node.cpp ----------
patch('src/px4ctrl_node.cpp', [(
"""    fsm.odom_data.p1_cfg.birth_thresh = param.p1_rebirth.birth_thresh;
""",
"""    fsm.odom_data.p1_cfg.birth_thresh = param.p1_rebirth.birth_thresh;
    // C3-v88: landing drift guard config injection (SITL yaml only)
    fsm.odom_data.land_guard_cfg.enabled = param.land_guard.enabled;
    fsm.odom_data.land_guard_cfg.z_floor = param.land_guard.z_floor;
    fsm.odom_data.land_guard_cfg.z_down_extra = param.land_guard.z_down_extra;
    fsm.odom_data.land_guard_cfg.z_up = param.land_guard.z_up;
    fsm.odom_data.land_guard_cfg.xy_cap = param.land_guard.xy_cap;
    fsm.odom_data.land_guard_cfg.alarm_thresh = param.land_guard.alarm_thresh;
    fsm.odom_data.land_guard_cfg.alarm_sustain = param.land_guard.alarm_sustain;
    fsm.odom_data.land_guard_cfg.rung_b2_land_xy_freeze = param.land_guard.rung_b2_land_xy_freeze;
    fsm.odom_data.land_guard_cfg.rung_b3_descent_cap = param.land_guard.rung_b3_descent_cap;
    fsm.odom_data.land_guard_cfg.b3_cap_mps = param.land_guard.b3_cap_mps;
    fsm.odom_data.land_guard_cfg.rung_a_drift_hold = param.land_guard.rung_a_drift_hold;
""")])

# ---------- PX4CtrlFSM.h ----------
patch('src/PX4CtrlFSM.h', [(
"""\tint ha_stage = 0;
""",
"""\tint ha_stage = 0;
\t// C3-v88 B3: near-ground descent cap engagement latch (AUTO_LAND descending)
\tdouble b3_engaged_z = -999.0;
\tdouble b3_engaged_t = 0.0;
""")])

# ---------- PX4CtrlFSM.cpp ----------
with io.open('src/PX4CtrlFSM.cpp', encoding='utf-8') as f:
    fsm = f.read()
lines = fsm.split('\n')
last_inc = max(i for i, l in enumerate(lines) if l.startswith('#include'))
lines.insert(last_inc + 1, '#include "land_drift_guard.h"  // C3-v88 (2026-10-17)')
fsm = '\n'.join(lines)
with io.open('src/PX4CtrlFSM.cpp', 'w', encoding='utf-8') as f:
    f.write(fsm)
print('OK src/PX4CtrlFSM.cpp (include)')

patch('src/PX4CtrlFSM.cpp', [
# episode bookkeeping
(
"""\tfd_in.ha_blind_land = (ha_stage >= 2);   // T1-v1139 梯①盲降: HAFIX LAND 期 decide_land odom 门旁路
""",
"""\tfd_in.ha_blind_land = (ha_stage >= 2);   // T1-v1139 梯①盲降: HAFIX LAND 期 decide_land odom 门旁路
\t// C3-v88: landing-episode drift guard bookkeeping — episode ends on
\t// landed / disarmed / new takeoff; anchor re-arms at next AUTO_LAND entry.
\tif (odom_data.land_guard_active() &&
\t    (fd_in.landed || !fd_in.armed || state == AUTO_TAKEOFF))
\t\todom_data.land_guard_end();
"""),
# HAFIX A-rung wiring
(
"""\t\tconst bool odom_dead = !odom_is_received(now_time);
""",
"""\t\tconst bool odom_dead = !odom_is_received(now_time);
\t\t// C3-v88 A-rung: drift alarm feeds the same HAFIX ladder (blind-land
\t\t// handover). The alarm is an already-sustained confirmed signature, so
\t\t// the dead_s confirmation window is waived (dead_elapsed floored).
\t\tconst bool drift_alarm = param.land_guard.enabled && param.land_guard.rung_a_drift_hold &&
\t\t    odom_data.land_guard_alarm();
"""),
(
"""\t\tha_in.flying = fd_in.armed && !fd_in.landed && odom_dead; // watch 域=飞行∧流死
""",
"""\t\tha_in.flying = fd_in.armed && !fd_in.landed && (odom_dead || drift_alarm); // watch 域=飞行∧(流死∨漂移告警) C3-v88
"""),
(
"""\t\tha_in.dead_elapsed = (ha_stage != 0) ? (now_time - ha_dead_since).toSec() : 0.0;
""",
"""\t\tha_in.dead_elapsed = (ha_stage != 0) ? (now_time - ha_dead_since).toSec() : 0.0;
\t\tif (drift_alarm && ha_in.dead_elapsed < param.ha_fix.dead_s)
\t\t\tha_in.dead_elapsed = param.ha_fix.dead_s; // C3-v88: alarm = confirmed signature, waive watch window
"""),
# AUTO_LAND entry site 1 (HAFIX auto_land)
(
"""\t\t\tROS_ERROR("[HAFIX] dead %.1fs >= %.1fs -> AUTO_LAND (blind-descend on stale odom)",
\t\t\t          ha_in.dead_elapsed, param.ha_fix.dead_s);
""",
"""\t\t\tROS_ERROR("[HAFIX] dead %.1fs >= %.1fs -> AUTO_LAND (blind-descend on stale odom)",
\t\t\t          ha_in.dead_elapsed, param.ha_fix.dead_s);
\t\t\tif (param.land_guard.enabled)
\t\t\t{
\t\t\t\todom_data.land_guard_begin(odom_data.p, now_time.toSec());
\t\t\t\tb3_engaged_z = -999.0;
\t\t\t}
"""),
# AUTO_LAND entry site 1b (HAFIX re-assert)
(
"""\t\t\tROS_ERROR("[HAFIX] re-assert AUTO_LAND (blind-descend FSM bounce guard)");
""",
"""\t\t\tROS_ERROR("[HAFIX] re-assert AUTO_LAND (blind-descend FSM bounce guard)");
\t\t\tif (param.land_guard.enabled)
\t\t\t{
\t\t\t\todom_data.land_guard_begin(odom_data.p, now_time.toSec());
\t\t\t\tb3_engaged_z = -999.0;
\t\t\t}
"""),
# AUTO_LAND entry site 2 (AUTO_HOVER -> AUTO_LAND)
(
"""\t\telse if (fd_o.next == fsm_decision::AUTO_LAND)
\t\t{
\t\t\tstate = AUTO_LAND;
\t\t\tset_start_pose_for_takeoff_land(odom_data);

\t\t\tROS_INFO("\\033[32m[px4ctrl] AUTO_HOVER(L2) --> AUTO_LAND\\033[32m");
""",
"""\t\telse if (fd_o.next == fsm_decision::AUTO_LAND)
\t\t{
\t\t\tstate = AUTO_LAND;
\t\t\tset_start_pose_for_takeoff_land(odom_data);
\t\t\tif (param.land_guard.enabled)
\t\t\t{
\t\t\t\todom_data.land_guard_begin(odom_data.p, now_time.toSec()); // C3-v88: episode anchor at land entry
\t\t\t\tb3_engaged_z = -999.0;
\t\t\t}

\t\t\tROS_INFO("\\033[32m[px4ctrl] AUTO_HOVER(L2) --> AUTO_LAND\\033[32m");
"""),
# AUTO_LAND -> AUTO_HOVER bounce: B2 xy freeze
(
"""\t\telse if (fd_o.next == fsm_decision::AUTO_HOVER)
\t\t{
\t\t\tstate = AUTO_HOVER;
\t\t\tset_hov_with_odom();
\t\t\tdes = get_hover_des();
\t\t\tROS_INFO("[px4ctrl] From AUTO_LAND to AUTO_HOVER(L2)!");
""",
"""\t\telse if (fd_o.next == fsm_decision::AUTO_HOVER)
\t\t{
\t\t\tstate = AUTO_HOVER;
\t\t\tset_hov_with_odom();
\t\t\t// C3-v88 B2: near-ground re-anchor xy freeze (horizontal ratchet cut;
\t\t\t// rung default OFF). Note B1 already bounds the re-anchor inside the
\t\t\t// tube via the clamped perception; B2 pins it to the episode anchor.
\t\t\tif (param.land_guard.enabled && param.land_guard.rung_b2_land_xy_freeze &&
\t\t\t    odom_data.land_guard_active() && odom_data.p(2) < 0.6)
\t\t\t{
\t\t\t\tEigen::Vector3d hp = hover_pose.head<3>();
\t\t\t\tland_guard_b2_freeze_xy(odom_data.land_guard_cfg, odom_data.land_guard_st, hp);
\t\t\t\thover_pose.head<3>() = hp;
\t\t\t}
\t\t\tdes = get_hover_des();
\t\t\tROS_INFO("[px4ctrl] From AUTO_LAND to AUTO_HOVER(L2)!");
"""),
# descending branch: B3 descent cap
(
"""\t\telse if (!fd_o.disarm) // descending
\t\t{
\t\t\tdes = get_takeoff_land_des(-param.takeoff_land.speed);
\t\t}
""",
"""\t\telse if (!fd_o.disarm) // descending
\t\t{
\t\t\tdes = get_takeoff_land_des(-param.takeoff_land.speed);
\t\t\t// C3-v88 B3: near-ground descent cap (rung default OFF), target-
\t\t\t// continuous: capped target never below the engage-point descent line.
\t\t\tif (param.land_guard.enabled && param.land_guard.rung_b3_descent_cap &&
\t\t\t    odom_data.land_guard_active() && odom_data.p(2) < 0.6)
\t\t\t{
\t\t\t\tif (b3_engaged_z < -100.0 || odom_data.p(2) > b3_engaged_z + 0.05)
\t\t\t\t{
\t\t\t\t\tb3_engaged_z = odom_data.p(2);
\t\t\t\t\tb3_engaged_t = now_time.toSec();
\t\t\t\t}
\t\t\t\tdes.p(2) = land_guard_b3_target_z(des.p(2), b3_engaged_z, b3_engaged_t,
\t\t\t\t                                  now_time.toSec(), param.land_guard.b3_cap_mps);
\t\t\t\tdes.v(2) = std::max(des.v(2), -param.land_guard.b3_cap_mps);
\t\t\t}
\t\t}
""")])

# ---------- CMakeLists.txt ----------
patch('CMakeLists.txt', [(
"""  catkin_add_gtest(test_cmdresp_gate
    test/test_cmdresp_gate.cpp)
  target_link_libraries(test_cmdresp_gate ${catkin_LIBRARIES})
endif()""",
"""  catkin_add_gtest(test_cmdresp_gate
    test/test_cmdresp_gate.cpp)
  target_link_libraries(test_cmdresp_gate ${catkin_LIBRARIES})

  # C3-v88: landing drift guard deterministic chain-break dry test
  # (three frame-level runaway signature types + transparency negatives)
  catkin_add_gtest(test_land_drift_guard
    test/test_land_drift_guard.cpp)
  target_link_libraries(test_land_drift_guard ${catkin_LIBRARIES})
endif()""")])

# ---------- ctrl_param_sitl.yaml ----------
with io.open('config/ctrl_param_sitl.yaml', encoding='utf-8') as f:
    y = f.read()
if 'land_guard:' not in y:
    y += """
# C3-v88 (2026-10-17): landing-episode drift guard — runaway root-cause fix
# (tuning_v82/runaway_root_cause.md; prereg = tuning_v82/fix_design_prereg_v88.md)
# B1 tube clamp live; B2/B3/A rungs default OFF (red-42 single-variable ladder).
# Real-machine yaml carries no key = OFF there (red-40: no auto deploy).
land_guard:
  enabled: true
  z_floor: -0.10
  z_down_extra: 1.20
  z_up: 0.30
  xy_cap: 1.50
  alarm_thresh: 0.40
  alarm_sustain: 1.0
  rung_b2_land_xy_freeze: false
  rung_b3_descent_cap: false
  b3_cap_mps: 0.35
  rung_a_drift_hold: false
"""
    with io.open('config/ctrl_param_sitl.yaml', 'w', encoding='utf-8') as f:
        f.write(y)
    print('OK config/ctrl_param_sitl.yaml (land_guard section appended)')
else:
    print('SKIP yaml (already has land_guard)')
print('ALL PATCHES DONE')
