/*******************************************************
 * T2-v9.5 (2026-10-05, prereg_reanchor_fix): pure-value
 * decision logic for the publish-side stream guard.
 *
 * Mechanism (MACH1 forensics): the storm walk stays under
 * the legacy poison bound (|V| < 50) for seconds -> 525
 * junk frames on the 125Hz stream; the reboot blackout
 * then re-anchors the solution and the first resumed
 * frame steps by the full frame delta (294 m in MACH1;
 * the 2.45-2.60 m constant family in mild rounds).
 *
 * Guard arms (config t2_stream_guard): sane-domain hold +
 * resume continuity (delta compensation through the T1-D1
 * smoother, adaptive frames cap the per-frame step at
 * 0.4 m < 0.5 m judgment line).
 *******************************************************/
#pragma once
#include <cmath>

struct StreamGuardLogic
{
    static constexpr double RESUME_GAP = 0.15;   // s; 125Hz stream misses ~19 frames

    // Publish sanity: normal-domain margin ~3x(|P|) / ~7x(|V|).
    static bool publish_sane(double p_norm, double v_norm, double sane_p, double sane_v)
    {
        return p_norm < sane_p && v_norm < sane_v;
    }

    static bool resume_needed(bool had_last, double gap_s)
    {
        return had_last && gap_s > RESUME_GAP;
    }

    // Adaptive ramp (v4): the released stream is sampled at 125 Hz (prop) AND
    // 10 Hz (odometry topic). Per-frame step <=0.4 m needs duration >= dP/50s;
    // per-10Hz-sample step <=0.5 m needs duration >= dP/5 s -- the odom rate is
    // binding (RA15: 26-frame ramp sampled as 8.5 m odom steps). Cap 20 s.
    static int resume_frames(double dP_norm)
    {
        if (dP_norm <= 0.3)
            return 15;
        int fr = (int)std::ceil(dP_norm / 5.0 / 0.008);   // 25*dP: 5 m/s release
        return fr > 2500 ? 2500 : fr;
    }

    // v2 (RA3 forensics): post-reboot first optimizations swing wildly
    // (published P walked -1037 -> +12.2 m/frame from poisoned offsets).
    // Hold publishing for a settle window after mid-flight init-finish
    // (first init of a round: had_last=false -> legacy timing untouched).
    static constexpr double POST_INIT_SETTLE = 2.0;   // s

    static bool settle_hold(bool had_last, double t_now, double t_init_finish)
    {
        return had_last && (t_now - t_init_finish) < POST_INIT_SETTLE;
    }

    // v2: the publish gate must also cover the offset-corrected values --
    // kernel latest_* can be sane while a poisoned smoother offset is not.
    static bool published_sane(double p_pub_norm, double v_pub_norm, double sane_p, double sane_v)
    {
        return p_pub_norm < sane_p && v_pub_norm < sane_v;
    }
};
