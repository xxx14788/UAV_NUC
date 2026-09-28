/*******************************************************
 * T1-D1 (2026-09-29): publish-side smooth reanchor.
 *
 * Mechanism (forensics: t1_evidence v1 salvage bags, 96% spike-odo
 * alignment, 588+600/600 jump==reanchor-delta matches):
 *   Estimator::updateLatestStates() (estimator.cpp:1736-1738) overwrites
 *   latest_P/V with the sliding-window solution after each optimization
 *   (~10Hz), while inputIMU() publishes latest_* at 125Hz -- the published
 *   imu_propagate stream steps by the reanchor delta (static实测 dP
 *   0.05-0.08 m, |dv| 0.35 m/s), threatening px4ctrl's 0.1 m/s hover gate.
 *
 * Fix (option b, publish side only; estimator kernel untouched):
 *   capture the simultaneous pure delta between a shadow propagation
 *   chain (continuing from pre-overwrite latest_*) and the re-anchored
 *   chain, then release it linearly over N published frames.
 * Conservation: sum of injected offsets == captured jump exactly.
 *******************************************************/
#pragma once
#include <Eigen/Dense>

struct ReanchorSmoother
{
    int frames = 15;                                        // amortize frame count (125Hz -> 0.12s)
    int remaining = 0;                                      // frames left to amortize
    Eigen::Vector3d offset_P = Eigen::Vector3d::Zero();     // active publish-side compensation
    Eigen::Vector3d offset_V = Eigen::Vector3d::Zero();
    Eigen::Vector3d step_P = Eigen::Vector3d::Zero();       // per-frame release increment
    Eigen::Vector3d step_V = Eigen::Vector3d::Zero();

    // Called at reanchor instant. JP/JV = shadow_chain - anchored_chain at
    // the same timestamp (pure reanchor delta, replay drift excluded).
    // Undigested offsets are folded into the new schedule (total conserved).
    void addJump(const Eigen::Vector3d &JP, const Eigen::Vector3d &JV)
    {
        offset_P += JP;
        offset_V += JV;
        if (frames <= 0) { reset(); return; }
        remaining = frames;
        step_P = offset_P / frames;
        step_V = offset_V / frames;
    }

    // Called after each published frame: linear release; strict zeroing when
    // done so idle periods can never accumulate drift from stale offsets.
    void step()
    {
        if (remaining > 0)
        {
            offset_P -= step_P;
            offset_V -= step_V;
            remaining--;
        }
        if (remaining <= 0)
        {
            offset_P.setZero();
            offset_V.setZero();
        }
    }

    void reset()
    {
        remaining = 0;
        offset_P.setZero(); offset_V.setZero();
        step_P.setZero();   step_V.setZero();
    }
};
