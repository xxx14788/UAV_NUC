#!/usr/bin/env python3
# t1_c1_extract_ulog.py — C-1 验证轮 ulog 五元组离线提取（2026-10-11 单元1）
# 用法: python3 t1_c1_extract_ulog.py <round.ulg>
# 五元组: ①vehicle_command_ack(179,result) ②vehicle_status.arming_state 翻转
#         ③actuator_armed.armed ④nav_state(mode) 序列 ⑤悬停维持(vehicle_local_position z)
# 附加: events/log_message 补采主题（logger_topics.txt 预防性配置,复现分支收窄用）
import sys
from collections import Counter
from pyulog import ULog

ulg_path = sys.argv[1]
u = ULog(ulg_path, None)
T0 = u.start_timestamp

def ds(name):
    for d in u.data_list:
        if d.name == name:
            return d
    return None

def rel(t):
    return (t - T0) / 1e6

print("ulog: %s" % ulg_path)
print("ver_sw: %s" % u.msg_info_dict.get('ver_sw', 'NA'))
print("duration_s: %.1f" % rel(u.last_timestamp))

# ① vehicle_command: 179 行
vc = ds('vehicle_command')
n179 = 0
if vc is not None:
    cmds = vc.data.get('command', [])
    tss = vc.data.get('timestamp', [])
    p1s = vc.data.get('param1', [])
    p2s = vc.data.get('param2', [])
    srcs = vc.data.get('source_component', []) if 'source_component' in vc.data else []
    tgts = vc.data.get('target_component', []) if 'target_component' in vc.data else []
    ext = vc.data.get('from_external', []) if 'from_external' in vc.data else []
    for i in range(len(cmds)):
        if cmds[i] == 179:
            n179 += 1
            extra = ""
            if len(srcs) > i:
                extra += " src_comp=%s tgt_comp=%s ext=%s" % (
                    srcs[i], tgts[i] if len(tgts) > i else '?', ext[i] if len(ext) > i else '?')
            print("CMD179 #%d: t+%.2fs param1=%s param2=%s%s" % (
                n179, rel(tss[i]), p1s[i], p2s[i], extra))
    print("total vehicle_command rows: %d, cmd179 rows: %d" % (len(cmds), n179))
else:
    print("vehicle_command: NOT IN ULOG")

# ① vehicle_command_ack: 179 的 result 序列
ack = ds('vehicle_command_ack')
if ack is not None:
    cmds = ack.data.get('command', [])
    results = ack.data.get('result', [])
    tss = ack.data.get('timestamp', [])
    r179 = [i for i in range(len(cmds)) if cmds[i] == 179]
    print("ACK179: %d rows; result histogram: %s" % (
        len(r179), dict(Counter(results[i] for i in r179)) if r179 else "(none)"))
    if r179:
        print("  first ACK179 t+%.2fs result=%d" % (rel(tss[r179[0]]), results[r179[0]]))
        print("  last  ACK179 t+%.2fs result=%d" % (rel(tss[r179[-1]]), results[r179[-1]]))
else:
    print("vehicle_command_ack: NOT IN ULOG")

# ② vehicle_status.arming_state 翻转
vs = ds('vehicle_status')
if vs is not None:
    arm = list(vs.data.get('arming_state', []))
    tss = list(vs.data.get('timestamp', []))
    flips = []
    for i in range(1, len(arm)):
        if arm[i] != arm[i - 1]:
            flips.append((rel(tss[i]), arm[i - 1], arm[i]))
    print("vehicle_status: %d samples; arming_state flips: %s" % (
        len(arm), flips if flips else "NONE (zero flips)"))
    print("  arming_state last 3: %s" % (arm[-3:] if len(arm) >= 3 else arm))
else:
    print("vehicle_status: NOT IN ULOG")

# ③ actuator_armed.armed
aa = ds('actuator_armed')
if aa is not None:
    armed = list(aa.data.get('armed', []))
    cnt = Counter(bool(x) for x in armed)
    print("actuator_armed: %d samples; True=%d False=%d; last=%s" % (
        len(armed), cnt.get(True, 0), cnt.get(False, 0), bool(armed[-1]) if armed else 'NA'))
else:
    print("actuator_armed: NOT IN ULOG")

# ④ nav_state 序列（4=AUTO_LOITER failsafe 悬停=08_24_40 观测态）
if vs is not None:
    nav = list(vs.data.get('nav_state', []))
    navcnt = Counter(nav)
    print("nav_state histogram: %s" % dict(navcnt))
    tail = [int(x) for x in nav[-50:]] if len(nav) >= 50 else [int(x) for x in nav]
    print("nav_state tail(last<=50 unique-run): %s" % sorted(set(tail)))

# ⑤ 悬停维持: vehicle_local_position z 序列（inject 前后带）
lp = ds('vehicle_local_position')
if lp is not None:
    zs = list(lp.data.get('z', []))
    tss = list(lp.data.get('timestamp', []))
    if zs:
        n = len(zs)
        k = max(1, n // 10)
        segs = []
        for s in range(0, n, k):
            seg = zs[s:s + k]
            segs.append("%d..%ds:[%.2f,%.2f]" % (
                rel(tss[s]), rel(tss[min(s + len(seg) - 1, n - 1)]),
                min(seg), max(seg)))
        print("local_position z bands(10 segments): %s" % " ".join(segs))
else:
    print("vehicle_local_position: NOT IN ULOG")

# 附加: events / log_message 补采（复现分支收窄面）
ev = ds('events')
if ev is not None:
    evs = list(ev.data.get('id', [])) if 'id' in ev.data else []
    print("events topic: %d rows (logger_topics.txt 补采生效)" % len(evs))
    print("  events id histogram(top10): %s" % dict(Counter(evs).most_common(10)))
else:
    print("events topic: NOT IN ULOG（补采未生效或零事件）")
lm = ds('log_message')
if lm is not None:
    msgs = list(lm.data.get('text', [])) if 'text' in lm.data else []
    print("log_message topic: %d rows" % len(msgs))
    for m in msgs[-15:]:
        try:
            print("  LOG: %s" % m.decode(errors='replace'))
        except Exception:
            print("  LOG: %r" % m)
else:
    print("log_message topic: NOT IN ULOG")
