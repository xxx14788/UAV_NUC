#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flight_shape.py 纯逻辑单测（不依赖 ROS）。"""
import importlib.util
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("flight_shape", os.path.join(HERE, "flight_shape.py"))
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)


class TestPaths(unittest.TestCase):
    def test_circle_length(self):
        pts, cum, total = fs.build_path("circle", radius=1.0)
        self.assertAlmostEqual(total, 2 * math.pi, delta=0.01)
        self.assertEqual(len(pts), 2400)
        self.assertAlmostEqual(cum[-1], total)

    def test_circle_wrap(self):
        pts, cum, total = fs.build_path("circle", radius=1.0)
        p0 = fs.point_at(pts, cum, 0.0)
        p1 = fs.point_at(pts, cum, total)
        p2 = fs.point_at(pts, cum, 2 * total + 0.0)
        for a, b in ((p0, p1), (p0, p2)):
            self.assertAlmostEqual(a[0], b[0], places=6)
            self.assertAlmostEqual(a[1], b[1], places=6)

    def test_circle_radius(self):
        pts, cum, _ = fs.build_path("circle", radius=1.2)
        for s in (0.0, 0.7, 2.1, 5.0):
            x, y = fs.point_at(pts, cum, s)
            self.assertAlmostEqual(math.hypot(x, y), 1.2, places=3)

    def test_eight_shape(self):
        pts, cum, total = fs.build_path("eight", amp_x=1.0, amp_y=0.7)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.assertAlmostEqual(max(xs), 1.0, delta=0.01)
        self.assertAlmostEqual(min(xs), -1.0, delta=0.01)
        self.assertAlmostEqual(max(ys), 0.7, delta=0.01)
        self.assertAlmostEqual(min(ys), -0.7, delta=0.01)
        x0, y0 = fs.point_at(pts, cum, 0.0)
        self.assertLess(math.hypot(x0, y0), 0.02)   # 起点在中心
        self.assertGreater(total, 4.0)              # 周长合理


class TestProjection(unittest.TestCase):
    def test_project_known_point(self):
        pts, cum, total = fs.build_path("circle", radius=1.0)
        s_true = 1.30
        x, y = fs.point_at(pts, cum, s_true)
        s = fs.project(pts, cum, (x, y), s_true, 1.2)
        self.assertAlmostEqual(s, s_true, delta=0.05)

    def test_project_stays_local(self):
        # 八字交叉点：两条瓣在空间上重合，但弧长相差半圈；局部搜索不能跳到另一瓣
        pts, cum, total = fs.build_path("eight", 1.0, 0.7)
        s = total * 0.02                     # 右瓣刚出中心
        x, y = fs.point_at(pts, cum, s)
        got = fs.project(pts, cum, (x, y), s, 1.2)
        self.assertLess(abs(got - s), 0.15)
        s2 = total * 0.52                    # 左瓣刚出中心
        x2, y2 = fs.point_at(pts, cum, s2)
        got2 = fs.project(pts, cum, (x2, y2), s2, 1.2)
        self.assertLess(abs(got2 - s2), 0.15)


class TestCarrot(unittest.TestCase):
    def test_rate_limit(self):
        s = fs.next_carrot(0.0, 0.0, 0.1, 0.4, 0.6, 10.0)
        self.assertAlmostEqual(s, 0.04)

    def test_lookahead_clamp(self):
        # 飞机没动 -> 目标最多到 s_proj+lookahead
        s = 0.0
        for _ in range(100):
            s = fs.next_carrot(s, 0.0, 0.1, 0.4, 0.6, 10.0)
        self.assertAlmostEqual(s, 0.6, places=6)

    def test_no_backwards(self):
        # 投影回退（抖动/遮挡）时目标不许后退
        s = fs.next_carrot(2.0, 0.5, 0.1, 0.4, 0.6, 10.0)
        self.assertGreaterEqual(s, 2.0)

    def test_end_clamp(self):
        s = fs.next_carrot(9.9, 9.8, 0.1, 0.5, 0.6, 10.0)
        self.assertLessEqual(s, 10.0)


class TestChecks(unittest.TestCase):
    def test_bounds_ok(self):
        pts, _, _ = fs.build_path("circle", radius=1.0)
        self.assertGreaterEqual(fs.bounds_margin(pts, 3.5, 0.25), 0.0)

    def test_bounds_fail(self):
        pts, _, _ = fs.build_path("circle", radius=1.6)
        self.assertLess(fs.bounds_margin(pts, 3.5, 0.25), 0.0)

    def test_circle_curvature(self):
        pts, cum, _ = fs.build_path("circle", radius=1.0)
        m = fs.path_metrics(pts, cum, 0.35)
        self.assertAlmostEqual(m["kmax"], 1.0, delta=0.02)
        self.assertLess(m["acc_centripetal"], 4.0)

    def test_eight_curvature_positive(self):
        pts, cum, _ = fs.build_path("eight", 1.0, 0.7)
        m = fs.path_metrics(pts, cum, 0.35)
        self.assertGreater(m["kmax"], 1.0)   # 八字尖端比 1 m 圆更弯

    def test_cli_dry_run(self):
        self.assertEqual(fs.main(["--shape", "circle", "--dry-run"]), 0)
        self.assertEqual(fs.main(["--shape", "eight", "--dry-run"]), 0)

    def test_cli_rejects_bad_speed(self):
        with self.assertRaises(SystemExit):
            fs.main(["--speed", "0.8", "--dry-run"])

    def test_cli_rejects_out_of_area(self):
        self.assertEqual(fs.main(["--radius", "1.8", "--dry-run"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
