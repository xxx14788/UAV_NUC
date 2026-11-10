#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""param_face_diff.py - 比较两份 px4ctrl 参数 yaml 的"参数面"（只比叶子键集，不比取值）。

用途：回答"SITL 与实机跑的是不是同一套参数面"。键只在一边出现时，另一边会静默
      走代码默认值 —— 参数面已经分叉而无人察觉。白名单把"有意的差异"固化成可
      评审的文件；差集必须被白名单覆盖才算通过。
用法：python tools/ci/param_face_diff.py [A.yaml] [B.yaml] [--allowlist L.yaml] [--json] [--selftest]
退出码：0 = 无差异，或差异全部被白名单覆盖；1 = 存在白名单外的差异；2 = 文件读不到/YAML 解析失败。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

from yaml_unique import DuplicateKeyError, safe_load_unique

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 默认路径按脚本位置解析，而不是按 cwd —— 这样从任何目录调用都指向同一份文件。
_HERE = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.abspath(os.path.join(_HERE, os.pardir, os.pardir))
_CFG = os.path.join(_WORK, "src", "px4ctrl", "config")
DEFAULT_A = os.path.join(_CFG, "ctrl_param_fpv.yaml")
DEFAULT_B = os.path.join(_CFG, "ctrl_param_sitl.yaml")
DEFAULT_ALLOWLIST = os.path.join(_CFG, "params_diff_allowlist.yaml")

SIDES = ("only_in_A", "only_in_B")


class InputError(Exception):
    """输入层面的错误：文件缺失、YAML 语法错、顶层结构不对、白名单格式错。"""


# --------------------------------------------------------------------------- #
# YAML -> 叶子键
# --------------------------------------------------------------------------- #
def flatten_leaves(node, prefix="", leaves=None, empty_blocks=None):
    """把 mapping 展开成 {"a.b.c": value}，只收叶子（有值的标量）。

    父键是容器，本身不参与比较；显式空值（`foo:` 后面既无同缩进标量也无子块）
    按容器占位处理 —— 记进 empty_blocks 供人类提示，绝不产出 "foo.None" 这种假键。
    列表值按叶子收（本项目参数面没有列表，这里只是不崩）。
    """
    if leaves is None:
        leaves = {}
    if empty_blocks is None:
        empty_blocks = []
    if isinstance(node, dict):
        for raw_key, value in node.items():
            key = str(raw_key)
            path = "%s.%s" % (prefix, key) if prefix else key
            if isinstance(value, dict):
                flatten_leaves(value, path, leaves, empty_blocks)
            elif isinstance(value, (list, tuple)):
                leaves[path] = value
            elif value is None:
                empty_blocks.append(path)
            else:
                leaves[path] = value
    return leaves


def load_yaml_leaves(path):
    """读一个 yaml，返回 (叶子键 dict, 空值容器列表)。错误一律带文件:行号抛出。"""
    if not os.path.isfile(path):
        raise InputError("%s: 文件不存在" % path)
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise InputError("%s: 读取失败: %s" % (path, exc))
    try:
        doc = safe_load_unique(raw, name=path)
    except DuplicateKeyError as exc:
        # 重复键 = 静默改配置（后者覆盖前者），比语法错更危险，按输入错误处理
        raise InputError("%s" % exc)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = "%s:%d" % (path, mark.line + 1) if mark is not None else "%s:?" % path
        detail = " ".join(str(exc).split())
        raise InputError("%s: YAML 解析失败: %s" % (where, detail))
    if doc is None:
        return {}, []
    if not isinstance(doc, dict):
        raise InputError(
            "%s:1: 顶层必须是 mapping（实际是 %s）" % (path, type(doc).__name__)
        )
    empty_blocks = []
    leaves = flatten_leaves(doc, "", None, empty_blocks)
    return leaves, empty_blocks


def _line_of(text, needle):
    """在原始文本里找 needle 的 1-based 行号（用于把白名单错误落到行）。"""
    for idx, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return idx
    return None


def _load_allowlist(path, explicit):
    """返回 {"only_in_A": {key: reason}, "only_in_B": {key: reason}}。

    文件不存在且不是显式指定 -> 空白名单（规格要求：缺省视为白）。
    文件存在但格式错 -> InputError（带文件:行号）。
    列表项接受两种写法：`- key_path: null` 之外的 `- key: <k>` mapping，
    或者裸字符串 `- <k>`（宽松兼容手写）。
    """
    empty = {side: {} for side in SIDES}
    if not os.path.isfile(path):
        if explicit:
            raise InputError("%s: --allowlist 指定的文件不存在" % path)
        return empty, False
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
        doc = yaml.safe_load(text)
    except OSError as exc:
        raise InputError("%s: 读取失败: %s" % (path, exc))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = "%s:%d" % (path, mark.line + 1) if mark is not None else "%s:?" % path
        raise InputError("%s: YAML 解析失败: %s" % (where, " ".join(str(exc).split())))
    if doc is None:
        return empty, True
    if not isinstance(doc, dict):
        raise InputError("%s:1: 白名单顶层必须是 mapping" % path)

    out = {side: {} for side in SIDES}
    for side in SIDES:
        items = doc.get(side)
        if items is None:
            continue
        if not isinstance(items, list):
            line = _line_of(text, side + ":") or 1
            raise InputError("%s:%d: '%s' 必须是列表" % (path, line, side))
        for idx, item in enumerate(items):
            key = None
            reason = ""
            if isinstance(item, str):
                key = item.strip()
            elif isinstance(item, dict):
                key = item.get("key")
                reason = item.get("reason") or ""
                if not isinstance(key, str):
                    line = _line_of(text, side + ":") or 1
                    raise InputError(
                        "%s:%d: %s[%d] 缺少字符串字段 'key'" % (path, line, side, idx)
                    )
            else:
                line = _line_of(text, side + ":") or 1
                raise InputError(
                    "%s:%d: %s[%d] 必须是 'key: ...' mapping 或字符串"
                    % (path, line, side, idx)
                )
            key = key.strip()
            if not key:
                line = _line_of(text, side + ":") or 1
                raise InputError("%s:%d: %s[%d] 的 key 为空" % (path, line, side, idx))
            out[side][key] = str(reason)
    for unknown in sorted(set(doc) - set(SIDES)):
        print("NOTE: 白名单 %s 里的未知分组 %r 被忽略（只认 %s）"
              % (path, unknown, "/".join(SIDES)))
    return out, True


# --------------------------------------------------------------------------- #
# 比较
# --------------------------------------------------------------------------- #
def compare(path_a, path_b, allowlist_path, allowlist_explicit):
    """返回 dict：机器可读字段 + 下划线开头的纯人类提示字段。"""
    leaves_a, empty_a = load_yaml_leaves(path_a)
    leaves_b, empty_b = load_yaml_leaves(path_b)
    only_a = sorted(set(leaves_a) - set(leaves_b))
    only_b = sorted(set(leaves_b) - set(leaves_a))
    allow, allow_exists = _load_allowlist(allowlist_path, allowlist_explicit)

    allowlisted = []
    violations = []
    allowlisted_detail = []
    for side, keys in (("only_in_A", only_a), ("only_in_B", only_b)):
        for key in keys:
            if key in allow[side]:
                allowlisted.append("%s:%s" % (side, key))
                allowlisted_detail.append((side, key, allow[side][key]))
            else:
                violations.append("%s:%s" % (side, key))

    stale = []
    for side in SIDES:
        present = set(only_a if side == "only_in_A" else only_b)
        for key in sorted(set(allow[side]) - present):
            stale.append((side, key))

    return {
        "only_in_A": only_a,
        "only_in_B": only_b,
        "allowlisted": allowlisted,
        "violations": violations,
        "ok": not violations,
        "_leaves_a": len(leaves_a),
        "_leaves_b": len(leaves_b),
        "_empty_a": empty_a,
        "_empty_b": empty_b,
        "_allow_path": allowlist_path,
        "_allow_exists": allow_exists,
        "_allowlisted_detail": allowlisted_detail,
        "_stale": stale,
    }


def _print_key_list(title, keys):
    if keys:
        print("%s: %d key(s)" % (title, len(keys)))
        for key in keys:
            print("  - %s" % key)
    else:
        print("%s: []" % title)


def print_human(res, path_a, path_b):
    print("A = %s  (leaves=%d)" % (path_a, res["_leaves_a"]))
    print("B = %s  (leaves=%d)" % (path_b, res["_leaves_b"]))
    if res["_allow_exists"]:
        print("allowlist = %s" % res["_allow_path"])
    else:
        print("allowlist = %s (不存在 -> 视为空白名单)" % res["_allow_path"])
    for name, blocks in (("A", res["_empty_a"]), ("B", res["_empty_b"])):
        if blocks:
            print("NOTE: %s 里 %d 个空值容器键按容器处理、不参与比较: %s"
                  % (name, len(blocks), ", ".join(blocks)))
    _print_key_list("only_in_A", res["only_in_A"])
    _print_key_list("only_in_B", res["only_in_B"])
    _print_key_list("allowlisted", res["allowlisted"])
    for side, key, reason in res["_allowlisted_detail"]:
        if reason:
            print("  reason[%s:%s] = %s" % (side, key, reason))
    _print_key_list("violations", res["violations"])
    for side, key in res["_stale"]:
        print("NOTE: 白名单条目 %s:%s 已不再出现在差集里（可删除，防止白名单腐烂）"
              % (side, key))
    if res["ok"]:
        print("RESULT: OK (差集被白名单全覆盖)")
    else:
        print("RESULT: FAIL (未登记差异 %d 个；要么修参数面，要么写进白名单)"
              % len(res["violations"]))


def json_line(res):
    payload = {k: v for k, v in res.items() if not k.startswith("_")}
    return json.dumps(payload, ensure_ascii=False, sort_keys=False)


# --------------------------------------------------------------------------- #
# selftest
# --------------------------------------------------------------------------- #
def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _run_cli(args):
    cmd = [sys.executable, os.path.abspath(__file__)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc


def selftest():
    tmp = tempfile.mkdtemp(prefix="param_face_diff_selftest_")
    base = "# 注释：selftest fixture\nmass: 1.91        # 行内注释\n" \
           "gain:\n  Kp0: 1.5\n  Kp1: 1.5\n" \
           "rc_reverse:\n  roll: false\n" \
           "empty_block:\n"
    a_keys_same = base
    b_keys_same = base.replace("1.91", "1.5").replace("1.5\n", "9.9\n")
    a_extra = base + "vins_guard_mode: 1\n"
    allow = ("only_in_A:\n"
             "  - key: vins_guard_mode\n"
             "    reason: \"实机专用，SITL 用代码默认 1（影子）\"\n"
             "only_in_B: []\n")
    allow_empty = "only_in_A: []\nonly_in_B: []\n"
    p_same_a = os.path.join(tmp, "same_a.yaml")
    p_same_b = os.path.join(tmp, "same_b.yaml")
    p_extra_a = os.path.join(tmp, "extra_a.yaml")
    p_allow = os.path.join(tmp, "allow.yaml")
    p_allow_empty = os.path.join(tmp, "allow_empty.yaml")
    _write(p_same_a, a_keys_same)
    _write(p_same_b, b_keys_same)
    _write(p_extra_a, a_extra)
    _write(p_allow, allow)
    _write(p_allow_empty, allow_empty)

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

    # 用例 1：键集相同（只有取值不同）-> 0
    proc = _run_cli([p_same_a, p_same_b, "--allowlist", p_allow, "--json"])
    check("case1/rc", proc.returncode == 0,
          "期望 0，实际 %d；stdout=%s stderr=%s"
          % (proc.returncode, proc.stdout.strip(), proc.stderr.strip()))

    # 用例 2：A 多一个键、无白名单覆盖 -> 1
    proc = _run_cli([p_extra_a, p_same_b, "--allowlist", p_allow_empty, "--json"])
    check("case2/rc", proc.returncode == 1,
          "期望 1，实际 %d；stdout=%s stderr=%s"
          % (proc.returncode, proc.stdout.strip(), proc.stderr.strip()))
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        payload = {}
        check("case2/json", False, "JSON 解析失败: %s" % exc)
    else:
        check("case2/json", payload.get("only_in_A") == ["vins_guard_mode"]
              and payload.get("ok") is False,
              "only_in_A/ok 不符: %r" % payload)

    # 用例 3：A 多一个键，但被白名单覆盖 -> 0
    proc = _run_cli([p_extra_a, p_same_b, "--allowlist", p_allow, "--json"])
    check("case3/rc", proc.returncode == 0,
          "期望 0，实际 %d；stdout=%s stderr=%s"
          % (proc.returncode, proc.stdout.strip(), proc.stderr.strip()))
    check("case3/allowlisted", "only_in_A:vins_guard_mode" in proc.stdout,
          "allowlisted 未包含 vins_guard_mode: %s" % proc.stdout.strip())

    # 用例 4：同一 mapping 内重复键 -> 必须 exit 2 并指出行号（后者静默覆盖前者=悄悄改配置）
    p_dup = os.path.join(tmp, "dup.yaml")
    _write(p_dup, "mass: 1.91\nmass: 9.99\ngain:\n  Kp0: 1.5\n")
    proc = _run_cli([p_dup, p_same_b, "--allowlist", p_allow_empty, "--json"])
    check("case4/rc", proc.returncode == 2,
          "期望 2（输入错误），实际 %d；stderr=%s" % (proc.returncode, proc.stderr.strip()))
    check("case4/msg", "重复键" in proc.stderr and "dup.yaml" in proc.stderr,
          "错误信息未指出重复键/文件: %s" % proc.stderr.strip())

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
        description="比较两份 px4ctrl 参数 yaml 的叶子键集（参数面），"
                    "差集必须被白名单覆盖。")
    parser.add_argument("a", nargs="?", default=DEFAULT_A, help="A 侧 yaml（实机，默认 %s）" % DEFAULT_A)
    parser.add_argument("b", nargs="?", default=DEFAULT_B, help="B 侧 yaml（SITL，默认 %s）" % DEFAULT_B)
    parser.add_argument("--allowlist", default=DEFAULT_ALLOWLIST,
                        help="白名单 yaml（默认 %s；不存在=空白名单）" % DEFAULT_ALLOWLIST)
    parser.add_argument("--json", action="store_true", help="只输出一行 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑内置自检")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    explicit_allow = any(a == "--allowlist" or a.startswith("--allowlist=")
                         for a in (argv if argv is not None else sys.argv[1:]))
    try:
        res = compare(args.a, args.b, args.allowlist, explicit_allow)
    except InputError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    if args.json:
        print(json_line(res))
    else:
        print_human(res, args.a, args.b)
        # 规格要求：人类可读输出之后，最后一行仍是机器可读 JSON。
        print(json_line(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
