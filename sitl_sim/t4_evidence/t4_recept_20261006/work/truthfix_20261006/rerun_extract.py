#!/usr/bin/env python3
# T4-truthfix 2026-10-06: compact truth segment re-extract (evidence dir read-only)
# 口径: 与 v519 compact_extract.py 完全一致, 唯一差异=模型名匹配两值并集('iris' 或 'iris_stereo_vins');
# end_diff 口径不变 = 末帧 odom 采样 vs 末帧 truth 采样 (v519 原口径, 不改判读语义)
import sys, json, math
import rosbag

bag_path, out_json = sys.argv[1:3]
out = {'bag': bag_path, 'status': None, 'model_name_used': None,
       'truth_n': None, 'truth_dur_s': None, 'truth_pz_min': None, 'truth_pz_max': None,
       'odom_n': None, 'odom_last_xyz': None, 'truth_last_xyz': None,
       'end_diff_odom_vs_truth_m': None, 'err': None}
try:
    bag = rosbag.Bag(bag_path, 'r')
    odom = []; truth = []; name_used = None; has_ms = False
    for topic, msg, t in bag.read_messages(topics=['/vins_estimator/odometry', '/gazebo/model_states']):
        try:
            if topic == '/vins_estimator/odometry':
                p = msg.pose.pose.position
                odom.append((t.to_sec(), p.x, p.y, p.z))
            elif topic == '/gazebo/model_states':
                has_ms = True
                names = list(msg.name)
                i = None
                for cand in ('iris', 'iris_stereo_vins'):
                    if cand in names:
                        i = names.index(cand); break
                if i is not None:
                    name_used = names[i]
                    p = msg.pose[i].position
                    truth.append((t.to_sec(), p.x, p.y, p.z))
        except Exception:
            pass
    bag.close()
    out['odom_n'] = len(odom)
    out['model_name_used'] = name_used
    if not has_ms:
        out['status'] = 'NO_MODEL_STATES'
    elif not truth:
        out['status'] = 'NO_NAME_MATCH'
    elif not odom:
        out['status'] = 'NO_ODOM'
    else:
        o = odom[-1]; tr = truth[-1]
        out['status'] = 'OK'
        out['truth_n'] = len(truth)
        out['truth_dur_s'] = round(truth[-1][0] - truth[0][0], 3)
        zs = [a[3] for a in truth]
        out['truth_pz_min'] = round(min(zs), 4)
        out['truth_pz_max'] = round(max(zs), 4)
        out['odom_last_xyz'] = [round(o[1], 4), round(o[2], 4), round(o[3], 4)]
        out['truth_last_xyz'] = [round(tr[1], 4), round(tr[2], 4), round(tr[3], 4)]
        out['end_diff_odom_vs_truth_m'] = round(math.sqrt((o[1]-tr[1])**2 + (o[2]-tr[2])**2 + (o[3]-tr[3])**2), 4)
except Exception as e:
    out['status'] = 'READ_ERR'
    out['err'] = repr(e)[:200]
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('RR_DONE %s ed=%s' % (out['status'], out['end_diff_odom_vs_truth_m']))
