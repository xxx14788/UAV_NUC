#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_v8_tools.py — 判读工具 v8 箱表扩支持面补丁（红线⑤合规：仅增箱表不改判读语义；v7 先例=坑9）
对象: corridor_geom_audit.py（WORLD_TABLES 增 v8 表）+ tools_b4/cling_pairing_bybox.py（BOXES_V8 + --world 选择）
箱位正源=gen_corridor_world_v8.py 同源公式（E/NE 航线系 d=0.60 错列）——本脚本自算并与生成器输出对照断言。
"""
import math, sys

OX, OY = 1.01, 0.98
STAGGER = 0.60
E_GOAL_RAW = (13.01, 0.98); NE_GOAL_RAW = (9.4953, 9.4653)
E_S = [2.0, 4.5, 7.0, 9.5, 12.0];  E_SIG = [1, -1, 1, -1, 1]
NE_S = [2.5, 5.0, 7.5, 10.0, 12.5]; NE_SIG = [1, -1, 1, -1, 1]

def frame(goal):
    gx, gy = goal; L = math.hypot(gx, gy)
    return ((gx/L, gy/L), (-gy/L, gx/L))

def boxes():
    out = []
    (eu, ep) = frame(E_GOAL_RAW); (nu, np_) = frame(NE_GOAL_RAW)
    for i, (s, sg) in enumerate(zip(E_S, E_SIG), 1):
        out.append((f"cB{i}", OX + s*eu[0] + sg*STAGGER*ep[0], OY + s*eu[1] + sg*STAGGER*ep[1]))
    for i, (s, sg) in enumerate(zip(NE_S, NE_SIG), 1):
        out.append((f"cN{i}", OX + s*nu[0] + sg*STAGGER*np_[0], OY + s*nu[1] + sg*STAGGER*np_[1]))
    return out

BX = boxes()
print("v8 箱表（正源自算）:")
for bn, gx, gy in BX:
    print(f"  {bn}: gazebo({gx:.3f},{gy:.3f}) odom({gx-OX:.2f},{gy-OY:.2f})")

# ---- 与生成器实际输出对照断言（防公式漂移; 生成器须已先跑） ----
import subprocess, re
world = open("/home/ghj/sitl_sim/c3_corridor_20261013/sitl_world_corridor_v8.world", encoding="utf-8").read()
for bn, gx, gy in BX:
    m = re.search(rf'<model name="{bn}">\s*<pose>([-0-9.]+) ([-0-9.]+) ', world)
    assert m, f"{bn} not in world xml"
    assert abs(float(m.group(1)) - gx) < 5e-4 and abs(float(m.group(2)) - gy) < 5e-4, \
        f"{bn} mismatch: computed({gx:.3f},{gy:.3f}) world({m.group(1)},{m.group(2)})"
print("对照断言 PASS: 自算箱位与 v8 world XML 逐箱一致")

# ---- 1) geom audit ----
GA = "/home/ghj/sitl_sim/c3_corridor_20261013/corridor_geom_audit.py"
s = open(GA, encoding="utf-8").read()
anchor = '    "v7": {'
assert s.count(anchor) == 1
v8_rows = ",\n".join(f'        "{bn}": ({gx:.3f}, {gy:.3f}, 0.5, 0.0, 1.8)' for bn, gx, gy in BX)
v8_block = ('    "v8": {\n' + v8_rows + ",\n    },\n")
# v7 表结尾锚（cN3 行 + 收括号）
anchor2 = '"cN3": (6.960, 7.759, 0.5, 0.0, 1.8),\n    },'
assert s.count(anchor2) == 1, "v7 table tail anchor miss"
s = s.replace(anchor2, '"cN3": (6.960, 7.759, 0.5, 0.0, 1.8),\n    },\n' + v8_block.rstrip("\n"), 1)
open(GA, "w", encoding="utf-8").write(s)
print("geom audit: v8 表已插入")

# ---- 2) cling_pairing_bybox ----
CP = "/home/ghj/sitl_sim/c3_corridor_20261013/tools_b4/cling_pairing_bybox.py"
c = open(CP, encoding="utf-8").read()
a1 = 'BOXES_V7 = {"cB1": (4.44, 0.94, "tag"), "cB2": (9.52, 0.12, "ctrl-Wood"), "cB3": (11.92, 1.50, "tag"),\n            "cN1": (2.41, 3.25, "tag"), "cN2": (5.03, 4.16, "ctrl-Bricks"), "cN3": (5.95, 6.78, "tag")}'
assert c.count(a1) == 1, "BOXES_V7 anchor miss"
v8_dict_rows = ",\n            ".join(
    f'"{bn}": ({gx-OX:.2f}, {gy-OY:.2f}, "{"ctrl-Wood" if bn=="cB2" else "ctrl-Bricks" if bn=="cN2" else "tag"}")'
    for bn, gx, gy in BX)
add = a1 + '\nBOXES_V8 = {' + v8_dict_rows + '}\nBOXES = BOXES_V7  # --world v8 时切（扩支持面, 判读语义零改动）'
c = c.replace(a1, add, 1)
assert c.count("BOXES_V7.items()") == 1 and c.count("BOXES_V7[bn][2]") == 1
c = c.replace("BOXES_V7.items()", "BOXES.items()").replace("BOXES_V7[bn][2]", "BOXES[bn][2]")
old_main = 'if __name__ == "__main__":\n    for d in sys.argv[1:]:\n        main(d)'
assert c.count(old_main) == 1
new_main = ('if __name__ == "__main__":\n'
            '    if "--world" in sys.argv:\n'
            '        wv = sys.argv[sys.argv.index("--world") + 1]\n'
            '        if wv == "v8":\n'
            '            BOXES = BOXES_V8\n'
            '        elif wv != "v7":\n'
            '            sys.exit("unknown --world " + wv)\n'
            '    for d in (a for a in sys.argv[1:] if not a.startswith("--world")):\n'
            '        if d == "v8" or d == "v7":\n'
            '            continue\n'
            '        main(d)')
c = c.replace(old_main, new_main, 1)
open(CP, "w", encoding="utf-8").write(c)
print("cling_pairing_bybox: BOXES_V8 + --world 已加")
print("ALL TOOLS PATCHED")
