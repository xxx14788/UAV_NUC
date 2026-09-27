#!/usr/bin/env bash
# 日志暴涨防御守护(T1-W5;防 5.8GB 日志重演)。
# 每 60s 扫一遍 ~/sitl_sim 下的一级 *.log 与 smoke_runs/**/sitl.log:
#   >1GB → 保留末 10MB 截断(rename 原子替换,避免截断正在写的文件句柄错乱)
# 用法: nohup bash log_truncate_guard.sh > /dev/null 2>&1 &
# 停止: pkill -f log_truncate_guard
set -u
LIMIT_MB=1024
KEEP_MB=10
DIR="$HOME/sitl_sim"

while true; do
    find "$DIR" -maxdepth 2 -name "*.log" -type f 2>/dev/null | while read -r f; do
        mb=$(( $(stat -c %s "$f" 2>/dev/null || echo 0) / 1048576 ))
        if [ "$mb" -gt "$LIMIT_MB" ]; then
            tail -c $(( KEEP_MB * 1048576 )) "$f" > "$f.tail" 2>/dev/null \
                && cat "$f.tail" > "$f" && rm -f "$f.tail" \
                && echo "$(date '+%F %H:%M:%S') truncated $f (${mb}MB -> ${KEEP_MB}MB)" >> "$DIR/truncate_guard.log"
        fi
    done
    sleep 60
done
