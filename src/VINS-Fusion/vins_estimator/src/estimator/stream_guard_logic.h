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

    // Adaptive ramp: <=6 m over the default 15 frames keeps each step <=0.4 m;
    // larger resume deltas stretch the ramp (cap 750 frames ~ 6 s @125Hz).
    static int resume_frames(double dP_norm)
    {
        if (dP_norm <= 6.0)
            return 15;
        int fr = (int)std::ceil(dP_norm / 0.4);
        return fr > 750 ? 750 : fr;
    }
};
