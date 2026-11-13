// 2026-11-12 质量修复 C：P2/P5 的不变量自检（进仓，防腐坏）。
// 覆盖：末端速度基线 / 追加 1 个减半 / 追加 2 个归零 / 按 ratio 拉伸后可行且仍为零。
#include <bspline_opt/uniform_bspline.h>
#include <cmath>
#include <iostream>

using namespace ego_planner;

static int g_fail = 0;
static void check(bool ok, const char *msg) {
  std::cout << (ok ? "PASS " : "FAIL ") << msg << std::endl;
  if (!ok) ++g_fail;
}

int main() {
  Eigen::MatrixXd cp(3, 10);
  for (int i = 0; i < 10; ++i) { cp(0, i) = 0.15 * i; cp(1, i) = 0.0; cp(2, i) = 0.0; }

  UniformBspline base(cp, 3, 0.05);
  base.setPhysicalLimits(0.5, 4.0, 0.05);
  const double v_base = base.getDerivative().evaluateDeBoorT(base.getTimeSum()).norm();
  check(v_base > 2.9 && v_base < 3.1, "baseline end velocity ~3 m/s");

  double ratio;
  const bool feasible = base.checkFeasibility(ratio, false);
  check(!feasible && ratio > 5.0, "baseline infeasible, ratio ~6");

  auto dup = [&](int k) {
    Eigen::MatrixXd c = cp;
    const int n = c.cols();
    c.conservativeResize(Eigen::NoChange, n + k);
    for (int i = 0; i < k; ++i) c.col(n + i) = c.col(n - 1);
    return UniformBspline(c, 3, 0.05);
  };

  UniformBspline p1 = dup(1);
  const double v1 = p1.getDerivative().evaluateDeBoorT(p1.getTimeSum()).norm();
  check(std::fabs(v1 - 1.5) < 0.05, "append 1 CP -> half end velocity");

  UniformBspline p2 = dup(2);
  const double v2 = p2.getDerivative().evaluateDeBoorT(p2.getTimeSum()).norm();
  check(v2 < 0.01, "append 2 CP (order-1) -> zero end velocity");

  // 生产版 P2（2026-11-12 质量修复 A）：把最后控制点改为样条原终点 pe，再追加 2 个 pe。
  // 断言：终点精确不变、末端速度=0（尾部无前冲由 /tmp/test_p2end 的 max_x 检查覆盖）。
  const Eigen::Vector3d pe = base.evaluateDeBoorT(base.getTimeSum());
  Eigen::MatrixXd c_end = cp;
  c_end.col(9) = pe;
  c_end.conservativeResize(Eigen::NoChange, 12);
  c_end.col(10) = pe;
  c_end.col(11) = pe;
  UniformBspline p_end(c_end, 3, 0.05);
  const Eigen::Vector3d pe2 = p_end.evaluateDeBoorT(p_end.getTimeSum());
  const double v_end = p_end.getDerivative().evaluateDeBoorT(p_end.getTimeSum()).norm();
  check((pe2 - pe).norm() < 1e-6, "end-point-preserving P2 keeps endpoint");
  check(v_end < 0.01, "end-point-preserving P2 zero end velocity");

  UniformBspline p3(p2.getControlPoint(), 3, p2.getInterval() * ratio);
  p3.setPhysicalLimits(0.5, 4.0, 0.05);
  double r3;
  const bool f3 = p3.checkFeasibility(r3, false);
  const double v3 = p3.getDerivative().evaluateDeBoorT(p3.getTimeSum()).norm();
  check(f3, "stretch by ratio -> feasible");
  check(v3 < 0.01, "stretch preserves zero end velocity");

  // 2026-11-13 v2：近距锚定只对 <=0.20 m；0.2 m 在 1.2 s interval 下必须可行，
  // 0.74 m 远距必须不可行（证明"远距离不强制锚定"的保护是必要的）。
  {
    const Eigen::MatrixXd cps_p_end = p_end.getControlPoint();
    const Eigen::Vector3d te = cps_p_end.col(cps_p_end.cols() - 1);
    const double gaps[2] = {0.20, 0.74};
    for (int gi = 0; gi < 2; ++gi)
    {
      const Eigen::Vector3d goal = te + Eigen::Vector3d(gaps[gi], 0.0, 0.0);
      Eigen::MatrixXd c = cps_p_end;
      for (int k = 1; k <= 3; ++k)
        c.col(c.cols() - k) = goal;
      UniformBspline q(c, 3, 1.2);
      q.setPhysicalLimits(0.5, 4.0, 0.05);
      double rq;
      const bool fq = q.checkFeasibility(rq, false);
      check(gi == 0 ? fq : !fq,
            gi == 0 ? "anchor 0.20m @1.2s feasible" : "anchor 0.74m @1.2s infeasible -> fallback path");
    }
  }

  std::cout << (g_fail ? "SELFCHECK FAIL" : "SELFCHECK PASS") << std::endl;
  return g_fail ? 1 : 0;
}
