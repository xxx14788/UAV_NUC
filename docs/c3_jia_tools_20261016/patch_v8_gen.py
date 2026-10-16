#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_v8_gen.py — gen_corridor_world_v7.py → gen_corridor_world_v8.py 派生补丁（③C-甲 Phase B）
改造点（全部精确字符串替换，逐项断言命中）:
  1) 箱位表参数化（env 覆写, 默认=v8 设计值: E[2.0,4.5,7.0,9.5,12.0]/NE[2.5,5.0,7.5,10.0,12.5] 交错±）
  2) tag 箱=全箱减对照（cB2/cN2 恒对照, 其余全 tag=8 箱）
  3) 新增硬门④: 每航线交错织行段 ≥4 ∧ 末箱-终点距 ≥ HALF_INFL
  4) 头注释/world 注释/默认输出名/model.config 描述 v8 化
确定性承袭: 同参数同 md5。
"""
import sys

SRC = "gen_corridor_world_v7.py"
DST = "gen_corridor_world_v8.py"

s = open(SRC, encoding="utf-8").read()
n0 = len(s)
REPL = []

def rep(old, new, cnt=1):
    global s
    c = s.count(old)
    assert c == cnt, f"FATAL anchor count={c} (expect {cnt}): {old[:80]!r}"
    s = s.replace(old, new)
    REPL.append((old[:60], c))

# 1) 文件头
rep('"""gen_corridor_world_v7.py — ③C 终局 C-2: world v7 正式生成器（2026-10-15）',
    '"""gen_corridor_world_v8.py — ③C-甲 Phase B: world v8 织行增益生成器（2026-10-16）\n'
    'v8 设计（任务书 §三 预注册）: 每航线 ≥5 箱/沿航线均匀 2.5m 间距（E 航线 v7.3 的 5.0m 偏离回归均匀）/\n'
    '交错符号全交替=每航线织行段 4; d=0.60/W=2.6/tag 400mm 每垂直面/对照 cB2 Wood+cN2 Bricks 承袭不动。\n'
    '参数化（env 覆写, v8.x 迭代用）: V8_E_S/V8_E_SIGNS/V8_NE_S/V8_NE_SIGNS（逗号分隔）。')

# 2) 箱位表参数化
rep('E_S_ALONG = [4.5, 9.5, 12.0]   # v7: 7→6 箱, E 去中段箱 s=7.0（间距 5.0/2.5）\n'
    'E_SIGNS   = [+1, -1, +1]\n'
    'NE_S = [4.0, 6.5, 9.0]\n'
    'NE_SIGNS = [+1, -1, +1]',
    'E_S_ALONG = [float(x) for x in os.environ.get("V8_E_S", "2.0,4.5,7.0,9.5,12.0").split(",")]   # v8: 5 箱均匀 2.5m\n'
    'E_SIGNS   = [int(x) for x in os.environ.get("V8_E_SIGNS", "+1,-1,+1,-1,+1").split(",")]\n'
    'NE_S = [float(x) for x in os.environ.get("V8_NE_S", "2.5,5.0,7.5,10.0,12.5").split(",")]      # v8: 5 箱均匀 2.5m\n'
    'NE_SIGNS = [int(x) for x in os.environ.get("V8_NE_SIGNS", "+1,-1,+1,-1,+1").split(",")]')

# 3) tag 箱=派生（全箱减对照）
rep('TAG_BOXES = {"cB1", "cB3", "cN1", "cN3"}    # tag 箱\n'
    'CTRL_BOXES = {"cB2": 0, "cN2": 1}           # 对照箱: cB2=Wood(0), cN2=Bricks(1)',
    'CTRL_BOXES = {"cB2": 0, "cN2": 1}           # 对照箱恒定: cB2=Wood(0), cN2=Bricks(1); 其余箱全 tag')

rep('for i, (s_, sg) in enumerate(zip(NE_S, NE_SIGNS), 1):\n'
    '    bx = OX + s_*NE_U[0] + sg*STAGGER*NE_P[0]\n'
    '    by = OY + s_*NE_U[1] + sg*STAGGER*NE_P[1]\n'
    '    boxes.append((f"cN{i}", bx, by, None))',
    'for i, (s_, sg) in enumerate(zip(NE_S, NE_SIGNS), 1):\n'
    '    bx = OX + s_*NE_U[0] + sg*STAGGER*NE_P[0]\n'
    '    by = OY + s_*NE_U[1] + sg*STAGGER*NE_P[1]\n'
    '    boxes.append((f"cN{i}", bx, by, None))\n'
    'TAG_BOXES = {bn for (bn, _, _, _) in boxes if bn not in CTRL_BOXES}  # v8: 派生（全箱减对照）')

# 4) 硬门④（织行段+终点净空）+ 总门条件
rep('if not (gate1 and gate2 and gate3):\n'
    '    print("硬门 FAIL → 不产出 world（复核次序: w_c 不足先 +W(0.2 步进) 再 −d(0.05 步进), 换代 v7.x）")\n'
    '    sys.exit(1)',
    'print("=" * 72)\n'
    'print("硬门④ 织行段数+终点净空（门: 每航线交错织行段 ≥4 ∧ 末箱-终点距 ≥ 膨胀半宽）:")\n'
    'def _weave(sg_list): return sum(1 for a, b in zip(sg_list, sg_list[1:]) if a * b < 0)\n'
    'gate4 = True\n'
    'for lane, s_list, sg_list, goal in (("E", E_S_ALONG, E_SIGNS, E_GOAL_RAW), ("NE", NE_S, NE_SIGNS, NE_GOAL_RAW)):\n'
    '    u_, p_ = lane_frame_params(goal)\n'
    '    bx_ = OX + s_list[-1]*u_[0] + sg_list[-1]*STAGGER*p_[0]\n'
    '    by_ = OY + s_list[-1]*u_[1] + sg_list[-1]*STAGGER*p_[1]\n'
    '    dg_ = math.hypot(OX + goal[0] - bx_, OY + goal[1] - by_)\n'
    '    wv_ = _weave(sg_list)\n'
    '    ok_ = (wv_ >= 4) and (dg_ >= HALF_INFL)\n'
    '    gate4 &= ok_\n'
    '    print(f"  {lane}: 交错织行段={wv_}  末箱-终点距={dg_:.3f}m（门≥{HALF_INFL:.3f}）  [{\'PASS\' if ok_ else \'FAIL\'}]")\n'
    'if not (gate1 and gate2 and gate3 and gate4):\n'
    '    print("硬门 FAIL → 不产出 world（复核次序: w_c 不足先 +W(0.2 步进) 再 −d(0.05 步进); 织行段不足查 signs 交替; 终点净空不足缩末箱 s, 换代 v8.x）")\n'
    '    sys.exit(1)')

# 5) world 头注释
rep('    <!-- sitl_world_corridor_v7 — ③C 终局 C-2 (2026-10-15)\n'
    '    规格: 6 箱(E x3: s=4.5/9.5/12.0 + NE x3: s=4.0/6.5/9.0) 1×1×1.8m; 大错列 d=0.60; 走廊半宽 W=2.6',
    '    <!-- sitl_world_corridor_v8 — ③C-甲 Phase B 织行增益 (2026-10-16)\n'
    '    规格: 10 箱(E x5: s=2.0/4.5/7.0/9.5/12.0 + NE x5: s=2.5/5.0/7.5/10.0/12.5, 均匀 2.5m) 1×1×1.8m; 大错列 d=0.60; 走廊半宽 W=2.6')

# 6) 默认输出名
rep('out = sys.argv[1] if len(sys.argv) > 1 else "sitl_world_corridor_v7.world"',
    'out = sys.argv[1] if len(sys.argv) > 1 else "sitl_world_corridor_v8.world"')

# 7) model.config 描述
rep('<description>C3 v7 tag face materials (gen_corridor_world_v7.py)</description>',
    '<description>C3 v8 tag face materials (gen_corridor_world_v8.py)</description>')

open(DST, "w", encoding="utf-8").write(s)
print(f"patched OK: {len(REPL)} anchors replaced; {SRC}({n0}B) -> {DST}({len(s)}B)")
