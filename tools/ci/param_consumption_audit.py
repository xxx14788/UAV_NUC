#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""param_consumption_audit.py - 找出"读了但从不使用"的僵尸参数键，以及"yaml 里有、代码从不读"的孤儿键。

用途：本项目出现过"yaml 写着 low_voltage 13.2，但低压保护根本不存在"这类缺陷 ——
      键被读进结构体就再没人消费。工具按 read_essential_param / nh.param 建立
      "键 -> 结构体字段"映射，逐字段统计消费点（排除读取语句自身），零消费判 ZOMBIE；
      反向把 yaml 里有、代码从不读的键判 ORPHAN。
用法：python tools/ci/param_consumption_audit.py [--src DIR] [--yaml F1.yaml F2.yaml ...] [--json] [--selftest]
退出码：0 = ZOMBIE 与 ORPHAN 都为 0；1 = 存在 ZOMBIE 或 ORPHAN；2 = 输入错误（目录/文件/YAML 解析）。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.abspath(os.path.join(_HERE, os.pardir, os.pardir))
DEFAULT_SRC = os.path.join(_WORK, "src", "px4ctrl", "src")

SOURCE_EXTS = (".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh")

# 读取目标的语法形状：a / a.b / a->b / a.b.c（允许中间有空白）
_TARGET = r"([A-Za-z_]\w*(?:\s*(?:\.|->)\s*[A-Za-z_]\w*)*)"
# read_essential_param(nh, "a/b", obj.field)
READ_ESSENTIAL_RE = re.compile(
    r"\bread_essential_param\s*\(\s*[^,()]+,\s*\"([^\"]+)\"\s*,\s*" + _TARGET + r"\s*\)"
)
# nh.param("a/b", obj.field, default) / nh.param<int>(...) / pnh->param<...>(...)
NH_PARAM_RE = re.compile(
    r"\b[A-Za-z_]\w*\s*(?:\.|->)\s*param\s*(?:<[^;()]*>)?\s*\(\s*\"([^\"]+)\"\s*,\s*"
    + _TARGET + r"\s*,"
)
# nh.getParam("a/b", obj.field)（少量代码直接用它）
GET_PARAM_RE = re.compile(
    r"\b[A-Za-z_]\w*\s*(?:\.|->)\s*getParam\w*\s*\(\s*\"([^\"]+)\"\s*,\s*" + _TARGET + r"\s*[,\)]"
)
READ_PATTERNS = (READ_ESSENTIAL_RE, NH_PARAM_RE, GET_PARAM_RE)

# 局部引用别名：const auto &glc = param.ground_lock;  之后 glc.enable 才是真消费
ALIAS_RE = re.compile(r"\bauto\s*(?:&+|\*)?\s*([A-Za-z_]\w*)\s*=\s*([^;]+);")

# 形如 "<类型> name;" / "<类型> a, b;" 的成员声明（不是消费点）
_DECL_RE = re.compile(
    r"^\s*(?:(?:static|mutable|const|constexpr|inline|volatile)\s+)*"
    r"(?:bool|char|short|int|long|unsigned|signed|float|double|size_t|ssize_t|"
    r"u?int(?:8|16|32|64)_t|int(?:8|16|32|64)_t|"
    r"std::[A-Za-z_]\w*(?:\s*<[^;()]*>)?|"
    r"struct\s+[A-Za-z_]\w*|"
    r"[A-Z][A-Za-z_0-9]*)\s+"
    r"[A-Za-z_]\w*(?:\s*=\s*[^;]*)?"
    r"(?:\s*,\s*[A-Za-z_]\w*(?:\s*=\s*[^;]*)?)*\s*;\s*$"
)


class InputError(Exception):
    """输入层面错误：目录/文件缺失、YAML 解析失败、结构不对。"""


# --------------------------------------------------------------------------- #
# 读文件 / 去注释
# --------------------------------------------------------------------------- #
def read_text(path):
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise InputError("%s: 读取失败: %s" % (path, exc))
    return raw.decode("utf-8", "replace")


def strip_comments(text):
    """把 // 与 /* */ 注释替换成等长空格（保留换行与字符串字面量）。

    等长替换让偏移量与原始文件一一对应，行号仍然准确；字符串里的 // 不会被误删。
    """
    out = []
    i = 0
    n = len(text)
    in_block = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_block:
            if ch == "*" and nxt == "/":
                out.append("  ")
                i += 2
                in_block = False
            elif ch == "\n":
                out.append("\n")
                i += 1
            else:
                out.append(" ")
                i += 1
            continue
        if ch == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if ch == "/" and nxt == "*":
            out.append("  ")
            i += 2
            in_block = True
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
            i += 1
            while i < n:
                cur = text[i]
                if cur == "\\" and i + 1 < n:
                    out.append(cur)
                    out.append(text[i + 1])
                    i += 2
                    continue
                out.append(cur)
                i += 1
                if cur == quote:
                    break
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def collect_sources(src_dir):
    if not os.path.isdir(src_dir):
        raise InputError("%s: --src 不是目录" % src_dir)
    found = []
    for root, dirs, files in os.walk(src_dir):
        dirs.sort()
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in SOURCE_EXTS:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, src_dir).replace(os.sep, "/")
                found.append((rel, full))
    if not found:
        raise InputError("%s: 目录下没有 .cpp/.h 源文件" % src_dir)
    return found


# --------------------------------------------------------------------------- #
# 键 / 字段
# --------------------------------------------------------------------------- #
def norm_key(raw):
    key = raw.strip()
    while key[:1] in ("~", "/"):
        key = key[1:]
    return key.replace("/", ".")


def split_target(expr):
    """'param_.ground_lock' -> ('param_.ground_lock', ['param_', 'ground_lock'])。"""
    norm = re.sub(r"\s*(?:\.|->)\s*", ".", expr.strip())
    parts = [p for p in norm.split(".") if p]
    return norm, parts


def find_read_calls(code, relpath):
    """在去注释后的源码里找读取语句，返回记录列表（含行号区间）。"""
    records = []
    for pattern in READ_PATTERNS:
        for match in pattern.finditer(code):
            key = norm_key(match.group(1))
            expr, parts = split_target(match.group(2))
            start = code.count("\n", 0, match.start()) + 1
            end = start + match.group(0).count("\n")
            records.append({
                "key": key,
                "target": expr,
                "obj": parts[0] if len(parts) > 1 else None,
                "field": parts[-1],
                "file": relpath,
                "line": start,
                "end_line": end,
            })
    records.sort(key=lambda r: (r["file"], r["line"], r["key"]))
    return records


def find_aliases(code):
    """收集 'auto &x = <...>.<seg>;' 形式的局部别名：{x: seg}。"""
    aliases = {}
    for match in ALIAS_RE.finditer(code):
        alias = match.group(1)
        tokens = re.findall(r"[A-Za-z_]\w*", match.group(2))
        if len(tokens) >= 2:
            aliases[alias] = tokens[-1]
    return aliases


def _word_re(needle):
    return re.compile(r"(?<!\w)" + re.escape(needle) + r"(?!\w)")


def _is_own_declaration(code_line, field):
    """`bool ghost_flag;` 这类本字段的声明不算消费；但 `= x.field;` 里的成员访问算。"""
    if not _DECL_RE.match(code_line):
        return False
    if re.search(r"(?:\.|->)\s*" + re.escape(field) + r"(?!\w)", code_line):
        return False  # 字段前面有 . / -> ：是成员访问，不是声明
    return re.search(r"(?<!\w)" + re.escape(field) + r"(?!\w)", code_line) is not None


def count_uses(lines, patterns, read_lines, field):
    hits = []
    for relpath, lineno, code_line in lines:
        if (relpath, lineno) in read_lines:
            continue
        if _is_own_declaration(code_line, field):
            continue
        for pattern in patterns:
            if pattern.search(code_line):
                hits.append((relpath, lineno))
                break
    return hits


# --------------------------------------------------------------------------- #
# yaml 叶子键（与 param_face_diff.py 同一套规则：只比叶子，父键是容器）
# --------------------------------------------------------------------------- #
def flatten_leaves(node, prefix="", leaves=None):
    if leaves is None:
        leaves = {}
    if isinstance(node, dict):
        for raw_key, value in node.items():
            path = "%s.%s" % (prefix, raw_key) if prefix else str(raw_key)
            if isinstance(value, dict):
                flatten_leaves(value, path, leaves)
            elif isinstance(value, (list, tuple)):
                leaves[path] = value
            elif value is None:
                continue  # 空值 = 容器占位，不是叶子
            else:
                leaves[path] = value
    return leaves


def load_yaml_leaves(path):
    if not os.path.isfile(path):
        raise InputError("%s: 文件不存在" % path)
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise InputError("%s: 读取失败: %s" % (path, exc))
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = "%s:%d" % (path, mark.line + 1) if mark is not None else "%s:?" % path
        raise InputError("%s: YAML 解析失败: %s" % (where, " ".join(str(exc).split())))
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise InputError("%s:1: 顶层必须是 mapping（实际是 %s）" % (path, type(doc).__name__))
    return flatten_leaves(doc)


def discover_yaml(src_dir):
    """自动发现同包 config/ 下的 ctrl_param*.yaml。"""
    pkg = os.path.dirname(os.path.abspath(src_dir))
    tried = []
    for cfg_dir in (os.path.join(pkg, "config"), os.path.join(src_dir, "config")):
        tried.append(cfg_dir)
        if not os.path.isdir(cfg_dir):
            continue
        found = [os.path.join(cfg_dir, name) for name in sorted(os.listdir(cfg_dir))
                 if name.startswith("ctrl_param")
                 and os.path.splitext(name)[1].lower() in (".yaml", ".yml")]
        if found:
            return found
    raise InputError("自动发现 yaml 失败，试过: %s；请用 --yaml 显式指定"
                     % ", ".join(tried))


# --------------------------------------------------------------------------- #
# 审计
# --------------------------------------------------------------------------- #
def audit(src_dir, yaml_paths, src_files=None):
    files = src_files if src_files is not None else collect_sources(src_dir)
    lines = []
    records = []
    read_lines = set()
    aliases = {}

    for relpath, full in files:
        code = strip_comments(read_text(full))
        for lineno, code_line in enumerate(code.splitlines(), 1):
            lines.append((relpath, lineno, code_line))
        calls = find_read_calls(code, relpath)
        records.extend(calls)
        for call in calls:
            for lineno in range(call["line"], call["end_line"] + 1):
                read_lines.add((relpath, lineno))
        aliases.update(find_aliases(code))

    if not records:
        raise InputError(
            "%s: 没找到任何 read_essential_param / nh.param / getParam 读取语句" % src_dir)

    # 按 (对象, 字段) 归并：同一个字段可能被多个键写（罕见），一并报告
    groups = {}
    for rec in records:
        groups.setdefault((rec["obj"], rec["field"]), []).append(rec)
    aliases_by_obj = {}
    for alias, seg in aliases.items():
        aliases_by_obj.setdefault(seg, []).append(alias)

    zombies = []
    used = 0
    for (obj, field), recs in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0] or "")):
        patterns = []
        if obj:
            patterns.append(_word_re("%s.%s" % (obj, field)))
            for alias in aliases_by_obj.get(obj, []):
                patterns.append(_word_re("%s.%s" % (alias, field)))
        qualified = count_uses(lines, patterns, read_lines, field) if patterns else []
        if qualified:
            used += 1
            continue
        # 二级判定：字段名本身出现在别处（间接消费 / 别名未识别）就不判僵尸，
        # 宁可漏报也不误杀 —— 详见文件头与 README 的误判说明。
        bare = count_uses(lines, [_word_re(field)], read_lines, field)
        if bare:
            used += 1
            continue
        first = recs[0]
        zombies.append({
            "key": first["key"],
            "keys": sorted({r["key"] for r in recs}),
            "field": field,
            "obj": obj,
            "read_at": "%s:%d" % (first["file"], first["line"]),
        })

    read_keys = {rec["key"] for rec in records}
    orphans = []
    yaml_info = []
    for path in yaml_paths:
        leaves = load_yaml_leaves(path)
        base = os.path.basename(path)
        yaml_info.append((base, len(leaves)))
        for key in leaves:
            if key in read_keys:
                continue
            for entry in orphans:
                if entry["key"] == key:
                    entry["in"].append(base)
                    break
            else:
                orphans.append({"key": key, "in": [base]})
    orphans.sort(key=lambda e: e["key"])

    return {
        "zombies": zombies,
        "orphans": orphans,
        "zombie_count": len(zombies),
        "orphan_count": len(orphans),
        "ok": not zombies and not orphans,
        "_src": os.path.abspath(src_dir),
        "_files": len(files),
        "_records": len(records),
        "_read_keys": len(read_keys),
        "_yaml_info": yaml_info,
        "_used": used,
        "_aliases": aliases,
    }


def print_human(res):
    print("src = %s  (files=%d)" % (res["_src"], res["_files"]))
    print("yaml = %s" % ", ".join("%s(leaves=%d)" % (b, n) for b, n in res["_yaml_info"]))
    print("read call sites = %d, distinct keys = %d, field groups = %d (used=%d)"
          % (res["_records"], res["_read_keys"], res["_used"] + res["zombie_count"], res["_used"]))
    if res["_aliases"]:
        print("alias = %s" % ", ".join("%s->%s" % (a, s) for a, s in sorted(res["_aliases"].items())))
    width = max([len(z["key"]) for z in res["zombies"]] + [24])
    for zombie in res["zombies"]:
        extra = ""
        if len(zombie["keys"]) > 1:
            extra = "  [keys: %s]" % ", ".join(zombie["keys"])
        print("ZOMBIE  %-*s (read at %s)%s"
              % (width, zombie["key"], zombie["read_at"], extra))
    for orphan in res["orphans"]:
        print("ORPHAN  %s (in %s, never read)"
              % (orphan["key"], ", ".join(orphan["in"])))
    print("ZOMBIE=%d ORPHAN=%d" % (res["zombie_count"], res["orphan_count"]))


def json_line(res):
    payload = {k: v for k, v in res.items() if not k.startswith("_")}
    return json.dumps(payload, ensure_ascii=False, sort_keys=False)


# --------------------------------------------------------------------------- #
# selftest
# --------------------------------------------------------------------------- #
def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _run_cli(args):
    cmd = [sys.executable, os.path.abspath(__file__)] + args
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


MINI_H = """#ifndef MINI_PARAM_H
#define MINI_PARAM_H

class Parameter_t
{
public:
	struct Gain
	{
		double Kp0;
	};
	Gain gain;          // 正常字段的容器
	bool ghost_flag;    // selftest: 只有声明，没人消费
};

#endif
"""

MINI_CPP = """#include "MINI_PARAM.h"

void Parameter_t::config(const ros::NodeHandle &nh)
{
	read_essential_param(nh, "gain/Kp0", gain.Kp0);
	nh.param("ghost/flag", ghost_flag, false);
}
"""

MINI_CONSUMER = """double use_it(const Parameter_t &param)
{
	return param.gain.Kp0 * 2.0;   // 正常字段有消费点；注释里的 ghost_flag 不算
}
"""

MINI_YAML = """# selftest fixture
gain:
  Kp0: 1.5
ghost:
  flag: true          # 被读取 -> 不是 ORPHAN，但字段是 ZOMBIE
orphan:
  key: 3              # 代码从不读 -> ORPHAN
"""

MINI_YAML_CLEAN = """gain:
  Kp0: 1.5
"""

MINI_CPP_CLEAN = """#include "MINI_PARAM.h"

void Parameter_t::config(const ros::NodeHandle &nh)
{
	read_essential_param(nh, "gain/Kp0", gain.Kp0);
}
"""


def selftest():
    tmp = tempfile.mkdtemp(prefix="param_consumption_audit_selftest_")
    dirty = os.path.join(tmp, "dirty")
    clean = os.path.join(tmp, "clean")
    _write(os.path.join(dirty, "src", "MINI_PARAM.h"), MINI_H)
    _write(os.path.join(dirty, "src", "MINI_PARAM.cpp"), MINI_CPP)
    _write(os.path.join(dirty, "src", "consumer.cpp"), MINI_CONSUMER)
    _write(os.path.join(dirty, "config", "ctrl_param_mini.yaml"), MINI_YAML)
    _write(os.path.join(clean, "src", "MINI_PARAM.h"), MINI_H)
    _write(os.path.join(clean, "src", "MINI_PARAM.cpp"), MINI_CPP_CLEAN)
    _write(os.path.join(clean, "src", "consumer.cpp"), MINI_CONSUMER)
    _write(os.path.join(clean, "config", "ctrl_param_mini.yaml"), MINI_YAML_CLEAN)

    passed = 0
    total = 0
    failures = []

    def check(name, cond, detail):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
        else:
            failures.append("%s: %s" % (name, detail))

    proc = _run_cli(["--src", os.path.join(dirty, "src"),
                     "--yaml", os.path.join(dirty, "config", "ctrl_param_mini.yaml"),
                     "--json"])
    check("dirty/rc", proc.returncode == 1,
          "期望 1，实际 %d；stdout=%s stderr=%s"
          % (proc.returncode, proc.stdout.strip(), proc.stderr.strip()))
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        payload = {}
        check("dirty/json", False, "JSON 解析失败: %s" % exc)
    else:
        zombie_keys = [z["key"] for z in payload.get("zombies", [])]
        orphan_keys = [o["key"] for o in payload.get("orphans", [])]
        check("dirty/zombie", zombie_keys == ["ghost.flag"],
              "ZOMBIE 应为 ['ghost.flag']，实际 %r" % (zombie_keys,))
        check("dirty/orphan", orphan_keys == ["orphan.key"],
              "ORPHAN 应为 ['orphan.key']，实际 %r" % (orphan_keys,))
        check("dirty/normal-not-flagged", "gain.Kp0" not in zombie_keys,
              "正常字段 gain.Kp0 被误判: %r" % (zombie_keys,))

    proc = _run_cli(["--src", os.path.join(clean, "src"),
                     "--yaml", os.path.join(clean, "config", "ctrl_param_mini.yaml"),
                     "--json"])
    check("clean/rc", proc.returncode == 0,
          "期望 0，实际 %d；stdout=%s stderr=%s"
          % (proc.returncode, proc.stdout.strip(), proc.stderr.strip()))

    if failures:
        print("SELFTEST FAIL %d/%d" % (total - passed, total))
        for item in failures:
            print("  - " + item)
        print("fixtures 保留在: %s" % tmp)
        return 1
    print("SELFTEST PASS %d/%d" % (passed, total))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="参数消费审计：ZOMBIE（读了不用）/ ORPHAN（yaml 有但代码不读）。")
    parser.add_argument("--src", default=DEFAULT_SRC,
                        help="px4ctrl/src 目录（默认 %s）" % DEFAULT_SRC)
    parser.add_argument("--yaml", nargs="+", default=None,
                        help="一份或多份参数 yaml；缺省自动发现同包 config/ctrl_param*.yaml")
    parser.add_argument("--json", action="store_true", help="只输出一行 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑内置自检")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        # 先校验 --src，错误信息才会指向用户真正写错的那个参数（而不是 yaml 自动发现）
        src_files = collect_sources(args.src)
        yaml_paths = args.yaml if args.yaml else discover_yaml(args.src)
        res = audit(args.src, yaml_paths, src_files)
    except InputError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    if args.json:
        print(json_line(res))
    else:
        print_human(res)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
