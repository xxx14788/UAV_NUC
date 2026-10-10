#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draft2verdicts.py — T4 judging_draft → verdicts 正本格式 增量节机械转换器 v1
（v5.26 池件5-2；任务书 plans/2026-10-09_T4_vision_acceptance_v5.26.md 单元 5 池）

职责边界（红线对齐）：
  * 只做结构映射，不做事实加工——任何表格单元格、状态词（未达·维持挂账 等）、
    凭据文本、判读语义词逐字搬运，零替换零增删；
  * 生成器合成的文本仅三类（--selftest 证据中逐行列示供审计）：
      (1) 章前分隔线 '---' + 批次章头 1 行（字段全部机械取自草稿 H1：版本号/日期段/章名）；
      (2) 子节粗体引导行（正本样板=verdicts L45 '- **判据链**：'，标题原文回填 '- **X**：'）；
      (3) 章尾出处行 1 条（固定模板+源草稿路径，不生成任何 md5/commit/时间凭据）；
  * 剥离件仅三类且全部在 --selftest 证据中列示：草稿 H1 行（信息已耗尽入章头）、
    独立 '---' 节分隔线（角色由 '### ' 小节标题承担）、末行斜体署名（草稿自署名面）；
  * 无锁交互：纯本地文本转换，不触碰 SITL 主锁/侧锁（SITL_LOCK_FILE 无关），零远端写入；
  * 不出三态、不代定数、不产生新凭据；并入正本由主会话执行，本工具不写 verdicts 正本。

映射依据（2026-10-09 夜实测）：
  草稿=D:/drone_VINS/t4_v526_out/verdicts_draft_v526.md（311 行）；
  正本=nuc2:~/catkin_ws/docs/t4_verdicts_v2.md（564 行/80497B/md5 4f34d500/mtime 10-06 13:10，
  只读勘察窗口 L1-6/L43-60/L87-100/L337-348/L401-408/L436-452/L557-564+grep '^#' 与 '^|' 全清单）。

用法：
  python3 draft2verdicts.py <draft.md>              # 增量节文本 → stdout
  python3 draft2verdicts.py <draft.md> -o out.md    # 增量节文本 → 文件（UTF-8）
  python3 draft2verdicts.py <draft.md> --selftest   # 转换+无损断言，证据 → stdout（可 >file）
  可选 --chapter '## 自定章头'                     # 覆盖机械派生章头（默认不使用）
"""
import argparse
import hashlib
import re
import sys

PROV_TMPL = ("> 本节=draft2verdicts.py 机械转换产物（源草稿={src}；结构映射 v1）；"
             "判读语义/表列/凭据/状态词零改写；并入正本由主会话执行，"
             "本工具零远端写入、无锁交互。")

# 状态词清单（仅计数对账用，零替换）
STATUS_WORDS = ["未达·维持挂账", "到达·已闭合", "挂账（§6）", "【待确认】", "草稿·待主会话定稿"]


def parse_h1(h1_line):
    """从草稿 H1 机械提取章头三字段：版本号/日期段/章名主体。"""
    title = h1_line.lstrip("#").strip()
    m_paren = re.search(r"（([^（）]*)）", title)
    date_phase = ""
    if m_paren:
        date_phase = m_paren.group(1).split("·")[0].strip()
    m_ver = re.search(r"v\d+\.\d+", title)
    version = m_ver.group(0) if m_ver else ""
    body = re.sub(r"（[^（）]*）", "", title).strip()
    if body.startswith("T4 "):
        body = body[len("T4 "):]
    if body.endswith("草稿"):
        body = body[: -len("草稿")] + "批"
    return version, date_phase, body


def carry_rules(lines):
    """对草稿行流施加搬运/降级/剥离规则，返回 (carried, dropped 清单)。"""
    carried, dropped = [], []
    last_nb = max(i for i, ln in enumerate(lines) if ln.strip())
    for idx, ln in enumerate(lines):
        if idx == 0 and ln.startswith("# "):
            dropped.append(("H1(信息入章头)", ln))
            continue
        if ln.startswith("## "):
            carried.append("### " + ln[len("## "):])
        elif ln.startswith("### "):
            carried.append("- **" + ln[len("### "):] + "**：")
        elif ln.strip() == "---":
            dropped.append(("---节分隔线", ln))
        elif (idx == last_nb and ln.startswith("*") and ln.rstrip().endswith("*")
              and not ln.startswith("**")):
            dropped.append(("末行斜体署名", ln))
        else:
            carried.append(ln)
    return carried, dropped


def transform(text, src_path, chapter_override=None):
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise SystemExit("FATAL: 首行不是 H1（'# '），非本工具约定的草稿结构，拒绝处理")
    first_sec = next((i for i, ln in enumerate(lines) if ln.startswith("## ")), None)
    if first_sec is None:
        raise SystemExit("FATAL: 未找到任何 '## ' 节标题，非本工具约定的草稿结构")
    version, date_phase, chap_body = parse_h1(lines[0])
    if chapter_override:
        chapter = chapter_override
    else:
        name = chap_body if chap_body else ((version + " ") if version else "") + "收口补办批"
        chapter = "## {n}（{d}, 源草稿机械转换·待主会话定稿并入）".format(
            n=name, d=date_phase if date_phase else "日期段缺失")
    carried, dropped = carry_rules(lines)
    prov = PROV_TMPL.format(src=src_path)
    out = ["---", "", chapter, ""] + carried + ["", prov]
    synth = {"separator": "---", "chapter": chapter, "provenance": prov,
             "leads": [l for l in carried if l.startswith("- **") and l.endswith("**：")]}
    return "\n".join(out) + "\n", dropped, synth


def selftest(text, out_text, dropped, synth, src_path):
    """无损断言：输出剥除三类合成行后应与草稿搬运规则结果 1:1 逐行相等。"""
    ev = []
    ok = True
    lines = text.splitlines()
    carried_expected, _ = carry_rules(lines)
    out_lines = out_text.splitlines()
    # 严格结构剥除：['---','',章头,''] 前缀 + ['',出处行] 后缀
    struct_ok = (len(out_lines) >= 6 and out_lines[0] == synth["separator"]
                 and out_lines[1] == "" and out_lines[2] == synth["chapter"]
                 and out_lines[3] == "" and out_lines[-1] == synth["provenance"]
                 and out_lines[-2] == "")
    got = out_lines[4:-2] if struct_ok else None
    ev.append("[1] 合成结构行剥除（---/空行/章头/空行 前缀 + 空行/出处行 后缀）: "
              + ("OK" if struct_ok else "FAIL（结构不符）"))
    ok &= struct_ok
    if struct_ok:
        n = max(len(carried_expected), len(got or []))
        diffs = []
        for i in range(n):
            a = carried_expected[i] if i < len(carried_expected) else "<缺失>"
            b = (got or [])[i] if i < len(got or []) else "<缺失>"
            if a != b:
                diffs.append((i + 1, a, b))
        ev.append("[2] 1:1 逐行无损断言: 期望 {} 行 vs 输出 {} 行, 差异 {} 处".format(
            len(carried_expected), len(got or []), len(diffs)))
        for d in diffs[:5]:
            ev.append("    首差异行#{}: 期望={!r} 输出={!r}".format(*d))
        ok &= (len(diffs) == 0 and len(carried_expected) == len(got or []))
    # 表格行对账（独立证据：行数+拼接 md5）
    tbl_d = [l for l in lines if l.startswith("|")]
    tbl_o = [l for l in (out_text.splitlines()) if l.startswith("|")]
    md5_d = hashlib.md5("\n".join(tbl_d).encode("utf-8")).hexdigest()[:8]
    md5_o = hashlib.md5("\n".join(tbl_o).encode("utf-8")).hexdigest()[:8]
    ev.append("[3] 表格行对账: 草稿 {} 行(md5前8={}) vs 输出 {} 行(md5前8={}) -> {}".format(
        len(tbl_d), md5_d, len(tbl_o), md5_o, "一致" if (tbl_d == tbl_o) else "不一致"))
    ok &= (tbl_d == tbl_o)
    # 状态词计数对账（零替换证据）
    for w in STATUS_WORDS:
        cd = sum(1 for l in lines if w in l)
        co = sum(1 for l in out_text.splitlines() if w in l)
        ev.append("[4] 状态词 {!r}: 草稿 {} vs 输出 {} -> {}".format(
            w, cd, co, "一致" if cd == co else "不一致"))
        ok &= (cd == co)
    # 凭据记号计数（零增删证据）
    cd = sum(1 for l in lines if "凭据" in l)
    co = sum(1 for l in out_text.splitlines() if "凭据" in l)
    ev.append("[5] 含'凭据'行数: 草稿 {} vs 输出 {} -> {}".format(
        cd, co, "一致" if cd == co else "不一致"))
    ok &= (cd == co)
    # 逐节行数对照（### 小节为界）
    secs, cur = [], ("(章头前区)", 0)
    for l in out_lines:
        if l.startswith("### "):
            secs.append(cur)
            cur = (l, 0)
        else:
            cur = (cur[0], cur[1] + 1)
    secs.append(cur)
    ev.append("[6] 输出逐节行数(节标题,行数): " + "; ".join(
        "{}={}".format(t[:38], c) for t, c in secs))
    # 剥离件清单（应为且仅为三类）
    ev.append("[7] 剥离件清单（{} 件）:".format(len(dropped)))
    for kind, ln in dropped:
        ev.append("    [{}] {}".format(kind, ln[:60]))
    ev.append("[8] 合成行清单（应仅为: 1×'---' + 1×章头 + {}×粗体引导 + 1×出处行）:".format(
        len(synth["leads"])))
    ev.append("    [章头] " + synth["chapter"])
    for l in synth["leads"]:
        ev.append("    [引导] " + l)
    ev.append("    [出处] " + synth["provenance"])
    ev.append("SELFTEST_RESULT=" + ("PASS" if ok else "FAIL"))
    return "\n".join(ev), ok


def main():
    ap = argparse.ArgumentParser(description="judging_draft → verdicts 正本格式 增量节机械转换器")
    ap.add_argument("draft", help="草稿 md 路径")
    ap.add_argument("-o", "--out", help="输出文件路径（缺省 stdout）")
    ap.add_argument("--selftest", action="store_true", help="转换+无损断言，证据打 stdout")
    ap.add_argument("--chapter", help="覆盖机械派生章头（默认不使用）")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    with open(args.draft, "r", encoding="utf-8") as f:
        text = f.read()
    out_text, dropped, synth = transform(text, args.draft, args.chapter)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(out_text)
    if args.selftest:
        ev, ok = selftest(text, out_text, dropped, synth, args.draft)
        print(ev)
        sys.exit(0 if ok else 2)
    if not args.out:
        sys.stdout.write(out_text)


if __name__ == "__main__":
    main()
