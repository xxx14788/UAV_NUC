#!/usr/bin/env python3
"""Deterministic probe tests without ROS or a simulator."""
import importlib.util
from pathlib import Path
import struct
import unittest

SPEC = importlib.util.spec_from_file_location('probe', Path(__file__).resolve().parents[2] / 'sitl_sim/baseline_probe.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


def row(stamp, arrival=None, clock=None, seq=None, topic=P.LEFT):
    value = dict.fromkeys(P.FIELDS)
    value.update(topic=topic, stamp_ns=stamp, arrival_ns=stamp if arrival is None else arrival,
                 clock_ns=clock, seq=seq)
    return value


class ProbeTests(unittest.TestCase):
    def test_header(self):
        self.assertEqual(P.header(struct.pack('<IIII', 12, 3, 4, 3) + b'cam'), (3000000004, 12))
        for value in (b'', struct.pack('<IIII', 0, 0, 1000000000, 0), struct.pack('<IIII', 0, 0, 0, 5)):
            with self.assertRaises(ValueError):
                P.header(value)

    def test_known_frequency(self):
        rows = [row(round(i * 1e9 / 30), round(i * 1e9 / 15), seq=i) for i in range(301)]
        result = P.stream_stats(rows, 30)
        self.assertAlmostEqual(result['sim_stamp_hz'], 30)
        self.assertAlmostEqual(result['wall_hz'], 15)
        self.assertEqual(result['nominal_missing_estimate'], 0)
        self.assertEqual(result['seq_missing'], 0)

    def test_missing_duplicate_regression(self):
        stamps = [0, 33333333, 100000000, 100000000, 90000000]
        rows = [row(s, i * 100000000, seq=q) for i, (s, q) in enumerate(zip(stamps, [0, 1, 3, 4, 0]))]
        result = P.stream_stats(rows, 30)
        self.assertEqual(result['nominal_missing_estimate'], 1)
        self.assertEqual(result['stamp_duplicates'], 1)
        self.assertEqual(result['stamp_regressions'], 1)
        self.assertEqual(result['seq_missing'], 1)
        self.assertEqual(result['seq_resets'], 1)

    def test_pairing(self):
        a = [row(x) for x in (0, 10, 10, 20)]
        b = [row(x) for x in (0, 10, 21)]
        result = P.stereo_stats(a, b)
        self.assertEqual(result['exact_pairs'], 2)
        self.assertEqual(result['left_exact_fraction'], .5)
        self.assertEqual(P.stereo_stats([], [])['left_exact_fraction'], None)

    def test_rtf(self):
        values = [row(None, i * 1000000000, i * 500000000) for i in range(5)]
        self.assertAlmostEqual(P.clock_stats(values)['overall_rtf'], .5)
        values.append(row(None, 5000000000, 0))
        self.assertIsNone(P.clock_stats(values)['overall_rtf'])
        self.assertEqual(P.clock_stats(values)['regressions'], 1)

    def test_empty_not_success(self):
        result = P.summarize([], 40, 'hover', 40)
        self.assertFalse(result['measurement_complete'])
        self.assertFalse(result['hover_window_valid'])
        self.assertIsNone(result['streams'][P.LEFT]['wall_hz'])

    def test_complete_and_early_stop(self):
        values = []
        for topic in P.TOPICS:
            for i in range(41):
                value = row(i * 1000000000, seq=i, topic=topic, clock=i * 1000000000)
                value.update(armed=True, x=0., y=0., z=1.)
                values.append(value)
        self.assertTrue(P.summarize(values, 40, 'hover', 40)['hover_window_valid'])
        self.assertFalse(P.summarize(values, 40, 'hover', 20)['measurement_complete'])


if __name__ == '__main__':
    unittest.main()
