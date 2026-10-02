/*******************************************************
 * Copyright (C) 2019, Aerial Robotics Group, Hong Kong University of Science and Technology
 * 
 * This file is part of VINS.
 * 
 * Licensed under the GNU General Public License v3.0;
 * you may not use this file except in compliance with the License.
 *******************************************************/

#include "estimator.h"

// T1-E2: one-shot env read (stderr forensics; see audit doc E2_writepoint_audit.md)
// P0-A.1 2026-10-01: restored from a5cd330 (c7d901d placeholder swap had neutralized the probe chain)
static const bool reanchor_dbg = (getenv("REANCHOR_DEBUG") != nullptr);
#include "../utility/visualization.h"
#include "../factor/initial_bias_factor.h"  // T2-WA7G
#include <cstdio>
#include <cstdlib>  // T1-E2: REANCHOR_DEBUG env gate

Estimator::Estimator(): f_manager{Rs}
{
    ROS_INFO("init begins");
    initThreadFlag = false;
    clearState();
}

Estimator::~Estimator()
{
    if (MULTIPLE_THREAD)
    {
        processThread.join();
        printf("join thread \n");
    }
}

void Estimator::clearState()
{
    mProcess.lock();
    while(!accBuf.empty())
        accBuf.pop();
    while(!gyrBuf.empty())
        gyrBuf.pop();
    while(!featureBuf.empty())
        featureBuf.pop();

    prevTime = -1;
    curTime = 0;
    openExEstimation = 0;
    initP = Eigen::Vector3d(0, 0, 0);
    initR = Eigen::Matrix3d::Identity();
    inputImageCnt = 0;
    initFirstPoseFlag = false;

    for (int i = 0; i < WINDOW_SIZE + 1; i++)
    {
        Rs[i].setIdentity();
        Ps[i].setZero();
        Vs[i].setZero();
        Bas[i].setZero();
        Bgs[i].setZero();
        dt_buf[i].clear();
        linear_acceleration_buf[i].clear();
        angular_velocity_buf[i].clear();

        if (pre_integrations[i] != nullptr)
        {
            delete pre_integrations[i];
        }
        pre_integrations[i] = nullptr;
    }

    for (int i = 0; i < NUM_OF_CAM; i++)
    {
        tic[i] = Vector3d::Zero();
        ric[i] = Matrix3d::Identity();
    }

    first_imu = false,
    sum_of_back = 0;
    sum_of_front = 0;
    frame_count = 0;
    solver_flag = INITIAL;
    initial_timestamp = 0;
    all_image_frame.clear();

    if (tmp_pre_integration != nullptr)
        delete tmp_pre_integration;
    if (last_marginalization_info != nullptr)
        delete last_marginalization_info;

    tmp_pre_integration = nullptr;
    last_marginalization_info = nullptr;
    last_marginalization_parameter_blocks.clear();

    f_manager.clearState();

    failure_occur = 0;

    mProcess.unlock();
}

void Estimator::setParameter()
{
    mProcess.lock();
    for (int i = 0; i < NUM_OF_CAM; i++)
    {
        tic[i] = TIC[i];
        ric[i] = RIC[i];
        cout << " exitrinsic cam " << i << endl  << ric[i] << endl << tic[i].transpose() << endl;
    }
    f_manager.setRic(ric);
    ProjectionTwoFrameOneCamFactor::sqrt_info = FOCAL_LENGTH / 1.5 * Matrix2d::Identity();
    ProjectionTwoFrameTwoCamFactor::sqrt_info = FOCAL_LENGTH / 1.5 * Matrix2d::Identity();
    ProjectionOneFrameTwoCamFactor::sqrt_info = FOCAL_LENGTH / 1.5 * Matrix2d::Identity();
    td = TD;
    g = G;
    cout << "set g " << g.transpose() << endl;
    featureTracker.readIntrinsicParameter(CAM_NAMES);

    std::cout << "MULTIPLE_THREAD is " << MULTIPLE_THREAD << '\n';
    if (MULTIPLE_THREAD && !initThreadFlag)
    {
        initThreadFlag = true;
        processThread = std::thread(&Estimator::processMeasurements, this);
    }
    // T2-v8.2 (unit-6 tool debt): one-line gate-config banner. Re-printed on
    // every reboot (setParameter) = reboot-completion observable marker; also
    // closes the "gates have no startup banner" verification gap.
    ROS_WARN("[T2GATECFG] cost_gate=%d ratio=%.1f n=%d win=%d | min_disparity=%.4g fardrop_min_near=%d depth_gate=%d",
             T2_COST_GATE, T2_COST_RATIO, T2_COST_N, T2_COST_BASE_WIN,
             T2_MIN_DISPARITY, T2_FARDROP_MIN_NEAR, T2_DEPTH_GATE);
    mProcess.unlock();
}

void Estimator::changeSensorType(int use_imu, int use_stereo)
{
    bool restart = false;
    mProcess.lock();
    if(!use_imu && !use_stereo)
        printf("at least use two sensors! \n");
    else
    {
        if(USE_IMU != use_imu)
        {
            USE_IMU = use_imu;
            if(USE_IMU)
            {
                // reuse imu; restart system
                restart = true;
            }
            else
            {
                if (last_marginalization_info != nullptr)
                    delete last_marginalization_info;

                tmp_pre_integration = nullptr;
                last_marginalization_info = nullptr;
                last_marginalization_parameter_blocks.clear();
            }
        }
        
        STEREO = use_stereo;
        printf("use imu %d use stereo %d\n", USE_IMU, STEREO);
    }
    mProcess.unlock();
    if(restart)
    {
        clearState();
        setParameter();
    }
}

void Estimator::inputImage(double t, const cv::Mat &_img, const cv::Mat &_img1)
{
    inputImageCnt++;
    map<int, vector<pair<int, Eigen::Matrix<double, 7, 1>>>> featureFrame;
    TicToc featureTrackerTime;

    if(_img1.empty())
        featureFrame = featureTracker.trackImage(t, _img);
    else
        featureFrame = featureTracker.trackImage(t, _img, _img1);
    //printf("featureTracker time: %f\n", featureTrackerTime.toc());

    if (SHOW_TRACK)
    {
        cv::Mat imgTrack = featureTracker.getTrackImage();
        pubTrackImage(imgTrack, t);
    }
    
    if(MULTIPLE_THREAD)  
    {     
        if(inputImageCnt % 2 == 0)
        {
            mBuf.lock();
            featureBuf.push(make_pair(t, featureFrame));
            mBuf.unlock();
        }
    }
    else
    {
        mBuf.lock();
        featureBuf.push(make_pair(t, featureFrame));
        mBuf.unlock();
        TicToc processTime;
        processMeasurements();
        printf("process time: %f\n", processTime.toc());
    }
    
}

void Estimator::inputIMU(double t, const Vector3d &linearAcceleration, const Vector3d &angularVelocity)
{
    mBuf.lock();
    accBuf.push(make_pair(t, linearAcceleration));
    gyrBuf.push(make_pair(t, angularVelocity));
    //printf("input imu with time %f \n", t);
    mBuf.unlock();

    if (solver_flag == NON_LINEAR)
    {
        mPropagate.lock();
        // T1-E2 A8: re-read solver_flag under mPropagate (TOCTOU hygiene;
        // after beta the init-side write lives inside this critical section).
        if (solver_flag != NON_LINEAR)
        {
            mPropagate.unlock();
            return;
        }
        fastPredictIMU(t, linearAcceleration, angularVelocity);
        // T1-E2 C03-A4 escape (b): a clamped step holds the publish side;
        // consumers see odom stop-flow into their failsafes (no silent
        // healthy-rate wrong-position stream). Cleared by ULS on_anchor.
        // T2-v3 W1.3 (2026-09-28): 发布端有界性防线。route 轮实测: ceres
        // 发散时 double2vector 把天文数字状态写进 latest_*, 125Hz 的
        // fastPredictIMU 即时外送, failureDetection 要到下一图像帧才拦截
        // —— px4ctrl 直供链路(imu_propagate 无门控)已吃到 e6 级毒值引发
        // 飞逸(实测 1.6e6 m)。发布前做有界性检查(与 failureDetection 同
        // 阈), 越界即停发: 消费方按 odom 停流进各自 failsafe, 毒值不出门。
        if (latest_P.allFinite() && latest_V.allFinite() &&
            latest_P.norm() < 1e3 && latest_V.norm() < 50.0)
        {
            // T1-D1 (2026-09-29): publish-side smooth reanchor -- published
            // value overlays the amortizing reanchor offset; estimator kernel
            // latest_* untouched. Boundedness gate above still checked on the
            // raw states (poison values are caught before smoothing).
            // REANCHOR_SMOOTH=0 (default; real-machine yaml has no key) keeps
            // the exact legacy publish behavior.
            if (REANCHOR_SMOOTH)
            {
                Eigen::Vector3d P_pub = latest_P + reanchor_smoother.offset_P;
                Eigen::Vector3d V_pub = latest_V + reanchor_smoother.offset_V;
                pubLatestOdometry(P_pub, latest_Q, V_pub, t);
                reanchor_smoother.step();
            }
            else
                pubLatestOdometry(latest_P, latest_Q, latest_V, t);
        }
        mPropagate.unlock();
    }
}

void Estimator::inputFeature(double t, const map<int, vector<pair<int, Eigen::Matrix<double, 7, 1>>>> &featureFrame)
{
    mBuf.lock();
    featureBuf.push(make_pair(t, featureFrame));
    mBuf.unlock();

    if(!MULTIPLE_THREAD)
        processMeasurements();
}


bool Estimator::getIMUInterval(double t0, double t1, vector<pair<double, Eigen::Vector3d>> &accVector, 
                                vector<pair<double, Eigen::Vector3d>> &gyrVector)
{
    if(accBuf.empty())
    {
        printf("not receive imu\n");
        return false;
    }
    //printf("get imu from %f %f\n", t0, t1);
    //printf("imu fornt time %f   imu end time %f\n", accBuf.front().first, accBuf.back().first);
    if(t1 <= accBuf.back().first)
    {
        while (accBuf.front().first <= t0)
        {
            accBuf.pop();
            gyrBuf.pop();
        }
        while (accBuf.front().first < t1)
        {
            accVector.push_back(accBuf.front());
            accBuf.pop();
            gyrVector.push_back(gyrBuf.front());
            gyrBuf.pop();
        }
        accVector.push_back(accBuf.front());
        gyrVector.push_back(gyrBuf.front());
    }
    else
    {
        printf("wait for imu\n");
        return false;
    }
    return true;
}

bool Estimator::IMUAvailable(double t)
{
    if(!accBuf.empty() && t <= accBuf.back().first)
        return true;
    else
        return false;
}

void Estimator::processMeasurements()
{
    while (1)
    {
        // T2-W4: 初始化质量门请求的完全重启（本处不持 mProcess 锁，
        // clearState 安全；部分内联重置实测会留毒状态槽）
        if (reinit_request)
        {
            reinit_request = false;
            clearState();
            setParameter();
            continue;
        }
        //printf("process measurments\n");
        pair<double, map<int, vector<pair<int, Eigen::Matrix<double, 7, 1> > > > > feature;
        vector<pair<double, Eigen::Vector3d>> accVector, gyrVector;
        if(!featureBuf.empty())
        {
            feature = featureBuf.front();
            curTime = feature.first + td;
            while(1)
            {
                if ((!USE_IMU  || IMUAvailable(feature.first + td)))
                    break;
                else
                {
                    printf("wait for imu ... \n");
                    if (! MULTIPLE_THREAD)
                        return;
                    std::chrono::milliseconds dura(5);
                    std::this_thread::sleep_for(dura);
                }
            }
            mBuf.lock();
            if(USE_IMU)
                getIMUInterval(prevTime, curTime, accVector, gyrVector);

            featureBuf.pop();
            mBuf.unlock();

            if(USE_IMU)
            {
                if(!initFirstPoseFlag)
                    initFirstIMUPose(accVector);
                for(size_t i = 0; i < accVector.size(); i++)
                {
                    double dt;
                    if(i == 0)
                        dt = accVector[i].first - prevTime;
                    else if (i == accVector.size() - 1)
                        dt = curTime - accVector[i - 1].first;
                    else
                        dt = accVector[i].first - accVector[i - 1].first;
                    // T2-U1 dt clamp (2026-09-28): 跨时钟域防线。
                    // 实测 bag-B/C/D/E 图像戳(sim 域 ~15-150s)与 IMU 戳(unix
                    // 1.79e9) 跨域时,getIMUInterval 每帧只交出一条 unix 域
                    // IMU,dt[0]=|域差|≈1.79e9s 进 processIMU 传播:deltaQ(w*dt)
                    // 三角函数溢出烂化 Rs(detR→1e30),Ps/Vs 连乘滚至 e25-e40
                    // (T2POISON 插桩实锤 fc=1 j=1 dt=1.791e9 |V|=1.2e25)。
                    // 钳制:dt 超出 [0, 0.5](125Hz 步长 62 倍裕量)或非有限时
                    // 置 0(该样本只更新 acc_0,不传播不进预积分),毒状态无从
                    // 产生;域问题由 t2_preflight_check/域卫士在系统层裁决。
                    if (!(dt >= 0.0 && dt <= 0.5))
                    {
                        static ros::Time t2_last_warn;
                        ros::Time t2_now = ros::Time::now();
                        if ((t2_now - t2_last_warn).toSec() > 5.0 || t2_last_warn.isZero())
                        {
                            ROS_ERROR("dt clamp: dt=%.4g imu_t=%.4f prev=%.4f (domain split or IMU disorder?)",
                                      dt, accVector[i].first, prevTime);
                            t2_last_warn = t2_now;
                        }
                        dt = 0.0;
                    }
                    processIMU(accVector[i].first, dt, accVector[i].second, gyrVector[i].second);
                }
            }
            mProcess.lock();
            processImage(feature.second, feature.first);
            prevTime = curTime;

            printStatistics(*this, 0);

            std_msgs::Header header;
            header.frame_id = "world";
            header.stamp = ros::Time(feature.first);

            pubOdometry(*this, header);
            pubKeyPoses(*this, header);
            pubCameraPose(*this, header);
            pubPointCloud(*this, header);
            pubKeyframe(*this);
            pubTF(*this, header);
            mProcess.unlock();
        }

        if (! MULTIPLE_THREAD)
            break;

        std::chrono::milliseconds dura(2);
        std::this_thread::sleep_for(dura);
    }
}


void Estimator::initFirstIMUPose(vector<pair<double, Eigen::Vector3d>> &accVector)
{
    printf("init first imu pose\n");
    initFirstPoseFlag = true;
    //return;
    Eigen::Vector3d averAcc(0, 0, 0);
    int n = (int)accVector.size();
    for(size_t i = 0; i < accVector.size(); i++)
    {
        averAcc = averAcc + accVector[i].second;
    }
    averAcc = averAcc / n;
    printf("averge acc %f %f %f\n", averAcc.x(), averAcc.y(), averAcc.z());
    Matrix3d R0 = Utility::g2R(averAcc);
    double yaw = Utility::R2ypr(R0).x();
    R0 = Utility::ypr2R(Eigen::Vector3d{-yaw, 0, 0}) * R0;
    Rs[0] = R0;
    cout << "init R0 " << endl << Rs[0] << endl;
    //Vs[0] = Vector3d(5, 0, 0);
}

void Estimator::initFirstPose(Eigen::Vector3d p, Eigen::Matrix3d r)
{
    Ps[0] = p;
    Rs[0] = r;
    initP = p;
    initR = r;
}


void Estimator::processIMU(double t, double dt, const Vector3d &linear_acceleration, const Vector3d &angular_velocity)
{
    if (!first_imu)
    {
        first_imu = true;
        acc_0 = linear_acceleration;
        gyr_0 = angular_velocity;
    }

    if (!pre_integrations[frame_count])
    {
        pre_integrations[frame_count] = new IntegrationBase{acc_0, gyr_0, Bas[frame_count], Bgs[frame_count]};
    }
    if (frame_count != 0)
    {
        pre_integrations[frame_count]->push_back(dt, linear_acceleration, angular_velocity);
        //if(solver_flag != NON_LINEAR)
            tmp_pre_integration->push_back(dt, linear_acceleration, angular_velocity);

        dt_buf[frame_count].push_back(dt);
        linear_acceleration_buf[frame_count].push_back(linear_acceleration);
        angular_velocity_buf[frame_count].push_back(angular_velocity);

        int j = frame_count;         
        Vector3d un_acc_0 = Rs[j] * (acc_0 - Bas[j]) - g;
        Vector3d un_gyr = 0.5 * (gyr_0 + angular_velocity) - Bgs[j];
        Rs[j] *= Utility::deltaQ(un_gyr * dt).toRotationMatrix();
        Vector3d un_acc_1 = Rs[j] * (linear_acceleration - Bas[j]) - g;
        Vector3d un_acc = 0.5 * (un_acc_0 + un_acc_1);
        Ps[j] += dt * Vs[j] + 0.5 * dt * dt * un_acc;
        Vs[j] += dt * un_acc;
        if (solver_flag == INITIAL && (!Vs[j].allFinite() || Vs[j].norm() > 100.0))
            ROS_WARN("T2POISON src=IMU-prop fc=%d j=%d |V|=%.4g dt=%.4g |acc|=%.4g |gyr|=%.4g detR=%.6f",
                     frame_count, j, Vs[j].norm(), dt, linear_acceleration.norm(), angular_velocity.norm(), Rs[j].determinant());
    }
    acc_0 = linear_acceleration;
    gyr_0 = angular_velocity; 
}

void Estimator::processImage(const map<int, vector<pair<int, Eigen::Matrix<double, 7, 1>>>> &image, const double header)
{
    ROS_DEBUG("new image coming ------------------------------------------");
    ROS_DEBUG("Adding feature points %lu", image.size());
    if (f_manager.addFeatureCheckParallax(frame_count, image, td))
    {
        marginalization_flag = MARGIN_OLD;
        //printf("keyframe\n");
    }
    else
    {
        marginalization_flag = MARGIN_SECOND_NEW;
        //printf("non-keyframe\n");
    }

    ROS_DEBUG("%s", marginalization_flag ? "Non-keyframe" : "Keyframe");
    ROS_DEBUG("Solving %d", frame_count);
    ROS_DEBUG("number of feature: %d", f_manager.getFeatureCount());
    Headers[frame_count] = header;
    // T2-WA1: stamp header time for [T2depth] census dumps (covers all triangulate calls + slide)
    f_manager.t2_cur_t = header;

    ImageFrame imageframe(image, header);
    imageframe.pre_integration = tmp_pre_integration;
    all_image_frame.insert(make_pair(header, imageframe));
    tmp_pre_integration = new IntegrationBase{acc_0, gyr_0, Bas[frame_count], Bgs[frame_count]};

    if(ESTIMATE_EXTRINSIC == 2)
    {
        ROS_INFO("calibrating extrinsic param, rotation movement is needed");
        if (frame_count != 0)
        {
            vector<pair<Vector3d, Vector3d>> corres = f_manager.getCorresponding(frame_count - 1, frame_count);
            Matrix3d calib_ric;
            if (initial_ex_rotation.CalibrationExRotation(corres, pre_integrations[frame_count]->delta_q, calib_ric))
            {
                ROS_WARN("initial extrinsic rotation calib success");
                ROS_WARN_STREAM("initial extrinsic rotation: " << endl << calib_ric);
                ric[0] = calib_ric;
                RIC[0] = calib_ric;
                ESTIMATE_EXTRINSIC = 1;
            }
        }
    }

    if (solver_flag == INITIAL)
    {
        // monocular + IMU initilization
        if (!STEREO && USE_IMU)
        {
            if (frame_count == WINDOW_SIZE)
            {
                bool result = false;
                if(ESTIMATE_EXTRINSIC != 2 && (header - initial_timestamp) > 0.1)
                {
                    result = initialStructure();
                    initial_timestamp = header;   
                }
                if(result)
                {
                    optimization();
                    // T1-E2 C03-A3 beta: flag set inside ULS critical section
                    // (capture guard true -> init delta captured; naive
                    // reordering forbidden, see C03 exclusion table).
                    updateLatestStates(true);
                    slideWindow();
                    ROS_INFO("Initialization finish!");
                }
                else
                    slideWindow();
            }
        }

        // stereo + IMU initilization
        if(STEREO && USE_IMU)
        {
            f_manager.initFramePoseByPnP(frame_count, Ps, Rs, tic, ric);
            f_manager.triangulate(frame_count, Ps, Rs, tic, ric);
            if (frame_count == WINDOW_SIZE)
            {
                {
                    char t2buf[900]; int t2off = 0;
                    t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off,
                                      "T2SNAP pre AIF=%d fc=%d Vs:", (int)all_image_frame.size(), frame_count);
                    for (int k = 0; k <= WINDOW_SIZE; k++)
                        t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " %.3g", Vs[k].norm());
                    t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " Ps:");
                    for (int k = 0; k <= WINDOW_SIZE; k++)
                        t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " %.3g", Ps[k].norm());
                    ROS_WARN("%s", t2buf);
                }
                map<double, ImageFrame>::iterator frame_it;
                int i = 0;
                for (frame_it = all_image_frame.begin(); frame_it != all_image_frame.end() && i <= WINDOW_SIZE; frame_it++)
                {
                    frame_it->second.R = Rs[i];
                    frame_it->second.T = Ps[i];
                    i++;
                }
                solveGyroscopeBias(all_image_frame, Bgs);
                // T2-W4 init quality gate (2026-09-27): stereo+IMU 原版窗口满即
                // 无条件宣布初始化完成；PnP 失败帧静默沿用废姿态时优化从垃圾
                // 初值出发，首帧 odometry 即天文数字（2026-09-26 A7 崩溃，
                // E20×bag-B 重放首帧 5.9e17 实测复现）。前置门控：bias/状态
                // 不合理直接重置，不让垃圾进求解器（实测偏置 -114511 进
                // optimization 后线程挂死）。
                // 前置门只查 bias（实测恒 sane；状态检查会拦截到上游
                // INITIAL 路径遗留的毒槽位 Vs[i]=e25，导致永久重试无法
                // 初始化——窗口状态交给 optimization 重写后由后置门判定）
                bool init_sane = Bgs[WINDOW_SIZE].allFinite() &&
                                 Bgs[WINDOW_SIZE].norm() < 0.5 &&
                                 Bas[WINDOW_SIZE].norm() < 1.0;
                if (!init_sane)
                {
                    double max_p = 0, max_v = 0;
                    for (int i = 0; i <= WINDOW_SIZE; i++)
                    {
                        max_p = max(max_p, Ps[i].norm());
                        max_v = max(max_v, Vs[i].norm());
                    }
                    double mx_p = 0, mx_v = 0; int bad_i = -1;
                    for (int i = 0; i <= WINDOW_SIZE; i++)
                        if (Ps[i].norm() > mx_p) { mx_p = Ps[i].norm(); bad_i = i; }
                    for (int i = 0; i <= WINDOW_SIZE; i++)
                        mx_v = max(mx_v, Vs[i].norm());
                    ROS_WARN("gate reject: |Bgs|=%.3g mxP=%.3g(mxV=%.3g,i=%d) bias_ok=%d",
                             Bgs[WINDOW_SIZE].norm(), mx_p, mx_v, bad_i,
                             (int)(Bgs[WINDOW_SIZE].allFinite() && Bgs[WINDOW_SIZE].norm() < 0.5));
                    reinit_request = true;
                    return;
                }
                for (int i = 0; i <= WINDOW_SIZE; i++)
                {
                    pre_integrations[i]->repropagate(Vector3d::Zero(), Bgs[i]);
                }
                optimization();
                bool init_sane_post = true;
                for (int i = 0; i <= WINDOW_SIZE; i++)
                {
                    if (!Ps[i].allFinite() || !Vs[i].allFinite() ||
                        !Rs[i].allFinite() ||
                        Ps[i].norm() > 1e3 || Vs[i].norm() > 50.0)
                    {
                        init_sane_post = false;
                        break;
                    }
                }
                if (init_sane_post)
                {
                    // T1-E2 C03-A3 beta (see init1 comment)
                    updateLatestStates(true);
                    slideWindow();
                    ROS_INFO("Initialization finish!");
                }
                else
                {
                    ROS_WARN("stereo init post-optimization states insane, re-init");
                    {
                        char t2buf[900]; int t2off = 0;
                        t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, "T2SNAP post-reject Vs:");
                        for (int k = 0; k <= WINDOW_SIZE; k++)
                            t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " %.3g", Vs[k].norm());
                        t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " Ps:");
                        for (int k = 0; k <= WINDOW_SIZE; k++)
                            t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " %.3g", Ps[k].norm());
                        t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " detRs:");
                        for (int k = 0; k <= WINDOW_SIZE; k++)
                            t2off += snprintf(t2buf + t2off, sizeof(t2buf) - t2off, " %.4f", Rs[k].determinant());
                        ROS_WARN("%s", t2buf);
                    }
                    reinit_request = true;
                    return;
                    // T2-U1 (2026-09-28): 此前 return 后遗留整段 unreachable
                    // 内联重置死代码(all_image_frame.clear()..f_manager.clearState()),
                    // 实际重置由 processMeasurements 循环头的 reinit_request 消费者
                    // (clearState+setParameter, 不持 mProcess 锁, 实测安全)完成,
                    // 已删除以免误导后续审计。
                }
            }
        }

        // stereo only initilization
        if(STEREO && !USE_IMU)
        {
            f_manager.initFramePoseByPnP(frame_count, Ps, Rs, tic, ric);
            f_manager.triangulate(frame_count, Ps, Rs, tic, ric);
            optimization();

            if(frame_count == WINDOW_SIZE)
            {
                optimization();
                // T1-E2 C03-A3 beta (see init1 comment)
                updateLatestStates(true);
                slideWindow();
                ROS_INFO("Initialization finish!");
            }
        }

        if(frame_count < WINDOW_SIZE)
        {
            frame_count++;
            int prev_frame = frame_count - 1;
            Ps[frame_count] = Ps[prev_frame];
            Vs[frame_count] = Vs[prev_frame];
            Rs[frame_count] = Rs[prev_frame];
            Bas[frame_count] = Bas[prev_frame];
            Bgs[frame_count] = Bgs[prev_frame];
        }

    }
    else
    {
        TicToc t_solve;
        if(!USE_IMU)
            f_manager.initFramePoseByPnP(frame_count, Ps, Rs, tic, ric);
        f_manager.triangulate(frame_count, Ps, Rs, tic, ric);
        optimization();
        set<int> removeIndex;
        outliersRejection(removeIndex);
        // T2-R1.5/R3 插桩:每帧状态轨迹(printf+fflush 防 nohup stdout 缓冲吞行)
        printf("[T2diag] t=%.4f P=[%.4f %.4f %.4f] V=[%.4f %.4f %.4f] |Bas|=%.6f |Bgs|=%.7f Bas=[%.6f %.6f %.6f] Bgs=[%.7f %.7f %.7f] tic0=[%.4f %.4f %.4f] tic1=[%.4f %.4f %.4f] td=%.5f track=%d\n",
               Headers[WINDOW_SIZE],
               Ps[WINDOW_SIZE].x(), Ps[WINDOW_SIZE].y(), Ps[WINDOW_SIZE].z(),
               Vs[WINDOW_SIZE].x(), Vs[WINDOW_SIZE].y(), Vs[WINDOW_SIZE].z(),
               Bas[WINDOW_SIZE].norm(), Bgs[WINDOW_SIZE].norm(),
               Bas[WINDOW_SIZE].x(), Bas[WINDOW_SIZE].y(), Bas[WINDOW_SIZE].z(),
               Bgs[WINDOW_SIZE].x(), Bgs[WINDOW_SIZE].y(), Bgs[WINDOW_SIZE].z(),
               tic[0].x(), tic[0].y(), tic[0].z(),
               tic[1].x(), tic[1].y(), tic[1].z(),
               td, f_manager.last_track_num);
        fflush(stdout);
        f_manager.removeOutlier(removeIndex);
        if (! MULTIPLE_THREAD)
        {
            featureTracker.removeOutliers(removeIndex);
            predictPtsInNextFrame();
        }
            
        ROS_DEBUG("solver costs: %fms", t_solve.toc());

        if (failureDetection())
        {
            // T2-R1.5 插桩:判据快照与触发行同 printf(stdout 缓冲丢失教训)
            printf("[T2fail] t=%.4f P=[%.4g %.4g %.4g] V=[%.4g %.4g %.4g] |Bas|=%.4g |Bgs|=%.4g tic0=[%.4f %.4f %.4f] td=%.5f track=%d\n",
                   Headers[WINDOW_SIZE],
                   Ps[WINDOW_SIZE].x(), Ps[WINDOW_SIZE].y(), Ps[WINDOW_SIZE].z(),
                   Vs[WINDOW_SIZE].x(), Vs[WINDOW_SIZE].y(), Vs[WINDOW_SIZE].z(),
                   Bas[WINDOW_SIZE].norm(), Bgs[WINDOW_SIZE].norm(),
                   tic[0].x(), tic[0].y(), tic[0].z(),
                   td, f_manager.last_track_num);
            fflush(stdout);
            ROS_WARN("failure detection!");
            // T2-v8.2 A1-fix (2026-10-03, prereg_a1fix.md): clearState() locks
            // mProcess which this path already holds (processMeasurements
            // estimator.cpp:388 -> processImage) — the previous direct call
            // self-deadlocked the process thread: odometry stayed silent for
            // the rest of the run and the spinner thread kept publishing
            // poisoned imu_propagate (A1: 142m/8.25s; A3: 93m/6.0s, stopped
            // only by the |V|<50 publish bound / teardown). Route the reboot
            // through the T2-U1 reinit_request loop-head consumer instead.
            t2_failure_reboot_request(failure_occur, reinit_request);
            ROS_WARN("system reboot requested (async via loop-head consumer)");
            return;
        }

        slideWindow();
        f_manager.removeFailures();
        // prepare output of VINS
        key_poses.clear();
        for (int i = 0; i <= WINDOW_SIZE; i++)
            key_poses.push_back(Ps[i]);

        last_R = Rs[WINDOW_SIZE];
        last_P = Ps[WINDOW_SIZE];
        last_R0 = Rs[0];
        last_P0 = Ps[0];
        updateLatestStates();
    }  
}

bool Estimator::initialStructure()
{
    TicToc t_sfm;
    //check imu observibility
    {
        map<double, ImageFrame>::iterator frame_it;
        Vector3d sum_g;
        for (frame_it = all_image_frame.begin(), frame_it++; frame_it != all_image_frame.end(); frame_it++)
        {
            double dt = frame_it->second.pre_integration->sum_dt;
            Vector3d tmp_g = frame_it->second.pre_integration->delta_v / dt;
            sum_g += tmp_g;
        }
        Vector3d aver_g;
        aver_g = sum_g * 1.0 / ((int)all_image_frame.size() - 1);
        double var = 0;
        for (frame_it = all_image_frame.begin(), frame_it++; frame_it != all_image_frame.end(); frame_it++)
        {
            double dt = frame_it->second.pre_integration->sum_dt;
            Vector3d tmp_g = frame_it->second.pre_integration->delta_v / dt;
            var += (tmp_g - aver_g).transpose() * (tmp_g - aver_g);
            //cout << "frame g " << tmp_g.transpose() << endl;
        }
        var = sqrt(var / ((int)all_image_frame.size() - 1));
        //ROS_WARN("IMU variation %f!", var);
        if(var < 0.25)
        {
            ROS_INFO("IMU excitation not enouth!");
            //return false;
        }
    }
    // global sfm
    Quaterniond Q[frame_count + 1];
    Vector3d T[frame_count + 1];
    map<int, Vector3d> sfm_tracked_points;
    vector<SFMFeature> sfm_f;
    for (auto &it_per_id : f_manager.feature)
    {
        int imu_j = it_per_id.start_frame - 1;
        SFMFeature tmp_feature;
        tmp_feature.state = false;
        tmp_feature.id = it_per_id.feature_id;
        for (auto &it_per_frame : it_per_id.feature_per_frame)
        {
            imu_j++;
            Vector3d pts_j = it_per_frame.point;
            tmp_feature.observation.push_back(make_pair(imu_j, Eigen::Vector2d{pts_j.x(), pts_j.y()}));
        }
        sfm_f.push_back(tmp_feature);
    } 
    Matrix3d relative_R;
    Vector3d relative_T;
    int l;
    if (!relativePose(relative_R, relative_T, l))
    {
        ROS_INFO("Not enough features or parallax; Move device around");
        return false;
    }
    GlobalSFM sfm;
    if(!sfm.construct(frame_count + 1, Q, T, l,
              relative_R, relative_T,
              sfm_f, sfm_tracked_points))
    {
        ROS_DEBUG("global SFM failed!");
        marginalization_flag = MARGIN_OLD;
        return false;
    }

    //solve pnp for all frame
    map<double, ImageFrame>::iterator frame_it;
    map<int, Vector3d>::iterator it;
    frame_it = all_image_frame.begin( );
    for (int i = 0; frame_it != all_image_frame.end( ); frame_it++)
    {
        // provide initial guess
        cv::Mat r, rvec, t, D, tmp_r;
        if((frame_it->first) == Headers[i])
        {
            frame_it->second.is_key_frame = true;
            frame_it->second.R = Q[i].toRotationMatrix() * RIC[0].transpose();
            frame_it->second.T = T[i];
            i++;
            continue;
        }
        if((frame_it->first) > Headers[i])
        {
            i++;
        }
        Matrix3d R_inital = (Q[i].inverse()).toRotationMatrix();
        Vector3d P_inital = - R_inital * T[i];
        cv::eigen2cv(R_inital, tmp_r);
        cv::Rodrigues(tmp_r, rvec);
        cv::eigen2cv(P_inital, t);

        frame_it->second.is_key_frame = false;
        vector<cv::Point3f> pts_3_vector;
        vector<cv::Point2f> pts_2_vector;
        for (auto &id_pts : frame_it->second.points)
        {
            int feature_id = id_pts.first;
            for (auto &i_p : id_pts.second)
            {
                it = sfm_tracked_points.find(feature_id);
                if(it != sfm_tracked_points.end())
                {
                    Vector3d world_pts = it->second;
                    cv::Point3f pts_3(world_pts(0), world_pts(1), world_pts(2));
                    pts_3_vector.push_back(pts_3);
                    Vector2d img_pts = i_p.second.head<2>();
                    cv::Point2f pts_2(img_pts(0), img_pts(1));
                    pts_2_vector.push_back(pts_2);
                }
            }
        }
        cv::Mat K = (cv::Mat_<double>(3, 3) << 1, 0, 0, 0, 1, 0, 0, 0, 1);     
        if(pts_3_vector.size() < 6)
        {
            cout << "pts_3_vector size " << pts_3_vector.size() << endl;
            ROS_DEBUG("Not enough points for solve pnp !");
            return false;
        }
        if (! cv::solvePnP(pts_3_vector, pts_2_vector, K, D, rvec, t, 1))
        {
            ROS_DEBUG("solve pnp fail!");
            return false;
        }
        cv::Rodrigues(rvec, r);
        MatrixXd R_pnp,tmp_R_pnp;
        cv::cv2eigen(r, tmp_R_pnp);
        R_pnp = tmp_R_pnp.transpose();
        MatrixXd T_pnp;
        cv::cv2eigen(t, T_pnp);
        T_pnp = R_pnp * (-T_pnp);
        frame_it->second.R = R_pnp * RIC[0].transpose();
        frame_it->second.T = T_pnp;
    }
    if (visualInitialAlign())
        return true;
    else
    {
        ROS_INFO("misalign visual structure with IMU");
        return false;
    }

}

bool Estimator::visualInitialAlign()
{
    TicToc t_g;
    VectorXd x;
    //solve scale
    bool result = VisualIMUAlignment(all_image_frame, Bgs, g, x);
    if(!result)
    {
        ROS_DEBUG("solve g failed!");
        return false;
    }

    // change state
    for (int i = 0; i <= frame_count; i++)
    {
        Matrix3d Ri = all_image_frame[Headers[i]].R;
        Vector3d Pi = all_image_frame[Headers[i]].T;
        Ps[i] = Pi;
        Rs[i] = Ri;
        all_image_frame[Headers[i]].is_key_frame = true;
    }

    double s = (x.tail<1>())(0);
    for (int i = 0; i <= WINDOW_SIZE; i++)
    {
        pre_integrations[i]->repropagate(Vector3d::Zero(), Bgs[i]);
    }
    for (int i = frame_count; i >= 0; i--)
        Ps[i] = s * Ps[i] - Rs[i] * TIC[0] - (s * Ps[0] - Rs[0] * TIC[0]);
    int kv = -1;
    map<double, ImageFrame>::iterator frame_i;
    for (frame_i = all_image_frame.begin(); frame_i != all_image_frame.end(); frame_i++)
    {
        if(frame_i->second.is_key_frame)
        {
            kv++;
            Vs[kv] = frame_i->second.R * x.segment<3>(kv * 3);
        }
    }

    Matrix3d R0 = Utility::g2R(g);
    double yaw = Utility::R2ypr(R0 * Rs[0]).x();
    R0 = Utility::ypr2R(Eigen::Vector3d{-yaw, 0, 0}) * R0;
    g = R0 * g;
    //Matrix3d rot_diff = R0 * Rs[0].transpose();
    Matrix3d rot_diff = R0;
    for (int i = 0; i <= frame_count; i++)
    {
        Ps[i] = rot_diff * Ps[i];
        Rs[i] = rot_diff * Rs[i];
        Vs[i] = rot_diff * Vs[i];
    }
    ROS_DEBUG_STREAM("g0     " << g.transpose());
    ROS_DEBUG_STREAM("my R0  " << Utility::R2ypr(Rs[0]).transpose()); 

    f_manager.clearDepth();
    f_manager.triangulate(frame_count, Ps, Rs, tic, ric);

    return true;
}

bool Estimator::relativePose(Matrix3d &relative_R, Vector3d &relative_T, int &l)
{
    // find previous frame which contians enough correspondance and parallex with newest frame
    for (int i = 0; i < WINDOW_SIZE; i++)
    {
        vector<pair<Vector3d, Vector3d>> corres;
        corres = f_manager.getCorresponding(i, WINDOW_SIZE);
        if (corres.size() > 20)
        {
            double sum_parallax = 0;
            double average_parallax;
            for (int j = 0; j < int(corres.size()); j++)
            {
                Vector2d pts_0(corres[j].first(0), corres[j].first(1));
                Vector2d pts_1(corres[j].second(0), corres[j].second(1));
                double parallax = (pts_0 - pts_1).norm();
                sum_parallax = sum_parallax + parallax;

            }
            average_parallax = 1.0 * sum_parallax / int(corres.size());
            if(average_parallax * 460 > 30 && m_estimator.solveRelativeRT(corres, relative_R, relative_T))
            {
                l = i;
                ROS_DEBUG("average_parallax %f choose l %d and newest frame to triangulate the whole structure", average_parallax * 460, l);
                return true;
            }
        }
    }
    return false;
}

void Estimator::vector2double()
{
    for (int i = 0; i <= WINDOW_SIZE; i++)
    {
        para_Pose[i][0] = Ps[i].x();
        para_Pose[i][1] = Ps[i].y();
        para_Pose[i][2] = Ps[i].z();
        Quaterniond q{Rs[i]};
        para_Pose[i][3] = q.x();
        para_Pose[i][4] = q.y();
        para_Pose[i][5] = q.z();
        para_Pose[i][6] = q.w();

        if(USE_IMU)
        {
            para_SpeedBias[i][0] = Vs[i].x();
            para_SpeedBias[i][1] = Vs[i].y();
            para_SpeedBias[i][2] = Vs[i].z();

            para_SpeedBias[i][3] = Bas[i].x();
            para_SpeedBias[i][4] = Bas[i].y();
            para_SpeedBias[i][5] = Bas[i].z();

            para_SpeedBias[i][6] = Bgs[i].x();
            para_SpeedBias[i][7] = Bgs[i].y();
            para_SpeedBias[i][8] = Bgs[i].z();
        }
    }

    for (int i = 0; i < NUM_OF_CAM; i++)
    {
        para_Ex_Pose[i][0] = tic[i].x();
        para_Ex_Pose[i][1] = tic[i].y();
        para_Ex_Pose[i][2] = tic[i].z();
        Quaterniond q{ric[i]};
        para_Ex_Pose[i][3] = q.x();
        para_Ex_Pose[i][4] = q.y();
        para_Ex_Pose[i][5] = q.z();
        para_Ex_Pose[i][6] = q.w();
    }


    VectorXd dep = f_manager.getDepthVector();
    for (int i = 0; i < f_manager.getFeatureCount(); i++)
        para_Feature[i][0] = dep(i);

    para_Td[0][0] = td;
}

void Estimator::double2vector()
{
    Vector3d origin_R0 = Utility::R2ypr(Rs[0]);
    Vector3d origin_P0 = Ps[0];

    if (failure_occur)
    {
        origin_R0 = Utility::R2ypr(last_R0);
        origin_P0 = last_P0;
        failure_occur = 0;
    }

    if(USE_IMU)
    {
        Vector3d origin_R00 = Utility::R2ypr(Quaterniond(para_Pose[0][6],
                                                          para_Pose[0][3],
                                                          para_Pose[0][4],
                                                          para_Pose[0][5]).toRotationMatrix());
        double y_diff = origin_R0.x() - origin_R00.x();
        //TODO
        Matrix3d rot_diff = Utility::ypr2R(Vector3d(y_diff, 0, 0));
        if (abs(abs(origin_R0.y()) - 90) < 1.0 || abs(abs(origin_R00.y()) - 90) < 1.0)
        {
            ROS_DEBUG("euler singular point!");
            rot_diff = Rs[0] * Quaterniond(para_Pose[0][6],
                                           para_Pose[0][3],
                                           para_Pose[0][4],
                                           para_Pose[0][5]).toRotationMatrix().transpose();
        }

        for (int i = 0; i <= WINDOW_SIZE; i++)
        {

            Rs[i] = rot_diff * Quaterniond(para_Pose[i][6], para_Pose[i][3], para_Pose[i][4], para_Pose[i][5]).normalized().toRotationMatrix();
            
            Ps[i] = rot_diff * Vector3d(para_Pose[i][0] - para_Pose[0][0],
                                    para_Pose[i][1] - para_Pose[0][1],
                                    para_Pose[i][2] - para_Pose[0][2]) + origin_P0;


                Vs[i] = rot_diff * Vector3d(para_SpeedBias[i][0],
                                            para_SpeedBias[i][1],
                                            para_SpeedBias[i][2]);

                Bas[i] = Vector3d(para_SpeedBias[i][3],
                                  para_SpeedBias[i][4],
                                  para_SpeedBias[i][5]);

                Bgs[i] = Vector3d(para_SpeedBias[i][6],
                                  para_SpeedBias[i][7],
                                  para_SpeedBias[i][8]);
            
        }
    }
    else
    {
        for (int i = 0; i <= WINDOW_SIZE; i++)
        {
            Rs[i] = Quaterniond(para_Pose[i][6], para_Pose[i][3], para_Pose[i][4], para_Pose[i][5]).normalized().toRotationMatrix();
            
            Ps[i] = Vector3d(para_Pose[i][0], para_Pose[i][1], para_Pose[i][2]);
        }
    }

    if(USE_IMU)
    {
        for (int i = 0; i < NUM_OF_CAM; i++)
        {
            tic[i] = Vector3d(para_Ex_Pose[i][0],
                              para_Ex_Pose[i][1],
                              para_Ex_Pose[i][2]);
            ric[i] = Quaterniond(para_Ex_Pose[i][6],
                                 para_Ex_Pose[i][3],
                                 para_Ex_Pose[i][4],
                                 para_Ex_Pose[i][5]).normalized().toRotationMatrix();
        }
    }

    VectorXd dep = f_manager.getDepthVector();
    for (int i = 0; i < f_manager.getFeatureCount(); i++)
        dep(i) = para_Feature[i][0];
    f_manager.setDepth(dep);

    if(USE_IMU)
        td = para_Td[0][0];

}

bool Estimator::failureDetection()
{
    // T2-W4 (2026-09-27): 原版首行 return false 使整个失败检测成为死代码，
    // e17 级状态一路外送（E20×bag-B/C/E 重放实测）。启用原有判据并补充
    // 状态幅值检查（与初始化质量门同判据，防 init 后首帧优化即发散）。
    if (!Ps[WINDOW_SIZE].allFinite() || !Vs[WINDOW_SIZE].allFinite() ||
        !Rs[WINDOW_SIZE].allFinite() ||
        Ps[WINDOW_SIZE].norm() > 1e3 || Vs[WINDOW_SIZE].norm() > 50.0)
    {
        ROS_WARN("insane states: |P|=%.3g |V|=%.3g, reboot",
                 Ps[WINDOW_SIZE].norm(), Vs[WINDOW_SIZE].norm());
        return true;
    }
    if (f_manager.last_track_num < 2)
    {
        ROS_INFO(" little feature %d", f_manager.last_track_num);
        //return true;
    }
    if (Bas[WINDOW_SIZE].norm() > 2.5)
    {
        ROS_INFO(" big IMU acc bias estimation %f", Bas[WINDOW_SIZE].norm());
        return true;
    }
    if (Bgs[WINDOW_SIZE].norm() > 1.0)
    {
        ROS_INFO(" big IMU gyr bias estimation %f", Bgs[WINDOW_SIZE].norm());
        return true;
    }
    // T2-R3F (unit4): cost-surge gate. R3 forensics proved range checks have
    // no discriminative power on the route acute-burst-freeze form (healthy
    // v_max 21.2 > sick 6.6; all four checks in-band for 600+ s of poisoned
    // output) while init_cost x10 at the precise onset is the earliest
    // self-consistent symptom. Thresholds data-driven: W=20/N=5/R=10 zero-fire
    // on U3PO/U3PG/U3PH, fire t=48.6s on route burst (=onset 48.7s).
    if (T2_COST_GATE && solver_flag == NON_LINEAR &&
        (int)t2_cost_hist.size() >= T2_COST_BASE_WIN &&
        t2_cost_streak >= T2_COST_N)
    {
        ROS_WARN("cost gate: streak=%d over %.1fx short-window median, reboot",
                 t2_cost_streak, T2_COST_RATIO);
        return true;
    }
    /*
    if (tic(0) > 1)
    {
        ROS_INFO(" big extri param estimation %d", tic(0) > 1);
        return true;
    }
    */
    Vector3d tmp_P = Ps[WINDOW_SIZE];
    if ((tmp_P - last_P).norm() > 5)
    {
        //ROS_INFO(" big translation");
        //return true;
    }
    if (abs(tmp_P.z() - last_P.z()) > 1)
    {
        //ROS_INFO(" big z translation");
        //return true; 
    }
    Matrix3d tmp_R = Rs[WINDOW_SIZE];
    Matrix3d delta_R = tmp_R.transpose() * last_R;
    Quaterniond delta_Q(delta_R);
    double delta_angle;
    delta_angle = acos(delta_Q.w()) * 2.0 / 3.14 * 180.0;
    if (delta_angle > 50)
    {
        ROS_INFO(" big delta_angle ");
        //return true;
    }
    return false;
}

void Estimator::optimization()
{
    TicToc t_whole, t_prepare;
    vector2double();

    ceres::Problem problem;
    ceres::LossFunction *loss_function;
    //loss_function = NULL;
    // T2-WA6G: vision loss kernel switch (absent key = Huber 1.0 = upstream)
    if (T2_VISION_LOSS == 1)
        loss_function = new ceres::CauchyLoss(T2_CAUCHY_DELTA / 1.5);
    else
        loss_function = new ceres::HuberLoss(1.0);
    //loss_function = new ceres::CauchyLoss(1.0 / FOCAL_LENGTH);
    //ceres::LossFunction* loss_function = new ceres::HuberLoss(1.0);
    for (int i = 0; i < frame_count + 1; i++)
    {
        ceres::LocalParameterization *local_parameterization = new PoseLocalParameterization();
        problem.AddParameterBlock(para_Pose[i], SIZE_POSE, local_parameterization);
        if(USE_IMU)
            problem.AddParameterBlock(para_SpeedBias[i], SIZE_SPEEDBIAS);
    }
    if(!USE_IMU)
        problem.SetParameterBlockConstant(para_Pose[0]);

    for (int i = 0; i < NUM_OF_CAM; i++)
    {
        ceres::LocalParameterization *local_parameterization = new PoseLocalParameterization();
        problem.AddParameterBlock(para_Ex_Pose[i], SIZE_POSE, local_parameterization);
        if ((ESTIMATE_EXTRINSIC && frame_count == WINDOW_SIZE && Vs[0].norm() > 0.2) || openExEstimation)
        {
            //ROS_INFO("estimate extinsic param");
            openExEstimation = 1;
        }
        else
        {
            //ROS_INFO("fix extinsic param");
            problem.SetParameterBlockConstant(para_Ex_Pose[i]);
        }
    }
    problem.AddParameterBlock(para_Td[0], 1);

    if (!ESTIMATE_TD || Vs[0].norm() < 0.2)
        problem.SetParameterBlockConstant(para_Td[0]);

    // T2-WA2G: per-factor-type block registry for cost decomposition ([T2cost])
    std::vector<std::pair<const ceres::CostFunction *, int>> t2_reg_f;
    std::vector<std::vector<double *>> t2_reg_p;
    auto t2_reg = [&](const ceres::CostFunction *f, int ty, std::initializer_list<double *> ps)
    {
        t2_reg_f.emplace_back(f, ty);
        t2_reg_p.emplace_back(ps);
    };
    // T2-WA7G: graded bias soft-constraint - when last-solved bias exceeds soft
    // threshold, pin every window frame's SpeedBias with a weak prior at the
    // TRIGGER-TIME snapshot (online WAOL1: Bgs sink 1.2 while track healthy =
    // residual-transfer third form; bias weakly observable per WB4)
    if (T2_BIAS_GUARD && solver_flag == NON_LINEAR &&
        (Bas[WINDOW_SIZE].norm() > T2_BAS_SOFT || Bgs[WINDOW_SIZE].norm() > T2_BGS_SOFT) &&
        t2_guard_last_ba.norm() < 1e-12)  // engage once per episode; snapshot at engage
    {
        t2_guard_engaged = true;
        // T2-WA7: anchor=0 pins to ZERO (sim-domain bias truth; snapshot-at-engage
        // legalizes the poisoned value - phase7 wa7_only froze Bas at 1.30 forever)
        if (T2_BIAS_ANCHOR == 0)
        {
            t2_guard_last_ba.setZero();
            t2_guard_last_bg.setZero();
        }
        else
        {
            t2_guard_last_ba = Bas[WINDOW_SIZE];
            t2_guard_last_bg = Bgs[WINDOW_SIZE];
        }
        printf("[T2guard] t=%.4f ENGAGE Bas=%.4f Bgs=%.5f w=%.1f\n",
               Headers[frame_count], Bas[WINDOW_SIZE].norm(), Bgs[WINDOW_SIZE].norm(), T2_BIAS_WEIGHT);
        fflush(stdout);
    }
    if (T2_BIAS_GUARD && solver_flag == NON_LINEAR && t2_guard_engaged)
    {
        for (int k = 0; k <= frame_count; k++)
        {
            InitialBiasFactor *bf = new InitialBiasFactor(t2_guard_last_ba, t2_guard_last_bg, T2_BIAS_WEIGHT);
            problem.AddResidualBlock(bf, NULL, para_SpeedBias[k]);
        }
    }
    // release when bias back under half-threshold (episode end)
    if (T2_BIAS_GUARD && solver_flag == NON_LINEAR && t2_guard_engaged &&
        Bas[WINDOW_SIZE].norm() < 0.5 * T2_BAS_SOFT && Bgs[WINDOW_SIZE].norm() < 0.5 * T2_BGS_SOFT)
    {
        printf("[T2guard] t=%.4f RELEASE Bas=%.4f Bgs=%.5f\n",
               Headers[frame_count], Bas[WINDOW_SIZE].norm(), Bgs[WINDOW_SIZE].norm());
        t2_guard_engaged = false;
        t2_guard_last_ba.setZero();
        t2_guard_last_bg.setZero();
    }
    if (last_marginalization_info && last_marginalization_info->valid)
    {
        // construct new marginlization_factor
        MarginalizationFactor *marginalization_factor = new MarginalizationFactor(last_marginalization_info);
        problem.AddResidualBlock(marginalization_factor, NULL,
                                 last_marginalization_parameter_blocks);
        if (T2_COST_TRACE)
        {
            std::vector<double *> pv(last_marginalization_parameter_blocks.begin(),
                                     last_marginalization_parameter_blocks.end());
            t2_reg_f.emplace_back(marginalization_factor, 0);
            t2_reg_p.push_back(std::move(pv));
        }
    }
    if(USE_IMU)
    {
        for (int i = 0; i < frame_count; i++)
        {
            int j = i + 1;
            if (pre_integrations[j]->sum_dt > 10.0)
                continue;
            IMUFactor* imu_factor = new IMUFactor(pre_integrations[j]);
            problem.AddResidualBlock(imu_factor, NULL, para_Pose[i], para_SpeedBias[i], para_Pose[j], para_SpeedBias[j]);
            if (T2_COST_TRACE)
                t2_reg(imu_factor, 1, {para_Pose[i], para_SpeedBias[i], para_Pose[j], para_SpeedBias[j]});
        }
    }

    int f_m_cnt = 0;
    int feature_index = -1;
    // T2-WA4G: chi2-rejected track ids (also honored by the marginalization loop below)
    std::set<int> t2_chi2_rejected;
    int t2_chi2_total = 0;
    for (auto &it_per_id : f_manager.feature)
    {
        it_per_id.used_num = it_per_id.feature_per_frame.size();
        if (it_per_id.used_num < 4)
            continue;

        ++feature_index;

        // T2-WA4G: chi-square pre-gate - reproj residual e^Te (FOCAL/1.5 weighted) vs chi2(2dof,conf)*m*n_obs
        if (T2_CHI2_GATE)
        {
            t2_chi2_total++;
            double chi2_sum = 0.0; int n_obs = 0;
            int ci = it_per_id.start_frame, cj = ci - 1;
            Vector3d pts_i_c = it_per_id.feature_per_frame[0].point;
            for (auto &fr : it_per_id.feature_per_frame)
            {
                cj++;
                Vector3d pts_j_c = fr.point;
                if (ci != cj)
                {
                    ProjectionTwoFrameOneCamFactor fc(pts_i_c, pts_j_c,
                        it_per_id.feature_per_frame[0].velocity, fr.velocity,
                        it_per_id.feature_per_frame[0].cur_td, fr.cur_td);
                    double res[2];
                    const double *prms[5] = {para_Pose[ci], para_Pose[cj], para_Ex_Pose[0],
                                             para_Feature[feature_index], para_Td[0]};
                    double *jac_null[5] = {nullptr, nullptr, nullptr, nullptr, nullptr};
                    if (fc.Evaluate(prms, res, jac_null))
                    { chi2_sum += res[0]*res[0] + res[1]*res[1]; n_obs++; }
                }
                if (STEREO && fr.is_stereo)
                {
                    Vector3d pts_jr = fr.pointRight;
                    if (ci != cj)
                    {
                        ProjectionTwoFrameTwoCamFactor fc(pts_i_c, pts_jr,
                            it_per_id.feature_per_frame[0].velocity, fr.velocityRight,
                            it_per_id.feature_per_frame[0].cur_td, fr.cur_td);
                        double res[2];
                        const double *prms[6] = {para_Pose[ci], para_Pose[cj], para_Ex_Pose[0], para_Ex_Pose[1],
                                                 para_Feature[feature_index], para_Td[0]};
                        double *jac_null[6] = {nullptr, nullptr, nullptr, nullptr, nullptr, nullptr};
                        if (fc.Evaluate(prms, res, jac_null))
                        { chi2_sum += res[0]*res[0] + res[1]*res[1]; n_obs++; }
                    }
                    else
                    {
                        ProjectionOneFrameTwoCamFactor fc(pts_i_c, pts_jr,
                            it_per_id.feature_per_frame[0].velocity, fr.velocityRight,
                            it_per_id.feature_per_frame[0].cur_td, fr.cur_td);
                        double res[2];
                        const double *prms[4] = {para_Ex_Pose[0], para_Ex_Pose[1],
                                                 para_Feature[feature_index], para_Td[0]};
                        double *jac_null[4] = {nullptr, nullptr, nullptr, nullptr};
                        if (fc.Evaluate(prms, res, jac_null))
                        { chi2_sum += res[0]*res[0] + res[1]*res[1]; n_obs++; }
                    }
                }
            }
            double chi2_2dof = (T2_CHI2_CONF >= 0.99) ? 9.210 : 5.991;
            if (n_obs > 0 && chi2_sum > T2_CHI2_M * n_obs * chi2_2dof)
            {
                t2_chi2_rejected.insert(feature_index);
                continue;
            }
        }

        int imu_i = it_per_id.start_frame, imu_j = imu_i - 1;
        
        Vector3d pts_i = it_per_id.feature_per_frame[0].point;

        for (auto &it_per_frame : it_per_id.feature_per_frame)
        {
            imu_j++;
            if (imu_i != imu_j)
            {
                Vector3d pts_j = it_per_frame.point;
                ProjectionTwoFrameOneCamFactor *f_td = new ProjectionTwoFrameOneCamFactor(pts_i, pts_j, it_per_id.feature_per_frame[0].velocity, it_per_frame.velocity,
                                                                 it_per_id.feature_per_frame[0].cur_td, it_per_frame.cur_td);
                problem.AddResidualBlock(f_td, loss_function, para_Pose[imu_i], para_Pose[imu_j], para_Ex_Pose[0], para_Feature[feature_index], para_Td[0]);
                if (T2_COST_TRACE)
                    t2_reg(f_td, 2, {para_Pose[imu_i], para_Pose[imu_j], para_Ex_Pose[0], para_Feature[feature_index], para_Td[0]});
            }

            if(STEREO && it_per_frame.is_stereo)
            {                
                Vector3d pts_j_right = it_per_frame.pointRight;
                if(imu_i != imu_j)
                {
                    ProjectionTwoFrameTwoCamFactor *f = new ProjectionTwoFrameTwoCamFactor(pts_i, pts_j_right, it_per_id.feature_per_frame[0].velocity, it_per_frame.velocityRight,
                                                                 it_per_id.feature_per_frame[0].cur_td, it_per_frame.cur_td);
                    problem.AddResidualBlock(f, loss_function, para_Pose[imu_i], para_Pose[imu_j], para_Ex_Pose[0], para_Ex_Pose[1], para_Feature[feature_index], para_Td[0]);
                    if (T2_COST_TRACE)
                        t2_reg(f, 2, {para_Pose[imu_i], para_Pose[imu_j], para_Ex_Pose[0], para_Ex_Pose[1], para_Feature[feature_index], para_Td[0]});
                }
                else
                {
                    ProjectionOneFrameTwoCamFactor *f = new ProjectionOneFrameTwoCamFactor(pts_i, pts_j_right, it_per_id.feature_per_frame[0].velocity, it_per_frame.velocityRight,
                                                                 it_per_id.feature_per_frame[0].cur_td, it_per_frame.cur_td);
                    problem.AddResidualBlock(f, loss_function, para_Ex_Pose[0], para_Ex_Pose[1], para_Feature[feature_index], para_Td[0]);
                    if (T2_COST_TRACE)
                        t2_reg(f, 2, {para_Ex_Pose[0], para_Ex_Pose[1], para_Feature[feature_index], para_Td[0]});
                }
               
            }
            f_m_cnt++;
        }
    }

    ROS_DEBUG("visual measurement count: %d", f_m_cnt);
    // T2-WA4G: per-frame chi2 gate stats (T2frame schema)
    if (T2_CHI2_GATE)
    {
        printf("[T2chi2] t=%.4f total=%d rej=%lu m=%.1f conf=%.2f\n",
               Headers[frame_count], t2_chi2_total,
               (unsigned long)t2_chi2_rejected.size(), T2_CHI2_M, T2_CHI2_CONF);
    }
    //printf("prepare for ceres: %f \n", t_prepare.toc());

    // T2-R3.3: 视觉饥饿窗(last_track_num<20,同 init 门槛)冻结外参优化自由度——
    // 断链窗口中 tic 与 V/Bas 联合爆走实测(E20×B tic0 爆漂 0.52m; E22 绑定外参后
    // 速度爆冲被抑制的实证反向应用)。特征恢复即自动解冻。
    if (ESTIMATE_EXTRINSIC == 1 && frame_count >= WINDOW_SIZE &&
        f_manager.last_track_num < 20)
    {
        for (int i = 0; i < NUM_OF_CAM; i++)
            problem.SetParameterBlockConstant(para_Ex_Pose[i]);
    }
    ceres::Solver::Options options;

    options.linear_solver_type = ceres::DENSE_SCHUR;
    //options.num_threads = 2;
    options.trust_region_strategy_type = ceres::DOGLEG;
    options.max_num_iterations = NUM_ITERATIONS;
    //options.use_explicit_schur_complement = true;
    //options.minimizer_progress_to_stdout = true;
    //options.use_nonmonotonic_steps = true;
    if (marginalization_flag == MARGIN_OLD)
        options.max_solver_time_in_seconds = SOLVER_TIME * 4.0 / 5.0;
    else
        options.max_solver_time_in_seconds = SOLVER_TIME;
    TicToc t_solver;
    ceres::Solver::Summary summary;
    ceres::Solve(options, &problem, &summary);
    if (solver_flag == INITIAL)
    {
        double t2vmax = 0; int t2vidx = -1;
        for (int k = 0; k <= WINDOW_SIZE; k++)
        {
            double t2n = sqrt(para_SpeedBias[k][0] * para_SpeedBias[k][0] +
                              para_SpeedBias[k][1] * para_SpeedBias[k][1] +
                              para_SpeedBias[k][2] * para_SpeedBias[k][2]);
            if (t2n > t2vmax) { t2vmax = t2n; t2vidx = k; }
        }
        ROS_WARN("T2OPT post-solve vmax=%.4g @i=%d init_cost=%.4g final_cost=%.4g iters=%d term=%d",
                 t2vmax, t2vidx, summary.initial_cost, summary.final_cost,
                 static_cast<int>(summary.iterations.size()), static_cast<int>(summary.termination_type));
    }
    //cout << summary.BriefReport() << endl;
    // T2-R1.5/R3 插桩:全阶段求解器健康(printf+fflush)
    printf("[T2slv] t=%.4f phase=%d init_cost=%.6g final_cost=%.6g iters=%d term=%d slv_ms=%.1f\n",
           Headers[frame_count], solver_flag,
           summary.initial_cost, summary.final_cost,
           static_cast<int>(summary.iterations.size()),
           static_cast<int>(summary.termination_type), t_solver.toc());
    // T2-R3F (unit4): cost-surge streak feed. Short median window (default 20
    // frames) catches ACUTE surges (R3 route: 65->643 x10 at burst onset
    // t=50.0s, healthy rounds zero-fire) while ignoring scene-level cost
    // drift (U3PO healthy 118->2730 slow climb). Gate itself lives in
    // failureDetection(); default t2_cost_gate=0 keeps this inert.
    if (T2_COST_GATE && solver_flag == NON_LINEAR)
    {
        if ((int)t2_cost_hist.size() >= T2_COST_BASE_WIN)
        {
            std::vector<double> hs(t2_cost_hist.begin(), t2_cost_hist.end());
            std::nth_element(hs.begin(), hs.begin() + hs.size() / 2, hs.end());
            if (summary.initial_cost > T2_COST_RATIO * hs[hs.size() / 2])
                t2_cost_streak++;
            else
                t2_cost_streak = 0;
        }
        t2_cost_hist.push_back(summary.initial_cost);
        if ((int)t2_cost_hist.size() > T2_COST_BASE_WIN)
            t2_cost_hist.pop_front();
    }
    fflush(stdout);
    // T2-WA2G: per-factor-type cost decomposition on the FINAL solution ([T2cost])
    double t2_cost_prior = -1.0, t2_cost_imu = -1.0, t2_cost_vis = -1.0;
    int t2_nb_prior = 0, t2_nb_imu = 0, t2_nb_vis = 0;
    if (T2_COST_TRACE && t2_reg_f.size() > 0)
    {
        double c[3] = {0, 0, 0}; int n[3] = {0, 0, 0};
        for (size_t k = 0; k < t2_reg_f.size(); k++)
        {
            int ty = t2_reg_f[k].second;
            if (ty < 0 || ty > 2) continue;
            int nr = t2_reg_f[k].first->num_residuals();
            std::vector<double> res(std::max(nr, 1));
            std::vector<const double *> pp(t2_reg_p[k].begin(), t2_reg_p[k].end());
            std::vector<double *> jac_null(t2_reg_p[k].size(), nullptr);
            if (t2_reg_f[k].first->Evaluate(pp.data(), res.data(), jac_null.data()))
            {
                double s2 = 0;
                for (int r = 0; r < nr; r++) s2 += res[r] * res[r];
                c[ty] += 0.5 * s2; n[ty]++;
            }
        }
        t2_cost_prior = c[0]; t2_cost_imu = c[1]; t2_cost_vis = c[2];
        t2_nb_prior = n[0]; t2_nb_imu = n[1]; t2_nb_vis = n[2];
        printf("[T2cost] t=%.4f tot=%.6g prior=%.6g imu=%.6g vis=%.6g prior_n=%d imu_n=%d vis_n=%d\n",
               Headers[frame_count], c[0] + c[1] + c[2], c[0], c[1], c[2], n[0], n[1], n[2]);
    }
    ROS_DEBUG("Iterations : %d", static_cast<int>(summary.iterations.size()));
    //printf("solver costs: %f \n", t_solver.toc());

    double2vector();
    //printf("frame_count: %d \n", frame_count);

    if(frame_count < WINDOW_SIZE)
        return;

    // T2-WA2G: prior health gate - break the polluted-prior carry chain.
    // triggers: init_cost spike | inter-frame ||dBAS|| | prior share of [T2cost];
    // cooldown-limited; strategies 1=drop prior+skip this marg, 2=re-marg without
    // old prior, 3=keep prior+skip this marg (frozen prior).
    bool t2_marg_skip = false, t2_drop_prior_only = false;
    if (T2_PRIOR_GATE && solver_flag == NON_LINEAR)
    {
        t2_solve_seq++;
        double dbas = (Bas[WINDOW_SIZE] - t2_prev_bas).norm();
        t2_prev_bas = Bas[WINDOW_SIZE];
        bool trig_cost = summary.initial_cost > T2_PRIOR_COST_THR;
        bool trig_bas = dbas > T2_PRIOR_DBAS_THR;
        // T2-WA2G fix: share trigger needs a cost floor - low-cost windows have
        // few visual constraints so prior share is naturally high (phase3 c_a2a4
        // 329m regression: share fired at cost=73 destroying healthy priors)
        bool trig_share = (t2_cost_prior >= 0) &&
                          (summary.initial_cost > T2_PRIOR_COST_THR) &&
                          (t2_cost_prior > T2_PRIOR_SHARE_THR * (t2_cost_prior + t2_cost_imu + t2_cost_vis));
        if ((trig_cost || trig_bas || trig_share) &&
            t2_solve_seq - t2_prior_gate_last > T2_PRIOR_COOLDOWN)
        {
            t2_prior_gate_last = t2_solve_seq;
            printf("[T2WA2G] t=%.4f TRIG seq=%ld cost=%.4g dbas=%.4f strategy=%d\n",
                   Headers[frame_count], t2_solve_seq, summary.initial_cost, dbas, T2_PRIOR_STRATEGY);
            fflush(stdout);
            if (T2_PRIOR_STRATEGY == 1)
            {
                if (last_marginalization_info) { delete last_marginalization_info; last_marginalization_info = nullptr; }
                t2_marg_skip = true;
            }
            else if (T2_PRIOR_STRATEGY == 2)
            {
                if (last_marginalization_info) { delete last_marginalization_info; last_marginalization_info = nullptr; }
                t2_drop_prior_only = true;
            }
            else
            {
                t2_marg_skip = true;
            }
        }
    }

    TicToc t_whole_marginalization;
    if (marginalization_flag == MARGIN_OLD && !t2_marg_skip)
    {
        MarginalizationInfo *marginalization_info = new MarginalizationInfo();
        vector2double();

        if (last_marginalization_info && last_marginalization_info->valid && !t2_drop_prior_only)
        {
            vector<int> drop_set;
            for (int i = 0; i < static_cast<int>(last_marginalization_parameter_blocks.size()); i++)
            {
                if (last_marginalization_parameter_blocks[i] == para_Pose[0] ||
                    last_marginalization_parameter_blocks[i] == para_SpeedBias[0])
                    drop_set.push_back(i);
            }
            // construct new marginlization_factor
            MarginalizationFactor *marginalization_factor = new MarginalizationFactor(last_marginalization_info);
            ResidualBlockInfo *residual_block_info = new ResidualBlockInfo(marginalization_factor, NULL,
                                                                           last_marginalization_parameter_blocks,
                                                                           drop_set);
            marginalization_info->addResidualBlockInfo(residual_block_info);
        }

        if(USE_IMU)
        {
            if (pre_integrations[1]->sum_dt < 10.0)
            {
                IMUFactor* imu_factor = new IMUFactor(pre_integrations[1]);
                ResidualBlockInfo *residual_block_info = new ResidualBlockInfo(imu_factor, NULL,
                                                                           vector<double *>{para_Pose[0], para_SpeedBias[0], para_Pose[1], para_SpeedBias[1]},
                                                                           vector<int>{0, 1});
                marginalization_info->addResidualBlockInfo(residual_block_info);
            }
        }

        {
            int feature_index = -1;
            for (auto &it_per_id : f_manager.feature)
            {
                it_per_id.used_num = it_per_id.feature_per_frame.size();
                if (it_per_id.used_num < 4)
                    continue;

                ++feature_index;
                if (t2_chi2_rejected.count(feature_index))
                    continue;  // T2-WA4G: chi2-rejected tracks stay out of the prior too

                int imu_i = it_per_id.start_frame, imu_j = imu_i - 1;
                if (imu_i != 0)
                    continue;

                Vector3d pts_i = it_per_id.feature_per_frame[0].point;

                for (auto &it_per_frame : it_per_id.feature_per_frame)
                {
                    imu_j++;
                    if(imu_i != imu_j)
                    {
                        Vector3d pts_j = it_per_frame.point;
                        ProjectionTwoFrameOneCamFactor *f_td = new ProjectionTwoFrameOneCamFactor(pts_i, pts_j, it_per_id.feature_per_frame[0].velocity, it_per_frame.velocity,
                                                                          it_per_id.feature_per_frame[0].cur_td, it_per_frame.cur_td);
                        ResidualBlockInfo *residual_block_info = new ResidualBlockInfo(f_td, loss_function,
                                                                                        vector<double *>{para_Pose[imu_i], para_Pose[imu_j], para_Ex_Pose[0], para_Feature[feature_index], para_Td[0]},
                                                                                        vector<int>{0, 3});
                        marginalization_info->addResidualBlockInfo(residual_block_info);
                    }
                    if(STEREO && it_per_frame.is_stereo)
                    {
                        Vector3d pts_j_right = it_per_frame.pointRight;
                        if(imu_i != imu_j)
                        {
                            ProjectionTwoFrameTwoCamFactor *f = new ProjectionTwoFrameTwoCamFactor(pts_i, pts_j_right, it_per_id.feature_per_frame[0].velocity, it_per_frame.velocityRight,
                                                                          it_per_id.feature_per_frame[0].cur_td, it_per_frame.cur_td);
                            ResidualBlockInfo *residual_block_info = new ResidualBlockInfo(f, loss_function,
                                                                                           vector<double *>{para_Pose[imu_i], para_Pose[imu_j], para_Ex_Pose[0], para_Ex_Pose[1], para_Feature[feature_index], para_Td[0]},
                                                                                           vector<int>{0, 4});
                            marginalization_info->addResidualBlockInfo(residual_block_info);
                        }
                        else
                        {
                            ProjectionOneFrameTwoCamFactor *f = new ProjectionOneFrameTwoCamFactor(pts_i, pts_j_right, it_per_id.feature_per_frame[0].velocity, it_per_frame.velocityRight,
                                                                          it_per_id.feature_per_frame[0].cur_td, it_per_frame.cur_td);
                            ResidualBlockInfo *residual_block_info = new ResidualBlockInfo(f, loss_function,
                                                                                           vector<double *>{para_Ex_Pose[0], para_Ex_Pose[1], para_Feature[feature_index], para_Td[0]},
                                                                                           vector<int>{2});
                            marginalization_info->addResidualBlockInfo(residual_block_info);
                        }
                    }
                }
            }
        }

        TicToc t_pre_margin;
        marginalization_info->preMarginalize();
        ROS_DEBUG("pre marginalization %f ms", t_pre_margin.toc());
        
        TicToc t_margin;
        marginalization_info->marginalize();
        ROS_DEBUG("marginalization %f ms", t_margin.toc());

        std::unordered_map<long, double *> addr_shift;
        for (int i = 1; i <= WINDOW_SIZE; i++)
        {
            addr_shift[reinterpret_cast<long>(para_Pose[i])] = para_Pose[i - 1];
            if(USE_IMU)
                addr_shift[reinterpret_cast<long>(para_SpeedBias[i])] = para_SpeedBias[i - 1];
        }
        for (int i = 0; i < NUM_OF_CAM; i++)
            addr_shift[reinterpret_cast<long>(para_Ex_Pose[i])] = para_Ex_Pose[i];

        addr_shift[reinterpret_cast<long>(para_Td[0])] = para_Td[0];

        vector<double *> parameter_blocks = marginalization_info->getParameterBlocks(addr_shift);

        if (last_marginalization_info)
            delete last_marginalization_info;
        last_marginalization_info = marginalization_info;
        last_marginalization_parameter_blocks = parameter_blocks;
        
    }
    else if (!t2_marg_skip)  // T2-WA2G: skip covers BOTH marginalization branches
    {
        if (last_marginalization_info &&
            std::count(std::begin(last_marginalization_parameter_blocks), std::end(last_marginalization_parameter_blocks), para_Pose[WINDOW_SIZE - 1]))
        {

            MarginalizationInfo *marginalization_info = new MarginalizationInfo();
            vector2double();
            if (last_marginalization_info && last_marginalization_info->valid)
            {
                vector<int> drop_set;
                for (int i = 0; i < static_cast<int>(last_marginalization_parameter_blocks.size()); i++)
                {
                    ROS_ASSERT(last_marginalization_parameter_blocks[i] != para_SpeedBias[WINDOW_SIZE - 1]);
                    if (last_marginalization_parameter_blocks[i] == para_Pose[WINDOW_SIZE - 1])
                        drop_set.push_back(i);
                }
                // construct new marginlization_factor
                MarginalizationFactor *marginalization_factor = new MarginalizationFactor(last_marginalization_info);
                ResidualBlockInfo *residual_block_info = new ResidualBlockInfo(marginalization_factor, NULL,
                                                                               last_marginalization_parameter_blocks,
                                                                               drop_set);

                marginalization_info->addResidualBlockInfo(residual_block_info);
            }

            TicToc t_pre_margin;
            ROS_DEBUG("begin marginalization");
            marginalization_info->preMarginalize();
            ROS_DEBUG("end pre marginalization, %f ms", t_pre_margin.toc());

            TicToc t_margin;
            ROS_DEBUG("begin marginalization");
            marginalization_info->marginalize();
            ROS_DEBUG("end marginalization, %f ms", t_margin.toc());
            
            std::unordered_map<long, double *> addr_shift;
            for (int i = 0; i <= WINDOW_SIZE; i++)
            {
                if (i == WINDOW_SIZE - 1)
                    continue;
                else if (i == WINDOW_SIZE)
                {
                    addr_shift[reinterpret_cast<long>(para_Pose[i])] = para_Pose[i - 1];
                    if(USE_IMU)
                        addr_shift[reinterpret_cast<long>(para_SpeedBias[i])] = para_SpeedBias[i - 1];
                }
                else
                {
                    addr_shift[reinterpret_cast<long>(para_Pose[i])] = para_Pose[i];
                    if(USE_IMU)
                        addr_shift[reinterpret_cast<long>(para_SpeedBias[i])] = para_SpeedBias[i];
                }
            }
            for (int i = 0; i < NUM_OF_CAM; i++)
                addr_shift[reinterpret_cast<long>(para_Ex_Pose[i])] = para_Ex_Pose[i];

            addr_shift[reinterpret_cast<long>(para_Td[0])] = para_Td[0];

            
            vector<double *> parameter_blocks = marginalization_info->getParameterBlocks(addr_shift);
            if (last_marginalization_info)
                delete last_marginalization_info;
            last_marginalization_info = marginalization_info;
            last_marginalization_parameter_blocks = parameter_blocks;
            
        }
    }
    //printf("whole marginalization costs: %f \n", t_whole_marginalization.toc());
    //printf("whole time for ceres: %f \n", t_whole.toc());
}

void Estimator::slideWindow()
{
    TicToc t_margin;
    if (marginalization_flag == MARGIN_OLD)
    {
        double t_0 = Headers[0];
        back_R0 = Rs[0];
        back_P0 = Ps[0];
        if (frame_count == WINDOW_SIZE)
        {
            for (int i = 0; i < WINDOW_SIZE; i++)
            {
                Headers[i] = Headers[i + 1];
                Rs[i].swap(Rs[i + 1]);
                Ps[i].swap(Ps[i + 1]);
                if(USE_IMU)
                {
                    std::swap(pre_integrations[i], pre_integrations[i + 1]);

                    dt_buf[i].swap(dt_buf[i + 1]);
                    linear_acceleration_buf[i].swap(linear_acceleration_buf[i + 1]);
                    angular_velocity_buf[i].swap(angular_velocity_buf[i + 1]);

                    Vs[i].swap(Vs[i + 1]);
                    Bas[i].swap(Bas[i + 1]);
                    Bgs[i].swap(Bgs[i + 1]);
                }
            }
            Headers[WINDOW_SIZE] = Headers[WINDOW_SIZE - 1];
            Ps[WINDOW_SIZE] = Ps[WINDOW_SIZE - 1];
            Rs[WINDOW_SIZE] = Rs[WINDOW_SIZE - 1];

            if(USE_IMU)
            {
                Vs[WINDOW_SIZE] = Vs[WINDOW_SIZE - 1];
                Bas[WINDOW_SIZE] = Bas[WINDOW_SIZE - 1];
                Bgs[WINDOW_SIZE] = Bgs[WINDOW_SIZE - 1];

                delete pre_integrations[WINDOW_SIZE];
                pre_integrations[WINDOW_SIZE] = new IntegrationBase{acc_0, gyr_0, Bas[WINDOW_SIZE], Bgs[WINDOW_SIZE]};

                dt_buf[WINDOW_SIZE].clear();
                linear_acceleration_buf[WINDOW_SIZE].clear();
                angular_velocity_buf[WINDOW_SIZE].clear();
            }

            if (true || solver_flag == INITIAL)
            {
                map<double, ImageFrame>::iterator it_0;
                it_0 = all_image_frame.find(t_0);
                delete it_0->second.pre_integration;
                all_image_frame.erase(all_image_frame.begin(), it_0);
            }
            slideWindowOld();
        }
    }
    else
    {
        if (frame_count == WINDOW_SIZE)
        {
            Headers[frame_count - 1] = Headers[frame_count];
            Ps[frame_count - 1] = Ps[frame_count];
            Rs[frame_count - 1] = Rs[frame_count];

            if(USE_IMU)
            {
                for (unsigned int i = 0; i < dt_buf[frame_count].size(); i++)
                {
                    double tmp_dt = dt_buf[frame_count][i];
                    Vector3d tmp_linear_acceleration = linear_acceleration_buf[frame_count][i];
                    Vector3d tmp_angular_velocity = angular_velocity_buf[frame_count][i];

                    pre_integrations[frame_count - 1]->push_back(tmp_dt, tmp_linear_acceleration, tmp_angular_velocity);

                    dt_buf[frame_count - 1].push_back(tmp_dt);
                    linear_acceleration_buf[frame_count - 1].push_back(tmp_linear_acceleration);
                    angular_velocity_buf[frame_count - 1].push_back(tmp_angular_velocity);
                }

                Vs[frame_count - 1] = Vs[frame_count];
                Bas[frame_count - 1] = Bas[frame_count];
                Bgs[frame_count - 1] = Bgs[frame_count];

                delete pre_integrations[WINDOW_SIZE];
                pre_integrations[WINDOW_SIZE] = new IntegrationBase{acc_0, gyr_0, Bas[WINDOW_SIZE], Bgs[WINDOW_SIZE]};

                dt_buf[WINDOW_SIZE].clear();
                linear_acceleration_buf[WINDOW_SIZE].clear();
                angular_velocity_buf[WINDOW_SIZE].clear();
            }
            slideWindowNew();
        }
    }
}

void Estimator::slideWindowNew()
{
    sum_of_front++;
    f_manager.removeFront(frame_count);
}

void Estimator::slideWindowOld()
{
    sum_of_back++;

    bool shift_depth = solver_flag == NON_LINEAR ? true : false;
    if (shift_depth)
    {
        Matrix3d R0, R1;
        Vector3d P0, P1;
        R0 = back_R0 * ric[0];
        R1 = Rs[0] * ric[0];
        P0 = back_P0 + back_R0 * tic[0];
        P1 = Ps[0] + Rs[0] * tic[0];
        f_manager.removeBackShiftDepth(R0, P0, R1, P1);
    }
    else
        f_manager.removeBack();
}


void Estimator::getPoseInWorldFrame(Eigen::Matrix4d &T)
{
    T = Eigen::Matrix4d::Identity();
    T.block<3, 3>(0, 0) = Rs[frame_count];
    T.block<3, 1>(0, 3) = Ps[frame_count];
}

void Estimator::getPoseInWorldFrame(int index, Eigen::Matrix4d &T)
{
    T = Eigen::Matrix4d::Identity();
    T.block<3, 3>(0, 0) = Rs[index];
    T.block<3, 1>(0, 3) = Ps[index];
}

void Estimator::predictPtsInNextFrame()
{
    //printf("predict pts in next frame\n");
    if(frame_count < 2)
        return;
    // predict next pose. Assume constant velocity motion
    Eigen::Matrix4d curT, prevT, nextT;
    getPoseInWorldFrame(curT);
    getPoseInWorldFrame(frame_count - 1, prevT);
    nextT = curT * (prevT.inverse() * curT);
    map<int, Eigen::Vector3d> predictPts;

    for (auto &it_per_id : f_manager.feature)
    {
        if(it_per_id.estimated_depth > 0)
        {
            int firstIndex = it_per_id.start_frame;
            int lastIndex = it_per_id.start_frame + it_per_id.feature_per_frame.size() - 1;
            //printf("cur frame index  %d last frame index %d\n", frame_count, lastIndex);
            if((int)it_per_id.feature_per_frame.size() >= 2 && lastIndex == frame_count)
            {
                double depth = it_per_id.estimated_depth;
                Vector3d pts_j = ric[0] * (depth * it_per_id.feature_per_frame[0].point) + tic[0];
                Vector3d pts_w = Rs[firstIndex] * pts_j + Ps[firstIndex];
                Vector3d pts_local = nextT.block<3, 3>(0, 0).transpose() * (pts_w - nextT.block<3, 1>(0, 3));
                Vector3d pts_cam = ric[0].transpose() * (pts_local - tic[0]);
                int ptsIndex = it_per_id.feature_id;
                predictPts[ptsIndex] = pts_cam;
            }
        }
    }
    featureTracker.setPrediction(predictPts);
    //printf("estimator output %d predict pts\n",(int)predictPts.size());
}

double Estimator::reprojectionError(Matrix3d &Ri, Vector3d &Pi, Matrix3d &rici, Vector3d &tici,
                                 Matrix3d &Rj, Vector3d &Pj, Matrix3d &ricj, Vector3d &ticj, 
                                 double depth, Vector3d &uvi, Vector3d &uvj)
{
    Vector3d pts_w = Ri * (rici * (depth * uvi) + tici) + Pi;
    Vector3d pts_cj = ricj.transpose() * (Rj.transpose() * (pts_w - Pj) - ticj);
    Vector2d residual = (pts_cj / pts_cj.z()).head<2>() - uvj.head<2>();
    double rx = residual.x();
    double ry = residual.y();
    return sqrt(rx * rx + ry * ry);
}

void Estimator::outliersRejection(set<int> &removeIndex)
{
    //return;
    int feature_index = -1;
    for (auto &it_per_id : f_manager.feature)
    {
        double err = 0;
        int errCnt = 0;
        it_per_id.used_num = it_per_id.feature_per_frame.size();
        if (it_per_id.used_num < 4)
            continue;
        feature_index ++;
        int imu_i = it_per_id.start_frame, imu_j = imu_i - 1;
        Vector3d pts_i = it_per_id.feature_per_frame[0].point;
        double depth = it_per_id.estimated_depth;
        for (auto &it_per_frame : it_per_id.feature_per_frame)
        {
            imu_j++;
            if (imu_i != imu_j)
            {
                Vector3d pts_j = it_per_frame.point;             
                double tmp_error = reprojectionError(Rs[imu_i], Ps[imu_i], ric[0], tic[0], 
                                                    Rs[imu_j], Ps[imu_j], ric[0], tic[0],
                                                    depth, pts_i, pts_j);
                err += tmp_error;
                errCnt++;
                //printf("tmp_error %f\n", FOCAL_LENGTH / 1.5 * tmp_error);
            }
            // need to rewrite projecton factor.........
            if(STEREO && it_per_frame.is_stereo)
            {
                
                Vector3d pts_j_right = it_per_frame.pointRight;
                if(imu_i != imu_j)
                {            
                    double tmp_error = reprojectionError(Rs[imu_i], Ps[imu_i], ric[0], tic[0], 
                                                        Rs[imu_j], Ps[imu_j], ric[1], tic[1],
                                                        depth, pts_i, pts_j_right);
                    err += tmp_error;
                    errCnt++;
                    //printf("tmp_error %f\n", FOCAL_LENGTH / 1.5 * tmp_error);
                }
                else
                {
                    double tmp_error = reprojectionError(Rs[imu_i], Ps[imu_i], ric[0], tic[0], 
                                                        Rs[imu_j], Ps[imu_j], ric[1], tic[1],
                                                        depth, pts_i, pts_j_right);
                    err += tmp_error;
                    errCnt++;
                    //printf("tmp_error %f\n", FOCAL_LENGTH / 1.5 * tmp_error);
                }       
            }
        }
        double ave_err = err / errCnt;
        // T2-WA8: native outlier threshold parametrized (upstream hard 3px; note this
        // is a track AVERAGE so poisoned observations get diluted in long tracks)
        double t2_px_thr = 3.0;
        if (T2_OUTLIER_PX > 0) t2_px_thr = T2_OUTLIER_PX;
        if(ave_err * FOCAL_LENGTH > t2_px_thr)
            removeIndex.insert(it_per_id.feature_id);

    }
}

// T1-E2 C03-A4: returns true when the step was clamped (dt outside [0,0.5]).
// Clamp semantics = T2-U1 style: time-base advances, NO integration for this
// step (advancing time keeps the next healthy dt finite; skipping the advance
// would freeze the chain -- V7 blind-alley, see C03 V11).
bool Estimator::propagateOnce(double &t, Eigen::Vector3d &P, Eigen::Vector3d &V,
                               Eigen::Quaterniond &Q, Eigen::Vector3d &acc_0, Eigen::Vector3d &gyr_0,
                               const Eigen::Vector3d &Ba, const Eigen::Vector3d &Bg,
                               double tn, const Eigen::Vector3d &accn, const Eigen::Vector3d &gyrn)
{
    double dt = tn - t;
    t = tn;
    if (PropagateGuard::dt_invalid(dt))
    {
        acc_0 = accn;
        gyr_0 = gyrn;
        return true;
    }
    Eigen::Vector3d un_acc_0 = Q * (acc_0 - Ba) - g;
    Eigen::Vector3d un_gyr = 0.5 * (gyr_0 + gyrn) - Bg;
    Q = Q * Utility::deltaQ(un_gyr * dt);
    Eigen::Vector3d un_acc_1 = Q * (accn - Ba) - g;
    Eigen::Vector3d un_acc = 0.5 * (un_acc_0 + un_acc_1);
    P = P + dt * V + 0.5 * dt * dt * un_acc;
    V = V + dt * un_acc;
    acc_0 = accn;
    gyr_0 = gyrn;
    return false;
}

void Estimator::fastPredictIMU(double t, Eigen::Vector3d linear_acceleration, Eigen::Vector3d angular_velocity)
{
    bool clamped = propagateOnce(latest_time, latest_P, latest_V, latest_Q, latest_acc_0, latest_gyr_0,
                                 latest_Ba, latest_Bg, t, linear_acceleration, angular_velocity);
    if (clamped)
    {
        propagate_guard.on_clamp();
        if (reanchor_dbg)
        {
            fprintf(stderr, "[E2clamp] latest_time=%.3f t=%.3f clamp_count=%d\n",
                    latest_time, t, propagate_guard.clamp_count);
            fflush(stderr);
        }
    }
}

void Estimator::updateLatestStates(bool set_flag)
{
    mPropagate.lock();
    // T1-E2 C03-A3 beta: init points pass set_flag=true; setting the flag
    // INSIDE the critical section makes the addJump guard true at init
    // (init delta captured) and pins the flag write under the same lock the
    // publisher reads under (TOCTOU window closed at the init path).
    if (set_flag)
        solver_flag = NON_LINEAR;
    // T1-D1 (2026-09-29): shadow chain -- snapshot the continuous propagation
    // state before the overwrite, integrate it alongside the re-anchored chain
    // over the replayed IMU buffer, yielding the simultaneous PURE reanchor
    // delta (shadow - latest) that feeds the publish-side smoother. Kernel
    // states latest_* keep their original semantics, unchanged.
    Eigen::Vector3d sh_P = latest_P, sh_V = latest_V;
    Eigen::Vector3d sh_acc_0 = latest_acc_0, sh_gyr_0 = latest_gyr_0;
    Eigen::Quaterniond sh_Q = latest_Q;
    double sh_t = latest_time;
    const Eigen::Vector3d sh_Ba = latest_Ba, sh_Bg = latest_Bg;

    latest_time = Headers[frame_count] + td;
    latest_P = Ps[frame_count];
    latest_Q = Rs[frame_count];
    latest_V = Vs[frame_count];
    latest_Ba = Bas[frame_count];
    latest_Bg = Bgs[frame_count];
    latest_acc_0 = acc_0;
    latest_gyr_0 = gyr_0;
    mBuf.lock();
    queue<pair<double, Eigen::Vector3d>> tmp_accBuf = accBuf;
    queue<pair<double, Eigen::Vector3d>> tmp_gyrBuf = gyrBuf;
    mBuf.unlock();
    while(!tmp_accBuf.empty())
    {
        double t = tmp_accBuf.front().first;
        Eigen::Vector3d acc = tmp_accBuf.front().second;
        Eigen::Vector3d gyr = tmp_gyrBuf.front().second;
        fastPredictIMU(t, acc, gyr);
        if (REANCHOR_SMOOTH && solver_flag == NON_LINEAR)
            propagateOnce(sh_t, sh_P, sh_V, sh_Q, sh_acc_0, sh_gyr_0, sh_Ba, sh_Bg, t, acc, gyr);
        tmp_accBuf.pop();
        tmp_gyrBuf.pop();
    }
    // T1-E2 C03-A3 gap guard: cross-second time-base break between the
    // shadow chain and the first replay sample -> skip the capture (count
    // it) instead of feeding a meter-scale garbage delta into the smoother;
    // D2 position jump gate remains the raw-stream backstop.
    if (REANCHOR_SMOOTH && solver_flag == NON_LINEAR)
    {
        bool gap = !tmp_accBuf.empty() &&
                   PropagateGuard::gap_skip_needed(sh_t, tmp_accBuf.front().first);
        if (gap)
        {
            propagate_guard.on_gap_skip();
            if (reanchor_dbg)
                fprintf(stderr, "[E2gap] sh_t=%.3f buf0=%.3f skip#=%d\n",
                        sh_t, tmp_accBuf.front().first, propagate_guard.gap_skips);
        }
        else
        {
            if (reanchor_dbg)
                fprintf(stderr, "[E2uls] flag=%d sh_t=%.3f new_t=%.3f dP=[%.4f %.4f %.4f] |dP|=%.4f first_dt=%.4f\n",
                        (int)solver_flag, sh_t, latest_time,
                        (sh_P - latest_P).x(), (sh_P - latest_P).y(), (sh_P - latest_P).z(),
                        (sh_P - latest_P).norm(),
                        tmp_accBuf.empty() ? -1.0 : (tmp_accBuf.front().first - sh_t));
            reanchor_smoother.addJump(sh_P - latest_P, sh_V - latest_V);
        }
    }
    // T1-E2 C03-A4 escape (b): ULS finished (overwrite+replay done) -> the
    // re-anchored chain is trustworthy again, release the publish hold.
    propagate_guard.on_anchor();
    mPropagate.unlock();
}
