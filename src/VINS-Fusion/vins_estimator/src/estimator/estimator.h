/*******************************************************
 * Copyright (C) 2019, Aerial Robotics Group, Hong Kong University of Science and Technology
 * 
 * This file is part of VINS.
 * 
 * Licensed under the GNU General Public License v3.0;
 * you may not use this file except in compliance with the License.
 *******************************************************/

#pragma once
 
#include <thread>
#include <mutex>
#include <atomic>
#include <std_msgs/Header.h>
#include <std_msgs/Float32.h>
#include <ceres/ceres.h>
#include <unordered_map>
#include <queue>
#include <opencv2/core/eigen.hpp>
#include <eigen3/Eigen/Dense>
#include <eigen3/Eigen/Geometry>

#include "parameters.h"
#include "feature_manager.h"
#include "../utility/utility.h"
#include "../utility/tic_toc.h"
#include "../initial/solve_5pts.h"
#include "../initial/initial_sfm.h"
#include "../initial/initial_alignment.h"
#include "../initial/initial_ex_rotation.h"
#include "reanchor_smoother.h"
#include "propagate_guard.h"
#include "stream_guard_logic.h"
#include "../factor/imu_factor.h"
#include "../factor/pose_local_parameterization.h"
#include "../factor/marginalization_factor.h"
#include "../factor/projectionTwoFrameOneCamFactor.h"
#include "../factor/projectionTwoFrameTwoCamFactor.h"
#include "../factor/projectionOneFrameTwoCamFactor.h"
#include "../featureTracker/feature_tracker.h"


class Estimator
{
  public:

    uint32_t t2_p3_get_notify() const { return t2_p3_notify.load(); }
    Estimator();
    ~Estimator();
    void setParameter();

    // interface
    void initFirstPose(Eigen::Vector3d p, Eigen::Matrix3d r);
    void inputIMU(double t, const Vector3d &linearAcceleration, const Vector3d &angularVelocity);
    void inputFeature(double t, const map<int, vector<pair<int, Eigen::Matrix<double, 7, 1>>>> &featureFrame);
    void inputImage(double t, const cv::Mat &_img, const cv::Mat &_img1 = cv::Mat());
    void processIMU(double t, double dt, const Vector3d &linear_acceleration, const Vector3d &angular_velocity);
    void processImage(const map<int, vector<pair<int, Eigen::Matrix<double, 7, 1>>>> &image, const double header);
    void processMeasurements();
    void changeSensorType(int use_imu, int use_stereo);

    // internal
    void clearState();

    bool reinit_request{false};  // T2-W4: 初始化质量门请求的完全重启标志
    // T1 v11.31 2f P3: 计划内 reboot 通告契约 v1 (p3_contract_design_v1)
    // 载荷位域: 高16位=事件(1=reboot,2=resume), 低16位=累计计数
    std::atomic<uint32_t> t2_p3_notify{0};
    uint32_t t2_p3_reboot_cnt = 0;
    uint32_t t2_p3_resume_cnt = 0;
    bool t2_p3_pending_resume = false;

    bool initialStructure();
    bool visualInitialAlign();
    bool relativePose(Matrix3d &relative_R, Vector3d &relative_T, int &l);
    void slideWindow();
    void slideWindowNew();
    void slideWindowOld();
    void optimization();
    void vector2double();
    void double2vector();
    bool failureDetection();
    bool getIMUInterval(double t0, double t1, vector<pair<double, Eigen::Vector3d>> &accVector, 
                                              vector<pair<double, Eigen::Vector3d>> &gyrVector);
    void getPoseInWorldFrame(Eigen::Matrix4d &T);
    void getPoseInWorldFrame(int index, Eigen::Matrix4d &T);
    void predictPtsInNextFrame();
    void outliersRejection(set<int> &removeIndex);
    double reprojectionError(Matrix3d &Ri, Vector3d &Pi, Matrix3d &rici, Vector3d &tici,
                                     Matrix3d &Rj, Vector3d &Pj, Matrix3d &ricj, Vector3d &ticj, 
                                     double depth, Vector3d &uvi, Vector3d &uvj);
    void updateLatestStates(bool set_flag = false);  // C03-A3 beta: init points pass true (flag set inside mPropagate)
    void fastPredictIMU(double t, Eigen::Vector3d linear_acceleration, Eigen::Vector3d angular_velocity);
    // T1-D1: single-source IMU propagation step (shared by the anchored chain
    // fastPredictIMU and the updateLatestStates shadow chain).
    bool propagateOnce(double &t, Eigen::Vector3d &P, Eigen::Vector3d &V,  // T1-E2: returns true when clamped
                       Eigen::Quaterniond &Q, Eigen::Vector3d &acc_0, Eigen::Vector3d &gyr_0,
                       const Eigen::Vector3d &Ba, const Eigen::Vector3d &Bg,
                       double tn, const Eigen::Vector3d &accn, const Eigen::Vector3d &gyrn);
    bool IMUAvailable(double t);
    void initFirstIMUPose(vector<pair<double, Eigen::Vector3d>> &accVector);

    enum SolverFlag
    {
        INITIAL,
        NON_LINEAR
    };

    enum MarginalizationFlag
    {
        MARGIN_OLD = 0,
        MARGIN_SECOND_NEW = 1
    };

    std::mutex mProcess;
    std::mutex mBuf;
    std::mutex mPropagate;
    queue<pair<double, Eigen::Vector3d>> accBuf;
    queue<pair<double, Eigen::Vector3d>> gyrBuf;
    queue<pair<double, map<int, vector<pair<int, Eigen::Matrix<double, 7, 1> > > > > > featureBuf;
    double prevTime, curTime;
    bool openExEstimation;

    std::thread trackThread;
    std::thread processThread;

    FeatureTracker featureTracker;

    SolverFlag solver_flag;
    MarginalizationFlag  marginalization_flag;
    Vector3d g;

    Matrix3d ric[2];
    Vector3d tic[2];

    Vector3d        Ps[(WINDOW_SIZE + 1)];
    Vector3d        Vs[(WINDOW_SIZE + 1)];
    Matrix3d        Rs[(WINDOW_SIZE + 1)];
    Vector3d        Bas[(WINDOW_SIZE + 1)];
    Vector3d        Bgs[(WINDOW_SIZE + 1)];
    double td;

    Matrix3d back_R0, last_R, last_R0;
    Vector3d back_P0, last_P, last_P0;
    double Headers[(WINDOW_SIZE + 1)];

    IntegrationBase *pre_integrations[(WINDOW_SIZE + 1)];
    // T2-WA2G: prior-health-gate state
    Eigen::Vector3d t2_prev_bas{0, 0, 0};
    long t2_solve_seq = 0, t2_prior_gate_last = -1000;
    // T2-WA7G: bias-guard episode state (zero = inactive)
    Eigen::Vector3d t2_guard_last_ba{0, 0, 0};
    Eigen::Vector3d t2_guard_last_bg{0, 0, 0};
    bool t2_guard_engaged = false;
    // T2-v10.10 ②b: transit-window relative bias lock state (design c16f59c1 §2)
    // armed = inside transit window (V first >0.3 -> snapshot; release V <0.2)
    Eigen::Vector3d t2_tlock_ba{0, 0, 0};
    Eigen::Vector3d t2_tlock_bg{0, 0, 0};
    bool t2_tlock_armed = false;   // snapshot taken, prior active
    bool t2_tlock_done = false;    // transit ended, no re-lock (single-window semantics)
    Vector3d acc_0, gyr_0;

    vector<double> dt_buf[(WINDOW_SIZE + 1)];
    vector<Vector3d> linear_acceleration_buf[(WINDOW_SIZE + 1)];
    vector<Vector3d> angular_velocity_buf[(WINDOW_SIZE + 1)];

    int frame_count;
    int sum_of_outlier, sum_of_back, sum_of_front, sum_of_invalid;
    int inputImageCnt;

    FeatureManager f_manager;
    MotionEstimator m_estimator;
    InitialEXRotation initial_ex_rotation;

    bool first_imu;
    bool is_valid, is_key;
    bool failure_occur;

    vector<Vector3d> point_cloud;
    vector<Vector3d> margin_cloud;
    vector<Vector3d> key_poses;
    double initial_timestamp;


    double para_Pose[WINDOW_SIZE + 1][SIZE_POSE];
    double para_SpeedBias[WINDOW_SIZE + 1][SIZE_SPEEDBIAS];
    double para_Feature[NUM_OF_F][SIZE_FEATURE];
    double para_Ex_Pose[2][SIZE_POSE];
    double para_Retrive_Pose[SIZE_POSE];
    double para_Td[1][1];
    double para_Tr[1][1];

    int loop_window_index;

    MarginalizationInfo *last_marginalization_info;
    vector<double *> last_marginalization_parameter_blocks;

    map<double, ImageFrame> all_image_frame;
    IntegrationBase *tmp_pre_integration;

    Eigen::Vector3d initP;
    Eigen::Matrix3d initR;

    double latest_time;
    Eigen::Vector3d latest_P, latest_V, latest_Ba, latest_Bg, latest_acc_0, latest_gyr_0;
    Eigen::Quaterniond latest_Q;
    ReanchorSmoother reanchor_smoother;   // T1-D1: publish-side smooth reanchor (kernel untouched)
    // T2-R3F: cost-surge gate state (unit4) - short-window median streak
    std::deque<double> t2_cost_hist;
    int t2_cost_streak = 0;
    double t2_t_init_finish = 0;  // T2-v8.9 case-A: init-finish stamp (grace window origin; 0 = fill-window)
    // T2NANDEF (v11.17 2.1, prereg nan_defense_v1): NaN 防线状态面
    double t2_last_initial_cost = -1.0; // optimization() 求解快照(D3 init 后置门消费)
    int t2_last_term = -1;              // termination_type 快照
    int t2_last_iters = 0;              // iterations 快照
    int t2_med_degen_n = 0;             // D4: cost-gate median 退化计数
    int t2_prior_drop_n = 0;            // D5: prior NaN 丢弃计数
    bool t2PriorNan(MarginalizationInfo *mi); // D5: prior 块有限性校验
    PropagateGuard propagate_guard;       // T1-E2: dt-clamp hold / gap-skip counters (C03 A3/A4)

    // T2-v9.5 stream guard (prereg_reanchor_fix): publish-side continuity
    // bookkeeping. t2_pub_* owned by the spinner thread inside mPropagate;
    // t2_odom_off_* written by the process thread under the existing
    // mProcess->mPropagate lock order (see updateLatestStates).
    Eigen::Vector3d t2_pub_last_P = Eigen::Vector3d::Zero();
    Eigen::Vector3d t2_pub_last_V = Eigen::Vector3d::Zero();
    double t2_pub_last_t = -1.0;
    bool t2_pub_had = false;
    Eigen::Vector3d t2_odom_off_P = Eigen::Vector3d::Zero();  // snapshot for pubOdometry
    Eigen::Vector3d t2_odom_off_V = Eigen::Vector3d::Zero();
    double t2_sg_init_finish = 0.0;  // v2: settle-window origin (init-finish, mPropagate domain)
    // v3: continuous-chain snapshot for the 10Hz odometry topic (written under
    // mPropagate at the pubOdometry call site; process thread is sole reader)
    Eigen::Vector3d t2_odom_pub_P = Eigen::Vector3d::Zero();
    Eigen::Vector3d t2_odom_pub_V = Eigen::Vector3d::Zero();
    Eigen::Quaterniond t2_odom_pub_Q = Eigen::Quaterniond::Identity();

    bool initFirstPoseFlag;
    bool initThreadFlag;
};

// T2-v8.2 A1-fix (2026-10-03, prereg_a1fix.md): failure-reboot request helper.
// CONTRACT: MUST NOT acquire any lock. failureDetection fires inside
// processImage, which runs under processMeasurements' mProcess
// (estimator.cpp:388); clearState() re-locks mProcess (estimator.cpp:38) so a
// direct call self-deadlocks the process thread (U3pp A1/A3: odometry dead
// forever, spinner kept publishing poisoned imu_propagate 8.25s/6.0s). The
// loop-head consumer (processMeasurements, outside the lock; T2-U1 pattern)
// owns the actual clearState+setParameter.
inline void t2_failure_reboot_request(bool &failure_occur, bool &reinit_request)
{
    failure_occur = 1;
    reinit_request = true;
}

