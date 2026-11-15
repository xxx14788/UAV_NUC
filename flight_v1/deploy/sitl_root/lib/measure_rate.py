#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_rate.py — 多话题速率测量（header.stamp 为时基，附到达间隔）

用法:  measure_rate.py --window 8 /topic/a /topic/b
输出:  每话题一行
  topic=<t> rate=<hz> n=<n> span_s=<s> max_gap_ms=<ms> arrival_max_gap_ms=<ms> src=<stamp|arrival|absent|error>

为什么不用 `rostopic hz`:
  `rostopic hz` 用「回调到达时刻」算间隔，CPU 一忙（Python GIL/调度抖动）读数就系统性偏低
  —— 实测同一条 200Hz 的 /mavros/imu/data_raw 能读出 189.9Hz，而 header.stamp 的间隔是稳的。
  本工具优先用 header.stamp（= 数据真实产生率），并同时给出 max_gap_ms：
  成段丢包会在 max_gap 上立刻暴露，而到达抖动不会。

退出码恒 0（除参数错误）：话题缺失/测不到时也输出一行，让调用方按 src 判定。
"""
import argparse
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--window", type=float, default=3.0)
    p.add_argument("--resolve-timeout", type=float, default=3.0,
                   help="等 publisher 出现的最长秒数")
    p.add_argument("topics", nargs="+")
    a = p.parse_args()

    try:
        import rospy
        rospy.init_node("measure_rate", anonymous=True, disable_signals=True)
        from rostopic import get_topic_class
    except Exception as e:                                    # 无 master / 环境坏
        for t in a.topics:
            print("topic=%s rate=0 n=0 src=error" % t)
        print("# init failed: %s" % e, file=sys.stderr)
        return 0

    def published():
        try:
            return {t for t, _ in (rospy.get_published_topics() or [])}
        except Exception:
            return set()

    # 等 publisher 出现（最多 resolve-timeout 秒；不等也不会阻塞）
    pub = published()
    t0 = time.monotonic()
    while [t for t in a.topics if t not in pub] and (time.monotonic() - t0) < a.resolve_timeout:
        time.sleep(0.2)
        pub = published()

    types = {}
    for t in a.topics:
        types[t] = None
        if t in pub:
            try:
                res = get_topic_class(t, blocking=False)
                types[t] = res[0] if res else None
            except Exception:
                types[t] = None

    data = {t: {"st": [], "ar": []} for t in a.topics}

    def make_cb(topic):
        def cb(msg):
            d = data[topic]
            d["ar"].append(time.monotonic())
            h = getattr(msg, "header", None)
            st = None
            if h is not None and hasattr(h, "stamp"):
                try:
                    st = h.stamp.to_sec()
                except Exception:
                    st = None
            d["st"].append(st if st else float("nan"))
        return cb

    subs = []
    for t in a.topics:
        if types[t] is None:
            continue
        try:
            subs.append(rospy.Subscriber(t, types[t], make_cb(t), queue_size=1000))
        except Exception:
            types[t] = None

    time.sleep(a.window)

    for t in a.topics:
        d = data[t]
        n = len(d["ar"])
        if types[t] is None:
            print("topic=%s rate=0 n=%d src=%s" % (t, n, "error" if t in pub else "absent"))
            continue
        has_nan = any(x != x for x in d["st"])
        if n < 2:
            print("topic=%s rate=0 n=%d src=%s" % (t, n, "arrival" if has_nan else "stamp"))
            continue

        src = "stamp"
        if has_nan:
            src = "arrival"
        use = list(d["ar"]) if src == "arrival" else list(d["st"])
        span = use[-1] - use[0]
        if span <= 0:
            print("topic=%s rate=0 n=%d src=%s" % (t, n, src))
            continue
        gaps = [(use[i + 1] - use[i]) * 1000.0 for i in range(n - 1)]
        if src == "stamp" and min(gaps) < -1.0:               # 时戳乱序 → 回退到达时基
            src = "arrival"
            use = list(d["ar"])
            span = use[-1] - use[0]
            if span <= 0:
                print("topic=%s rate=0 n=%d src=%s" % (t, n, src))
                continue
            gaps = [(use[i + 1] - use[i]) * 1000.0 for i in range(n - 1)]
        agaps = [(d["ar"][i + 1] - d["ar"][i]) * 1000.0 for i in range(n - 1)]
        print("topic=%s rate=%.2f n=%d span_s=%.2f max_gap_ms=%.1f arrival_max_gap_ms=%.1f src=%s"
              % (t, (n - 1) / span, n, span, max(gaps), max(agaps), src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
