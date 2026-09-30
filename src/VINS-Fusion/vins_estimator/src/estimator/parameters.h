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

const double FOCAL_LENGTH = 467.7427;  // T2-U7: align with sim_stereo yaml fx (SDF hfov=1.2), T4-J3 E1 measured; was upstream default 460.0 (1.7% const bias)
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
