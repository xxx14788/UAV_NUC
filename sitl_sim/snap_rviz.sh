#!/usr/bin/env bash
# 一键截图 rviz(:99)（T3-W5，T4 视觉线判读穿墙检查素材）。
# 前置: DISPLAY=:99 有常驻 rviz(B0 方法,见 STATUS 2026-09-26);本脚本只抓屏不动 rviz。
# 用法: snap_rviz.sh [名字前缀]   输出 ~/sitl_sim/vision_inputs/<前缀>_HHMMSS.png
# 依赖: imagemagick(import 或 xwd+convert 二选一)
set -u
PREFIX="${1:-rviz_traj}"
OUT="$HOME/sitl_sim/vision_inputs"
mkdir -p "$OUT"
NAME="$OUT/${PREFIX}_$(date +%H%M%S).png"

# 等渲染稳定一帧的时间不需要——rviz 常驻自刷新,直接抓根窗口
if command -v import >/dev/null 2>&1; then
    DISPLAY=:99 import -window root "$NAME"
elif command -v xwd >/dev/null 2>&1 && command -v convert >/dev/null 2>&1; then
    DISPLAY=:99 xwd -root -silent | convert xwd:- "$NAME"
else
    echo "ERROR: 无 import/xwd+convert(image_magick 未装?)" >&2
    exit 1
fi

if [ -s "$NAME" ]; then
    echo "saved: $NAME ($(stat -c%s "$NAME") bytes)"
else
    echo "ERROR: 截图失败或为空(Xvfb :99 上没有 rviz?)" >&2
    exit 1
fi
