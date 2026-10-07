/*******************************************************
 * Copyright (C) 2019, Aerial Robotics Group, Hong Kong University of Science and Technology
 * 
 * This file is part of VINS.
 * 
 * Licensed under the GNU General Public License v3.0;
 * you may not use this file except in compliance with the License.
 *******************************************************/

#pragma once

#include <ros/ros.h>
#include <vector>
#include <eigen3/Eigen/Dense>
#include "../utility/utility.h"
#include <opencv2/opencv.hpp>
#include <opencv2/core/eigen.hpp>
#include <fstream>
#include <map>

using namespace std;

const double FOCAL_LENGTH = 467.7427;  // T2-U7 RE-APPLY (2026-10-01 20:06): carrier exonerated by R2 verdict carrier_input_domain (9-cell falsification, 04d1a73) - stack-difference variable excluded; re-apply per taskbook v7.2 unlock clause. Online verification round prereg = t2_results/R2_dissect/prereg_u7_online.md (U7OL1/U7OL2).
const int WINDOW_SIZE = 10;
const int NUM_OF_F = 1000;
//#define UNIT_SPHERE_ERROR

extern double INIT_DEPTH;
extern double MIN_PARALLAX;
extern int ESTIMATE_EXTRINSIC;

extern double ACC_N, ACC_W;
extern double GYR_N, GYR_W;

extern std::vector<Eigen::Matrix3d> RIC;
extern std::vector<Eigen::Vector3d> TIC;
extern Eigen::Vector3d G;

extern double BIAS_ACC_THRESHOLD;
extern double BIAS_GYR_THRESHOLD;
extern double SOLVER_TIME;
extern int NUM_ITERATIONS;
extern std::string EX_CALIB_RESULT_PATH;
extern std::string VINS_RESULT_PATH;
extern std::string OUTPUT_FOLDER;
extern std::string IMU_TOPIC;
extern double TD;
extern int ESTIMATE_TD;
extern int ROLLING_SHUTTER;
// T2-WA1G: depth-domain gate (defaults = gate off, legacy behavior)
extern int T2_DEPTH_GATE;
extern double T2_DEPTH_MIN, T2_DEPTH_MAX, T2_XCHECK_TOL;
// T2-v8.9 route-fix faces (absent keys = legacy behavior, bit-identical)
extern int T2_DEPTH_GATE_STAGED;   // case-A staged depth gate: reject only in steady state
extern double T2_STAGED_N_SEC;     // case-A post-init grace window (s) before arming rejection
extern int T2_STREAM_GUARD;        // T2-v9.5: publish-side stream guard master switch (0 = legacy)
extern double T2_PUB_SANE_P;       // publish sanity |P| bound (guard-armed rounds only)
extern double T2_PUB_SANE_V;       // publish sanity |V| bound (guard-armed rounds only)
extern double T2_W4_BGS_THRESH;    // case-B W4 pre-init gate Bgs line (default 0.5 = legacy hardcode)
// T2 zeta-fix (odometry re-ignition, X-line trigger; absent keys = legacy bit-identical)
extern int T2_PSEUDO_DROP;         // exclude pseudo-depth (INIT_DEPTH-injected) features from NON_LINEAR solves
extern int T2_STARVE_FLOOR;        // track-count floor arming starvation-weighted vision (0 = off)
extern double T2_STARVE_ALPHA;     // vision sqrt_info scale in starved windows (1.0 = off; 0 = pure IMU+prior)

// T2 zeta-fix: starvation arming predicate — few LK-surviving tracks means the
// surviving observations are unreliable wholesale (X1prime forensics 2026-10-04:
// track 9-33 vs hover 120-140, P flip-flopping between two solution bands).
inline bool t2_starve_now(bool non_linear, int track_num, int floor)
{
    return non_linear && floor > 0 && track_num < floor;
}

// T2-v8.9 case-B: W4 pre-init Bgs-line predicate (0.5 default = bit-identical
// to the former hardcoded norm()<0.5 in Estimator::initialStructure)
inline bool t2_w4_bgs_ok(const Eigen::Vector3d &bgs, double thresh)
{
    return bgs.allFinite() && bgs.norm() < thresh;
}

// T2-v8.9 case-A: steady-state arming condition — NON_LINEAR and past the
// post-init grace window (t_init_finish==0 = never finished = fill-window)
inline bool t2_staged_steady_now(bool non_linear, double t_init_finish, double header, double n_sec)
{
    return non_linear && t_init_finish > 0 && header - t_init_finish >= n_sec;
}

// T1-v1125 M2 腿B (INPUTFACE-SCREEN, 58a4a027): frame-level input quality gate (staged).
// 判读史: 1e 裁决=输入面实锤(verdict c2d75688)——跳变触发层=输入内容锚定;本门=稳态期
// 拒收坏帧(init 期/宽限期全放行,保 Bgs 解=T2 depth-gate 活锁教训直接应用);
// fail-open=连续拒收达上限后放行一帧(防门致盲飞,估计器留重锁采样)。
// 默认全关=零栈改动(实机 config 无这些键=与上游逐位同)。
extern int T2_IQG_GATE;               // master switch (default 0 = OFF)
extern int T2_IQG_OBSERVE;           // T2 v10.4 1a: observe-only (metrics+per-frame METRIC log, never reject)
extern int T2_IQG_MIN_CORNERS;        // K1 供给: 帧特征数下限
extern double T2_IQG_MIN_DEPTH_RATIO; // K2: 有效深(0<z<band)特征占比下限
extern double T2_IQG_MAX_DEPTH_M;     // K2 band: 深度有效上界(m)
extern double T2_IQG_MIN_STEREO_RATIO;// K3: cam0+cam1 配对特征占比下限
extern double T2_IQG_STAGED_N_SEC;    // staging: init 完成后宽限期(s)
extern int T2_IQG_MAX_CONSEC_REJECT;  // fail-open: 连续拒收上限(达则放行一帧)

struct T2IQGMetrics
{
    int corners;
    double depth_ok_ratio;
    double stereo_pair_ratio;
};

// 纯逻辑(gtest 面): steady=staged 稳态位;返回 true=拒收该帧
inline bool t2_iqg_should_reject(bool steady, const T2IQGMetrics &m,
                                 int consec_rejects, const char **reason)
{
    if (!steady)
        return false;  // init 期/宽限期全放行(保 Bgs 解)
    if (consec_rejects >= T2_IQG_MAX_CONSEC_REJECT)
    {
        if (reason) *reason = "fail-open";
        return false;  // 防门致盲飞:连续拒收超限放行一帧(计数随之清零)
    }
    if (m.corners < T2_IQG_MIN_CORNERS)
    {
        if (reason) *reason = "corners";
        return true;
    }
    if (m.depth_ok_ratio < T2_IQG_MIN_DEPTH_RATIO)
    {
        if (reason) *reason = "depth";
        return true;
    }
    if (m.stereo_pair_ratio < T2_IQG_MIN_STEREO_RATIO)
    {
        if (reason) *reason = "stereo";
        return true;
    }
    return false;
}
// T2-WA23456G (defaults = legacy behavior)
extern int T2_VISION_LOSS;
extern double T2_CAUCHY_DELTA;
extern int T2_REJECT_F;
extern int T2_CHI2_GATE;
extern double T2_CHI2_M, T2_CHI2_CONF;
extern int T2_PRIOR_GATE;
extern double T2_PRIOR_COST_THR, T2_PRIOR_DBAS_THR, T2_PRIOR_SHARE_THR;
extern int T2_PRIOR_COOLDOWN, T2_PRIOR_STRATEGY, T2_COST_TRACE;
// T2-WA3G
extern int T2_REPROPAGATE;
extern double T2_REPROP_BA_THR, T2_REPROP_BG_THR;
// T2-WA7G
extern int T2_BIAS_GUARD;
extern double T2_BAS_SOFT, T2_BGS_SOFT, T2_BIAS_WEIGHT;
extern int T2_BIAS_ANCHOR;
extern double T2_OUTLIER_PX;
extern double T2_MOTION2_MIN_BASE;

// T2-R2F: disparity observability screen (px, via FOCAL_LENGTH macro; 0 = off =
// bit-identical legacy). fardrop_min_near = starvation guard floor.
extern double T2_MIN_DISPARITY;
extern int T2_FARDROP_MIN_NEAR;
// T2-R3F: solver cost-surge gate (unit4; 0 = off = bit-identical legacy)
extern int T2_COST_GATE;
extern double T2_COST_RATIO;
extern int T2_COST_N;
extern int T2_COST_BASE_WIN;
extern int ROW, COL;
extern int NUM_OF_CAM;
extern int STEREO;
extern int USE_IMU;
extern int MULTIPLE_THREAD;
// pts_gt for debug purpose;
extern map<int, Eigen::Vector3d> pts_gt;

extern std::string IMAGE0_TOPIC, IMAGE1_TOPIC;
extern std::string FISHEYE_MASK;
extern std::vector<std::string> CAM_NAMES;
extern int MAX_CNT;
extern int MIN_DIST;
extern double F_THRESHOLD;
extern int SHOW_TRACK;
extern int FLOW_BACK;
extern bool REANCHOR_SMOOTH;        // T1-D1: publish-side smooth reanchor switch
extern int REANCHOR_SMOOTH_FRAMES;  // T1-D1: amortize frame count

void readParameters(std::string config_file);

enum SIZE_PARAMETERIZATION
{
    SIZE_POSE = 7,
    SIZE_SPEEDBIAS = 9,
    SIZE_FEATURE = 1
};

enum StateOrder
{
    O_P = 0,
    O_R = 3,
    O_V = 6,
    O_BA = 9,
    O_BG = 12
};

enum NoiseOrder
{
    O_AN = 0,
    O_GN = 3,
    O_AW = 6,
    O_GW = 9
};
