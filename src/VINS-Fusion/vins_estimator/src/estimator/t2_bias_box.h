/***************************************************************
 * T2-v10.10 (prereg bias_constraint2_design_v1.md, md5 c16f59c1,
 * frozen 2026-10-09 07:1x): constraint-2a physical-domain box
 * on the IMU bias states — ceres SetParameterLowerBound/Upper
 * on para_SpeedBias Ba[3..5] (+/-0.5 m/s^2) and Bg[6..8]
 * (+/-0.05 rad/s) — 1b section-1 step-0 plausibility domain.
 *
 * Mechanism (design section-1): transit-window bias drift
 * absorption (poor observability + marg prior self-hold) is the
 * last live lever on the bias route after warmup falsification
 * (v10.7 8/8 pairs: A-arm transit jump WORSE 4/7 — excitation
 * pushes bias into a large transient band, not convergence).
 * The box is a full-run structural safety domain (not windowed).
 *
 * Master switch: config key t2_bias_box / env T2_BIAS_BOX.
 * Default 0 applies ZERO bounds = legacy path bit-identical
 * (arm-batch B-side control-variable iron rule; gtest
 * test_t2_bias_box locks the off-path no-op).
 ***************************************************************/
#pragma once
#include <ceres/ceres.h>
#include "estimator/parameters.h"

struct T2BiasBox
{
    // para_SpeedBias layout: [V(0..2) Ba(3..5) Bg(6..8)]
    static constexpr int BA0 = 3, BG0 = 6;
    // frozen domain half-widths (design section-2; value-audit = new prereg entry only)
    static constexpr double BA_HALF = 0.5;   // m/s^2
    static constexpr double BG_HALF = 0.05;  // rad/s

    // Apply per-component box bounds to one SpeedBias parameter block.
    // Returns number of bounds set; 0 when the switch is off (no-op = legacy).
    static int apply(ceres::Problem &problem, double *speed_bias)
    {
        if (!T2_BIAS_BOX)
            return 0;
        for (int k = 0; k < 3; k++)
        {
            problem.SetParameterLowerBound(speed_bias, BA0 + k, -BA_HALF);
            problem.SetParameterUpperBound(speed_bias, BA0 + k, BA_HALF);
            problem.SetParameterLowerBound(speed_bias, BG0 + k, -BG_HALF);
            problem.SetParameterUpperBound(speed_bias, BG0 + k, BG_HALF);
        }
        return 12;
    }
};
// odr-use definitions live in parameters.cpp (single TU; C++14 out-of-line
// constexpr defs in a header would be multiple-definition at link time)

// ---------------------------------------------------------------------------
// T2-v10.10 ②b transit relative lock — window predicate (design §2 frozen):
// engage when V first > 0.3 m/s (snapshot window-head bias), release V < 0.2.
struct T2BiasTlockLogic
{
    static constexpr double ENGAGE_V = 0.3;  // m/s
    static constexpr double RELEASE_V = 0.2; // m/s

    // pure transition test: returns 1 = engage, -1 = release, 0 = no change
    static int transition(bool armed, double v_norm)
    {
        if (!armed && v_norm > ENGAGE_V) return 1;
        if (armed && v_norm < RELEASE_V) return -1;
        return 0;
    }
};
