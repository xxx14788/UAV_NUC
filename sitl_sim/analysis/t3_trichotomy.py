#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3 v10.3 单元 1: 三列分账权威分类器（计数口径 v1;2026-10-07 冻结;红线 24 流程上线）。

口径（prereg xline_prereg_v1_1.md §2.9;用户 10-07 tag 口径裁定落地）:
  物理绿 phys_green      = RESULT=PASS ∧ 门干预证据=0（gatehit/pregate-block/COSTGATE-FIRE/faildet 全无）
  门拦截计入 gate_intercept = 门干预≥1 ∧ 完整恢复四条全齐:
      [1] 受控中止   = gatehit.action ∈ 受控中止链（goal-stop+land / land-fallback 降级预案）
                       ∨ cf=controlled（栈内 cost 门 L1+L2 双证;legacy 轮兼容面）
      [2] 完整降落   = gatehit.landed=1 ∨ LANDING 行 z_end<0.15m ∨ (RES=PASS∧disarm=1: 任务完成含落地)
      [3] disarm=1   = RESULT.txt 'auto_disarm->1'
      [4] 无 T2fail  = faildet_n=0 ∨ (legacy 门轮: faildet 全部先于恢复窗 ∧ cf=controlled)
  拦截不完整 intercept_incomplete = 门干预≥1 ∧ 四条不齐（不计红不计绿;批语义=换轮重试占门拦截预算 ≤3/格）
  真 FAIL true_fail = 其余（现行 §2.5 四指标红面;door 撞门型另注,不属门拦截）

门干预证据优先级（新批主面→兼容面）:
  1) gatehit_<round>.json（T1 v11.20 三层防线契约文件;字段=t_trig/metric/value/baseline/gate/action/landed）
  2) COSTGATE-FIRE 行（栈内 cost 门:'cost gate: streak=N over Mx short-window median, reboot'）
  3) 'failure detection!'（legacy 门;faildet_n 计数=T2fail 面）
  4) pregate_<round>.json verdict=block（起飞前门拒绝;轮未起飞域→分母语义,不入三列,仅标注）

历史轮零重判:本口径只对 2026-10-07 后新批生效;历史轮判读保持原账（§2.9-b 条款）。
5/5 判定（x4_batch 消费）= 物理绿+门拦截计入 ≥5 ∧ 物理绿 ≥3（默认案,--phys-floor 可调=用户窗内可改）。

用法: t3_trichotomy.py <run_dir> [--cf <controlled|clean|...>]
输出(冻结格式,两行):
  GATEHIT-STAT: n=<n> ts=<t> val=<v> kind=<k> chain=abort:<b>,land:<b>,disarm:<b>,not2fail:<b>
  TRICHOTOMY: class=<phys_green|gate_intercept|intercept_incomplete|true_fail> detail=<...>
"""
import glob
import json
import os
import re
import sys

RE_COSTFIRE = re.compile(r'cost gate: streak=(\d+) over ([\d.]+)x short-window median, reboot')
RE_WARNHDR = re.compile(r'\[[\d.]+, ([\d.]+)\]:')
LAND_Z_MAX = 0.15
ABORT_ACTIONS = ('goal-stop', 'controlled-abort', 'land-fallback', 'land', 'goal_stop')


def classify(run_dir, cf_state=None):
    out = {"n": 0, "ts": None, "val": None, "kind": None,
           "abort": 0, "land": 0, "disarm": 0, "not2fail": 0,
           "class": None, "detail": [], "pregate_block": 0}
    rp = os.path.join(run_dir, 'RESULT.txt')
    res_txt = open(rp, errors='ignore').read() if os.path.exists(rp) else ''
    m = re.search(r'RESULT=(PASS|FAIL|ENV-FAIL)', res_txt)
    res = m.group(1) if m else 'NO-RESULT'
    disarm = 1 if re.search(r'auto_disarm->1', res_txt) else 0
    z_end = None
    mz = re.search(r'LANDING: z_end=([0-9.]+)', res_txt)
    if mz:
        z_end = float(mz.group(1))

    vlog = os.path.join(run_dir, 'simvins.log')
    fires, faildet_n = [], 0
    if os.path.exists(vlog):
        with open(vlog, errors='replace') as f:
            for line in f:
                mm = RE_COSTFIRE.search(line)
                if mm:
                    tm = RE_WARNHDR.search(line)
                    fires.append((float(tm.group(1)) if tm else None, int(mm.group(1)), float(mm.group(2))))
                if 'failure detection!' in line:
                    faildet_n += 1

    # 门干预证据收集（优先级: gatehit json > cost 门行 > legacy faildet）
    gatehits = sorted(glob.glob(os.path.join(run_dir, 'gatehit_*.json')))
    gh = None
    if gatehits:
        try:
            gh = json.load(open(gatehits[0]))
        except (OSError, ValueError):
            gh = None
    pregates = sorted(glob.glob(os.path.join(run_dir, 'pregate_*.json')))
    pg_block = 0
    for p in pregates:
        try:
            if json.load(open(p)).get('verdict') == 'block':
                pg_block = 1
        except (OSError, ValueError):
            pass
    out['pregate_block'] = pg_block

    trig = 0
    if gh is not None:
        trig += 1
        out['kind'] = 'watchdog'
        out['ts'] = gh.get('t_trig')
        out['val'] = gh.get('value')
    elif fires:
        trig += 1
        out['kind'] = 'cost'
        out['ts'] = fires[0][0]
        out['val'] = 'streak=%s,ratio=%s' % (fires[0][1], fires[0][2])
    elif faildet_n > 0:
        trig += 1
        out['kind'] = 'legacy'
        out['ts'] = None
        out['val'] = 'faildet_n=%d' % faildet_n
    out['n'] = trig + (len(gatehits) - 1 if len(gatehits) > 1 else 0)

    # ---- 分类 ----
    if res == 'ENV-FAIL':
        out['class'] = 'env'
        out['detail'].append('RESULT=ENV-FAIL 环境面(不计三列)')
        return out
    if pg_block and res == 'NO-RESULT':
        out['class'] = 'pregate-block'
        out['detail'].append('起飞前门拒绝,轮未起飞(分母外,重试域)')
        return out

    if trig == 0:
        if res == 'PASS':
            out['class'] = 'phys_green'
            out['detail'].append('无门干预全绿')
        else:
            out['class'] = 'true_fail'
            out['detail'].append('无门干预的非 PASS(红面)')
        return out

    # 门干预≥1 → 四条恢复链判定
    cf_ok = (cf_state == 'controlled')
    if gh is not None:
        act = str(gh.get('action', ''))
        out['abort'] = 1 if any(k in act for k in ABORT_ACTIONS) else 0
        if gh.get('landed') == 1:
            out['land'] = 1
    else:
        out['abort'] = 1 if cf_ok else 0
    if not out['land']:
        if z_end is not None and z_end < LAND_Z_MAX:
            out['land'] = 1
        elif res == 'PASS' and disarm:
            out['land'] = 1
    out['disarm'] = disarm
    if faildet_n == 0:
        out['not2fail'] = 1
    elif gh is None and cf_ok:
        out['not2fail'] = 1  # legacy 门轮: faildet 即门本身,cf L2 已证恢复
    complete = all(out[k] for k in ('abort', 'land', 'disarm', 'not2fail'))
    if complete and (res == 'PASS' or out['abort'] or cf_ok):
        out['class'] = 'gate_intercept'
        out['detail'].append('门触发+完整恢复四条全齐(计入 5/5;成色注记)')
    else:
        out['class'] = 'intercept_incomplete'
        miss = [k for k in ('abort', 'land', 'disarm', 'not2fail') if not out[k]]
        out['detail'].append('恢复链缺:%s(不计红绿,重试域 ≤3/格)' % ','.join(miss) if miss else '四条齐但无 PASS/受控锚')
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    cf = None
    for i, a in enumerate(sys.argv):
        if a == '--cf' and i + 1 < len(sys.argv):
            cf = sys.argv[i + 1]
    if len(args) < 1:
        print('usage: t3_trichotomy.py <run_dir> [--cf <state>]', file=sys.stderr)
        sys.exit(2)
    r = classify(args[0], cf)
    print('GATEHIT-STAT: n=%d ts=%s val=%s kind=%s chain=abort:%d,land:%d,disarm:%d,not2fail:%d'
          % (r['n'], r['ts'] if r['ts'] is not None else 'NA',
             r['val'] if r['val'] is not None else 'NA', r['kind'] or 'NA',
             r['abort'], r['land'], r['disarm'], r['not2fail']))
    print('TRICHOTOMY: class=%s detail=%s' % (r['class'], ';'.join(r['detail'])))


if __name__ == '__main__':
    main()
