/*******************************************************
 * Copyright (C) 2019, Aerial Robotics Group, Hong Kong University of Science and Technology
 * 
 * This file is part of VINS.
 * 
 * Licensed under the GNU General Public License v3.0;
 * you may not use this file except in compliance with the License.
 *******************************************************/

#include "parameters.h"

double INIT_DEPTH;
// T2-WA1G: depth-domain gate globals
int T2_DEPTH_GATE = 0;
int T2_PSEUDO_DROP = 0;          // T2 zeta-fix: 0=off=bit-identical
int T2_STARVE_FLOOR = 0;         // T2 zeta-fix: 0=off
double T2_STARVE_ALPHA = 1.0;    // T2 zeta-fix: 1.0=off
int T2_DEPTH_GATE_STAGED = 0;     // T2-v8.9 case-A: 0=off=bit-identical
double T2_STAGED_N_SEC = 80.0;    // T2-v8.9 case-A: post-init grace (VR2 rebuild-onset 4.3-78.7s conservative upper bound)
double T2_W4_BGS_THRESH = 0.5;    // T2-v8.9 case-B: W4 Bgs line, 0.5 = legacy hardcode
double T2_DEPTH_MIN = 0.15, T2_DEPTH_MAX = 30.0, T2_XCHECK_TOL = 0.30;
// T2-WA23456G globals (defaults = legacy behavior)
int T2_VISION_LOSS = 0;
double T2_CAUCHY_DELTA = 4.0;
int T2_REJECT_F = 0;
int T2_CHI2_GATE = 0;
double T2_CHI2_M = 5.0, T2_CHI2_CONF = 0.95;
int T2_PRIOR_GATE = 0;
double T2_PRIOR_COST_THR = 5e3, T2_PRIOR_DBAS_THR = 0.05, T2_PRIOR_SHARE_THR = 0.5;
int T2_PRIOR_COOLDOWN = 5, T2_PRIOR_STRATEGY = 1, T2_COST_TRACE = 0;
// T2-WA3G globals
int T2_REPROPAGATE = 0;
double T2_REPROP_BA_THR = 0.10, T2_REPROP_BG_THR = 0.01;
// T2-WA7G globals
int T2_BIAS_GUARD = 0;
double T2_BAS_SOFT = 1.0, T2_BGS_SOFT = 0.5, T2_BIAS_WEIGHT = 50.0;
double T2_OUTLIER_PX = 0;  // T2-WA8: 0=legacy 3px hard
double T2_MOTION2_MIN_BASE = 0.0;  // T2-WA9: min inter-frame baseline (m) for motion2 triangulation, 0=off
double T2_MIN_DISPARITY = 0.0;     // T2-R2F: stereo disparity floor (px), 0=off=legacy bit-identical
int T2_FARDROP_MIN_NEAR = 30;    // T2-R2F: starvation guard: far-drop only while near supply >= this
int T2_COST_GATE = 0;            // T2-R3F: cost-surge gate, 0=off=legacy bit-identical
double T2_COST_RATIO = 10.0;     // T2-R3F: surge ratio vs short-window median
int T2_COST_N = 5;               // T2-R3F: consecutive-frame streak to fire (anti single-frame)
int T2_COST_BASE_WIN = 20;       // T2-R3F: short median window (frames) - sees acute surges, not scene drift
int T2_BIAS_ANCHOR = 0;
double MIN_PARALLAX;
double ACC_N, ACC_W;
double GYR_N, GYR_W;

std::vector<Eigen::Matrix3d> RIC;
std::vector<Eigen::Vector3d> TIC;

Eigen::Vector3d G{0.0, 0.0, 9.8};

double BIAS_ACC_THRESHOLD;
double BIAS_GYR_THRESHOLD;
double SOLVER_TIME;
int NUM_ITERATIONS;
bool REANCHOR_SMOOTH = false;       // T1-D1: publish-side smooth reanchor (default off = legacy)
int REANCHOR_SMOOTH_FRAMES = 15;    // T1-D1: amortize frames @125Hz (0.12s)
int ESTIMATE_EXTRINSIC;
int ESTIMATE_TD;
int ROLLING_SHUTTER;
std::string EX_CALIB_RESULT_PATH;
std::string VINS_RESULT_PATH;
std::string OUTPUT_FOLDER;
std::string IMU_TOPIC;
int ROW, COL;
double TD;
int NUM_OF_CAM;
int STEREO;
int USE_IMU;
int MULTIPLE_THREAD;
map<int, Eigen::Vector3d> pts_gt;
std::string IMAGE0_TOPIC, IMAGE1_TOPIC;
std::string FISHEYE_MASK;
std::vector<std::string> CAM_NAMES;
int MAX_CNT;
int MIN_DIST;
double F_THRESHOLD;
int SHOW_TRACK;
int FLOW_BACK;


template <typename T>
T readParam(ros::NodeHandle &n, std::string name)
{
    T ans;
    if (n.getParam(name, ans))
    {
        ROS_INFO_STREAM("Loaded " << name << ": " << ans);
    }
    else
    {
        ROS_ERROR_STREAM("Failed to load " << name);
        n.shutdown();
    }
    return ans;
}

void readParameters(std::string config_file)
{
    FILE *fh = fopen(config_file.c_str(),"r");
    if(fh == NULL){
        ROS_WARN("config_file dosen't exist; wrong config_file path");
        ROS_BREAK();
        return;          
    }
    fclose(fh);

    cv::FileStorage fsSettings(config_file, cv::FileStorage::READ);
    if(!fsSettings.isOpened())
    {
        std::cerr << "ERROR: Wrong path to settings" << std::endl;
    }

    fsSettings["image0_topic"] >> IMAGE0_TOPIC;
    fsSettings["image1_topic"] >> IMAGE1_TOPIC;
    MAX_CNT = fsSettings["max_cnt"];
    MIN_DIST = fsSettings["min_dist"];
    F_THRESHOLD = fsSettings["F_threshold"];
    SHOW_TRACK = fsSettings["show_track"];
    FLOW_BACK = fsSettings["flow_back"];

    MULTIPLE_THREAD = fsSettings["multiple_thread"];

    USE_IMU = fsSettings["imu"];
    printf("USE_IMU: %d\n", USE_IMU);
    if(USE_IMU)
    {
        fsSettings["imu_topic"] >> IMU_TOPIC;
        printf("IMU_TOPIC: %s\n", IMU_TOPIC.c_str());
        ACC_N = fsSettings["acc_n"];
        ACC_W = fsSettings["acc_w"];
        GYR_N = fsSettings["gyr_n"];
        GYR_W = fsSettings["gyr_w"];
        G.z() = fsSettings["g_norm"];
    }

    SOLVER_TIME = fsSettings["max_solver_time"];
    NUM_ITERATIONS = fsSettings["max_num_iterations"];
    MIN_PARALLAX = fsSettings["keyframe_parallax"];
    MIN_PARALLAX = MIN_PARALLAX / FOCAL_LENGTH;

    // T1-D1 (2026-09-29): absent key keeps defaults (off) -> real-machine
    // configs with no key behave exactly as before. SITL sim_stereo yaml
    // sets reanchor_smooth: 1.
    if (!fsSettings["reanchor_smooth"].empty())
        REANCHOR_SMOOTH = (int)fsSettings["reanchor_smooth"];
    if (!fsSettings["reanchor_smooth_frames"].empty())
        REANCHOR_SMOOTH_FRAMES = (int)fsSettings["reanchor_smooth_frames"];
    // T2-WA1G: depth-domain gate knobs (absent key = gate OFF = legacy behavior;
    // real-machine configs without these keys are bit-identical to upstream)
    if (!fsSettings["t2_depth_gate"].empty())
        T2_DEPTH_GATE = (int)fsSettings["t2_depth_gate"];
    if (!fsSettings["t2_staged_depth_gate"].empty())
        T2_DEPTH_GATE_STAGED = (int)fsSettings["t2_staged_depth_gate"];
    if (!fsSettings["t2_staged_n_sec"].empty())
        T2_STAGED_N_SEC = (double)fsSettings["t2_staged_n_sec"];
    if (!fsSettings["t2_w4_bgs_thresh"].empty())
        T2_W4_BGS_THRESH = (double)fsSettings["t2_w4_bgs_thresh"];
    if (!fsSettings["t2_pseudo_drop"].empty())
        T2_PSEUDO_DROP = (int)fsSettings["t2_pseudo_drop"];
    if (!fsSettings["t2_starve_floor"].empty())
        T2_STARVE_FLOOR = (int)fsSettings["t2_starve_floor"];
    if (!fsSettings["t2_starve_alpha"].empty())
        T2_STARVE_ALPHA = (double)fsSettings["t2_starve_alpha"];
    if (!fsSettings["t2_depth_min"].empty())
        T2_DEPTH_MIN = (double)fsSettings["t2_depth_min"];
    if (!fsSettings["t2_depth_max"].empty())
        T2_DEPTH_MAX = (double)fsSettings["t2_depth_max"];
    if (!fsSettings["t2_xcheck_tol"].empty())
        T2_XCHECK_TOL = (double)fsSettings["t2_xcheck_tol"];
    if (!fsSettings["t2_min_disparity"].empty())
        T2_MIN_DISPARITY = (double)fsSettings["t2_min_disparity"];
    if (!fsSettings["t2_fardrop_min_near"].empty())
        T2_FARDROP_MIN_NEAR = (int)fsSettings["t2_fardrop_min_near"];
    if (!fsSettings["t2_cost_gate"].empty())
        T2_COST_GATE = (int)fsSettings["t2_cost_gate"];
    if (!fsSettings["t2_cost_ratio"].empty())
        T2_COST_RATIO = (double)fsSettings["t2_cost_ratio"];
    if (!fsSettings["t2_cost_n"].empty())
        T2_COST_N = (int)fsSettings["t2_cost_n"];
    if (!fsSettings["t2_cost_base_win"].empty())
        T2_COST_BASE_WIN = (int)fsSettings["t2_cost_base_win"];
    printf("T2_DEPTH_GATE: %d min=%.3f max=%.3f xcheck_tol=%.2f\n",
           T2_DEPTH_GATE, T2_DEPTH_MIN, T2_DEPTH_MAX, T2_XCHECK_TOL);
    printf("T2_ROUTEFIX: staged=%d n=%.1f w4_bgs=%.4g\n",
           T2_DEPTH_GATE_STAGED, T2_STAGED_N_SEC, T2_W4_BGS_THRESH);
    printf("T2_ZETAFIX: pd=%d sf=%d sa=%.2f\n",
           T2_PSEUDO_DROP, T2_STARVE_FLOOR, T2_STARVE_ALPHA);
    // T2-WA23456G knobs (absent = legacy)
    if (!fsSettings["t2_vision_loss"].empty())
        T2_VISION_LOSS = (int)fsSettings["t2_vision_loss"];
    if (!fsSettings["t2_cauchy_delta"].empty())
        T2_CAUCHY_DELTA = (double)fsSettings["t2_cauchy_delta"];
    if (!fsSettings["t2_reject_f"].empty())
        T2_REJECT_F = (int)fsSettings["t2_reject_f"];
    if (!fsSettings["t2_chi2_gate"].empty())
        T2_CHI2_GATE = (int)fsSettings["t2_chi2_gate"];
    if (!fsSettings["t2_chi2_m"].empty())
        T2_CHI2_M = (double)fsSettings["t2_chi2_m"];
    if (!fsSettings["t2_chi2_conf"].empty())
        T2_CHI2_CONF = (double)fsSettings["t2_chi2_conf"];
    if (!fsSettings["t2_prior_gate"].empty())
        T2_PRIOR_GATE = (int)fsSettings["t2_prior_gate"];
    if (!fsSettings["t2_prior_cost_thr"].empty())
        T2_PRIOR_COST_THR = (double)fsSettings["t2_prior_cost_thr"];
    if (!fsSettings["t2_prior_dbas_thr"].empty())
        T2_PRIOR_DBAS_THR = (double)fsSettings["t2_prior_dbas_thr"];
    if (!fsSettings["t2_prior_share_thr"].empty())
        T2_PRIOR_SHARE_THR = (double)fsSettings["t2_prior_share_thr"];
    if (!fsSettings["t2_prior_cooldown"].empty())
        T2_PRIOR_COOLDOWN = (int)fsSettings["t2_prior_cooldown"];
    if (!fsSettings["t2_prior_strategy"].empty())
        T2_PRIOR_STRATEGY = (int)fsSettings["t2_prior_strategy"];
    if (!fsSettings["t2_cost_trace"].empty())
        T2_COST_TRACE = (int)fsSettings["t2_cost_trace"];
    // T2-WA7G: bias guard knobs
    if (!fsSettings["t2_bias_guard"].empty())
        T2_BIAS_GUARD = (int)fsSettings["t2_bias_guard"];
    if (!fsSettings["t2_bas_soft"].empty())
        T2_BAS_SOFT = (double)fsSettings["t2_bas_soft"];
    if (!fsSettings["t2_bgs_soft"].empty())
        T2_BGS_SOFT = (double)fsSettings["t2_bgs_soft"];
    if (!fsSettings["t2_bias_weight"].empty())
        T2_BIAS_WEIGHT = (double)fsSettings["t2_bias_weight"];
    if (!fsSettings["t2_bias_anchor"].empty())
        T2_BIAS_ANCHOR = (int)fsSettings["t2_bias_anchor"];
    if (!fsSettings["t2_outlier_px"].empty())
        T2_OUTLIER_PX = (double)fsSettings["t2_outlier_px"];
    if (!fsSettings["t2_motion2_min_base"].empty())
        T2_MOTION2_MIN_BASE = (double)fsSettings["t2_motion2_min_base"];
    // T2-WA3G knobs
    if (!fsSettings["t2_repropagate"].empty())
        T2_REPROPAGATE = (int)fsSettings["t2_repropagate"];
    if (!fsSettings["t2_reprop_ba_thr"].empty())
        T2_REPROP_BA_THR = (double)fsSettings["t2_reprop_ba_thr"];
    if (!fsSettings["t2_reprop_bg_thr"].empty())
        T2_REPROP_BG_THR = (double)fsSettings["t2_reprop_bg_thr"];
    printf("T2 knobs: loss=%d cauchy=%.2f rejectF=%d chi2=%d(m=%.1f conf=%.2f) prior=%d(cost=%.4g dbas=%.3f share=%.2f cd=%d strat=%d) cost_trace=%d\n",
           T2_VISION_LOSS, T2_CAUCHY_DELTA, T2_REJECT_F, T2_CHI2_GATE, T2_CHI2_M, T2_CHI2_CONF,
           T2_PRIOR_GATE, T2_PRIOR_COST_THR, T2_PRIOR_DBAS_THR, T2_PRIOR_SHARE_THR,
           T2_PRIOR_COOLDOWN, T2_PRIOR_STRATEGY, T2_COST_TRACE);
    printf("REANCHOR_SMOOTH: %d frames: %d\n", REANCHOR_SMOOTH, REANCHOR_SMOOTH_FRAMES);

    fsSettings["output_path"] >> OUTPUT_FOLDER;
    VINS_RESULT_PATH = OUTPUT_FOLDER + "/vio.csv";
    std::cout << "result path " << VINS_RESULT_PATH << std::endl;
    std::ofstream fout(VINS_RESULT_PATH, std::ios::out);
    fout.close();

    ESTIMATE_EXTRINSIC = fsSettings["estimate_extrinsic"];
    if (ESTIMATE_EXTRINSIC == 2)
    {
        ROS_WARN("have no prior about extrinsic param, calibrate extrinsic param");
        RIC.push_back(Eigen::Matrix3d::Identity());
        TIC.push_back(Eigen::Vector3d::Zero());
        EX_CALIB_RESULT_PATH = OUTPUT_FOLDER + "/extrinsic_parameter.csv";
    }
    else 
    {
        if ( ESTIMATE_EXTRINSIC == 1)
        {
            ROS_WARN(" Optimize extrinsic param around initial guess!");
            EX_CALIB_RESULT_PATH = OUTPUT_FOLDER + "/extrinsic_parameter.csv";
        }
        if (ESTIMATE_EXTRINSIC == 0)
            ROS_WARN(" fix extrinsic param ");

        cv::Mat cv_T;
        fsSettings["body_T_cam0"] >> cv_T;
        Eigen::Matrix4d T;
        cv::cv2eigen(cv_T, T);
        RIC.push_back(T.block<3, 3>(0, 0));
        TIC.push_back(T.block<3, 1>(0, 3));
    } 
    
    NUM_OF_CAM = fsSettings["num_of_cam"];
    printf("camera number %d\n", NUM_OF_CAM);

    if(NUM_OF_CAM != 1 && NUM_OF_CAM != 2)
    {
        printf("num_of_cam should be 1 or 2\n");
        assert(0);
    }


    int pn = config_file.find_last_of('/');
    std::string configPath = config_file.substr(0, pn);
    
    std::string cam0Calib;
    fsSettings["cam0_calib"] >> cam0Calib;
    std::string cam0Path = configPath + "/" + cam0Calib;
    CAM_NAMES.push_back(cam0Path);

    if(NUM_OF_CAM == 2)
    {
        STEREO = 1;
        std::string cam1Calib;
        fsSettings["cam1_calib"] >> cam1Calib;
        std::string cam1Path = configPath + "/" + cam1Calib; 
        //printf("%s cam1 path\n", cam1Path.c_str() );
        CAM_NAMES.push_back(cam1Path);
        
        cv::Mat cv_T;
        fsSettings["body_T_cam1"] >> cv_T;
        Eigen::Matrix4d T;
        cv::cv2eigen(cv_T, T);
        RIC.push_back(T.block<3, 3>(0, 0));
        TIC.push_back(T.block<3, 1>(0, 3));
    }

    INIT_DEPTH = 5.0;
    BIAS_ACC_THRESHOLD = 0.1;
    BIAS_GYR_THRESHOLD = 0.1;

    TD = fsSettings["td"];
    ESTIMATE_TD = fsSettings["estimate_td"];
    if (ESTIMATE_TD)
        ROS_INFO_STREAM("Unsynchronized sensors, online estimate time offset, initial td: " << TD);
    else
        ROS_INFO_STREAM("Synchronized sensors, fix time offset: " << TD);

    ROW = fsSettings["image_height"];
    COL = fsSettings["image_width"];
    ROS_INFO("ROW: %d COL: %d ", ROW, COL);

    if(!USE_IMU)
    {
        ESTIMATE_EXTRINSIC = 0;
        ESTIMATE_TD = 0;
        printf("no imu, fix extrinsic param; no time offset calibration\n");
    }

    fsSettings.release();
}
