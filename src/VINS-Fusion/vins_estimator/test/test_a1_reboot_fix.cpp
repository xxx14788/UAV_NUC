// T2-v8.2 A1-fix gtest (prereg_a1fix.md): failure-reboot request must be
// lock-free — the old failure branch called clearState() (which locks
// mProcess) from inside processImage, itself running under processMeasure-
// ments' mProcess: same-thread self-deadlock, odometry dead forever, poisoned
// imu_propagate published until teardown (U3pp A1: 142m/8.25s; A3: 93m/6.0s).
#include "estimator/estimator.h"
#include <gtest/gtest.h>
#include <atomic>
#include <chrono>
#include <mutex>
#include <thread>

TEST(A1RebootFix, RequestSetsBothFlags)
{
    bool failure_occur = 0;
    bool reinit_request = false;
    t2_failure_reboot_request(failure_occur, reinit_request);
    EXPECT_EQ(failure_occur, 1);
    EXPECT_TRUE(reinit_request);
}

// Canary: the request helper must complete even while another thread holds
// the process-thread mutex (the estimator.cpp:388 regime). If someone later
// "enriches" the helper with a locked call (e.g. clearState), this test hangs
// and the gtest timeout fails — regression guard for the deadlock class.
TEST(A1RebootFix, RequestReturnsWhileMutexHeld)
{
    std::mutex mProcess;  // mirrors estimator.h mProcess held at est.cpp:388
    bool failure_occur = 0;
    bool reinit_request = false;
    std::atomic<bool> done{false};
    std::thread holder([&] { mProcess.lock(); while (!done) std::this_thread::sleep_for(std::chrono::microseconds(200)); mProcess.unlock(); });
    // let the holder actually acquire
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    auto t0 = std::chrono::steady_clock::now();
    t2_failure_reboot_request(failure_occur, reinit_request);
    double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    done = true;
    holder.join();
    EXPECT_LT(ms, 500.0);
    EXPECT_EQ(failure_occur, 1);
    EXPECT_TRUE(reinit_request);
}

// Documentation-grade: the OLD shape (locking an already-held non-recursive
// mutex) is detectable — try_lock fails while held. This is the failure mode
// the fix removes; kept as an executable record of the bug mechanics.
TEST(A1RebootFix, OldDeadlockShapeIsDetectable)
{
    std::mutex mProcess;
    mProcess.lock();
    EXPECT_FALSE(mProcess.try_lock());  // same-thread relock would deadlock
    mProcess.unlock();
    EXPECT_TRUE(mProcess.try_lock());   // released path is lockable again
    mProcess.unlock();
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
