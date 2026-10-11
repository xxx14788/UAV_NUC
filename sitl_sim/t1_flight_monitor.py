#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
t1_flight_monitor.py v1.0 — 首飞态势屏 dashboard v1（专项① 单元2，2026-10-11）
七面指标（阈值预注册，沿用手册§五+自检 v1 口径，禁放宽）:
  1. odom 频率   /vins_estimator/imu_propagate  基线 15Hz；<5Hz 黄、=0 且 armed 红
  2. |Bas|       VINS log [T2diag] 行解析       0.8 告警（预检带口径）
  3. 单帧跳变    相邻 odom position 位移        >0.5m 红色告警（j0d 在线版）
  4. 累计漂移率  10s 窗位移×6 = m/min           6.0 黄 / 18.0 红（=0.1/0.3 m/s，手册警戒线）
  5. 电池电压    /mavros/battery                14.2 预警 / 14.0 红线 / 13.2 立即降落
  6. armed/模式  /mavros/state                  + FSM 状态机行 /debugPx4ctrl/fsm_state（HAFIX 可视）
  7. position_cmd /position_cmd                 100Hz 基线=任务中指示（0=悬停等 goal，非错误）
附: 1Hz 刷新 + 告警着色 + 声音告警(beep, 现场嘈杂) + 最近 5min sparkline + 全程 csv 落盘
    + 一键录制(r 键; 话题集=首飞录袋方案§单元4; firstflight_日期_序号 自动命名)
用法:
  实机: python3 t1_flight_monitor.py --vins-log $(ls -t ~/sitl_realmachine/09_reboot_stack_*/vins_*.log | head -1)
  SITL: python3 t1_flight_monitor.py --vins-log <轮目录>/simvins.log --bag-dir /tmp
键位: r=启动/停止录制  q=退出（--plain 无 curses 时仅打印行）
退出时 csv 自动收尾；录制中退出会先停录再退（袋完整性）。
"""
import argparse
import csv
import datetime as dt
import math
import os
import subprocess
import sys
import threading
import time
from collections import deque

import rospy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String
from mavros_msgs.msg import State

# ---------------- 阈值预注册（禁放宽；改动须呈报+册注记） ----------------
TH_ODOM_OK = 5.0        # Hz，手册 §3.3
TH_BAS_WARN = 0.8       # 预检带
TH_JUMP_RED = 0.5       # m，单帧位移（j0d 在线版）
TH_DRIFT_WARN = 6.0     # m/min (=0.1 m/s)
TH_DRIFT_RED = 18.0     # m/min (=0.3 m/s 手册警戒线)
TH_BATT_WARN = 14.2     # V 预警
TH_BATT_RED = 14.0      # V 红线（起飞门）
TH_BATT_LAND = 13.2     # V 立即手动降落（px4ctrl low_voltage）
TH_CMD_BASE = 100.0     # Hz 基线（指示性，不设告警门）

# 首飞录袋话题集（单元4 方案；SITL/实机差异话题存在性由 rosbag 自行等待）
BAG_TOPICS = [
    "/camera/infra1/image_rect_raw",
    "/camera/infra2/image_rect_raw",
    "/mavros/imu/data_raw",
    "/vins_estimator/odometry",
    "/vins_estimator/imu_propagate",
    "/mavros/state",
    "/mavros/battery",
    "/position_cmd",
    "/debugPx4ctrl/fsm_state",
    "/px4ctrl/takeoff_land",
    "/mavros/local_position/odom",
]

HIST_POINTS = 60        # 5min @5s/点
SPARK_CHARS = "▁▂▃▄▅▆▇█"


def now_str():
    return dt.datetime.now().strftime("%H:%M:%S")


class Metrics:
    """线程共享指标仓（rospy 回调写，UI 主循环读）。"""

    def __init__(self):
        self.lock = threading.Lock()
        # odom 面
        self.odom_times = deque()          # 接收墙钟
        self.last_pos = None
        self.last_jump = 0.0
        self.max_jump = 0.0
        self.jump_red_until = 0.0   # JUMP RED 闩锁到期时刻
        self.pos_hist = deque()            # (wall_t, (x,y,z))
        self.odom_hz = 0.0
        # bas（log 解析）
        self.bas = None
        self.bas_t = None
        # 电池
        self.batt_v = None
        # state
        self.armed = None
        self.mode = ""
        self.connected = None
        # fsm
        self.fsm = ""
        # position_cmd
        self.cmd_times = deque()
        self.cmd_hz = 0.0
        # 告警事件（时间, 文本, 级别）
        self.events = deque(maxlen=200)
        # 历史曲线（每指标 5s 一点）
        self.hz_hist = deque(maxlen=HIST_POINTS)
        self.bas_hist = deque(maxlen=HIST_POINTS)
        self.drift_hist = deque(maxlen=HIST_POINTS)
        self.batt_hist = deque(maxlen=HIST_POINTS)

    def event(self, text, level):
        with self.lock:
            self.events.append((now_str(), text, level))

    def on_odom(self, msg):
        p = msg.pose.pose.position
        t = time.time()
        with self.lock:
            self.odom_times.append(t)
            while self.odom_times and t - self.odom_times[0] > 2.0:
                self.odom_times.popleft()
            self.odom_hz = len(self.odom_times) / 2.0
            if self.last_pos is not None:
                d = math.dist((p.x, p.y, p.z), self.last_pos)
                self.last_jump = d
                if d > self.max_jump:
                    self.max_jump = d
                if d > TH_JUMP_RED:
                    self.jump_red_until = t + 3.0   # RED 闩锁 3s（防 1s 采样粒度漏显）
                    self.events.append((now_str(),
                                        "JUMP %.3f m 单帧位移>0.5m（j0d 红线）" % d, "RED"))
            self.last_pos = (p.x, p.y, p.z)
            self.pos_hist.append((t, (p.x, p.y, p.z)))
            while self.pos_hist and t - self.pos_hist[0][0] > 12.0:
                self.pos_hist.popleft()

    def on_batt(self, msg):
        with self.lock:
            self.batt_v = msg.voltage

    def on_state(self, msg):
        with self.lock:
            self.armed = msg.armed
            self.mode = msg.mode
            self.connected = msg.connected

    def on_fsm(self, msg):
        prev = self.fsm
        with self.lock:
            self.fsm = msg.data
        head = msg.data.split()[0] if msg.data.split() else ""
        if prev and head != prev.split()[0]:
            self.event("FSM %s -> %s" % (prev.split()[0], head),
                       "RED" if head in ("AUTO_LAND", "MANUAL_CTRL") else "INFO")

    def on_cmd(self, _msg):
        t = time.time()
        with self.lock:
            self.cmd_times.append(t)
            while self.cmd_times and t - self.cmd_times[0] > 2.0:
                self.cmd_times.popleft()
            self.cmd_hz = len(self.cmd_times) / 2.0

    def drift_m_per_min(self):
        with self.lock:
            if len(self.pos_hist) < 2:
                return None
            t0, p0 = self.pos_hist[0]
            t1, p1 = self.pos_hist[-1]
            dt_ = t1 - t0
            if dt_ < 3.0:
                return None
            d = math.dist(p0, p1)
            return d / dt_ * 60.0


def tail_bas_loop(path, metrics, stop_evt):
    """轮询 VINS log 尾部解析 [T2diag] |Bas|（2s 周期；文件截断/换新自适应）。"""
    inode = None
    f = None
    while not stop_evt.is_set():
        try:
            if f is None or inode != os.stat(path).st_ino:
                inode = os.stat(path).st_ino
                if f:
                    f.close()
                f = open(path, "r", errors="replace")
                f.seek(0, os.SEEK_END)   # 从尾随起，只追新行
            # 每轮把已积压的新行全部读完（防追赶不及）
            for _ in range(2000):
                line = f.readline()
                if not line:
                    break
                if "[T2diag]" in line and "|Bas|=" in line:
                    try:
                        seg = line.split("|Bas|=")[1].split()[0]
                        metrics.bas = float(seg)
                        metrics.bas_t = time.time()
                    except (ValueError, IndexError):
                        pass
        except OSError:
            f = None
        stop_evt.wait(2.0)


class Recorder:
    """一键录制：firstflight_YYYYMMDD_NN.bag 自动序号。"""

    def __init__(self, bag_dir, topics):
        self.dir = bag_dir
        self.topics = topics
        self.proc = None
        self.path = None

    def start(self):
        os.makedirs(self.dir, exist_ok=True)
        date = dt.datetime.now().strftime("%Y%m%d")
        n = 1
        while os.path.exists(
                os.path.join(self.dir, "firstflight_%s_%02d.bag" % (date, n))):
            n += 1
        self.path = os.path.join(self.dir, "firstflight_%s_%02d.bag" % (date, n))
        self.proc = subprocess.Popen(
            ["rosbag", "record", "-O", self.path] + self.topics,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        return self.path

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


def spark(hist, lo=None, hi=None):
    if not hist:
        return "~" * 10
    vals = [v for v in hist if v is not None]
    if not vals:
        return "~" * 10
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    if hi <= lo:
        hi = lo + 1e-9
    out = []
    for v in hist[-20:]:
        if v is None:
            out.append("·")
        else:
            idx = int((v - lo) / (hi - lo) * (len(SPARK_CHARS) - 1) + 0.5)
            out.append(SPARK_CHARS[max(0, min(len(SPARK_CHARS) - 1, idx))])
    return "".join(out)


def classify(m):
    """返回告警级别与文字列表（级别: OK/WARN/RED）。"""
    rows = []
    # 1 odom
    hz = m.odom_hz
    if hz == 0.0:
        lv = "RED" if m.armed else "WARN"
        rows.append(("odom 频率", "%.1f Hz" % hz, lv,
                     "断流!" if m.armed else "无流(未起飞?)"))
    elif hz < TH_ODOM_OK:
        rows.append(("odom 频率", "%.1f Hz" % hz, "WARN", "<5Hz"))
    else:
        rows.append(("odom 频率", "%.1f Hz" % hz, "OK", "基线15"))
    # 2 bas
    if m.bas is None or (time.time() - (m.bas_t or 0)) > 30:
        rows.append(("|Bas|", "N/A", "WARN", "T2diag 未解析/停更>30s"))
    elif m.bas > TH_BAS_WARN:
        rows.append(("|Bas|", "%.3f" % m.bas, "RED", ">0.8 预检带"))
    else:
        rows.append(("|Bas|", "%.3f" % m.bas, "OK", "<0.8"))
    # 3 jump（RED 闩锁 3s 内保持红显——瞬时事件防 1s/5s 采样漏显）
    if time.time() < getattr(m, 'jump_red_until', 0.0):
        rows.append(("单帧跳变", "%.3f m (max %.3f)" % (m.last_jump, m.max_jump),
                     "RED", "闩锁窗内:跳变红线!"))
    elif m.last_jump > TH_JUMP_RED:
        rows.append(("单帧跳变", "%.3f m" % m.last_jump, "RED", ">0.5m 红线!"))
    else:
        rows.append(("单帧跳变", "%.3f m (max %.3f)" % (m.last_jump, m.max_jump),
                     "OK", ""))
    # 4 drift
    dr = m.drift_m_per_min()
    if dr is None:
        rows.append(("累计漂移率", "N/A", "OK", "窗未满"))
    elif dr > TH_DRIFT_RED:
        rows.append(("累计漂移率", "%.2f m/min" % dr, "RED", ">18 (=0.3m/s)"))
    elif dr > TH_DRIFT_WARN:
        rows.append(("累计漂移率", "%.2f m/min" % dr, "WARN", ">6 (=0.1m/s)"))
    else:
        rows.append(("累计漂移率", "%.2f m/min" % dr, "OK", ""))
    # 5 batt
    if m.batt_v is None:
        rows.append(("电池", "N/A", "WARN", "无流(未插电池=SITL常态)"))
    elif m.batt_v <= TH_BATT_LAND:
        rows.append(("电池", "%.2f V" % m.batt_v, "RED", "<=13.2 立即手动降落!"))
    elif m.batt_v <= TH_BATT_RED:
        rows.append(("电池", "%.2f V" % m.batt_v, "RED", "<=14.0 红线"))
    elif m.batt_v < TH_BATT_WARN:
        rows.append(("电池", "%.2f V" % m.batt_v, "WARN", "<14.2 预警"))
    else:
        rows.append(("电池", "%.2f V" % m.batt_v, "OK", "线 14.2/14.0/13.2"))
    # 6 state（armed=True=飞行中正常态，非告警）
    st = "%s / %s  link:%s" % (
        "True" if m.armed else "False", m.mode or "?",
        "?" if m.connected is None else str(m.connected))
    fsm_head = (m.fsm or "?").split()[0] if m.fsm else "?"
    fsm_lv = "RED" if fsm_head in ("AUTO_LAND",) else "OK"
    rows.append(("armed/mode", st, "OK", ""))
    rows.append(("FSM(HAFIX)", fsm_head, fsm_lv,
                 "盲降保护中!" if fsm_head == "AUTO_LAND" else ""))
    # 7 cmd
    if m.cmd_hz > 0:
        rows.append(("position_cmd", "%.1f Hz" % m.cmd_hz, "OK", "任务中(基线100)"))
    else:
        rows.append(("position_cmd", "0 Hz", "OK", "悬停等goal(非错误)"))
    return rows


def redraw(scr, m, rec, sound_on, csv_w, last_beep):
    import curses
    curses.use_default_colors()
    scr.erase()
    lv_color = {"OK": curses.A_NORMAL, "WARN": curses.A_BOLD, "RED": curses.A_REVERSE}
    worst = "OK"
    y = 0
    scr.addstr(y, 0, "=== 首飞态势屏 t1_flight_monitor v1.0 === %s  [录制: %s]  音:%s"
               % (now_str(),
                  ("ON " + os.path.basename(rec.path)) if rec.proc else "OFF",
                  "ON" if sound_on else "OFF"))
    y += 1
    hist_map = {0: m.hz_hist, 1: m.bas_hist, 3: m.drift_hist, 4: m.batt_hist}
    for i, (name, val, lv, note) in enumerate(classify(m)):
        if lv == "WARN" and worst == "OK":
            worst = "WARN"
        if lv == "RED":
            worst = "RED"
        attr = curses.color_pair(2) if lv == "RED" else (
            curses.color_pair(1) if lv == "WARN" else curses.A_NORMAL)
        sp = spark(hist_map[i]) if i in hist_map else ""
        line = " %-13s: %-28s %-14s %s" % (name, val, ("[%s]" % lv) + (
            " " + note if note else ""), sp)
        try:
            scr.addstr(y, 0, line[:curses.COLS - 1], attr)
        except curses.error:
            pass
        y += 1
    y += 1
    scr.addstr(y, 0, "--- 事件(最近8条) ---")
    y += 1
    with m.lock:
        evs = list(m.events)[-8:]
    for ts, txt, lv in evs:
        try:
            scr.addstr(y, 0, (" [%s] %s: %s" % (ts, lv, txt))[:curses.COLS - 1],
                       curses.color_pair(2) if lv == "RED" else curses.A_NORMAL)
        except curses.error:
            pass
        y += 1
    y += 1
    scr.addstr(y, 0, "键位: r=启/停录制  b=声音开关  q=退出 | 告警=黄(WARN)/反白(RED)")
    # beep：红色在场时 2s 一次
    if worst == "RED" and sound_on and time.time() - last_beep[0] > 2.0:
        curses.beep()
        last_beep[0] = time.time()
    scr.refresh()
    return worst


def plain_tick(m, rec, csv_w):
    rows = classify(m)
    worst = max((lv for _, _, lv, _ in rows), key=lambda s: {"OK": 0, "WARN": 1, "RED": 2}[s])
    print("%s | " % now_str() +
          " | ".join("%s=%s[%s]" % (n, v, lv) for n, v, lv, _ in rows) +
          (" | REC:" + (rec.path or "") if rec.proc else ""))
    if worst == "RED":
        sys.stdout.write("\a")
        sys.stdout.flush()
    return worst


def csv_tick(m, csv_w):
    rows = classify(m)
    dr = m.drift_m_per_min()
    csv_w.writerow([
        dt.datetime.now().isoformat(timespec="seconds"),
        "%.2f" % m.odom_hz,
        "" if m.bas is None else "%.4f" % m.bas,
        "%.4f" % m.last_jump,
        "" if dr is None else "%.3f" % dr,
        "" if m.batt_v is None else "%.2f" % m.batt_v,
        "" if m.armed is None else int(m.armed),
        m.mode, m.fsm, "%.1f" % m.cmd_hz,
        ";".join("%s:%s" % (n, lv) for n, _, lv, _ in rows if lv != "OK")])
    csv_f.flush()


def main():
    global csv_f
    ap = argparse.ArgumentParser()
    ap.add_argument("--vins-log", help="VINS 日志路径（|Bas| T2diag 源；不给则 N/A）")
    ap.add_argument("--csv", default=None, help="csv 落盘路径（默认 /tmp/flight_monitor_时间戳.csv）")
    ap.add_argument("--bag-dir", default=os.path.expanduser("~/sitl_realmachine/bags"),
                    help="一键录制袋目录")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--plain", action="store_true", help="无 curses 纯文本行模式（兼容差终端）")
    args = ap.parse_args()

    if args.csv is None:
        args.csv = "/tmp/flight_monitor_%s.csv" % dt.datetime.now().strftime("%m%d_%H%M")
    csv_f = open(args.csv, "w", newline="", encoding="utf-8")
    csv_w = csv.writer(csv_f)
    csv_w.writerow(["wall_ts", "odom_hz", "bas", "last_jump_m", "drift_m_min",
                    "batt_v", "armed", "mode", "fsm", "cmd_hz", "alarms"])

    rospy.init_node("t1_flight_monitor", anonymous=True, disable_signals=True)
    m = Metrics()
    rospy.Subscriber("/vins_estimator/imu_propagate", Odometry, m.on_odom, queue_size=10)
    rospy.Subscriber("/mavros/battery", BatteryState, m.on_batt, queue_size=2)
    rospy.Subscriber("/mavros/state", State, m.on_state, queue_size=2)
    rospy.Subscriber("/debugPx4ctrl/fsm_state", String, m.on_fsm, queue_size=2)
    rospy.Subscriber("/position_cmd", rospy.AnyMsg, m.on_cmd, queue_size=50)

    stop_evt = threading.Event()
    if args.vins_log:
        threading.Thread(target=tail_bas_loop,
                         args=(args.vins_log, m, stop_evt), daemon=True).start()

    rec = Recorder(args.bag_dir, BAG_TOPICS)
    m.event("monitor 启动 csv=%s" % args.csv, "INFO")

    if args.plain:
        try:
            tick = 0
            while not rospy.is_shutdown():
                plain_tick(m, rec, csv_w)
                tick += 1
                if tick % 5 == 0:
                    csv_tick(m, csv_w)
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass
    else:
        import curses

        def run(scr):
            curses.curs_set(0)
            curses.init_pair(1, curses.COLOR_YELLOW, -1)
            curses.init_pair(2, curses.COLOR_RED, -1)
            scr.timeout(1000)
            sound_on = not args.no_sound
            last_beep = [0.0]
            tick = 0
            while not rospy.is_shutdown():
                redraw(scr, m, rec, sound_on, csv_w, last_beep)
                ch = scr.getch()
                if ch in (ord('q'), ord('Q')):
                    break
                if ch in (ord('r'), ord('R')):
                    if rec.proc:
                        rec.stop()
                        m.event("录制停止", "INFO")
                    else:
                        p = rec.start()
                        m.event("录制启动 %s" % p, "INFO")
                if ch in (ord('b'), ord('B')):
                    sound_on = not sound_on
                tick += 1
                if tick % 5 == 0:
                    with m.lock:
                        m.hz_hist.append(m.odom_hz)
                        m.bas_hist.append(m.bas)
                        m.drift_hist.append(m.drift_m_per_min())
                        m.batt_hist.append(m.batt_v)
                    csv_tick(m, csv_w)
        try:
            curses.wrapper(run)
        except KeyboardInterrupt:
            pass

    if rec.proc:
        rec.stop()
        m.event("录制收尾停止", "INFO")
    stop_evt.set()
    csv_f.close()
    print("csv 落盘: %s" % args.csv)
    if rec.path:
        print("录制袋: %s" % rec.path)


if __name__ == "__main__":
    main()
