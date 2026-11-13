#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""形状路径纯几何（2026-11-13，flight_shape_mission.py 专用）。

坐标约定：VINS world 系，原点 = 起飞点，+x = 起飞时机头朝向。
所有形状都从**起飞点 (0,0)** 起步、回到起飞点闭环，避免跨障碍入场。

- 圆：直径 d，圆心 (d/2, 0)，从原点起逆时针一圈；
- 八字：长 L（沿 +x）、宽 W（沿 y），Gerono x=L/2 + L/2·sin t，y=W/2·sin 2t，
  中心 (L/2, 0)，从左尖端（原点）起；
- both：圆 + 八字串联（两者都在原点闭合），用于一轮起飞飞两个形状。
"""
import bisect
import math


def build_path(shape, circle_diameter=2.2, eight_length=4.0, eight_width=2.2,
               n=2400, rotate_deg=0.0):
    """返回 (pts, cum, total)。pts 为闭合折线（不重复首点）；cum 长度 n+1。"""
    if n < 64:
        raise ValueError("n 太小")
    if shape not in ("circle", "eight", "both"):
        raise ValueError("shape 只能是 circle/eight/both")
    pts = []
    if shape in ("circle", "both"):
        r = circle_diameter / 2.0
        cx = r
        for i in range(n):
            th = math.pi + 2.0 * math.pi * i / n   # 从原点 (θ=π) 起，逆时针
            pts.append((cx + r * math.cos(th), r * math.sin(th)))
    if shape in ("eight", "both"):
        a = eight_length / 2.0
        b = eight_width / 2.0
        cx = a
        for i in range(n):
            t = 1.5 * math.pi + 2.0 * math.pi * i / n  # 从左尖端 (t=3π/2) 起
            pts.append((cx + a * math.sin(t), b * math.sin(2.0 * t)))
    if rotate_deg:
        c, s = math.cos(math.radians(rotate_deg)), math.sin(math.radians(rotate_deg))
        pts = [(c * x - s * y, s * x + c * y) for x, y in pts]
    cum = [0.0]
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    return pts, cum, cum[-1]


def point_at(pts, cum, s):
    """按弧长取点（s 按整圈取模）。"""
    total = cum[-1]
    if total <= 0:
        return pts[0]
    s = s % total
    i = bisect.bisect_right(cum, s) - 1
    i = min(max(i, 0), len(pts) - 1)
    s0, s1 = cum[i], cum[i + 1]
    f = 0.0 if s1 <= s0 else (s - s0) / (s1 - s0)
    p0, p1 = pts[i], pts[(i + 1) % len(pts)]
    return (p0[0] + f * (p1[0] - p0[0]), p0[1] + f * (p1[1] - p0[1]))


def project(pts, cum, p, s_hint, window, step=0.02):
    """在 [s_hint-window, s_hint+window] 内找最近点的弧长（局部搜索，交叉不跳瓣）。"""
    best_d, best_s = float("inf"), s_hint
    s = s_hint - window
    while s <= s_hint + window + 1e-9:
        q = point_at(pts, cum, s)
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        if d < best_d:
            best_d, best_s = d, s
        s += step
    return best_s


def next_carrot(s_cursor, s_proj, dt, speed, lookahead, s_end):
    """目标沿弧长前进：≤speed*dt，≤s_proj+lookahead，≤终点；绝不后退。"""
    tgt = min(s_cursor + speed * dt, s_proj + lookahead, s_end)
    return max(s_cursor, tgt)


def path_metrics(pts, cum, speed):
    """最大曲率与对应向心加速度（三点外接圆采样）。"""
    total = cum[-1]
    kmax = 0.0
    n = len(pts)
    for i in range(0, n, max(1, n // 800)):
        a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        ab = math.hypot(b[0] - a[0], b[1] - a[1])
        bc = math.hypot(c[0] - b[0], c[1] - b[1])
        ca = math.hypot(a[0] - c[0], a[1] - c[1])
        area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        if ab * bc * ca > 1e-12:
            kmax = max(kmax, 2.0 * area2 / (ab * bc * ca))
    return {"length": total, "kmax": kmax, "acc_centripetal": speed * speed * kmax}


def bounds(pts):
    """返回 (max_forward_x, max_abs_y, min_x)：形状包络。"""
    return (max(p[0] for p in pts), max(abs(p[1]) for p in pts),
            min(p[0] for p in pts))


def box_surface_distance(pts, obstacle, size):
    """路径点到轴对齐方块表面的最小距离（方块中心 obstacle，边长 size）。"""
    h = size / 2.0
    best = float("inf")
    for x, y in pts:
        dx = abs(x - obstacle[0]) - h
        dy = abs(y - obstacle[1]) - h
        best = min(best, math.hypot(max(dx, 0.0), max(dy, 0.0)))
    return best


def milestones(total, laps, n=8):
    """总里程上的 n 个里程碑（含终点）。"""
    return [total * laps * k / float(n) for k in range(1, n + 1)]
