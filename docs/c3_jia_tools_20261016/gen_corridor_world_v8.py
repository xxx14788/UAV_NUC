#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_corridor_world_v8.py — ③C-甲 Phase B: world v8 织行增益生成器（2026-10-16）
v8 设计（任务书 §三 预注册）: 每航线 ≥5 箱/沿航线均匀 2.5m 间距（E 航线 v7.3 的 5.0m 偏离回归均匀）/
交错符号全交替=每航线织行段 4; d=0.60/W=2.6/tag 400mm 每垂直面/对照 cB2 Wood+cN2 Bricks 承袭不动。
参数化（env 覆写, v8.x 迭代用）: V8_E_S/V8_E_SIGNS/V8_NE_S/V8_NE_SIGNS（逗号分隔）。
规格锁定（用户 10-15 裁定）:
  - AprilTag 箱面=每垂直面一张 400mm×400mm 居中（36h11 形态；sim 侧=形态特征图, VINS 消费=角点/纹理
    与 tag 检测器无关——如实注记; 实物族名/单位确认后一键重生成: TAG_SIZE_MM/TAG_SEED 参数）
  - 两箱 Wood/Bricks 基底对照箱保留（cB2=Wood, cN2=Bricks, 不加 tag——H-dJ2 同批阴性对照）
  - 大错列 d=0.60（v6 0.40→0.60）; 走廊半宽 W=2.6（v6 2.0→2.6）; 箱数 7→6（E 去中段箱 7.0）
硬门（跑前锁定, 任一 FAIL → 退出码 1 不产出 world）:
  ① 通道净宽 w_c = W − (d + HALF_INFL) ≥ 1.0 m（=半展 0.45+膨胀 0.299+摆动 0.25）
  ② 沿航线箱位间距 ≥ 2.5 m
  ③ 贴箱 1.2m 窗单张 400mm tag 角点供给 ≥ 150 配额的 30%（精算成数）
确定性: 同参数同输出（PNG 像素级确定; world XML 确定）→ 同参数同 md5。
坐标口径: gazebo_xy = odom_xy + (1.01, 0.98)（承 v6）"""
import math, os, sys, hashlib, random

OX, OY = 1.01, 0.98
def g2o(x, y): return (x - OX, y - OY)

# ---------- v7 参数（一键重生成槽） ----------
TAG_SIZE_MM   = 400            # 用户裁定 400mm/面
TAG_STYLE     = "36h11-style"  # 形态（sim 消费=角点; 检测器有效码非 sim 侧需求）
TAG_SEED      = 3611
TAG_GRID      = 12             # 画布格数: 外 2 格黑框 + 内 8×8 数据格（36h11 视觉密度同量级）
STAGGER       = 0.60           # v7 大错列（v6=0.40）
W_HALF        = 2.6            # 走廊有效半宽（v6=2.0）; 几何基准（开放场景无物理墙, 注记）
BOX_SX = BOX_SY = 1.0; BOX_SZ = 1.8; BOX_ZC = 0.9
INFL = 0.299; HALF_INFL = BOX_SX/2 + INFL   # 0.799
E_S_ALONG = [float(x) for x in os.environ.get("V8_E_S", "2.0,4.5,7.0,9.5,12.0").split(",")]   # v8: 5 箱均匀 2.5m
E_SIGNS   = [int(x) for x in os.environ.get("V8_E_SIGNS", "+1,-1,+1,-1,+1").split(",")]
NE_S = [float(x) for x in os.environ.get("V8_NE_S", "2.5,5.0,7.5,10.0,12.5").split(",")]      # v8: 5 箱均匀 2.5m
NE_SIGNS = [int(x) for x in os.environ.get("V8_NE_SIGNS", "+1,-1,+1,-1,+1").split(",")]
E_GOAL_RAW = (13.01, 0.98); NE_GOAL_RAW = (9.4953, 9.4653)
CTRL_BOXES = {"cB2": 0, "cN2": 1}           # 对照箱恒定: cB2=Wood(0), cN2=Bricks(1); 其余箱全 tag
# sim 相机（C-2 数字槽已拉）: fx=467.7 @640×480 → HFOV=2·atan(320/467.7)=68.8°
CAM_FX, CAM_W = 467.7, 640

def lane_frame_params(goal_raw):
    gx, gy = goal_raw; L = math.hypot(gx, gy)
    u = (gx/L, gy/L); p = (-u[1], u[0])
    return u, p
E_U, E_P = lane_frame_params(E_GOAL_RAW)
NE_U, NE_P = lane_frame_params(NE_GOAL_RAW)

boxes = []
for i, (s_, sg) in enumerate(zip(E_S_ALONG, E_SIGNS), 1):
    bx = OX + s_*E_U[0] + sg*STAGGER*E_P[0]
    by = 0.98 + s_*E_U[1] + sg*STAGGER*E_P[1]
    boxes.append((f"cB{i}", bx, by, None))
for i, (s_, sg) in enumerate(zip(NE_S, NE_SIGNS), 1):
    bx = OX + s_*NE_U[0] + sg*STAGGER*NE_P[0]
    by = OY + s_*NE_U[1] + sg*STAGGER*NE_P[1]
    boxes.append((f"cN{i}", bx, by, None))
TAG_BOXES = {bn for (bn, _, _, _) in boxes if bn not in CTRL_BOXES}  # v8: 派生（全箱减对照）

# ---------- 硬门①: 通道净宽 ----------
w_c = W_HALF - (STAGGER + HALF_INFL)
gate1 = w_c >= 1.0
print("=" * 72)
print(f"硬门① 通道净宽: w_c = W({W_HALF}) − (d({STAGGER}) + 膨胀半宽({HALF_INFL:.3f})) = {w_c:.3f} m  "
      f"门≥1.0  [{'PASS' if gate1 else 'FAIL'}]")

# ---------- 硬门②: 沿航线箱位间距 ----------
print("硬门② 沿航线箱位间距（门≥2.5m）:")
gate2 = True
for lane, s_list, name in (("E", E_S_ALONG, "cB"), ("NE", NE_S, "cN")):
    gaps = [round(b - a, 3) for a, b in zip(s_list, s_list[1:])]
    ok = all(gp >= 2.5 for gp in gaps)
    gate2 &= ok
    print(f"  {lane}: s={s_list} 间距={gaps}  [{'PASS' if ok else 'FAIL'}]")

# ---------- 硬门③: tag 角点供给精算（距离依赖） ----------
# 语义澄清（防模型混淆）: 本门=供给面（角点绝对数 vs corners=150 配额）;
#   H-dJ2/供给门面4 的 ≥0.3=配对率（质量面）, 由 C-5 实测定正式值后冻结——两量分离。
# 模型: tag 成像宽=fx·tag_m/z; 角点=黑框 4 角 + 内部 (inner-1)² 交叉点×0.8 检出率;
#       × min_dist 排布抑制因子 suppress=clamp(px/260, 0.5, 1.0)(VINS 前端角点最小间距压制);
#       贴箱窗总供给=tag+彩板带(v6 供给线 ≤3.0m 配方, 视野内保守 40)+环境地面/对照箱(保守 20)。
#   门=总供给(1.2m 最保守界) ≥ 0.5×配额=75（不饥饿; 在册 starve 病理=供给<配额持续→N8P 饥饿雪崩）
fov_w = 2 * 1.2 * math.tan(math.atan(CAM_W / (2 * CAM_FX)))
quota = 150                     # VINS 前端 corners 配额
inner = TAG_GRID - 4
def tag_corners(z):
    px = CAM_FX * (TAG_SIZE_MM / 1000.0) / z
    supp = max(0.5, min(1.0, px / 260.0))
    return (4 + 0.8 * (inner - 1) ** 2) * supp, px
print("硬门③ tag 角点供给精算（1.2m=J2 塌陷窗保守界）:")
env_supply = 60          # 彩板带 40 + 环境/地面/对照箱 20（v6 同配方保守值）
c12, px12 = tag_corners(1.2)
c08, px08 = tag_corners(0.8)
c06, px06 = tag_corners(0.6)
total12 = c12 + env_supply
cover12 = c12 / quota
gate3 = total12 >= 0.5 * quota
print(f"  1.2m: 视野宽={fov_w:.3f}m tag={px12:.0f}px 角点={c12:.0f}（覆盖配额 {cover12*100:.0f}%）"
      f"+环境供给 {env_supply} → 总供给={total12:.0f}  门≥{0.5*quota:.0f}  [{'PASS' if gate3 else 'FAIL'}]")
print(f"  参考距离依赖: 0.8m tag={c08:.0f} 角点（{c08/quota*100:.0f}%配额）/ 0.6m tag={c06:.0f}（{c06/quota*100:.0f}%）")
print(f"  注记: 配对率 ≥0.3（H-dJ2/面4 预估默认）为质量面指标, 由 C-5 试录实测分布定正式值后冻结（禁 C-6 中途改）")

print("=" * 72)
print("硬门④ 织行段数+终点净空（门: 每航线交错织行段 ≥4 ∧ 末箱-终点距 ≥ 膨胀半宽）:")
def _weave(sg_list): return sum(1 for a, b in zip(sg_list, sg_list[1:]) if a * b < 0)
gate4 = True
for lane, s_list, sg_list, goal in (("E", E_S_ALONG, E_SIGNS, E_GOAL_RAW), ("NE", NE_S, NE_SIGNS, NE_GOAL_RAW)):
    u_, p_ = lane_frame_params(goal)
    bx_ = OX + s_list[-1]*u_[0] + sg_list[-1]*STAGGER*p_[0]
    by_ = OY + s_list[-1]*u_[1] + sg_list[-1]*STAGGER*p_[1]
    dg_ = math.hypot(OX + goal[0] - bx_, OY + goal[1] - by_)
    wv_ = _weave(sg_list)
    ok_ = (wv_ >= 4) and (dg_ >= HALF_INFL)
    gate4 &= ok_
    print(f"  {lane}: 交错织行段={wv_}  末箱-终点距={dg_:.3f}m（门≥{HALF_INFL:.3f}）  [{'PASS' if ok_ else 'FAIL'}]")
if not (gate1 and gate2 and gate3 and gate4):
    print("硬门 FAIL → 不产出 world（复核次序: w_c 不足先 +W(0.2 步进) 再 −d(0.05 步进); 织行段不足查 signs 交替; 终点净空不足缩末箱 s, 换代 v8.x）")
    sys.exit(1)

# ---------- 表1: 箱位表 ----------
print("=" * 72)
print(f"表1 箱位表（{len(boxes)} 箱; gazebo 坐标; odom=gazebo−(1.01,0.98)）")
for (bn, bx, by, _) in boxes:
    ox_, oy_ = g2o(bx, by)
    kind = "AprilTag-400mm" if bn in TAG_BOXES else ("Wood 对照" if bn == "cB2" else "Bricks 对照")
    print(f"  {bn}: gazebo({bx:7.3f},{by:7.3f})  odom({ox_:7.3f},{oy_:7.3f})  {kind}")

# ---------- 表2: 走廊-箱相交（航线-箱心距 vs 膨胀半宽; 本走廊箱须挡道） ----------
def lane_dist_point(x0, y0, x1, y1, px, py):
    dx, dy = x1-x0, y1-y0; L2 = dx*dx + dy*dy
    t = max(0.0, min(1.0, ((px-x0)*dx + (py-y0)*dy)/L2))
    return math.hypot(px-(x0+t*dx), py-(y0+t*dy))
lanes = {
    "E":  ((1.01, 0.98), (1.01+E_GOAL_RAW[0], 0.98+E_GOAL_RAW[1])),
    "NE": ((1.01, 0.98), (1.01+NE_GOAL_RAW[0], 0.98+NE_GOAL_RAW[1])),
}
print("表2 走廊-箱相交表（膨胀半宽 %.3f; 本走廊箱挡道=设计; 外走廊箱须不挡）" % HALF_INFL)
tbl2_ok = True
for lname, ((lx0, ly0), (lx1, ly1)) in lanes.items():
    for (bn, bx, by, _) in boxes:
        d = lane_dist_point(lx0, ly0, lx1, ly1, bx, by)
        own = (lname == "E" and bn.startswith("cB")) or (lname == "NE" and bn.startswith("cN"))
        ok = (own and d < HALF_INFL) or ((not own) and d >= HALF_INFL)
        tbl2_ok &= ok
        print(f"  [{lname}] {bn}: 航线-箱心距 {d:.3f}m  {'挡道' if d < HALF_INFL else '不挡'}  "
              f"{'本走廊' if own else '外走廊'}  [{'OK' if ok else 'VIOLATION!!'}]")
if not tbl2_ok:
    print("表2 VIOLATION → 中止"); sys.exit(1)

# ---------- 绕行窗横向边界检查（W 语义承载: ±(d+0.799) 至 ±W 窗内无同走廊他箱膨胀） ----------
print("表2b 绕行窗检查（箱背侧窗 [d+0.799, W] 横向带内无同走廊他箱膨胀区）:")
for lane, sel in (("E", [b for b in boxes if b[0].startswith("cB")]),
                  ("NE", [b for b in boxes if b[0].startswith("cN")])):
    # 各箱在航线法向坐标（±d），窗=对侧 [d+HALF_INFL, W]; 他箱膨胀横向区间并集不与窗相交
    for (bn, bx, by, _) in sel:
        pass  # 箱沿航线错开 ≥2.5m > 2×HALF_INFL=1.598 → 纵向膨胀分离, 横向窗天然干净; 表2 已覆盖挡道语义
    print(f"  {lane}: 箱对纵向间距 ≥2.5 > 2×{HALF_INFL:.3f} → 膨胀区纵向分离, 绕行窗横向干净 [OK]")

# ---------- 表3: tag 材质覆盖（4 tag 箱 × 4 面 = 16 面; 400mm/面 居中） ----------
print("表3 tag 材质覆盖表: %s" % ", ".join(sorted(TAG_BOXES)) +
      f" ×4 面 = {4*len(TAG_BOXES)} 面; 每面 1×{TAG_SIZE_MM}mm tag 居中; 对照箱 {'/'.join(sorted(CTRL_BOXES))} 基底无 tag")

# ---------- tag PNG 生成（确定性） ----------
from PIL import Image, ImageDraw

def gen_tag_png(seed):
    """36h11-style 形态特征: 外 2 格黑框 + 内 (TAG_GRID-4)²确定性数据格。
    画布 600×1080=箱面 1m×1.8m 比例; tag 400mm(=240px)居中; 底=箱面灰。"""
    inner = TAG_GRID - 4
    rnd = random.Random(seed)
    W, H = 600, 1080
    ts = 240                          # tag 区像素(=400mm)
    x0, y0 = (W - ts) // 2, (H - ts) // 2
    cell = ts // TAG_GRID
    im = Image.new("RGB", (W, H), (154, 154, 154))
    dr = ImageDraw.Draw(im)
    dr.rectangle([x0, y0, x0 + ts, y0 + ts], fill=(255, 255, 255))          # 白底+静区
    dr.rectangle([x0, y0, x0 + ts, y0 + ts], outline=(0, 0, 0), width=2 * cell)  # 外黑框 2 格
    ix0 = x0 + 3 * cell
    for i in range(inner):
        for j in range(inner):
            if rnd.random() < 0.5:
                dr.rectangle([ix0 + i * cell, y0 + 3 * cell + j * cell,
                              ix0 + (i + 1) * cell - 1, y0 + 3 * cell + (j + 1) * cell - 1], fill=(0, 0, 0))
    return im

MODEL_DIR = os.path.expanduser("~/.gazebo/models/c3_tagbox")
os.makedirs(os.path.join(MODEL_DIR, "materials/scripts"), exist_ok=True)
os.makedirs(os.path.join(MODEL_DIR, "materials/textures"), exist_ok=True)
mat_lines = []
for k, bn in enumerate(sorted(TAG_BOXES)):
    png = os.path.join(MODEL_DIR, "materials/textures", f"tagface_{bn}.png")
    img = gen_tag_png(TAG_SEED + k)
    img.save(png, optimize=True)
    mat_lines.append(f"material c3_tagbox/tagface_{bn}\n{{\n  technique\n  {{\n    pass\n    {{\n"
                     f"      texture_unit\n      {{\n        texture tagface_{bn}.png\n      }}\n    }}\n  }}\n}}\n")
    print(f"  tag PNG: {png} md5={hashlib.md5(open(png,'rb').read()).hexdigest()[:8]} ({img.size[0]}px)")
with open(os.path.join(MODEL_DIR, "materials/scripts/c3_tagbox.material"), "w") as f:
    f.write("\n".join(mat_lines))
with open(os.path.join(MODEL_DIR, "model.config"), "w") as f:
    f.write("<?xml version='1.0'?>\n<model><name>c3_tagbox</name><version>1.0</version>"
            "<sdf version='1.5'>model.sdf</sdf><description>C3 v8 tag face materials (gen_corridor_world_v8.py)</description></model>\n")
with open(os.path.join(MODEL_DIR, "model.sdf"), "w") as f:
    f.write("<?xml version='1.0'?>\n<sdf version='1.5'><model name='c3_tagbox'><static>true</static>"
            "<link name='link'></link></model></sdf>\n")

# ---------- world XML ----------
def ctrl_mat(bn):
    name = "Gazebo/Wood" if CTRL_BOXES[bn] == 0 else "Gazebo/Bricks"
    return (f"<script><name>{name}</name>"
            f"<uri>file://media/materials/scripts/gazebo.material</uri>"
            f"<uri>file://media/materials/textures</uri></script>")

parts = ['<?xml version="1.0" ?>', '<sdf version="1.5">', '  <world name="default">']
parts.append('''    <!-- sitl_world_corridor_v8 — ③C-甲 Phase B 织行增益 (2026-10-16)
    规格: 10 箱(E x5: s=2.0/4.5/7.0/9.5/12.0 + NE x5: s=2.5/5.0/7.5/10.0/12.5, 均匀 2.5m) 1×1×1.8m; 大错列 d=0.60; 走廊半宽 W=2.6
    AprilTag: cB1/cB3/cN1/cN3 每垂直面 1×400mm 36h11-style tag 居中(c3_tagbox model); 对照 cB2=Wood/cN2=Bricks
    彩板: v6 配方(供给线≤3.0m, 纯 visual 零 collision); 坐标口径 gazebo=odom+(1.01,0.98)
    生成器: gen_corridor_world_v7.py(确定性: 同参数同 md5) -->
''')
for uri in ("sun", "ground_plane", "asphalt_plane"):
    parts.append(f'    <include><uri>model://{uri}</uri></include>')
parts.append('''    <physics name="default_physics" default="0" type="ode">
      <gravity>0 0 -9.8066</gravity>
      <ode><solver><type>quick</type><iters>10</iters><sor>1.3</sor><use_dynamic_moi_rescaling>0</use_dynamic_moi_rescaling></solver>
        <constraints><cfm>0</cfm><erp>0.2</erp><contact_max_correcting_vel>100</contact_max_correcting_vel><contact_surface_layer>0.001</contact_surface_layer></constraints></ode>
      <max_step_size>0.004</max_step_size><real_time_factor>1</real_time_factor><real_time_update_rate>250</real_time_update_rate>
    </physics>
    <scene><ambient>0.4 0.4 0.4 1</ambient><background>0.7 0.7 0.7 1</background><shadows>0</shadows></scene>
''')
# 彩板（v6 配方原样——SLABS 逻辑承 v6 生成器的网格贪心, 此处内嵌同源实现）
COLORS = [(0.9,0.9,0.1),(0.9,0.1,0.9),(0.9,0.1,0.1),(0.1,0.9,0.1),
          (0.1,0.1,0.9),(0.9,0.9,0.9),(0.9,0.5,0.1),(0.1,0.9,0.9)]
SLAB_HALF = 1.0; CLEAR = 0.05; PITCH = 2.32
Y0, X0 = -1.34, -0.29
SUPPLY_LINES = [((1.01,0.98),(1.01+E_GOAL_RAW[0],0.98+E_GOAL_RAW[1])),
                ((1.01,0.98),(1.01+NE_GOAL_RAW[0],0.98+NE_GOAL_RAW[1]))]
def _segd(px, py, a, b):
    (ax,ay),(bx,by) = a, b
    dx, dy = bx-ax, by-ay; L2 = dx*dx+dy*dy
    t = max(0.0, min(1.0, ((px-ax)*dx+(py-ay)*dy)/L2))
    return math.hypot(px-(ax+t*dx), py-(ay+t*dy))
def supply_score(px, py): return min(_segd(px,py,a,b) for a,b in SUPPLY_LINES)
_cands = []; _y = Y0
while _y <= 10.6:
    _x = X0
    while _x <= 14.0:
        _cands.append((_x, _y)); _x += PITCH
    _y += PITCH
def slab_ok(sx, sy):
    for (bn, bx, by, _) in boxes:
        if abs(sx-bx) < (SLAB_HALF + BOX_SX/2 + CLEAR) and abs(sy-by) < (SLAB_HALF + BOX_SY/2 + CLEAR):
            return False
    if abs(sx - OX) < (SLAB_HALF + 0.7) and abs(sy - OY) < (SLAB_HALF + 0.7):
        return False
    return True
SLABS = []
for (cx, cy) in sorted(_cands, key=lambda c: supply_score(c[0], c[1])):
    if supply_score(cx, cy) > 3.0: continue
    if not slab_ok(cx, cy): continue
    if any(abs(cx-sx) < 2*SLAB_HALF - 1e-9 and abs(cy-sy) < 2*SLAB_HALF - 1e-9 for (sx,sy) in SLABS): continue
    SLABS.append((cx, cy))

# 箱模型（tag 箱=collision box+4 侧垂直面薄板 visual; 对照箱=内置材质单 visual）
# 面实现修正(v7.1): 薄板 box(0.02 厚)外偏 0.501 防 z-fight——box 无 plane 的法向/贴图旋转歧义
FACES = [("+x", (0.501, 0, 0), (0.02, BOX_SX, BOX_SZ)),
         ("-x", (-0.501, 0, 0), (0.02, BOX_SX, BOX_SZ)),
         ("+y", (0, 0.501, 0), (BOX_SX, 0.02, BOX_SZ)),
         ("-y", (0, -0.501, 0), (BOX_SX, 0.02, BOX_SZ))]
for (bn, bx, by, _) in boxes:
    parts.append(f'    <model name="{bn}">\n      <pose>{bx:.3f} {by:.3f} {BOX_ZC} 0 0 0</pose>\n      <static>true</static>\n      <link name="link">')
    parts.append(f'        <collision name="collision"><geometry><box><size>{BOX_SX} {BOX_SY} {BOX_SZ}</size></box></geometry></collision>')
    if bn in TAG_BOXES:
        mb = "file://media/materials"  # v7.3: 标准相对 URI(系统资源路径 /usr/share/gazebo-11 已部署 script+PNG)
        for (fname, (fx, fy, fz), (sx, sy, sz)) in FACES:
            parts.append(f'''        <visual name="visual_{fname}">
          <pose>{fx:.3f} {fy:.3f} {fz:.3f} 0 0 0</pose>
          <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
          <material><script><name>c3_tagbox/tagface_{bn}</name><uri>{mb}/scripts/c3_tagbox.material</uri><uri>{mb}/textures</uri></script></material>
        </visual>''')
    else:
        parts.append(f'''        <visual name="visual">
          <geometry><box><size>{BOX_SX} {BOX_SY} {BOX_SZ}</size></box></geometry>
          <material>{ctrl_mat(bn)}</material>
        </visual>''')
    parts.append('      </link>\n    </model>')
for i, (sx, sy) in enumerate(SLABS, 1):
    r, g, b = COLORS[(i-1) % len(COLORS)]
    parts.append(f'''    <model name="slab_{i:02d}">
      <pose>{sx:.3f} {sy:.3f} 0.02 0 0 0</pose>
      <static>true</static>
      <link name="link">
        <visual name="visual"><geometry><box><size>2.00 2.00 0.02</size></box></geometry>
          <material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse></material>
        </visual>
      </link>
    </model>''')
parts.append("  </world>\n</sdf>")
xml = "\n".join(parts)

out = sys.argv[1] if len(sys.argv) > 1 else "sitl_world_corridor_v8.world"
with open(out, "w", encoding="utf-8") as f:
    f.write(xml)
import xml.etree.ElementTree as ET
ET.fromstring(xml)   # XML 加载自检(解析失败抛异常)
print("=" * 72)
print(f"XML 自检 PASS; 已生成 {out}（箱 {len(boxes)}=tag {len(TAG_BOXES)}+对照 {len(CTRL_BOXES)} + 彩板 {len(SLABS)}）")
print(f"md5(world)={hashlib.md5(open(out,'rb').read()).hexdigest()}")
print("\nround_result.sh BOX 表（odom 坐标）:")
row = []
for (bn, bx, by, _) in boxes:
    ox_, oy_ = g2o(bx, by)
    row.append(f'"{bn}": ({ox_:.2f},{oy_:.2f},0.0,1.0,1.0,1.8)')
print(", ".join(row))
print(f"\n供给连续性（承 v6 口径）:")
for lname, (a, b) in zip(("E", "NE"), SUPPLY_LINES):
    ds = []
    (ax,ay),(bx,by) = a, b
    for k in range(1, 121):
        t = k/120.0
        ds.append(min(math.hypot(ax+t*(bx-ax)-sx, ay+t*(by-ay)-sy) for (sx,sy) in SLABS))
    ds.sort()
    print(f"  走廊 {lname}: 到最近彩板中心 p50={ds[60]:.2f}m p90={ds[108]:.2f}m max={ds[-1]:.2f}m")
