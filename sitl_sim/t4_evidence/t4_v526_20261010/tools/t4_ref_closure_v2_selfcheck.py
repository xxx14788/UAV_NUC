#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t4_ref_closure_v2_selfcheck.py -- self-verification driver for
t4_ref_closure_v2.py (v5.26 pool: 引用闭环 NUC 腿 v2).

Runs from the local Windows control host (D:/drone_VINS). Remote existence
checks are read-only only (ssh test -e / test -f / ls), per ask.

Inputs : tokens_v1report.tsv  (70 rows token<TAB>cat<TAB>kind<TAB>cnt<TAB>anchored
         extracted from the defective v1 report's missing-list)
Controls: 2 positive on NUC (must judge present) + 2 negative (must judge absent).

Method:
  A. v2 leg   : import v2, call nuc_check_batch(items)  (the fixed code path)
  B. GT leg   : independent hand-written remote sh (strict-path per token) +
                one combined basename find + driver-side pairing. Does NOT
                call any v2 function for judging.
  C. evidence : for every path v2 claims present/hint -> ssh test -f + ls -ld
  D. compare  : exact-string policy comparison per token, per-item table.
"""

import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import t4_ref_closure_v2 as v2  # noqa: E402

TOKENS_TSV = os.path.join(HERE, '..', 'tmp_v1fetch', 'tokens_v1report.tsv')

CONTROLS = [
    # (token, anchored, tag)
    ('~/.bashrc', True, 'CTRL-POS-tilde'),
    ('/home/uav/.bashrc', True, 'CTRL-POS-abs'),
    ('~/zzz_v2check_absent_ctrl.bag', True, 'CTRL-NEG-tilde'),
    ('zzz_ctrl_dir_v2check/zzz_nofind_ctrl.txt', False, 'CTRL-NEG-rel'),
]


def sh(host, script, timeout=240):
    """bytes transport: Windows text mode turns \\n into \\r\\n on stdin and
    the remote sh then dies with 'Syntax error' + empty stdout (observed
    live during self-check)."""
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
           '-o', 'StrictHostKeyChecking=no', host, 'sh', '-s']
    r = subprocess.run(cmd, input=script.encode('utf-8'),
                       capture_output=True, timeout=timeout)
    r.stdout = r.stdout.decode('utf-8', 'replace')
    return r


def load_items():
    items = []
    for line in io.open(TOKENS_TSV, encoding='utf-8'):
        parts = line.rstrip('\n').split('\t')
        if len(parts) >= 5 and parts[0]:
            items.append((parts[0], parts[4] == '1', parts[1]))
    return items


def gt_strict(tokens):
    """Independent strict-path ground truth; returns dict tok->path|None.
    Payload embedded in the script (printf list) — nothing is written on
    the remote side."""
    quoted = ' \\\n'.join("'%s'" % t for t in tokens)
    script = ("printf '%%s\\n' \\\n%s | while read -r TOK; do\n"
              '''
  [ -z "$TOK" ] && continue
  hit=""
  case "$TOK" in
    "~/"*) p="$HOME/${TOK#'~/'}"; [ -e "$p" ] && hit="$p" ;;
    "./"*) p="$HOME/catkin_ws/docs/${TOK#./}"; [ -e "$p" ] && hit="$p" ;;
    "/"*)  [ -e "$TOK" ] && hit="$TOK" ;;
    *)     for b in "$HOME" "$HOME/catkin_ws" "$HOME/sitl_sim" \\
               "$HOME/catkin_ws/sitl_sim" "$HOME/catkin_ws/docs" \\
               "$HOME/catkin_ws/sitl_sim/analysis" \\
               "$HOME/catkin_ws/sitl_sim/t4_evidence"; do
             p="$b/$TOK"; [ -e "$p" ] && { hit="$p"; break; }
           done ;;
  esac
  if [ -n "$hit" ]; then echo "STRICT $TOK FOUND $hit"
  else echo "STRICT $TOK NONE"; fi
done
''' % quoted)
    r = sh('nuc', script, timeout=240)
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split(' ', 2)
        if len(parts) == 3 and parts[0] == 'STRICT':
            out[parts[1]] = None if parts[2] == 'NONE' else \
                parts[2].split(' ', 1)[1]
    return out


def gt_basename_find(tokens):
    """Independent basename find for non-rooted tokens; returns
    dict basename -> set(paths). Chunked like v2 (40/chunk, head -400
    per chunk): the unchunked variant demonstrably crowds hits out of
    the capped output (observed on v1_ground_salvage_211520.bag in the
    first self-check run)."""
    names = sorted({os.path.basename(t) for t in tokens
                    if not t.startswith('/')})
    hits = {}
    for i in range(0, len(names), 40):
        chunk = names[i:i + 40]
        pats = ' -o '.join("-name '%s'" % n for n in chunk)
        script = ('find "$HOME/sitl_sim" "$HOME/catkin_ws" -maxdepth 7 '
                  "\\( -path '*/.git' -o -path '*/build' -o -path '*/devel' "
                  "-o -path '*/logs' \\) -prune -o -type f \\( %s \\) -print "
                  '2>/dev/null | head -400' % pats)
        r = sh('nuc', script, timeout=240)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith('/'):
                hits.setdefault(os.path.basename(line), set()).add(line)
    return hits


def expected_status(tok, strict_path, base_hits):
    if strict_path:
        return 'present'
    if tok.startswith('/'):
        return 'absent'
    b = os.path.basename(tok)
    if b in base_hits:
        if tok.startswith('~/'):
            return 'absent (basename hint)'   # any hit path; set compared
        return 'present (basename hit)'
    return 'absent'


def main():
    items = load_items()
    print('loaded_tokens=%d (from defective v1 report missing-list)' % len(items))
    tok_meta = {t: (a, c) for t, a, c in items}
    run_items = [(t, a) for t, a, _ in items] + [(t, a) for t, a, _ in CONTROLS]

    # A. v2 code path
    v2res = v2.nuc_check_batch(run_items)

    # B. independent ground truth
    all_toks = [t for t, _, _ in items] + [t for t, _, _ in CONTROLS]
    strict = gt_strict(all_toks)
    base_hits = gt_basename_find(all_toks)

    # C. evidence for every path v2 claims present/hint
    claimed = []
    for t in all_toks:
        s = v2res.get(t, '')
        if '(basename ' in s:
            claimed.append(s.rsplit(' ', 1)[1].rstrip(')'))
        elif strict.get(t):
            claimed.append(strict[t])
    ev_lines = []
    if claimed:
        script = 'rm -f /dev/null\n'
        q = '\n'.join('if [ -f "%s" ]; then echo "FILE_OK %s"; '
                      'else echo "NOT_FILE %s"; fi; ls -ld "%s" 2>&1'
                      % (p, p, p, p) for p in sorted(set(claimed)))
        r = sh('nuc', q, timeout=120)
        ev_lines = r.stdout.splitlines()

    # D. compare
    rows, agree, mismatch = [], 0, []
    for t, a, cat in items + [(t, a, tag) for t, a, tag in CONTROLS]:
        v2s = v2res.get(t, 'MISSING-FROM-V2-RESULT')
        exp = expected_status(t, strict.get(t), base_hits)
        ok = False
        if exp == 'present':
            ok = (v2s == 'present')
        elif exp == 'absent':
            ok = (v2s == 'absent')
        elif exp == 'absent (basename hint)':
            ok = v2s.startswith('absent (basename hint: ') and \
                v2s.rsplit(' ', 1)[1].rstrip(')') in base_hits[
                    os.path.basename(t)]
        elif exp == 'present (basename hit)':
            ok = v2s.startswith('present (basename hit: ') and \
                v2s.rsplit(' ', 1)[1].rstrip(')') in base_hits[
                    os.path.basename(t)]
        if ok:
            agree += 1
        else:
            mismatch.append((t, v2s, exp))
        rows.append((t, cat, a, v2s, strict.get(t) or 'NONE',
                     sorted(base_hits.get(os.path.basename(t), []))[:2],
                     'OK' if ok else 'MISMATCH'))

    with io.open(os.path.join(HERE, 'selfcheck_results.tsv'), 'w',
                 encoding='utf-8') as f:
        f.write('token\tv1_category\tanchored\tv2_status\tGT_strict\t'
                'GT_basename_hits\tverdict\n')
        for r in rows:
            f.write('%s\t%s\t%d\t%s\t%s\t%s\t%s\n'
                    % (r[0], r[1], r[2], r[3], r[4],
                       '|'.join(r[5]), r[6]))

    print('agree=%d mismatch=%d total=%d' % (agree, len(mismatch), len(rows)))
    for m in mismatch:
        print('MISMATCH token=%r v2=%r expected=%r' % m)
    print('evidence_lines=%d' % len(ev_lines))
    for ln in ev_lines[:20]:
        print('EV ' + ln)
    return 0 if not mismatch else 1


if __name__ == '__main__':
    sys.exit(main())
