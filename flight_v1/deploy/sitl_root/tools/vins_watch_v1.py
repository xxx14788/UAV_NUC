#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vins_watch_v1.py — VINS 实时盯盘 v1（2026-10-21）

只读订阅（零发布，不干扰运行栈），终端每秒一行汇总 + 告警旗；Ctrl+C 退出。
用法:
  python3 vins_watch_v1.py [--vins-log 路径] [--csv out.csv] [--path-band 3.0] [--no-color]

显示样例:
  [14:22:31] pos(+0.12,-0.05,+1.18) h=0.13 |v|=0.03 feat=132 Hz[odom 8.8|prop 50.1] Bas 0.32 cost 1.2e3  OK
告警旗（出现即该行标红/黄）:
  NaN         位置/速度/姿态出现非有限值
  ODOM_RATE   /vins_estimator/odometry < 5 Hz（见过流之后才判）
  PROP_RATE   /vins_estimator/imu_propagate < 35 Hz 且 odom 活着（半死链信号）
  DRIFT       水平距离原点 > --path-band（默认 3.0 m；原点=VINS 初始化点）
  ALT_HIGH/ALT_NEG  z > 5.0 m 或 z < -0.5 m（地面静置 z≈0 属正常，不告警）
  PATHO       日志病理带：|Bas|>0.8 或 final_cost>1e4（正则同 t1_preflight_check）
注: Bas/cost 来自 [--vins-log]（增量尾随，窗口 120s 中位）；不给则显示 -
"""
import argparse
import collections
import math
import os
import re
import sys
import threading
import time

try:
    import rosgraph
except ImportError:
    print("✗ 无 ROS 环境——请在 NUC 上 source 后运行"); sys.exit(3)

PAT_DIAG = re.compile(r"\[T2diag\] t=([0-9.]+).*\|Bas\|=([0-9.e+-]+)")
PAT_SLV = re.compile(r"\[T2slv\] t=([0-9.]+).*final_cost=([0-9.e+-]+)")
PAT_TRACK = re.compile(r"track=(\d+)")


def median(xs):
    xs = sorted(xs); n = len(xs)
    if not n:
        return None
    m = n // 2
    return xs[m] if n % 2 else 0.5 * (xs[m - 1] + xs[m])


class Watcher:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.last = None            # (x,y,z,vx,vy,vz)
        self.nan = False
        self.feat = None
        self.t_odom = collections.deque(maxlen=400)
        self.t_prop = collections.deque(maxlen=2000)
        self.seen_odom = False
        self.seen_prop = False
        self.first_odom_mono = None
        self.log_track = None
        self.bas = collections.deque()   # (log_t, v)
        self.cost = collections.deque()
        self.log_f = None
        self.log_off = 0
        self.q_odom = None
        self.q_px4 = None

    # ---------- 回调（只读） ----------
    def _cb_odom(self, msg):
        p, q, w = msg.pose.pose.position, msg.pose.pose.orientation, msg.twist.twist.linear
        vals = (p.x, p.y, p.z, q.x, q.y, q.z, q.w, w.x, w.y, w.z)
        with self.lock:
            self.t_odom.append(time.monotonic())
            self.seen_odom = True
            if self.first_odom_mono is None:
                self.first_odom_mono = time.monotonic()
            if not all(math.isfinite(v) for v in vals):
                self.nan = True
            self.last = (p.x, p.y, p.z, w.x, w.y, w.z)
        self.q_odom = (q.x, q.y, q.z, q.w)

    def _cb_prop(self, _msg):
        with self.lock:
            self.t_prop.append(time.monotonic())
            self.seen_prop = True

    def _cb_imu(self, msg):
        q = msg.orientation
        with self.lock:
            self.q_px4 = (q.x, q.y, q.z, q.w)

    def _cb_feat(self, msg):
        with self.lock:
            self.feat = (msg.width or 0) * (msg.height or 1)

    # ---------- 日志增量尾随 ----------
    def log_pump(self):
        if not self.log_f:
            return
        try:
            self.log_f.seek(self.log_off)
            chunk = self.log_f.read()
            self.log_off = self.log_f.tell()
        except OSError:
            return
        for line in chunk.splitlines():
            m = PAT_DIAG.search(line)
            if m:
                self.bas.append((float(m.group(1)), float(m.group(2))))
                mt = PAT_TRACK.search(line)
                if mt:
                    self.log_track = int(mt.group(1))
                continue
            m = PAT_SLV.search(line)
            if m:
                self.cost.append((float(m.group(1)), float(m.group(2))))
        now_t = max([t for t, _ in self.bas] + [t for t, _ in self.cost] + [0.0])
        w0 = now_t - 120.0
        while self.bas and self.bas[0][0] < w0:
            self.bas.popleft()
        while self.cost and self.cost[0][0] < w0:
            self.cost.popleft()

    # ---------- 汇总行 ----------
    def render(self):
        now = time.strftime("%H:%M:%S")
        with self.lock:
            last, nan, feat = self.last, self.nan, self.feat
            t_o, t_p = list(self.t_odom), list(self.t_prop)
            first_odom = self.first_odom_mono
            qo, qp = self.q_odom, self.q_px4
        def hz(ts):
            cut = time.monotonic() - 2.0
            return 0.5 * sum(1 for t in ts if t >= cut)
        hz_o, hz_p = hz(t_o), hz(t_p)
        bas = median([v for _, v in self.bas])
        cost = median([v for _, v in self.cost])
        feat_disp = feat if feat is not None else ("~%s" % self.log_track if self.log_track else "-")
        # 速率告警宽限：订阅建立后头几秒连接未稳，先见流满 3 秒才判速率
        warm = first_odom is not None and (time.monotonic() - first_odom) > 3.0

        def _rpy(q):
            x, y, z, w = q
            r = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
            p_ = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))))
            y_ = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
            return r, p_, y_

        def _gb(q):
            x, y, z, w = q
            R = ((1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
                 (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
                 (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)))
            return (-R[0][2], -R[1][2], -R[2][2])

        att_err = None
        if qo is not None and qp is not None:
            go, gq = _gb(qo), _gb(qp)
            d = sum(a_ * b_ for a_, b_ in zip(go, gq))
            att_err = math.degrees(math.acos(max(-1.0, min(1.0, d))))

        flags, hard = [], False
        if nan:
            flags.append("NaN"); hard = True
        if last is None:
            body = "等待 VINS 出流…（初始化完成后才有数据；master 在线即可）"
        else:
            x, y, z, vx, vy, vz = last
            h = math.hypot(x, y); vm = math.sqrt(vx * vx + vy * vy + vz * vz)
            body = ("pos(%+.4f,%+.4f,%+.4f) h=%.4f |v|=%.3f feat=%s Hz[odom %.1f|prop %.1f] Bas %s cost %s"
                    % (x, y, z, h, vm, feat_disp,
                       hz_o, hz_p,
                       ("%.3f" % bas) if bas is not None else "-",
                       ("%.1e" % cost) if cost is not None else "-"))
            if qo is not None:
                ro, po, yo = _rpy(qo)
                if qp is not None:
                    rp_, pp_, yp_ = _rpy(qp)
                    body += ("  ang[V %+.1f/%+.1f/%+.1f P %+.1f/%+.1f/%+.1f d=%.1f]"
                             % (ro, po, yo, rp_, pp_, yp_, att_err if att_err is not None else -1.0))
                else:
                    body += "  ang[V %+.1f/%+.1f/%+.1f P -/-/- d=-]" % (ro, po, yo)
            if h > self.args.path_band:
                flags.append("DRIFT>%.1fm" % self.args.path_band); hard = True
            # 地面静置 z≈0 是正常态，不设下界告警；只报过高与负穿地
            if z > 5.0:
                flags.append("ALT_HIGH z=%.2f" % z); hard = True
            if z < -0.5:
                flags.append("ALT_NEG z=%.2f" % z); hard = True
        if att_err is not None and att_err > 1.0:
            flags.append("ATT_ERR %.1fdeg" % att_err); hard = True
        if warm and hz_o < 5.0:
            flags.append("ODOM_RATE %.1fHz" % hz_o); hard = True
        if warm and hz_p < 35.0:
            flags.append("PROP_RATE %.0fHz(半死链?)" % hz_p); hard = True
        # 2026-11-13 收紧（用户令）：正常静态 ~0.002；起飞后 >0.05 说明零偏在跑
        # （11-12 失效值 0.24-0.55，旧 0.8 门根本拦不住）。
        if bas is not None and bas > 0.05:
            flags.append("BAS_HI %.3f" % bas); hard = True
        if bas is not None and bas > 0.15 or cost is not None and cost > 3e4:
            flags.append("PATHO"); hard = True

        c = self.args.color
        tag = "OK" if not flags else " ".join(flags)
        col = ("", "") if not c else ("\033[1;31m", "\033[0m") if hard and flags else \
              (("\033[1;33m", "\033[0m") if flags else ("\033[1;32m", "\033[0m"))
        return "%s[%s] %s  %s%s%s" % (col[0], now, body, "" if not flags else "⚠ ", tag, col[1])


def main():
    ap = argparse.ArgumentParser(description="VINS 实时盯盘 v1（只读）")
    ap.add_argument("--vins-log", default=None, help="VINS 日志路径（尾随取 Bas/cost 病理带）")
    ap.add_argument("--csv", default=None, help="逐行落盘 CSV")
    ap.add_argument("--path-band", type=float, default=3.0, help="水平距离告警带（米）")
    ap.add_argument("--no-color", dest="color", action="store_false")
    args = ap.parse_args()

    if not rosgraph.is_master_online():
        print("✗ ROS master 不在线——先起栈（bash ~/realflight_stack.sh）再开盯盘"); sys.exit(3)

    w = Watcher(args)
    if args.vins_log and os.path.isfile(args.vins_log):
        w.log_f = open(args.vins_log, "r", errors="replace")
        w.log_off = 0
        w.log_f.seek(0, os.SEEK_END); w.log_off = w.log_f.tell()   # 只看启动后的新行
        print("— 盯盘启动：跟随日志 %s（只取启动后新行；重启 VINS 后请重开盯盘）" % args.vins_log)
    elif args.vins_log:
        print("— 日志 %s 不存在，Bas/cost 显示 -" % args.vins_log)
    print("— 门限：odom≥5Hz prop≥35Hz 水平≤%.1fm z≤5.0(地面≈0正常) |Bas|≤0.15 cost≤3e4；Ctrl+C 退出" % args.path_band)
    print("— 字段说明（启动时打印一次）：")
    print("    pos(+x,+y,+z) = VINS 估计位置（米，四位小数；原点=VINS 初始化点，轮间重启后归零属正常）")
    print("    h = 水平离原点距离（米）  |v| = 速度模长（米/秒）")
    print("    feat = 跟踪特征数（话题无发布时改用日志 track= 值，带 ~ 前缀）")
    print("    Hz[odom] = 优化器输出频率  Hz[prop] = IMU 传播输出频率（px4ctrl 跟的就是这路）")
    print("    Bas = 加计零偏范数中位（日志 120s 窗）  cost = 求解代价中位（越小越健康）")
    print("    ang[V ... P ...] = VINS/PX4 的 roll/pitch/yaw(度)；d = 两者姿态夹角(度，去yaw后可比)")
    print("    d>1.0deg 出 ATT_ERR 旗：VINS 姿态有偏，飞起来会斜着走（2deg≈0.34m/s2）")
    print("    行尾 OK = 全部门限内；⚠+旗名 = 有告警")
    print("— 告警旗含义：")
    print("    NaN        位置/速度/姿态出现非有限值（数值病，立刻按接管标准评估）")
    print("    ODOM_RATE  优化器输出过慢（<5Hz）")
    print("    PROP_RATE  IMU 传播停/慢（<35Hz）——半死链信号：VINS 内部出问题")
    print("    DRIFT      水平离原点超带（默认 >3.0m，悬停期持续增大=在漂）")
    print("    ALT_HIGH   z > 5.0m（超预期高度）   ALT_NEG  z < -0.5m（穿地=异常）")
    print("    PATHO      病理带超限：|Bas|>0.15 或 cost>3e4（历史实机病理带）")

    import rospy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import PointCloud2
    rospy.init_node("vins_watch_v1", anonymous=True, disable_signals=True)
    rospy.Subscriber("/vins_estimator/odometry", Odometry, w._cb_odom, queue_size=1, buff_size=65536)
    rospy.Subscriber("/vins_estimator/imu_propagate", Odometry, w._cb_prop, queue_size=1, buff_size=65536)
    rospy.Subscriber("/vins_estimator/feature_pts", PointCloud2, w._cb_feat, queue_size=1, buff_size=65536)
    from sensor_msgs.msg import Imu
    rospy.Subscriber("/mavros/imu/data", Imu, w._cb_imu, queue_size=20)

    csv_f = open(args.csv, "a") if args.csv else None
    try:
        while not rospy.is_shutdown():
            w.log_pump()
            line = w.render()
            print(line, flush=True)
            if csv_f:
                csv_f.write(re.sub(r"\x1b\[[0-9;]*m", "", line) + "\n"); csv_f.flush()
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        if csv_f:
            csv_f.close()
        print("— 盯盘退出")


if __name__ == "__main__":
    main()
