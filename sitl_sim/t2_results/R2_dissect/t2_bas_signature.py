#!/usr/bin/env python3
# t2_bas_signature.py — B3 追加签名判读 + 机器对照 Bas 签名提取（T2 v9.3 收口件）
# 0 锁纯日志分析。输入=vins_smoke_runs/run_*/simvins.log 的 [T2diag] 行(10Hz)
# 输出=逐轮签名 JSON 行：Bas/Bgs 极值与时刻、爆程段(>0.5 计)、track 带、P/V 幅值
import sys, os, re, glob, json

ANSI = re.compile(r'\x1b\[[0-9;]*m')
DIAG = re.compile(
    r'\[T2diag\] t=([0-9.]+) P=\[([-0-9.eE ]+)\] V=\[([-0-9.eE ]+)\] '
    r'\|Bas\|=([0-9.eE-]+) \|Bgs\|=([0-9.eE-]+) .*track=([0-9]+)')

def scan(run_dir):
    log = os.path.join(run_dir, 'simvins.log')
    if not os.path.exists(log):
        return None
    rows = []
    with open(log, 'r', errors='replace') as f:
        for line in f:
            if '[T2diag]' not in line:
                continue
            m = DIAG.search(ANSI.sub('', line))
            if not m:
                continue
            t = float(m.group(1))
            P = [abs(float(x)) for x in m.group(2).split()]
            V = [abs(float(x)) for x in m.group(3).split()]
            bas, bgs, trk = float(m.group(4)), float(m.group(5)), int(m.group(6))
            rows.append((t, bas, bgs, trk, max(P) if P else 0, max(V) if V else 0))
    if not rows:
        return None
    bas_arr = [r[1] for r in rows]
    imax = max(range(len(rows)), key=lambda i: rows[i][1])
    over05 = [rows[i] for i in range(len(rows)) if rows[i][1] > 0.5]
    over05_t = [r[0] for r in over05]
    # 发作窗(若有)=首末越限时刻; 窗内 track 带
    if over05:
        w0, w1 = min(over05_t), max(over05_t)
        wtrk = sorted(r[3] for r in over05)
        trk_med = wtrk[len(wtrk)//2]
    else:
        w0 = w1 = trk_med = None
    t_end = rows[-1][0]
    # Bas@末段(最后10s中位) vs @首段(前10s中位): 持久性(先验冻结 vs 回落)
    def med(seg):
        s = sorted(seg); return s[len(s)//2] if s else None
    bas_early = med([r[1] for r in rows if r[0] - rows[0][0] < 10])
    bas_late = med([r[1] for r in rows if t_end - r[0] < 10])
    return {
        'dir': os.path.basename(run_dir),
        'n': len(rows), 't_end': round(t_end, 1),
        'bas_max': round(max(bas_arr), 3), 'bas_tmax': round(rows[imax][0], 1),
        'bas_early_med': round(bas_early, 4) if bas_early is not None else None,
        'bas_late_med': round(bas_late, 4) if bas_late is not None else None,
        'n_over05': len(over05),
        'win': [round(w0, 1), round(w1, 1)] if w0 is not None else None,
        'trk_med_in_win': trk_med,
        'p_max': round(max(r[4] for r in rows), 2),
        'v_max': round(max(r[5] for r in rows), 2),
    }

def main():
    pats = sys.argv[1:]
    out = []
    for p in pats:
        for d in sorted(glob.glob(os.path.expanduser(p))):
            r = scan(d)
            if r:
                out.append(r)
    print(json.dumps(out, indent=1))

if __name__ == '__main__':
    main()
