#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
t4_ref_closure_v2.py -- citation-closure checker, NUC-leg v2 (T4 v5.26 pool).

v2 provenance (2026-10-09):
  Defective v1  = md5 f17ebfcd (git 9c5f129; produced report
                  t4_evidence/t4_ref_closure_20261005.md).  Defect: the NUC
                  existence leg tested anchored refs as '[ -e "~/..." ]' --
                  a literal tilde inside double quotes never expands in sh,
                  so EVERY ~/-anchored probe was falsely 'absent' and real
                  files were reported missing-both (report claimed 61;
                  independent recheck found 8 of 29 sampled tokens actually
                  present on NUC; T1 validation found 3 of 61 flipping).
  Base of v2    = 3090 on-disk md5 e850bf42 (T1 代持 in-place fix, commit
                  2f67d89: $HOME expansion + 7 mirrored bases + P2 find).
  v2 fix point  = 修复 NUC 腿 ~/ 锚定引用双引号内不展开致实存判缺
                  （承 e850bf42），再修其残余：P2 find 截断 100→400/块
                  50→40 防命中被挤出；~/ 锚定 token 缺失时 basename 兜底
                  只出 hint 不翻 present（保严格路径语义，与未锚定 token
                  的翻案策略分离）；新增 --probe-tokens 独立批量核验模式；
                  ssh 探针改 bytes 传输（Windows 控制机中继时 text 模式
                  \r\n 污染远端 sh 致 stdout 空、全体静默 skip——自证
                  阶段实证后加固）。

Mission (pool ask 20261005, unchanged):
  Scan (read-only):
    S1 verdicts  : ~/catkin_ws/docs/t4_verdicts_v2.md
    S2 runbook   : ~/catkin_ws/docs/sim2real_runbook.md
    S3 docs/     : ~/catkin_ws/docs/*.md with mtime within last N days (default 7)
  Extract:
    - bag references: tokens ending in .bag, plus registered bag-name
      stems/prefixes (stems learned from ~/sitl_sim bag inventory)
    - file path references (anchored ~/, / , ./, or known file extension)
  Verify each reference against the local (3090) filesystem.
  NUC existence check for missing items via read-only ssh (host alias
  'nuc'); on any failure/timeout -> marked 'skip'.
  Report-only: NEVER modifies any scanned file. Missing refs are listed,
  never fixed/created.

Output: ~/catkin_ws/sitl_sim/t4_evidence/t4_ref_closure_<YYYYMMDD>.md
Usage : python3 t4_ref_closure_v2.py [--out PATH] [--days N] [--no-nuc]
        python3 t4_ref_closure_v2.py --probe-tokens TSV [--out TSV]
            TSV lines: token<TAB>anchored(0/1); prints token<TAB>status
"""

import argparse
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

HOME = os.path.expanduser('~')
REPO = os.path.join(HOME, 'catkin_ws')
DOCS = os.path.join(REPO, 'docs')
SITL = os.path.join(HOME, 'sitl_sim')
EVID = os.path.join(REPO, 'sitl_sim', 't4_evidence')

VERDICTS = os.path.join(DOCS, 't4_verdicts_v2.md')
RUNBOOK = os.path.join(DOCS, 'sim2real_runbook.md')

# known file extensions that make a bare token a file reference
EXTS = {
    'bag', 'md', 'py', 'sh', 'bash', 'yaml', 'yml', 'json', 'csv', 'txt',
    'png', 'jpg', 'jpeg', 'pdf', 'world', 'launch', 'so', 'lock', 'cfg',
    'conf', 'config', 'urdf', 'xacro', 'service', 'svd', 'elf', 'map',
    'log', 'tar', 'gz', 'zip', 'xz',
}
EXT_RE = re.compile(r'\.(' + '|'.join(sorted(EXTS)) + r')\Z')

TOKEN_RE = re.compile(r'[A-Za-z0-9_\-.~/]+')
URL_RE = re.compile(r'(?:https?|ssh|git|ftp)://\S+')
ANGLE_RE = re.compile(r'<[^<>\n]*>')          # usage placeholders like <src.bag>
MIDEXT_RE = re.compile(r'\.(?:' + '|'.join(sorted(EXTS)) + r')/')
NUMSEG_RE = re.compile(r'^[\d.]+$')

PRUNE_DIRS = {'.git', 'build', 'devel', 'logs', '.catkin_tools', '__pycache__'}

# --------------------------------------------------------------- inventory


def add_file(ap, all_files, bags, stems):
    if not os.path.exists(ap):      # skip dangling symlinks from the index
        return
    b = os.path.basename(ap)
    lst = all_files.setdefault(b, [])
    if ap not in lst:
        lst.append(ap)
    if b.endswith('.bag'):
        bl = bags.setdefault(b, [])
        if ap not in bl:
            bl.append(ap)
        stems.add(b[:-4])


def add_tree(ap, depth, all_files, bags, stems):
    if depth < 0:
        return
    try:
        entries = sorted(os.listdir(ap))
    except OSError:
        return
    for e in entries:
        ep = os.path.join(ap, e)
        add_file(ep, all_files, bags, stems)
        if os.path.isdir(ep) or (os.path.islink(ep) and os.path.isdir(ep)):
            add_tree(ep, depth - 1, all_files, bags, stems)


def build_index():
    all_files, bags, stems = {}, {}, set()
    # ~/sitl_sim : full walk (no symlink-dir follow), then staging dirs 2 deep
    for root, dirs, files in os.walk(SITL):
        for f in files:
            add_file(os.path.join(root, f), all_files, bags, stems)
    try:
        for e in sorted(os.listdir(os.path.join(SITL, 'bags'))):
            ep = os.path.join(SITL, 'bags', e)
            if os.path.isdir(ep) or os.path.islink(ep):
                add_tree(ep, 2, all_files, bags, stems)
    except OSError:
        pass
    # ~/catkin_ws : pruned walk
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
        for f in files:
            add_file(os.path.join(root, f), all_files, bags, stems)
    return all_files, bags, stems

# --------------------------------------------------------------- extraction


def clean_token(tok):
    # keep leading anchor chars (~/, /, ./); drop trailing punctuation only
    tok = tok.rstrip('./-')
    if tok.startswith('-/') or tok.startswith('-~'):
        tok = tok.lstrip('-')   # glue from ${VAR:-/path} / bullet lists
    return tok


def looks_like_path(t):
    if t.startswith('~/') or t.startswith('/') or t.startswith('./'):
        return True
    if '/' in t and '.' in t:
        return True
    return False


def extract_refs(text):
    """Return list of (token, kind)."""
    out = []
    text = URL_RE.sub(' ', text)
    text = ANGLE_RE.sub(' ', text)
    for m in TOKEN_RE.finditer(text):
        tok = clean_token(m.group(0))
        if len(tok) < 4 or not re.search(r'[A-Za-z]', tok):
            continue
        if tok.startswith('.'):
            if not tok.startswith('./'):
                continue    # bare '.bag'-style suffix artifacts
        if tok.startswith('/') and tok.count('/') == 1:
            continue        # one-segment rooted token: slash-glue artifact
        if '/' in tok and MIDEXT_RE.search(tok):
            continue        # a/b.md/c.md-style prose enumeration
        segs = tok.split('/')
        if sum(1 for s in segs if NUMSEG_RE.match(s)) >= 2:
            continue        # v5.0/5.1/5.2-style prose enumeration
        if tok.lower().endswith('.bag'):
            out.append((tok, 'bag-file'))
        elif looks_like_path(tok) and EXT_RE.search(tok):
            out.append((tok, 'path'))
        elif tok in _STEMS or (len(tok) >= 8 and '_' in tok
                               and any(c.isdigit() for c in tok)
                               and any(s.startswith(tok) for s in _STEMS)):
            out.append((tok, 'bag-prefix'))
    return out

# --------------------------------------------------------------- resolution


def resolve_path(t, doc_dir, all_files):
    if t.startswith('~/'):
        cands = [os.path.join(HOME, t[2:])]
    elif t.startswith('./'):
        cands = [os.path.join(doc_dir, t[2:])]
    elif t.startswith('/'):
        cands = [t]
    else:
        bases = [REPO, os.path.join(REPO, 'sitl_sim'), SITL, doc_dir,
                 os.path.join(REPO, 'sitl_sim', 'analysis'),
                 os.path.join(REPO, 'sitl_sim', 't4_evidence'), HOME]
        cands = [os.path.join(b, t) for b in bases]
    for c in cands:
        if os.path.islink(c) and not os.path.exists(c):
            return 'dangling-symlink', c
        if os.path.exists(c):
            return 'present', c
    if '/' not in t:
        hits = all_files.get(os.path.basename(t))
        if hits:
            return 'present', hits[0]
    return 'missing', None


def resolve_ref(tok, kind, doc_dir, all_files, bags):
    """-> (status, resolved_path, remark)"""
    if kind == 'bag-file':
        base = os.path.basename(tok)
        if '/' in tok:
            st, rp = resolve_path(tok, doc_dir, all_files)
            if st == 'present':
                return st, rp, ''
        hits = bags.get(base)
        if hits:
            return 'present', hits[0], ''
        return 'missing', None, ''
    if kind == 'path':
        st, rp = resolve_path(tok, doc_dir, all_files)
        remark = ''
        if st == 'missing':
            if os.path.basename(tok) == 'SITL.lock':
                remark = '锁 symlink 为瞬态结构，缺失属预期态'
            hits = all_files.get(os.path.basename(tok))
            if hits:
                remark += ("basename '%s' exists at %s (parent path absent)"
                           % (os.path.basename(tok), hits[0]))
        return st, rp, remark
    if kind == 'bag-prefix':
        stems = sorted(s for s in _STEMS if s == tok or s.startswith(tok))
        return 'present', stems[0], ('%d stem(s) match' % len(stems)
                                     if len(stems) > 1 else '')
    return 'missing', None, 'unknown kind'

# --------------------------------------------------------------- NUC check


def nuc_host_configured():
    cfg = os.path.join(HOME, '.ssh', 'config')
    try:
        with open(cfg, 'r', errors='replace') as f:
            txt = f.read()
    except OSError:
        return False
    return re.search(r'(?im)^\s*Host\s+nuc\s*$', txt) is not None


# Base-dir candidates for UNanchored tokens on the NUC — mirrors the 3090
# local resolve_path() bases 1:1 ([REPO, REPO/sitl_sim, SITL, doc_dir,
# REPO/sitl_sim/analysis, REPO/sitl_sim/t4_evidence, HOME]).
NUC_BASES = (
    '$HOME/catkin_ws',
    '$HOME/catkin_ws/sitl_sim',
    '$HOME/sitl_sim',
    '$HOME/catkin_ws/docs',
    '$HOME/catkin_ws/sitl_sim/analysis',
    '$HOME/catkin_ws/sitl_sim/t4_evidence',
    '$HOME',
)


def build_nuc_probe_script(items):
    """Build the read-only sh probe run on the NUC. Two phases:
    P1 per-token [ -e ] over the mirrored candidate bases (anchored ~/x is
    expanded via $HOME — literal "~" inside double quotes never expands,
    which is exactly the v1 bug that turned existing ~/... refs into false
    'absent'); P2 one batched `find` basename fallback whose bare-path
    output is paired to P1-absent tokens by basename (parse side).
    v2: P2 output cap raised 100->400 and chunk size 50->40 so a basename
    with many hits cannot crowd other basenames out of the capped output."""
    lines = []
    for tok, anchored in items:
        if tok.startswith('~/'):
            cand = '[ -e "$HOME/%s" ]' % tok[2:]
        elif tok.startswith('./'):
            # local semantics: resolve against the docs dir (repo-synced)
            cand = '[ -e "$HOME/catkin_ws/docs/%s" ]' % tok[2:]
        elif tok.startswith('/'):
            cand = '[ -e "%s" ]' % tok
        else:
            cand = ' || '.join('[ -e "%s/%s" ]' % (b, tok) for b in NUC_BASES)
        lines.append('if %s; then echo "OK %s"; else echo "NO %s"; fi'
                     % (cand, tok, tok))
    basenames = sorted({os.path.basename(t) for t, a in items
                        if not t.startswith('/')})
    for i in range(0, len(basenames), 40):
        chunk = basenames[i:i + 40]
        pats = ' -o '.join("-name '%s'" % b for b in chunk)
        lines.append(
            'find "$HOME/sitl_sim" "$HOME/catkin_ws" -maxdepth 7 '
            "\\( -path '*/.git' -o -path '*/build' -o -path '*/devel' "
            "-o -path '*/logs' \\) -prune -o -type f \\( %s \\) -print "
            '2>/dev/null | head -400' % pats)
    return '\n'.join(lines) + '\n'


def parse_nuc_probe_output(stdout, items):
    """Map probe output back to token -> status string. P1 lines are
    'OK/NO <token>'; P2 find output is bare paths, paired to P1-absent
    tokens by basename (evidence path kept in the status string).
    v2 pairing policy split by anchor:
      - unanchored token absent + basename hit -> 'present (basename hit:
        P)' (mirror of the 3090 basename fallback: the referenced artifact
        exists on the NUC, base dir merely differs);
      - ~/-anchored token absent + basename hit -> 'absent (basename hint:
        P)' (STRICT path semantics: the exact HOME-relative path is absent;
        the hint is evidence, not a flip);
      - /-rooted (absolute) token absent -> plain 'absent', NEVER paired
        (an absolute path either exists verbatim or the ref is broken;
        e850bf42 residual bug fixed here: a rooted /tmp/... token could be
        flipped 'present' by an unrelated same-basename file under $HOME)."""
    direct = {}
    paths = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith('OK '):
            direct[line[3:]] = 'present'
        elif line.startswith('NO '):
            direct[line[3:]] = 'absent'
        elif line.startswith('/'):
            paths.append(line)
    by_base = {}
    for p in paths:
        by_base.setdefault(os.path.basename(p), p)
    res = {}
    for tok, anchored in items:
        if direct.get(tok) == 'absent' and not tok.startswith('/'):
            b = os.path.basename(tok)
            if b in by_base:
                if anchored:
                    res[tok] = 'absent (basename hint: %s)' % by_base[b]
                else:
                    res[tok] = 'present (basename hit: %s)' % by_base[b]
                continue
        res[tok] = direct.get(tok, 'skip: no answer from nuc')
    return res


def nuc_check_batch(items):
    """ssh read-only existence check on nuc for missing refs.
    items: list of (token, anchored). Tokens are filesystem-safe charset
    only ([A-Za-z0-9_-.~/], no spaces/quotes), so inline shell quoting is
    safe. Fix history: v1 (f17ebfcd) tested '~/x' inside double quotes ->
    never expands -> false absent; e850bf42 (T1) expanded via $HOME,
    mirrored 7 bases, added P2 find fallback; v2 (this file) keeps those,
    raises P2 cap, and splits the basename pairing policy by anchor
    (unanchored flip / anchored hint-only). Returns dict token ->
    'present[ (basename hit: path)]' | 'absent[ (basename hint: path)]' |
    'skip: reason'."""
    res = {}
    if not items:
        return res
    tokens = [t for t, _ in items]
    if not nuc_host_configured():
        return {t: 'skip: no ssh host alias nuc on 3090' for t in tokens}
    script = build_nuc_probe_script(items)
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
           '-o', 'StrictHostKeyChecking=no', 'nuc', 'sh', '-s']
    try:
        # bytes transport on purpose: text mode translates \n->os.linesep on
        # Windows, the \r poisons the remote sh parser ("expecting fi") and
        # stdout comes back EMPTY -> every token silently 'skip'/'absent'
        # (same silent-failure family as the v1 defect). v2 change #4.
        r = subprocess.run(cmd, input=script.encode('utf-8'),
                           capture_output=True, timeout=180)
        res = parse_nuc_probe_output(r.stdout.decode('utf-8', 'replace'),
                                     items)
    except subprocess.TimeoutExpired:
        return {t: 'skip: ssh timeout' for t in tokens}
    except OSError as e:
        return {t: 'skip: ssh error %s' % e for t in tokens}
    for t in tokens:
        res.setdefault(t, 'skip: no answer from nuc')
    return res

# --------------------------------------------------------------- scanning


def scan_sources(days):
    cutoff = time.time() - days * 86400
    fixed, extra = [], []
    for p in (VERDICTS, RUNBOOK):
        if os.path.isfile(p):
            fixed.append(p)
    for fn in sorted(os.listdir(DOCS)):
        p = os.path.join(DOCS, fn)
        if not fn.endswith('.md') or not os.path.isfile(p) or p in fixed:
            continue
        if os.path.getmtime(p) >= cutoff:
            extra.append(p)
    return fixed, extra


def md5_8(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()[:8]

# --------------------------------------------------------------- main


_STEMS = set()


def main():
    global _STEMS
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None)
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--no-nuc', action='store_true')
    ap.add_argument('--missing-out', default=None,
                    help='write missing refs (token\\tanchored) for an '
                         'external NUC relay check')
    ap.add_argument('--nuc-result-file', default=None,
                    help='precomputed NUC results, lines: token\\tstatus')
    ap.add_argument('--nuc-source', default='',
                    help='free-text annotation of how NUC results were '
                         'obtained (recorded in the report)')
    ap.add_argument('--probe-tokens', default=None,
                    help='v2: standalone NUC-leg batch check; TSV lines: '
                         'token\\tanchored(0/1); prints token\\tstatus')
    args = ap.parse_args()

    if args.probe_tokens:
        items = []
        with open(args.probe_tokens, 'r', encoding='utf-8',
                  errors='replace') as f:
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) >= 2 and parts[0]:
                    items.append((parts[0], parts[1] == '1'))
        res = nuc_check_batch(items)
        out = args.out or '-'
        lines = ['%s\t%s' % (t, res.get(t, 'skip: no answer from nuc'))
                 for t, _ in items]
        if out == '-':
            sys.stdout.write('\n'.join(lines) + '\n')
        else:
            with open(out, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
            print('wrote %s (%d tokens)' % (out, len(items)))
        return 0

    now = datetime.datetime.now()
    all_files, bags, stems = build_index()
    _STEMS = stems

    fixed, extra = scan_sources(args.days)
    refs = {}   # token -> dict(kind, occ=[(file,line)], count)
    for path in fixed + extra:
        doc_dir = os.path.dirname(path)
        with open(path, 'r', errors='replace') as f:
            for ln, line in enumerate(f, 1):
                for tok, kind in extract_refs(line):
                    d = refs.setdefault(tok, {'kind': kind, 'occ': [],
                                              'count': 0})
                    d['count'] += 1
                    if len(d['occ']) < 5:
                        d['occ'].append((path, ln))

    # resolve on 3090
    rows = []
    for tok in sorted(refs):
        d = refs[tok]
        st, rp, remark = resolve_ref(tok, d['kind'], DOCS, all_files, bags)
        rows.append({'token': tok, 'kind': d['kind'], 'count': d['count'],
                     'occ': d['occ'], 'status': st, 'resolved': rp,
                     'remark': remark})

    missing = [r for r in rows if r['status'] == 'missing']
    if args.missing_out and missing:
        with open(args.missing_out, 'w', encoding='utf-8') as f:
            for r in missing:
                f.write('%s\t%d\n' % (r['token'],
                                      1 if r['token'].startswith(
                                          ('~/', '/', './')) else 0))
    nuc_res = {}
    if not args.no_nuc and missing:
        if args.nuc_result_file:
            with open(args.nuc_result_file, 'r', encoding='utf-8',
                      errors='replace') as f:
                for line in f:
                    parts = line.rstrip('\n').split('\t')
                    if len(parts) >= 2 and parts[0]:
                        nuc_res[parts[0]] = parts[1]
            for r in missing:
                nuc_res.setdefault(r['token'], 'skip: not in result file')
        else:
            items = [(r['token'],
                      r['token'].startswith(('~/', '/', './')))
                     for r in missing]
            nuc_res = nuc_check_batch(items)

    # classify missing
    for r in missing:
        n = nuc_res.get(r['token'], 'skip: nuc check disabled')
        r['nuc'] = n
        if str(n).startswith('present'):
            r['category'] = 'nuc-only'
        elif str(n).startswith('skip'):
            r['category'] = 'nuc-check-skip'
        else:
            r['category'] = 'missing-both'

    cnt = {}
    for r in rows:
        cnt[r['status']] = cnt.get(r['status'], 0) + 1
    cat = {}
    for r in missing:
        cat[r['category']] = cat.get(r['category'], 0) + 1

    # machine snapshot
    du = shutil.disk_usage(HOME)
    free_g = du.free / (1 << 30)

    def pgrep_c(name):
        try:
            r = subprocess.run(['pgrep', '-cx', name], capture_output=True,
                               text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return 'err'
    snap = {n: pgrep_c(n) for n in ('rosbag', 'gzserver', 'px4')}

    self_md5 = md5_8(os.path.abspath(__file__))

    # ---------------------------------------------------------- report
    out_path = args.out or os.path.join(
        EVID, 't4_ref_closure_%s.md' % now.strftime('%Y%m%d'))
    L = []
    w = L.append
    w('# T4 池件①-2 引用闭环报告（%s，v2 脚本）' % now.strftime('%Y%m%d'))
    w('')
    w('- 生成时间（3090 本机）：%s' % now.strftime('%F %T %z'))
    w('- 脚本：`sitl_sim/analysis/t4_ref_closure_v2.py`（本报告由该脚本产出；'
      '脚本自报 md5 前 8 位 = `%s`）' % self_md5)
    w('- v2 脚本源流：带病 v1=f17ebfcd（git 9c5f129，NUC 腿 ~/ 引号内不展开'
      '致实存判缺）→ T1 代持原位修复 e850bf42（commit 2f67d89）→ 本 v2'
      '（残余修正+--probe-tokens）。')
    w('- 性质：登记性质清单（只列不修）。缺失引用不代建不代改；'
      '他域缺失项供主会话催办。')
    w('- 机器快照：df 可用 %.0fG；pgrep -cx → rosbag=%s gzserver=%s px4=%s'
      % (free_g, snap['rosbag'], snap['gzserver'], snap['px4']))
    w('')
    w('## 扫描源')
    w('')
    w('| 源 | 说明 | mtime |')
    w('|---|---|---|')
    for p in fixed:
        w('| `%s` | 固定源（verdicts 3090 正源 / runbook） | %s |'
          % (os.path.relpath(p, REPO),
             datetime.datetime.fromtimestamp(
                 os.path.getmtime(p)).strftime('%F %T')))
    for p in extra:
        w('| `%s` | docs/ 近 %d 天判读文 | %s |'
          % (os.path.relpath(p, REPO), args.days,
             datetime.datetime.fromtimestamp(
                 os.path.getmtime(p)).strftime('%F %T')))
    w('')
    w('## 抽取与核对规则')
    w('')
    w('- bag 引用：token 以 `.bag` 结尾（含带路径形态）；'
      '袋名前缀引用 = token 为在册袋 stem 全名或其前缀'
      '（len≥8、含 `_` 与数字；stem 集 = 3090 盘上全部 *.bag 去扩展名）。')
    w('- 路径引用：`~/`、`/`、`./` 锚定 token，或不带斜杠但带已知扩展名 token；'
      '相对路径按 ~/catkin_ws、~/catkin_ws/sitl_sim、~/sitl_sim、docs/、'
      'analysis/、t4_evidence/、~ 依次试探；裸文件名按全盘索引 basename 兜底。')
    w('- URL（含 `://`）剔除；去重后按 token 记账，出处最多记 5 条。')
    w('- 3090 存在性 = 本机实测（os.path.exists，悬空 symlink 单列）；'
      '缺失项再做 NUC 只读 ssh 存在性（超时/失败 → skip，如实注记）。')
    w('- NUC 侧配对策略（v2）：未锚定 token 缺失但 basename 兜底命中 → '
      'present(basename hit)（与 3090 腿同策略）；`~/` 锚定 token 缺失但 '
      'basename 命中 → absent(basename hint)（严格路径语义，只出证据不翻案）。')
    w('- 边界：docs/ 仅顶层 *.md（figs/ 子目录不在判读文面）；'
      '裸目录名引用（无扩展名、非袋前缀）不在抽取面，见注记；'
      '占位符 `<...>`、`${VAR:-/x}` 与 prose 枚举粘连形态已过滤，'
      '不计数不判缺。')
    w('')
    w('## 汇总')
    w('')
    w('| 项 | 数值 |')
    w('|---|---|')
    w('| 引用总数（去重 token） | %d |' % len(rows))
    w('| 引用总出现次数 | %d |' % sum(r['count'] for r in rows))
    w('| bag 引用（bag-file） | %d |'
      % sum(1 for r in rows if r['kind'] == 'bag-file'))
    w('| 袋名前缀引用（bag-prefix） | %d |'
      % sum(1 for r in rows if r['kind'] == 'bag-prefix'))
    w('| 路径引用（path） | %d |'
      % sum(1 for r in rows if r['kind'] == 'path'))
    w('| 在位（3090） | %d |' % cnt.get('present', 0))
    w('| 悬空 symlink | %d |' % cnt.get('dangling-symlink', 0))
    w('| 缺失（3090）合计 | %d |' % len(missing))
    for k in ('missing-both', 'nuc-only', 'nuc-check-skip'):
        w('| — %s | %d |' % (k, cat.get(k, 0)))
    w('')
    w('## 缺失清单（只列不修）')
    w('')
    if missing:
        w('| 引用 | 类别 | kind | 出现次数 | 出处（file:line） | NUC | 备注 |')
        w('|---|---|---|---|---|---|---|')
        for r in missing:
            occ = '；'.join('%s:%d' % (os.path.relpath(p, REPO), ln)
                            for p, ln in r['occ'][:3])
            if r['count'] > 3:
                occ += '；…(%d 处)' % r['count']
            w('| `%s` | %s | %s | %d | %s | %s | %s |'
              % (r['token'], r['category'], r['kind'], r['count'], occ,
                 r['nuc'], r['remark']))
    else:
        w('（无缺失引用）')
    w('')
    w('## 在位引用（%d 条）' % (cnt.get('present', 0)
                                + cnt.get('dangling-symlink', 0)))
    w('')
    w('| 引用 | kind | 次数 | 3090 解析 |')
    w('|---|---|---|---|')
    for r in rows:
        if r['status'] == 'missing':
            continue
        w('| `%s` | %s | %d | %s%s |'
          % (r['token'], r['kind'], r['count'],
             '悬空symlink:' if r['status'] == 'dangling-symlink' else '',
             r['resolved'] or ''))
    w('')
    w('## 注记')
    w('')
    if args.nuc_result_file:
        w('- NUC 查证口径：已执行，结果经结果文件回灌（%s；渠道：%s）。'
          '相对路径在 NUC 侧按 ~/、~/catkin_ws/、~/sitl_sim/、'
          '~/catkin_ws/sitl_sim/ 同款基目录展开 test -e，'
          '任一命中即 present。'
          % (args.nuc_result_file, args.nuc_source or 'unspecified'))
    else:
        w('- NUC 查证口径：%s'
          % ('已执行（对 %d 个 3090 缺失项批量只读 test -e）' % len(missing)
             if not args.no_nuc and missing else
             ('未执行（--no-nuc）' if args.no_nuc else
              '无缺失项，未触发')))
    w('- `/home/uav/...` 形态引用为旧 NUC 时代绝对路径（NUC 用户 uav；'
      '3090 用户 ghj），3090 侧按路径原文判缺，由 NUC 查证给出归宿。')
    w('- `run_*` staging 目录为重放期临时 ln -s 结构，'
      '其引用判缺属预期态（原始袋在位即闭环），已在备注列标注 basename 归宿。')
    w('- 本报告不产 PASS/FAIL 判读，不含任何判据阈值；'
      '缺失清单不触发任何修复动作。')
    w('')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    # ASCII stdout summary
    print('refs_total=%d occurrences=%d present=%d dangling=%d missing=%d'
          % (len(rows), sum(r['count'] for r in rows),
             cnt.get('present', 0), cnt.get('dangling-symlink', 0),
             len(missing)))
    print('missing_both=%d nuc_only=%d nuc_skip=%d'
          % (cat.get('missing-both', 0), cat.get('nuc-only', 0),
             cat.get('nuc-check-skip', 0)))
    print('scanned=%d sources=%d' % (len(fixed) + len(extra), len(extra)))
    print('report=%s' % out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
