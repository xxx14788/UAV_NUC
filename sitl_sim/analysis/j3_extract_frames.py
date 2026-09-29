#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4-J3 (C09-E2) 分层提帧 + bag 口径落账.

从 rosbag 分段均匀提取图像帧（--pairs 同时保存每选中帧的紧邻下一帧 _next，
供 D12 时序差分与时序/立体 FB 残差分析），落 manifest.json：
帧清单 + camera_info 摘要 + 传感器 property（代位物口径登记，CF-2 前置步）。

用法:
  python3 j3_extract_frames.py --bag X.bag --topic /cam/left --topic /cam/right \
      --out frames_dir [--segments 3 --per-seg 12 --pairs]
"""
import argparse
import json
import os

import cv2
import numpy as np
import rosbag

ENC_MAP = {
    'mono8': (np.uint8, 1), '8UC1': (np.uint8, 1), 'Y8': (np.uint8, 1),
    'bgr8': (np.uint8, 3), 'rgb8': (np.uint8, 3), '8UC3': (np.uint8, 3),
    '16UC1': (np.uint16, 1), 'mono16': (np.uint16, 1), '32FC1': (np.float32, 1),
}


def img_to_array(msg):
    dt, ch = ENC_MAP[msg.encoding]
    if msg.is_bigendian:
        dt = dt.newbyteorder('>')
    arr = np.frombuffer(msg.data, dtype=dt)
    if arr.size != msg.width * msg.height * ch:
        raise ValueError('size mismatch %s: %d != %d' % (
            msg.encoding, arr.size, msg.width * msg.height * ch))
    return arr.reshape(msg.height, msg.width, ch) if ch > 1 else arr.reshape(msg.height, msg.width)


def to_gray8(arr):
    if arr.dtype == np.uint16:
        return cv2.convertScaleAbs(arr, alpha=0.05)
    if arr.dtype != np.uint8:
        arr = cv2.convertScaleAbs(arr)
    if arr.ndim == 3:
        return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY if arr.shape[2] == 3 else cv2.COLOR_BGR2GRAY)
    return arr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bag', required=True)
    ap.add_argument('--topic', action='append', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--segments', type=int, default=3)
    ap.add_argument('--per-seg', type=int, default=12)
    ap.add_argument('--pairs', action='store_true')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    bag = rosbag.Bag(args.bag, 'r')

    # pass 1: 时间戳与元数据（样张 bag 头戳可为 0，用接收时间排序）
    stamps = {t: [] for t in args.topic}
    cam_info, props = {}, []
    t_min = t_max = None
    for topic, msg, t_rec in bag.read_messages():
        if topic in stamps:
            ts = t_rec.to_sec()
            stamps[topic].append(ts)
            t_min = ts if t_min is None else min(t_min, ts)
            t_max = ts if t_max is None else max(t_max, ts)
        elif topic.endswith('/camera_info') and topic not in cam_info:
            cam_info[topic] = {
                'size': [msg.width, msg.height],
                'fx': round(msg.K[0], 3), 'fy': round(msg.K[4], 3),
                'cx': round(msg.K[2], 3), 'cy': round(msg.K[5], 3),
                'D': [round(d, 6) for d in msg.D[:5]],
                'model': msg.distortion_model,
            }
        elif topic.endswith('/property'):
            props.append({'key': msg.key, 'value': msg.value})

    manifest = {
        'bag': os.path.abspath(args.bag), 'topics': args.topic,
        't_range': [t_min, t_max], 'duration_s': round(t_max - t_min, 3),
        'msg_counts': {t: len(v) for t, v in stamps.items()},
        'camera_info': cam_info, 'sensor_property': props, 'frames': [],
    }

    # pass 2: 选帧（每段均匀 per-seg 个选中帧；pairs 时并入其紧邻下一帧）
    span = t_max - t_min
    seg_bounds = [t_min + span * i / args.segments for i in range(args.segments + 1)]
    short_of = {t: ('L%d' % i if len(args.topic) > 1 else 'M') for i, t in enumerate(args.topic)}
    want = {}   # ts -> (topic, seq_no, tag)  seq_no 按选中帧编号, next 帧继承
    for t in args.topic:
        ss = sorted(stamps[t])
        nxt = {ss[i]: ss[i + 1] for i in range(len(ss) - 1)}
        k = 0
        for si in range(args.segments):
            lo, hi = seg_bounds[si], seg_bounds[si + 1]
            in_seg = [x for x in ss if lo <= x < hi]
            if not in_seg:
                continue
            idx = np.unique(np.linspace(0, len(in_seg) - 1, args.per_seg).astype(int))
            for j in idx:
                sel = in_seg[j]
                k += 1
                want[sel] = (t, k, '')
                if args.pairs and sel in nxt:
                    want[nxt[sel]] = (t, k, '_next')

    # pass 3: 写 PNG
    for topic, msg, t_rec in bag.read_messages(topics=args.topic):
        ts = t_rec.to_sec()
        if ts not in want:
            continue
        t, k, tag = want[ts]
        if t != topic:
            continue
        gray = to_gray8(img_to_array(msg))
        si = args.segments - 1
        for i in range(args.segments):
            if seg_bounds[i] <= ts < seg_bounds[i + 1]:
                si = i
                break
        fn = '%s_%s_s%d_%04d%s.png' % (
            os.path.splitext(os.path.basename(args.bag))[0],
            short_of[t], si, k, tag)
        cv2.imwrite(os.path.join(args.out, fn), gray)
        manifest['frames'].append({
            'file': fn, 'topic': topic, 't_rec': round(ts, 4), 'seg': si,
            'tag': tag.strip('_'), 'size': [gray.shape[1], gray.shape[0]],
        })
    bag.close()
    manifest['frames'].sort(key=lambda f: (f['topic'], f['t_rec']))
    with open(os.path.join(args.out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print('frames:', len(manifest['frames']))
    print('camera_info:', json.dumps(cam_info))
    print('property:', json.dumps(props[:16]))


if __name__ == '__main__':
    main()
