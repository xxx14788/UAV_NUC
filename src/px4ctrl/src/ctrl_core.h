#ifndef __PX4CTRL_CTRL_CORE_H
#define __PX4CTRL_CTRL_CORE_H
/*******************************************************
 * ctrl_core.h -- W4/W5/W6 的控制核心（纯函数，无 ROS 依赖）
 *
 * 设计原则（每条对应任务书条款）：
 *  1. 串级 + 积分（W4/W5）：位置 P → 速度 PI → 加速度；积分带限幅 + 条件积分抗饱和。
 *  2. 参考整形（W4 步骤5 / W6 步骤3）：jerk 限幅 + 加速度限幅；**切换点参考连续化**
 *     （handover 时把参考初始化为"切换瞬间的实际参考"，再由整形器推向目标，消除
 *     `fsm_decision.h` 记录的 +9.4 cm 位置阶跃）。
 *  3. 推力映射（W4/D4）：除以 cos(倾角)（照 PX4 `PositionControl.cpp:219-220`），
 *     并保留 `zb.z>=0.1g` 护栏语义（由调用方的 attitudeFromAccel 负责）。
 *  4. 模型无扰切换（W4/D3）：换 thr2acc 时平移积分，使当前拍的加速度指令不变
 *     （照 PX4 `PositionControl::updateHoverThrust`，`PositionControl.cpp:75-89`）。
 *  5. RLS 门控（W4/AMENDMENT-002 铁律）：空中门 + 激励门 + 存储点限幅 + P 保正。
 *  6. z_eq 定律（E9）：把"P-only + 冻结模型"的平衡高度写成函数，供单测锚定 S2。
 *  7. 降落（W6）：高度参考而非时间斜坡（VINS z 漂移不驱动参考穿地）+ 三段速度上限。
 *
 * 单位约定：**全部用"向上为正"**（与 px4ctrl 一致，与 PX4 NED 相反）。
 *******************************************************/
#include <cmath>
#include <algorithm>

namespace px4ctrl_core
{

// ============================================================================
// 接线状态（2026-11-06，必须与实际调用点一致；改代码请同步这张表）
//
// **已接线**（controller.cpp / PX4CtrlFSM.cpp 有真实调用）：
//   axisStep, thrustFromAcc, retargetThrustModel, kV2* 常量
// **未接线**（已单测覆盖，等下一阶段；不是死代码，是保留件）：
//   shapeRef / refSettled / takeoffRef / takeoffArrived  -> W6 起飞参考整形
//   landStep                                             -> W6 降落参考
//   slewTilt                                             -> 倾角斜率限幅
//   eqHeight / maxHoverableThrust                        -> 判读用解析式（E9 定律）
// 为什么保留：这三组是 W6 的内容，接线会改起飞/降落剖面，**必须在 v2 垂直环
// 飞验证之后单独一批做**；现在接等于两个变量一起动，出问题分不清是谁。
// ============================================================================

constexpr double G = 9.81;

// ============================================================================
// v2 增益与限幅：**锁死在这里，不暴露成 yaml 参数**（2026-11-06 砍旋钮）
// 理由：这些是 PX4 的参考值，没有"按机器调"的正当理由；把它们做成参数只会
//       制造 13 个没人标定过的旋钮。真正需要知道的只有 hover_percentage（电池属性）。
// 来源：PX4-Autopilot src/modules/mc_pos_control/PositionControl.cpp 及参数表。
// ============================================================================
constexpr double kV2Zp = 1.0;    // MPC_Z_P      位置环 P        [1/s]
constexpr double kV2Zv = 6.0;    // 速度环 P [1/s]  2026-11-06: 4.0->6.0
// 为什么偏离 PX4 的 4.0：PX4 的悬停油门是准的，不会激励垂直模态；我们有 5-10% 冷启
// 模型误差，正好把它踢起来。实测（20261106_222806）峰值 0.785、谷 0.656，摆幅 12.9cm。
// 仿真扫描（同一套数学，三轮实测 u_hover，aim=0.75/k=0.25）：
//   kp_v=4, ki=2 -> 峰 0.736 谷 0.659 摆幅 0.077   （当前）
//   kp_v=6, ki=3 -> 峰 0.706 谷 0.669 摆幅 0.037   （摆幅减半，ζ 仍 0.70）
//   kp_v=8, ki=3 -> 峰 0.708 谷 0.670 摆幅 0.038   （边际递减）
// 稳态不受影响（30s 误差 0.0000）。**注意**：仿真没有推力滞后，提带宽遇到未建模滞后
// 有振荡风险 -> 首飞必须盯"周期>5s 的摆动"这条中止条件。
constexpr double kV2Zi = 3.0;    // 速度环 I [1/s^2]  2026-11-06: 2.0->3.0（Ti=2.0s, ζ=0.70）
constexpr double kV2ZpXY = 0.55; // MPC_XY_P
constexpr double kV2ZvXY = 1.80; // MPC_XY_VEL_P
constexpr double kV2ZiXY = 0.40; // MPC_XY_VEL_I  -> Ti=4.5s
constexpr double kV2ZvelMax = 3.0;   // MPC_Z_VEL_MAX_UP/DN
constexpr double kV2XYvelMax = 12.0;
// 积分限幅：覆盖 hp∈[0.46,0.62] 的冷启偏差
//   I_need = u_hover*(G/hp) - G；hp=0.54 时 u=0.62 -> +1.46，u=0.46 -> -1.45
constexpr double kV2Zilim = 0.3 * G;    // 2.943，余量 2x
constexpr double kV2XYilim = 0.15 * G;  // 1.4715，吃 0.209 m/s^2 常值扰动绰绰有余
constexpr double kV2CosMin = 0.5;       // = cos(60deg)，1/cos 补偿护栏
constexpr double kV2DtMin = 0.002;      // 照 PX4 的 dt 钳位
constexpr double kV2DtMax = 0.040;
// 水平抗饱和的加速度上限 = g*tan(tilt)；倾角上限本身来自 takeoff_land/max_angle，
// 这里只限制"换算用的倾角不超过 60°"，避免 tan 发散。
constexpr double kV2AccLimTiltMaxDeg = 60.0;

// ---------------------------------------------------------------- 垂直/水平通用
struct AxisCfg
{
  double kp_p = 1.0;          // 位置 P [1/s]
  double kp_v = 4.0;          // 速度 P [1/s]
  double ki_v = 2.0;          // 速度 I [1/s^2 per (m/s)]
  double vel_max_up = 3.0;    // 速度指令上限（正方向）[m/s]
  double vel_max_dn = 3.0;    // 速度指令下限（负方向）[m/s]
  double i_lim = 0.3 * G;     // 积分限幅 [m/s^2]（任务书 W4 步骤2：±0.3g）
  double thr2acc = 0.0;       // u -> 加速度 斜率 [m/s^2 per unit u]
  // 0 = 未初始化。**故意不设默认值**：写死 G/0.48 会和 hover_percentage 脱钩
  // （2026-11-06 实测已不一致）。调用方必须先用 retargetThrustModel() 灌入真值；
  // 若仍是 0，axisStep 走"不出力"分支（安全方向），不会除零放大推力。
  double cos_tilt_min = 0.5;  // 1/cos 补偿的护栏（等效最大倾角 60°）
  double u_min = 0.0;         // 推力下限（怠速用 0.04 由调用方给）
  double u_max = 1.0;
  // 2026-11-06（顾问自审补）：该轴的**加速度指令上限** [m/s^2]，0=不限。
  // 为什么需要它：水平轴的执行器上限是**倾角**，不是推力。而 axisStep 的饱和判据
  // 用的是 u=(acc+g)/(k*ct)，对 x/y 来说 acc 只有几 m/s^2，u 恒在 [0,1] 内 ->
  // 水平积分**永不冻结**（抗饱和形同虚设），大步长机动后会积到 i_lim 再花 Ti 解开，
  // 表现为 ~1.5 m 的位置过冲。垂直轴保持只用 u 判（推力就是它的执行器）。
  double acc_lim = 0.0;
};

struct AxisMem
{
  double i = 0.0;             // 速度积分 [m/s^2]
};

struct AxisDebug
{
  double v_d = 0.0;           // 速度指令 [m/s]
  double e_p = 0.0;           // 位置误差 [m]
  double e_v = 0.0;           // 速度误差 [m/s]
  double acc = 0.0;           // 加速度指令（含前馈）[m/s^2]
  double u = 0.0;             // 推力指令 [0,1]
  double sat = 0.0;           // −1=下限饱和, 0=未饱和, +1=上限饱和
  double cos_comp = 1.0;      // 1/cos(倾角) 实际使用的补偿系数
};

/* 单轴串级一步。p_d/p/v 同一坐标系同一原点；v_d_ff/a_ff 为轨迹前馈；
   cos_tilt 为机体 z 轴与世界 z 轴夹角的余弦（倾角补偿）；dt 已由调用方钳位。
   物理：竖直加速度 = u·thr2acc·cos(tilt) − g，故 u = (acc_dyn + g)/(thr2acc·cos)。 */
inline AxisDebug axisStep(const AxisCfg &c, AxisMem &m,
                          double p_d, double p, double v_d_ff, double v,
                          double a_ff, double cos_tilt, double dt)
{
  AxisDebug d;
  // (1) 位置环 → 速度指令（带前馈与限速）
  d.e_p = p_d - p;
  double v_d_raw = v_d_ff + c.kp_p * d.e_p;
  d.v_d = std::max(-c.vel_max_dn, std::min(c.vel_max_up, v_d_raw));

  // (2) 速度误差
  d.e_v = d.v_d - v;

  // (3) 动态加速度指令（P + I + 前馈；**不含重力**）
  double acc = c.kp_v * d.e_v + m.i + a_ff;
  d.acc = acc;

  // (3.5) 模型未初始化 -> 不出力（安全方向）。绝不能让 thr2acc=0 走除法：
  //       那会得到 inf -> 被 clamp 到 u_max=1.0 = 满推力。
  if (!(c.thr2acc > 1.0))
  {
    d.u = 0.0;
    d.sat = -1.0;
    d.cos_comp = 1.0;
    return d;
  }
  // (4) 推力（含 1/cos 倾角补偿与限幅）
  double ct = std::max(cos_tilt, c.cos_tilt_min);
  d.cos_comp = 1.0 / ct;
  double u_raw = (acc + G) / (c.thr2acc * ct);
  double u = std::max(c.u_min, std::min(c.u_max, u_raw));
  d.sat = (u_raw > c.u_max) ? 1.0 : ((u_raw < c.u_min) ? -1.0 : 0.0);
  d.u = u;
  // 该轴另有加速度上限时（水平轴=倾角预算），并入饱和判据
  if (c.acc_lim > 0.0)
  {
    if (acc >= c.acc_lim)       d.sat = 1.0;
    else if (acc <= -c.acc_lim) d.sat = -1.0;
  }

  // (5) 条件积分抗饱和：饱和且误差指向饱和方向 → 本拍不积分
  bool frozen = (d.sat > 0.0 && d.e_v > 0.0) || (d.sat < 0.0 && d.e_v < 0.0);
  if (!frozen && dt > 0.0)
  {
    m.i += c.ki_v * d.e_v * dt;
    m.i = std::max(-c.i_lim, std::min(c.i_lim, m.i));
  }
  return d;
}

/* 推力：acc_up [m/s^2] → u，含 1/cos(倾角) 与 [u_min,u_max] 限幅。
   与 axisStep 内部同一公式，单独暴露便于 gtest 与 W6 直接用。 */
inline double thrustFromAcc(double acc_up, double thr2acc, double cos_tilt,
                           double u_min, double u_max, double cos_min = 0.5)
{
  double ct = std::max(cos_tilt, cos_min);
  double u = (acc_up + G) / (thr2acc * ct);
  return std::max(u_min, std::min(u_max, u));
}

/* 模型无扰切换（照 PX4 PositionControl::updateHoverThrust）：
   把 thr2acc 由 old 换到 neu 时平移积分，使"用当前 u 反算出的加速度"前后一致。 */
inline void retargetThrustModel(AxisCfg &c, AxisMem &m, double new_thr2acc,
                                double u_now, double cos_tilt, double cos_min = 0.5)
{
  if (new_thr2acc <= 0.0)
    return;
  // 由 u = (acc+G)/(k·ct) 反解：acc = u·k·ct − G
  // 要让"同一 u"不变，需 acc' − acc = u·ct·(k' − k)；ct=1 时退化为 PX4 原式（u·(k'−k)）
  double ct = std::max(cos_tilt, cos_min);
  double delta_acc = u_now * ct * (new_thr2acc - c.thr2acc);
  m.i += delta_acc;                                // 用积分吸收差值 → 下一拍 u 不变
  m.i = std::max(-c.i_lim, std::min(c.i_lim, m.i));
  c.thr2acc = new_thr2acc;
}

// ---------------------------------------------------------------- 参考整形
struct Ref
{
  double p, v, a;
  Ref() : p(0.0), v(0.0), a(0.0) {}
  Ref(double p_, double v_, double a_) : p(p_), v(v_), a(a_) {}
};

/* 二阶整形：把 ref 从 cur 推向 target，受 v_max / a_max / j_max 约束。
   性质（gtest 锚定）：
     - p 连续（每拍增量 <= v*dt + 0.5*a*dt^2），**不产生阶跃**；
     - 不越过 target（到顶即 v=target.v, a=0）；
     - cur==target 时原样返回（幂等）。 */
inline Ref shapeRef(const Ref &cur, const Ref &target,
                    double v_max, double a_max, double j_max, double dt)
{
  Ref r = cur;
  if (dt <= 0.0)
    return r;

  // 速度指令：P 型趋近（增益 1.0/s），带限速
  double v_des = target.v;
  double dp = target.p - cur.p;
  if (std::fabs(dp) > 1e-4)
    v_des = std::max(-v_max, std::min(v_max, 1.0 * dp)); // P 趋近，增益 1.0 /s
  // 接近目标时用目标速度，避免抖振
  if (std::fabs(dp) < 0.02 && std::fabs(target.v) < 1e-9)
    v_des = 0.0;

  // 加速度指令（受 a_max）
  double a_des = (v_des - cur.v) / std::max(dt, 1e-4);
  a_des = std::max(-a_max, std::min(a_max, a_des));
  // jerk 限幅
  double da = a_des - cur.a;
  double da_max = j_max * dt;
  da = std::max(-da_max, std::min(da_max, da));
  r.a = std::max(-a_max, std::min(a_max, cur.a + da));
  // 积分
  r.v = cur.v + r.a * dt;
  r.p = cur.p + cur.v * dt + 0.5 * r.a * dt * dt;

  // 防越位（单向）：若越过目标位置，钉死在目标
  if ((dp >= 0.0 && r.p > target.p) || (dp < 0.0 && r.p < target.p))
  {
    r.p = target.p;
    if ((target.v >= 0.0 && r.v > target.v) || (target.v < 0.0 && r.v < target.v))
    {
      r.v = target.v;
      r.a = 0.0;
    }
  }
  return r;
}

/* 悬停参考达标的判据（供 FSM 用）：位置误差与速度都进入带内。 */
inline bool refSettled(const Ref &r, const Ref &target, double p_tol, double v_tol)
{
  return std::fabs(r.p - target.p) <= p_tol && std::fabs(r.v - target.v) <= v_tol;
}

// ---------------------------------------------------------------- 起飞参考（W6）
struct TakeoffCfg
{
  double height = 0.5;     // 目标高度（地面起算）[m]
  double speed = 0.45;     // 爬升速度 [m/s]
  double acc = 1.0;        // 加速/减速度 [m/s^2]（沿用现网 a=1.0）
  double spinup = 3.0;     // 电机加速段 [s]（此间 des 保持在地面）
  double arrive_k = 0.208; // 预测到位系数 1/(2*Kv2) [s]
};

/* 起飞参考：返回 (p,v,a)（地面起算高度）。t 为 AUTO_TAKEOFF 已持续时间。
   末态**恰好** p=height, v=0（不再 aim=height+0.05，消除切换点阶跃的根因）。 */
inline Ref takeoffRef(double t, const TakeoffCfg &c)
{
  Ref r;
  if (t <= c.spinup)
  {
    r.p = 0.0; r.v = 0.0; r.a = 0.0;
    return r;
  }
  double tt = t - c.spinup;
  double t_acc = c.speed / c.acc;                    // 加速到 speed 的时间
  double d_acc = 0.5 * c.acc * t_acc * t_acc;        // 加速段位移
  double d_dec = d_acc;                              // 对称减速
  if (c.height <= 2.0 * d_acc)                       // 高太矮：三角剖面
  {
    double v_peak = std::sqrt(c.acc * c.height);
    double t_half = v_peak / c.acc;
    if (tt <= t_half)
    {
      r.p = 0.5 * c.acc * tt * tt; r.v = c.acc * tt; r.a = c.acc;
    }
    else if (tt <= 2.0 * t_half)
    {
      double s = tt - t_half;
      r.p = 0.5 * c.acc * t_half * t_half + v_peak * s - 0.5 * c.acc * s * s;
      r.v = v_peak - c.acc * s; r.a = -c.acc;
    }
    else
    {
      r.p = c.height; r.v = 0.0; r.a = 0.0;
    }
    return r;
  }
  // 梯形剖面
  double t_const = (c.height - d_acc - d_dec) / c.speed;
  if (tt <= t_acc)
  {
    r.p = 0.5 * c.acc * tt * tt; r.v = c.acc * tt; r.a = c.acc;
  }
  else if (tt <= t_acc + t_const)
  {
    double s = tt - t_acc;
    r.p = d_acc + c.speed * s; r.v = c.speed; r.a = 0.0;
  }
  else if (tt <= t_acc + t_const + t_acc)
  {
    double s = tt - t_acc - t_const;
    r.p = d_acc + c.speed * t_const + c.speed * s - 0.5 * c.acc * s * s;
    r.v = c.speed - c.acc * s; r.a = -c.acc;
  }
  else
  {
    r.p = c.height; r.v = 0.0; r.a = 0.0;
  }
  return r;
}

/* 预测到位判据（与 fsm_decision::decide_takeoff 的 J3 同式，抽出便于单测） */
inline bool takeoffArrived(const Ref &r, double vz_meas, const TakeoffCfg &c)
{
  double vz = vz_meas > 0.0 ? vz_meas : 0.0;
  if (r.p + c.arrive_k * vz >= c.height)
    return true;
  return r.p >= c.height + 0.10;
}

// ---------------------------------------------------------------- 积分/平衡高度定律
/* E9 的 z_eq 定律：P-only（无积分）+ 冻结模型时的稳态平衡高度。
   aim 为参考目标高度，u_hover 为真实悬停推力，thr2acc_est = G/hover_pct_cold。 */
inline double eqHeight(double aim, double u_hover, double thr2acc_est, double kp_p)
{
  return aim - (u_hover * thr2acc_est - G) / std::max(kp_p, 1e-9);
}

/* 给定模型/增益，反解"能悬停的最高 u_hover"（=到得了 aim 的临界值） */
inline double maxHoverableThrust(double aim, double thr2acc_est, double kp_p)
{
  return (kp_p * aim + G) / std::max(thr2acc_est, 1e-9);
}

// ---------------------------------------------------------------- 降落（W6）
struct LandCfg
{
  double v_cmd = 0.15;   // 用户指令降落速度 [m/s]
  double v_cap1 = 0.70;  // PX4 MPC_LAND_SPEED（高段上限）
  double v_cap2 = 0.30;  // MPC_LAND_CRWL（低段上限）
  double alt3 = 1.0;     // MPC_LAND_ALT3：低于此高度进入爬行
  double ground_eps = 0.01;
};

struct LandMem
{
  double p_d = 0.0;      // 当前下降参考（绝对高度）
  bool done = false;
};

/* 高度参考式下降：每拍 p_d 向下推进 v*dt，但**不低于 ground**。
   返回本拍下降速度（正=下降速率），des.v = −rate。 */
inline double landStep(const LandCfg &c, LandMem &m, double ground, double dt)
{
  if (m.done)
    return 0.0;
  double v = std::min(c.v_cmd, c.v_cap1);
  double alt = m.p_d - ground;
  if (alt <= c.alt3)
    v = std::min(v, c.v_cap2);
  m.p_d -= v * dt;
  if (m.p_d - ground <= c.ground_eps)
  {
    m.p_d = ground;
    m.done = true;
  }
  return v;
}

// ---------------------------------------------------------------- 倾角限幅斜率（W6）
inline double slewTilt(double cur, double target, double rate_deg_s, double dt)
{
  double dmax = rate_deg_s * dt;
  double d = target - cur;
  d = std::max(-dmax, std::min(dmax, d));
  return cur + d;
}

// ============================================================================
// 2026-11-07 起飞地面锁定（GROUND_LOCK，判读 v1 §3）：离地判定纯函数
//
// 背景（实测）：起飞前姿态指令是斜的（地面段 roll -6.44 / pitch +3.25 deg），
// 地面按着执行不了，离地瞬间释放成横向冲量 —— 离地后 0~2 s 漂移 0.25~0.60 m。
// 治本 = 地面阶段不产生水平力需求 + 姿态指令走执行器侧 pass-through；
// 本函数只负责"还在不在"地面：双门(dz / vz) + 确认窗 + 滞回，防单点抖动提前放锁
// （提前放锁 = 锚点取在离地前 = 等于没改）。
//
// 无 ROS 依赖；gtest: test_ground_lock。
// ============================================================================
struct GroundLockCfg
{
  bool enable = false;      // 总开关（代码默认关；实机 yaml 打开）
  double z_release = 0.06;  // 离地判据：dz 超锚 [m]
  double vz_release = 0.05; // 离地判据：vz 超此值 [m/s]
  double confirm_s = 0.15;  // 两门同时成立需持续 [s]
};

struct GroundLockState
{
  bool airborne = false; // 本次起飞已确认离地（不再回退）
  double since = -1.0;   // 确认窗起点 [s]，<0 = 未开始
};

struct GroundLockOut
{
  bool locked = false;        // 本拍是否锁定（=仍在地面）
  bool just_airborne = false; // 本拍刚确认离地（调用方此刻重捕锚点）
  GroundLockState next;
};

inline GroundLockOut groundLockStep(bool in_takeoff, double dz, double vz,
                                    double now, const GroundLockCfg &c,
                                    const GroundLockState &s)
{
  GroundLockOut o;
  o.next = s;
  if (!c.enable || !in_takeoff)
  {
    // 非起飞态 / 总开关关：复位，保证下一次起飞重新判定
    o.next.airborne = false;
    o.next.since = -1.0;
    o.locked = false;
    return o;
  }
  if (!s.airborne)
  {
    const bool hit = (dz > c.z_release) && (vz > c.vz_release);
    if (hit)
    {
      const double since = (s.since < 0.0) ? now : s.since;
      if (now - since >= c.confirm_s)
      {
        o.next.airborne = true;
        o.next.since = -1.0;
        o.just_airborne = true;
      }
      else
      {
        o.next.since = since;
      }
    }
    else
    {
      o.next.since = -1.0; // 双门任一掉落即重计时（防抖）
    }
  }
  o.locked = !o.next.airborne;
  return o;
}
} // namespace px4ctrl_core

#endif
