/*******************************************************
 * T1-E2 (2026-09-30): propagation guard, pure-value logic
 * for the C03 A3/A4 fixes:
 *   - W3 dt clamp: propagateOnce clamps dt outside [0, 0.5]
 *     (time-base advances, no integration for that step);
 *     a clamped latest-chain step raises pub_hold which stops
 *     publishing (escape (b): consumers see odom stop-flow and
 *     fall into their own failsafes).
 *   - pub_hold is cleared only by a successful ULS re-anchor
 *     (overwrite + replay finished). If the solver thread is
 *     dead (smooth3-type), the hold is permanent -- a silent
 *     "healthy-rate wrong-position" stream is forbidden.
 *   - gap guard: at the ULS capture path, if the shadow time to
 *     the first replay-buffer sample spans > 0.3s (10x the
 *     healthy <=0.03s pipe residency), skip the capture (and
 *     count it) instead of feeding a meter-scale garbage delta
 *     into the smoother; D2 position jump gate stays the
 *     backstop for the raw stream.
 *******************************************************/
#pragma once
#include <cmath>

struct PropagateGuard
{
    bool pub_hold = false;
    int clamp_count = 0;
    int gap_skips = 0;
    int held_frames = 0;   // frames skipped by the publish-side hold

    // NaN compares false in both range tests => caught as invalid.
    static bool dt_invalid(double dt)
    {
        return !(dt >= 0.0 && dt <= 0.5);
    }

    // Called when a latest-chain propagation step was clamped.
    void on_clamp()
    {
        pub_hold = true;
        clamp_count++;
    }

    // Called when a ULS overwrite+replay finished (solver alive).
    void on_anchor()
    {
        pub_hold = false;
    }

    // Publish-side: true when this frame must be withheld.
    bool should_hold_publish()
    {
        if (pub_hold)
            held_frames++;
        return pub_hold;
    }

    // C03 A3 gap guard threshold: 10x the healthy pipe residency.
    static bool gap_skip_needed(double shadow_t, double buf_first_t)
    {
        return std::fabs(shadow_t - buf_first_t) > 0.3;
    }

    void on_gap_skip()
    {
        gap_skips++;
    }
};
