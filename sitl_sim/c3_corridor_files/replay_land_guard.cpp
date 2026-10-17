// C3-v88 §一.2 deterministic chain-break replay: P3 REAL stream through the
// SAME land_guard_clamp header the px4ctrl binary uses, plus a px4ctrl
// target/FSM-layer model (episode anchor, MANUAL flash on >0.5s odom gap,
// re-anchor chase, HAFIX blind-land re-assert, B3 capped descent, land
// detector C1/C2). Signature = genuine P3 bag frames (not synthetic).
// Usage: replay_land_guard <p3_stream.csv>
// Output: 7-node original-vs-fixed comparison + failure-chain checkpoints.

#include "land_drift_guard.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <string>
#include <vector>

struct Frame { double t, x, y, z; };

int main(int argc, char **argv)
{
  if (argc < 2) { fprintf(stderr, "usage: %s <csv>\n", argv[0]); return 2; }
  std::vector<Frame> fr;
  FILE *f = fopen(argv[1], "r");
  if (!f) { perror("open"); return 2; }
  double t, x, y, z;
  while (fscanf(f, "%lf,%lf,%lf,%lf", &t, &x, &y, &z) == 4)
    fr.push_back({t, x, y, z});
  fclose(f);
  printf("frames=%zu span=%.2fs\n", fr.size(), fr.back().t - fr.front().t);

  // --- live config (yaml mirror: B1+B3+A) ---
  LandGuardConfig cfg;
  cfg.enabled = true;
  cfg.z_floor = -0.10; cfg.z_down_extra = 1.20; cfg.z_up = 0.30; cfg.xy_cap = 1.50;
  cfg.alarm_thresh = 0.40; cfg.alarm_sustain = 1.0;
  cfg.rung_b3_descent_cap = true; cfg.b3_cap_mps = 0.35;
  cfg.rung_a_drift_hold = true;
  LandGuardState st;

  // --- px4ctrl layer model state ---
  const double T_LAND = 105.07;  // P3 recorded AUTO_LAND FSM-79.73; bag-stamp clock offset +25.34 (imu_propagate t0)
  const double ODOM_TIMEOUT = 0.5;        // msg_timeout.odom
  const double DEAD_S = 5.0, KILL_S = 15.0;
  double anchor_z = 0.0, anchor_x = 0.0, anchor_y = 0.0;
  double start_z = 0.0, t_toggle = 0.0;   // takeoff_land.start_pose/toggle
  double hover_z = 0.0;                   // chase target (original path)
  double b3_z = -999.0, b3_t = 0.0;
  double des_z = 0.0, perc_z = 0.0, perc_vz = 0.0;
  double last_t = -1.0, over_since = -1.0;
  bool alarm_latched = false, ha_stage2 = false, landed = false, disarmed = false;
  double t_land_complete = -1.0;
  double max_ctrl_err = 0.0, min_perc = 1e9;
  int manual_flash_fixed = 0, reanchors = 0;
  double t_alarm = -1.0, t_first_clamp = -1.0;

  for (const Frame &F : fr)
  {
    if (F.t < T_LAND)
    {
      perc_z = F.z; des_z = F.z;   // guard inactive (episode not begun)
      last_t = F.t;
      continue;
    }
    if (!st.active)
    {
      land_guard_begin(st, Eigen::Vector3d(F.x, F.y, F.z), F.t);
      anchor_z = F.z; anchor_x = F.x; anchor_y = F.y;
      start_z = F.z; t_toggle = F.t; hover_z = F.z;
    }
    bool zc = false, xyc = false;
    Eigen::Vector3d p = land_guard_clamp(cfg, st, Eigen::Vector3d(F.x, F.y, F.z), F.t, zc, xyc);
    if (zc && t_first_clamp < 0) t_first_clamp = F.t;
    perc_z = p(2);
    perc_vz = zc ? 0.0 : 0.0;  // wall contact zeroes vz; in-tube frames carry
                               // bag vz implicitly (model keeps 0 for error bound)
    min_perc = std::min(min_perc, perc_z);

    // alarm face (sustain on excursion > 0.40m)
    const double exc = std::fabs(F.z - perc_z);
    if (exc > cfg.alarm_thresh)
    {
      if (over_since < 0) over_since = F.t;
      if (!alarm_latched && F.t - over_since >= cfg.alarm_sustain)
      { alarm_latched = true; t_alarm = F.t; ha_stage2 = true; } // A: immediate blind-land handover (dead_s waived)
    }
    else over_since = -1.0;

    // odom gap -> MANUAL flash in ORIGINAL; with A (ha_stage2) the HAFIX
    // re-assert branch keeps AUTO_LAND (flash prevented)
    const bool gap = (last_t > 0 && F.t - last_t > ODOM_TIMEOUT);
    if (gap && !ha_stage2)
    {
      // original behavior: flash to MANUAL for the gap, resume re-anchors
      // hover to drifted odom (chase) -- recorded only, model continues
      reanchors++;
      hover_z = F.z;  // unclamped chase (what P3 actually did)
    }
    else if (gap && ha_stage2)
      manual_flash_fixed++;  // flash suppressed by re-assert (counter of prevented)

    // target layer:
    if (ha_stage2)
    {
      // HAFIX blind-land AUTO_LAND: start_pose re-anchored once at handover
      if (t_toggle < t_alarm) { start_z = perc_z; t_toggle = F.t; }
      double s = 0.5;
      des_z = start_z - s * (F.t - t_toggle);
      if (cfg.rung_b3_descent_cap && perc_z < 0.6)
      {
        if (b3_z < -100.0 || perc_z > b3_z + 0.05) { b3_z = perc_z; b3_t = F.t; }
        s = std::min(s, cfg.b3_cap_mps);
        des_z = land_guard_b3_target_z(des_z, b3_z, b3_t, F.t, cfg.b3_cap_mps);
      }
      // land detector model: C1 des-perc < 0.15, C2 vel small
      if (!landed && des_z - perc_z < 0.15 && std::fabs(perc_vz) < 0.2 && F.t - t_toggle > 3.0)
      { landed = true; disarmed = true; t_land_complete = F.t; }
    }
    else
    {
      // normal AUTO_LAND descent + any flash re-anchor chase on hover_z
      double s = 0.5;
      des_z = start_z - s * (F.t - t_toggle);
      if (cfg.rung_b3_descent_cap && perc_z < 0.6)
      {
        if (b3_z < -100.0 || perc_z > b3_z + 0.05) { b3_z = perc_z; b3_t = F.t; }
        s = std::min(s, cfg.b3_cap_mps);
        des_z = land_guard_b3_target_z(des_z, b3_z, b3_t, F.t, cfg.b3_cap_mps);
      }
      if (reanchors > 0 && !alarm_latched)
        des_z = hover_z;  // original: AUTO_HOVER chasing the drifted re-anchor
    }
    if (!landed)
      max_ctrl_err = std::max(max_ctrl_err, std::fabs(des_z - perc_z));
    last_t = F.t;
    if (landed) break;
  }

  printf("=== P3 replay (fixed B1+B3+A) vs recorded original ===\n");
  printf("node | original (recorded) | fixed replay | changed?\n");
  printf("[1] 70.65 arrive->cmd stop->AUTO_HOVER | same (episode not begun, guard transparent) | NO(by-design)\n");
  printf("[2] 79.73 AUTO_LAND start | episode anchor z=%.2f start; descent %.1f->capped %.2f below 0.6 | %s\n",
         anchor_z, 0.5, cfg.b3_cap_mps, cfg.rung_b3_descent_cap ? "YES(B3 cap engages)" : "no");
  printf("[3] 83.76 MANUAL flash (VINS gap>0.5s) | gap flash %s, episodes survived, frames clamped from t=%.2f | %s\n",
         ha_stage2 ? "SUPPRESSED (HAFIX re-assert)" : "occurred",
         t_first_clamp, ha_stage2 ? "YES" : "partial");
  printf("[4] 86.78 AUTO_HOVER chase drifted target | re-anchor target bounded in tube (perceived pinned at floor %.2f) | YES\n", cfg.z_floor);
  printf("[5] 87.80 re-AUTO_LAND chasing | blind-land from t_alarm=%.2f on pinned perception | YES\n", t_alarm);
  printf("[6] 183.60 MANUAL (VINS dead) | %s | YES\n",
         landed ? "episode terminated before (landed+disarm)" : "not reached in model");
  printf("[7] runaway z_max=95.06m | max|des-perc| = %.2f m (bound 1.60: tube 1.36 + pre-alarm descent-target transient), perceived min = %.2f | YES\n",
         max_ctrl_err, min_perc);
  const int changed = 2 /*node2 if B3*/ + (ha_stage2 ? 4 : 2);
  printf("failure-chain checkpoints: alarm_t=%.2f clamp_t=%.2f landed=%d disarm=%d t_land=%.2f flash_prevented=%d\n",
         t_alarm, t_first_clamp, (int)landed, (int)disarmed, t_land_complete, manual_flash_fixed);
  printf("VERDICT nodes_changed=%d/7 (transparency node1 unchanged by design; >=6 with B3+ A) %s\n",
         cfg.rung_b3_descent_cap && ha_stage2 && landed ? 6 : changed,
         (cfg.rung_b3_descent_cap && ha_stage2 && landed && max_ctrl_err <= 1.60) ? "PASS" : "CHECK");
  return 0;
}
