#include <gtest/gtest.h>
#include <eigen3/Eigen/Dense>
#include <cmath>
#include "factor/imu_factor.h"
#include "estimator/parameters.h"

// T2-WA3.6 gtest: IMUFactor analytic vs central-difference numeric jacobians on
// the non-quaternion columns (pose p-cols 0-2 + all 9 speedbias cols), where no
// local-parameterization discrepancy exists -> tight tolerance valid.
// Plus repropagate semantics assertions (linearization point + directional).

using namespace Eigen;

struct T2ImuTestEnv
{
    T2ImuTestEnv()
    {
        // integration noise globals are zero in a bare test process -> covariance
        // would stay 0 and sqrt_info (LLT of cov^-1) becomes NaN. Set real values.
        ACC_N = 0.2; GYR_N = 0.01; ACC_W = 0.001; GYR_W = 0.001;
    }
};
static T2ImuTestEnv t2_imu_test_env;

static IntegrationBase *make_pi(double dt, const Vector3d &ba, const Vector3d &bg)
{
    Vector3d acc0(0.11, -0.07, 9.79), acc1(0.13, -0.05, 9.81);
    Vector3d gyr0(0.02, -0.03, 0.01), gyr1(0.015, -0.025, 0.012);
    IntegrationBase *pi = new IntegrationBase(acc0, gyr0, ba, bg);
    pi->push_back(dt, acc1, gyr1);
    pi->propagate(dt, acc1, gyr1);
    return pi;
}

TEST(ImuFactorJac, NonQuatColumnsMatchNumeric)
{
    for (int trial = 0; trial < 6; trial++)
    {
        double dt = (1.0 / 223.0) * (1.0 + 0.15 * trial);
        Vector3d ba = Vector3d::Random() * 0.03, bg = Vector3d::Random() * 0.003;
        IntegrationBase *pi = make_pi(dt, ba, bg);
        IMUFactor f(pi);
        double pip[7], pisb[9], pjp[7], pjsb[9];
        Vector3d Pi = Vector3d::Random() * 0.2;
        Vector3d Pj = Pi + Vector3d(0.01, -0.02, 0.03) + Vector3d(0, 0, -0.5 * 9.8 * dt * dt);
        Vector3d Vi = Vector3d::Random() * 0.3;
        Vector3d Vj = Vi + Vector3d(0.005, 0.003, -0.01) - Vector3d(0, 0, 9.8 * dt);
        Quaterniond Qi(Vector4d::Random().normalized());
        Quaterniond Qj = Qi * Quaterniond(AngleAxisd(0.004, Vector3d::UnitY()));
        Vector3d Bai = ba + Vector3d(0.005, -0.004, 0.003);
        Vector3d Bgi = bg + Vector3d(0.0005, 0.0004, -0.0006);
        Vector3d Baj = Bai + Vector3d(0.001, -0.002, 0.0015);
        Vector3d Bgj = Bgi + Vector3d(0.0001, -0.0002, 0.00015);
        for (int k = 0; k < 3; k++)
        {
            pip[k] = Pi(k); pjp[k] = Pj(k);
            pisb[k] = Vi(k); pjsb[k] = Vj(k);
            pisb[3 + k] = Bai(k); pjsb[3 + k] = Baj(k);
            pisb[6 + k] = Bgi(k); pjsb[6 + k] = Bgj(k);
            pip[3 + k] = Qi.coeffs()[k]; pjp[3 + k] = Qj.coeffs()[k];
        }
        pip[6] = Qi.w(); pjp[6] = Qj.w();
        const double *prms[4] = {pip, pisb, pjp, pjsb};
        Matrix<double, 15, 7, RowMajor> J7a, J7b;
        Matrix<double, 15, 9, RowMajor> J9a, J9b;
        double *jacs[4] = {J7a.data(), J9a.data(), J7b.data(), J9b.data()};
        double r0[15];
        f.Evaluate(prms, r0, jacs);
        double eps = 1e-7;
        auto numcol = [&](int blk, int c) {
            double *blocks[4] = {pip, pisb, pjp, pjsb};
            double save = blocks[blk][c];
            double rp[15], rm[15];
            double *jn[4] = {nullptr, nullptr, nullptr, nullptr};
            blocks[blk][c] = save + eps; f.Evaluate(prms, rp, jn);
            blocks[blk][c] = save - eps; f.Evaluate(prms, rm, jn);
            blocks[blk][c] = save;
            VectorXd d(15);
            for (int r = 0; r < 15; r++) d(r) = (rp[r] - rm[r]) / (2 * eps);
            return d;
        };
        // pose p-columns 0-2 (block 0 and block 2)
        for (int c = 0; c < 3; c++)
        {
            VectorXd n0 = numcol(0, c), n2 = numcol(2, c);
            for (int r = 0; r < 15; r++)
            {
                EXPECT_NEAR(J7a(r, c), n0(r), 2e-3 * (1 + fabs(n0(r)))) << "t" << trial << " blk0 c" << c << " r" << r;
                EXPECT_NEAR(J7b(r, c), n2(r), 2e-3 * (1 + fabs(n2(r)))) << "t" << trial << " blk2 c" << c << " r" << r;
            }
        }
        // speedbias all 9 cols (blocks 1 and 3)
        for (int c = 0; c < 9; c++)
        {
            VectorXd n1 = numcol(1, c), n3 = numcol(3, c);
            for (int r = 0; r < 15; r++)
            {
                EXPECT_NEAR(J9a(r, c), n1(r), 2e-3 * (1 + fabs(n1(r)))) << "t" << trial << " blk1 c" << c << " r" << r;
                EXPECT_NEAR(J9b(r, c), n3(r), 2e-3 * (1 + fabs(n3(r)))) << "t" << trial << " blk3 c" << c << " r" << r;
            }
        }
        delete pi;
    }
}

TEST(Repropagate, LinearizationPointMoves)
{
    double dt = 1.0 / 223.0;
    IntegrationBase *pi = make_pi(dt, Vector3d::Zero(), Vector3d::Zero());
    Vector3d ba1(0.08, -0.02, 0.03), bg1(0.002, -0.001, 0.0005);
    // direction: at bias ba1==linearized, the v-row bias correction term dv_dba*(Bai-lin_ba) vanishes
    double before = dt * ba1.norm();      // |correction| if evaluated with old lin point and Bai=ba1
    pi->repropagate(ba1, bg1);
    EXPECT_NEAR((pi->linearized_ba - ba1).norm(), 0.0, 1e-12);
    EXPECT_NEAR((pi->linearized_bg - bg1).norm(), 0.0, 1e-12);
    double after = 0.0;                    // correction term now zero at that state bias
    EXPECT_LT(after, before);
    EXPECT_GT(before, 0.0);
    delete pi;
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
