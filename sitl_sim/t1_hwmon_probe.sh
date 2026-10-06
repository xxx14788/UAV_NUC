#!/usr/bin/env bash
# t1_hwmon_probe.sh — 任务书 v11.17 §1.3 随轮硬件遥测探针（采样面预注册冻结,纯取证）
# usage: t1_hwmon_probe.sh <round_dir>   (轮脚本起/停;kill TERM/INT 即退)
# 采样面(prereg v1 冻结):
#   1Hz TSV: epoch | load1/5/15 | runnable | ctxt_cum(全局上下文切换累计) |
#            freq_min/avg/max(kHz,28核 scaling_cur_freq 分布) |
#            pkg_temp(x86_pkg_temp,0.001°C) | thm_flag(pkg_temp≥80000=Intel high 档)
#   dmesg 全量尾随(-wT)→hwmon_dmesg.log(USB/WiFi 事件判读面;分析期过滤)
#   历史轮无 hwmon=覆盖缺口注记不回填(任务书原文)
D="$1"; [ -d "$D" ] || { echo "hwmon: bad dir $D"; exit 1; }
TSV="$D/hwmon.tsv"; DML="$D/hwmon_dmesg.log"
trap 'exit 0' TERM INT
dmesg -wT > "$DML" 2>/dev/null &
DM=$!
trap 'kill $DM 2>/dev/null; exit 0' TERM INT
CPUS=$(grep -c ^processor /proc/cpuinfo)
MAXF=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq 2>/dev/null || echo 0)
echo -e "epoch\tload1\tload5\tload15\trunnable\tctxt_cum\tfreq_min\tfreq_avg\tfreq_max\tmaxf_ref\tpkg_temp\tthm_flag" > "$TSV"
while :; do
  L=$(head -1 /proc/loadavg)
  CT=$(awk '/^ctxt/{print $2}' /proc/stat)
  FS=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq 2>/dev/null | sort -n)
  FMIN=$(echo "$FS" | head -1); FMAX=$(echo "$FS" | tail -1)
  FAVG=$(echo "$FS" | awk '{s+=$1;n++}END{if(n)printf "%.0f",s/n}')
  TP=$(cat /sys/class/thermal/thermal_zone1/temp 2>/dev/null || echo -1)
  TH=0; [ "$TP" -ge 80000 ] 2>/dev/null && TH=1
  echo -e "$(date +%s)\t$(echo "$L" | cut -d' ' -f1-3 | tr ' ' '\t')\t$(echo "$L" | awk '{print $4}' | cut -d/ -f1)\t$CT\t${FMIN:-0}\t${FAVG:-0}\t${FMAX:-0}\t$MAXF\t$TP\t$TH" >> "$TSV"
  sleep 1
done
