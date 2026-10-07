#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
t2_bag_editor.py -- T2 unit-3 input-edit replay tool (v1.1)

Taskbook: 2026-10-07_T2_vins_quality_v10.4.md unit 3.
Three edit modes (arms A/B/C of the input-face isolation experiment):
  retstamp : rewrite L/R image header stamps (align-to-same-stamp or known
             offset gradient +/- delta)                    -> arm A (td candidate)
  retiming : drop / reorder / downfreq image frames        -> arm B (render-timing candidate)
  repaint  : paint over regions of selected frames         -> arm C (content candidate)

Disk policy (taskbook mandate): PARAMETERIZED REGENERATION. The tool writes a
JSON manifest (src bag path+md5 + edit params + scope + guards + fingerprint);
edited bags are deleted after each run and can be regenerated 1:1 from the
manifest. Standing edited copies (13G x N) are FORBIDDEN.

Time windows are RELATIVE seconds from bag start (cross-domain absolute-stamp
trap: T2b poison-slot lesson -- never key edits off raw header domains).

Frozen semantics (preregistered in t2_results/INPUTFACE, do not change without
a new prereg entry):
  retstamp align=same   : tgt.header.stamp := nearest ref frame stamp
  retstamp align=offset : tgt.header.stamp := nearest ref stamp + delta_ms
  retiming reorder      : within each span of swap_window consecutive in-window
                          frames, frame k receives header stamp of frame k+1
                          (last receives first); bag-time t untouched
  retiming drop/downfreq: frames removed from the bag outright
  repaint               : normalized rect region, mode black|mean|noise(seed)

Runs on 3090 (rosbag/cv2 required; cv_bridge only for sensor_msgs/Image
repaint). On Windows hosts only `python -m py_compile` is expected to pass.

Exit codes: 0 ok | 2 dry-run found violations | 3 hard error.
All log output is ASCII (CN-printf-mojibake lesson).
"""

import argparse
import hashlib
import json
import os
import sys
import time

TOOL_NAME = "t2_bag_editor.py"
TOOL_VERSION = "1.1"

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def md5_of_file(path, chunk=1 << 22):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def edit_fingerprint(edit_spec, src_md5):
    payload = canonical_json({"edit": edit_spec, "src_md5": src_md5})
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def make_stamp(sec):
    """rospy Time from float seconds (Time.from_sec does not exist)."""
    from rospy.rostime import Time

    sec = float(sec)
    nsec = int(round((sec - int(sec)) * 1e9))
    if nsec >= 1000000000:
        nsec -= 1000000000
        sec += 1.0
    return Time(int(sec), nsec)


def disk_free(path):
    try:
        import shutil

        return shutil.disk_usage(os.path.dirname(path) or ".").free
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# domain scan (poison-slot guard)
# --------------------------------------------------------------------------- #


def scan_domains(bag_path):
    """Per-topic count + header-stamp domain vs bag-time domain.

    Exposes the classic 1.79e9 cross-domain split before any edit is applied.
    """
    import rosbag

    out = {}
    with rosbag.Bag(bag_path, "r") as bag:
        for topic, msg, t in bag.read_messages():
            rec = out.setdefault(
                topic,
                {
                    "count": 0,
                    "hdr_first": None,
                    "hdr_last": None,
                    "bag_first": t.to_sec(),
                    "bag_last": t.to_sec(),
                },
            )
            rec["count"] += 1
            rec["bag_last"] = t.to_sec()
            hdr = getattr(msg, "header", None)
            if hdr is not None:
                hs = hdr.stamp.to_sec()
                if rec["hdr_first"] is None:
                    rec["hdr_first"] = hs
                rec["hdr_last"] = hs
    for rec in out.values():
        if rec["hdr_first"] is not None:
            rec["hdr_minus_bag_first"] = rec["hdr_first"] - rec["bag_first"]
            rec["hdr_minus_bag_last"] = rec["hdr_last"] - rec["bag_last"]
    return out


def domain_check_pass(domains, warn_split=600.0):
    """Fail if any topic's header-vs-bag offset exceeds warn_split seconds."""
    worst = 0.0
    for rec in domains.values():
        for k in ("hdr_minus_bag_first", "hdr_minus_bag_last"):
            if k in rec:
                worst = max(worst, abs(rec[k]))
    return worst < warn_split, worst


# --------------------------------------------------------------------------- #
# arm A: retstamp plan
# --------------------------------------------------------------------------- #


class RetstampPlan(object):
    """Nearest-neighbour L/R stamp pairing from a first pass over ref topic."""

    def __init__(self, ref_topic, tgt_topic, align, delta_ms):
        self.ref_topic = ref_topic
        self.tgt_topic = tgt_topic
        self.align = align
        self.delta_s = delta_ms / 1000.0
        self.ref_stamps = []

    def first_pass(self, bag_path):
        import rosbag

        with rosbag.Bag(bag_path, "r") as bag:
            for _topic, msg, _t in bag.read_messages(topics=[self.ref_topic]):
                self.ref_stamps.append(msg.header.stamp.to_sec())
        self.ref_stamps.sort()

    def nearest_ref(self, t):
        arr = self.ref_stamps
        lo, hi = 0, len(arr) - 1
        if t <= arr[0]:
            return arr[0]
        if t >= arr[hi]:
            return arr[hi]
        while lo < hi:
            mid = (lo + hi) // 2
            if arr[mid] < t:
                lo = mid + 1
            else:
                hi = mid
        cand_a, cand_b = arr[lo - 1], arr[lo]
        return cand_a if (t - cand_a) <= (cand_b - t) else cand_b

    def new_stamp(self, t_ref):
        if self.align == "same":
            return t_ref
        return t_ref + self.delta_s


# --------------------------------------------------------------------------- #
# arm B: retiming frame plan
# --------------------------------------------------------------------------- #


class FrameSelector(object):
    """Deterministic per-topic in-window frame plan.

    Modes:
      drop-periodic : keep idx % drop_every != drop_every-1
      drop-random   : seeded bernoulli, keep if rnd >= drop_frac
      downfreq      : keep frames nearest a uniform target_hz grid
      reorder       : keep all; plan = list of span lengths (swap_window)
    """

    def __init__(self, op, drop_every=0, drop_frac=0.0, seed=0,
                 target_hz=0.0, swap_window=2):
        self.op = op
        self.drop_every = drop_every
        self.drop_frac = drop_frac
        self.seed = seed
        self.target_hz = target_hz
        self.swap_window = max(2, swap_window)

    def plan_for_count(self, stamps):
        """stamps: in-window header stamps per topic (arrival order).
        Returns keep list (bool) -- for reorder, all True."""
        n = len(stamps)
        if self.op == "reorder":
            return [True] * n
        import random

        rng = random.Random(self.seed)
        keep = []
        for i in range(n):
            if self.op == "drop-periodic":
                keep.append(i % self.drop_every != self.drop_every - 1)
            elif self.op == "drop-random":
                keep.append(rng.random() >= self.drop_frac)
            elif self.op == "downfreq":
                keep.append(False)
            else:
                keep.append(True)
        if self.op == "downfreq" and n:
            t0, t1 = stamps[0], stamps[-1]
            span = max(t1 - t0, 1e-9)
            nslots = max(1, int(span * self.target_hz))
            chosen = set()
            for k in range(nslots + 1):
                want = t0 + span * k / float(nslots)
                best, bd = None, None
                for i, s in enumerate(stamps):
                    d = abs(s - want)
                    if bd is None or d < bd:
                        best, bd = i, d
                if best is not None:
                    chosen.add(best)
            for i in range(n):
                keep[i] = i in chosen
        return keep


# --------------------------------------------------------------------------- #
# arm C: repaint
# --------------------------------------------------------------------------- #


class Repainter(object):
    """Paints a normalized rect region on selected in-window image frames."""

    def __init__(self, region, mode, seed):
        self.rx, self.ry, self.rw, self.rh = [float(v) for v in region]
        self.mode = mode
        self.seed = seed
        self.frames_touched = 0
        self._rng = None

    @property
    def rng(self):
        if self._rng is None:
            import random

            self._rng = random.Random(self.seed)
        return self._rng

    def apply(self, msg):
        kind = msg._type if hasattr(msg, "_type") else type(msg).__name__
        if "CompressedImage" in kind:
            return self._apply_compressed(msg)
        return self._apply_raw(msg)

    def _apply_raw(self, msg):
        from cv_bridge import cv_bridge

        bridge = cv_bridge.CvBridge()
        arr = bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        out = self._paint_array(arr)
        newmsg = bridge.cv2_to_imgmsg(out, encoding=msg.encoding)
        newmsg.header = msg.header
        return newmsg

    def _apply_compressed(self, msg):
        import cv2
        import numpy as np

        arr = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_COLOR)
        if arr is None:
            raise RuntimeError("compressed image decode failed")
        out = self._paint_array(arr)
        ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ok:
            raise RuntimeError("jpeg re-encode failed")
        msg.data = buf.tobytes()
        return msg

    def _paint_array(self, arr):
        import numpy as np

        h, w = arr.shape[0], arr.shape[1]
        x0 = max(0, min(int(self.rx * w), w - 1))
        y0 = max(0, min(int(self.ry * h), h - 1))
        x1 = min(w, max(x0 + 1, int((self.rx + self.rw) * w)))
        y1 = min(h, max(y0 + 1, int((self.ry + self.rh) * h)))
        roi = arr[y0:y1, x0:x1]
        if self.mode == "black":
            arr[y0:y1, x0:x1] = 0
        elif self.mode == "mean":
            arr[y0:y1, x0:x1] = roi.mean(axis=(0, 1)).astype(arr.dtype)
        elif self.mode == "noise":
            noise = np.array(
                [[self.rng.randint(0, 255) for _ in range(x1 - x0)]
                 for _ in range(y1 - y0)],
                dtype=arr.dtype,
            )
            if arr.ndim == 3:
                noise = np.stack([noise] * arr.shape[2], axis=-1)
            arr[y0:y1, x0:x1] = noise
        self.frames_touched += 1
        return arr


# --------------------------------------------------------------------------- #
# reorder buffering (per-topic FIFO of the current span)
# --------------------------------------------------------------------------- #


class ReorderBuffer(object):
    def __init__(self):
        self.buf = []       # list of (msg, bag_time)
        self.span_len = None
        self.spans_done = 0

    def set_span_len(self, n):
        self.span_len = n

    def full(self):
        return (self.span_len is not None
                and len(self.buf) >= self.span_len)


def _flush_slice(buf, rotate, bag_out, stats, last_written_stamp, topic):
    """Write one buffered span. rotate=True -> rotate header stamps by one."""
    msgs = list(buf)
    if rotate and len(msgs) >= 2:
        stamps = [m.header.stamp for m in msgs]
        for k in range(len(msgs)):
            msgs[k][0].header.stamp = stamps[(k + 1) % len(msgs)]
            stats["stamp_rewrites"] += 1
    for (m, tt) in msgs:
        _guard_monotonic(topic, m, last_written_stamp, stats, strict=False)
        if bag_out is not None:
            bag_out.write(topic, m, tt)
        stats["msg_written"] += 1
    del buf[:]


def _guard_monotonic(topic, msg, last_written_stamp, stats, strict):
    hs = msg.header.stamp.to_sec()
    last = last_written_stamp.get(topic)
    if last is not None and hs < last:
        stats["stamp_monotonic_violations"] += 1
        if strict:
            msg.header.stamp = make_stamp(last)
    last_written_stamp[topic] = msg.header.stamp.to_sec()


# --------------------------------------------------------------------------- #
# main edit pass
# --------------------------------------------------------------------------- #


def run_edit(args):
    import rosbag

    src = os.path.abspath(args.src)
    if args.out:
        out = os.path.abspath(args.out)
    else:
        out = os.path.join(
            os.path.dirname(src),
            os.path.basename(src)[:-4] + "_EDIT_%s.bag" % args.fingerprint_stub,
        )
    if src == out:
        print("[hard] out path must differ from src")
        return 3
    if not os.path.exists(src):
        print("[hard] src bag missing: %s" % src)
        return 3

    img_topics = [t.strip() for t in args.image_topics.split(",") if t.strip()]
    win = [args.win_start, args.win_end]  # relative seconds

    # ---- md5 (streaming, once) ----
    t_md5 = time.time()
    src_md5 = md5_of_file(src)
    print("[info] src md5 %s (%.1fs)" % (src_md5, time.time() - t_md5))

    # ---- pass 1: domain scan over ALL topics (poison guard) ----
    t0 = time.time()
    domains = scan_domains(src)
    dom_ok, dom_worst = domain_check_pass(domains)
    bag_times = [r["bag_first"] for r in domains.values()]
    bag_start = min(bag_times) if bag_times else 0.0
    bag_end = max(r["bag_last"] for r in domains.values())
    dur = bag_end - bag_start
    print("[info] pass1 domain scan: duration %.1fs topics=%d worst-offset "
          "%.3fs -> %s (%.1fs)"
          % (dur, len(domains), dom_worst,
             "PASS" if dom_ok else "FAIL", time.time() - t0))

    for t in img_topics:
        if t not in domains:
            print("[hard] image topic not in bag: %s (have: %s)"
                  % (t, ", ".join(sorted(domains.keys()))))
            return 3

    # ---- mode validation + first passes ----
    retstamp_plan = None
    selector = None
    repainter = None
    edit_spec = {"mode": args.mode}

    if args.mode == "retstamp":
        if args.stamp_target not in ("left", "right"):
            print("[hard] retstamp requires --stamp-target left|right")
            return 3
        if args.align == "offset" and args.delta_ms == 0.0:
            print("[hard] align=offset requires non-zero --delta-ms")
            return 3
        if args.stamp_target == "right":
            ref, tgt = args.left_topic, args.right_topic
        else:
            ref, tgt = args.right_topic, args.left_topic
        retstamp_plan = RetstampPlan(ref, tgt, args.align, args.delta_ms)
        t0 = time.time()
        retstamp_plan.first_pass(src)
        print("[info] retstamp ref scan: %d frames (%.1fs)"
              % (len(retstamp_plan.ref_stamps), time.time() - t0))
        edit_spec.update({
            "align": args.align,
            "delta_ms": args.delta_ms,
            "target": args.stamp_target,
            "ref_topic": ref,
            "tgt_topic": tgt,
        })
    elif args.mode == "retiming":
        if args.retiming_op is None:
            print("[hard] retiming requires --retiming-op")
            return 3
        if args.retiming_op == "drop-periodic" and args.drop_every < 2:
            print("[hard] drop-periodic requires --drop-every >= 2")
            return 3
        if args.retiming_op == "drop-random" and not (0.0 < args.drop_frac < 1.0):
            print("[hard] drop-random requires 0 < --drop-frac < 1")
            return 3
        if args.retiming_op == "downfreq" and args.target_hz <= 0:
            print("[hard] downfreq requires --target-hz > 0")
            return 3
        selector = FrameSelector(
            args.retiming_op, args.drop_every, args.drop_frac,
            args.seed, args.target_hz, args.swap_window)
        edit_spec.update({
            "op": args.retiming_op,
            "drop_every": args.drop_every,
            "drop_frac": args.drop_frac,
            "seed": args.seed,
            "target_hz": args.target_hz,
            "swap_window": args.swap_window,
        })
    elif args.mode == "repaint":
        if args.win_start >= args.win_end:
            print("[hard] repaint needs a bounded --win-start/--win-end")
            return 3
        repainter = Repainter(args.region, args.repaint_mode, args.seed)
        edit_spec.update({
            "region": list(args.region),
            "paint": args.repaint_mode,
            "seed": args.seed,
        })
    else:
        print("[hard] unknown mode %s" % args.mode)
        return 3

    scope = {
        "image_topics": img_topics,
        "window_rel_s": [win[0], (win[1] if win[1] < 1e17 else dur)],
        "window_abs_bagtime": [bag_start + win[0],
                               bag_start + (win[1] if win[1] < 1e17 else dur)],
    }

    # ---- pass 2 (retiming only): in-window stamp census per image topic ----
    plan_keep = {}
    swap_window = selector.swap_window if selector else 0
    if selector is not None:
        t0 = time.time()
        inwin_stamps = {t: [] for t in img_topics}
        with rosbag.Bag(src, "r") as bag:
            for topic, msg, t in bag.read_messages(topics=img_topics):
                rel = t.to_sec() - bag_start
                if win[0] <= rel <= win[1]:
                    inwin_stamps[topic].append(msg.header.stamp.to_sec())
        for topic, stamps in inwin_stamps.items():
            plan_keep[topic] = selector.plan_for_stamps(stamps)
        print("[info] retiming plan (%.1fs): kept %s of %s in-window"
              % (time.time() - t0,
                 {t: int(sum(plan_keep[t])) for t in plan_keep},
                 {t: len(plan_keep[t]) for t in plan_keep}))

    # ---- main pass: transform + write (or dry-run stats) ----
    stats = {
        "msg_total": 0,
        "msg_written": 0,
        "msg_dropped": 0,
        "frames_edited": 0,
        "stamp_rewrites": 0,
        "stamp_monotonic_violations": 0,
    }
    last_written_stamp = {}
    inwin_idx = {t: 0 for t in img_topics}
    rebuf = {t: ReorderBuffer() for t in img_topics}

    def in_window(t_sec):
        rel = t_sec - bag_start
        return win[0] <= rel <= win[1]

    bag_out = None
    if not args.dry_run:
        free = disk_free(out)
        src_size = os.path.getsize(src)
        if free is not None and free < src_size * 0.55:
            print("[hard] low disk at out dir: free=%.1fG need>=%.1fG"
                  % (free / 1e9, src_size * 0.55 / 1e9))
            return 3
        bag_out = rosbag.Bag(out, "w")

    try:
        with rosbag.Bag(src, "r") as bag:
            for topic, msg, t in bag.read_messages():
                stats["msg_total"] += 1

                if topic not in img_topics or not in_window(t.to_sec()):
                    if bag_out is not None:
                        bag_out.write(topic, msg, t)
                    stats["msg_written"] += 1
                    continue

                idx = inwin_idx[topic]
                inwin_idx[topic] += 1

                if selector is not None:
                    keep = plan_keep.get(topic, [])
                    if idx < len(keep) and not keep[idx]:
                        stats["msg_dropped"] += 1
                        continue
                    if selector.op == "reorder":
                        rb = rebuf[topic]
                        if rb.span_len is None or rb.spans_done > 0:
                            # start a fresh span: swap_window frames each
                            rb.buf = []
                            rb.span_len = min(swap_window,
                                              len(keep) - idx + len(rb.buf))
                            rb.spans_done = 0
                        rb.buf.append((msg, t))
                        if rb.full():
                            _flush_slice(rb.buf, rotate=True, bag_out=bag_out,
                                         stats=stats,
                                         last_written_stamp=last_written_stamp,
                                         topic=topic)
                            rb.spans_done += 1
                            rb.span_len = None
                            rb.buf = []
                        continue

                if repainter is not None:
                    msg = repainter.apply(msg)
                    stats["frames_edited"] += 1

                if (retstamp_plan is not None
                        and topic == retstamp_plan.tgt_topic):
                    t_ref = retstamp_plan.nearest_ref(
                        msg.header.stamp.to_sec())
                    msg.header.stamp = make_stamp(
                        retstamp_plan.new_stamp(t_ref))
                    stats["stamp_rewrites"] += 1

                _guard_monotonic(topic, msg, last_written_stamp, stats,
                                 strict=(args.mode != "retiming"))
                if bag_out is not None:
                    bag_out.write(topic, msg, t)
                stats["msg_written"] += 1

        # flush any trailing reorder leftovers
        for topic, rb in rebuf.items():
            if rb.buf:
                _flush_slice(rb.buf, rotate=(rb.span_len is not None
                                             and len(rb.buf) >= 2),
                             bag_out=bag_out, stats=stats,
                             last_written_stamp=last_written_stamp,
                             topic=topic)
                rb.buf = []
    finally:
        if bag_out is not None:
            bag_out.close()

    if args.dry_run:
        report = {
            "tool": TOOL_NAME,
            "version": TOOL_VERSION,
            "dry_run": True,
            "src_bag": {
                "path": src,
                "md5": src_md5,
                "size_bytes": os.path.getsize(src),
                "duration_s": dur,
            },
            "edit": edit_spec,
            "scope": scope,
            "domains": domains,
            "domain_check": "PASS" if dom_ok else "FAIL",
            "stats": stats,
        }
        print(json.dumps(report, indent=2, default=str))
        return 2 if (not dom_ok
                     or stats["stamp_monotonic_violations"]) else 0

    # ---- manifest ----
    fp = edit_fingerprint(edit_spec, src_md5)
    manifest = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "src_bag": {
            "path": src,
            "md5": src_md5,
            "size_bytes": os.path.getsize(src),
            "duration_s": dur,
        },
        "edit": edit_spec,
        "scope": scope,
        "stats": stats,
        "guards": {
            "domain_check": "PASS" if dom_ok else "FAIL",
            "stamp_monotonic_violations":
                stats["stamp_monotonic_violations"],
            "note": ("monotonic violations expected>0 ONLY for "
                     "retiming/reorder; retstamp/repaint must be 0"),
        },
        "edit_fingerprint": fp,
        "regen_cmd": ("%s --from-manifest MANIFEST.json --out %s"
                      % (TOOL_NAME, out)),
    }
    mpath = (out[:-4] + "_manifest.json" if out.endswith(".bag")
             else out + ".manifest.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print("[done] wrote %s (%d/%d msgs, drops=%d, edits=%d, rewrites=%d, "
          "mono-viol=%d)"
          % (out, stats["msg_written"], stats["msg_total"],
             stats["msg_dropped"], stats["frames_edited"],
             stats["stamp_rewrites"],
             stats["stamp_monotonic_violations"]))
    print("[done] manifest %s fingerprint=%s" % (mpath, fp))
    return 0


# --------------------------------------------------------------------------- #
# manifest regeneration
# --------------------------------------------------------------------------- #


def regen_from_manifest(mpath, out):
    with open(mpath) as f:
        m = json.load(f)
    if m.get("tool") != TOOL_NAME:
        print("[hard] manifest not produced by %s" % TOOL_NAME)
        return 3
    src = m["src_bag"]["path"]
    if not os.path.exists(src):
        print("[hard] src bag gone: %s" % src)
        return 3
    cur_md5 = md5_of_file(src)
    if cur_md5 != m["src_bag"]["md5"]:
        print("[hard] src bag md5 drift: manifest=%s now=%s -- refusing"
              % (m["src_bag"]["md5"], cur_md5))
        return 3
    e = m["edit"]
    scope = m["scope"]
    w = scope["window_rel_s"]
    argv = [src, out, "--mode", e["mode"],
            "--image-topics", ",".join(scope["image_topics"]),
            "--win-start", str(w[0]), "--win-end", str(w[1])]
    if e["mode"] == "retstamp":
        if e["target"] == "right":
            argv += ["--left-topic", e["ref_topic"],
                     "--right-topic", e["tgt_topic"]]
        else:
            argv += ["--left-topic", e["tgt_topic"],
                     "--right-topic", e["ref_topic"]]
        argv += ["--align", e["align"], "--delta-ms", str(e["delta_ms"]),
                 "--stamp-target", e["target"]]
    elif e["mode"] == "retiming":
        argv += ["--retiming-op", e["op"],
                 "--drop-every", str(e["drop_every"]),
                 "--drop-frac", str(e["drop_frac"]),
                 "--seed", str(e["seed"]),
                 "--target-hz", str(e["target_hz"]),
                 "--swap-window", str(e["swap_window"])]
    elif e["mode"] == "repaint":
        argv += ["--region", ",".join(str(v) for v in e["region"]),
                 "--repaint-mode", e["paint"], "--seed", str(e["seed"])]
    args = parse_args(argv)
    args.region = [float(v) for v in args.region] if args.region else args.region
    fp_old = m.get("edit_fingerprint")
    fp_new = edit_fingerprint(e, m["src_bag"]["md5"])
    if fp_old and fp_old != fp_new:
        print("[hard] fingerprint mismatch on regen (%s vs %s)"
              % (fp_old, fp_new))
        return 3
    return run_edit(args)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="T2 input-edit replay tool (arms A/B/C), "
                    "parameterized-regeneration disk policy")
    p.add_argument("src", nargs="?", help="source bag")
    p.add_argument("out", nargs="?", help="output edited bag (default: "
                                          "<src>_EDIT_<fp>.bag)")
    p.add_argument("--from-manifest", dest="from_manifest",
                   help="regenerate edited bag from a manifest json")
    p.add_argument("--mode", choices=["retstamp", "retiming", "repaint"],
                   default="retstamp")
    p.add_argument("--dry-run", action="store_true",
                   help="scan + validate + stats only, write nothing")
    # topics
    p.add_argument("--image-topics",
                   default="/camera/left/image_raw,/camera/right/image_raw",
                   help="comma list of image topics under edit scope")
    p.add_argument("--left-topic", default="/camera/left/image_raw")
    p.add_argument("--right-topic", default="/camera/right/image_raw")
    p.add_argument("--win-start", type=float, default=0.0,
                   help="edit window start, RELATIVE seconds from bag start")
    p.add_argument("--win-end", type=float, default=1e18,
                   help="edit window end, RELATIVE seconds")
    # arm A
    p.add_argument("--align", choices=["same", "offset"], default="same")
    p.add_argument("--delta-ms", type=float, default=0.0,
                   help="tgt := ref + delta (align=offset)")
    p.add_argument("--stamp-target", choices=["left", "right"],
                   default="right")
    # arm B
    p.add_argument("--retiming-op",
                   choices=["drop-periodic", "drop-random", "downfreq",
                            "reorder"])
    p.add_argument("--drop-every", type=int, default=0)
    p.add_argument("--drop-frac", type=float, default=0.0)
    p.add_argument("--target-hz", type=float, default=0.0)
    p.add_argument("--swap-window", type=int, default=2)
    p.add_argument("--seed", type=int, default=7)
    # arm C
    p.add_argument("--region", type=str, help="x,y,w,h normalized 0-1")
    p.add_argument("--repaint-mode", choices=["black", "mean", "noise"],
                   default="black")
    # misc
    p.add_argument("--fingerprint-stub", default="TMP")
    return p.parse_args(argv)


def main():
    args = parse_args()
    if args.from_manifest:
        if not args.out:
            print("[hard] --from-manifest needs positional out path")
            return 3
        return regen_from_manifest(args.from_manifest, args.out)
    if not args.src:
        print("[hard] positional src bag required")
        return 3
    if args.region:
        try:
            args.region = [float(v) for v in args.region.split(",")]
            if len(args.region) != 4:
                raise ValueError
        except ValueError:
            print("[hard] --region must be x,y,w,h floats")
            return 3
    else:
        args.region = [0.0, 0.0, 1.0, 1.0]
    return run_edit(args)


if __name__ == "__main__":
    sys.exit(main())
