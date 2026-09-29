#ifndef __ODOM_SANITY_V2_H
#define __ODOM_SANITY_V2_H

#include <Eigen/Dense>
#include <cmath>
#include <limits>

/*******************************************************
 * T3-Z1.2 (2026-09-30): odom value-sanity gate v2 —— 设计稿(未接线)
 *
 * 在 T1-D2 三层门(vel/acc/jump,odom_sanity.h,WD1b 实战)之上,按
 * plans/directions/C07_odom-poison-failsafe-paradigm/DOSSIER.md 方向 2/3 增补:
 *   ④ R 层:运动学残差 r_k = ‖P_k − P_{k−1} − ½(V_{k−1}+V_k)Δt‖
 *      健康流梯形恒等式钉零基线(C07-03 D3);阈值=Y1.4 r 扫描当前层
 *      p999×3(223Hz imu_propagate 流 0.025×3≈0.075→取 0.08,C07 带[0.02,0.1])
 *      已知盲区(2026-09-30 Z1.1+Y1.4 实证):速度爬坡型运动学自洽漂移
 *      r≡0(105449 轮 r 中位 0/p99 1.15)——VEL 层是该形态唯一防线,
 *      r 层防的是离散阶跃与不协调跳变(0.5m 干净阶跃 K4 缺口)。
 *   ⑤ STAMP 层:双判据——戳龄(age>τ_max 拒)+严格单调(回退拒)
 *      陈旧突发形态(值域门逻辑不可见,C07-03 D6)的唯一防线;
 *      单调违反=滤波状态污染(PX4 同构,C07-02 S17)。
 * 接线纪律:本头为设计稿+gtest 对象;接入 px4ctrl_node 走 STATUS 异议窗
 * +配对提交(T3 v7.2:124)。默认 enabled_v2=false = v1 行为逐位不变。
 *******************************************************/

struct OdomSanityConfigV2
{
  // ---- v1(D2 三层,阈值沿用 odom_sanity.h 实战值)----
  bool enabled = false;
  double max_vel = 5.0;    // m/s
  double max_acc = 10.0;   // m/s^2(帧间差分型;223Hz 噪声上界见 H12 重标注)
  double max_jump = 0.6;   // m(T1-D4 反哺收紧值)
  double reboot_dt = 1.0;  // s
  int warn_every = 50;
  // ---- v2 增补(Z1.2)----
  bool enabled_v2 = false;         // v2 总开关(false=纯 v1 行为)
  double max_r = 0.08;             // m,运动学残差门(当前层 p999×3)
  double stamp_age_max = 0.2;      // s,戳龄门(健康链路 max gap 20ms×10 裕度;
                                   //  外锚 PX4 EV_MAX_INTERVAL=0.2s 量级,C07-02 S14)
  bool stamp_monotonic = true;     // 时戳回退拒(污染轮 hdr 回退 16135 帧实证)
};

enum class OdomSanityVerdictV2
{
  ACCEPT = 0,
  REJECT_VEL = 1,
  REJECT_ACC = 2,
  REJECT_JUMP = 3,
  REJECT_NAN = 4,
  REJECT_R = 5,        // v2:运动学残差
  REJECT_STAMP_AGE = 6, // v2:戳龄
  REJECT_STAMP_BACK = 7 // v2:时戳回退
};

struct OdomSanityStateV2
{
  bool has_ref = false;
  Eigen::Vector3d last_p = Eigen::Vector3d::Zero();
  Eigen::Vector3d last_v = Eigen::Vector3d::Zero();
  double last_t = 0.0;
  double last_stamp = 0.0;   // header.stamp 链(单调判据用;与 last_t 局部钟分离)
  long accepted = 0;
  long rejected = 0;
  long rejected_r = 0;
  long rejected_stamp = 0;
};

inline OdomSanityVerdictV2 odom_sanity_check_v2(const OdomSanityConfigV2 &cfg,
                                                OdomSanityStateV2 &st,
                                                double stamp,     // header.stamp 秒
                                                double t_now,     // 本地到达钟(戳龄分母)
                                                const Eigen::Vector3d &p,
                                                const Eigen::Vector3d &v)
{
  if (!cfg.enabled)
    return OdomSanityVerdictV2::ACCEPT;

  // NaN/Inf 防护(v1 语义)
  if (!p.allFinite() || !v.allFinite())
    return OdomSanityVerdictV2::REJECT_NAN;

  // ---- v2 STAMP 层(在值域层之前:陈旧/回退帧无论取值如何都拒)----
  if (cfg.enabled_v2)
  {
    if (cfg.stamp_monotonic && st.has_ref && stamp < st.last_stamp - 1e-9)
    {
      st.rejected++; st.rejected_stamp++;
      return OdomSanityVerdictV2::REJECT_STAMP_BACK;
    }
    if (t_now > 0.0 && stamp > 0.0 && (t_now - stamp) > cfg.stamp_age_max)
    {
      st.rejected++; st.rejected_stamp++;
      return OdomSanityVerdictV2::REJECT_STAMP_AGE;
    }
  }

  if (!st.has_ref)
  {
    st.has_ref = true;
    st.last_p = p; st.last_v = v; st.last_t = t_now; st.last_stamp = stamp;
    st.accepted++;
    return OdomSanityVerdictV2::ACCEPT;
  }

  const double dt = t_now - st.last_t;
  const bool reboot_gap = dt >= cfg.reboot_dt;

  // ---- v1 三层(顺序=WD1b 实战次序:ACC→JUMP→VEL)----
  if (!reboot_gap)
  {
    const Eigen::Vector3d dv = v - st.last_v;
    if (dv.norm() / dt > cfg.max_acc)
    {
      st.rejected++;
      return OdomSanityVerdictV2::REJECT_ACC;
    }
    if ((p - st.last_p).norm() > cfg.max_jump)
    {
      st.rejected++;
      return OdomSanityVerdictV2::REJECT_JUMP;
    }
    // ---- v2 R 层(协调性:位置增量与速度梯形积分的一致性)----
    if (cfg.enabled_v2)
    {
      const Eigen::Vector3d pred = st.last_p + 0.5 * (st.last_v + v) * dt;
      const double r = (p - pred).norm();
      if (r > cfg.max_r)
      {
        st.rejected++; st.rejected_r++;
        return OdomSanityVerdictV2::REJECT_R;
      }
    }
  }
  if (v.norm() > cfg.max_vel)
  {
    st.rejected++;
    return OdomSanityVerdictV2::REJECT_VEL;
  }

  st.last_p = p; st.last_v = v; st.last_t = t_now; st.last_stamp = stamp;
  st.accepted++;
  return OdomSanityVerdictV2::ACCEPT;
}

#endif  // __ODOM_SANITY_V2_H
