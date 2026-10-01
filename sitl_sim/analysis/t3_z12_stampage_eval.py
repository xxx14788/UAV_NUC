#!/usr/bin/env python3
"""t3_z12_stampage_eval.py — Z1.2 v2 接线后 STAMP-AGE 层在线评估（T3 v8.3 单元 4 预写）

用途：接线（enabled_v2 true）后的在线轮 bag 上评估 STAMP-AGE 层健康度。
口径（预注册，2026-10-02 冻结；C07 勘误④约束下的一阶近似）：
  - 库袋无 rcv_stamp（Px4ctrlDebug 无双戳字段）→ 截龄代理 = rosbag record time(袋收包时刻)
    − header.stamp。录制机=消费机（单机 SITL）时该代理与 px4ctrl 进程内 t_now−stamp
    同源同量级（差=rosbag 进程调度延迟，健康链路 <5ms 量级）。
  - 门模拟：age > 0.2s（odom_sanity_v2.h stamp_age_max）帧计数+占比；
    单调层（stamp 回退）计数一并报。
  - 判读带（预注册）：
      健康：p50<0.03s，p95<0.06s，>0.2s 帧占比 <0.01%（≈零误伤）
      可疑：p95∈[0.06,0.2) 或偶发 >0.2s——先查录制负载（大 IO 会抬高代理偏差）
      触发面：>0.2s 帧成簇=真陈旧流（接线后应被拒，对拍 px4ctrl log rejected_stamp）
  输出：JSON（stdout）+可选 --csv 逐帧时间轴（t, age_s）
用法：t3_z12_stampage_eval.py <bag> [--topic /vins_estimator/imu_propagate] [--csv out.csv]
"""
import json
import sys

import rosbag

AGE_GATE = 0.2


def main():
    bag_path = sys.argv[1]
    topic = '/vins_estimator/imu_propagate'
    csv_out = None
    if '--topic' in sys.argv:
        topic = sys.argv[sys.argv.index('--topic') + 1]
    if '--csv' in sys.argv:
        csv_out = sys.argv[sys.argv.index('--csv') + 1]
    ages, back_jumps = [], 0
    last_stamp = None
    t0 = None
    with rosbag.Bag(bag_path) as b:
        t0 = b.get_start_time()
        for _, msg, t in b.read_messages(topics=[topic]):
            try:
                st = msg.header.stamp.to_sec()
            except AttributeError:
                continue
            rcv = t.to_sec()
            ages.append((rcv, rcv - st))
            if last_stamp is not None and st < last_stamp - 1e-9:
                back_jumps += 1
            last_stamp = st
    if not ages:
        print(json.dumps({'bag': bag_path, 'topic': topic, 'n': 0, 'error': 'no msgs'}))
        return 2
    vals = sorted(a for _, a in ages)
    n = len(vals)

    def pct(p):
        return round(vals[min(int(p * n), n - 1)], 4)

    over = sum(1 for v in vals if v > AGE_GATE)
    rep = {
        'bag': bag_path, 'topic': topic, 'n': n,
        'age_p50_s': pct(0.50), 'age_p95_s': pct(0.95), 'age_p999_s': pct(0.999),
        'age_max_s': pct(1.0),
        'gate_0.2s': AGE_GATE,
        'over_gate_n': over, 'over_gate_frac': round(over / n, 6),
        'stamp_back_jumps_n': back_jumps,
        'verdict_band': 'HEALTHY' if (pct(0.95) < 0.06 and over / n < 1e-4)
        else ('SUSPECT' if pct(0.95) < AGE_GATE else 'TRIGGER-FACE'),
        'note': 'age 代理=bag rcv time - header.stamp(C07 勘误④一阶口径); '
                '接线后对拍 px4ctrl rejected_stamp 计数定真触发面',
        'bag_start': round(t0, 2),
    }
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    if csv_out:
        with open(csv_out, 'w') as f:
            f.write('t_rel,age_s\n')
            for rcv, a in ages:
                f.write('%.3f,%.4f\n' % (rcv - t0, a))
    return 0


if __name__ == '__main__':
    sys.exit(main())
