#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-08 用户八条整改（参数联动 / 自机排除盒 / 真刹车 / 录深度）。

原始量（改这里，派生量自动一致）：
  RES=0.15  INFL=0.15  GROUND=-0.01  CEIL_MAX=1.5  MAX_RAY=2.5  MAX_VEL=0.5  MAX_ACC=1.0
派生：
  map_size_z      = CEIL_MAX - GROUND
  eff_inflation   = ceil(INFL / RES) * RES
  depth_mindist   = eff_inflation - CAM_FWD - 0.001
  自机排除盒(相机系 AABB) = body_T_cam0 变换机体系盒
"""
import argparse
import datetime
import math
import os
import shutil
import sys

NL = chr(10)
FV = os.path.expanduser('~/sitl_realmachine/flight_v1')
LAUNCH = os.path.join(FV, 'run_planner_realmachine_map_v1.launch')
CONTRACT = os.path.join(FV, 'contract/flight_contract.yaml')
GM = os.path.expanduser('~/catkin_ws/src/planner/plan_env/src/grid_map.cpp')
FSM = os.path.expanduser('~/catkin_ws/src/planner/plan_manage/src/ego_replan_fsm.cpp')
FSMH = os.path.expanduser('~/catkin_ws/src/planner/plan_manage/include/plan_manage/ego_replan_fsm.h')
REC = os.path.expanduser('~/realflight_record_v1.sh')

RES, INFL, GROUND, CEIL_MAX, MAX_RAY, MAX_VEL, MAX_ACC = 0.15, 0.15, -0.01, 1.5, 2.5, 0.5, 1.0
CAM_FWD = 0.034
BODY_BOX = ((-0.32, 0.32), (-0.32, 0.32), (-0.16, 0.10))
R = [[-0.03059710573435037, -0.005892783524167222, 0.9995144282215331],
     [-0.9995314462665196, -0.0006596618070580096, -0.030601515822914926],
     [0.0008396696021568117, -0.9999824198197875, -0.005869838696387131]]
T = [0.033999957421591, 0.016000045354189814, 0.08359999085891315]


def derive():
    map_size_z = round(CEIL_MAX - GROUND, 2)
    eff_infl = math.ceil(INFL / RES) * RES
    mindist = round(min(eff_infl - CAM_FWD - 1e-3, 0.15), 3)
    lo, hi = [1e9] * 3, [-1e9] * 3
    for cx in BODY_BOX[0]:
        for cy in BODY_BOX[1]:
            for cz in BODY_BOX[2]:
                d = [cx - T[0], cy - T[1], cz - T[2]]
                pc = [sum(R[k][i] * d[k] for k in range(3)) for i in range(3)]
                for i in range(3):
                    lo[i] = min(lo[i], pc[i])
                    hi[i] = max(hi[i], pc[i])
    return dict(map_size_z=map_size_z, eff_infl=eff_infl, mindist=mindist,
                lo=[round(v, 3) for v in lo], hi=[round(v, 3) for v in hi])


def read(p):
    return open(p, encoding='utf-8', newline='').read()


def rep(t, old, new, tag):
    if t.count(old) != 1:
        raise AssertionError('%s: %d 次' % (tag, t.count(old)))
    return t.replace(old, new, 1)


def join(*parts):
    return NL.join(parts)


def launch_block(d):
    return join(
        '  <!-- ===== 2026-11-08 user-order items: derived params; primitives live in',
        '       ~/sitl_realmachine/flight_v1/sync_params.py (change one, all follow) =====',
        '       primitives: resolution %.2f / obstacles_inflation %.2f / ground_height %.2f / ceiling_max %.2f / max_ray_length %.1f' % (RES, INFL, GROUND, CEIL_MAX, MAX_RAY),
        '       derived: map_size_z = %.2f -> ceiling %.2f ; eff_inflation = ceil(%.2f/%.2f)*%.2f = %.2f ; depth_mindist = %.3f (blind %.3f <= inflation %.2f) -->' % (
            d['map_size_z'], GROUND + d['map_size_z'], INFL, RES, RES, d['eff_infl'],
            d['mindist'], d['mindist'] + CAM_FWD, d['eff_infl']),
        '  <param name="/drone_0_ego_planner_node/grid_map/obstacles_inflation" value="%.2f"/>' % INFL,
        '  <param name="/drone_0_ego_planner_node/grid_map/ground_height" value="%.2f"/>' % GROUND,
        '  <param name="/drone_0_ego_planner_node/grid_map/map_size_z" value="%.2f"/>' % d['map_size_z'],
        '  <param name="/drone_0_ego_planner_node/grid_map/max_ray_length" value="%.1f"/>' % MAX_RAY,
        '  <param name="/drone_0_ego_planner_node/grid_map/depth_filter_maxdist" value="5.0"/>',
        '  <param name="/drone_0_ego_planner_node/grid_map/depth_filter_mindist" value="%.3f"/>' % d['mindist'],
        '  <param name="/drone_0_ego_planner_node/grid_map/pose_type" value="1"/>',
        '  <param name="/drone_0_ego_planner_node/grid_map/local_map_margin" value="10"/>')


def edit_launch(d):
    """两遍：先滤掉旧的 ground_height/mindist 行并记录 inflation 行位置，再插派生块。
    （一遍做会把刚插入块里的行又当旧行删掉 -> 每次运行都漂移。）"""
    text_all = read(LAUNCH)
    keep = []
    infl_at = None
    for ln in text_all.split(NL):
        if '<param name="/drone_0_ego_planner_node/grid_map/obstacles_inflation"' in ln:
            if infl_at is None:          # 只认第一条，其余（历史遗留块）全部丢弃
                infl_at = len(keep)
                keep.append('@@INFL@@')
            continue
        if '<param' in ln and (
                'grid_map/ground_height"' in ln or 'grid_map/depth_filter_mindist"' in ln):
            continue                      # 旧值，由派生块统一给
        keep.append(ln)
    if infl_at is None:
        raise AssertionError('launch: inflation anchor not found')
    keep[infl_at] = launch_block(d)   # 两遍结构已保证幂等（块在过滤之后插入）
    out = []
    for ln in keep:
        st = ln.strip()
        if st.startswith('<arg name="map_size_z_"'):
            ln = '    <arg name="map_size_z_" value="%.2f"/>' % d['map_size_z']
        elif st.startswith('<arg name="max_vel"'):
            ln = '    <arg name="max_vel" value="%.1f"/>' % MAX_VEL
        elif st.startswith('<arg name="max_acc"'):
            ln = '    <arg name="max_acc" value="%.1f"/>' % MAX_ACC
        elif '地面(-0.30)' in ln:
            ln = ln.replace('地面(-0.30)', '地面(%.2f)' % GROUND)
        out.append(ln)
    return NL.join(out)


def edit_grid_map(d):
    g = read(GM)
    if 'SELF_BOX_LO_0' in g:
        return g
    consts = join(
        '',
        '// 2026-11-08 (user order #2): self-occlusion rejection box, in CAMERA frame.',
        '// Body box |x|,|y| <= 0.32, z in [-0.16, 0.10] (props/guards/legs margin) mapped by',
        '// body_T_cam0 (vins_stereo_realmachine_v0.yaml:29-36) to an AABB in the camera frame.',
        'static const double SELF_BOX_LO_0 = %.3f, SELF_BOX_HI_0 = %.3f;' % (d['lo'][0], d['hi'][0]),
        'static const double SELF_BOX_LO_1 = %.3f, SELF_BOX_HI_1 = %.3f;' % (d['lo'][1], d['hi'][1]),
        'static const double SELF_BOX_LO_2 = %.3f, SELF_BOX_HI_2 = %.3f;' % (d['lo'][2], d['hi'][2]),
        '')
    g = rep(g, 'void GridMap::projectDepthImage()' + NL + '{',
            consts + NL + 'void GridMap::projectDepthImage()' + NL + '{', 'gm/consts')
    g = rep(g, '  Eigen::Vector3d pt_cur, pt_world, pt_reproj;',
            '  Eigen::Vector3d pt_cur, pt_world, pt_reproj;' + NL +
            '  Eigen::Vector3d pc;   // camera-frame point (self-box rejection)', 'gm/pc_decl')
    anchor = join('          // project to world frame',
                  '          pt_cur(0) = (u - mp_.cx_) * depth / mp_.fx_;')
    box = join(
        '          /* 2026-11-08 (user order #2): reject the drone own body.',
        '             Near-field self points (props/guards/legs) measure 0.07~0.22 m. A single',
        '             depth_filter_mindist either leaks the 0.20~0.22 band or pushes the blind',
        '             face beyond the inflation radius. Geometric fix: drop points inside the',
        '             body AABB expressed in the camera frame (neither hit nor free). */',
        '          pc(0) = (u - mp_.cx_) * depth / mp_.fx_;',
        '          pc(1) = (v - mp_.cy_) * depth / mp_.fy_;',
        '          pc(2) = depth;',
        '          if (pc(0) > SELF_BOX_LO_0 && pc(0) < SELF_BOX_HI_0 &&',
        '              pc(1) > SELF_BOX_LO_1 && pc(1) < SELF_BOX_HI_1 &&',
        '              pc(2) > SELF_BOX_LO_2 && pc(2) < SELF_BOX_HI_2)',
        '            continue;',
        '',
        '          // project to world frame',
        '          pt_cur(0) = (u - mp_.cx_) * depth / mp_.fx_;')
    return rep(g, anchor, box, 'gm/self_box')


def edit_fsm():
    f = read(FSM)
    if 'last_brake_t_' in f:
        return f, read(FSMH)
    old = join('      if (flag_escape_emergency_) // Avoiding repeated calls',
               '      {',
               '        callEmergencyStop(odom_pos_);',
               '      }',
               '      else',
               '      {',
               '        if (enable_fail_safe_ && odom_vel_.norm() < 0.1)',
               '          changeFSMExecState(GEN_NEW_TRAJ, "FSM");',
               '      }')
    new = join('      if (flag_escape_emergency_) // Avoiding repeated calls',
               '      {',
               '        callEmergencyStop(odom_pos_);',
               '      }',
               '      else if (odom_vel_.norm() > 0.10)',
               '      {',
               '        /* 2026-11-08 (user order #3): real brake. It used to brake once on entry and',
               '           then just hold. Now: keep issuing brake trajectories at <=5 Hz while any',
               '           speed remains; only below 0.1 m/s does the recovery criterion apply. */',
               '        if ((ros::Time::now() - last_brake_t_).toSec() > 0.2)',
               '        {',
               '          last_brake_t_ = ros::Time::now();',
               '          callEmergencyStop(odom_pos_);',
               '        }',
               '      }',
               '      else',
               '      {',
               '        if (enable_fail_safe_ && odom_vel_.norm() < 0.1)',
               '          changeFSMExecState(GEN_NEW_TRAJ, "FSM");',
               '      }')
    f = rep(f, old, new, 'fsm/brake')
    fh = read(FSMH)
    fh = rep(fh, '    ros::Time fail_safe_healthy_since_;',
             '    ros::Time fail_safe_healthy_since_;' + NL +
             '    ros::Time last_brake_t_;   // 2026-11-08 user order #3: brake rate limit',
             'fsm_h/member')
    return f, fh


def edit_record():
    rc = read(REC)
    if '/camera/depth/image_rect_raw' in rc:
        return rc
    return rep(rc, '    /position_cmd',
               join('    # 2026-11-08 (user order #8) depth into the bag: 16UC1 640x480@30 ~18 MB/s',
                    '    # (2 min ~ 2.2 GB; --min-space 10G still guards)',
                    '    /camera/depth/image_rect_raw',
                    '    /camera/depth/camera_info',
                    '    /position_cmd'), 'rec/depth')


def edit_contract(d):
    C = read(CONTRACT)
    import re

    def setk(key, val):
        nonlocal C
        pat = re.compile(r'^(  %s:)[^\n#]*' % re.escape(key), re.M)
        n = len(pat.findall(C))
        if n != 1:
            raise AssertionError('contract %s: %d matches' % (key, n))
        C = pat.sub(lambda m: m.group(1) + ' ' + val + '   ', C, count=1)   # 保留注释前空格

    for k, v in (('max_vel', '%.1f' % MAX_VEL), ('max_acc', '%.1f' % MAX_ACC),
                 ('ground_height', '%.2f' % GROUND), ('map_size_z', '%.2f' % d['map_size_z']),
                 ('depth_mindist', '%.3f' % d['mindist']), ('ceiling_max', '%.1f' % CEIL_MAX)):
        setk(k, v)
    if 'obstacles_inflation:' not in C:
        C = C.replace('  depth_mindist:',
                      join('  resolution: %.2f' % RES,
                           '  obstacles_inflation: %.2f' % INFL,
                           '  max_ray_length: %.1f' % MAX_RAY,
                           '  local_map_margin: 10',
                           '  depth_mindist:'), 1)
    return C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    d = derive()
    print('derived: eff_inflation=%.3f  map_size_z=%.2f (ceiling %.2f)  mindist=%.3f (blind %.3f)'
          % (d['eff_infl'], d['map_size_z'], GROUND + d['map_size_z'], d['mindist'],
             d['mindist'] + CAM_FWD))
    print('self box (camera frame): lo=%s hi=%s' % (d['lo'], d['hi']))
    L = edit_launch(d)
    g = edit_grid_map(d)
    f, fh = edit_fsm()
    rc = edit_record()
    C = edit_contract(d)
    print('five targets generated')
    if not a.apply:
        return 0
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    for p, t in ((LAUNCH, L), (CONTRACT, C), (GM, g), (FSM, f), (FSMH, fh), (REC, rc)):
        shutil.copy2(p, p + '.bak_u8_' + ts)
        open(p, 'w', encoding='utf-8', newline=NL).write(t)
    print('written .bak_u8_%s' % ts)
    return 0


if __name__ == '__main__':
    sys.exit(main())
