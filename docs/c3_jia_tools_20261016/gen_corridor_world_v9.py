#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_corridor_world_v9.py — ③C-甲合流册 §二：实验室尺度场景生成器（2026-10-16，预注册跑前锁定版）
v9 规格（v9_design_prereg.md 锁定）:
  6×6m 带边界墙(高2m/厚0.1m)/对角单 lane spawn room(0.8,0.8)→goal room(5.0,5.0)=odom(4.2,4.2) z=0.8;
  两箱 600×600×1500mm 错列 d=0.18(s1=2.2 s2=4.7 交替 +/−, 沿航线中心口径)/tag 400mm 每面 1 张;
  无对照箱(H-dJ2 对照链=v7.0/v7.3/v8 语料); 地板 1×1m 8 色棋盘(visual-only)/墙 0.5m 棋盘纹理(collision ON)。
坐标: gazebo = room + (0.21,0.18); odom = gazebo − (1.01,0.98)。
  依据: iris 出生硬编码 sitl_run.sh:130 (-x 1.01 -y 0.98) 实测核验 → 房间原点使 spawn(room0.8,0.8)=gazebo(1.01,0.98)。
硬门(跑前锁, 任一 FAIL → exit 1 不产出):
  ①封线 d<0.599(轴对齐口径; 对角支撑 0.723 注记) ②沿航线箱距≥2.5
  ③tag 贴窗(1.2m)角点供给≥75 ④墙净距≥1.0(包络=箱膨胀∪织行包络 lat±0.903; 端点悬停域除外, 预注册口径)
  ⑤交错织行段≥2(signs 交替) ⑥端点余量 进场≥2/出场≥1(中心口径)
S 形门推导值(生成时数值重算并打印=锁定源): 交替最短避障路径 ratio 下取(预注册 1.07 复核位)。
确定性: 同参数同输出(world XML 确定性; PNG PIL optimize 确定性) → 同参数同 md5。
参数化 env(v9.x 迭代槽, 默认=锁定值): V9_D / V9_S1 / V9_GAP / V9_SIGNS。"""
import math, os, sys, hashlib, random, heapq

# ---------- 锁定参数 ----------
ROX, ROY = 0.21, 0.18                 # 房间原点(gazebo)
SP_R = (0.8, 0.8); GOAL_R = (5.0, 5.0); GOAL_Z = 0.8
D      = float(os.environ.get("V9_D", "0.18"))
S1     = float(os.environ.get("V9_S1", "2.2"))
GAP    = float(os.environ.get("V9_GAP", "2.5"))
SIGNS  = [int(x) for x in os.environ.get("V9_SIGNS", "+1,-1").split(",")]
ROOM, WALL_H, WALL_T = 6.0, 2.0, 0.1
BOX_SX = BOX_SY = 0.6; BOX_SZ = 1.5; BOX_ZC = 0.75
INFL = 0.299; HALF = BOX_SX / 2.0; HALF_INFL = HALF + INFL      # 0.599
DIAG_SUP = HALF * math.sqrt(2) + INFL                            # 0.723 (45° 对角支撑, 勘误注记)
TAG_SIZE_MM = 400; TAG_GRID = 12; TAG_SEED = 3611
CAM_FX, CAM_W = 467.7, 640
OX, OY = 1.01, 0.98                  # odom→gazebo 偏移(承全战役)
g = lambda x, y: (x + ROX, y + ROY)                       # room→gazebo
o = lambda x, y: (x - OX, y - OY)                          # gazebo→odom

L = math.hypot(GOAL_R[0]-SP_R[0], GOAL_R[1]-SP_R[1])
U = ((GOAL_R[0]-SP_R[0])/L, (GOAL_R[1]-SP_R[1])/L); N = (-U[1], U[0])
S2 = S1 + GAP
BOXES_R = {"cL1": (SP_R[0]+S1*U[0]+SIGNS[0]*D*N[0], SP_R[1]+S1*U[1]+SIGNS[0]*D*N[1]),
           "cL2": (SP_R[0]+S2*U[0]+SIGNS[1]*D*N[0], SP_R[1]+S2*U[1]+SIGNS[1]*D*N[1])}
def lane_of(p):  # room 点 → (s, lat)
    rx, ry = p[0]-SP_R[0], p[1]-SP_R[1]
    return rx*U[0]+ry*U[1], rx*N[0]+ry*N[1]
print("=" * 76)
print(f"v9 实验室尺度: L={L:.4f}m  spawn room{SP_R}=gazebo{g(*SP_R)}=odom(0,0)  goal room{GOAL_R}=gazebo{g(*GOAL_R)}=odom(4.2,4.2) z={GOAL_Z}")

# ---------- 硬门① 封线 ----------
ok1 = all(abs(D*sg) < HALF_INFL for sg in (1, -1))
print(f"硬门① 封线: d={D} < 半宽+膨胀={HALF_INFL:.3f} [{'PASS' if ok1 else 'FAIL'}]"
      f"  (对角支撑勘误注记: 45° 口径 {DIAG_SUP:.3f} ⇒ 物理最小幅度 A_geo={DIAG_SUP-D:.3f}; 门值基准 A={HALF_INFL-D:.3f})")
# ---------- 硬门② 箱距 ----------
ok2 = GAP >= 2.5
print(f"硬门② 沿航线箱距: GAP={GAP:.2f} (中心口径)  门≥2.5  [{'PASS' if ok2 else 'FAIL'}]")
# ---------- 硬门③ tag 供给 ----------
fov_w = 2 * 1.2 * math.tan(math.atan(CAM_W / (2 * CAM_FX)))
quota = 150; inner = TAG_GRID - 4
def tag_corners(z):
    px = CAM_FX * (TAG_SIZE_MM / 1000.0) / z
    supp = max(0.5, min(1.0, px / 260.0))
    return (4 + 0.8 * (inner - 1) ** 2) * supp, px
c12, px12 = tag_corners(1.2)
floor_sup, wall_sup = 40, 30      # v6 彩板带同保守基 / 墙棋盘带保守值(预注册 §5)
total12 = c12 + floor_sup + wall_sup
ok3 = total12 >= 0.5 * quota
print(f"硬门③ tag 供给(1.2m 贴窗): 视野宽={fov_w:.3f}m tag={px12:.0f}px 角点={c12:.1f} +地板棋盘{floor_sup}+墙棋盘{wall_sup}"
      f" = {total12:.1f}  门≥{0.5*quota:.0f}  [{'PASS' if ok3 else 'FAIL'}]  (实测面=试录 corners≥75∧配对p50≥0.10)")
# ---------- 硬门④ 墙净距 ----------
def wall_clear(x_r, y_r, pad):  # room 点带膨胀 pad 到最近墙内表面净距
    return min(x_r - pad, y_r - pad, ROOM - x_r - pad, ROOM - y_r - pad)
print(f"硬门④ 墙净距(包络→墙内表面, 门≥1.0; 端点悬停域除外=预注册口径):")
ok4 = True; worst = 9e9
for bn, (bx, by) in BOXES_R.items():
    c = wall_clear(bx, by, HALF_INFL)
    ok4 &= c >= 1.0; worst = min(worst, c)
    print(f"  {bn} 膨胀区: 净距={c:.3f}  [{'PASS' if c>=1.0 else 'FAIL'}]")
    s_c, lat_c = lane_of((bx, by))
    for sgn in (1, -1):   # 织行包络极值点(abeam 侧向 ±(DIAG_SUP+D 侧) 物理包络 0.903)
        ex = SP_R[0] + s_c*U[0] + sgn*(DIAG_SUP+D)*N[0]
        ey = SP_R[1] + s_c*U[1] + sgn*(DIAG_SUP+D)*N[1]
        c2 = wall_clear(ex, ey, 0.0)
        ok4 &= c2 >= 1.0; worst = min(worst, c2)
        print(f"  {bn} 织行包络极值({sgn:+d}侧 room({ex:.3f},{ey:.3f})): 净距={c2:.3f}  [{'PASS' if c2>=1.0 else 'FAIL'}]")
print(f"  最小净距={worst:.3f}  [{'PASS' if ok4 else 'FAIL'}]")
# ---------- 硬门⑤ 织行段 ----------
weave = sum(1 for a, b in zip(SIGNS, SIGNS[1:]) if a * b < 0)
ok5 = weave >= 2 - 1  # 2 箱 → 交错段数 = len(SIGNS)-1 ≥ 1 ⇒ ≥2 织行窗(门=交替)
ok5 = (len(SIGNS) >= 2) and all(a * b < 0 for a, b in zip(SIGNS, SIGNS[1:]))
print(f"硬门⑤ 交错织行: signs={SIGNS} 交替段={weave}  [{'PASS' if ok5 else 'FAIL'}]")
# ---------- 硬门⑥ 端点余量 ----------
ok6 = (S1 >= 2.0) and (L - S2 >= 1.0)
print(f"硬门⑥ 端点余量: 进场={S1:.2f}≥2.0  出场={L-S2:.2f}≥1.0 (中心口径)  [{'PASS' if ok6 else 'FAIL'}]")
if not (ok1 and ok2 and ok3 and ok4 and ok5 and ok6):
    print("硬门 FAIL → 不产出 world"); sys.exit(1)

# ---------- S 形门推导: 数值路径积分(72 边形膨胀区+切线可见图+侧向约束带) ----------
def _poly(bx, by, nudge=0.0, Nseg=72):
    pts = []
    for k in range(Nseg):
        th = 2 * math.pi * k / Nseg
        cx, cy = math.cos(th), math.sin(th)
        px = HALF * (1 if cx > 0 else -1 if cx < 0 else 0); py = HALF * (1 if cy > 0 else -1 if cy < 0 else 0)
        pts.append((bx + px + (INFL + nudge) * cx, by + py + (INFL + nudge) * cy))
    return pts
def _pip(pt, P):
    x, y = pt; c = False
    for i in range(len(P)):
        x1, y1 = P[i]; x2, y2 = P[(i + 1) % len(P)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
def _seg_inter(a, b, c, dpt):
    def cr(o, a2, b2): return (a2[0]-o[0])*(b2[1]-o[1])-(a2[1]-o[1])*(b2[0]-o[0])
    d1, d2, d3, d4 = cr(c,dpt,a), cr(c,dpt,b), cr(a,b,c), cr(a,b,dpt)
    return ((d1>0)!=(d2>0)) and ((d3>0)!=(d4>0))
B1r, B2r = BOXES_R["cL1"], BOXES_R["cL2"]
P1, P2 = _poly(*B1r), _poly(*B2r)
def _rect_band(slo, shi, latlo, lathi, steps=8):
    pts = [(SP_R[0]+slo*U[0]+latlo*N[0], SP_R[1]+slo*U[1]+latlo*N[1])]
    pts += [(SP_R[0]+(slo+(shi-slo)*t/steps)*U[0]+latlo*N[0], SP_R[1]+(slo+(shi-slo)*t/steps)*U[1]+latlo*N[1]) for t in range(1, steps+1)]
    pts += [(SP_R[0]+shi*U[0]+(lathi-(lathi-latlo)*t/steps)*N[0], SP_R[1]+shi*U[1]+(lathi-(lathi-latlo)*t/steps)*N[1]) for t in range(1, steps+1)]
    return pts
# sense A: cL1 从 -n 避(堵 +lat), cL2 从 +n 避(堵 -lat) —— 交替向
bands = [_rect_band(S1-0.75, S1+0.75, 0.02, 1.6), _rect_band(S2-0.75, S2+0.75, -1.6, -0.02)]
obst = [P1, P2] + bands
def _seg_free(a, b):
    for P in obst:
        if _pip(a, P) or _pip(b, P): return False
        for i in range(len(P)):
            if _seg_inter(a, b, P[i], P[(i+1) % len(P)]): return False
    return True
nodes = [SP_R, GOAL_R] + _poly(*B1r, 1e-6) + _poly(*B2r, 1e-6)
adj = [[] for _ in nodes]
for i in range(len(nodes)):
    for j in range(i+1, len(nodes)):
        if _seg_free(nodes[i], nodes[j]):
            w = math.hypot(nodes[i][0]-nodes[j][0], nodes[i][1]-nodes[j][1])
            adj[i].append((j, w)); adj[j].append((i, w))
INF = 9e18; dist = [INF]*len(nodes); dist[0] = 0.0; pq = [(0.0, 0)]
while pq:
    dd, i = heapq.heappop(pq)
    if dd > dist[i]: continue
    for j, w in adj[i]:
        if dist[j] > dd + w: dist[j] = dd + w; heapq.heappush(pq, (dist[j], j))
L_alt = dist[1]; ratio_alt = L_alt / L
ratio_gate = math.floor(ratio_alt * 100) / 100.0
# 无约束最短(单侧 C 形上界, 排除证明)
obst_nc = [P1, P2]
def _seg_free_nc(a, b):
    for P in obst_nc:
        if _pip(a, P) or _pip(b, P): return False
        for i in range(len(P)):
            if _seg_inter(a, b, P[i], P[(i+1) % len(P)]): return False
    return True
nodes_nc = nodes
adj_nc = [[] for _ in nodes_nc]
for i in range(len(nodes_nc)):
    for j in range(i+1, len(nodes_nc)):
        if _seg_free_nc(nodes_nc[i], nodes_nc[j]):
            w = math.hypot(nodes_nc[i][0]-nodes_nc[j][0], nodes_nc[i][1]-nodes_nc[j][1])
            adj_nc[i].append((j, w)); adj_nc[j].append((i, w))
dist_nc = [INF]*len(nodes_nc); dist_nc[0] = 0.0; pq = [(0.0, 0)]
while pq:
    dd, i = heapq.heappop(pq)
    if dd > dist_nc[i]: continue
    for j, w in adj_nc[i]:
        if dist_nc[j] > dd + w: dist_nc[j] = dd + w; heapq.heappush(pq, (dist_nc[j], j))
ratio_c = dist_nc[1] / L
print("-" * 76)
print(f"S 形门推导值(数值路径积分, 生成时锁定源): 交替最短={L_alt:.4f}m ratio={ratio_alt:.4f} → 门 ratio≥{ratio_gate:.2f}"
      f" | 无约束最短(C 形上界)={dist_nc[1]:.4f}m ratio={ratio_c:.4f} < 门={'YES(排除)' if ratio_c < ratio_gate else 'NO!!'}")
print(f"  maxlat 门={HALF_INFL-D-0.10:.2f}(A-0.10)  ndetour 门=2(段阈 THR={HALF_INFL-D-0.10:.2f})  双侧交替门=相邻段符号异号")
# ---------- 表1 箱位 ----------
print("=" * 76)
print(f"表1 箱位表(2 箱 600×600×1500; gazebo=room+({ROX},{ROY}); odom=gazebo-({OX},{OY}))")
for bn, (bx, by) in BOXES_R.items():
    gx_, gy_ = g(bx, by); ox_, oy_ = o(gx_, gy_)
    s_c, lat_c = lane_of((bx, by))
    print(f"  {bn}: room({bx:.4f},{by:.4f})  gazebo({gx_:.4f},{gy_:.4f})  odom({ox_:.4f},{oy_:.4f})  s={s_c:.3f} lat={lat_c:+.3f}")
# ---------- 表2 航线-箱相交 ----------
print("表2 航线-箱相交(门=本走廊箱挡道: 航线-箱心距<膨胀半宽)")
t2 = True
for bn, (bx, by) in BOXES_R.items():
    dlat = abs(lane_of((bx, by))[1])
    ok = dlat < HALF_INFL
    t2 &= ok
    print(f"  {bn}: 航线-箱心横向距 {dlat:.3f} < {HALF_INFL:.3f}  挡道 [{'OK' if ok else 'VIOLATION!!'}]")
if not t2: print("表2 VIOLATION → 中止"); sys.exit(1)
# ---------- 表3 tag 覆盖 ----------
print(f"表3 tag 材质覆盖: cL1/cL2 ×4 垂直面 = 8 面; 每面 1×{TAG_SIZE_MM}mm 居中; 无对照箱(H-dJ2 对照链=历史语料)")

# ---------- 资产生成(确定性) ----------
from PIL import Image, ImageDraw
PALETTE = [(0.9,0.9,0.1),(0.9,0.1,0.9),(0.9,0.1,0.1),(0.1,0.9,0.1),
           (0.1,0.1,0.9),(0.9,0.9,0.9),(0.9,0.5,0.1),(0.1,0.9,0.9)]
PAL255 = [(int(r*255), int(g2*255), int(b*255)) for (r, g2, b) in PALETTE]
def gen_tag_png(seed):
    Wc, Hc, ts = 360, 900, 240          # 画布=0.6×1.5m 面; tag 240px=400mm
    rnd = random.Random(seed)
    x0, y0 = (Wc - ts)//2, (Hc - ts)//2
    cell = ts // TAG_GRID; inner = TAG_GRID - 4
    im = Image.new("RGB", (Wc, Hc), (154, 154, 154)); dr = ImageDraw.Draw(im)
    dr.rectangle([x0, y0, x0+ts, y0+ts], fill=(255, 255, 255))
    dr.rectangle([x0, y0, x0+ts, y0+ts], outline=(0, 0, 0), width=2*cell)
    ix0 = x0 + 3*cell
    for i in range(inner):
        for j in range(inner):
            if rnd.random() < 0.5:
                dr.rectangle([ix0+i*cell, y0+3*cell+j*cell, ix0+(i+1)*cell-1, y0+3*cell+(j+1)*cell-1], fill=(0,0,0))
    return im
def gen_wall_png(wall_len_m):
    Wp, Hp = int(wall_len_m*200), 400    # 200px/m; 高 2m
    im = Image.new("RGB", (Wp, Hp)); dr = ImageDraw.Draw(im)
    cs = 100                              # 0.5m 格
    for i in range(Wp//cs):
        for j in range(Hp//cs):
            dr.rectangle([i*cs, j*cs, (i+1)*cs-1, (j+1)*cs-1], fill=PAL255[(i*7+j*13) % 8])
    return im
MODEL_DIR = os.path.expanduser("~/.gazebo/models/c3_lab")
os.makedirs(os.path.join(MODEL_DIR, "materials/scripts"), exist_ok=True)
os.makedirs(os.path.join(MODEL_DIR, "materials/textures"), exist_ok=True)
mats = []
for k, bn in enumerate(sorted(BOXES_R)):
    png = os.path.join(MODEL_DIR, "materials/textures", f"v9tag_{bn}.png")
    gen_tag_png(TAG_SEED + k).save(png, optimize=True)
    mats.append(f"material c3_lab/v9tag_{bn}\n{{\n  technique\n  {{\n    pass\n    {{\n      texture_unit\n      {{\n        texture v9tag_{bn}.png\n      }}\n    }}\n  }}\n}}\n")
    print(f"  tag PNG: {png} md5={hashlib.md5(open(png,'rb').read()).hexdigest()[:8]}")
wall_pngs = []
for wi, wlen in enumerate((ROOM + 2*WALL_T, ROOM), 1):   # 两长墙(X 向)/两短墙(Y 向) —— 视觉等长按 6m 贴
    png = os.path.join(MODEL_DIR, "materials/textures", f"v9wall_{wi}.png")
    gen_wall_png(6.0).save(png, optimize=True)
    wall_pngs.append(png)
    mats.append(f"material c3_lab/v9wall_{wi}\n{{\n  technique\n  {{\n    pass\n    {{\n      texture_unit\n      {{\n        texture v9wall_{wi}.png\n      }}\n    }}\n  }}\n}}\n")
    print(f"  wall PNG: {png} md5={hashlib.md5(open(png,'rb').read()).hexdigest()[:8]}")
with open(os.path.join(MODEL_DIR, "materials/scripts/c3_lab.material"), "w") as f:
    f.write("\n".join(mats))
with open(os.path.join(MODEL_DIR, "model.config"), "w") as f:
    f.write("<?xml version='1.0'?><model><name>c3_lab</name><version>1.0</version>"
            "<sdf version='1.5'>model.sdf</sdf><description>C3 v9 lab materials</description></model>\n")
with open(os.path.join(MODEL_DIR, "model.sdf"), "w") as f:
    f.write("<?xml version='1.0'?><sdf version='1.5'><model name='c3_lab'><static>true</static>"
            "<link name='link'></link></model></sdf>\n")

# ---------- world XML ----------
parts = ['<?xml version="1.0" ?>', '<sdf version="1.5">', '  <world name="default">']
parts.append(f'''    <!-- sitl_world_corridor_v9 — ③C-甲合流 §二 实验室尺度 (2026-10-16, 预注册锁定)
    6×6m 房(墙高2m厚0.1m) / lane spawn room(0.8,0.8)→goal room(5.0,5.0)=odom(4.2,4.2) z=0.8 / L={L:.4f}m
    2 箱 600×600×1500 错列 d={D} s={S1}/{S2:.1f} signs={SIGNS} / tag 400mm 每面1张 / 无对照箱
    地板 1×1m 8色棋盘(visual) / 墙 0.5m 棋盘纹理(collision) / 坐标 gazebo=room+({ROX},{ROY})
    S形门(推导): ratio≥{ratio_gate:.2f} maxlat≥{HALF_INFL-D-0.10:.2f} ndetour≥2(THR同maxlat门) 双侧交替
    生成器: gen_corridor_world_v9.py(确定性: 同参数同 md5) -->
''')
parts.append('    <include><uri>model://sun</uri></include>\n    <include><uri>model://ground_plane</uri></include>')
parts.append('''    <physics name="default_physics" default="0" type="ode">
      <gravity>0 0 -9.8066</gravity>
      <ode><solver><type>quick</type><iters>10</iters><sor>1.3</sor><use_dynamic_moi_rescaling>0</use_dynamic_moi_rescaling></solver>
        <constraints><cfm>0</cfm><erp>0.2</erp><contact_max_correcting_vel>100</contact_max_correcting_vel><contact_surface_layer>0.001</contact_surface_layer></constraints></ode>
      <max_step_size>0.004</max_step_size><real_time_factor>1</real_time_factor><real_time_update_rate>250</real_time_update_rate>
    </physics>
    <scene><ambient>0.4 0.4 0.4 1</ambient><background>0.7 0.7 0.7 1</background><shadows>0</shadows></scene>
''')
MB = "file://media/materials"     # v7.3 验证链: 系统资源路径 /usr/share/gazebo-11
# 四面墙(room 边界; collision ON)
WALLS = [("wall_S", 3.0, -WALL_T/2, ROOM + 2*WALL_T, WALL_T),
         ("wall_N", 3.0, ROOM + WALL_T/2, ROOM + 2*WALL_T, WALL_T),
         ("wall_W", -WALL_T/2, 3.0, WALL_T, ROOM),
         ("wall_E", ROOM + WALL_T/2, 3.0, WALL_T, ROOM)]
for wi, (wn, cx, cy, sx, sy) in enumerate(WALLS, 1):
    gx_, gy_ = g(cx, cy)
    parts.append(f'''    <model name="{wn}">
      <pose>{gx_:.3f} {gy_:.3f} {WALL_H/2:.1f} 0 0 0</pose>
      <static>true</static>
      <link name="link">
        <collision name="collision"><geometry><box><size>{sx:.2f} {sy:.2f} {WALL_H:.1f}</size></box></geometry></collision>
        <visual name="visual"><geometry><box><size>{sx:.2f} {sy:.2f} {WALL_H:.1f}</size></box></geometry>
          <material><script><name>c3_lab/v9wall_{1 if wi <= 2 else 2}</name><uri>{MB}/scripts/c3_lab.material</uri><uri>{MB}/textures</uri></script></material>
        </visual>
      </link>
    </model>''')
# 地板棋盘(1×1m 8 色循环, visual-only, 减箱足迹格)
FACES = [("+x", (HALF+0.001, 0, 0), (0.02, BOX_SY, BOX_SZ)),
         ("-x", (-(HALF+0.001), 0, 0), (0.02, BOX_SY, BOX_SZ)),
         ("+y", (0, HALF+0.001, 0), (BOX_SX, 0.02, BOX_SZ)),
         ("-y", (0, -(HALF+0.001), 0), (BOX_SX, 0.02, BOX_SZ))]
n_cells = 0
for i in range(6):
    for j in range(6):
        cx_r, cy_r = 0.5 + i, 0.5 + j
        if any(abs(cx_r-bx) < (0.5 + HALF + 0.05) and abs(cy_r-by) < (0.5 + HALF + 0.05) for (bx, by) in BOXES_R.values()):
            continue
        gx_, gy_ = g(cx_r, cy_r)
        r, g2, b = PALETTE[(i*5 + j*3) % 8]
        parts.append(f'''    <model name="floor_{i}{j}">
      <pose>{gx_:.3f} {gy_:.3f} 0.011 0 0 0</pose>
      <static>true</static>
      <link name="link">
        <visual name="visual"><geometry><box><size>1.00 1.00 0.02</size></box></geometry>
          <material><ambient>{r} {g2} {b} 1</ambient><diffuse>{r} {g2} {b} 1</diffuse></material>
        </visual>
      </link>
    </model>''')
        n_cells += 1
# 两 tag 箱(collision + 4 面薄板 visual, v7.1 修正族)
for bn, (bx, by) in BOXES_R.items():
    gx_, gy_ = g(bx, by)
    parts.append(f'    <model name="{bn}">\n      <pose>{gx_:.4f} {gy_:.4f} {BOX_ZC} 0 0 0</pose>\n      <static>true</static>\n      <link name="link">')
    parts.append(f'        <collision name="collision"><geometry><box><size>{BOX_SX} {BOX_SY} {BOX_SZ}</size></box></geometry></collision>')
    for (fname, (fx, fy, fz), (sx, sy, sz)) in FACES:
        parts.append(f'''        <visual name="visual_{fname}">
          <pose>{fx:.3f} {fy:.3f} {0:.3f} 0 0 0</pose>
          <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
          <material><script><name>c3_lab/v9tag_{bn}</name><uri>{MB}/scripts/c3_lab.material</uri><uri>{MB}/textures</uri></script></material>
        </visual>''')
    parts.append('      </link>\n    </model>')
parts.append("  </world>\n</sdf>")
xml = "\n".join(parts)
out = sys.argv[1] if len(sys.argv) > 1 else "sitl_world_corridor_v9.world"
with open(out, "w", encoding="utf-8") as f:
    f.write(xml)
import xml.etree.ElementTree as ET
ET.fromstring(xml)
print("=" * 76)
print(f"XML 自检 PASS; 已生成 {out} (墙4+箱2+地板格{n_cells}; tag 面8)")
print(f"md5(world)={hashlib.md5(open(out,'rb').read()).hexdigest()}")
print("\n部署清单(四处): repo worlds/ + 战役目录 + PX4 worlds/ + ~/.gazebo/models/c3_lab → sudo cp 至 /usr/share/gazebo-11/media/materials/")
print("round_result/audit 表(odom): cL1=(%.4f,%.4f,0,0.6,0.6,1.5) cL2=(%.4f,%.4f,0,0.6,0.6,1.5)" % (
    o(*g(*BOXES_R["cL1"]))[0], o(*g(*BOXES_R["cL1"]))[1], o(*g(*BOXES_R["cL2"]))[0], o(*g(*BOXES_R["cL2"]))[1]))
print(f"audit LANES.LAB=(gazebo) ({g(*SP_R)[0]:.3f},{g(*SP_R)[1]:.3f})→({g(*GOAL_R)[0]:.3f},{g(*GOAL_R)[1]:.3f})  L_straight={L:.4f}")
