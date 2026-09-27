#!/usr/bin/env bash
# SITL 运行时锁(T1-W5;T1/T2/T3 三任务共用仲裁)。
# 符号链接创建是原子操作:创建成功=持锁,失败=别人持有。
# 用法:
#   sitl_lock.sh get [owner]    # 获取(owner 缺省=调用者标识,如 T1/T2/T3)
#   sitl_lock.sh release        # 释放(仅持锁者;用 readlink 核对 owner)
#   sitl_lock.sh force [owner]  # 抢占:必须先确认 pgrep -f "bin/px4|gzserver" 为 0
#   sitl_lock.sh status         # 查看当前持锁者
# 持锁上限 30 分钟/段;超时可 force 抢占(抢占前必须确认无 SITL 进程)。
set -u
LOCK="$HOME/sitl_sim/SITL.lock"
OWNER="${2:-$(whoami)-$$-$(date +%H%M)}"

case "${1:-}" in
get)
    if ln -s "$OWNER" "$LOCK" 2>/dev/null; then
        echo "locked owner=$OWNER"
    else
        echo "HELD by $(readlink "$LOCK" 2>/dev/null || echo unknown)" >&2
        exit 1
    fi
    ;;
release)
    # 属主前缀(如 T1/T2/T3);不传=任意锁(慎用,跨任务抢占语义)
    PFX="${2:-}"
    if [ -L "$LOCK" ]; then
        cur=$(readlink "$LOCK")
        if [ -z "$PFX" ] || echo "$cur" | grep -q "^$PFX"; then
            rm -f "$LOCK" && echo "released: $cur"
        else
            echo "锁属 $cur,前缀 $PFX 不符,拒绝释放" >&2
            exit 1
        fi
    else
        echo "无锁"
    fi
    ;;
force)
    n=$(pgrep -cf "bin/px4|gzserver" || true)
    if [ "${n:-0}" != "0" ]; then
        echo "拒绝抢占:仍有 $n 个 SITL 进程在跑,先确认持锁者已收尾" >&2
        exit 1
    fi
    rm -f "$LOCK"
    ln -s "$OWNER" "$LOCK" 2>/dev/null && echo "forced owner=$OWNER" || { echo "抢占失败" >&2; exit 1; }
    ;;
status)
    [ -L "$LOCK" ] && echo "held by $(readlink "$LOCK")" || echo "free"
    ;;
*)
    echo "用法: $0 {get|release|force|status} [owner|owner前缀]" >&2
    exit 2
    ;;
esac
