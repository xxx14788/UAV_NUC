#pragma once
// T2NANDEF (v11.17 2.1, prereg nan_defense_v1): NaN 防线判定纯函数(gtest 单测面)。
// 健康轮零触发=零行为差;触发判据见 t2_results/nan_defense_v1/prereg_v1.md(冻结)。
#include <cmath>
#include <vector>
#include <Eigen/Dense>

namespace t2nandef
{
// ceres::TerminationType::FAILURE 的数值(estimator.cpp 静态断言对齐;ceres 枚举漂移=编译期暴露)
constexpr int CERES_FAILURE = 2;

// D3: init 后置门求解面谓词——initial_cost 有限 ∧ termination!=FAILURE ∧ iters>=1
inline bool init_solve_ok(double initial_cost, int term, int iters)
{
    return std::isfinite(initial_cost) && term != CERES_FAILURE && iters >= 1;
}

// D4: cost-gate median 退化谓词——median<=0 ∨ 非有限
inline bool med_degenerate(double med)
{
    return !std::isfinite(med) || med <= 0.0;
}

// D5: prior 块数值有限性(residuals + jacobians 全扫)
inline bool block_finite(const Eigen::VectorXd &r,
                         const std::vector<Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>> &J)
{
    for (int i = 0; i < r.size(); i++)
        if (!std::isfinite(r[i]))
            return false;
    for (const auto &j : J)
        for (int a = 0; a < j.rows(); a++)
            for (int b = 0; b < j.cols(); b++)
                if (!std::isfinite(j(a, b)))
                    return false;
    return true;
}
} // namespace t2nandef
