#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_trichotomy selftest（红线 24 流程件;T3 v10.3 单元 1）。

合成样例（临时目录,零外部依赖）:
  S1 phys_green            : PASS+四绿+无门干预
  S2 gate_intercept        : gatehit json(watchdog 受控中止+landed)+disarm+无faildet
  S3 true_fail             : FAIL+无门干预
  S4 intercept_incomplete  : gatehit json+disarm=0(恢复链缺)
  S5 gate_intercept(legacy): faildet=1+--cf controlled(legacy 门轮 not2fail 豁免面)
  S6 gate_intercept(cost)  : cost gate 行+--cf controlled+LANDING 降落证据
断言 t3_trichotomy.classify 输出;N/N PASS 才算过。
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t3_trichotomy as T

COST_LINE = '[ WARN] [1760000000.000, 51.872]: cost gate: streak=3 over 12.5x short-window median, reboot\n'


def mk(dirname, result_lines, vins_lines=(), gatehit=None, pregate=None):
    d = os.path.join(dirname)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'RESULT.txt'), 'w') as f:
        f.write('\n'.join(result_lines) + '\n')
    with open(os.path.join(d, 'simvins.log'), 'w') as f:
        f.writelines(vins_lines)
    if gatehit is not None:
        with open(os.path.join(d, 'gatehit_S1.json'), 'w') as f:
            json.dump(gatehit, f)
    if pregate is not None:
        with open(os.path.join(d, 'pregate_S1.json'), 'w') as f:
            json.dump(pregate, f)
    return d


def main():
    tmp = tempfile.mkdtemp(prefix='tri_selftest_')
    cases = []
    try:
        # S1 物理绿
        d = mk(os.path.join(tmp, 'S1'),
               ['RESULT=PASS  (证据: tmp)', 'auto_disarm->1', 'LANDING: z_end=0.080 (<0.15)->1'])
        cases.append(('S1 phys_green', d, None, 'phys_green'))
        # S2 门拦截计入（watchdog 面）
        d = mk(os.path.join(tmp, 'S2'),
               ['RESULT=FAIL  (证据: tmp)', 'auto_disarm->1', 'LANDING: z_end=0.100 (<0.15)->1'],
               gatehit={'round': 'S2', 't_trig': 66.3, 'metric': 'cost', 'value': 14.2,
                        'baseline': 1.1, 'gate': 'adaptive', 'action': 'goal-stop+land', 'landed': 1})
        cases.append(('S2 gate_intercept(watchdog)', d, None, 'gate_intercept'))
        # S3 真 FAIL
        d = mk(os.path.join(tmp, 'S3'),
               ['RESULT=FAIL  (证据: tmp)', 'auto_disarm->1'])
        cases.append(('S3 true_fail', d, None, 'true_fail'))
        # S4 拦截不完整（disarm=0）
        d = mk(os.path.join(tmp, 'S4'),
               ['RESULT=FAIL  (证据: tmp)', 'auto_disarm->0'],
               gatehit={'round': 'S4', 't_trig': 40.2, 'metric': 'cost', 'value': 22.0,
                        'baseline': 1.0, 'gate': 'abs', 'action': 'goal-stop+land', 'landed': 1})
        cases.append(('S4 intercept_incomplete', d, None, 'intercept_incomplete'))
        # S5 legacy 门轮（faildet=1+cf=controlled → not2fail 豁免）
        d = mk(os.path.join(tmp, 'S5'),
               ['RESULT=FAIL  (证据: tmp)', 'auto_disarm->1', 'LANDING: z_end=0.110 (<0.15)->1'],
               vins_lines=['[ WARN] [1760000000.000, 49.376]: failure detection!\n'])
        cases.append(('S5 gate_intercept(legacy+cf)', d, 'controlled', 'gate_intercept'))
        # S6 cost 门轮（COSTGATE-FIRE+cf=controlled+LANDING 降落）
        d = mk(os.path.join(tmp, 'S6'),
               ['RESULT=FAIL  (证据: tmp)', 'auto_disarm->1', 'LANDING: z_end=0.095 (<0.15)->1'],
               vins_lines=[COST_LINE])
        cases.append(('S6 gate_intercept(cost+cf)', d, 'controlled', 'gate_intercept'))

        npass = 0
        for name, d, cf, expect in cases:
            r = T.classify(d, cf)
            ok = r['class'] == expect
            npass += 1 if ok else 0
            print('%-32s expect=%-20s got=%-20s %s' % (name, expect, r['class'], 'PASS' if ok else 'FAIL'))
            if not ok:
                print('   detail: %s' % '; '.join(r['detail']))
        print('trichotomy selftest: %d/%d PASS' % (npass, len(cases)))
        sys.exit(0 if npass == len(cases) else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
