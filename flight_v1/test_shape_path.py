#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""shape_path.py 纯几何单测（不依赖 ROS）。"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shape_path as sp


class TestCircle(unittest.TestCase):
    def setUp(self):
        self.pts, self.cum, self.total = sp.build_path("circle", circle_diameter=2.2)

    def test_length(self):
        self.assertAlmostEqual(self.total, math.pi * 2.2, delta=0.01)

    def test_start_end_at_origin(self):
        p0 = sp.point_at(self.pts, self.cum, 0.0)
        p1 = sp.point_at(self.pts, self.cum, self.total)
        self.assertLess(math.hypot(*p0), 0.01)
        self.assertLess(math.hypot(*p1), 0.01)

    def test_radius_and_bounds(self):
        fwd, lat, minx = sp.bounds(self.pts)
        self.assertAlmostEqual(fwd, 2.2, places=3)
        self.assertAlmostEqual(lat, 1.1, places=3)
        self.assertAlmostEqual(minx, 0.0, places=3)
        for s in (0.5, 1.5, 3.0, 5.0):
            x, y = sp.point_at(self.pts, self.cum, s)
            self.assertAlmostEqual(math.hypot(x - 1.1, y), 1.1, places=3)

    def test_obstacle_clearance(self):
        d = sp.box_surface_distance(self.pts, (1.0, 0.0), 0.5)
        self.assertGreater(d, 0.64)
        self.assertLess(d, 0.72)   # 圆心 (1.1,0)，最近是箱角 -> ~0.67


class TestEight(unittest.TestCase):
    def setUp(self):
        self.pts, self.cum, self.total = sp.build_path("eight", eight_length=4.0, eight_width=2.2)

    def test_start_end_at_origin(self):
        for s in (0.0, self.total):
            x, y = sp.point_at(self.pts, self.cum, s)
            self.assertLess(math.hypot(x, y), 0.02)

    def test_bounds(self):
        fwd, lat, minx = sp.bounds(self.pts)
        self.assertAlmostEqual(fwd, 4.0, places=2)
        self.assertAlmostEqual(lat, 1.1, places=2)
        self.assertAlmostEqual(minx, 0.0, places=2)

    def test_obstacle_clearance(self):
        d = sp.box_surface_distance(self.pts, (1.0, 0.0), 0.5)
        self.assertGreater(d, 0.32)
        self.assertLess(d, 0.45)   # 2.2 m 宽：箱面 ~0.38，膨胀层边界附近

    def test_length_positive(self):
        self.assertGreater(self.total, 10.0)
        self.assertLess(self.total, 13.0)

    def test_projection_local_at_crossing(self):
        # 交叉点 (2,0) 在弧长 1/4 和 3/4 各出现一次；局部窗口不能跳到另一瓣
        s1 = self.total * 0.25
        x, y = sp.point_at(self.pts, self.cum, s1)
        got = sp.project(self.pts, self.cum, (x, y), s1, 1.2)
        self.assertLess(abs(got - s1), 0.20)


class TestBoth(unittest.TestCase):
    def test_both_total_and_closure(self):
        p1, c1, t1 = sp.build_path("circle", circle_diameter=2.2)
        p2, c2, t2 = sp.build_path("eight", eight_length=4.0, eight_width=2.2)
        p, c, t = sp.build_path("both", circle_diameter=2.2, eight_length=4.0, eight_width=2.2)
        self.assertAlmostEqual(t, t1 + t2, delta=0.05)
        self.assertEqual(len(p), len(p1) + len(p2))
        x, y = sp.point_at(p, c, 0.0)
        self.assertLess(math.hypot(x, y), 0.02)


class TestCarrot(unittest.TestCase):
    def test_rate_limit_and_clamp(self):
        s = 0.0
        for _ in range(100):
            s = sp.next_carrot(s, 0.0, 0.1, 0.3, 0.6, 10.0)
        self.assertAlmostEqual(s, 0.6, places=6)
        self.assertAlmostEqual(sp.next_carrot(0.0, 0.0, 0.1, 0.3, 0.6, 10.0), 0.03, places=6)

    def test_no_backwards_and_end_clamp(self):
        self.assertGreaterEqual(sp.next_carrot(2.0, 0.5, 0.1, 0.3, 0.6, 10.0), 2.0)
        self.assertLessEqual(sp.next_carrot(9.9, 9.8, 0.1, 0.3, 0.6, 10.0), 10.0)


class TestRotate(unittest.TestCase):
    def test_rotate_90(self):
        p, c, t = sp.build_path("eight", eight_length=4.0, eight_width=2.2, rotate_deg=90.0)
        fwd, lat, minx = sp.bounds(p)
        self.assertAlmostEqual(lat, 4.0, places=2)
        self.assertAlmostEqual(fwd, 1.1, places=2)


class TestMetrics(unittest.TestCase):
    def test_circle_curvature(self):
        p, c, _ = sp.build_path("circle", circle_diameter=2.2)
        m = sp.path_metrics(p, c, 0.30)
        self.assertAlmostEqual(m["kmax"], 1.0 / 1.1, delta=0.03)
        self.assertLess(m["acc_centripetal"], 4.0)

    def test_milestones(self):
        ms = sp.milestones(10.0, 2, 8)
        self.assertEqual(len(ms), 8)
        self.assertAlmostEqual(ms[0], 2.5)
        self.assertAlmostEqual(ms[-1], 20.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
