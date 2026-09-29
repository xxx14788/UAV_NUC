/*******************************************************
 * Copyright (C) 2019, Aerial Robotics Group, Hong Kong University of Science and Technology
 * 
 * This file is part of VINS.
 * 
 * Licensed under the GNU General Public License v3.0;
 * you may not use this file except in compliance with the License.
 *******************************************************/

#include "feature_manager.h"

int FeaturePerId::endFrame()
{
    return start_frame + feature_per_frame.size() - 1;
}

FeatureManager::FeatureManager(Matrix3d _Rs[])
    : Rs(_Rs)
{
    for (int i = 0; i < NUM_OF_CAM; i++)
        ric[i].setIdentity();
}

void FeatureManager::setRic(Matrix3d _ric[])
{
    for (int i = 0; i < NUM_OF_CAM; i++)
    {
        ric[i] = _ric[i];
    }
}

void FeatureManager::clearState()
{
    feature.clear();
}

int FeatureManager::getFeatureCount()
{
    int cnt = 0;
    for (auto &it : feature)
    {
        it.used_num = it.feature_per_frame.size();
        if (it.used_num >= 4)
        {
            cnt++;
        }
    }
    return cnt;
}


bool FeatureManager::addFeatureCheckParallax(int frame_count, const map<int, vector<pair<int, Eigen::Matrix<double, 7, 1>>>> &image, double td)
{
    ROS_DEBUG("input feature: %d", (int)image.size());
    ROS_DEBUG("num of feature: %d", getFeatureCount());
    double parallax_sum = 0;
    int parallax_num = 0;
    last_track_num = 0;
    last_average_parallax = 0;
    new_feature_num = 0;
    long_track_num = 0;
    for (auto &id_pts : image)
    {
        FeaturePerFrame f_per_fra(id_pts.second[0].second, td);
        assert(id_pts.second[0].first == 0);
        if(id_pts.second.size() == 2)
        {
            f_per_fra.rightObservation(id_pts.second[1].second);
            assert(id_pts.second[1].first == 1);
        }

        int feature_id = id_pts.first;
        auto it = find_if(feature.begin(), feature.end(), [feature_id](const FeaturePerId &it)
                          {
            return it.feature_id == feature_id;
                          });

        if (it == feature.end())
        {
            feature.push_back(FeaturePerId(feature_id, frame_count));
            feature.back().feature_per_frame.push_back(f_per_fra);
            new_feature_num++;
        }
        else if (it->feature_id == feature_id)
        {
            it->feature_per_frame.push_back(f_per_fra);
            last_track_num++;
            if( it-> feature_per_frame.size() >= 4)
                long_track_num++;
        }
    }

    //if (frame_count < 2 || last_track_num < 20)
    //if (frame_count < 2 || last_track_num < 20 || new_feature_num > 0.5 * last_track_num)
    if (frame_count < 2 || last_track_num < 20 || long_track_num < 40 || new_feature_num > 0.5 * last_track_num)
    {
        // T2-R3.3 特征雨护栏: 完全断链(last_track_num<10)时 new>0.5*last 是 LK 断链的
        // 被动产物而非场景切换信号——原逻辑此刻狂滑 marg old,窗口仅存的历史约束被丢弃,
        // 优化器在无视觉约束窗口把 V/tic/Bas 联合推向爆走(C_shift 三配置实测 track=0
        // 全程+22.43-22.87s 共爆; t2_lk_survival.py 数据侧存活率中位 0.00 独立实锤)。
        // 改为不 marg old(调用方走 MARGIN_SECOND_NEW,窗口不推进),老帧约束保留,
        // IMU 传播继续,特征链恢复后自动回归正常滑窗。frame_count<2 保持原语义。
        if (frame_count >= 2 && last_track_num < 10 &&
            new_feature_num > 0.5 * std::max(last_track_num, 1))
            return false;
        return true;
    }

    for (auto &it_per_id : feature)
    {
        if (it_per_id.start_frame <= frame_count - 2 &&
            it_per_id.start_frame + int(it_per_id.feature_per_frame.size()) - 1 >= frame_count - 1)
        {
            parallax_sum += compensatedParallax2(it_per_id, frame_count);
            parallax_num++;
        }
    }

    if (parallax_num == 0)
    {
        return true;
    }
    else
    {
        ROS_DEBUG("parallax_sum: %lf, parallax_num: %d", parallax_sum, parallax_num);
        ROS_DEBUG("current parallax: %lf", parallax_sum / parallax_num * FOCAL_LENGTH);
        last_average_parallax = parallax_sum / parallax_num * FOCAL_LENGTH;
        return parallax_sum / parallax_num >= MIN_PARALLAX;
    }
}

vector<pair<Vector3d, Vector3d>> FeatureManager::getCorresponding(int frame_count_l, int frame_count_r)
{
    vector<pair<Vector3d, Vector3d>> corres;
    for (auto &it : feature)
    {
        if (it.start_frame <= frame_count_l && it.endFrame() >= frame_count_r)
        {
            Vector3d a = Vector3d::Zero(), b = Vector3d::Zero();
            int idx_l = frame_count_l - it.start_frame;
            int idx_r = frame_count_r - it.start_frame;

            a = it.feature_per_frame[idx_l].point;

            b = it.feature_per_frame[idx_r].point;
            
            corres.push_back(make_pair(a, b));
        }
    }
    return corres;
}

void FeatureManager::setDepth(const VectorXd &x)
{
    int feature_index = -1;
    for (auto &it_per_id : feature)
    {
        it_per_id.used_num = it_per_id.feature_per_frame.size();
        if (it_per_id.used_num < 4)
            continue;

        it_per_id.estimated_depth = 1.0 / x(++feature_index);
        //ROS_INFO("feature id %d , start_frame %d, depth %f ", it_per_id->feature_id, it_per_id-> start_frame, it_per_id->estimated_depth);
        if (it_per_id.estimated_depth < 0)
        {
            it_per_id.solve_flag = 2;
        }
        else
            it_per_id.solve_flag = 1;
    }
}

void FeatureManager::removeFailures()
{
    for (auto it = feature.begin(), it_next = feature.begin();
         it != feature.end(); it = it_next)
    {
        it_next++;
        if (it->solve_flag == 2)
            feature.erase(it);
    }
}

void FeatureManager::clearDepth()
{
    for (auto &it_per_id : feature)
        it_per_id.estimated_depth = -1;
}

VectorXd FeatureManager::getDepthVector()
{
    VectorXd dep_vec(getFeatureCount());
    int feature_index = -1;
    for (auto &it_per_id : feature)
    {
        it_per_id.used_num = it_per_id.feature_per_frame.size();
        if (it_per_id.used_num < 4)
            continue;
#if 1
        dep_vec(++feature_index) = 1. / it_per_id.estimated_depth;
#else
        dep_vec(++feature_index) = it_per_id->estimated_depth;
#endif
    }
    return dep_vec;
}


void FeatureManager::triangulatePoint(Eigen::Matrix<double, 3, 4> &Pose0, Eigen::Matrix<double, 3, 4> &Pose1,
                        Eigen::Vector2d &point0, Eigen::Vector2d &point1, Eigen::Vector3d &point_3d)
{
    Eigen::Matrix4d design_matrix = Eigen::Matrix4d::Zero();
    design_matrix.row(0) = point0[0] * Pose0.row(2) - Pose0.row(0);
    design_matrix.row(1) = point0[1] * Pose0.row(2) - Pose0.row(1);
    design_matrix.row(2) = point1[0] * Pose1.row(2) - Pose1.row(0);
    design_matrix.row(3) = point1[1] * Pose1.row(2) - Pose1.row(1);
    Eigen::Vector4d triangulated_point;
    triangulated_point =
              design_matrix.jacobiSvd(Eigen::ComputeFullV).matrixV().rightCols<1>();
    point_3d(0) = triangulated_point(0) / triangulated_point(3);
    point_3d(1) = triangulated_point(1) / triangulated_point(3);
    point_3d(2) = triangulated_point(2) / triangulated_point(3);
}


bool FeatureManager::solvePoseByPnP(Eigen::Matrix3d &R, Eigen::Vector3d &P, 
                                      vector<cv::Point2f> &pts2D, vector<cv::Point3f> &pts3D)
{
    Eigen::Matrix3d R_initial;
    Eigen::Vector3d P_initial;

    // w_T_cam ---> cam_T_w 
    R_initial = R.inverse();
    P_initial = -(R_initial * P);

    //printf("pnp size %d \n",(int)pts2D.size() );
    if (int(pts2D.size()) < 4)
    {
        printf("feature tracking not enough, please slowly move you device! \n");
        return false;
    }
    cv::Mat r, rvec, t, D, tmp_r;
    cv::eigen2cv(R_initial, tmp_r);
    cv::Rodrigues(tmp_r, rvec);
    cv::eigen2cv(P_initial, t);
    cv::Mat K = (cv::Mat_<double>(3, 3) << 1, 0, 0, 0, 1, 0, 0, 0, 1);  
    bool pnp_succ;
    // T2-W4 (2026-09-27): 改用 RANSAC 版 PnP。裸 solvePnP 会被退化立体
    // 三角化点（零视差→深度 1e17）带偏，帧姿态直接天文数字（bag-B 初始化
    // 窗口 |P|=8e17 实测），下游全灭。RANSAC 外点剔除是上游注释掉的原选。
    cv::Mat pnp_inliers;
    pnp_succ = cv::solvePnPRansac(pts3D, pts2D, K, D, rvec, t, 1,
                                  100, 8.0 / 460.0, 0.99, pnp_inliers);

    if(!pnp_succ)
    {
        printf("pnp failed ! \n");
        return false;
    }
    cv::Rodrigues(rvec, r);
    //cout << "r " << endl << r << endl;
    Eigen::MatrixXd R_pnp;
    cv::cv2eigen(r, R_pnp);
    Eigen::MatrixXd T_pnp;
    cv::cv2eigen(t, T_pnp);

    // cam_T_w ---> w_T_cam
    R = R_pnp.transpose();
    P = R * (-T_pnp);

    return true;
}

void FeatureManager::initFramePoseByPnP(int frameCnt, Vector3d Ps[], Matrix3d Rs[], Vector3d tic[], Matrix3d ric[])
{

    if(frameCnt > 0)
    {
        vector<cv::Point2f> pts2D;
        vector<cv::Point3f> pts3D;
        for (auto &it_per_id : feature)
        {
            if (it_per_id.estimated_depth > 0)
            {
                int index = frameCnt - it_per_id.start_frame;
                if((int)it_per_id.feature_per_frame.size() >= index + 1)
                {
                    Vector3d ptsInCam = ric[0] * (it_per_id.feature_per_frame[0].point * it_per_id.estimated_depth) + tic[0];
                    Vector3d ptsInWorld = Rs[it_per_id.start_frame] * ptsInCam + Ps[it_per_id.start_frame];

                    cv::Point3f point3d(ptsInWorld.x(), ptsInWorld.y(), ptsInWorld.z());
                    cv::Point2f point2d(it_per_id.feature_per_frame[index].point.x(), it_per_id.feature_per_frame[index].point.y());
                    pts3D.push_back(point3d);
                    pts2D.push_back(point2d); 
                }
            }
        }
        Eigen::Matrix3d RCam;
        Eigen::Vector3d PCam;
        // trans to w_T_cam
        RCam = Rs[frameCnt - 1] * ric[0];
        PCam = Rs[frameCnt - 1] * tic[0] + Ps[frameCnt - 1];

        if(solvePoseByPnP(RCam, PCam, pts2D, pts3D))
        {
            // trans to w_T_imu
            Rs[frameCnt] = RCam * ric[0].transpose(); 
            Ps[frameCnt] = -RCam * ric[0].transpose() * tic[0] + PCam;

            Eigen::Quaterniond Q(Rs[frameCnt]);
            //cout << "frameCnt: " << frameCnt <<  " pnp Q " << Q.w() << " " << Q.vec().transpose() << endl;
            //cout << "frameCnt: " << frameCnt << " pnp P " << Ps[frameCnt].transpose() << endl;
        }
    }
}


// T2-WA1: SVD second-solution depth for a (stereo) feature - cross-check data
// source for the depth-domain gate design (stereo solution vs multi-frame SVD).
static bool t2SvdDepth(const FeaturePerId &fp, int frameCnt, Vector3d Ps[], Matrix3d Rs[],
                       Vector3d tic[], Matrix3d ric[], double &depth_out)
{
    if (fp.feature_per_frame.size() < 2) return false;
    if (fp.start_frame + (int)fp.feature_per_frame.size() - 1 > frameCnt) return false;
    int imu_i = fp.start_frame, imu_j = imu_i - 1;
    Eigen::MatrixXd A(2 * fp.feature_per_frame.size(), 4);
    int idx = 0;
    Eigen::Vector3d t0 = Ps[imu_i] + Rs[imu_i] * tic[0];
    Eigen::Matrix3d R0 = Rs[imu_i] * ric[0];
    for (auto &fr : fp.feature_per_frame)
    {
        imu_j++;
        Eigen::Vector3d t1 = Ps[imu_j] + Rs[imu_j] * tic[0];
        Eigen::Matrix3d R1 = Rs[imu_j] * ric[0];
        Eigen::Vector3d t = R0.transpose() * (t1 - t0);
        Eigen::Matrix3d R = R0.transpose() * R1;
        Eigen::Matrix<double, 3, 4> P;
        P.leftCols<3>() = R.transpose();
        P.rightCols<1>() = -R.transpose() * t;
        Eigen::Vector3d f = fr.point.normalized();
        A.row(idx++) = f[0] * P.row(2) - f[2] * P.row(0);
        A.row(idx++) = f[1] * P.row(2) - f[2] * P.row(1);
    }
    Eigen::Vector4d V = Eigen::JacobiSVD<Eigen::MatrixXd>(A, Eigen::ComputeThinV).matrixV().rightCols<1>();
    if (std::fabs(V[3]) < 1e-12) return false;
    double d = V[2] / V[3];
    if (!(d > 0) || !std::isfinite(d)) return false;
    depth_out = d;
    return true;
}

void FeatureManager::triangulate(int frameCnt, Vector3d Ps[], Matrix3d Rs[], Vector3d tic[], Matrix3d ric[])
{
    // T2-WA1G: depth-domain gate - out-of-range / cross-disagreeing features are
    // erased after the loop (INIT_DEPTH silent pseudo-depth path fully removed
    // when gate on; absent config key = gate off = upstream behavior bit-identical)
    std::set<int> t2_gate_reject;
    int t2_stat_tri = 0, t2_stat_rej = 0, t2_stat_xrej = 0, t2_stat_init = 0;
    for (auto &it_per_id : feature)
    {
        if (it_per_id.estimated_depth > 0)
        {
            // T2-WA1 xcross: periodic stereo-vs-SVD dual-solution dump (census data source)
            if (it_per_id.feature_per_frame.size() >= 2 &&
                it_per_id.feature_per_frame[0].is_stereo &&
                frameCnt - it_per_id.t2_xcheck_frame >= 5)
            {
                double d2 = -1.0;
                if (t2SvdDepth(it_per_id, frameCnt, Ps, Rs, tic, ric, d2) && d2 > 0)
                {
                    double mx = std::max(it_per_id.estimated_depth, d2);
                    double rel = (mx > 1e-9) ? std::fabs(it_per_id.estimated_depth - d2) / mx : 0.0;
                    printf("[T2xcross] t=%.4f id=%d est=%.4f svd=%.4f rel=%.4f track=%d sf=%d\n",
                           t2_cur_t, it_per_id.feature_id, it_per_id.estimated_depth, d2, rel,
                           (int)it_per_id.feature_per_frame.size(), it_per_id.start_frame);
                    it_per_id.t2_xcheck_frame = frameCnt;
                    // T2-WA1G NOTE: cross-disagreement REJECTION was falsified by census
                    // data (2026-09-30: pass-bag ROUTE112652 rel P50=0.849, gt30=77% -
                    // far-range features have intrinsically high solution variance at
                    // 0.1m baseline; any tol would massacre healthy tracks). Dump-only.
                }
            }
            continue;
        }
        t2_stat_tri++;

        if(STEREO && it_per_id.feature_per_frame[0].is_stereo)
        {
            int imu_i = it_per_id.start_frame;
            Eigen::Matrix<double, 3, 4> leftPose;
            Eigen::Vector3d t0 = Ps[imu_i] + Rs[imu_i] * tic[0];
            Eigen::Matrix3d R0 = Rs[imu_i] * ric[0];
            leftPose.leftCols<3>() = R0.transpose();
            leftPose.rightCols<1>() = -R0.transpose() * t0;
            //cout << "left pose " << leftPose << endl;

            Eigen::Matrix<double, 3, 4> rightPose;
            Eigen::Vector3d t1 = Ps[imu_i] + Rs[imu_i] * tic[1];
            Eigen::Matrix3d R1 = Rs[imu_i] * ric[1];
            rightPose.leftCols<3>() = R1.transpose();
            rightPose.rightCols<1>() = -R1.transpose() * t1;
            //cout << "right pose " << rightPose << endl;

            Eigen::Vector2d point0, point1;
            Eigen::Vector3d point3d;
            point0 = it_per_id.feature_per_frame[0].point.head(2);
            point1 = it_per_id.feature_per_frame[0].pointRight.head(2);
            //cout << "point0 " << point0.transpose() << endl;
            //cout << "point1 " << point1.transpose() << endl;

            triangulatePoint(leftPose, rightPose, point0, point1, point3d);
            Eigen::Vector3d localPoint;
            localPoint = leftPose.leftCols<3>() * point3d + leftPose.rightCols<1>();
            double depth = localPoint.z();
            // T2-WA1 census dump: stereo branch
            {
                double d2 = -1.0;
                t2SvdDepth(it_per_id, frameCnt, Ps, Rs, tic, ric, d2);
                printf("[T2depth] t=%.4f id=%d src=stereo u=%.1f v=%.1f depth=%.4f depth2=%.4f track=%d sf=%d flag=%s\n",
                       t2_cur_t, it_per_id.feature_id,
                       it_per_id.feature_per_frame[0].uv.x(), it_per_id.feature_per_frame[0].uv.y(),
                       (depth > 0) ? depth : INIT_DEPTH, d2,
                       (int)it_per_id.feature_per_frame.size(), it_per_id.start_frame,
                       (depth > 0) ? "ok" : "init_neg");
            }
            // T2-WA1G: stereo branch gate - out-of-range depth rejects the track
            // (replaces the silent INIT_DEPTH pseudo-depth path when gate on)
            if (T2_DEPTH_GATE)
            {
                if (depth < T2_DEPTH_MIN || depth > T2_DEPTH_MAX || !(depth > 0))
                {
                    t2_gate_reject.insert(it_per_id.feature_id);
                    t2_stat_rej++;
                    continue;
                }
                it_per_id.estimated_depth = depth;
                continue;
            }
            if (depth > 0)
                it_per_id.estimated_depth = depth;
            else
            {
                it_per_id.estimated_depth = INIT_DEPTH;
                t2_stat_init++;
            }
            /*
            Vector3d ptsGt = pts_gt[it_per_id.feature_id];
            printf("stereo %d pts: %f %f %f gt: %f %f %f \n",it_per_id.feature_id, point3d.x(), point3d.y(), point3d.z(),
                                                            ptsGt.x(), ptsGt.y(), ptsGt.z());
            */
            continue;
        }
        else if(it_per_id.feature_per_frame.size() > 1)
        {
            int imu_i = it_per_id.start_frame;
            Eigen::Matrix<double, 3, 4> leftPose;
            Eigen::Vector3d t0 = Ps[imu_i] + Rs[imu_i] * tic[0];
            Eigen::Matrix3d R0 = Rs[imu_i] * ric[0];
            leftPose.leftCols<3>() = R0.transpose();
            leftPose.rightCols<1>() = -R0.transpose() * t0;

            imu_i++;
            Eigen::Matrix<double, 3, 4> rightPose;
            Eigen::Vector3d t1 = Ps[imu_i] + Rs[imu_i] * tic[0];
            Eigen::Matrix3d R1 = Rs[imu_i] * ric[0];
            rightPose.leftCols<3>() = R1.transpose();
            rightPose.rightCols<1>() = -R1.transpose() * t1;

            Eigen::Vector2d point0, point1;
            Eigen::Vector3d point3d;
            point0 = it_per_id.feature_per_frame[0].point.head(2);
            point1 = it_per_id.feature_per_frame[1].point.head(2);
            triangulatePoint(leftPose, rightPose, point0, point1, point3d);
            Eigen::Vector3d localPoint;
            localPoint = leftPose.leftCols<3>() * point3d + leftPose.rightCols<1>();
            double depth = localPoint.z();
            // T2-WA1 census dump: two-frame motion branch (no right obs -> no cross-solution)
            printf("[T2depth] t=%.4f id=%d src=motion2 u=%.1f v=%.1f depth=%.4f depth2=-1.0000 track=%d sf=%d flag=%s\n",
                   t2_cur_t, it_per_id.feature_id,
                   it_per_id.feature_per_frame[0].uv.x(), it_per_id.feature_per_frame[0].uv.y(),
                   (depth > 0) ? depth : INIT_DEPTH,
                   (int)it_per_id.feature_per_frame.size(), it_per_id.start_frame,
                   (depth > 0) ? "ok" : "init_neg");
            // T2-WA1G: two-frame motion branch gate (same policy as stereo)
            if (T2_DEPTH_GATE)
            {
                if (depth < T2_DEPTH_MIN || depth > T2_DEPTH_MAX || !(depth > 0))
                {
                    t2_gate_reject.insert(it_per_id.feature_id);
                    t2_stat_rej++;
                    continue;
                }
                it_per_id.estimated_depth = depth;
                continue;
            }
            if (depth > 0)
                it_per_id.estimated_depth = depth;
            else
            {
                it_per_id.estimated_depth = INIT_DEPTH;
                t2_stat_init++;
            }
            /*
            Vector3d ptsGt = pts_gt[it_per_id.feature_id];
            printf("motion  %d pts: %f %f %f gt: %f %f %f \n",it_per_id.feature_id, point3d.x(), point3d.y(), point3d.z(),
                                                            ptsGt.x(), ptsGt.y(), ptsGt.z());
            */
            continue;
        }
        it_per_id.used_num = it_per_id.feature_per_frame.size();
        if (it_per_id.used_num < 4)
            continue;

        int imu_i = it_per_id.start_frame, imu_j = imu_i - 1;

        Eigen::MatrixXd svd_A(2 * it_per_id.feature_per_frame.size(), 4);
        int svd_idx = 0;

        Eigen::Matrix<double, 3, 4> P0;
        Eigen::Vector3d t0 = Ps[imu_i] + Rs[imu_i] * tic[0];
        Eigen::Matrix3d R0 = Rs[imu_i] * ric[0];
        P0.leftCols<3>() = Eigen::Matrix3d::Identity();
        P0.rightCols<1>() = Eigen::Vector3d::Zero();

        for (auto &it_per_frame : it_per_id.feature_per_frame)
        {
            imu_j++;

            Eigen::Vector3d t1 = Ps[imu_j] + Rs[imu_j] * tic[0];
            Eigen::Matrix3d R1 = Rs[imu_j] * ric[0];
            Eigen::Vector3d t = R0.transpose() * (t1 - t0);
            Eigen::Matrix3d R = R0.transpose() * R1;
            Eigen::Matrix<double, 3, 4> P;
            P.leftCols<3>() = R.transpose();
            P.rightCols<1>() = -R.transpose() * t;
            Eigen::Vector3d f = it_per_frame.point.normalized();
            svd_A.row(svd_idx++) = f[0] * P.row(2) - f[2] * P.row(0);
            svd_A.row(svd_idx++) = f[1] * P.row(2) - f[2] * P.row(1);

            if (imu_i == imu_j)
                continue;
        }
        ROS_ASSERT(svd_idx == svd_A.rows());
        Eigen::Vector4d svd_V = Eigen::JacobiSVD<Eigen::MatrixXd>(svd_A, Eigen::ComputeThinV).matrixV().rightCols<1>();
        double svd_method = svd_V[2] / svd_V[3];
        //it_per_id->estimated_depth = -b / A;
        //it_per_id->estimated_depth = svd_V[2] / svd_V[3];

        it_per_id.estimated_depth = svd_method;
        //it_per_id->estimated_depth = INIT_DEPTH;

        // T2-WA1 census dump: multi-frame SVD branch (INIT_DEPTH replace at <0.1 exposed)
        printf("[T2depth] t=%.4f id=%d src=svd u=%.1f v=%.1f depth=%.4f depth2=-1.0000 track=%d sf=%d flag=%s\n",
               t2_cur_t, it_per_id.feature_id,
               it_per_id.feature_per_frame[0].uv.x(), it_per_id.feature_per_frame[0].uv.y(),
               (it_per_id.estimated_depth < 0.1) ? INIT_DEPTH : it_per_id.estimated_depth,
               (int)it_per_id.feature_per_frame.size(), it_per_id.start_frame,
               (it_per_id.estimated_depth < 0.1) ? "init_low" : "ok");

        // T2-WA1G: SVD branch gate - out-of-range or degenerate depth rejects the
        // track (replaces the silent <0.1 -> INIT_DEPTH pseudo-depth path)
        if (T2_DEPTH_GATE)
        {
            if (it_per_id.estimated_depth < T2_DEPTH_MIN ||
                it_per_id.estimated_depth > T2_DEPTH_MAX)
            {
                t2_gate_reject.insert(it_per_id.feature_id);
                t2_stat_rej++;
                it_per_id.estimated_depth = -1.0;
                continue;
            }
            continue;
        }
        if (it_per_id.estimated_depth < 0.1)
        {
            it_per_id.estimated_depth = INIT_DEPTH;
            t2_stat_init++;
        }

    }
    // T2-WA1G: apply gate rejections + per-frame stats (T2frame schema)
    if (!t2_gate_reject.empty())
    {
        for (auto it = feature.begin(); it != feature.end();)
        {
            if (t2_gate_reject.count(it->feature_id))
                it = feature.erase(it);
            else
                ++it;
        }
    }
    printf("[T2gate] t=%.4f tri=%d rej=%d xrej=%d init_replace=%d gate=%d\n",
           t2_cur_t, t2_stat_tri, t2_stat_rej, t2_stat_xrej, t2_stat_init, T2_DEPTH_GATE);
}

void FeatureManager::removeOutlier(set<int> &outlierIndex)
{
    std::set<int>::iterator itSet;
    for (auto it = feature.begin(), it_next = feature.begin();
         it != feature.end(); it = it_next)
    {
        it_next++;
        int index = it->feature_id;
        itSet = outlierIndex.find(index);
        if(itSet != outlierIndex.end())
        {
            feature.erase(it);
            //printf("remove outlier %d \n", index);
        }
    }
}

void FeatureManager::removeBackShiftDepth(Eigen::Matrix3d marg_R, Eigen::Vector3d marg_P, Eigen::Matrix3d new_R, Eigen::Vector3d new_P)
{
    for (auto it = feature.begin(), it_next = feature.begin();
         it != feature.end(); it = it_next)
    {
        it_next++;

        if (it->start_frame != 0)
            it->start_frame--;
        else
        {
            Eigen::Vector3d uv_i = it->feature_per_frame[0].point;  
            it->feature_per_frame.erase(it->feature_per_frame.begin());
            if (it->feature_per_frame.size() < 2)
            {
                feature.erase(it);
                continue;
            }
            else
            {
                Eigen::Vector3d pts_i = uv_i * it->estimated_depth;
                Eigen::Vector3d w_pts_i = marg_R * pts_i + marg_P;
                Eigen::Vector3d pts_j = new_R.transpose() * (w_pts_i - new_P);
                double dep_j = pts_j(2);
                // T2-WA1 census dump: depth transfer on slide - only INIT_DEPTH replacements
                // (ok-shift is routine transfer, ~1/3 of log volume, no analytic value)
                if (!(dep_j > 0))
                    printf("[T2depth] t=%.4f id=%d src=shift u=-1 v=-1 depth=%.4f depth2=-1.0000 track=%d sf=0 flag=%s\n",
                           t2_cur_t, it->feature_id, INIT_DEPTH,
                           (int)it->feature_per_frame.size(), "init_neg");
                // T2-WA1G: transfer gate - out-of-range reprojected depth drops the track
                // (instead of silent INIT_DEPTH pseudo-depth when gate on)
                if (T2_DEPTH_GATE && !(dep_j >= T2_DEPTH_MIN && dep_j <= T2_DEPTH_MAX))
                {
                    it = feature.erase(it);
                    continue;
                }
                if (dep_j > 0)
                    it->estimated_depth = dep_j;
                else
                    it->estimated_depth = INIT_DEPTH;
            }
        }
        // remove tracking-lost feature after marginalize
        /*
        if (it->endFrame() < WINDOW_SIZE - 1)
        {
            feature.erase(it);
        }
        */
    }
}

void FeatureManager::removeBack()
{
    for (auto it = feature.begin(), it_next = feature.begin();
         it != feature.end(); it = it_next)
    {
        it_next++;

        if (it->start_frame != 0)
            it->start_frame--;
        else
        {
            it->feature_per_frame.erase(it->feature_per_frame.begin());
            if (it->feature_per_frame.size() == 0)
                feature.erase(it);
        }
    }
}

void FeatureManager::removeFront(int frame_count)
{
    for (auto it = feature.begin(), it_next = feature.begin(); it != feature.end(); it = it_next)
    {
        it_next++;

        if (it->start_frame == frame_count)
        {
            it->start_frame--;
        }
        else
        {
            int j = WINDOW_SIZE - 1 - it->start_frame;
            if (it->endFrame() < frame_count - 1)
                continue;
            it->feature_per_frame.erase(it->feature_per_frame.begin() + j);
            if (it->feature_per_frame.size() == 0)
                feature.erase(it);
        }
    }
}

double FeatureManager::compensatedParallax2(const FeaturePerId &it_per_id, int frame_count)
{
    //check the second last frame is keyframe or not
    //parallax betwwen seconde last frame and third last frame
    const FeaturePerFrame &frame_i = it_per_id.feature_per_frame[frame_count - 2 - it_per_id.start_frame];
    const FeaturePerFrame &frame_j = it_per_id.feature_per_frame[frame_count - 1 - it_per_id.start_frame];

    double ans = 0;
    Vector3d p_j = frame_j.point;

    double u_j = p_j(0);
    double v_j = p_j(1);

    Vector3d p_i = frame_i.point;
    Vector3d p_i_comp;

    //int r_i = frame_count - 2;
    //int r_j = frame_count - 1;
    //p_i_comp = ric[camera_id_j].transpose() * Rs[r_j].transpose() * Rs[r_i] * ric[camera_id_i] * p_i;
    p_i_comp = p_i;
    double dep_i = p_i(2);
    double u_i = p_i(0) / dep_i;
    double v_i = p_i(1) / dep_i;
    double du = u_i - u_j, dv = v_i - v_j;

    double dep_i_comp = p_i_comp(2);
    double u_i_comp = p_i_comp(0) / dep_i_comp;
    double v_i_comp = p_i_comp(1) / dep_i_comp;
    double du_comp = u_i_comp - u_j, dv_comp = v_i_comp - v_j;

    ans = max(ans, sqrt(min(du * du + dv * dv, du_comp * du_comp + dv_comp * dv_comp)));

    return ans;
}