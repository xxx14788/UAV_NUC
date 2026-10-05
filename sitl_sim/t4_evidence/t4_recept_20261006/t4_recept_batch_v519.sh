#!/bin/bash
# =============================================================================
# t4_recept_batch_v519.sh -- T4 v5.19 backlog reception batch (3090-localized)
# 2026-10-06
#
# Design (disconnect-tolerant):
#   - launch: setsid nohup bash t4_recept_batch_v519.sh </dev/null >nohup.log 2>&1 &
#   - all state persisted on 3090: chain.log / summary.json / perbag/ / judging_draft.md
#   - orchestrator only short-connection tail/poll; no batch state held across ssh
#   - idempotent: perbag/<run>.done marker -> bag skipped on rerun
#
# Red lines honored:
#   - judging rows are DRAFTS ONLY; no PASS/FAIL; no three-state outside cohort
#   - sigma only P25; quantiles+CI+n quoted verbatim from tool outputs
#   - no invented thresholds; 0.79-1.10m band cited as draft material (T3 anchor v1.4)
#   - tool md5 verified before use; mismatch -> hard stop
#   - IO mutex before replay/extract/d9: rosbag/gzserver/px4 three-zero + T1
#     batch-report mtime gate, up to 40 min, then DEFER to retry queue (never force)
#   - df < 25G -> whole-script stop
#
# Usage: bash t4_recept_batch_v519.sh [--dry]
#   --dry : inventory (rosbag info classification) + leg plan only; no legs.
# =============================================================================

EV=/home/ghj/catkin_ws/sitl_sim/t4_evidence/t4_recept_20261006
VS=/home/ghj/sitl_sim/vins_smoke_runs
BAGS=/home/ghj/sitl_sim/bags
VIN=/home/ghj/sitl_sim/vision_inputs
A=/home/ghj/catkin_ws/sitl_sim/analysis
T1EV=/home/ghj/catkin_ws/sitl_sim/t1_evidence
CFG_E01=/home/ghj/sitl_sim/t2_configs/E01_baseline/sim_stereo_imu_config.yaml
CFG_W1REF=/home/ghj/catkin_ws/src/VINS-Fusion/config/sim_stereo/e2_debug_smooth.yaml
VINS_NODE=/home/ghj/catkin_ws/devel/lib/vins/vins_node
VINS_LIB=/home/ghj/catkin_ws/devel/.private/vins/lib/libvins_lib.so

LOG=$EV/chain.log
WORK=$EV/work
PERBAG=$EV/perbag
LIB=$EV/lib
DRAFT=$EV/judging_draft.md
PLAN=$EV/plan.txt
PIDFILE=$EV/batch.pid

RECEIVED12="run_T2MACH1_010832 run_T2MACH2_011343 run_T2MACH3_011804 run_T2MACH4_012523 run_T2MACH5_013233 run_T2MACH6_013944 run_T2MACH7_014657 run_T2MACH8_015411 run_T2MACH9_020133 run_T2MACH10_020846 run_T2MACH11_021559 run_T2MACH12_022312"
HOV_BAG=$BAGS/run_t4w1_hov134845/flight.bag
HOV_BAG_ALT=$BAGS/t2v3_hover_134845.bag
GATE_MAX_SEC=2400
GATE_POLL=60
DF_MIN=25

DRY=0
[ "${1:-}" = "--dry" ] && DRY=1

mkdir -p "$EV" "$PERBAG" "$WORK/baginfo" "$LIB"
export PYTHONIOENCODING=utf-8
# main-context ROS (python legs import rosbag; house pattern: source before set -u)
set +u; source /opt/ros/noetic/setup.bash >/dev/null 2>&1; source /home/ghj/catkin_ws/devel/setup.bash >/dev/null 2>&1; set -u

say(){ echo "[$(date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }
dfg(){ df --output=avail -BG /home/ghj | tail -1 | tr -dc '0-9'; }
t1busy(){ find "$T1EV" -name x4_batch_report.md -mmin -10 2>/dev/null | grep -q .; }

# ---------------------------------------------------------------- sanity ----
fatal_exit(){ # $1=reason
  say "FATAL $1 -> stop before heavy work"
  if [ "$DRY" = 0 ]; then
    python3 - "$EV" "$1" <<'PYEOF'
import sys, json, os, time
ev, why = sys.argv[1], sys.argv[2]
json.dump({"script":"t4_recept_batch_v519.sh","batch_complete":False,"fatal":why,
           "updated_at":time.strftime('%F %T')},
          open(os.path.join(ev,'summary.json'),'w',encoding='utf-8'))
PYEOF
  fi
  exit 2
}

md5_tool_fail=0
for t in j3_extract_frames.py j3_feature_density.py j3_image_metrics.py j3_fb_residual.py; do
  m=$(md5sum "$A/$t" 2>/dev/null | cut -c1-8)
  say "TOOL_MD5 $t $m"
  case "$t" in
    j3_extract_frames.py)  e=18a71153 ;;
    j3_feature_density.py) e=7f45974b ;;
    j3_image_metrics.py)   e=3721399e ;;
    j3_fb_residual.py)     e=08cb8829 ;;
  esac
  if [ "$m" != "$e" ]; then say "TOOL_MD5_MISMATCH $t got=$m expect=$e"; md5_tool_fail=1; fi
done
[ "$md5_tool_fail" = 1 ] && fatal_exit "tool_md5_mismatch"
say "TOOL_MD5_ALL_MATCH"

[ -f "$CFG_E01" ] || fatal_exit "E01_baseline config missing: $CFG_E01"
say "CONFIG_E01 $(md5sum "$CFG_E01" 2>&1)"
say "CONFIG_W1REF $(md5sum "$CFG_W1REF" 2>/dev/null | cut -d' ' -f1) (W1 chain used this one; v5.19 spec says E01_baseline -> difference recorded per bag)"
say "VINS_NODE $(md5sum "$VINS_NODE" 2>&1)"
say "VINS_LIB $(md5sum "$VINS_LIB" 2>&1)"
say "PREREG_BOOK $(md5sum /home/ghj/catkin_ws/docs/t4_smooth_lie_prereg.md 2>&1)"

# ---------------------------------------------------------------- python lib -
cat > "$LIB/compact_extract.py" <<'PYEOF'
#!/usr/bin/env python3
# compact bag mechanical face: three sources (vins odom / mavros local_position / gazebo truth iris)
import sys, json, math
import rosbag

bag_path, out_json, draft, run, j0d, received = sys.argv[1:7]
bag = rosbag.Bag(bag_path, 'r')
t0b = bag.get_start_time(); t1b = bag.get_end_time()

sel = []
try:
    ti = bag.get_type_and_topic_info()
    for tn, info in ti.topics.items():
        if info.msg_count > 0 and (tn == '/vins_estimator/odometry'
                                   or tn.startswith('/mavros/local_position')
                                   or tn == '/gazebo/model_states'):
            sel.append(tn)
except Exception:
    pass

SRC = {'odom': [], 'mavros': [], 'truth': []}
for topic, msg, t in bag.read_messages(topics=sel):
    try:
        if topic == '/vins_estimator/odometry':
            p = msg.pose.pose.position; SRC['odom'].append((t.to_sec(), p.x, p.y, p.z))
        elif topic.startswith('/mavros/local_position'):
            p = msg.pose.pose.position; SRC['mavros'].append((t.to_sec(), p.x, p.y, p.z))
        elif topic == '/gazebo/model_states':
            if hasattr(msg, 'name') and 'iris' in list(msg.name):
                i = list(msg.name).index('iris'); p = msg.pose[i].position
                SRC['truth'].append((t.to_sec(), p.x, p.y, p.z))
    except Exception:
        pass
bag.close()

def stats(arr):
    if not arr:
        return None
    n = len(arr); z = [a[3] for a in arr]
    jumps = 0; jmax = 0.0
    for a, b in zip(arr, arr[1:]):
        d = math.sqrt((a[1]-b[1])**2 + (a[2]-b[2])**2 + (a[3]-b[3])**2)
        if d > 0.5: jumps += 1
        if d > jmax: jmax = d
    return {'n': n, 'dur_s': round(arr[-1][0]-arr[0][0], 3),
            'z_min': round(min(z), 4), 'z_max': round(max(z), 4),
            'jump_cnt_gt05m': jumps, 'jump_max_m': round(jmax, 4)}

res = {'run': run, 'bag': bag_path, 'bag_dur_s': round(t1b-t0b, 3), 'received': int(received),
       'sources': {k: stats(v) for k, v in SRC.items()}}
if SRC['odom'] and SRC['truth']:
    o = SRC['odom'][-1]; tr = SRC['truth'][-1]
    res['end_diff_odom_vs_truth_m'] = round(math.sqrt((o[1]-tr[1])**2 + (o[2]-tr[2])**2 + (o[3]-tr[3])**2), 4)
else:
    res['end_diff_odom_vs_truth_m'] = None
res['j0d_ref'] = j0d if j0d else 'T3 工具产出后增列'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

d = res['sources']
ed = res['end_diff_odom_vs_truth_m']
if ed is None:
    flavor = '末端位置差不可得(源缺失)——素材缺失·如实登记'
elif ed > 1.10:
    flavor = '超健康带上界(>1.10m)=爆型 A 域素材'
elif ed >= 0.79:
    flavor = '落健康带 0.79-1.10m=精度地板 C 域素材'
else:
    flavor = '健康带下(<0.79m)=两味素材之外(素材中性)'
lines = []
lines.append('')
lines.append('## [COMPACT] %s — 草稿·待主会话定稿' % run)
rcv = ' | received=1(W1 收货集 MACH-compact, v5.19 补判读行)' if received == '1' else ''
lines.append('- 分类: ③紧凑零图像%s | 第五坑登记: EX-FAIL 零图像(W1 挂账, v5.19 本批补 odom/truth 机械面)' % rcv)
def fmt(s, k):
    return s[k] if s else '-'
lines.append('- 数据段(perbag/%s.json): bag时长%.1fs | odom n=%s dur=%ss pz=[%s,%s] | mavros n=%s pz=[%s,%s] | truth n=%s pz=[%s,%s]' % (
    run, res['bag_dur_s'],
    fmt(d['odom'], 'n'), fmt(d['odom'], 'dur_s'), fmt(d['odom'], 'z_min'), fmt(d['odom'], 'z_max'),
    fmt(d['mavros'], 'n'), fmt(d['mavros'], 'z_min'), fmt(d['mavros'], 'z_max'),
    fmt(d['truth'], 'n'), fmt(d['truth'], 'z_min'), fmt(d['truth'], 'z_max')))
lines.append('- 末端位置差 odom-vs-truth = %s m' % (('%.4f' % ed) if ed is not None else 'N/A'))
lines.append('- jump 普查(|dP|>0.5m, 相邻样本): odom cnt=%s max=%sm | truth cnt=%s max=%sm' % (
    fmt(d['odom'], 'jump_cnt_gt05m'), fmt(d['odom'], 'jump_max_m'),
    fmt(d['truth'], 'jump_cnt_gt05m'), fmt(d['truth'], 'jump_max_m')))
lines.append('- j0d 引用: %s%s' % (j0d if j0d else 'T3 工具产出后增列', ' (在册即引·不代判)' if j0d else ''))
lines.append('- FAIL 两味素材: 末端漂移 %s 对照健康带 0.79-1.10 m (T3 anchor v1.4 修正口径: t3_anchor_survey_v1.csv + round_result v1.4=c708151f) -> %s (草稿素材·主会话定标)' % (
    (('%.4f m' % ed) if ed is not None else 'N/A'), flavor))
lines.append('- 受控注记: cohort 外袋不出三态——本行不构成三态判定; 数值面=极值/普查+n, 无单帧结论')
with open(draft, 'a', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('COMPACT_DONE %s end_diff=%s' % (run, ed))
PYEOF

cat > "$LIB/freeze_d9.py" <<'PYEOF'
#!/usr/bin/env python3
# D9: freeze window = continuous spans with odom z > 5.0 m (prereg book sec.2, mechanical, no min length)
import sys, json
import rosbag

bag_path, manifest_json, metrics_json, out_json, draft, run = sys.argv[1:7]

bag = rosbag.Bag(bag_path, 'r')
zseries = []
for topic, msg, t in bag.read_messages(topics=['/vins_estimator/odometry']):
    zseries.append((t.to_sec(), msg.pose.pose.position.z))
bag.close()

windows = []
cur = None
for t, z in zseries:
    if z > 5.0:
        if cur is None:
            cur = [t, t, 1]
        else:
            cur[1] = t; cur[2] += 1
    else:
        if cur is not None:
            windows.append(cur); cur = None
if cur is not None:
    windows.append(cur)
wins = [{'t0': round(w[0], 3), 't1': round(w[1], 3), 'n_samples': w[2], 'len_s': round(w[1]-w[0], 3)} for w in windows]
out = {'run': run, 'freeze_windows': wins, 'n_windows': len(wins)}

if not wins:
    out['d9'] = 'no_freeze_window -> skip (如实注记)'
    json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(draft, 'a', encoding='utf-8') as f:
        f.write('- D9 扩样腿: 无冻结窗(odom_z>5.0m 零窗) -> 跳过(如实注记, 判据册 §2 口径)\n')
    print('D9_NOWINDOW %s' % run)
    sys.exit(0)

man = json.load(open(manifest_json, encoding='utf-8'))
trec = {}
for fr in man.get('frames', []):
    fn = fr.get('file') or fr.get('fname') or fr.get('name') or fr.get('path')
    tt = fr.get('t_rec', fr.get('t'))
    if fn and tt is not None:
        trec[fn] = float(tt)

met = json.load(open(metrics_json, encoding='utf-8'))
pf = met.get('per_frame', [])
if not isinstance(pf, list) or not pf:
    out['d9'] = 'per_frame_missing -> frozen subset not computable (如实注记)'
    json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(draft, 'a', encoding='utf-8') as f:
        f.write('- D9 扩样腿: 冻结窗检出但 metrics 无 per_frame -> 冻结子集重算不可行(如实注记)\n')
    print('D9_NOPF %s' % run)
    sys.exit(0)

def inwin(t):
    return any(w[0] <= t <= w[1] for w in windows)

MET6 = ['supply_frac', 'grid4x4_occupancy_frac', 'd12_sigma_p25', 'd12_sigma_flat', 'med_gray', 'corners_gFT']
frozen = {m: [] for m in MET6}
outside = {m: [] for m in MET6}
n_in = 0; n_out = 0; n_unmapped = 0
for row in pf:
    fn = row.get('file') or row.get('path')
    t = trec.get(fn) if fn else None
    if t is None:
        n_unmapped += 1; continue
    if inwin(t):
        n_in += 1; tgt = frozen
    else:
        n_out += 1; tgt = outside
    for m in MET6:
        v = row.get(m)
        if isinstance(v, (int, float)):
            tgt[m].append(float(v))

import numpy as np
def q(v):
    if not v:
        return None
    a = np.array(v)
    return {'n': len(v), 'p10': round(float(np.percentile(a, 10)), 4),
            'p50': round(float(np.percentile(a, 50)), 4), 'p90': round(float(np.percentile(a, 90)), 4)}

out['d9'] = 'freeze_subset_recomputed'
out['frames_in_window'] = n_in
out['frames_outside'] = n_out
out['frames_unmapped'] = n_unmapped
out['frozen_subset'] = {m: q(frozen[m]) for m in MET6}
out['outside_subset'] = {m: q(outside[m]) for m in MET6}
json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

lines = ['', '### [D9 扩样行] %s — 草稿·待主会话定稿' % run]
lines.append('- 冻结窗(odom_z>5.0m 连续窗, 判据册 §2 机械判定): %d 窗, 窗长(s)=%s, 帧归属 in=%d out=%d unmapped=%d' % (
    len(wins), ','.join(str(w['len_s']) for w in wins[:8]), n_in, n_out, n_unmapped))
lines.append('- 六指标冻结子集(分位+n, 无CI=草稿素材): ' + '; '.join(
    '%s: n=%s p50=%s' % (m, (out['frozen_subset'][m] or {}).get('n'), (out['frozen_subset'][m] or {}).get('p50'))
    for m in MET6))
lines.append('- n 扩样口径: 基线 n_primary=%s -> 冻结子集 n=%d(窗内帧); 窗外子集另报(outside_subset)' % (
    met.get('n_primary'), n_in))
lines.append('- 受控注记: 扩样行=数据段草稿, 不构成三态判定')
with open(draft, 'a', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('D9_WINDOW %s wins=%d in=%d' % (run, len(wins), n_in))
PYEOF

cat > "$LIB/render_image_row.py" <<'PYEOF'
#!/usr/bin/env python3
import sys, json

run, received, cls, draft, metrics_json, fbres_json, d9_json, topics_l, topics_r, cfg_note = sys.argv[1:11]

def load(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return None

met = load(metrics_json); fb = load(fbres_json); d9 = load(d9_json)
lines = []
lines.append('')
lines.append('## [IMAGE%s] %s — 草稿·待主会话定稿' % ('-RECEIVED-VERIFY' if received == '1' else '', run))
lines.append('- 分类: %s | 双目话题 L=%s R=%s' % (cls, topics_l or '-', topics_r or '-'))
if received == '1':
    lines.append('- W1 收货集在册(I 章): 本行仅核对台账族在位, 不重链不代判')
if met:
    M = met.get('metrics', {})
    def row(key, label):
        v = M.get(key)
        if not isinstance(v, dict):
            return '- %s(%s): 缺(如实登记)' % (label, key)
        return '- %s(%s): p10=%s p50=%s p90=%s n=%s p90_ci=%s med_ci=%s' % (
            label, key, v.get('p10'), v.get('p50'), v.get('p90'), v.get('n'), v.get('p90_ci'), v.get('med_ci'))
    lines.append(row('supply_frac', 'M1 supply_frac'))
    lines.append(row('grid4x4_occupancy_frac', 'M2 grid4x4_occupancy_frac'))
    lines.append(row('d12_sigma_p25', 'sigma_hat P25 (d12_sigma_p25)'))
    lines.append(row('med_gray', 'med_gray'))
    lines.append('- 数值口径: 工具输出分位+CI+n 原样引用(sigma 只认 P25); n_primary=%s' % met.get('n_primary'))
else:
    lines.append('- metrics JSON 缺失/不可读 -> 指标面缺失(如实登记)')
if fb:
    for pool in ('temporal', 'stereo'):
        arr = fb.get(pool, [])
        if isinstance(arr, list):
            for e in arr:
                if isinstance(e, dict) and 'label' in e:
                    lines.append('- FB %s: label=%s n=%s p50=%s p90=%s p95=%s p90_ci=%s' % (
                        pool, e.get('label'), e.get('n'), e.get('p50'), e.get('p90'), e.get('p95'), e.get('p90_ci')))
else:
    lines.append('- fbres JSON 缺失/不可读 -> FB 残差面缺失(如实登记)')
if d9:
    lines.append('- D9 扩样腿: %s (详见 perbag/%s.d9.json)' % (d9.get('d9'), run))
else:
    lines.append('- D9 扩样腿: 未产出(如实登记)')
lines.append('- config 注记: %s' % cfg_note)
lines.append('- 域外注记: cohort 外袋不出三态——本行不构成三态判定 (H/I 章先例)')
lines.append('- 受控注记: 任一门拦截+完整恢复=受控失败; 门/腿 rc 记录见 chain.log 与 perbag json')
with open(draft, 'a', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('ROW_DONE %s' % run)
PYEOF

cat > "$LIB/upd.py" <<'PYEOF'
#!/usr/bin/env python3
import sys, json, time
path, patch = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path, encoding='utf-8'))
except Exception:
    d = {}
p = json.loads(patch)
def merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            merge(a[k], v)
        else:
            a[k] = v
merge(d, p)
d['updated_at'] = time.strftime('%F %T')
json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
PYEOF

cat > "$LIB/assemble.py" <<'PYEOF'
#!/usr/bin/env python3
import sys, os, json, time, glob

ev = sys.argv[1]
final = '--final' in sys.argv
fatal = None
for a in sys.argv[2:]:
    if a.startswith('--fatal='):
        fatal = a.split('=', 1)[1]

bags = {}
for p in sorted(glob.glob(os.path.join(ev, 'perbag', '*.json'))):
    b = os.path.basename(p)
    if b.endswith('.d9.json'):
        continue
    try:
        d = json.load(open(p, encoding='utf-8'))
        bags[d.get('run', b[:-5])] = d
    except Exception:
        pass

counts = {'total_runs': 0, 'nobag': 0, 'compact': 0, 'compact_received': 0,
          'img_unlinked_fullchain': 0, 'img_linked_verify': 0, 'img_received_verify': 0,
          't1_round_defer': 0, 'hov_verify': 0, 'err_info': 0,
          'done_ok': 0, 'deferred_final': 0, 'partial': 0}
for r, d in bags.items():
    counts['total_runs'] += 1
    c = d.get('class', '')
    if c == 'NOBAG': counts['nobag'] += 1
    elif c == 'ERR_INFO': counts['err_info'] += 1
    elif c == 'T1_ROUND': counts['t1_round_defer'] += 1
    elif c == 'COMPACT': counts['compact'] += 1
    elif c == 'R_COMPACT': counts['compact_received'] += 1
    elif c == 'IMG_FULLCHAIN': counts['img_unlinked_fullchain'] += 1
    elif c == 'IMG_LINKED_VERIFY': counts['img_linked_verify'] += 1
    elif c == 'R_IMG_VERIFY': counts['img_received_verify'] += 1
    elif c == 'HOV_VERIFY': counts['hov_verify'] += 1
    rc = d.get('rc', '')
    if rc == 'OK': counts['done_ok'] += 1
    elif rc == 'DEFERRED_FINAL': counts['deferred_final'] += 1
    elif rc == 'PARTIAL': counts['partial'] += 1

deferred = sorted([r for r, d in bags.items() if d.get('rc') == 'DEFERRED_FINAL'])
summary = {
    'script': 't4_recept_batch_v519.sh',
    'updated_at': time.strftime('%F %T'),
    'counts': counts,
    'deferred_final': deferred,
    'batch_complete': bool(final) and counts['deferred_final'] == 0 and fatal is None,
}
if fatal:
    summary['fatal'] = fatal
json.dump(summary, open(os.path.join(ev, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('SUMMARY counts=%s complete=%s' % (json.dumps(counts), summary['batch_complete']))
PYEOF

python3 -m py_compile "$LIB/compact_extract.py" "$LIB/freeze_d9.py" "$LIB/render_image_row.py" "$LIB/upd.py" "$LIB/assemble.py" 2>> "$LOG" || fatal_exit "py_compile failed"
say "PYLIB_OK $(ls "$LIB" | grep -c '\.py$') py files"

# ---------------------------------------------------------------- gate -------
gate(){
  # 0=clear 1=timeout(bag deferred) 2=df fatal
  local label="$1" waited=0 c1 c2 c3 g tb
  while true; do
    c1=$(pgrep -cx '[r]osbag'); c1=${c1:-0}
    c2=$(pgrep -cx '[g]zserver'); c2=${c2:-0}
    c3=$(pgrep -cx '[p]x4'); c3=${c3:-0}
    g=$(dfg); tb=N; t1busy && tb=Y
    if [ "$g" -lt "$DF_MIN" ]; then
      say "GATE_DF_STOP $label df=${g}G < ${DF_MIN}G -> WHOLE SCRIPT STOP (no force)"
      return 2
    fi
    if [ "$c1" = "0" ] && [ "$c2" = "0" ] && [ "$c3" = "0" ] && [ "$tb" = "N" ]; then
      say "GATE_OK $label waited=${waited}s rosbag=$c1 gzserver=$c2 px4=$c3 df=${g}G"
      return 0
    fi
    if [ "$waited" -ge "$GATE_MAX_SEC" ]; then
      say "GATE_TIMEOUT $label waited=${waited}s rosbag=$c1 gzserver=$c2 px4=$c3 t1rep_busy=$tb -> DEFER bag (no force)"
      return 1
    fi
    if [ $((waited % 600)) -eq 0 ]; then
      say "GATE_WAIT $label waited=${waited}s rosbag=$c1 gzserver=$c2 px4=$c3 t1rep_busy=$tb df=${g}G"
    fi
    sleep "$GATE_POLL"
    waited=$((waited + GATE_POLL))
  done
}

# ---------------------------------------------------------------- helpers ----
is_received12(){ case " $RECEIVED12 " in *" $1 "*) return 0;; *) return 1;; esac; }

# T1 x4_batch round bags (run_X1*/X2*/X3*): T1-line judging subjects (STATUS 04:51 T1 row),
# X1final feature replay = locked ledger item (no re-search). -> registration row only, never chained here.
is_t1_round(){ case "$1" in run_X[0-9]*) return 0;; *) return 1;; esac; }

ledger_family(){ # $1=run -> members found (space separated); ledger names drop the "run_" prefix
  local r="${1#run_}" out=""
  [ -f "$VIN/metrics_$r.json" ] && out="$out metrics"
  [ -f "$VIN/fbres_$r.json" ] && out="$out fbres"
  [ -f "$VIN/offset_$r.stdout" ] && out="$out offset"
  [ -d "$VIN/jr3_replay_$r" ] && out="$out jr3_replay"
  echo "$out"
}

baginfo_of(){ # $1=run -> echoes baginfo path; cached <6h
  local r="$1" bag="$VS/$1/flight.bag" f="$WORK/baginfo/$1.txt"
  if [ -s "$f" ] && [ $(( $(date +%s) - $(stat -c %Y "$f") )) -lt 21600 ]; then
    echo "$f"; return 0
  fi
  if timeout 240 bash -c "set +u; source /opt/ros/noetic/setup.bash >/dev/null 2>&1; set -u; rosbag info '$bag'" > "$f.tmp" 2>/dev/null && [ -s "$f.tmp" ]; then
    mv "$f.tmp" "$f"; echo "$f"; return 0
  fi
  rm -f "$f.tmp"; return 1
}

img_topics_of(){ grep -E 'sensor_msgs/Image' "$1" 2>/dev/null | awk '$2+0>0 {print $1":"$2}'; }
dur_of(){ grep -m1 '^duration:' "$1" 2>/dev/null | tr -dc '0-9.'; }

# ---------------------------------------------------------------- replay -----
master_busy(){ (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -q ':11314 '; }

replay_one(){ # $1=link $2=outdir $3=budget_sec
  local link="$1" out="$2" budget="$3"
  mkdir -p "$out"
  if master_busy; then
    sleep 60
    if master_busy; then say "REPLAY_MASTER_BUSY 11314 held -> leg fail (no force)"; return 5; fi
  fi
  set +u; source /opt/ros/noetic/setup.bash >/dev/null 2>&1; source /home/ghj/catkin_ws/devel/setup.bash >/dev/null 2>&1; set -u
  local c1 c2
  c1=$(ps -eo comm= | grep -cx rosbag); c1=${c1:-0}; sleep 5
  c2=$(ps -eo comm= | grep -cx rosbag); c2=${c2:-0}
  if [ "$c1" != "0" ] || [ "$c2" != "0" ]; then
    say "REPLAY_INTERNAL_WINDOW_FAIL c1=$c1 c2=$c2 -> defer"
    return 3
  fi
  export ROS_MASTER_URI="http://127.0.0.1:11314/"
  roscore -p 11314 > "$out/roscore.log" 2>&1 &
  local P_MASTER=$!
  sleep 3
  nice -n 10 rosrun vins vins_node "$CFG_E01" > "$out/vins.log" 2>&1 &
  local P_VINS=$!
  sleep 5
  rosbag play "$link" --clock -r 1.0 > "$out/play.log" 2>&1 &
  local P_PLAY=$!
  rosbag record -O "$out/features.bag" /vins_estimator/point_cloud /vins_estimator/odometry > "$out/record.log" 2>&1 &
  local P_REC=$!
  local SECS=0
  while kill -0 "$P_PLAY" 2>/dev/null && [ "$SECS" -lt "$budget" ]; do sleep 10; SECS=$((SECS+10)); done
  sleep 5
  kill -INT "$P_REC" 2>/dev/null; sleep 3
  kill -TERM "$P_PLAY" "$P_VINS" 2>/dev/null; sleep 2
  kill -TERM "$P_MASTER" 2>/dev/null; sleep 1
  kill -9 "$P_PLAY" "$P_VINS" "$P_MASTER" 2>/dev/null
  wait 2>/dev/null
  if [ -s "$out/features.bag" ]; then
    say "REPLAY_PRODUCT $out/features.bag $(du -h "$out/features.bag" | cut -f1)"
    return 0
  fi
  say "REPLAY_EMPTY_FEATURES $out (check vins.log/play.log)"
  return 4
}

# ================================================================ START ======
echo $$ > "$PIDFILE"
say "=== t4_recept_batch_v519 start pid=$$ dry=$DRY df=$(dfg)G ==="
echo "$(date '+%F %T') batch start pid=$$ dry=$DRY" > "$EV/progress.txt"

# ---------------------------------------------------------------- inventory --
say "INVENTORY_BEGIN snapshot=$(date '+%F %T')"
: > "$EV/plan.txt.tmp"
n_nobag=0; n_compact=0; n_rcompact=0; n_imgfull=0; n_imglink=0; n_rimg=0; n_err=0; n_t1r=0
NOBAG_RUNS=""
for d in "$VS"/run_*; do
  [ -d "$d" ] || continue
  run=$(basename "$d")
  bag="$d/flight.bag"
  if [ ! -f "$bag" ]; then
    n_nobag=$((n_nobag+1)); NOBAG_RUNS="$NOBAG_RUNS $run"
    echo "NOBAG $run" >> "$EV/plan.txt.tmp"
    continue
  fi
  bytes=$(stat -c %s "$bag" 2>/dev/null)
  if ! info=$(baginfo_of "$run"); then
    n_err=$((n_err+1))
    echo "ERR_INFO $run bytes=$bytes rosbag_info_failed" >> "$EV/plan.txt.tmp"
    if [ "$DRY" = 0 ] && [ ! -f "$PERBAG/$run.done" ]; then
      python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"ERR_INFO\",\"bag\":\"$bag\",\"bag_bytes\":$bytes,\"rc\":\"OK\",\"note\":\"rosbag info failed (可能录制中/损坏); 登记行, 不硬凑\"}" >/dev/null 2>&1
      echo "$run ERR_INFO" > "$PERBAG/$run.done"
    fi
    continue
  fi
  img=$(img_topics_of "$info" | tr '\n' ' ')
  n_img=$(echo $img | wc -w)
  if is_t1_round "$run"; then
    n_t1r=$((n_t1r+1))
    echo "T1_ROUND $run bytes=$bytes img_topics=$img note=T1_x4_batch_round_bag_not_ours" >> "$EV/plan.txt.tmp"
    continue
  fi
  if is_received12 "$run"; then
    if [ "$n_img" -gt 0 ]; then cls=R_IMG_VERIFY; n_rimg=$((n_rimg+1)); else cls=R_COMPACT; n_rcompact=$((n_rcompact+1)); fi
  elif [ "$n_img" -gt 0 ]; then
    if [ -f "$VIN/metrics_${run#run_}.json" ]; then cls=IMG_LINKED_VERIFY; n_imglink=$((n_imglink+1)); else cls=IMG_FULLCHAIN; n_imgfull=$((n_imgfull+1)); fi
  else
    cls=COMPACT; n_compact=$((n_compact+1))
  fi
  echo "$cls $run bytes=$bytes img_topics=$img" >> "$EV/plan.txt.tmp"
done
mv "$EV/plan.txt.tmp" "$PLAN"
say "INVENTORY_DONE nobag=$n_nobag compact=$n_compact received_compact=$n_rcompact img_fullchain=$n_imgfull img_linked_verify=$n_imglink received_img_verify=$n_rimg t1_round_defer=$n_t1r err_info=$n_err"
echo "$(date '+%F %T') plan: nobag=$n_nobag compact=$n_compact r_compact=$n_rcompact img_full=$n_imgfull img_link_verify=$n_imglink r_img_verify=$n_rimg t1_round=$n_t1r err=$n_err" >> "$EV/progress.txt"

if [ "$DRY" = 1 ]; then
  say "DRY_MODE_END plan at $PLAN ; no legs executed"
  echo "--- DRY counts: nobag=$n_nobag compact=$n_compact r_compact=$n_rcompact img_fullchain=$n_imgfull img_linked_verify=$n_imglink r_img_verify=$n_rimg t1_round_defer=$n_t1r err_info=$n_err"
  echo "--- plan lines: $(grep -c . "$PLAN")"
  exit 0
fi

if [ ! -s "$DRAFT" ]; then
  {
    echo "# T4 v5.19 积压收货批 判读行草稿 (t4_recept_batch_v519.sh 生成)"
    echo "# 红线: 本文件全部为草稿·待主会话定稿; 无预注册判据不出 PASS/FAIL; cohort 外袋不出三态;"
    echo "#       σ̂ 只认 P25; 阈值禁预拍(健康带 0.79-1.10m 仅作素材对照, T3 anchor v1.4 修正口径)."
    echo "# config=E01_baseline($CFG_E01) — 与 W1 收货链 e2_debug_smooth(a01e7a37) 不同, 差异逐行如实登记."
  } > "$DRAFT"
fi

# received hover verify (I3: hover stays in received set; verify receipts only, no re-chain)
hovbag="$HOV_BAG"; [ -f "$hovbag" ] || hovbag="$HOV_BAG_ALT"
if [ -f "$hovbag" ] && [ ! -f "$PERBAG/t2v3_hover_134845.done" ]; then
  say "HOV_VERIFY bag=$hovbag j0d=/home/ghj/sitl_sim/t3_results/j0d_t4w1/hov134845/j0_decomp.json"
  python3 "$LIB/upd.py" "$PERBAG/t2v3_hover_134845.json" "{\"run\":\"t2v3_hover_134845\",\"class\":\"HOV_VERIFY\",\"received\":1,\"bag\":\"$hovbag\",\"rc\":\"OK\",\"note\":\"I3 权属裁定: hover 计入收货集维持; 本批仅核对 receipt, 不重链\"}" >/dev/null 2>&1
  echo "t2v3_hover_134845 HOV" > "$PERBAG/t2v3_hover_134845.done"
elif [ ! -f "$hovbag" ]; then
  say "HOV_VERIFY_MISS bag not found at $HOV_BAG nor $HOV_BAG_ALT (honest)"
fi

# ---------------------------------------------------------------- legs -------
run_compact_leg(){ # $1=run $2=received(0/1)
  local run="$1" rec="$2" bag="$VS/$run/flight.bag" j0d="" clsx
  [ "$rec" = "1" ] && clsx=R_COMPACT || clsx=COMPACT
  [ -f "$VS/$run/j0_decomp.json" ] && j0d="$VS/$run/j0_decomp.json"
  say "COMPACT_BEGIN $run rec=$rec j0d=${j0d:-none}"
  if nice -n 10 timeout 900 python3 "$LIB/compact_extract.py" "$bag" "$PERBAG/$run.json" "$DRAFT" "$run" "$j0d" "$rec" < /dev/null >> "$WORK/compact_$run.log" 2>&1; then
    say "COMPACT_OK $run"
    python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"$clsx\",\"bag\":\"$bag\",\"rc\":\"OK\"}" >/dev/null
  else
    local frc=$?
    say "COMPACT_FAIL $run rc=$frc (honest, no force)"
    python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"$clsx\",\"bag\":\"$bag\",\"rc\":\"PARTIAL\",\"compact_fail\":true}" >/dev/null
  fi
  echo "$run COMPACT" > "$PERBAG/$run.done"
  python3 "$LIB/assemble.py" "$EV" >/dev/null
}

verify_img_ledger(){ # $1=run $2=cls
  local run="$1" cls="$2" fam recval=0
  fam=$(ledger_family "$run")
  [ "$cls" = "R_IMG_VERIFY" ] && recval=1
  if echo "$fam" | grep -q metrics; then
    say "IMG_VERIFY_OK $run cls=$cls ledger=[$fam] (在册 -> 跳过重链只核对)"
    python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"$cls\",\"received\":$recval,\"ledger\":\"$fam\",\"rc\":\"OK\"}" >/dev/null
  else
    say "IMG_VERIFY_MISS $run cls=$cls ledger empty (在册袋缺台账 -> 如实登记)"
    python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"$cls\",\"received\":$recval,\"ledger_missing\":true,\"rc\":\"PARTIAL\"}" >/dev/null
  fi
  echo "$run VERIFY" > "$PERBAG/$run.done"
  python3 "$LIB/assemble.py" "$EV" >/dev/null
}

run_image_leg(){ # $1=run ; returns 0 done 1 defer 2 df-stop
  local run="$1" bag="$VS/$run/flight.bag" info rc g tl tr budget link stage offout rshort
  rshort="${run#run_}"
  info="$WORK/baginfo/$run.txt"
  stage="$BAGS/run_t4r519_$run"; link="$stage/flight.bag"
  mkdir -p "$stage"
  if [ -e "$link" ] || [ -L "$link" ]; then
    say "STAGE_EXISTS $run -> $link"
  else
    if ln -s "$bag" "$link"; then say "STAGE_OK $run -> $link"; else
      say "STAGE_FAIL $run"
      python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"IMG_FULLCHAIN\",\"rc\":\"PARTIAL\",\"stage_fail\":true}" >/dev/null
      echo "$run IMG" > "$PERBAG/$run.done"
      return 0
    fi
  fi
  tl=$(img_topics_of "$info" | cut -d: -f1 | grep -i left | head -1)
  tr=$(img_topics_of "$info" | cut -d: -f1 | grep -i right | head -1)
  [ -z "$tl" ] && tl=$(img_topics_of "$info" | cut -d: -f1 | head -1)
  [ -z "$tr" ] && tr=$(img_topics_of "$info" | cut -d: -f1 | sed -n 2p)
  [ "$tl" = "$tr" ] && tr=""
  say "IMG_TOPICS $run L=$tl R=$tr"
  python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"IMG_FULLCHAIN\",\"bag\":\"$bag\",\"topic_l\":\"$tl\",\"topic_r\":\"$tr\"}" >/dev/null

  gate "${run}_extract"; g=$?
  [ $g -eq 2 ] && return 2
  [ $g -eq 1 ] && return 1
  say "EXTRACT_BEGIN $run"
  nice -n 10 timeout 1800 python3 "$A/j3_extract_frames.py" --bag "$link" --topic "$tl" ${tr:+--topic "$tr"} \
    --out "$WORK/frames_$run" --segments 3 --per-seg 24 --pairs < /dev/null > "$WORK/extract_$run.log" 2>&1
  rc=$?; say "EXTRACT_RC=$rc $run"
  python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"legs\":{\"extract_rc\":$rc}}" >/dev/null
  if [ $rc -ne 0 ]; then
    say "IMG_LEG_ABORT $run extract_rc=$rc -> PARTIAL honest"
    python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"rc\":\"PARTIAL\"}" >/dev/null
    echo "$run IMG" > "$PERBAG/$run.done"
    python3 "$LIB/assemble.py" "$EV" >/dev/null
    return 0
  fi

  gate "${run}_offset"; g=$?
  [ $g -eq 2 ] && return 2
  [ $g -eq 1 ] && return 1
  say "OFFSET_BEGIN $run"
  offout="$VIN/offset_$rshort.stdout"; [ -f "$offout" ] && offout="$WORK/offset_$run.stdout.rerun"
  nice -n 10 timeout 1800 python3 "$A/j3_feature_density.py" --mode offset --bag "$link" < /dev/null > "$offout" 2> "$WORK/offset_$run.err"
  rc=$?; say "OFFSET_RC=$rc $run out=$offout"
  python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"legs\":{\"offset_rc\":$rc,\"offset_out\":\"$offout\"}}" >/dev/null

  gate "${run}_metrics"; g=$?
  [ $g -eq 2 ] && return 2
  [ $g -eq 1 ] && return 1
  say "METRICS_BEGIN $run"
  nice -n 10 timeout 900 python3 "$A/j3_image_metrics.py" --frames-dir "$WORK/frames_$run" --out "$WORK/metrics_$run.json" < /dev/null > "$WORK/metrics_$run.log" 2>&1
  rc=$?; say "METRICS_RC=$rc $run"
  python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"legs\":{\"metrics_rc\":$rc}}" >/dev/null
  say "FBRES_BEGIN $run"
  nice -n 10 timeout 900 python3 "$A/j3_fb_residual.py" --frames-dir "$WORK/frames_$run" --out "$WORK/fbres_$run.json" < /dev/null > "$WORK/fbres_$run.log" 2>&1
  rc=$?; say "FBRES_RC=$rc $run"
  python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"legs\":{\"fbres_rc\":$rc}}" >/dev/null

  local dur; dur=$(dur_of "$info"); dur=${dur:-60}
  budget=$(awk -v d="$dur" 'BEGIN{b=d+180; if(b>1050)b=1050; if(b<300)b=300; printf "%d", b}')
  gate "${run}_replay"; g=$?
  [ $g -eq 2 ] && return 2
  [ $g -eq 1 ] && return 1
  md5sum "$VINS_NODE" > "$WORK/replay_md5_${run}_pre.txt" 2>&1
  md5sum "$VINS_LIB" >> "$WORK/replay_md5_${run}_pre.txt" 2>&1
  say "REPLAY_BEGIN $run budget=${budget}s outer_timeout=1200 config=E01_baseline(7836067e)"
  nice -n 10 timeout --kill-after=30 1200 bash -c "$(declare -f replay_one); $(declare -f master_busy); replay_one '$link' '$WORK/replay_$run' '$budget'; echo INNER_RC=\$?" > "$WORK/replay_$run.log" 2>&1
  rc=$?; say "REPLAY_RC=$rc $run"
  md5sum "$VINS_NODE" > "$WORK/replay_md5_${run}_post.txt" 2>&1
  md5sum "$VINS_LIB" >> "$WORK/replay_md5_${run}_post.txt" 2>&1
  python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"legs\":{\"replay_rc\":$rc,\"budget_s\":$budget}}" >/dev/null

  if [ -s "$WORK/metrics_$run.json" ] && [ -s "$WORK/frames_$run/manifest.json" ]; then
    gate "${run}_d9"; g=$?
    [ $g -eq 2 ] && return 2
    [ $g -eq 1 ] && return 1
    say "D9_BEGIN $run"
    nice -n 10 timeout 900 python3 "$LIB/freeze_d9.py" "$bag" "$WORK/frames_$run/manifest.json" "$WORK/metrics_$run.json" "$PERBAG/$run.d9.json" "$DRAFT" "$run" < /dev/null > "$WORK/d9_$run.log" 2>&1
    rc=$?; say "D9_RC=$rc $run"
    python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"legs\":{\"d9_rc\":$rc}}" >/dev/null
  else
    say "D9_SKIP $run (metrics/manifest missing -> 如实注记)"
    python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"legs\":{\"d9_rc\":-1}}" >/dev/null
  fi

  # ledger deposit (add-only, never overwrite; ledger names drop "run_" prefix)
  if [ -s "$WORK/metrics_$run.json" ] && [ ! -f "$VIN/metrics_$rshort.json" ]; then
    cp "$WORK/metrics_$run.json" "$VIN/metrics_$rshort.json" && say "LEDGER_DEPOSIT metrics_$rshort.json"
  fi
  if [ -s "$WORK/fbres_$run.json" ] && [ ! -f "$VIN/fbres_$rshort.json" ]; then
    cp "$WORK/fbres_$run.json" "$VIN/fbres_$rshort.json" && say "LEDGER_DEPOSIT fbres_$rshort.json"
  fi
  if [ -d "$WORK/replay_$run" ] && [ ! -d "$VIN/jr3_replay_$rshort" ]; then
    mv "$WORK/replay_$run" "$VIN/jr3_replay_$rshort" && say "LEDGER_DEPOSIT jr3_replay_$rshort/"
  fi
  if [ -s "$WORK/frames_$run/manifest.json" ] && [ ! -f "$VIN/frames_${rshort}_manifest.json" ]; then
    cp "$WORK/frames_$run/manifest.json" "$VIN/frames_${rshort}_manifest.json" && say "LEDGER_DEPOSIT frames_${rshort}_manifest.json"
  fi

  python3 "$LIB/render_image_row.py" "$run" 0 IMG_FULLCHAIN "$DRAFT" "$WORK/metrics_$run.json" "$WORK/fbres_$run.json" "$PERBAG/$run.d9.json" "$tl" "$tr" "E01_baseline(7836067e)≠W1链e2_debug_smooth(a01e7a37), v5.19 任务书指定, 差异如实登记" < /dev/null >> "$WORK/render_$run.log" 2>&1

  python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"rc\":\"OK\"}" >/dev/null
  echo "$run IMG" > "$PERBAG/$run.done"
  python3 "$LIB/assemble.py" "$EV" >/dev/null
  say "IMG_DONE $run"
  return 0
}

# ---- pass 1 ------------------------------------------------------------------
declare -a DEFERQ=()
df_stop=0
while read -r line <&3; do
  cls=$(echo "$line" | awk '{print $1}')
  run=$(echo "$line" | awk '{print $2}')
  [ -z "$run" ] && continue
  [ -f "$PERBAG/$run.done" ] && { say "IDEMPOTENT_SKIP $run"; continue; }
  case "$cls" in
    NOBAG)
      say "NOBAG_REGISTER $run (④无袋 run -> 登记行, 不收货)"
      python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"NOBAG\",\"rc\":\"OK\",\"note\":\"④无袋 run 登记行\"}" >/dev/null 2>&1
      echo "$run NOBAG" > "$PERBAG/$run.done"
      ;;
    T1_ROUND)
      say "T1_ROUND_REGISTER $run (T1 x4_batch 轮次袋, 判读权在 T1 补判版; X1final 特征重放=挂账禁重检索 -> 本批登记行, 不链不代判)"
      python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"run\":\"$run\",\"class\":\"T1_ROUND\",\"rc\":\"OK\",\"note\":\"T1 x4_batch 轮次袋, 他域判读权, 本批只登记\"}" >/dev/null 2>&1
      echo "$run T1_ROUND" > "$PERBAG/$run.done"
      ;;
    ERR_INFO) : ;;
    R_IMG_VERIFY|IMG_LINKED_VERIFY) verify_img_ledger "$run" "$cls" ;;
    R_COMPACT) run_compact_leg "$run" 1 ;;
    COMPACT) run_compact_leg "$run" 0 ;;
    IMG_FULLCHAIN)
      run_image_leg "$run"; r=$?
      if [ "$r" = "1" ]; then
        say "DEFERRED $run -> retry queue"
        python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"rc\":\"DEFERRED\"}" >/dev/null
        DEFERQ+=("$run")
      elif [ "$r" = "2" ]; then df_stop=1; break; fi
      ;;
  esac
  echo "$(date '+%H:%M:%S') processed=$run cls=$cls" >> "$EV/progress.txt"
done 3< "$PLAN"

# ---- pass 2: defer queue tail retry ------------------------------------------
if [ "$df_stop" = "0" ] && [ "${#DEFERQ[@]}" -gt 0 ]; then
  say "DEFER_RETRY_PASS n=${#DEFERQ[@]}"
  for run in "${DEFERQ[@]}"; do
    [ -f "$PERBAG/$run.done" ] && continue
    run_image_leg "$run"; r=$?
    if [ "$r" = "1" ]; then
      say "DEFERRED_FINAL $run (gate busy after retry -> honest, batch_complete=false)"
      python3 "$LIB/upd.py" "$PERBAG/$run.json" "{\"rc\":\"DEFERRED_FINAL\"}" >/dev/null
    elif [ "$r" = "2" ]; then df_stop=1; break; fi
  done
fi

# ---- final -------------------------------------------------------------------
if [ "$df_stop" = "1" ]; then
  python3 "$LIB/assemble.py" "$EV" --fatal=df_below_25G
  say "=== BATCH_END df_stop -> batch_complete=false ==="
else
  python3 "$LIB/assemble.py" "$EV" --final
  say "=== BATCH_END normal (batch_complete 见 summary.json) ==="
fi
echo "$(date '+%F %T') batch end df_stop=$df_stop" >> "$EV/progress.txt"
tail -3 "$LOG"
