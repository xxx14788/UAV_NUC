#!/usr/bin/env bash
# T3 X 线轮落盘即入账一键件(v7.4 等待池⑥;X 线轮跑完后的标准动作,runbook §8 配套)
# 用法: bash t3_xline_intake.sh <run_dir> [--csv ~/sitl_sim/xline_wa_gate.csv] [--auto-ledger]
# 动作:
#   1) 前置:RESULT.txt+flight.bag 在位(轮完整落盘);forensics 缺则 wa_gate 自动生成
#   2) t3_wa_gate --online 判决 → <run_dir>/wa_gate_online.json + 汇总 CSV 追加行
#   3) 台账模板行 → <run_dir>/ledger_line.md(默认打印人审;--auto-ledger 直接 append 台账)
#   4) figs 再生提示(fig1/fig4 即刻;X7 报告数据源)
#   legs 全库重扫(leg_database.py)不在轮内自动跑(IO 重);X4 5/5 判定时统一跑。
set -u
A="$HOME/catkin_ws/sitl_sim/analysis"
RD="${1:?run_dir}"; shift || true
CSV="$HOME/sitl_sim/xline_wa_gate.csv"; AUTO=0
while [ $# -gt 0 ]; do case "$1" in
  --csv) CSV="$2"; shift 2;;
  --auto-ledger) AUTO=1; shift;;
  *) echo "unknown arg $1"; exit 2;;
esac; done

[ -f "$RD/RESULT.txt" ] && [ -f "$RD/flight.bag" ] || { echo "FATAL 轮未完整落盘(缺 RESULT.txt/flight.bag): $RD"; exit 1; }

echo "== [intake 1/3] wa_gate 在线判决 =="
python3 "$A/t3_wa_gate.py" --online --csv "$CSV" "$RD" || exit 1

echo "== [intake 2/3] 台账模板行 =="
python3 - "$RD" > "$RD/ledger_line.md" <<'PYEOF'
import json, os, sys, re
rd = sys.argv[1]
j = json.load(open(os.path.join(rd, "wa_gate_online.json"), errors="replace"))
x, v, fo = j.get("xline", {}), j.get("vins", {}), j.get("forensics", {})
txt = open(os.path.join(rd, "RESULT.txt"), errors="replace").read()
aw = re.search(r"ARRIVE_WATCH1: (.*)", txt)
p95 = re.search(r"跟踪 p95=([\d.]+) m", txt)
row = ("| %s | %s | %s | %s | %s | raw%s/smj%s | %s | %s | %s |" % (
    j["dir"], j.get("verdict"),
    "/".join(str(f) for f in x.get("four") or []),
    (aw.group(1)[:70] if aw else "?"),
    (p95.group(1) if p95 else "?"),
    x.get("fj_raw"), x.get("fj_smj"),
    "有" if x.get("env_sig") else "无",
    "%s(bas_pk=%s,ate=%s)" % ("健康" if v.get("pass_vins") else "异常",
                              (v.get("bas") or {}).get("peak"),
                              (v.get("ate") or {}).get("ate_rmse_m")),
    rd))
print("<!-- T3 intake 自动生成(人审后入账;--auto-ledger 跳过人审) -->")
print("| 轮 | 判决 | 四指标 | 到位双口径 | p95 | J0(raw/smj) | 污染 | vins域 | 证据 |")
print("|---|---|---|---|---|---|---|---|---|")
print(row)
PYEOF
cat "$RD/ledger_line.md"
if [ "$AUTO" = "1" ]; then
  tail -n +3 "$RD/ledger_line.md" >> "$HOME/catkin_ws/sitl_sim/t3_experiments.md"
  echo "(已 --auto-ledger 追加台账)"
fi

echo "== [intake 3/3] figs 再生(X7 数据源;fig2/3/5 逐轮 JSON 已就位) =="
echo "  python3 $A/t3_xline_report_figs.py --csv $CSV --runs-glob '$RD' --out-dir ~/catkin_ws/sitl_sim/docs/figs"
echo "== intake 完成: $(basename "$RD") | 判决=$(python3 -c "import json;print(json.load(open('$RD/wa_gate_online.json'))['verdict'])") =="
