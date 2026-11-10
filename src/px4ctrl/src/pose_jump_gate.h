#ifndef __PX4CTRL_POSE_JUMP_GATE_H
#define __PX4CTRL_POSE_JUMP_GATE_H
/*******************************************************
 * pose_jump_gate.h — VINS camera_pose 跳变判据（纯函数，无 ROS 依赖）
 *
 * 【职责】给 PX4CtrlFSM::vinsPoseFeed 提供"这一帧位置跳变是否物理不可能"的判定
 * 【单位】p 为世界系位置 [m]，dt 为**同一时钟域**的两帧消息时间戳差 [s]
 * 【调用方】PX4CtrlFSM::vinsPoseFeed()、test/test_pose_jump.cpp
 * 【不负责】断流判定（那用到达墙钟差，见 vinsPoseFeed 的 gap 分支）
 *
 * 背景（2026-11-10 整改 N-02）：新加的 VINS guard 里，dt 是用
 *   `msg->header.stamp - vins_pose_stamp_`
 * 算的，而 `vins_pose_stamp_` 存的是**到达墙钟**。混域相减在本工程所有链路里都 ≤0
 * （墙钟 ≥ 消息戳），于是 `dt > 1e-3` 恒假 —— "位置跳变 >3 m/s" 这一面**从上线起
 * 从未生效**，只有"断流 0.4 s"一面在跑。现把消息戳与墙钟分开存，并把判据抽成
 * 纯函数，让 gtest 能锚定"dt 异常必须显式上报，不许静默跳过"。
 *******************************************************/
#include <Eigen/Dense>
#include <cmath>

namespace px4ctrl_gate
{

struct PoseJumpCfg
{
  double min_dt = 1e-3;          // [s] 小于此值视为时间戳异常（含 dt<=0 / 非有限）
  double max_implied_mps = 3.0;  // [m/s] 帧间隐含速度上限（多旋翼物理不可能值）
};

struct PoseJumpOut
{
  bool bad = false;            // 判为跳变（应触发 guard）
  bool stamp_anomaly = false;  // dt 不可用（<=min_dt / 非有限）——调用方必须记录，不许静默
  bool non_finite = false;     // 位置含 NaN/Inf
  double dt = 0.0;             // 实际使用的 dt
  double v_implied = 0.0;      // 帧间隐含速度 [m/s]
};

/* 单帧跳变判定。p_prev/p_now 必须同坐标系；dt 必须来自同一时钟域。 */
inline PoseJumpOut poseJumpCheck(const Eigen::Vector3d &p_prev, const Eigen::Vector3d &p_now,
                                 double dt, const PoseJumpCfg &cfg = PoseJumpCfg())
{
  PoseJumpOut o;
  o.dt = dt;
  if (!p_prev.allFinite() || !p_now.allFinite())
  {
    o.non_finite = true;
    o.bad = true;  // 含 NaN 的位置绝不能进控制
    return o;
  }
  if (!std::isfinite(dt) || dt < cfg.min_dt)
  {
    // 时间戳回退/停住/跨域 —— 判据不可用。调用方要计数并限频告警，
    // 否则"换个时钟域"又会静默失效一次。
    o.stamp_anomaly = true;
    return o;
  }
  o.v_implied = (p_now - p_prev).norm() / dt;
  o.bad = o.v_implied > cfg.max_implied_mps;
  return o;
}

}  // namespace px4ctrl_gate

#endif  // __PX4CTRL_POSE_JUMP_GATE_H
