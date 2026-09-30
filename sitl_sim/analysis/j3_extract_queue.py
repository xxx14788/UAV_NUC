#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4-J-R3① 批量提帧排队器（包装 j3_extract_frames.py，串行单路）.

设计约束（任务书 v4.0 J-R3 + E1 锁语义附录 + verdicts 事故记录 2）：
  - df 门: 可用空间 < --min-free-gb 时拒绝开新袋（20G 水位线为硬底，默认门 25G 留余量）
  - 空窗判定: pgrep rosbag 连续两次（间隔 --idle-gap 秒）计数均为 0 才动手
    （并发带图 IO 打死 NUC 前科，09-29/09-30 两案；大 IO 前 pgrep 双 0 铁律）
  - 断点续跑: 状态落 --state json；已完成袋以 out/manifest.json 存在为准，
    半途目录（无 manifest）自动清空重做；中断(SIGINT/异常)后直接重跑同一命令即续
  - 串行: 同一时刻最多一个提帧进程；本脚本自身只读 bag+写帧目录，零锁零飞行轮

用法:
  python3 j3_extract_queue.py --queue bags.txt --out-root ~/sitl_sim/vision_inputs/queue_j3 \
      [--topics /cam/left /cam/right] [--segments 3 --per-seg 12 --pairs]
  bags.txt 每行一个 bag 绝对路径（# 注释行忽略）；也可 --scan-dir DIR 自动发现
  DIR 下 run_*/flight.bag 中未完成的加入队尾。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTOR = os.path.join(HERE, 'j3_extract_frames.py')


def log(msg):
    print('[%s] %s' % (datetime.now().strftime('%m-%d %H:%M:%S'), msg), flush=True)


def df_free_gb(path):
    st = os.statvfs(os.path.dirname(path) or path)
    return st.f_bavail * st.f_frsize / (1024 ** 3)


def rosbag_count():
    """ps comm 精确计数真实 rosbag 进程.

    坑位(2026-10-01 夜两次实锤): pgrep -x 探不到 python 包装的 rosbag;
    pgrep -f 会被任何含"rosbag"字样的外层包装命令(bash -c/ssh 复合串)自命中毒计数。
    shebang 脚本进程的 comm=脚本名(rosbag), 包装 shell comm=bash, 天然免疫。
    """
    try:
        out = subprocess.run("ps -eo comm= | grep -cx rosbag", shell=True,
                             capture_output=True, text=True, timeout=10)
        s = out.stdout.strip()
        return int(s) if s.isdigit() else 0
    except Exception:
        return -1  # 探测失败按不空窗处理（宁可不跑）


def wait_idle_window(gap, tries=120):
    """rosbag 双 0 空窗：两次间隔 gap 秒均为 0；否则等待重试，最多 tries 轮。"""
    for i in range(tries):
        c1 = rosbag_count()
        if c1 == 0:
            time.sleep(gap)
            c2 = rosbag_count()
            if c2 == 0:
                return True
            log('空窗判定失败(第一次0,第二次%d)，等待重试 %d/%d' % (c2, i + 1, tries))
        else:
            log('rosbag 在飞(count=%d)，等待 %d/%d' % (c1, i + 1, tries))
            time.sleep(30)
    return False


def load_state(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {'bags': {}}


def save_state(path, st):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def bag_done(out_dir):
    return os.path.exists(os.path.join(out_dir, 'manifest.json'))


def extract_one(bag, out_dir, topics, segments, per_seg, pairs):
    if os.path.isdir(out_dir) and not bag_done(out_dir):
        log('  清理半途目录(无 manifest): %s' % out_dir)
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    cmd = [sys.executable, EXTRACTOR, '--bag', bag, '--out', out_dir]
    for t in topics:
        cmd += ['--topic', t]
    cmd += ['--segments', str(segments), '--per-seg', str(per_seg)]
    if pairs:
        cmd.append('--pairs')
    log('  RUN %s' % ' '.join(cmd))
    # 非交互 shell 无 ROS 环境: 显式 source(rosbag 模块在 noetic dist-packages)
    wrapped = ("source /opt/ros/noetic/setup.bash 2>/dev/null; "
               "source $HOME/catkin_ws/devel/setup.bash 2>/dev/null; "
               + ' '.join("'%s'" % c.replace("'", "'\\''") for c in cmd))
    r = subprocess.run(['bash', '-c', wrapped])
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--queue', help='bag 路径清单文件(每行一个)')
    ap.add_argument('--scan-dir', help='自动发现 run_*/flight.bag 未完成者入队尾')
    ap.add_argument('--out-root', required=True)
    ap.add_argument('--topics', nargs='+',
                    default=['/iris_stereo_vins/vins_cam_left/image_raw',
                             '/iris_stereo_vins/vins_cam_right/image_raw'])
    ap.add_argument('--segments', type=int, default=3)
    ap.add_argument('--per-seg', type=int, default=12)
    ap.add_argument('--pairs', action='store_true')
    ap.add_argument('--min-free-gb', type=float, default=25.0,
                    help='df 门(GB)；20G 为禁新轮硬水位，默认留余量')
    ap.add_argument('--idle-gap', type=float, default=5.0, help='rosbag 双检间隔秒')
    ap.add_argument('--state', default=None, help='状态文件(默认 out-root/queue_state.json)')
    ap.add_argument('--dry-run', action='store_true', help='只列队与判定，不提帧')
    args = ap.parse_args()

    if not args.queue and not args.scan_dir:
        ap.error('--queue 与 --scan-dir 至少给一个')

    state_path = args.state or os.path.join(args.out_root, 'queue_state.json')
    os.makedirs(args.out_root, exist_ok=True)
    st = load_state(state_path)
    st.setdefault('bags', {})

    # 组队：queue 文件顺序 + scan-dir 增量；已 done 的不再排
    bags = []
    if args.queue and os.path.exists(args.queue):
        with open(args.queue, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and os.path.exists(line):
                    bags.append(line)
                elif line and not line.startswith('#'):
                    log('警告: 队列文件条目不存在，跳过: %s' % line)
    if args.scan_dir:
        for name in sorted(os.listdir(args.scan_dir)):
            cand = os.path.join(args.scan_dir, name, 'flight.bag')
            if name.startswith('run_') and os.path.exists(cand) and cand not in bags:
                bags.append(cand)

    pending, done, skip = [], 0, 0
    for b in bags:
        out_dir = os.path.join(args.out_root, os.path.basename(os.path.dirname(b)) or 'bag')
        rec = st['bags'].get(b, {})
        if rec.get('status') == 'done' and bag_done(out_dir):
            done += 1
            continue
        pending.append((b, out_dir))
    log('组队完成: 共 %d 袋, 已完成 %d, 待跑 %d' % (len(bags), done, len(pending)))

    for b, out_dir in pending:
        tag = os.path.basename(os.path.dirname(b))
        free = df_free_gb(args.out_root)
        if free < args.min_free_gb:
            log('DF-GATE 拒绝: %s 可用 %.1fG < 门 %.1fG（袋 %s 挂起，重跑续）'
                % (args.out_root, free, args.min_free_gb, tag))
            st['bags'][b] = dict(st['bags'].get(b, {}), status='blocked-df',
                                 free_gb=round(free, 1),
                                 ts=datetime.now().isoformat(timespec='seconds'))
            save_state(state_path, st)
            continue
        if args.dry_run:
            log('DRY-RUN 会跑: %s (free %.1fG)' % (tag, free))
            skip += 1
            continue
        if not wait_idle_window(args.idle_gap):
            log('空窗等待超限，本轮停在 %s（重跑续）；已完成 %d 袋状态已落盘' % (tag, done))
            save_state(state_path, st)
            return 2
        log('[%d/%d] 开始: %s' % (done + 1, done + len(pending), tag))
        t0 = time.time()
        st['bags'][b] = dict(st['bags'].get(b, {}), status='running',
                             ts=datetime.now().isoformat(timespec='seconds'))
        save_state(state_path, st)
        rc = extract_one(b, out_dir, args.topics, args.segments, args.per_seg, args.pairs)
        dt = time.time() - t0
        if rc == 0 and bag_done(out_dir):
            st['bags'][b] = dict(st['bags'][b], status='done', rc=0,
                                 seconds=round(dt, 1),
                                 ts=datetime.now().isoformat(timespec='seconds'))
            done += 1
            log('  DONE %s (%.1fs)' % (tag, dt))
        else:
            st['bags'][b] = dict(st['bags'][b], status='fail', rc=rc,
                                 seconds=round(dt, 1),
                                 ts=datetime.now().isoformat(timespec='seconds'))
            log('  FAIL %s rc=%d (%.1fs)——继续下一袋' % (tag, rc, dt))
        save_state(state_path, st)

    n_fail = sum(1 for v in st['bags'].values() if v.get('status') == 'fail')
    n_block = sum(1 for v in st['bags'].values() if str(v.get('status', '')).startswith('blocked'))
    log('队列收口: done=%d fail=%d blocked-df=%d dry-run跳过=%d 状态=%s'
        % (done, n_fail, n_block, skip, state_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
