#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机上参数的**唯一总开关**（2026-11-08 v2）。

改一处，联动写全：
  · 规划器 launch（派生参数块 / goal_topic / 深度内参 / max_vel / max_acc / map_size_z）
  · 契约 flight_contract.yaml（params / runtime.rc / runtime.battery / runtime.depth_intrinsics / goal 话题）
  · grid_map.cpp 的自机排除盒（**外参现读 VINS 的 yaml**，不再硬拷一份）
  · px4ctrl 的 ctrl_param_fpv.yaml（takeoff_height / low_voltage）
  · 录包话题清单 ~/sitl_realmachine/flight_v1/generated/record_topics.txt
  · ego_replan_fsm 的刹车计时成员（一次性补齐）

用法：python3 sync_params.py            # 只打印将要写入的值
      python3 sync_params.py --apply   # 落盘（幂等，两次运行哈希一致）
"""
import argparse
import datetime
import math
import os
import re
import shutil
import sys

NL = chr(10)
FV = os.path.expanduser('~/sitl_realmachine/flight_v1')
LAUNCH = os.path.join(FV, 'run_planner_realmachine_map_v1.launch')
CONTRACT = os.path.join(FV, 'contract/flight_contract.yaml')
# 2026-11-11：备份不再落 git 工作树（此前把这条覆盖丢过一次）
SYNC_BAK = os.path.expanduser("~/patches_archive/sync_bak")
GEN_TOPICS = os.path.join(FV, 'generated/record_topics.txt')
GM = os.path.expanduser('~/catkin_ws/src/planner/plan_env/src/grid_map.cpp')
FSM = os.path.expanduser('~/catkin_ws/src/planner/plan_manage/src/ego_replan_fsm.cpp')
FSMH = os.path.expanduser('~/catkin_ws/src/planner/plan_manage/include/plan_manage/ego_replan_fsm.h')
PX4YAML = os.path.expanduser('~/catkin_ws/src/px4ctrl/config/ctrl_param_fpv.yaml')
VINSYAML = os.path.expanduser('~/sitl_realmachine/03_realmachine_config/vins_stereo_realmachine_v0.yaml')

# ============================== 原始量（要改就改这里） ==============================
P = {
    # 任务层
    'takeoff_height': 0.7,
    'goal_radius': 3.5,
    'no_replan_m': 0.3,           # 距目标多少米内仍允许重规划（P0-2；1.0 会造成末段开环）
    'replan_time': 0.5,           # 两次重规划最小间隔（用户令 1.0 -> 0.5）
    'hover_s': 5.0,
    'goal_topic': '/flight_v1/goal_gate',
    # 规划器/地图（派生链的根）
    'resolution': 0.15,
    'inflation': 0.299,          # 2026-11-11 用户令：上游实机值 -> 等效 ceil(0.299/0.15)*0.15 = 0.30
                                  #   （现场实测净空 0.25-0.30 m；机体直径 0.337，留 0.13 m 裕度）
    'ground_height': -0.10,      # 2026-11-08 用户令：图底压到 -0.10（地板点稳在图内）
    'ceiling_max': 1.5,
    'max_ray': 5.0,                  # 2026-11-12 用户令：回上游 5.0（实测 CPU 无压力，见下）
    'max_vel': 0.5,                 # 2026-11-12 用户令：0.4 -> 0.5（对齐上游；进近限速 1.0 m）
    'max_acc': 4.0,                 # 2026-11-12 用户令：3.0 -> 4.0（上游 6.0 的一半，倾角 22°<25°）
    'near_goal_dist': 1.0,          # 进近限速起点（>= 减速距离 v/kp；0.6 在 v=0.5 时太晚）
    'planning_horizon': 6.0,        # 2026-11-12：回上游 6.0（=1.2x 感知 5.0，>=1.5x 规则的 7.5>6 略紧但上游即此值）
    # 近场剔除下限：用户令 0.2（显式给定，不再按 eff 派生；几何自洽由 checker 把关）
    'depth_mindist': 0.2,
    'local_map_margin': 10,
    'pose_type': 1,
    # D435 对齐深度内参（规划器消费的是"对齐到彩色"的深度图）
    'depth_fx': 427.873138427734,
    'depth_fy': 427.873138427734,
    'depth_cx': 427.866149902344,
    'depth_cy': 231.891784667969,
    # RC 闸门
    'rc_channels': 8,
    'rc_centered_tol': 125,
    'rc_ch5_min': 1750,
    # 电池：min_fly=人操作卡的"才许飞"；low_voltage=px4ctrl 的掉电保护（两者不是一回事）
    'battery_min_fly': 14.0,
    'battery_low_voltage': 13.2,
    # 机身自机盒（机体系，含桨/保护圈/脚架余量）
    'body_box': ((-0.32, 0.32), (-0.32, 0.32), (-0.16, 0.10)),
    'cam_fwd': 0.034,
}

RECORD_TOPICS = [
    '/mavros/state', '/mavros/extended_state', '/mavros/battery',
    '/mavros/imu/data', '/mavros/imu/data_raw', '/mavros/imu/mag',
    '/mavros/imu/temperature_imu', '/mavros/altitude', '/vins_imu/data_raw',
    '/mavros/local_position/odom',
    '/mavros/vision_pose/pose', '/mavros/rc/in', '/mavros/rc/out',
    '/mavros/setpoint_raw/attitude', '/mavros/time_reference', '/mavros/estimator_status',
    '/record/infra1',      # 15 Hz 副本（throttle 生成；VINS 仍吃原始 30 Hz） '/camera/infra1/camera_info',
    '/record/infra2',      # 15 Hz 副本 '/camera/infra2/camera_info',
    '/record/depth',       # 10 Hz 副本（深度体积最大） '/camera/depth/camera_info',
    '/vins_estimator/odometry', '/vins_estimator/imu_propagate',
    '/vins_estimator/camera_pose', '/vins_estimator/extrinsic',
    '/vins_estimator/keyframe_pose',
    '/px4ctrl/takeoff_land', '/debugPx4ctrl', '/debugPx4ctrl/fsm_state',
    '/move_base_simple/goal', '/flight_v1/goal_gate',   # goal 项会被 record_topics() 换成 P['goal_topic']
    '/position_cmd', '/drone_0_planning/bspline',
    '/drone_0_ego_planner_node/grid_map/occupancy',           # 2026-11-11：原始占据图（真实净空的唯一判据）
    '/drone_0_ego_planner_node/grid_map/occupancy_inflate',   # P1-6：离线判目标是否在膨胀层
    '/flight_v1/planned_path',
    '/flight_v1/goal_status',
    '/flight_v1/goal_ack',       # 2026-11-12 P6：点击反馈（ACCEPTED/REJECTED/REPLACE）   # 2026-11-11：规划器 OK/ADJUSTED/UNREACHABLE（判读必需） '/flight_v1/executed_trail', '/flight_v1/goal_marker',
    '/tf', '/tf_static', '/rosout',
]


GOAL_TOPIC_LEGACY = '/flight_v1/goal_gate'


def record_topics():
    """录包清单：goal 话题跟随 P['goal_topic']（单一原始量），其余原样。"""
    return [P['goal_topic'] if t == GOAL_TOPIC_LEGACY else t for t in RECORD_TOPICS]


def derive():
    d = {}
    d['map_size_z'] = round(P['ceiling_max'] - P['ground_height'], 2)
    d['eff_infl'] = math.ceil(P['inflation'] / P['resolution']) * P['resolution']
    if 'depth_mindist' in P:
        d['mindist'] = round(float(P['depth_mindist']), 3)   # 用户令：显式值优先
    else:
        d['mindist'] = round(min(d['eff_infl'] - P['cam_fwd'] - 1e-3, 0.15), 3)
    d['ceiling'] = round(P['ground_height'] + d['map_size_z'], 2)
    # 自机盒 → 相机系 AABB（外参从 VINS yaml 读，见 read_extrinsic）
    R, T = read_extrinsic()
    lo, hi = [1e9] * 3, [-1e9] * 3
    for cx in P['body_box'][0]:
        for cy in P['body_box'][1]:
            for cz in P['body_box'][2]:
                dd = [cx - T[0], cy - T[1], cz - T[2]]
                pc = [sum(R[k][i] * dd[k] for k in range(3)) for i in range(3)]
                for i in range(3):
                    lo[i] = min(lo[i], pc[i])
                    hi[i] = max(hi[i], pc[i])
    d['lo'] = [round(v, 3) for v in lo]
    d['hi'] = [round(v, 3) for v in hi]
    return d


def read_extrinsic():
    """从 VINS 的 yaml 读 body_T_cam0（唯一来源；不再硬拷一份）。"""
    txt = read(VINSYAML)
    m = re.search(r'body_T_cam0:.*?data:\s*\[([^\]]*)\]', txt, re.S)
    if not m:
        raise AssertionError('VINS yaml 里找不到 body_T_cam0')
    v = [float(x) for x in m.group(1).replace(NL, ' ').split(',') if x.strip()]
    if len(v) != 16:
        raise AssertionError('body_T_cam0 数值个数 %d != 16' % len(v))
    R = [[v[0], v[1], v[2]], [v[4], v[5], v[6]], [v[8], v[9], v[10]]]
    T = [v[3], v[7], v[11]]
    return R, T


def read(p):
    return open(p, encoding='utf-8', newline='').read()


def write(p, t):
    """只在内容变化时写盘并返回 True（保 mtime，便于"源比二进制新"这类判定）。"""
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    if os.path.exists(p):
        try:
            if read(p) == t:
                return False
        except Exception:
            pass
    open(p, 'w', encoding='utf-8', newline=NL).write(t)
    return True


def rep(t, old, new, tag):
    n = t.count(old)
    if n != 1:
        raise AssertionError('%s: %d 次' % (tag, n))
    return t.replace(old, new, 1)


def join(*a):
    return NL.join(a)


# ---------------------------------------------------------------- 1) 规划器 launch
def launch_block(d):
    prim = ('       原始量: takeoff_height %.2f / goal_radius %.1f / inflation %.3f / ground_height %.2f /'
            % (P['takeoff_height'], P['goal_radius'], P['inflation'], P['ground_height']))
    prim2 = ('               ceiling_max %.2f / max_ray %.1f / max_vel %.1f / resolution %.2f'
             % (P['ceiling_max'], P['max_ray'], P['max_vel'], P['resolution']))
    deriv = ('       派生: map_size_z=%.2f (天花板 %.2f) / eff_inflation=%.2f / mindist=%.3f -->'
             % (d['map_size_z'], d['ceiling'], d['eff_infl'], d['mindist']))
    return join(
        '  <!-- ===== BEGIN 派生参数块（由 flight_v1/sync_params.py 生成，勿手改） =====',
        prim, prim2, deriv,
        '  <param name="/drone_0_ego_planner_node/grid_map/obstacles_inflation" value="%.3f"/>' % P['inflation'],
        '  <param name="/drone_0_ego_planner_node/grid_map/ground_height" value="%.2f"/>' % P['ground_height'],
        '  <param name="/drone_0_ego_planner_node/grid_map/map_size_z" value="%.2f"/>' % d['map_size_z'],
        '  <param name="/drone_0_ego_planner_node/grid_map/max_ray_length" value="%.1f"/>' % P['max_ray'],
        '  <param name="/drone_0_ego_planner_node/grid_map/depth_filter_maxdist" value="5.0"/>',
        '  <param name="/drone_0_ego_planner_node/grid_map/depth_filter_mindist" value="%.3f"/>' % d['mindist'],
        '  <param name="/drone_0_ego_planner_node/fsm/thresh_no_replan_meter" value="%.1f"/>' % P['no_replan_m'],
        '  <param name="/drone_0_ego_planner_node/fsm/thresh_replan_time" value="%.1f"/>' % P['replan_time'],
        '  <param name="/drone_0_ego_planner_node/fsm/near_goal_dist" value="%.1f"/>' % P['near_goal_dist'],
        '  <param name="/drone_0_ego_planner_node/fsm/near_goal_vel" value="0.15"/>',
        '  <param name="/drone_0_ego_planner_node/grid_map/pose_type" value="%d"/>' % P['pose_type'],
        '  <param name="/drone_0_ego_planner_node/grid_map/local_map_margin" value="%d"/>' % P['local_map_margin'],
        '  <param name="/drone_0_ego_planner_node/grid_map/resolution" value="%.2f"/>' % P['resolution'],
        '  <param name="/drone_0_ego_planner_node/grid_map/fx" value="%.6f"/>' % P['depth_fx'],
        '  <param name="/drone_0_ego_planner_node/grid_map/fy" value="%.6f"/>' % P['depth_fy'],
        '  <param name="/drone_0_ego_planner_node/grid_map/cx" value="%.6f"/>' % P['depth_cx'],
        '  <param name="/drone_0_ego_planner_node/grid_map/cy" value="%.6f"/>' % P['depth_cy'],
        '  <param name="/drone_0_ego_planner_node/fsm/manual_goal_z" value="%.2f"/>' % P['takeoff_height'],
        '  <param name="/drone_0_ego_planner_node/fsm/manual_goal_max_distance" value="%.1f"/>' % P['goal_radius'],
        '  <!-- ===== END 派生参数块 ===== -->')


# 派生块里由本脚本统一提供的参数名（先全删、再插一次 => 幂等）
BLOCK_PARAM_KEYS = (
    'obstacles_inflation', 'ground_height', 'map_size_z', 'max_ray_length',
    'depth_filter_maxdist', 'depth_filter_mindist', 'pose_type', 'local_map_margin',
    'resolution', 'fx', 'fy', 'cx', 'cy',
    'manual_goal_z', 'manual_goal_max_distance',
)


def _is_block_param(ln):
    s = ln.strip()
    if not s.startswith('<param'):
        return False
    if '/drone_0_ego_planner_node/grid_map/' not in s and \
       '/drone_0_ego_planner_node/fsm/manual_goal' not in s:
        return False
    return any(('/' + k + '"') in s for k in BLOCK_PARAM_KEYS)


def _is_block_comment_frag(ln):
    s = ln.strip()
    return s.startswith('primitives:') or s.startswith('derived:')


def note_block(d):
    """设计说明块：也由 sync_params 生成，避免"参数改了注释还在讲旧值"。"""
    blind = d['mindist'] + P['cam_fwd']
    return join(
        '  <!-- ===== 设计说明（由 sync_params.py 生成，勿手改；派生值见下方 BEGIN/END 块）=====',
        '',
        '       地图：resolution %.2f m；图底 ground_height %.2f；顶 = %.2f + %.2f = %.2f m'
        % (P['resolution'], P['ground_height'], P['ground_height'], d['map_size_z'], d['ceiling']),
        '         · 图底比真实地面低 %.2f m，地板点稳定落在图内并被记成"障碍"。' % (-P['ground_height']),
        '         · 出图的点不会被丢弃，而是 clamp 到边界后按 miss 投票（等于"把地板擦掉"），',
        '           所以图底不能高于地板；地面测试用它区分"地板在地图里"与"地板被擦掉"。',
        '',
        '       膨胀：param %.3f -> ceil(%.3f/%.2f) = %.0f 格 -> 有效 %.2f m（机体直径 0.337，净裕度 %.2f m）'
        % (P['inflation'], P['inflation'], P['resolution'],
           math.ceil(P['inflation'] / P['resolution']), d['eff_infl'], d['eff_infl'] - 0.1685),
        '         · 2026-11-11（用户问 5/7 根因）：A*/优化器的"自机自由球"已撤销 —— 它把球内真障碍',
        '           一起当自由（实测起点离箱心 0.34 m 时整箱被抹掉，贴箱切角）。起点在膨胀层里由',
        '           A* 的 start/end 反向外推解决；FSM 碰撞判据改用原始占据格。本参数只决定规划裕度。',
        '',
        '       天花板：地图顶 %.2f 必须不高于箱高 1.50（"禁止从箱子上方飞越"）；检查器门是 <=。'
        % d['ceiling'],
        '',
        '       感知/规划：depth_filter_maxdist 5.0 采样、max_ray_length %.1f 截断；' % P['max_ray'],
        '         planning_horizon %.1f（感知 %.1f m，满足上游 "horizon >= 1.5 x sensing"）'
        % (P['planning_horizon'], P['max_ray']),
        '',
        '       近场：mindist %.3f + 相机前移 %.3f = 盲面 %.3f <= 有效膨胀 %.3f'
        % (d['mindist'], P['cam_fwd'], blind, d['eff_infl']),
        '         自机点（桨/保护圈/脚架）由 grid_map.cpp 的自机排除盒剔除，不靠 mindist：',
        '         机体系 %s -> 相机系 AABB lo=%s hi=%s（外参读 VINS yaml）'
        % (P['body_box'], d['lo'], d['hi']),
        '',
        '       历史（别按旧注释理解现象）：',
        '         11-07 ground_height=-0.30 -> 地图下有走廊，实测钻到 z=-0.25',
        '         11-08 morning  ground_height=0.05 -> 地板被 miss 擦掉，机体自己出图',
        '         11-08 19:33    ground -0.01 + 膨胀 0.15（回上游）',
        '         11-08 21:xx    ground -0.10 + 膨胀 0.337（用户令，已废止）',
        '         11-11          膨胀 0.299 -> 有效 0.30（上游实机值；对齐现场 0.25-0.30 m 净空）',
        '       ================================================================== -->')


RETIRED_PARAMS = {"grid_map/self_bubble"}   # 2026-11-11：自机自由球撤销，参数废止

def w_launch(d):
    """重写 launch：先删掉**所有**派生块痕迹，再插一次。

    2026-11-08 修：旧实现只删到 local_map_margin，位置在其后的重复 param
    和半截注释会留下来 —— 文件在第 N 次同步后不再是合法 XML（roslaunch 直接起不来）。
    """
    lines = read(LAUNCH).split(NL)
    out, first_at, i = [], None, 0
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        # 旧块头（中文 BEGIN / 旧英文 user-order items）：连注释续行一起吃掉
        if st.startswith('<!--') and ('派生参数块' in ln or 'user-order items' in ln):
            if first_at is None:
                first_at = len(out)
            while i < len(lines) and '-->' not in lines[i]:
                i += 1
            i += 1
            continue
        # 半截注释残骸（没有 <!-- 开头的 primitives/derived 行）
        if _is_block_comment_frag(ln):
            i += 1
            continue
        # 任何位置的同名 param（重复块 / 旧值）一律删掉，交给派生块统一给
        if _is_block_param(ln):
            i += 1
            continue
        out.append(ln)
        i += 1

    if first_at is None:
        idx = next((k for k, l in enumerate(out) if 'fsm/manual_goal' in l), None)
        if idx is None:
            idx = next(k for k, l in enumerate(out) if 'obstacles_inflation' in l)
        first_at = idx
    out[first_at:first_at] = [launch_block(d)]

    res = []
    for ln in out:
        st = ln.strip()
        if st.startswith('<arg name="map_size_z_"'):
            ln = '    <arg name="map_size_z_" value="%.2f"/>' % d['map_size_z']
        elif st.startswith('<arg name="max_vel"'):
            ln = '    <arg name="max_vel" value="%.1f"/>' % P['max_vel']
        elif st.startswith('<arg name="max_acc"'):
            ln = '    <arg name="max_acc" value="%.1f"/>' % P['max_acc']
        elif st.startswith('<arg name="planning_horizon"'):
            ln = '    <arg name="planning_horizon" value="%.1f"/>' % P['planning_horizon']
        elif st.startswith('<arg name="goal_topic"'):
            ln = '    <arg name="goal_topic" value="%s"/>' % P['goal_topic']
        elif GOAL_TOPIC_LEGACY in ln:
            ln = ln.replace(GOAL_TOPIC_LEGACY, P['goal_topic'])
        elif st.startswith('<arg name="depth_fx"'):
            ln = '    <arg name="depth_fx" default="%.6f"/>' % P['depth_fx']
        elif st.startswith('<arg name="depth_fy"'):
            ln = '    <arg name="depth_fy" default="%.6f"/>' % P['depth_fy']
        elif st.startswith('<arg name="depth_cx"'):
            ln = '    <arg name="depth_cx" default="%.6f"/>' % P['depth_cx']
        elif st.startswith('<arg name="depth_cy"'):
            ln = '    <arg name="depth_cy" default="%.6f"/>' % P['depth_cy']
        elif re.search(r'地面\(-?[0-9.]+\)', ln):
            ln = re.sub(r'地面\(-?[0-9.]+\)', '地面(%.2f)' % P['ground_height'], ln)
        res.append(ln)
    # 设计说明块整体重生成（旧块的数字会随参数漂移，所以不留手写版）
    txt = NL.join(res)
    st = txt.find('  <!-- ===== 设计说明')
    en = txt.find('================================================================== -->')
    if st >= 0 and en > st:
        en = txt.find('-->', en) + 3
        txt = txt[:st] + note_block(d) + txt[en:]
    # 2026-11-10：块外"同名参数"一律丢弃 —— 通用的去重，不是只盯某一个。
    # 背景：self_bubble 曾被历史补丁追加 3 份、no_replan 被反复追加，
    # 同一参数在 launch 里出现多次（后写的生效，另一处装死）。
    lines_all = txt.split(NL)
    inside, names, in_block = [], set(), False
    for ln in lines_all:
        if 'BEGIN 派生参数块' in ln:
            in_block = True
        if in_block:
            inside.append(ln)
            m = re.search(r'<param name="([^"]+)"', ln)
            if m:
                names.add(m.group(1))
            if 'END 派生参数块' in ln:
                in_block = False
    keep, in_block = [], False
    for ln in lines_all:
        if 'BEGIN 派生参数块' in ln:
            in_block = True
        if in_block:
            keep.append(ln)
            if 'END 派生参数块' in ln:
                in_block = False
            continue
        m = re.search(r'<param name="([^"]+)"', ln)
        # 2026-11-11：已废止参数（如 self_bubble）即使不在派生块里也要清掉残留
        if m and (m.group(1) in names or any(m.group(1).endswith(r) for r in RETIRED_PARAMS)):
            continue          # 块外同名 -> 丢弃（块内是唯一权威）
        keep.append(ln)
    return NL.join(keep)


# ---------------------------------------------------------------- 2) 契约
def params_block(d):
    return join(
        'params:',
        '  takeoff_height: %.2f          # == px4ctrl takeoff_height == 规划器 manual_goal_z' % P['takeoff_height'],
        '  goal_radius_m: %.1f            # == 规划器 manual_goal_max_distance == mission GOAL_RADIUS' % P['goal_radius'],
        '  no_replan_m: %.1f              # == 规划器 fsm/thresh_no_replan_meter（末段死区）' % P['no_replan_m'],
        '  replan_time: %.1f             # == 规划器 fsm/thresh_replan_time' % P['replan_time'],
        '  takeoff_hover_s: %.1f' % P['hover_s'],
        '  goal_hover_s: %.1f' % P['hover_s'],
        '  max_vel: %.1f' % P['max_vel'],
        '  max_acc: %.1f' % P['max_acc'],
        '  pose_type: %d' % P['pose_type'],
        '  resolution: %.2f' % P['resolution'],
        '  obstacles_inflation: %.3f' % P['inflation'],
        '  max_ray_length: %.1f' % P['max_ray'],
        '  local_map_margin: %d' % P['local_map_margin'],
        '  ground_height: %.2f' % P['ground_height'],
        '  map_size_z: %.2f             # 天花板 = %.2f' % (d['map_size_z'], d['ceiling']),
        '  ceiling_max: %.1f' % P['ceiling_max'],
        '  depth_mindist: %.3f          # 近场剔除下限（显式；几何门: mindist+cam_fwd <= eff_inflation）' % d['mindist'],
        '',
        'runtime:',
        '  # 2026-11-08：以下三组原来散落在 launch / bash / 人的操作卡里，现已收到契约。',
        '  depth_intrinsics:            # 规划器消费的 D435 对齐深度内参（VINS 用它自己的一套，见 left/right yaml）',
        '    fx: %.6f' % P['depth_fx'],
        '    fy: %.6f' % P['depth_fy'],
        '    cx: %.6f' % P['depth_cx'],
        '    cy: %.6f' % P['depth_cy'],
        '  rc:',
        '    channels: %d' % P['rc_channels'],
        '    centered_tol: %d' % P['rc_centered_tol'],
        '    ch5_min: %d' % P['rc_ch5_min'],
        '  battery:',
        '    min_fly_v: %.1f             # 人操作卡的"才许飞"门（mission preflight 用的是这个）' % P['battery_min_fly'],
        '    low_voltage_v: %.1f         # px4ctrl 的掉电保护（低于它才保护，与上式不同层）' % P['battery_low_voltage'],
        '')


def w_contract(d):
    lines = read(CONTRACT).split(NL)
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip() == 'params:':
            i += 1
            while i < len(lines) and (lines[i].startswith(' ') or lines[i].strip() == ''):
                i += 1
            out.append(params_block(d).rstrip(NL))
            continue
        if i < len(lines) and re.match(r'^runtime:', lines[i]):
            i += 1
            while i < len(lines) and (lines[i].startswith(' ') or lines[i].strip() == ''):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    txt = NL.join(out)
    # goal 话题（seams.goal.topic 是唯一一处 /flight_v1/... ）
    txt = re.sub(r'^(    topic: )/flight_v1/[^\n]*', lambda m: m.group(1) + P['goal_topic'], txt,
                 count=1, flags=re.M)
    # 记录话题清单也进契约（人看得见）
    txt = re.sub(r'^record_topics:.*?(?=^\S|\Z)', '', txt, flags=re.M | re.S)
    txt = txt.rstrip(NL) + NL + NL + 'record_topics:   # 录包唯一清单（recorder 读 generated/record_topics.txt）' + NL
    txt += NL.join('  - %s' % t for t in record_topics()) + NL
    return txt


# ---------------------------------------------------------------- 3) grid_map 自机盒
def w_grid_map(d):
    g = read(GM)
    consts = join(
        '// 2026-11-08（sync_params 生成）自机排除盒：相机系 AABB',
        '// 由 VINS yaml 的 body_T_cam0 把机体系盒 %s 变来（外参只存一份）' % (P['body_box'],),
        'static const double SELF_BOX_LO_0 = %.3f, SELF_BOX_HI_0 = %.3f;' % (d['lo'][0], d['hi'][0]),
        'static const double SELF_BOX_LO_1 = %.3f, SELF_BOX_HI_1 = %.3f;' % (d['lo'][1], d['hi'][1]),
        'static const double SELF_BOX_LO_2 = %.3f, SELF_BOX_HI_2 = %.3f;' % (d['lo'][2], d['hi'][2]))
    if 'SELF_BOX_LO_0' in g:
        g = re.sub(r'// 2026-11-08[^\n]*自机排除盒.*?static const double SELF_BOX_LO_2[^\n]*\n',
                   consts + NL, g, count=1, flags=re.S)
        return g
    raise AssertionError('grid_map 里没有自机盒常量，先跑一次旧版补丁')


# ---------------------------------------------------------------- 4) px4ctrl yaml
def w_px4ctrl():
    t = read(PX4YAML)
    t = re.sub(r'(    takeoff_height: )[0-9.]+', lambda m: m.group(1) + '%.2f' % P['takeoff_height'], t, count=1)
    t = re.sub(r'^(low_voltage: )[0-9.]+', lambda m: m.group(1) + '%.1f' % P['battery_low_voltage'], t,
               count=1, flags=re.M)
    return t


# ---------------------------------------------------------------- 5) 录包清单
def w_topics():
    head = ['# 由 flight_v1/sync_params.py 生成，勿手改', '# 2026-11-08：录包话题的唯一定义处']
    return NL.join(head + record_topics()) + NL


# ---------------------------------------------------------------- 6) fsm 刹车成员
def w_fsm():
    f = read(FSM)
    fh = read(FSMH)
    if 'last_brake_t_' not in fh:
        fh = rep(fh, '    ros::Time fail_safe_healthy_since_;',
                 '    ros::Time fail_safe_healthy_since_;' + NL +
                 '    ros::Time last_brake_t_;   // 2026-11-08 用户令③：急停期持续刹车限频', 'fsmh')
    return f, fh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    d = derive()
    print('takeoff_height=%.2f  goal_radius=%.1f  hover=%.1fs  goal_topic=%s'
          % (P['takeoff_height'], P['goal_radius'], P['hover_s'], P['goal_topic']))
    print('地图: 底 %.2f 顶 %.2f (map_size_z %.2f) 膨胀 %.2f 等效 %.2f 盲面 %.3f'
          % (P['ground_height'], d['ceiling'], d['map_size_z'], P['inflation'], d['eff_infl'],
             d['mindist'] + P['cam_fwd']))
    print('自机盒(相机系) lo=%s hi=%s' % (d['lo'], d['hi']))
    L = w_launch(d)
    C = w_contract(d)
    g = w_grid_map(d)
    px = w_px4ctrl()
    tp = w_topics()
    f, fh = w_fsm()
    print('将写: launch / contract / grid_map / px4ctrl.yaml / generated/record_topics.txt / fsm(h)')
    if not a.apply:
        return 0
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    changed, changed_cpp = [], []
    for p, t in ((LAUNCH, L), (CONTRACT, C), (GM, g), (PX4YAML, px), (GEN_TOPICS, tp),
                 (FSM, f), (FSMH, fh)):
        if read(p) == t:
            continue                      # 内容没变就不碰（mtime 保持，便于判"要不要重建"）
        os.makedirs(SYNC_BAK, exist_ok=True)
        shutil.copy2(p, os.path.join(SYNC_BAK, os.path.basename(p) + '.bak_sync_' + ts))
        write(p, t)
        changed.append(os.path.basename(p))
        if p in (GM, FSM, FSMH):
            changed_cpp.append(os.path.basename(p))
    print('已落盘 .bak_sync_%s：%s' % (ts, ', '.join(changed) if changed else '内容全同，未写盘'))
    if changed_cpp:
        print('!! C++ 源已改：%s' % ', '.join(changed_cpp))
        print('!! 必须重建再起栈：catkin build plan_env path_searching bspline_opt ego_planner')
    return 0


if __name__ == '__main__':
    sys.exit(main())
