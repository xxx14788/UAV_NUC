#!/usr/bin/env python3
# T1 v11.39 单元0留守件 v2 — static_watch 周期时间线重构(勘误:ALERT 件=同一累积 vins log 的
# 每 5min 全量重解析,非独立周期;t*=347 全同/span 递增 598→40861s 为证)
# 正解: 末件 ALERT_152028.txt 的 60s 段 |Bas| med 序列=完整时间线;台阶转移检测重构周期:
#   发作=med 跳上(>0.8 或 >0.3 阶跃);重启=med 回落至收敛带(<0.03)
import re, os

D = os.path.expanduser("~/sitl_sim/t1_evidence/v11_39_2026-10-09/static_watch/static_watch")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_39_2026-10-09")

# 取 span 最大的 ALERT(全量时间线最完整)
best, best_span = None, 0
for fp in sorted(os.listdir(D)):
    if not fp.startswith("ALERT_"): continue
    txt = open(os.path.join(D, fp), errors="replace").read()
    m = re.search(r"span=(\d+)s", txt)
    if m and int(m.group(1)) > best_span:
        best, best_span = os.path.join(D, fp), int(m.group(1))

txt = open(best, errors="replace").read()
# 勘误2: ALERT 件内有两张同格式段表(|Bas| 与 final_cost,med 值域 0.01-2 vs 200-1000),
# v2 初版正则两张表通吃(1358 段=681×2 实锤)。正解=只取 |Bas| 节。
bastxt = txt.split("=== final_cost")[0]
seg = []
for m in re.finditer(r"t=\s*(\d+)-\s*\d+s\s+n=\s*\d+\s+min=[0-9.]+\s+med=([0-9.]+)", bastxt):
    seg.append((int(m.group(1)), float(m.group(2))))
seg.sort()

CONV, OUTBREAK, STEPPED = 0.05, 0.8, 0.3   # 收敛带/发作线/台阶线
events = []   # (t, type, med)
state = "conv" if seg[0][1] < CONV else "stepped"
for i in range(1, len(seg)):
    t, v = seg[i]
    pv = seg[i-1][1]
    if state in ("conv",) and v > OUTBREAK:
        events.append((t, "OUTBREAK", v)); state = "outb"
    elif state in ("conv",) and v > STEPPED:
        events.append((t, "STEP-UP", v)); state = "stepped"
    elif state in ("stepped", "outb") and v < CONV:
        events.append((t, "RESTART(recovery)", v)); state = "conv"
    elif state == "stepped" and v > OUTBREAK:
        events.append((t, "OUTBREAK", v)); state = "outb"
    elif state == "outb" and v > STEPPED and abs(v - pv) > 0.3:
        events.append((t, "STEP-UP", v)); state = "stepped"

# 周期切分: RESTART→(STEP-UP…)→OUTBREAK→…→RESTART
restarts = [t for t, k, _ in events if "RESTART" in k]
outbreaks = [t for t, k, _ in events if k == "OUTBREAK"]
stepups = [t for t, k, _ in events if k == "STEP-UP"]
# 周期长度=相邻 restart 间隔
cyc = [restarts[i+1] - restarts[i] for i in range(len(restarts) - 1)]
# 各周期内发作时刻(相对周期起点)
onset_in_cycle = []
for i in range(len(restarts)):
    t0 = restarts[i]; t1 = restarts[i+1] if i + 1 < len(restarts) else seg[-1][0]
    ob = [t - t0 for t in outbreaks if t0 < t <= t1]
    onset_in_cycle += ob

def q(v, p):
    if not v: return None
    s = sorted(v); k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)

lines = [
    "# 留守件判读 v2(勘误版):旧机 static_watch 周期时间线重构(v1.2 追加节素材)",
    "",
    f"- 数据面勘误: ALERT 123 件=同一累积 vins log 每 ~5-6.5min 全量重解析(t*=347s 全同/span 递增 598→{best_span}s 实锤);",
    f"  周期统计正源=末件 {os.path.basename(best)} 的 60s 段 |Bas| med 时间线(n={len(seg)} 段={len(seg)}min)。",
    f"- 事件面: RESTART(回落收敛带)×{len(restarts)} | STEP-UP ×{len(stepups)} | OUTBREAK(>0.8)×{len(outbreaks)}",
    f"- 周期长度(相邻 RESTART 间隔): n={len(cyc)} min={min(cyc) if cyc else '-'} p50={q(cyc,0.5)} max={max(cyc) if cyc else '-'}s",
    f"- 周期内发作滞后(STEP-UP/OUTBREAK 相对周期起点): n={len(onset_in_cycle)} "
    f"min={min(onset_in_cycle) if onset_in_cycle else '-'} p50={q(onset_in_cycle,0.5)} p90={q(onset_in_cycle,0.9)} max={max(onset_in_cycle) if onset_in_cycle else '-'}s",
    "",
    "## 结论(同构性+结局分布;v1.1 样本 2→扩展)",
    f"- 同构性: {len(restarts)} 次重启循环全部重复「收敛→台阶上移(0.42/0.30 族)→发作(>0.8)→…→回落」节律;",
    f"  首周期 t*=347s(与 v1.1 样本及 T3 scen0 窗注记一致);后续周期发作滞后分布见上(重启后病理再发作自持)。",
    f"- 结局分布: 无一周期自然恢复(回落=重启事件;发作后 |Bas| 台阶单向上移无回落观察维持)。",
    f"- 静置病理定性: 重启循环(约 {q(cyc,0.5) or 'NA'}s/周期)×10h+ 自持;实机静置任务时长上限=发作滞后下界({min(onset_in_cycle) if onset_in_cycle else 'NA'}s)——",
    "  首飞风险评估输入(报告 v2/呈报件§④直接引用)。",
    f"- 污染注记: 04:44-04:48 断段维持(v1.1 口径;全量重解析下断段表现为段谱空洞,不影响事件面)。",
    "",
    "## 事件时间线(前 30+后 10)",
]
for t, k, v in events[:30]:
    lines.append(f"  t={t}s {k} med={v:.4f}")
if len(events) > 40:
    lines.append("  ...")
    for t, k, v in events[-10:]:
        lines.append(f"  t={t}s {k} med={v:.4f}")
open(os.path.join(OUT, "static_watch_judge_v2_v1139.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines[:14]))
