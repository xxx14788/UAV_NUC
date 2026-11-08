#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1（方案 v2 / C1-C4）：接缝契约的静态检查 + **负测试** + 金丝雀纯函数。

无 ROS 依赖，可在任何机器跑（必须在 NUC 上，因为要读真实文件）。

负测试的意义：证明检查器"有牙"——故意破坏 6 个接缝，每一个都必须被 --static 抓住，
且抓在**对应的那一条**上（不是碰巧别的条失败）。

退出码：0=全过，2=有失败。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

FV = os.path.expanduser("~/sitl_realmachine/flight_v1")
CHECKER = os.path.join(FV, "check_interfaces.py")
CONTRACT = os.path.join(FV, "contract", "flight_contract.yaml")
LAUNCH = os.path.join(FV, "run_planner_realmachine_map_v1.launch")
MISSION = os.path.join(FV, "flight_mission.py")
STACK = os.path.expanduser("~/realflight_stack.sh")

results = []


def ok(name, cond, actual=""):
    results.append((name, bool(cond), actual))
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if actual == "" else "  [%s]" % actual),
          flush=True)
    return bool(cond)


def run_static(contract_path, stack=STACK):
    proc = subprocess.run(
        [sys.executable, CHECKER, "--static", "--contract", contract_path,
         "--launch", LAUNCH, "--mission", MISSION, "--stack", stack],
        capture_output=True, text=True)
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return proc.returncode, "PARSE_ERROR", ["<stdout 不可解析>"], proc.stdout[-400:]
    bad = [c["name"] for c in data.get("checks", []) if not c["ok"]]
    return proc.returncode, data.get("verdict"), bad, ""


def mutate(fn):
    import yaml
    with open(CONTRACT, encoding="utf-8") as fh:
        c = yaml.safe_load(fh)
    fn(c)
    fd, path = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(c, fh, allow_unicode=True, sort_keys=False)
    return path


def main():
    if not os.path.exists(CONTRACT):
        print("!! 契约不存在：%s" % CONTRACT)
        return 2

    print("== A. 正向：原样契约必须 PASS")
    rc, verdict, bad, extra = run_static(CONTRACT)
    ok("原样契约 --static PASS", rc == 0 and verdict == "PASS",
       "rc=%d verdict=%s bad=%s %s" % (rc, verdict, bad, extra))

    print("== B. 负测试（每一刀都必须被抓住，且抓在对应的那条上）")
    cases = [
        ("深度话题改回 aligned_depth_to_color",
         lambda c: c["seams"]["depth"].__setitem__("topic", "/camera/aligned_depth_to_color/image_raw"),
         "深度"),
        ("camera_pose 话题写错",
         lambda c: c["seams"]["camera_pose"].__setitem__("topic", "/planner/camera_pose_wrong"),
         "位姿"),
        ("takeoff_height=0.5（与规划器/px4ctrl 不一致）",
         lambda c: c["params"].__setitem__("takeoff_height", 0.5),
         "高度"),
        ("goal_radius=2.0（与规划器不一致）",
         lambda c: c["params"].__setitem__("goal_radius_m", 2.0),
         "半径"),
        ("目标直连 /move_base_simple/goal（绕过校验门）",
         lambda c: c["seams"]["goal"].__setitem__("topic", "/move_base_simple/goal"),
         "目标"),
        ("阈值非法 max_skew_s=0",
         lambda c: c["seams"]["camera_pose"].__setitem__("max_skew_s", 0),
         "阈值"),
    ]
    for name, fn, keyword in cases:
        path = mutate(fn)
        try:
            rc, verdict, bad, extra = run_static(path)
            hit = any(keyword in b for b in bad)
            ok(name + " -> FAIL 且抓在对应条", rc != 0 and hit,
               "rc=%d bad=%s %s" % (rc, bad, extra))
        finally:
            os.unlink(path)

    print("== C. 负测试：健康门又写回旧话题（P0 那个真实缺陷）")
    tmpd = tempfile.mkdtemp(prefix="stackmut_")
    bad_stack = os.path.join(tmpd, "stack.sh")
    shutil.copy(STACK, bad_stack)
    with open(bad_stack, encoding="utf-8") as fh:
        txt = fh.read()
    txt = txt.replace('hz "$DEPTH_TOPIC"', 'hz "/camera/aligned_depth_to_color/image_raw"')
    with open(bad_stack, "w", encoding="utf-8") as fh:
        fh.write(txt)
    try:
        rc, verdict, bad, extra = run_static(CONTRACT, stack=bad_stack)
        ok("健康门写回 aligned_depth -> FAIL", rc != 0 and any("健康门" in b for b in bad),
           "rc=%d bad=%s" % (rc, bad))
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)

    print("== D. 金丝雀判据（纯函数）+ 契约取值")
    sys.path.insert(0, FV)
    try:
        import flight_mission as fm
    except Exception as exc:
        ok("flight_mission 可导入（无 ROS）", False, repr(exc))
        fm = None
    if fm is not None:
        ok("flight_mission 可导入（无 ROS）", True)
        # 2026-11-08 二审：判据="离目标还差 >0.5 m 且没有指令速度"
        ok("金丝雀:离目标 1.2 m 且不动 -> 中止",
           fm.goal_stall_verdict(5.0, 1.20, 0.001) is True)
        ok("金丝雀:离目标 0.1 m（近目标已到）-> 不中止",
           fm.goal_stall_verdict(5.0, 0.10, 0.0) is False)
        ok("金丝雀:离目标 0.6 m 但在动 -> 不中止",
           fm.goal_stall_verdict(5.0, 0.60, 0.12) is False)
        ok("金丝雀:未到 5 s -> 不中止",
           fm.goal_stall_verdict(3.0, 1.20, 0.0) is False)
        ok("金丝雀:离目标 0.5 m 边界（> 才中止）-> 不中止",
           fm.goal_stall_verdict(5.0, 0.50, 0.0) is False)
        ok("契约取值:GOAL_RADIUS 来自契约",
           abs(fm.GOAL_RADIUS - 3.5) < 1e-9, str(fm.GOAL_RADIUS))
        ok("契约缺失时回退默认值",
           abs(fm._contract_value("params.no_such_key", 7.5) - 7.5) < 1e-9)

    bad_list = [r for r in results if not r[1]]
    print("\n==== T1 结果：%d/%d PASS ====" % (len(results) - len(bad_list), len(results)))
    return 0 if not bad_list else 2


if __name__ == "__main__":
    sys.exit(main())
