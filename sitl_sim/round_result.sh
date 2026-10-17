#!/usr/bin/env bash
# round_result.sh — VINS 链路轮次四指标 RESULT(真值+VINS双口径,两段式按goal切窗)
# 到位门场景分门(用户 10-01 裁决,2026-10-01 落地): world 含 obstacles→0.75m,否则 0.5m;
# J0 锚差跳变门(>0.5 一律 FAIL)与避障/频率/降落门不变。
# 用法: round_result.sh <bag> <gx> <gy> <gz> <world> <evdir> <arr1> <arr2> <hasl2> <l2x> <l2y> <l2z>
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
python3 - "$@" <<'PYEOF'
import sys, math
import rosbag
bag, gx, gy, gz, world, ev, arr, arr2, hasl2 = sys.argv[1:10]
l2x, l2y, l2z = float(sys.argv[10]), float(sys.argv[11]), float(sys.argv[12])
gx, gy, gz = float(gx), float(gy), float(gz); hasl2 = hasl2 == '1'
BOX = {"box_A": (3.5,-1.5,0.0,1.0,1.0,1.8), "box_B": (5.0,-2.5,0.0,1.5,1.0,1.2),
       "box_C": (4.5,-3.5,0.0,1.0,1.0,2.2)}
if world.endswith('_v2'):
    BOX["box_D"] = (6.4,-2.0,0.0,1.0,1.0,2.8); BOX["box_E"] = (6.4,0.5,0.0,1.0,1.0,2.8)
if world.endswith('_v9'):
    BOX = {"cL1": (2.4384, 2.6629, 0.0, 0.602, 0.602, 1.5), "cL2": (4.4607, 4.1761, 0.0, 0.602, 0.602, 1.5)}  # P0-2 fix 2026-10-17: v9 rounds previously fell into 13m cB/cN table = phantom min_dist (frame+table mismatch, P02 filing); gazebo-frame ground truth from sitl_world_corridor_v9.world poses; thin-panel box equivalent solid
elif "corridor" in world:   # v1.5c C3: GAZEBO frame (truth tong zhen; jiubiao A/B/C shi odom zuobiao dai ±1m xitong cha de lishi baoliu mian). zhengyuan=~/sitl_sim/c3_corridor_20261013/world_design_rationale.md sec8
    BOX = {"cB1": (4.457,0.737,0.0,1.0,1.0,1.8), "cB2": (7.010,0.127,0.0,1.0,1.0,1.8),
           "cB3": (9.442,1.112,0.0,1.0,1.0,1.8), "cB4": (11.995,0.502,0.0,1.0,1.0,1.8),
           "cN1": (2.544,3.100,0.0,1.0,1.0,1.8), "cN2": (4.875,4.295,0.0,1.0,1.0,1.8),
           "cN3": (6.077,6.622,0.0,1.0,1.0,1.8)}  # v1.5g: world v6 (d=0.40 RC-3 retreat; v5 backup 191b06de)
def dbox(p, b):
    cx,cy,z0,sx,sy,sz = b
    dx = max(abs(p[0]-cx)-sx/2, 0.0); dy = max(abs(p[1]-cy)-sy/2, 0.0)
    dz = max(max(z0-p[2], p[2]-(z0+sz)), 0.0)
    return math.hypot(dx,dy,dz)
prop, truth, cmd, armed, goals = [], [], [], [], []
with rosbag.Bag(bag,'r') as b:
    for topic, msg, t in b.read_messages():
        ts = t.to_sec()
        if topic == '/vins_estimator/imu_propagate':
            p = msg.pose.pose.position; prop.append((ts,p.x,p.y,p.z))
        elif topic == '/gazebo/model_states':
            try: i = msg.name.index('iris_stereo_vins')
            except ValueError: continue
            p = msg.pose[i].position; truth.append((ts,p.x,p.y,p.z))
        elif topic == '/position_cmd':
            p = msg.position; cmd.append((ts,p.x,p.y,p.z))
        elif topic == '/mavros/state':
            armed.append(msg.armed)
        elif topic == '/move_base_simple/goal':
            p = msg.pose.position; goals.append((ts,p.x,p.y,p.z))
if not prop: print('RESULT=FAIL 无 imu_propagate'); sys.exit()
def near(arr, tt): return min(arr, key=lambda p: abs(p[0]-tt))
p0 = prop[0]
# ---- v1.4 双锚取稳（prereg xline_prereg §2.8;2026-10-05 冻结;用户裁定案③）----
# C_dyn=goal+5s 窗(逐字旧口径保位等价);C_sta=goal-15~-5s 窗(探针口径);
# 稳态=窗内配对差逐轴 std<=0.03 ∧ IQR<=0.06(评估预算150样本,锚值仍前50构造)+
# 可用性 n>=50 ∧ 跨度>=0.4s;R1-R5 取稳;A* 供到位判;旧 a 变量=A*(双列输出兼容)。
g1_ts0 = next((g[0] for g in goals if abs(g[1]-gx)<0.01 and abs(g[2]-gy)<0.01 and abs(g[3]-gz)<0.01), prop[0][0])

def win_anchor(f, to):
    """窗锚(v1.1 位等价构造):窗内前 50 prop 配最近 truth 的逐轴均值差。"""
    pw = [p for p in prop if f <= p[0] <= to]
    if not pw: return None, []
    sw = pw[:50]
    tw = [near(truth, p[0]) for p in sw]
    if not truth or len(tw) != len(sw): return None, []
    anc = tuple(sum(t[k] for t in tw)/len(tw) - sum(p[k] for p in sw)/len(sw) for k in (1,2,3))
    return anc, sw

def win_stable(f, to):
    """稳态判据:窗内配对差(预算150)逐轴 std<=0.03 ∧ IQR<=0.06 ∧ n>=50 ∧ 跨度>=0.4s。"""
    pw = [p for p in prop if f <= p[0] <= to][:150]
    if len(pw) < 50: return False, len(pw), 0.0
    tw = [near(truth, p[0]) for p in pw]
    d = [[t[k]-p[k] for k in (1,2,3)] for t, p in zip(tw, pw)]
    span = pw[-1][0] - pw[0][0]
    if span < 0.4: return False, len(pw), span
    for k in range(3):
        col = sorted(x[k] for x in d)
        n = len(col); mean = sum(col)/n
        std = math.sqrt(sum((x-mean)**2 for x in col)/n)
        q1, q3 = col[int(0.25*n)], col[min(int(0.75*n), n-1)]
        if std > 0.03 or (q3-q1) > 0.06: return False, n, span
    return True, len(pw), span

c_dyn, _ = win_anchor(g1_ts0, g1_ts0 + 5)
c_sta, _ = win_anchor(g1_ts0 - 15, g1_ts0 - 5)
st_dyn, n_dyn, sp_dyn = win_stable(g1_ts0, g1_ts0 + 5) if c_dyn else (False, 0, 0.0)
st_sta, n_sta, sp_sta = win_stable(g1_ts0 - 15, g1_ts0 - 5) if c_sta else (False, 0, 0.0)
# F 兜底锚(出生锚;=旧 a_pre 构造)
a_fb = None
for t in truth:
    if t[0] >= p0[0]: a_fb = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3]); break
gap = 99.9; rule = 'R5'; flag = 'DUAL-ANCHOR-UNSTABLE'
if c_sta and st_sta and c_dyn and st_dyn:
    gap = math.hypot(*(x-y for x,y in zip(c_sta, c_dyn)))
    if gap <= 0.15: rule, flag = 'R1', 'AGREE'
    else:           rule, flag = 'R2', 'DUAL-ANCHOR-DIVERGENT'
    a = c_sta
elif c_sta and st_sta:
    rule, flag = 'R3', ''; a = c_sta
elif c_dyn and st_dyn:
    rule, flag = 'R4', 'STA-UNSTABLE'; a = c_dyn
elif c_dyn is not None:
    rule, flag = 'R5', 'DUAL-ANCHOR-UNSTABLE'; a = a_fb if a_fb else c_dyn
else:
    rule, flag = 'R5', 'DUAL-ANCHOR-UNSTABLE'; a = a_fb
if a is None and truth:
    t = truth[0]; a = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3])
# 帧稳定性:goal前锚 vs 末段锚(差>0.5m=VINS帧中途跳变→任务物理未完成,FAIL 定性)
a_pre = None
for t in truth:
    if t[0] >= p0[0]:
        a_pre = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3]); break
a_post = None
if prop and truth:
    tp = near(prop, prop[-1][0]-3); tg = near(truth, tp[0])
    a_post = (tg[1]-tp[1], tg[2]-tp[2], tg[3]-tp[3])
jump = 99.9
if a_pre and a_post:
    jump = math.hypot(*(x-y for x,y in zip(a_pre, a_post)))
# 勘误(prereg §2.8a,2026-10-05 夜):历史锚构造(本文件旧版+探针同源)prop 侧均值为
# sum(前50)/len(全窗)——静态窗 prop≈VINS 原点故隐身;动态窗 prop 达 5-10m 时被系统性
# 缩放污染(在册"动态窗 z 污染 +0.18~+0.71"含此算术伪影成分)。v1.4 两侧均值同用前50
# 样本(C_sta 与历史位等价因静态窗隐身性;A* 判决面不受影响——两种构造下 A* 同选)。
print('anchor(双锚取稳A*): (%.3f, %.3f, %.3f) | 帧稳定性 |pre-post|=%.3f m%s'
      % (a[0], a[1], a[2], jump, '  <-- VINS 帧中途跳变!' if jump > 0.5 else ''))
# v1.5(2026-10-13 C3): corridor world box-table + scene-gate extension; panduan luoji ling gaidong
# v1.4 双锚取稳双列(prereg §2.8):A* 已用于到位判;gap=‖C_sta−C_dyn‖(未评估=99.9)
def _fmt(x): return ('(%.3f, %.3f, %.3f)' % x) if x else 'N/A'
print('DUAL-ANCHOR v1.4: A*=%s rule=%s gap=%.3f flag=%s | sta=%s(n=%d,span=%.1fs,stable=%d) dyn=%s(n=%d,span=%.1fs,stable=%d)'
      % (_fmt(a), rule, gap, flag or '-', _fmt(c_sta), n_sta, sp_sta, 1 if st_sta else 0,
         _fmt(c_dyn), n_dyn, sp_dyn, 1 if st_dyn else 0))
t2_start = None
if hasl2:
    for g in goals:
        if abs(g[1]-l2x) < 0.01 and abs(g[2]-l2y) < 0.01 and abs(g[3]-l2z) < 0.01:
            t2_start = g[0]; break
def leg_min(pts, goal, ts_from, ts_to, anchored=True):
    if a is None and anchored: return -1
    tx, ty, tz = (goal[0]+a[0], goal[1]+a[1], goal[2]+a[2]) if anchored else goal
    sel = [p for p in pts if ts_from <= p[0] <= ts_to]
    if not sel: return -1
    return min(math.hypot(p[1]-tx,p[2]-ty,p[3]-tz) for p in sel)
t_end = truth[-1][0] if truth else prop[-1][0]
g1_ts = next((g[0] for g in goals if abs(g[1]-gx)<0.01 and abs(g[2]-gy)<0.01 and abs(g[3]-gz)<0.01), prop[0][0])
w1_to = t2_start if t2_start else t_end
dt1 = leg_min(truth, (gx,gy,gz), g1_ts, w1_to)
dv1 = leg_min(prop, (gx,gy,gz), g1_ts, w1_to, anchored=False)
mind = min(dbox((p[1],p[2],p[3]), bx) for p in truth for bx in BOX.values()) if truth else -1  # v1.5b C3: yuan 4-tuple zhijie ru dbox -> p[0]=ts bei dang x zuoobiao(historical mind=ts-vs-box-x weying, 19.8/15.0 deng zhi quantibu weying); fix=(x,y,z) qiepian, yuhe yuyi huigui
hz = len(cmd)/(cmd[-1][0]-cmd[0][0]) if len(cmd)>10 else 0
import bisect
dev = []; ts_prop = [p[0] for p in prop]
for c in cmd:
    j = bisect.bisect_left(ts_prop, c[0])
    if 0 < j < len(prop):
        p = prop[j]; dev.append(math.hypot(c[1]-p[1],c[2]-p[2],c[3]-p[3]))
dev.sort(); p95 = dev[int(0.95*len(dev))] if dev else -1
disarm_ok = (not armed[-1]) if armed else False
# 完整降落证据（三列分账 v1 恢复链[2];T3 v10.3 单元 1）：真值末 50 帧 z 均值 <0.15m
z_end = (sum(t[3] for t in truth[-50:])/min(50, len(truth))) if truth else -1.0
land_ok = z_end < 0.15
GATE = 0.75 if ('obstacles' in world or 'corridor' in world) else 0.5   # dao wei scene gate; v1.5 C3: corridor han 7 shiti zhangai, an 10-01 fenmen yuyi chi 0.75 (renwushu danyuan3 yuzhuce)
ok = [dt1 < GATE, mind > 0.349, hz >= 50, disarm_ok]
if jump > 0.5:
    # v1.5h(2026-10-14 C3): 慢漂豁免——|pre-post| 是累积量, 慢漂轮(hover6: 1.28m/102s=0.0126m/s,
    # j0d 证 jump 分量仅 0.135)被误翻案; 跳变带对照(E4_224447 24m/307s=0.078, E1_205851 21.7m/57s=0.38)。
    # 门=漂移率 0.03 m/s(3× 慢漂健康带上界); 单帧跳终判归 j0d max_frame_de_m(判据③语义对齐)。
    _win = (prop[-1][0] - p0[0]) if (prop and p0) else 0
    _rate = (jump / _win) if _win > 30 else 9.9
    if _rate > 0.03:
        ok[0] = 0
        print('判据: VINS 帧跳变(%.2fm)>0.5m 且漂移率 %.4f m/s>0.03 → 到位判 FAIL(目标物理位置被跳变移走,T2 瞬态发散类)' % (jump, _rate))
    else:
        print('注记: |pre-post|=%.2fm>0.5 但漂移率 %.4f m/s≤0.03=慢漂带豁免(v1.5h; 单帧跳终判归 j0d)' % (jump, _rate))
print('leg1 到位(真值) min=%.3f m (<%.2f,场景门 world=%s)->%d | leg1(VINS自报) min=%.3f m' % (dt1, GATE, world, ok[0], dv1))
if hasl2 and t2_start:
    dt2 = leg_min(truth, (l2x,l2y,l2z), t2_start, t_end)
    dv2 = leg_min(prop, (l2x,l2y,l2z), t2_start, t_end, anchored=False)
    ok[0] = ok[0] and (dt2 < GATE)
    print('leg2 到位(真值) min=%.3f m (<%.2f,与leg1合并判)->%d | leg2(VINS自报) min=%.3f m' % (dt2, GATE, dt2 < GATE, dv2))
print('避障 min_dist=%.3f m (>0.349)->%d [P0-2: v9 表已修 2026-10-17; 13m 历史轮该行禁引—帧系+版本双错配, 净距唯一正源=audit min_surf]' % (mind, ok[1]))
print('poscmd %.1f Hz (>=50)->%d' % (hz, ok[2]))
print('auto_disarm->%d' % ok[3])
print('LANDING: z_end=%.3f m (<0.15)->%d' % (z_end, 1 if land_ok else 0))
print('跟踪 p95=%.3f m (cmd-odom, 信息项)' % p95)
print('ARRIVE_WATCH1: %s' % arr)
print('ARRIVE_WATCH2: %s' % arr2)
# T4-E4.2(2026-09-29): 环境性崩溃分口径——gzserver/px4 轮中死亡=ENV-FAIL(重试不计入飞行预算)
import os as _os, glob as _glob
# v1.1 受控失败标注(纯标注,不改任何判值;prereg xline_prereg_v1_1.md §3.2)
# COSTGATE-FIRE=L1 触发行证据(first_t=WARN 头 sim 时刻,与袋时戳同钟);FAILDET=failure 计数
import re as _re
_fires = []; _nfd = 0; _m = None
_cl = _os.path.join(ev, 'simvins.log')
if _os.path.exists(_cl):
    try:
        _lt = open(_cl, errors='ignore').read()
    except OSError:
        _lt = ''
    _fires = _re.findall(r'cost gate: streak=(\d+) over ([\d.]+)x short-window median, reboot', _lt)
    if _fires:
        _m = _re.search(r'\[[\d.]+, ([\d.]+)\]:[^\n]*cost gate: streak=', _lt)
        print('COSTGATE-FIRE n=%d first_t=%s streak=%s ratio=%s' % (
            len(_fires), _m.group(1) if _m else '?', _fires[0][0], _fires[0][1]))
    _nfd = _lt.count('failure detection!')
    if _nfd:
        print('FAILDET n=%d' % _nfd)
# ---- 三列分账 v1 单轮证据面（T3 v10.3 单元 1；prereg §2.9）----
# 格式冻结：GATEHIT-STAT 行=批计数正源素材;分类权威=analysis/t3_trichotomy.py(x4_batch 消费,
# cf 状态由 t3_wa_gate --online 现场传入)。此处内联版供单轮人读+背书链;cost-fire 轮 abort 初判
# =0(cf 面在 wa_gate 权威,批面补齐)。
import json as _json
_ghs = sorted(_glob.glob(_os.path.join(ev, 'gatehit_*.json')))
_gh = None
if _ghs:
    try: _gh = _json.load(open(_ghs[0]))
    except (OSError, ValueError): _gh = None
_pgb = 0
for _p in sorted(_glob.glob(_os.path.join(ev, 'pregate_*.json'))):
    try:
        if _json.load(open(_p)).get('verdict') == 'block': _pgb = 1
    except (OSError, ValueError): pass
if _gh is not None:
    _kind, _ts, _val = 'watchdog', _gh.get('t_trig'), _gh.get('value')
    _abort = 1 if any(k in str(_gh.get('action', '')) for k in
                      ('goal-stop', 'controlled-abort', 'land-fallback', 'land', 'goal_stop')) else 0
    _land = 1 if (_gh.get('landed') == 1 or land_ok) else 0
elif _fires:
    _kind, _ts = 'cost', (_m.group(1) if _m else None)
    _val = 'streak=%s,ratio=%s' % _fires[0]
    _abort, _land = 0, (1 if land_ok else 0)
elif _nfd > 0:
    _kind, _ts, _val = 'legacy', None, 'faildet_n=%d' % _nfd
    _abort, _land = 0, (1 if land_ok else 0)
else:
    _kind = _ts = _val = None
    _abort = _land = 0
_trig_n = (1 if _gh is not None else 0) + len(_fires) + (1 if _nfd > 0 else 0)
_dis = 1 if disarm_ok else 0
_n2f = 1 if _nfd == 0 else 0
print('GATEHIT-STAT: n=%d ts=%s val=%s kind=%s chain=abort:%d,land:%d,disarm:%d,not2fail:%d'
      % (_trig_n, _ts if _ts is not None else 'NA',
         _val if _val is not None else 'NA', _kind or 'NA', _abort, _land, _dis, _n2f))
if _pgb:
    print('PREGATE-BLOCK: 1 (起飞前门拒绝;轮未起飞域→分母外重试)')
if _trig_n == 0:
    _tri = 'phys_green' if all(ok) else 'true_fail'
elif _abort and _land and _dis and _n2f:
    _tri = 'gate_intercept(初判;cf面待wa_gate权威)'
else:
    _tri = 'intercept_incomplete(初判;cf面待wa_gate权威)'
print('TRICHOTOMY: class=%s [门干预n=%d]' % (_tri, _trig_n))
_envfail = False
for _lg in [ _os.path.join(ev, 'sitl.log'), _os.path.join(ev, 'round.log') ] + _glob.glob(_os.path.join(ev, '*.log')):
    try:
        _txt = open(_lg, errors='ignore').read()
    except OSError:
        continue
    if ('Connection closed by client' in _txt or 'px4 亡,进程组整组清场' in _txt
            or _os.path.exists(_os.path.join(ev, 'ENVDEAD'))):
        _envfail = True
        break
if _envfail and not all(ok):
    print('RESULT=ENV-FAIL  (环境性:gazebo/px4 轮中死亡,证据见 %s;重试不计入飞行预算,对齐 T3-X4 允许 1 环境性重试)' % ev)
else:
    print('RESULT=%s  (证据: %s)' % ('PASS' if all(ok) else 'FAIL', ev))
PYEOF
