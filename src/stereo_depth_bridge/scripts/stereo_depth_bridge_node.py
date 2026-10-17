#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stereo_depth_bridge — sim-only stereo->depth bridge node (v6.2 §一).

Subscribes the ALIVE dynamic stereo pair (camera-type sensors survive in the
full production stack; the openni depth sensor dies ~1s after creation), runs
OpenCV SGBM, publishes 32FC1 metric depth for EGO-Planner grid_map.

RED LINE (v6.2 #19): sim-only component. Never enters the real-machine stack;
real D435 true-depth chain unaffected. World/SDF/VINS/PX4 zero-change.

Geometry (D435-aligned 2026-10-17, PREREG v1):
  fx=fy=387.5078  B=0.0493  (numDisparities=96 covers Z>=0.199m; 0.3m->63.68px)
Output in LEFT camera optical frame (X right / Y down / Z forward), stamp=left.

Pairing: nearest-stamp right frame within tol (measured offset distribution:
75% exact / p90 4ms / max 52ms -> tol 60ms). Skipped/unpaired frames counted.
"""
import numpy as np
import cv2
cv2.setNumThreads(4)   # v2: busy 28-core machine -> SGBM oversubscription degrades p95

# ------- pure core (unit-testable, no ROS imports above this line) -------
def make_sgbm(num_disparities=96, block_size=5, uniqueness=15,
              speckle_win=50, speckle_range=2, disp12maxdiff=1, mode_3way=True):
    # v3 tuning attempt#2: MODE_SGBM_3WAY (8ms vs 31ms HH at 4 threads on loaded box;
    # accuracy relmed 3.19% vs 2.77% HH on cL1 faces — box hard gate margin ~40x)
    return cv2.StereoSGBM_create(minDisparity=0,
                                 numDisparities=num_disparities,
                                 blockSize=block_size,
                                 uniquenessRatio=uniqueness,
                                 speckleWindowSize=speckle_win,
                                 speckleRange=speckle_range,
                                 disp12MaxDiff=disp12maxdiff,
                                 P1=8 * 1 * block_size * block_size,
                                 P2=32 * 1 * block_size * block_size,
                                 mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY if mode_3way else cv2.STEREO_SGBM_MODE_SGBM)

def texture_mask(gray, thresh=8.0, win=25):
    """v4 tuning#3: local-std gate — pixels in low-texture patches are unreliable for
    stereo matching (white box faces produced confident far-mismatches -> phantom map
    cells in the flight corridor, gate2d evidence). D435 confidence-filter analog."""
    g = gray.astype(np.float32)
    m1 = cv2.boxFilter(g, -1, (win, win), normalize=True)
    m2 = cv2.boxFilter(g * g, -1, (win, win), normalize=True)
    std = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    return std >= thresh

def compute_depth(left_gray, right_gray, fx=387.5078, baseline=0.0493, sgbm=None,
                  min_valid_disp=0.5, half_res=False, tex_thresh=8.0):
    """Return float32 depth map (meters); invalid pixels = 0.0."""
    if sgbm is None:
        sgbm = make_sgbm()
    if half_res:
        lg = cv2.resize(left_gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        rg = cv2.resize(right_gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    else:
        lg, rg = left_gray, right_gray
    disp = sgbm.compute(lg, rg).astype(np.float32) / 16.0
    valid = disp >= min_valid_disp
    depth = np.zeros(disp.shape, np.float32)
    fx_eff = fx * (0.5 if half_res else 1.0)
    depth[valid] = fx_eff * baseline / disp[valid]
    if half_res:
        out = cv2.resize(depth, (left_gray.shape[1], left_gray.shape[0]),
                         interpolation=cv2.INTER_NEAREST)
        out[out > 60.0] = 0.0
        out[~np.isfinite(out)] = 0.0
        if tex_thresh > 0:
            out[~texture_mask(left_gray, tex_thresh)] = 0.0
        return out
    depth[depth > 60.0] = 0.0
    depth[~np.isfinite(depth)] = 0.0
    if tex_thresh > 0:
        depth[~texture_mask(left_gray, tex_thresh)] = 0.0
    return depth

def msg_to_gray(msg):
    enc = msg.encoding
    if enc in ('rgb8', 'bgr8'):
        a = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        return cv2.cvtColor(a, cv2.COLOR_RGB2GRAY if enc == 'rgb8' else cv2.COLOR_BGR2GRAY)
    if enc == 'mono8':
        return np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width).copy()
    if enc == 'mono16':
        a = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width)
        return cv2.convertScaleAbs(a, alpha=0.25)
    raise ValueError('unsupported encoding %s' % enc)

# ------------------------------- ROS node -------------------------------
def main():
    import rospy, sys, threading, time, json
    from sensor_msgs.msg import Image, CameraInfo

    FX = rospy.get_param('~fx', 387.5078)
    BASELINE = rospy.get_param('~baseline', 0.0493)
    CX = rospy.get_param('~cx', 323.5014)
    CY = rospy.get_param('~cy', 232.6917)
    PAIR_TOL = rospy.get_param('~pair_tol_s', 0.060)
    HALF_RES = rospy.get_param('~half_res', False)
    NUMD = rospy.get_param('~num_disparities', 96)
    BLOCK = rospy.get_param('~block_size', 5)
    UNIQ = rospy.get_param('~uniqueness', 15)
    TEX_TH = rospy.get_param('~tex_thresh', 8.0)

    rospy.init_node('stereo_depth_bridge')
    pub = rospy.Publisher('/sdb/depth/image_raw', Image, queue_size=2)
    pub_ci = rospy.Publisher('/sdb/depth/camera_info', CameraInfo, queue_size=2, latch=True)

    sgbm = make_sgbm(NUMD, BLOCK, UNIQ)
    right_buf = []            # (stamp, msg) small ring
    lock = threading.Lock()
    busy = threading.Event()  # worker busy flag
    mail = []                 # handed-over pair
    stat = dict(left_in=0, right_in=0, paired=0, unpaired_drop=0, busy_drop=0, published=0,
                lat_wall_ms=[], lat_sim_ms=[], finite_ratio=[], last_depth_med=0.0)

    def on_ci(msg):
        ci = CameraInfo()
        ci.header = msg.header
        ci.height, ci.width = 480, 640
        ci.distortion_model = 'plumb_bob'
        ci.K = [FX, 0, CX, 0, FX, CY, 0, 0, 1]
        ci.R = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        ci.P = [FX, 0, CX, 0, 0, FX, CY, 0, 0, 0, 1, 0]
        pub_ci.publish(ci)
    rospy.Subscriber('/iris_stereo_vins/vins_cam_left/camera_info', CameraInfo, on_ci, queue_size=1)

    def worker():
        while not rospy.is_shutdown():
            if not mail:
                time.sleep(0.002)
                continue
            t_wall0 = time.time()
            ls, lmsg, rmsg = mail.pop(0)
            gl = msg_to_gray(lmsg)
            gr = msg_to_gray(rmsg)
            depth = compute_depth(gl, gr, FX, BASELINE, sgbm, half_res=HALF_RES, tex_thresh=TEX_TH)
            out = Image()
            out.header = lmsg.header
            out.height, out.width = depth.shape
            out.encoding = '32FC1'
            out.step = out.width * 4
            out.data = depth.tobytes()
            pub.publish(out)
            t_wall1 = time.time()
            try:
                lat_sim = (rospy.Time.now() - lmsg.header.stamp).to_sec() * 1000.0
            except Exception:
                lat_sim = float('nan')
            stat['published'] += 1
            stat['lat_wall_ms'].append((t_wall1 - t_wall0) * 1000.0)
            stat['lat_sim_ms'].append(lat_sim)
            fin = float(np.count_nonzero(depth > 0.0)) / depth.size
            stat['finite_ratio'].append(fin)
            stat['last_depth_med'] = float(np.median(depth[depth > 0])) if np.any(depth > 0) else 0.0
            busy.clear()

    pending = []   # v2 deferred pairing: lefts waiting for a right (arrival-order robust)

    def try_pair(ts, lmsg):
        # find best right within tol; on miss keep left pending (caller)
        with lock:
            best, bd = None, 1e9
            for s, m in right_buf:
                d = abs((s - ts).to_sec())
                if d < bd: bd, best = d, (s, m)
            if best is not None and bd <= PAIR_TOL:
                pair = (ts, lmsg, best[1])
            else:
                pair = None
        if pair is None:
            return False
        if busy.is_set():
            stat['busy_drop'] += 1
            return True   # pair existed; consumed as busy-drop
        stat['paired'] += 1
        busy.set()
        mail.append(pair)
        return True

    def on_left(msg):
        stat['left_in'] += 1
        if not try_pair(msg.header.stamp, msg):
            with lock:
                pending.append((msg.header.stamp, msg))
                while len(pending) > 3:
                    pending.pop(0)
                    stat['unpaired_drop'] += 1

    def on_right(msg):
        stat['right_in'] += 1
        with lock:
            right_buf.append((msg.header.stamp, msg))
            while len(right_buf) > 6:
                right_buf.pop(0)
            snap = list(pending)
        still = []
        for ts, lm in snap:
            if not try_pair(ts, lm):
                still.append((ts, lm))
        with lock:
            pending[:] = [x for x in pending if x not in snap] + [x for x in still if x not in pending]

    rospy.Subscriber('/iris_stereo_vins/vins_cam_left/image_raw', Image, on_left, queue_size=1, buff_size=2 ** 24)
    rospy.Subscriber('/iris_stereo_vins/vins_cam_right/image_raw', Image, on_right, queue_size=1, buff_size=2 ** 24)

    threading.Thread(target=worker, daemon=True).start()
    rate = rospy.Rate(0.2)
    while not rospy.is_shutdown():
        rate.sleep()
        lw = stat['lat_wall_ms'][-150:] if stat['lat_wall_ms'] else [0]
        ls = stat['lat_sim_ms'][-150:] if stat['lat_sim_ms'] else [0]
        fr = stat['finite_ratio'][-150:] if stat['finite_ratio'] else [0]
        drops = stat['unpaired_drop'] + stat['busy_drop']
        tot = max(stat['left_in'], 1)
        s = dict(n_left=stat['left_in'], n_pub=stat['published'], drop_unpaired=stat['unpaired_drop'],
                 drop_busy=stat['busy_drop'], drop_rate=round(drops / tot, 4),
                 lat_wall_p50=round(float(np.percentile(lw, 50)), 1), lat_wall_p95=round(float(np.percentile(lw, 95)), 1),
                 lat_sim_p50=round(float(np.nanpercentile(ls, 50)), 1), lat_sim_p95=round(float(np.nanpercentile(ls, 95)), 1),
                 finite_ratio_last=round(float(fr[-1]) if fr else 0, 3), finite_ratio_med=round(float(np.median(fr)), 3),
                 depth_med=round(stat['last_depth_med'], 2),
                 params=dict(fx=FX, B=BASELINE, numd=NUMD, block=BLOCK, uniq=UNIQ, half=HALF_RES, tex=TEX_TH))
        rospy.loginfo('[SDB-STAT] %s', json.dumps(s))

if __name__ == '__main__':
    main()
