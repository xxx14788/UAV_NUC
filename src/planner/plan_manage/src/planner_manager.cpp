// #include <fstream>
#include <plan_manage/planner_manager.h>
#include <thread>
#include "visualization_msgs/Marker.h" // zx-todo

namespace ego_planner
{

  // SECTION interfaces for setup and query

  EGOPlannerManager::EGOPlannerManager() {}

  EGOPlannerManager::~EGOPlannerManager() {}

  void EGOPlannerManager::initPlanModules(ros::NodeHandle &nh, PlanningVisualization::Ptr vis)
  {
    /* read algorithm parameters */

    nh.param("manager/max_vel", pp_.max_vel_, -1.0);
    nh.param("manager/max_acc", pp_.max_acc_, -1.0);
    nh.param("manager/max_jerk", pp_.max_jerk_, -1.0);
    nh.param("manager/feasibility_tolerance", pp_.feasibility_tolerance_, 0.0);
    nh.param("manager/control_points_distance", pp_.ctrl_pt_dist, -1.0);
    nh.param("manager/planning_horizon", pp_.planning_horizen_, 5.0);
    nh.param("manager/seed_horizon", pp_.seed_horizon_, 2.0);   // 2026-11-15（P2）
    nh.param("manager/use_distinctive_trajs", pp_.use_distinctive_trajs, false);
    nh.param("manager/drone_id", pp_.drone_id, -1);

    local_data_.traj_id_ = 0;
    grid_map_.reset(new GridMap);
    grid_map_->initMap(nh);

    // obj_predictor_.reset(new fast_planner::ObjPredictor(nh));
    // obj_predictor_->init();
    // obj_pub_ = nh.advertise<visualization_msgs::Marker>("/dynamic/obj_prdi", 10); // zx-todo

    bspline_optimizer_.reset(new BsplineOptimizer);
    bspline_optimizer_->setParam(nh);
    bspline_optimizer_->setEnvironment(grid_map_, obj_predictor_);
    bspline_optimizer_->a_star_.reset(new AStar);
    bspline_optimizer_->a_star_->initGridMap(grid_map_, Eigen::Vector3i(100, 100, 100));

    visualization_ = vis;
  }

  // !SECTION

  // SECTION rebond replanning

  bool EGOPlannerManager::reboundReplan(Eigen::Vector3d start_pt, Eigen::Vector3d start_vel,
                                        Eigen::Vector3d start_acc, Eigen::Vector3d local_target_pt,
                                        Eigen::Vector3d local_target_vel, bool flag_polyInit, bool flag_randomPolyTraj)
  {
    static int count = 0;
    printf("\033[47;30m\n[drone %d replan %d]==============================================\033[0m\n", pp_.drone_id, count++);
    // cout.precision(3);
    // cout << "start: " << start_pt.transpose() << ", " << start_vel.transpose() << "\ngoal:" << local_target_pt.transpose() << ", " << local_target_vel.transpose()
    //      << endl;

    if ((start_pt - local_target_pt).norm() < 0.2)
    {
      // 2026-11-15（审查修正）：到点不是失败；返回 true 让 FSM 保持/结束，别让 P3 计时器
      // 在目标 0.2 m 内 1.5 s 后误触发 EMERGENCY。
      cout << "Close to goal" << endl;
      return true;
    }

    bspline_optimizer_->setLocalTargetPt(local_target_pt);

    ros::Time t_start = ros::Time::now();
    ros::Duration t_init, t_opt, t_refine;

    /*** STEP 1: INIT ***/
    double ts = (start_pt - local_target_pt).norm() > 0.1 ? pp_.ctrl_pt_dist / pp_.max_vel_ * 1.5 : pp_.ctrl_pt_dist / pp_.max_vel_ * 5; // pp_.ctrl_pt_dist / pp_.max_vel_ is too tense, and will surely exceed the acc/vel limits
    vector<Eigen::Vector3d> point_set, start_end_derivatives;
    static bool flag_first_call = true, flag_force_polynomial = false;
    bool flag_regenerate = false;
    do
    {
      point_set.clear();
      start_end_derivatives.clear();
      flag_regenerate = false;

      if (flag_first_call || flag_polyInit || flag_force_polynomial /*|| ( start_pt - local_target_pt ).norm() < 1.0*/) // Initial path generated from a min-snap traj by order.
      {
        flag_first_call = false;
        flag_force_polynomial = false;

        PolynomialTraj gl_traj;

        double dist = (start_pt - local_target_pt).norm();
        double time = pow(pp_.max_vel_, 2) / pp_.max_acc_ > dist ? sqrt(dist / pp_.max_acc_) : (dist - pow(pp_.max_vel_, 2) / pp_.max_acc_) / pp_.max_vel_ + 2 * pp_.max_vel_ / pp_.max_acc_;

        if (!flag_randomPolyTraj)
        {
          gl_traj = PolynomialTraj::one_segment_traj_gen(start_pt, start_vel, start_acc, local_target_pt, local_target_vel, Eigen::Vector3d::Zero(), time);
        }
        else
        {
          Eigen::Vector3d horizen_dir = ((start_pt - local_target_pt).cross(Eigen::Vector3d(0, 0, 1))).normalized();
          Eigen::Vector3d vertical_dir = ((start_pt - local_target_pt).cross(horizen_dir)).normalized();
          Eigen::Vector3d random_inserted_pt = (start_pt + local_target_pt) / 2 +
                                               (((double)rand()) / RAND_MAX - 0.5) * (start_pt - local_target_pt).norm() * horizen_dir * 0.8 * (-0.978 / (continous_failures_count_ + 0.989) + 0.989) +
                                               (((double)rand()) / RAND_MAX - 0.5) * (start_pt - local_target_pt).norm() * vertical_dir * 0.4 * (-0.978 / (continous_failures_count_ + 0.989) + 0.989);
          Eigen::MatrixXd pos(3, 3);
          pos.col(0) = start_pt;
          pos.col(1) = random_inserted_pt;
          pos.col(2) = local_target_pt;
          Eigen::VectorXd t(2);
          t(0) = t(1) = time / 2;
          gl_traj = PolynomialTraj::minSnapTraj(pos, start_vel, local_target_vel, start_acc, Eigen::Vector3d::Zero(), t);
        }

        double t;
        bool flag_too_far;
        ts *= 1.5; // ts will be divided by 1.5 in the next
        do
        {
          ts /= 1.5;
          point_set.clear();
          flag_too_far = false;
          Eigen::Vector3d last_pt = gl_traj.evaluate(0);
          for (t = 0; t < time; t += ts)
          {
            Eigen::Vector3d pt = gl_traj.evaluate(t);
            if ((last_pt - pt).norm() > pp_.ctrl_pt_dist * 1.5)
            {
              flag_too_far = true;
              break;
            }
            last_pt = pt;
            point_set.push_back(pt);
          }
        } while (flag_too_far || point_set.size() < 7); // To make sure the initial path has enough points.
        t -= ts;
        start_end_derivatives.push_back(gl_traj.evaluateVel(0));
        start_end_derivatives.push_back(local_target_vel);
        start_end_derivatives.push_back(gl_traj.evaluateAcc(0));
        start_end_derivatives.push_back(gl_traj.evaluateAcc(t));
      }
      else // Initial path generated from previous trajectory.
      {

        double t;
        double t_cur = (ros::Time::now() - local_data_.start_time_).toSec();

        vector<double> pseudo_arc_length;
        vector<Eigen::Vector3d> segment_point;
        pseudo_arc_length.push_back(0.0);
        // 2026-11-15（P2 根因修复）：只取上一条轨迹的前 seed_horizon_ 秒做种子。
        // 不这样做的话整条回环尾巴（14-19 s）被继承，飞机 0.5 s 只走 0.1 m，
        // 返回段永远到不了（11-14 bag1 绕到 y=1.33 的直接机制）。
        const double t_seed_end = std::min(local_data_.duration_, t_cur + pp_.seed_horizon_);
        for (t = t_cur; t < t_seed_end + 1e-3; t += ts)
        {
          segment_point.push_back(local_data_.position_traj_.evaluateDeBoorT(t));
          if (t > t_cur)
          {
            pseudo_arc_length.push_back((segment_point.back() - segment_point[segment_point.size() - 2]).norm() + pseudo_arc_length.back());
          }
        }
        if (segment_point.empty())
        {
          // 2026-11-15（P2）：轨迹已走完（t_cur >= duration_）时尾巴为空；不能对空
          // vector 取 back()。直接改用全新多项式分支（flag_regenerate 回到循环头）。
          flag_force_polynomial = true;
          flag_regenerate = true;
          continue;
        }
        t -= ts;

        // 2026-11-15（P2）：尾段后面的多项式时长改用上游"距离/最大速度 + 2*v/a"
        // （与全新目标同一公式），不再 *2；否则 2 m 缺口给 8 s，种子仍偏长。
        const double poly_dist = (local_data_.position_traj_.evaluateDeBoorT(t) - local_target_pt).norm();
        double poly_time = poly_dist / pp_.max_vel_ + 2.0 * pp_.max_vel_ / pp_.max_acc_;
        if (poly_time > ts)
        {
          PolynomialTraj gl_traj = PolynomialTraj::one_segment_traj_gen(local_data_.position_traj_.evaluateDeBoorT(t),
                                                                        local_data_.velocity_traj_.evaluateDeBoorT(t),
                                                                        local_data_.acceleration_traj_.evaluateDeBoorT(t),
                                                                        local_target_pt, local_target_vel, Eigen::Vector3d::Zero(), poly_time);

          for (t = ts; t < poly_time; t += ts)
          {
            if (!pseudo_arc_length.empty())
            {
              segment_point.push_back(gl_traj.evaluate(t));
              pseudo_arc_length.push_back((segment_point.back() - segment_point[segment_point.size() - 2]).norm() + pseudo_arc_length.back());
            }
            else
            {
              ROS_ERROR("pseudo_arc_length is empty, return!");
              continous_failures_count_++;
              return false;
            }
          }
        }

        // 2026-11-15（P2 自检抓到的坑）：截短后的种子可能几乎是原地（弧长≈0），
        // 下面的 do/while 会因插值区间为 0 而永远凑不满 7 个点 -> 规划器死循环。
        // 零弧长直接改用全新多项式；并给 cps_dist 细分加硬上限，双保险。
        if (pseudo_arc_length.back() < 1e-3)
        {
          flag_force_polynomial = true;
          flag_regenerate = true;
          continue;
        }

        double sample_length = 0;
        double cps_dist = pp_.ctrl_pt_dist * 1.5; // cps_dist will be divided by 1.5 in the next
        size_t id = 0;
        int cps_guard = 0;
        do
        {
          cps_dist /= 1.5;
          point_set.clear();
          sample_length = 0;
          id = 0;
          while ((id <= pseudo_arc_length.size() - 2) && sample_length <= pseudo_arc_length.back())
          {
            if (sample_length >= pseudo_arc_length[id] && sample_length < pseudo_arc_length[id + 1])
            {
              point_set.push_back((sample_length - pseudo_arc_length[id]) / (pseudo_arc_length[id + 1] - pseudo_arc_length[id]) * segment_point[id + 1] +
                                  (pseudo_arc_length[id + 1] - sample_length) / (pseudo_arc_length[id + 1] - pseudo_arc_length[id]) * segment_point[id]);
              sample_length += cps_dist;
            }
            else
              id++;
          }
          point_set.push_back(local_target_pt);
        } while (point_set.size() < 7 && ++cps_guard < 25); // If the start point is very close to end point, this will help
        if (point_set.size() < 5)
        {
          // 细分 25 次仍然凑不满 4 个点：种子退化，直接换全新多项式
          flag_force_polynomial = true;
          flag_regenerate = true;
          continue;
        }

        start_end_derivatives.push_back(local_data_.velocity_traj_.evaluateDeBoorT(t_cur));
        start_end_derivatives.push_back(local_target_vel);
        start_end_derivatives.push_back(local_data_.acceleration_traj_.evaluateDeBoorT(t_cur));
        start_end_derivatives.push_back(Eigen::Vector3d::Zero());

        if (point_set.size() > pp_.planning_horizen_ / pp_.ctrl_pt_dist * 3) // The initial path is unnormally too long!
        {
          flag_force_polynomial = true;
          flag_regenerate = true;
        }
      }
    } while (flag_regenerate);

    /* 2026-11-13 v2（深层根因）：A* 路径的第一个采样点是栅格中心（0.15 m 量化），
       且 start_end_derivatives 取的是"上一条轨迹"在 t_cur 的速度/加速度，不是实测机身。
       回放实测起点偏移 p50 0.16 / max 0.57 m、起点速度差 p95 0.13 m/s 都源于此。
       这里把 B 样条第一个采样点改成 FSM 传入的实测 start_pt，起点导数改成实测
       start_vel/start_acc —— 新轨迹从飞机当前位置/速度起步，而不是从栅格中心/旧轨迹起步。 */
    if (!point_set.empty())
      point_set[0] = start_pt;
    if (start_end_derivatives.size() >= 3)
    {
      start_end_derivatives[0] = start_vel;
      start_end_derivatives[2] = start_acc;
    }

    Eigen::MatrixXd ctrl_pts, ctrl_pts_temp;
    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);

    vector<std::pair<int, int>> segments;
    segments = bspline_optimizer_->initControlPoints(ctrl_pts, true);

    t_init = ros::Time::now() - t_start;
    t_start = ros::Time::now();

    /*** STEP 2: OPTIMIZE ***/
    bool flag_step_1_success = false;
    vector<vector<Eigen::Vector3d>> vis_trajs;

    if (pp_.use_distinctive_trajs)
    {
      // cout << "enter" << endl;
      std::vector<ControlPoints> trajs = bspline_optimizer_->distinctiveTrajs(segments);
      cout << "\033[1;33m"
           << "multi-trajs=" << trajs.size() << "\033[1;0m" << endl;

      double final_cost, min_cost = 999999.0;
      for (int i = trajs.size() - 1; i >= 0; i--)
      {
        if (bspline_optimizer_->BsplineOptimizeTrajRebound(ctrl_pts_temp, final_cost, trajs[i], ts))
        {

          cout << "traj " << trajs.size() - i << " success." << endl;

          flag_step_1_success = true;
          if (final_cost < min_cost)
          {
            min_cost = final_cost;
            ctrl_pts = ctrl_pts_temp;
          }

          // visualization
          point_set.clear();
          for (int j = 0; j < ctrl_pts_temp.cols(); j++)
          {
            point_set.push_back(ctrl_pts_temp.col(j));
          }
          vis_trajs.push_back(point_set);
        }
        else
        {
          cout << "traj " << trajs.size() - i << " failed." << endl;
        }
      }

      t_opt = ros::Time::now() - t_start;

      visualization_->displayMultiInitPathList(vis_trajs, 0.2); // This visuallization will take up several milliseconds.
    }
    else
    {
      flag_step_1_success = bspline_optimizer_->BsplineOptimizeTrajRebound(ctrl_pts, ts);
      t_opt = ros::Time::now() - t_start;
      //static int vis_id = 0;
      visualization_->displayInitPathList(point_set, 0.2, 0);
    }

    cout << "plan_success=" << flag_step_1_success << endl;
    if (!flag_step_1_success)
    {
      visualization_->displayOptimalList(ctrl_pts, 0);
      continous_failures_count_++;
      return false;
    }

    t_start = ros::Time::now();

    UniformBspline pos = UniformBspline(ctrl_pts, 3, ts);
    pos.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);

    /*** STEP 3: REFINE(RE-ALLOCATE TIME) IF NECESSARY ***/
    // Note: Only adjust time in single drone mode. But we still allow drone_0 to adjust its time profile.
    if (pp_.drone_id <= 0)
    {

      /* 2026-11-13 v2：step-2 的 refine 只调用一次，保留有限 ratio 的重定时；
         ratio=inf/NaN（起点贴障/优化器退化）时 lengthenTime(inf)->NaN，必须跳过，
         交给下面 P5 有界均匀拉伸/拒发。P5 自身的 refine 已删除（迭代复合才是 10-85s 爆炸源）。 */
      double ratio;
      bool flag_step_2_success = true;
      if (!pos.checkFeasibility(ratio, false))
      {
        if (std::isfinite(ratio) && ratio > 0.0 && ratio <= 10.0)
        {
          Eigen::MatrixXd optimal_control_points;
          flag_step_2_success = refineTrajAlgo(pos, start_end_derivatives, ratio, ts, optimal_control_points);
          if (flag_step_2_success)
            pos = UniformBspline(optimal_control_points, 3, ts);
        }
        else
        {
          ROS_ERROR("[refine] step-2 ratio=%.3f non-finite/extreme -> skip refine (P5 bounded will handle)", ratio);
        }
      }
      if (!flag_step_2_success)
      {
        continous_failures_count_++;
        return false;
      }
    }
    else
    {
      static bool print_once = true;
      if (print_once)
      {
        print_once = false;
        ROS_ERROR("IN SWARM MODE, REFINE DISABLED!");
      }
    }

    t_refine = ros::Time::now() - t_start;


    /* 2026-11-12 P2+P5：末端零速化 + 无条件限速（用户批准的方案，不加门）
       P2：优化器不约束末端导数（末端速度 ∝ P_n − P_{n-1}）。
            追加一个与 P_n 相同的控制点 → 末端速度 = 0。
            实测 bag 000019 每条轨迹末端 0.05–0.34 m/s，到点全靠位置环刹。
       P5：refine 的重参数化只是近似（多项式拟合），可能仍超限。
            实测 bag 001036 参考速度 0.597 m/s（限 0.4，refine 后仍超 49%）。
            修法：同一路径拉伸时间轴（速度 ∝ 1/interval），迭代直到可行。 */
    {
      // P2: 末端零速化（带膨胀约束的追加）
      Eigen::MatrixXd cps_base = pos.getControlPoint();
      int n_cp = cps_base.cols();
      if (n_cp >= 2)
      {
        const double t_old = pos.getTimeSum();
        const double dt_int = pos.getInterval();
        Eigen::Vector3d v_end_p2 = pos.getDerivative().evaluateDeBoorT(t_old);
        if (v_end_p2.norm() > 0.03)
        {
          /* 实测（/tmp/test_p2k）：cubic 追加 1 个副本只把末端速度减半，追加 2 个（order-1）才归零。
             2026-11-12 质量修复 A：追加段是优化后的后处理，必须检查它不进入膨胀层；
             撞了就退化为 1 个副本（减半），再撞就不追加（保留残余速度），绝不硬塞。 */
          /* 2026-11-12 质量修复 A（实测 /tmp/test_p2end）：
             追加"最后控制点副本"会把终点向前推（1.2 -> 1.35），且膨胀检查常常因此失败。
             正确做法：把最后一个控制点**改为样条原终点 pe**，再追加 2 个 pe。
             实测：end=pe 精确不变、|v_end|=0、尾段最大 x 不超过 pe（无前冲）。
             膨胀检查只看尾段**内部**（排除终点自身：终点是规划器已接受的自由点）。 */
          const Eigen::Vector3d p_end_p2 = pos.evaluateDeBoorT(t_old);
          const bool end_inflated = grid_map_->getInflateOccupancy(p_end_p2) > 0;
          UniformBspline orig_pos = pos;
          auto try_dup = [&](int k, UniformBspline &out) -> bool {
            Eigen::MatrixXd c = cps_base;
            c.col(n_cp - 1) = p_end_p2;   // 关键：终点不前进（实测 1.2 -> 1.2，尾部无前冲）
            c.conservativeResize(Eigen::NoChange, n_cp + k);
            for (int i = 0; i < k; ++i)
              c.col(n_cp + i) = p_end_p2;
            UniformBspline cand(c, 3, dt_int);
            const double t_new = cand.getTimeSum();
            /* 只拒绝"新增"侵入：同一 t 上，改后进了膨胀格而原轨迹没进 -> 拒绝。
               原来已贴着膨胀层的采样点不算（终点本身就在自由边界上）。 */
            const double step = std::max(0.02, dt_int * 0.1);
            for (double tt = std::max(0.0, t_old - dt_int); tt < t_old; tt += step)
            {
              const int o = grid_map_->getInflateOccupancy(orig_pos.evaluateDeBoorT(tt));
              const int m = grid_map_->getInflateOccupancy(cand.evaluateDeBoorT(tt));
              if (m > 0 && o <= 0)
                return false;
            }
            /* 尾段：终点自由时才要求尾段自由；终点本身贴层时，尾段最大前冲=终点，
               不增加峰值侵入（实测 max_x_tail=pe）。 */
            if (!end_inflated)
            {
              for (double tt = t_old + 1e-6; tt < t_new - 1e-9; tt += step)
                if (grid_map_->getInflateOccupancy(cand.evaluateDeBoorT(tt)) > 0)
                  return false;
            }
            out = cand;
            return true;
          };
          UniformBspline cand;
          int used = -1;
          const int tries[3] = {2, 1, 0};
          for (int k = 0; k < 3; ++k)
            if (try_dup(tries[k], cand)) { used = tries[k]; break; }
          if (used >= 0)
          {
            pos = cand;
            if (used < 2)
              ROS_WARN_THROTTLE(2.0, "[P2] brake extension reduced to %d CP (inflation)", used);
            else
              ROS_INFO_THROTTLE(2.0, "[P2] end velocity %.3f -> 0 (2 CP appended)", v_end_p2.norm());
          }
          else
          {
            ROS_WARN_THROTTLE(2.0, "[P2] brake extension blocked by inflation; residual %.3f m/s kept",
                              v_end_p2.norm());
          }
        }
      }
      // P5: 无条件限速（2026-11-13 v2：去掉 refineTrajAlgo，只做有界均匀拉伸）
      for (int iter_p5 = 0; iter_p5 < 2; ++iter_p5)
      {
        pos.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
        double ratio_p5;
        if (pos.checkFeasibility(ratio_p5, false))
          break;
        /* refineTrajAlgo 会改控制点数量/时间基：实测把 interval 从 4 s 拉到 10-85 s、
           总时长到 593 s。这里只做有界均匀拉伸：每轮 ≤2×，最多 2 轮（总 ≤4×）。
           仍不可行 -> 拒绝本次轨迹（不发布超长/高加速度轨迹）。 */
        const double step = std::min(2.0, std::max(1.0, ratio_p5));
        if (step <= 1.0001)
          break;
        const double old_int = pos.getInterval();
        Eigen::MatrixXd cp_p5 = pos.getControlPoint();
        pos = UniformBspline(cp_p5, 3, old_int * step);
        ROS_WARN_THROTTLE(2.0, "[P5] uniform stretch (ratio %.2f): interval %.3f -> %.3f",
                          ratio_p5, old_int, pos.getInterval());
      }
      {
        double r_final;
        if (!pos.checkFeasibility(r_final, false))
        {
          ROS_ERROR("[P5] still infeasible after bounded stretch (ratio=%.2f), reject trajectory", r_final);
          return false;
        }
      }
    }

    // save planned results
    updateTrajInfo(pos, ros::Time::now());

    static double sum_time = 0;
    static int count_success = 0;
    sum_time += (t_init + t_opt + t_refine).toSec();
    count_success++;
    cout << "total time:\033[42m" << (t_init + t_opt + t_refine).toSec() << "\033[0m,optimize:" << (t_init + t_opt).toSec() << ",refine:" << t_refine.toSec() << ",avg_time=" << sum_time / count_success << endl;

    // success. YoY
    continous_failures_count_ = 0;
    return true;
  }

  bool EGOPlannerManager::EmergencyStop(Eigen::Vector3d stop_pos)
  {
    Eigen::MatrixXd control_points(3, 6);
    for (int i = 0; i < 6; i++)
    {
      control_points.col(i) = stop_pos;
    }

    updateTrajInfo(UniformBspline(control_points, 3, 1.0), ros::Time::now());

    return true;
  }

  bool EGOPlannerManager::checkCollision(int drone_id)
  {
    if (local_data_.start_time_.toSec() < 1e9) // It means my first planning has not started
      return false;

    double my_traj_start_time = local_data_.start_time_.toSec();
    double other_traj_start_time = swarm_trajs_buf_[drone_id].start_time_.toSec();

    double t_start = max(my_traj_start_time, other_traj_start_time);
    double t_end = min(my_traj_start_time + local_data_.duration_ * 2 / 3, other_traj_start_time + swarm_trajs_buf_[drone_id].duration_);

    for (double t = t_start; t < t_end; t += 0.03)
    {
      if ((local_data_.position_traj_.evaluateDeBoorT(t - my_traj_start_time) - swarm_trajs_buf_[drone_id].position_traj_.evaluateDeBoorT(t - other_traj_start_time)).norm() < bspline_optimizer_->getSwarmClearance())
      {
        return true;
      }
    }

    return false;
  }

  bool EGOPlannerManager::planGlobalTrajWaypoints(const Eigen::Vector3d &start_pos, const Eigen::Vector3d &start_vel, const Eigen::Vector3d &start_acc,
                                                  const std::vector<Eigen::Vector3d> &waypoints, const Eigen::Vector3d &end_vel, const Eigen::Vector3d &end_acc)
  {

    // generate global reference trajectory

    vector<Eigen::Vector3d> points;
    points.push_back(start_pos);

    for (size_t wp_i = 0; wp_i < waypoints.size(); wp_i++)
    {
      points.push_back(waypoints[wp_i]);
    }

    double total_len = 0;
    total_len += (start_pos - waypoints[0]).norm();
    for (size_t i = 0; i < waypoints.size() - 1; i++)
    {
      total_len += (waypoints[i + 1] - waypoints[i]).norm();
    }

    // insert intermediate points if too far
    vector<Eigen::Vector3d> inter_points;
    double dist_thresh = max(total_len / 8, 4.0);

    for (size_t i = 0; i < points.size() - 1; ++i)
    {
      inter_points.push_back(points.at(i));
      double dist = (points.at(i + 1) - points.at(i)).norm();

      if (dist > dist_thresh)
      {
        int id_num = floor(dist / dist_thresh) + 1;

        for (int j = 1; j < id_num; ++j)
        {
          Eigen::Vector3d inter_pt =
              points.at(i) * (1.0 - double(j) / id_num) + points.at(i + 1) * double(j) / id_num;
          inter_points.push_back(inter_pt);
        }
      }
    }

    inter_points.push_back(points.back());

    // for ( int i=0; i<inter_points.size(); i++ )
    // {
    //   cout << inter_points[i].transpose() << endl;
    // }

    // write position matrix
    int pt_num = inter_points.size();
    Eigen::MatrixXd pos(3, pt_num);
    for (int i = 0; i < pt_num; ++i)
      pos.col(i) = inter_points[i];

    Eigen::Vector3d zero(0, 0, 0);
    Eigen::VectorXd time(pt_num - 1);
    for (int i = 0; i < pt_num - 1; ++i)
    {
      time(i) = (pos.col(i + 1) - pos.col(i)).norm() / (pp_.max_vel_);
    }

    time(0) *= 2.0;
    time(time.rows() - 1) *= 2.0;

    PolynomialTraj gl_traj;
    if (pos.cols() >= 3)
      gl_traj = PolynomialTraj::minSnapTraj(pos, start_vel, end_vel, start_acc, end_acc, time);
    else if (pos.cols() == 2)
      gl_traj = PolynomialTraj::one_segment_traj_gen(start_pos, start_vel, start_acc, pos.col(1), end_vel, end_acc, time(0));
    else
      return false;

    auto time_now = ros::Time::now();
    global_data_.setGlobalTraj(gl_traj, time_now);

    return true;
  }

  bool EGOPlannerManager::planGlobalTraj(const Eigen::Vector3d &start_pos, const Eigen::Vector3d &start_vel, const Eigen::Vector3d &start_acc,
                                         const Eigen::Vector3d &end_pos, const Eigen::Vector3d &end_vel, const Eigen::Vector3d &end_acc)
  {

    // generate global reference trajectory

    vector<Eigen::Vector3d> points;
    points.push_back(start_pos);
    points.push_back(end_pos);

    // insert intermediate points if too far
    vector<Eigen::Vector3d> inter_points;
    const double dist_thresh = 4.0;

    for (size_t i = 0; i < points.size() - 1; ++i)
    {
      inter_points.push_back(points.at(i));
      double dist = (points.at(i + 1) - points.at(i)).norm();

      if (dist > dist_thresh)
      {
        int id_num = floor(dist / dist_thresh) + 1;

        for (int j = 1; j < id_num; ++j)
        {
          Eigen::Vector3d inter_pt =
              points.at(i) * (1.0 - double(j) / id_num) + points.at(i + 1) * double(j) / id_num;
          inter_points.push_back(inter_pt);
        }
      }
    }

    inter_points.push_back(points.back());

    // write position matrix
    int pt_num = inter_points.size();
    Eigen::MatrixXd pos(3, pt_num);
    for (int i = 0; i < pt_num; ++i)
      pos.col(i) = inter_points[i];

    Eigen::Vector3d zero(0, 0, 0);
    Eigen::VectorXd time(pt_num - 1);
    for (int i = 0; i < pt_num - 1; ++i)
    {
      time(i) = (pos.col(i + 1) - pos.col(i)).norm() / (pp_.max_vel_);
    }

    time(0) *= 2.0;
    time(time.rows() - 1) *= 2.0;

    PolynomialTraj gl_traj;
    if (pos.cols() >= 3)
      gl_traj = PolynomialTraj::minSnapTraj(pos, start_vel, end_vel, start_acc, end_acc, time);
    else if (pos.cols() == 2)
      gl_traj = PolynomialTraj::one_segment_traj_gen(start_pos, start_vel, start_acc, end_pos, end_vel, end_acc, time(0));
    else
      return false;

    auto time_now = ros::Time::now();
    global_data_.setGlobalTraj(gl_traj, time_now);

    return true;
  }

  bool EGOPlannerManager::refineTrajAlgo(UniformBspline &traj, vector<Eigen::Vector3d> &start_end_derivative, double ratio, double &ts, Eigen::MatrixXd &optimal_control_points)
  {
    double t_inc;

    Eigen::MatrixXd ctrl_pts; // = traj.getControlPoint()

    // std::cout << "ratio: " << ratio << std::endl;
    reparamBspline(traj, start_end_derivative, ratio, ctrl_pts, ts, t_inc);

    traj = UniformBspline(ctrl_pts, 3, ts);

    double t_step = traj.getTimeSum() / (ctrl_pts.cols() - 3);
    bspline_optimizer_->ref_pts_.clear();
    for (double t = 0; t < traj.getTimeSum() + 1e-4; t += t_step)
      bspline_optimizer_->ref_pts_.push_back(traj.evaluateDeBoorT(t));

    bool success = bspline_optimizer_->BsplineOptimizeTrajRefine(ctrl_pts, ts, optimal_control_points);

    return success;
  }

  void EGOPlannerManager::updateTrajInfo(const UniformBspline &position_traj, const ros::Time time_now)
  {
    local_data_.start_time_ = time_now;
    local_data_.position_traj_ = position_traj;
    local_data_.velocity_traj_ = local_data_.position_traj_.getDerivative();
    local_data_.acceleration_traj_ = local_data_.velocity_traj_.getDerivative();
    local_data_.start_pos_ = local_data_.position_traj_.evaluateDeBoorT(0.0);
    local_data_.duration_ = local_data_.position_traj_.getTimeSum();
    local_data_.traj_id_ += 1;
  }

  void EGOPlannerManager::reparamBspline(UniformBspline &bspline, vector<Eigen::Vector3d> &start_end_derivative, double ratio,
                                         Eigen::MatrixXd &ctrl_pts, double &dt, double &time_inc)
  {
    double time_origin = bspline.getTimeSum();
    int seg_num = bspline.getControlPoint().cols() - 3;
    // double length = bspline.getLength(0.1);
    // int seg_num = ceil(length / pp_.ctrl_pt_dist);

    bspline.lengthenTime(ratio);
    double duration = bspline.getTimeSum();
    dt = duration / double(seg_num);
    time_inc = duration - time_origin;

    vector<Eigen::Vector3d> point_set;
    for (double time = 0.0; time <= duration + 1e-4; time += dt)
    {
      point_set.push_back(bspline.evaluateDeBoorT(time));
    }
    UniformBspline::parameterizeToBspline(dt, point_set, start_end_derivative, ctrl_pts);
  }

} // namespace ego_planner
