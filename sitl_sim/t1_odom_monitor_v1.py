#!/usr/bin/env python3
"""t1_odom_monitor.py — odom 监控告警器 v1.2 (T1 v11.28 3a;v11.39 三注记+P-2 终态面)

v1.0→v1.2(T1 v11.39 单元4,判读缺陷注记落码):
  [a] D 检测器阈值口径注记: drate 语义=滑窗平均漂移速率 m/s;事件行双口径
      (detail 附 m/min 换算+rec.d_rate_m_per_min)——判读侧禁再歧义(报告口径=m/min)
  [b] phase 横跳修复: TAKEOFF 升档须 |vz|>0.3 持续≥1s(CRUISE↔TAKEOFF 抖动会
      hist.clear()+D.clear() 反复清零=慢漂检测盲区,D5 判读在案)
  [c] 收尾退出时序: SIGTERM/SIGINT→final state dump(批 teardown 杀监控时尾段
      告警/状态不再丢;disable_signals 下手动接管)
  [d] P-2 终态判据面: 订阅 /mavros/extended_state;armed True→False 沿发 TERMINAL 事件
      (landed_state=1=SAFE_LANDED 安全终态 / =2=AIRBORNE_KILL 空中断电机[HAFIX KILL
      路径预期=先 2 后 1] / 话题缺=UNKNOWN)——「电机停+落地」双要素监控面

v0→v1 修复(缺陷编号沿 v11.25r2 D5 判读):
  [1] 起飞段相位感知: GROUND/TAKEOFF(解锁沿≤10s 或 |vz|>0.3)/CRUISE 分档;
      TAKEOFF 段 vmax/drate 阈值 ×2(起飞激励假阳修复); GROUND 段漂移静默
  [2] 一次性聋→事件状态机: 每类独立 IDLE→ACTIVE(全量)→LATCHED(30s remind)→RECOVERED;
      恢复后重新武装,二次触发=新事件计数; --repeat 保留(语义=PHASE 行也打印)
  [3] 双发布器交错→发布器追踪: 启动快照原发布器; 多发布器/接管即告警(按名,非频率)
预注册判据(D5 六用例)见台账 local_staging/unit3_3a_monitor_v1_design.md — 禁放宽。

输出契约(v0 兼容): <out>/odom_alarm.json(state+alarms)+stdout "ODOM-ALARM {json}"
                  +<out>/odom_alarm.flag; 新增 <out>/monitor_v1_events.log
用法: t1_odom_monitor.py <out_dir> [--vmax 0.5] [--vsec 3] [--drate 0.3] [--win 10]
                          [--repeat] [--takeoff-win 10] [--timeout 5]"""
import sys, os, json, argparse, math, collections, signal


class AlarmFSM:
    IDLE, ACTIVE, LATCHED, RECOVERED = "IDLE", "ACTIVE", "LATCHED", "RECOVERED"

    def __init__(self, kind):
        self.kind = kind
        self.state = self.IDLE
        self.count = 0
        self.active_since = 0.0
        self.last_transition = 0.0
        self.last_remind = 0.0

    def trigger(self, t):
        if self.state in (self.IDLE, self.RECOVERED):
            self.count += 1
            self.state = self.ACTIVE
            self.active_since = t
            self.last_transition = t
            return "NEW" if self.count == 1 else "REARM"
        return None  # 已热: 不重复

    def tick(self, t, remind_s=30.0):
        if self.state == self.ACTIVE and t - self.last_transition >= remind_s:
            self.state = self.LATCHED
            self.last_remind = t
            self.last_transition = t
            return "PERSIST"
        if self.state == self.LATCHED and t - self.last_remind >= remind_s:
            self.last_remind = t
            return "PERSIST"
        return None

    def clear(self, t):
        if self.state in (self.ACTIVE, self.LATCHED):
            dur = t - self.active_since
            self.state = self.RECOVERED
            self.last_transition = t
            return dur
        return None

    @property
    def hot(self):
        return self.state in (self.ACTIVE, self.LATCHED)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--vmax", type=float, default=0.5)
    ap.add_argument("--vsec", type=float, default=3.0)
    ap.add_argument("--drate", type=float, default=0.3)
    ap.add_argument("--win", type=float, default=10.0)
    ap.add_argument("--repeat", action="store_true")
    ap.add_argument("--takeoff-win", type=float, default=10.0)
    ap.add_argument("--timeout", type=float, default=5.0)  # 断流(与 HAFIX dead_s 同源)
    ap.add_argument("--jump", type=float, default=3.0)     # 位置单步跳阈(米)
    ap.add_argument("--topic", default="/vins_estimator/odometry")
    a = ap.parse_args()

    import rospy
    from nav_msgs.msg import Odometry
    rospy.init_node("t1_odom_monitor_v1", anonymous=True, disable_signals=True)

    hist = collections.deque()  # (t, x, y, z)
    v_run_start = None
    last_p = None
    state = {"t0": None, "frames": 0, "alarms": [], "phase": "GROUND", "monitor": "v1.2"}
    vz_run_start = None  # v1.2[b]: vz>0.3 持续计时(TAKEOFF 升档迟滞)
    alarms = {k: AlarmFSM(k) for k in ("V", "D", "J", "TIMEOUT", "MULTI_PUB", "PUB_TAKEOVER")}
    # 相位
    arm_was = False
    takeoff_at = None
    phase = "GROUND"
    # 发布器
    pub_snapshot, pub_snap_done = set(), False
    last_msg_wall = None
    evlog = open(os.path.join(a.out_dir, "monitor_v1_events.log"), "a", buffering=1)

    def emit(t, kind, why, detail, extra=None):
        rec = {"t": round(t, 2), "kind": kind, "why": why, "detail": detail,
               "pos": None, "phase": phase}
        if extra:
            rec.update(extra)
        state["alarms"].append(rec)
        json.dump(state, open(os.path.join(a.out_dir, "odom_alarm.json"), "w"),
                  ensure_ascii=False, indent=1)
        if p3.get("last_t") is not None and (rospy.get_time() - p3["last_t"]) < 30.0:
            rec["p3_window"] = True  # T1 v11.31 2f: 计划内恢复窗=降级告警等级
        print("ODOM-ALARM " + json.dumps(rec, ensure_ascii=False), flush=True)
        open(os.path.join(a.out_dir, "odom_alarm.flag"), "a").write(f"{kind}\n")
        evlog.write(f"{t:.2f} {kind} {why} {detail}\n")

    def cb(msg):
        nonlocal v_run_start, arm_was, takeoff_at, phase, last_msg_wall, last_p, vz_run_start
        t = msg.header.stamp.to_sec() or rospy.get_time()
        p = msg.pose.pose.position
        tw = msg.twist.twist.linear
        v = math.sqrt(tw.x ** 2 + tw.y ** 2 + tw.z ** 2)
        wall = rospy.get_time()
        last_msg_wall = wall
        hist.append((t, p.x, p.y, p.z))
        while hist and t - hist[0][0] > a.win:
            hist.popleft()
        state["frames"] += 1
        if state["t0"] is None:
            state["t0"] = t

        # ---- [1] 相位分档(v1.2[b]: vz 路径升 TAKEOFF 须持续≥1s,防横跳清零 D 窗) ----
        armed = rospy.get_param("/mavros/state/armed", None)
        if armed is not None and armed and not arm_was:
            takeoff_at = t
        if armed is not None:
            arm_was = armed
        if abs(tw.z) > 0.3:
            vz_run_start = vz_run_start or t
        else:
            vz_run_start = None
        vz_sustained = vz_run_start is not None and (t - vz_run_start) >= 1.0
        in_takeoff = (takeoff_at is not None and t - takeoff_at <= a.takeoff_win) or vz_sustained
        new_phase = ("GROUND" if armed is False else
                     "TAKEOFF" if in_takeoff and armed else
                     "CRUISE" if armed else phase)
        if armed is None:  # 无 mavros 状态(SITL 纯 VINS 段): 以 vz 判
            new_phase = "TAKEOFF" if in_takeoff else "CRUISE"
        if new_phase != phase:
            evlog.write(f"{t:.2f} PHASE {phase}->{new_phase}\n")
            if a.repeat:
                print(f"PHASE {phase}->{new_phase}", flush=True)
            phase = new_phase
            state["phase"] = phase
            hist.clear()  # 相位切换排空滑窗: 旧相位位移不参与新相位判据(TAKEOFF->CRUISE 假阳修复)
            alarms["D"].clear(t)
        thr_scale = 2.0 if phase == "TAKEOFF" else 1.0

        # ---- J 阈(单帧位置跳; 相位不放宽——跳变安全语义不变) ----
        if last_p is not None:
            step = math.dist((last_p[0], last_p[1], last_p[2]), (p.x, p.y, p.z))
            if step >= a.jump:
                r = alarms["J"].trigger(t)
                if r:
                    emit(t, "J", r, "step=%.2fm>=%.1f phase=%s" % (step, a.jump, phase))
            else:
                d = alarms["J"].clear(t)
                if d is not None:
                    evlog.write(f"{t:.2f} J RECOVERED dur={d:.1f}s\n")
        last_p = (p.x, p.y, p.z)

        # ---- [2] V 阈(速度异常; TAKEOFF 放宽×2) ----
        if v > a.vmax * thr_scale:
            v_run_start = v_run_start or t
            if t - v_run_start >= a.vsec:
                r = alarms["V"].trigger(t)
                if r:
                    emit(t, "V", r, "|v|=%.2f>%.2f 持续%.1fs phase=%s" % (v, a.vmax * thr_scale, t - v_run_start, phase))
        else:
            v_run_start = None
            d = alarms["V"].clear(t)
            if d is not None:
                evlog.write(f"{t:.2f} V RECOVERED dur={d:.1f}s\n")

        # ---- D 阈(慢漂; GROUND 静默, TAKEOFF 放宽×2; v1.2[a] 双口径注记) ----
        if phase != "GROUND" and len(hist) >= 2 and t - hist[0][0] >= a.win * 0.5:
            dpos = math.dist(hist[0][1:], (p.x, p.y, p.z))
            rate = dpos / (t - hist[0][0])
            if rate > a.drate * thr_scale:
                r = alarms["D"].trigger(t)
                if r:
                    emit(t, "D", r, "drift=%.3fm/s(=%.1fm/min)>%.3fm/s win=%.0fs phase=%s"
                         % (rate, rate * 60, a.drate * thr_scale, a.win, phase),
                         extra={"d_rate_m_per_min": round(rate * 60, 3)})
            else:
                d = alarms["D"].clear(t)
                if d is not None:
                    evlog.write(f"{t:.2f} D RECOVERED dur={d:.1f}s\n")

    rospy.Subscriber(a.topic, Odometry, cb, queue_size=2)

    # T1 v11.31 2f P3: 计划内 reboot 通告订阅(降级注记面)
    from std_msgs.msg import UInt32 as _U32
    p3 = {"last_ev": 0, "last_t": None}

    # v1.2[d] P-2 终态判据面: armed True→False 沿发 TERMINAL(landed_state 判 SAFE/AIRBORNE_KILL)
    term = {"landed_state": None, "armed_was": None}

    def _es_cb(msg):
        term["landed_state"] = msg.landed_state

    def _st_cb(msg):
        if term["armed_was"] and not msg.armed:
            ls = term.get("landed_state")
            verdict = "SAFE_LANDED" if ls == 1 else ("AIRBORNE_KILL" if ls == 2 else "UNKNOWN(no-extended-state)")
            rec = {"t": round(rospy.get_time(), 2), "kind": "TERMINAL", "why": "armed_drop",
                   "detail": "landed_state=%s verdict=%s" % (ls, verdict), "phase": phase}
            state["alarms"].append(rec)
            json.dump(state, open(os.path.join(a.out_dir, "odom_alarm.json"), "w"),
                      ensure_ascii=False, indent=1)
            print("ODOM-ALARM " + json.dumps(rec, ensure_ascii=False), flush=True)
            open(os.path.join(a.out_dir, "odom_alarm.flag"), "a").write("TERMINAL\n")
            evlog.write("%s TERMINAL armed_drop landed_state=%s %s\n" % (rec["t"], ls, verdict))
        term["armed_was"] = msg.armed

    try:
        from mavros_msgs.msg import ExtendedState as _ES
        from mavros_msgs.msg import State as _MState
        rospy.Subscriber("/mavros/extended_state", _ES, _es_cb, queue_size=1)
        rospy.Subscriber("/mavros/state", _MState, _st_cb, queue_size=1)
    except Exception:
        pass  # 话题/类型缺失(纯 VINS 段)不影响监控本业;终态面=UNKNOWN 注记路径

    def p3_active():
        return p3["last_t"] is not None and (rospy.get_time() - p3["last_t"]) < 30.0

    def _p3_cb(msg):
        p3["last_ev"] = msg.data >> 16
        p3["last_t"] = rospy.get_time()
        print("P3-NOTIFY ev=%d cnt=%d" % (msg.data >> 16, msg.data & 0xFFFF), flush=True)

    try:
        rospy.Subscriber("/vins_estimator/reboot_notify", _U32, _p3_cb, queue_size=2)
    except Exception:
        pass  # 话题缺失(旧栈)不影响监控本业

    # ---- [3] 发布器追踪 + 断流 + remind 主循环 ----
    import rosgraph.masterapi
    master = rosgraph.masterapi.Master("/t1_odom_monitor_v1")
    # v1.2[c] 收尾退出时序: SIGTERM/SIGINT→受控 shutdown(while 退出后 final dump 不丢)
    def _final_dump_signal(signum, _frame):
        rospy.signal_shutdown("sig%d" % signum)
    signal.signal(signal.SIGTERM, _final_dump_signal)
    signal.signal(signal.SIGINT, _final_dump_signal)
    rate = rospy.Rate(2)
    t_start = rospy.get_time()
    while not rospy.is_shutdown():
        t = rospy.get_time()
        # 断流(TIMEOUT)
        if last_msg_wall is None:
            if t - t_start > 30:
                r = alarms["TIMEOUT"].trigger(t)
                if r:
                    emit(t, "TIMEOUT", r, "no-odom-since-start>30s")
        elif t - last_msg_wall > a.timeout:
            r = alarms["TIMEOUT"].trigger(t)
            if r:
                emit(t, "TIMEOUT", r, "silence=%.1fs>%.0fs" % (t - last_msg_wall, a.timeout))
        else:
            d = alarms["TIMEOUT"].clear(t)
            if d is not None:
                evlog.write(f"{t:.2f} TIMEOUT RECOVERED dur={d:.1f}s\n")
        # 发布器
        try:
            pubs_sys, _, _ = master.getSystemState()
            cur = set()
            for topic, nodes in pubs_sys:
                if topic == a.topic:
                    cur = set(nodes)
            if not pub_snap_done and cur:
                pub_snapshot = cur
                pub_snap_done = True
                evlog.write(f"{t:.2f} PUB_SNAPSHOT {sorted(cur)}\n")
            elif pub_snap_done:
                if len(cur) > 1:
                    r = alarms["MULTI_PUB"].trigger(t)
                    if r:
                        emit(t, "MULTI_PUB", r, "nodes=%s" % sorted(cur))
                elif not alarms["MULTI_PUB"].hot:
                    pass
                else:
                    d = alarms["MULTI_PUB"].clear(t)
                    if d is not None:
                        evlog.write(f"{t:.2f} MULTI_PUB RECOVERED\n")
                if cur and not (cur & pub_snapshot):
                    r = alarms["PUB_TAKEOVER"].trigger(t)
                    if r:
                        emit(t, "PUB_TAKEOVER", r, "orig=%s cur=%s" % (sorted(pub_snapshot), sorted(cur)))
                elif cur & pub_snapshot:
                    d = alarms["PUB_TAKEOVER"].clear(t)
                    if d is not None:
                        evlog.write(f"{t:.2f} PUB_TAKEOVER RECOVERED\n")
        except Exception as e:
            evlog.write(f"{t:.2f} pub_poll_err {e}\n")
        # remind tick
        for k, fsm in alarms.items():
            w = fsm.tick(t)
            if w:
                evlog.write(f"{t:.2f} {k} {w} #{fsm.count}\n")
        rate.sleep()

    json.dump(state, open(os.path.join(a.out_dir, "odom_monitor_state.json"), "w"),
              ensure_ascii=False, indent=1)
    evlog.write("monitor_v1 exit\n")


if __name__ == "__main__":
    sys.exit(main())
