#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P-N2 verdicts 引用闭环自动核对（幂等、只报告、不改任何被扫文件）。

扫描 ~/catkin_ws/docs/t4_verdicts_v2.md 全文，抽取三类引用锚并核对在位性：
  a) commit 短哈希引用：7-8 位十六进制（带边界约束，避免长十六进制串内截取）。
     入锚集条件=上下文含 commit/哈希/链 任一关键词，或 git cat-file -t 可解析；
     逐一 git -C ~/catkin_ws cat-file -t <hash> 验证存在性：
       可解析=在位；不可解析且有关键词=失配；
       纯数字不可解析=不可判(疑似时间戳/尺寸等纯数字误报)；其余不可解析=不可判(未采信)。
  b) 自引用行号："verdicts v2:NNN"/"verdicts:NNN"/"t4_verdicts_v2.md:NNN" 冒号形态、
     区间形态 "v2:NNN-NNN"（与冒号形态重叠去重），及上下文指向本文件的 "LNNN" 形态；
     核对目标行（区间则逐行）存在，且目标内容与引用锚前后 40 字符窗口首 4 个汉字词粗匹配
     （分级：全文串=匹配 → 4 字头 → 2 字头宽松，档位如实标注）。
  c) 文件引用：docs/ derived/ sitl_sim/ t4_evidence/ 前缀路径形态；多基目录解析；
     {a,b} 花括号展开逐体核对；* 通配形态=不可判。

输出：~/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived/pn2_verdicts_refs_report.md
（逐类 总数/在位/失配/不可判 计数 + 失配行原文 + 正本漂移面结论行 + 单元 6 锚注册表清查尾注）。
失配≠改文件，只报告；重跑覆盖本报告（幂等）。
"""
import hashlib
import io
import os
import re
import subprocess
from datetime import datetime

HOME = os.path.expanduser("~")
CATKIN = os.path.join(HOME, "catkin_ws")
VERDICTS = os.path.join(CATKIN, "docs", "t4_verdicts_v2.md")
OUT_DIR = os.path.join(CATKIN, "sitl_sim", "t4_evidence", "v55_20261003", "derived")
OUT = os.path.join(OUT_DIR, "pn2_verdicts_refs_report.md")

COMMIT_KW = ("commit", "哈希", "链")
CHAIN_PREV = "2f4323f1"
CHAIN_CUR_EXPECT = "b2412d08"  # 池件给定：2026-10-04 夜 H 章定稿后现值

HEX_RE = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{7,8}(?![0-9A-Fa-f])")
SELF_RE = re.compile(r"verdicts(?:\s*v2)?\s*[:：]\s*(\d{1,4})", re.I)
SELF_FILE_RE = re.compile(r"t4_verdicts_v2\.md\s*[:：]\s*(\d{1,4})", re.I)
V2_RE = re.compile(r"(?<![A-Za-z0-9_])v2\s*[:：]\s*(\d{1,4})(?:\s*[-–—]\s*(\d{1,4}))?(?!\d)")
LREF_RE = re.compile(r"(?<![A-Za-z0-9_])L(\d{1,4})(?![0-9A-Za-z_])")
CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
FREF_RE = re.compile(
    r"(?<![\w./\-])((?:docs|derived|sitl_sim|t4_evidence)/[A-Za-z0-9_\-.,/*{}]+)")
OTHER_ATTACH_RE = re.compile(
    r"[A-Za-z0-9_\-.]+\.(?:md|csv|json|py|txt|log|bag)\s*[:：]?\s*$")

BASES = [
    ("catkin_ws", CATKIN),
    ("v55_20261003", os.path.join(CATKIN, "sitl_sim", "t4_evidence", "v55_20261003")),
    ("v54_20261002", os.path.join(CATKIN, "sitl_sim", "t4_evidence", "v54_20261002")),
    ("catkin_ws_sitl_sim", os.path.join(CATKIN, "sitl_sim")),
    ("home_sitl_sim", os.path.join(HOME, "sitl_sim")),
]

UNIT6_NOTE = (
    "全 docs 面（~/catkin_ws/docs/*.md + sitl_sim/docs/*.md）仅 t3_xline_runbook.md §9.2 "
    "一张结构化“删袋前必查”注册表；T2/T1 无同类机制（t2_experiments/t3_experiments 为逐行裁定台账"
    "非注册表；vision_materials.md 为截图材料规范）。")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_cat_cache = {}


def cat_file_type(ref):
    if ref not in _cat_cache:
        t = None
        try:
            p = subprocess.run(
                ["git", "-C", CATKIN, "cat-file", "-t", ref],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20)
            if p.returncode == 0:
                t = p.stdout.decode("utf-8", "replace").strip()
        except Exception:
            t = None
        _cat_cache[ref] = t
    return _cat_cache[ref]


def kw_in_window(line, s, e):
    """关键词窗口：锚点前 24 / 后 12 字符（'上下文'取紧邻语段，防全行远距巧合命中）。"""
    seg = line[max(0, s - 24):e + 12].lower()
    return any(k in seg for k in COMMIT_KW)


# ---------------- a) commit short hashes ----------------

def scan_hex(lines):
    anchors = []    # status: 在位 / 失配
    excluded = []   # status: 不可判(...)
    for i, ln in enumerate(lines, 1):
        md58_line = bool(re.search(r"md5\s*前\s*8", ln, re.I)) and ("commit" not in ln.lower())
        for m in HEX_RE.finditer(ln):
            tok = m.group(0)
            kw = kw_in_window(ln, m.start(), m.end())
            t = cat_file_type(tok)
            if t:
                anchors.append((i, tok, kw, t, "在位", ln))
            elif tok.isdigit():
                excluded.append((i, tok, kw, None,
                                 "不可判(纯数字，疑似时间戳/尺寸误报，未采信)", ln))
            elif md58_line and not kw:
                excluded.append((i, tok, kw, None,
                                 "不可判(md5 前8 形态锚，非 commit 语境，未采信)", ln))
            elif kw:
                anchors.append((i, tok, kw, None, "失配", ln))
            else:
                excluded.append((i, tok, kw, None,
                                 "不可判(窗口内无关键词且 cat-file 不可解析，未采信)", ln))
    return anchors, excluded


# ---------------- b) self references ----------------

def anchor_kws(ln, span, maxn=4):
    """引用锚前后文（前 40 / 后 40 字符）首 maxn 个汉字词（CJK 连续串，去重保序）。"""
    s, e = span
    runs = CJK_RE.findall(ln[max(0, s - 40):s]) + CJK_RE.findall(ln[e:e + 40])
    seen = set()
    out = []
    for r in runs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out[:maxn]


def _match_tier(kws, tgt_all):
    """粗匹配分级：全文串 → 4 字头 → 2 字头；返回 tier 名或 None。"""
    keys = []
    for k in kws:
        keys.append((k, "全文"))
        if len(k) >= 4:
            keys.append((k[:4], "4字头"))
            keys.append((k[:2], "2字头"))
        elif len(k) == 3:
            keys.append((k[:2], "2字头"))
    for tier in ("全文", "4字头", "2字头"):
        for k, t in keys:
            if t == tier and k in tgt_all:
                return tier
    return None


def selfref_item(i, anchor, lo, hi, lines, span):
    ln = lines[i - 1]
    kws = anchor_kws(ln, span)
    item = {"line": i, "anchor": anchor, "lo": lo, "hi": hi, "kws": kws,
            "text": ln.strip(), "tgt": ""}
    if lo < 1 or hi > len(lines) or lo > hi:
        item["status"] = "失配(目标行不存在)"
        return item
    tgts = lines[lo - 1:hi]
    head = " ⏐ ".join(t.strip()[:72] for t in tgts[:2])
    item["tgt"] = head + ("…(共 %d 行)" % len(tgts) if len(tgts) > 2 else "")
    if not kws:
        item["status"] = "不可判(引用处窗口无语义关键词)"
        return item
    tier = _match_tier(kws, "".join(tgts))
    if tier == "全文":
        item["status"] = "匹配"
    elif tier == "4字头":
        item["status"] = "匹配(4字头)"
    elif tier == "2字头":
        item["status"] = "匹配(2字头宽松)"
    else:
        item["status"] = "失配(目标行与关键词无粗匹配)"
    return item


def scan_self(lines):
    self_items = []
    other = []   # LNNN 紧邻他文件名 → 非自引用
    undec = []   # LNNN 指向不明 → 不可判
    for i, ln in enumerate(lines, 1):
        spans = []
        for m in SELF_RE.finditer(ln):
            self_items.append(selfref_item(i, m.group(0), int(m.group(1)),
                                           int(m.group(1)), lines,
                                           (m.start(), m.end())))
            spans.append((m.start(), m.end()))
        for m in SELF_FILE_RE.finditer(ln):
            self_items.append(selfref_item(i, m.group(0), int(m.group(1)),
                                           int(m.group(1)), lines,
                                           (m.start(), m.end())))
            spans.append((m.start(), m.end()))
        for m in V2_RE.finditer(ln):
            if any(not (m.end() <= s or m.start() >= e) for s, e in spans):
                continue  # 与 verdicts v2:NNN 冒号形态重叠，已计
            lo = int(m.group(1))
            hi = int(m.group(2)) if m.group(2) else lo
            self_items.append(selfref_item(i, m.group(0).strip(), lo, hi, lines,
                                           (m.start(), m.end())))
        for m in LREF_RE.finditer(ln):
            start = m.start()
            prefix = ln[max(0, start - 60):start]
            if OTHER_ATTACH_RE.search(prefix):
                other.append((i, m.group(0), ln.strip()))
                continue
            ctx = ln + "\n" + (lines[i - 2] if i >= 2 else "")
            if re.search(r"verdicts", ctx, re.I):
                self_items.append(selfref_item(i, m.group(0), int(m.group(1)),
                                               int(m.group(1)), lines,
                                               (m.start(), m.end())))
            else:
                undec.append((i, m.group(0), ln.strip()))
    return self_items, other, undec


# ---------------- c) file references ----------------

def expand_braces(ref):
    m = re.search(r"\{([^{}]+)\}", ref)
    if not m:
        return [ref]
    out = []
    for a in m.group(1).split(","):
        out.extend(expand_braces(ref[:m.start()] + a + ref[m.end():]))
    return out


def resolve_ref(ref):
    if "*" in ref:
        return "不可判(通配形态)", None, ref
    variants = expand_braces(ref)
    partial = None
    for bname, base in BASES:
        hits = [os.path.join(base, v) for v in variants]
        if all(os.path.isfile(p) for p in hits):
            return "在位", bname, " ".join(variants)
        if len(variants) == 1 and os.path.isdir(hits[0]):
            return "在位(目录)", bname, variants[0]
        if any(os.path.isfile(p) for p in hits):
            missing = [v for v, p in zip(variants, hits) if not os.path.isfile(p)]
            partial = (bname, missing)
    if partial:
        return "失配", partial[0], "基=%s 缺=%s" % (partial[0], ",".join(partial[1]))
    return "失配", None, "所有基目录均不存在"


def scan_files(lines):
    items = []
    for i, ln in enumerate(lines, 1):
        for m in FREF_RE.finditer(ln):
            # 全角标点不在字符类内、本就捕不进来；尾剥只限 . , / ，保住 {a,b} 的 '}' 与 '*'
            ref = m.group(1).rstrip(".,/")
            if not ref:
                continue
            st, base, detail = resolve_ref(ref)
            items.append((i, ref, st, base, detail, ln.strip()))
    return items


# ---------------- report ----------------

def main():
    with io.open(VERDICTS, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    n_lines = len(lines)
    vbytes = os.path.getsize(VERDICTS)
    vmd5 = md5_of(VERDICTS)
    vmd5_8 = vmd5[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    a_anchors, a_excl = scan_hex(lines)
    b_self, b_other, b_undec = scan_self(lines)
    c_items = scan_files(lines)

    a_ok = [x for x in a_anchors if x[4] == "在位"]
    a_bad = [x for x in a_anchors if x[4] != "在位"]
    a_pd = [x for x in a_excl if x[4].startswith("不可判(纯数字")]
    a_nk = [x for x in a_excl if x not in a_pd]

    b_ok = [x for x in b_self if x["status"].startswith("匹配")]
    b_ok_strict = [x for x in b_self if x["status"] == "匹配"]
    b_bad = [x for x in b_self if x["status"].startswith("失配")]
    b_und = [x for x in b_self if x["status"].startswith("不可判")]

    c_ok = [x for x in c_items if x[2].startswith("在位")]
    c_bad = [x for x in c_items if x[2] == "失配"]
    c_und = [x for x in c_items if x[2].startswith("不可判")]

    drift = (vmd5_8 == CHAIN_CUR_EXPECT)
    if drift:
        drift_line = ("实测 verdicts md5 前 8 位 = %s == 演进链现值 b2412d08 → "
                      "与 2f4323f1→b2412d08 演进链一致，未发现漂移（如实登记，未对 verdicts 做任何修改）。"
                      % vmd5_8)
    else:
        drift_line = ("实测 verdicts md5 前 8 位 = %s ≠ 演进链现值 b2412d08（链 %s→%s）→ "
                      "漂移发现，如实报告，未修改。" % (vmd5_8, CHAIN_PREV, CHAIN_CUR_EXPECT))

    L = []
    L.append("# P-N2 verdicts 引用闭环自动核对报告")
    L.append("")
    L.append("- 生成时刻：%s（NUC uav4 本地时钟）" % now)
    L.append("- 脚本：sitl_sim/t4_evidence/v55_20261003/tools/verify_verdicts_refs.py（幂等，重跑覆盖本报告）")
    L.append("- 对象：~/catkin_ws/docs/t4_verdicts_v2.md（%d 行；%d B；md5 前 8 位=%s；全值=%s）"
             % (n_lines, vbytes, vmd5_8, vmd5))
    L.append("- 性质：在位性自动核对，只报告；失配≠改文件，本核对未对 verdicts 与任何被引文件做修改。")
    L.append("")
    L.append("## 正本漂移面结论行")
    L.append("- verdicts 现文件 md5 前 8 位 = %s；演进链注记：%s → %s（%s 为 2026-10-04 夜 H 章定稿后现值）。"
             % (vmd5_8, CHAIN_PREV, CHAIN_CUR_EXPECT, CHAIN_CUR_EXPECT))
    L.append("- %s" % drift_line)
    L.append("")
    L.append("## a) commit 短哈希引用（7-8 位十六进制）")
    L.append("- 口径：边界约束的 7-8 位十六进制；关键词=commit/哈希/链，取锚点前 24/后 12 字符窗口"
             "（防全行远距巧合命中）；入锚集=窗口含关键词或 git cat-file -t 可解析；纯数字与"
             "『md5 前 8』形态（行含 md5前8 标注且窗口无关键词）不可解析者不入锚集（疑误报）。"
             "40 位全哈希与 30-32 位 md5 全串形态按池件规格（7-8 位）不在扫描面（边界约束排除，内截不取）。")
    L.append("- 计数：候选命中共 %d 处；入锚集 %d（在位 %d / 失配 %d）；不可判排除 %d"
             "（纯数字 %d + 无关键词不可解析 %d）。计数口径=出现次数（同一哈希多处引用逐处计）。"
             % (len(a_anchors) + len(a_excl), len(a_anchors), len(a_ok), len(a_bad),
                len(a_excl), len(a_pd), len(a_nk)))
    L.append("- 明细（在位/失配）：")
    for (i, tok, kw, t, st, ln) in a_anchors:
        L.append("  - L%d 锚=`%s` 关键词=%s cat-file=%s 判定=%s"
                 % (i, tok, ("有" if kw else "无"), (t if t else "不可解析"), st))
    if a_bad:
        L.append("- 失配行原文：")
        for (i, tok, kw, t, st, ln) in a_bad:
            L.append("  - L%d 锚=`%s`：%s" % (i, tok, ln.strip()))
    if a_excl:
        L.append("- 不可判排除面明细（未采信，仅留痕）：")
        for (i, tok, kw, t, st, ln) in a_excl:
            L.append("  - L%d `%s` %s" % (i, tok, st))
    L.append("")
    L.append("## b) 自引用行号（verdicts v2:NNN / LNNN→本文件）")
    L.append("- 口径：冒号形态（verdicts v2:NNN / verdicts:NNN / t4_verdicts_v2.md:NNN）、"
             "区间形态（v2:NNN-NNN，与冒号形态重叠去重）与上下文含 verdicts 指向本文件的 LNNN；"
             "核对目标行（区间则逐行）存在性 + 目标内容与引用锚前后 40 字符窗口首 4 个汉字词粗匹配，"
             "分级=全文串→4 字头→2 字头（宽松档如实标注）。LNNN 紧邻他文件名者=非自引用排除；"
             "指向不明者=不可判。")
    L.append("- 计数：自引用锚 %d（匹配 %d〔其中严格 %d〕/ 失配 %d / 不可判 %d）；"
             "LNNN 非自引用排除 %d；LNNN 指向不明不可判 %d。"
             % (len(b_self), len(b_ok), len(b_ok_strict), len(b_bad), len(b_und),
                len(b_other), len(b_undec)))
    if b_self:
        L.append("- 自引用明细：")
        for it in b_self:
            rng = ("L%d" % it["lo"]) if it["lo"] == it["hi"] else ("L%d-L%d" % (it["lo"], it["hi"]))
            L.append("  - L%d 锚=`%s` → 目标 %s 判定=%s 关键词=%s"
                     % (it["line"], it["anchor"], rng, it["status"],
                        ("/".join(it["kws"]) if it["kws"] else "无")))
        L.append("- 目标内容：")
        for it in b_self:
            rng = ("L%d" % it["lo"]) if it["lo"] == it["hi"] else ("L%d-L%d" % (it["lo"], it["hi"]))
            L.append("  - %s ← `%s`" % (rng, (it["tgt"] or "<不存在>")))
    if b_bad:
        L.append("- 失配行原文：")
        for it in b_bad:
            L.append("  - L%d 锚=`%s`：%s" % (it["line"], it["anchor"], it["text"]))
    if b_other:
        L.append("- LNNN 非自引用排除面（紧邻他文件名）：")
        for (i, tok, ln) in b_other:
            L.append("  - L%d `%s`：%s" % (i, tok, ln[:160]))
    if b_undec:
        L.append("- LNNN 指向不明不可判面（本行及前一行未见 verdicts 指向）：")
        for (i, tok, ln) in b_undec:
            L.append("  - L%d `%s`：%s" % (i, tok, ln[:160]))
    L.append("")
    L.append("## c) 文件引用（docs/ 与 derived/ 路径形态，扩 sitl_sim/ t4_evidence/ 前缀）")
    L.append("- 口径：前缀 docs/ derived/ sitl_sim/ t4_evidence/ 的路径引用；基目录依序="
             "catkin_ws → v55_20261003 → v54_20261002 → catkin_ws/sitl_sim → ~/sitl_sim，"
             "首个全命中基记为在位；{a,b} 花括号展开逐体核对（部分缺=失配并注缺失体）；"
             "* 通配形态=不可判；目录形态命中注(目录)。")
    L.append("- 计数：总数 %d（在位 %d / 失配 %d / 不可判 %d）。"
             % (len(c_items), len(c_ok), len(c_bad), len(c_und)))
    L.append("- 明细：")
    for (i, ref, st, base, detail, ln) in c_items:
        L.append("  - L%d `%s` 判定=%s 基=%s 注=%s"
                 % (i, ref, st, (base or "-"), (detail if detail else "-")))
    if c_bad:
        L.append("- 失配行原文：")
        for (i, ref, st, base, detail, ln) in c_bad:
            L.append("  - L%d `%s` %s：%s" % (i, ref, detail, ln.strip()))
    L.append("")
    L.append("## 尾注（单元 6 登记随带·他线锚注册表清查结论，主会话已核）")
    L.append("- " + UNIT6_NOTE)
    L.append("")

    os.makedirs(OUT_DIR, exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))

    print("=== P-N2 SUMMARY ===")
    print("VERDICTS lines=%d bytes=%d md5_8=%s" % (n_lines, vbytes, vmd5_8))
    print("DRIFT %s" % ("none (== b2412d08)" if drift else
                         "FOUND (%s != b2412d08)" % vmd5_8))
    print("A candidates=%d anchors=%d ok=%d bad=%d excl_pd=%d excl_nk=%d"
          % (len(a_anchors) + len(a_excl), len(a_anchors), len(a_ok), len(a_bad),
             len(a_pd), len(a_nk)))
    print("B self=%d ok=%d(strict %d) bad=%d und=%d other_file=%d undec_lref=%d"
          % (len(b_self), len(b_ok), len(b_ok_strict), len(b_bad), len(b_und),
             len(b_other), len(b_undec)))
    print("C total=%d ok=%d bad=%d und=%d"
          % (len(c_items), len(c_ok), len(c_bad), len(c_und)))
    for (i, tok, kw, t, st, ln) in a_bad:
        print("A_BAD L%d %s" % (i, tok))
    for it in b_bad:
        print("B_BAD L%d %s -> target L%d-L%d" % (it["line"], it["anchor"], it["lo"], it["hi"]))
    for (i, ref, st, base, detail, ln) in c_bad:
        print("C_BAD L%d %s (%s)" % (i, ref, detail))
    print("REPORT %s" % OUT)
    print("REPORT_MD5 %s" % md5_of(OUT))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
