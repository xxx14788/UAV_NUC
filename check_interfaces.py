#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flight_v1 接缝检查器（方案 v2 / C2）。

契约唯一事实源 = contract/flight_contract.yaml。
本脚本把契约与"活的东西"对账，三种模式：

    --static   无 ROS。契约自洽 + 携带字面量的文件（规划器 launch / 起栈健康门 /
               px4ctrl yaml）必须与契约逐项相等。
    --live     仅 ROS。原有的接线/参数检查 + 三条边的活性与时戳对齐。
    --task     --static + --live + 任务接缝（goal 消费边、/position_cmd 唯一源）。
               起飞前必须跑这个。

输出：JSON（含每条的 name/ok/actual）。退出码：0=PASS，2=FAIL，1=内部异常。

2026-11-08 来历：22:36 那轮"点目标不走"的根因之一就是**起飞前的检查没有牙**
（健康门查的是 aligned_depth_to_color，规划器吃的是 depth/image_rect_raw；
两条流都活着，于是假绿灯）。本脚本把"谁必须等于谁"变成可执行断言，并配
负测试（tests/test_contract.py）证明它真的会 FAIL。
"""
import argparse
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACT = os.path.join(HERE, "contract", "flight_contract.yaml")
PLANNER_LAUNCH = os.path.join(HERE, "run_planner_realmachine_map_v1.launch")
MISSION_PY = os.path.join(HERE, "flight_mission.py")
STACK_SH = os.path.expanduser("~/realflight_stack.sh")
PX4CTRL_YAML = os.path.expanduser("~/catkin_ws/src/px4ctrl/config/ctrl_param_fpv.yaml")

PLANNER = "/drone_0_ego_planner_node"


# ---------------------------------------------------------------- 小工具
def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def _load_contract(path):
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _get(d, dotted, default=None):
    cur = d
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _launch_arg(text, name):
    """从 launch 里取 <arg name="X" value="Y"/> 的 Y（也接受 param 同值写法）。"""
    m = re.search(r'<arg\s+name="%s"\s+value="([^"]+)"' % re.escape(name), text)
    if m:
        return m.group(1)
    m = re.search(r'%s"\s+value="([^"]+)"' % re.escape(name), text)
    return m.group(1) if m else None


def _yaml_scalar(path, dotted):
    """极简 YAML 取值：只支持 'a:\n  b: v' 这种两层键（够用，避免依赖 pyyaml 的失败面）。"""
    import yaml
    try:
        with open(path, encoding="utf-8") as fh:
            cur = yaml.safe_load(fh)
        return _get(cur, dotted)
    except Exception:
        return None


class Checker:
    def __init__(self):
        self.checks = []

    def add(self, name, ok, actual):
        self.checks.append({"name": name, "ok": bool(ok), "actual": actual})

    def verdict(self):
        return "PASS" if all(c["ok"] for c in self.checks) else "FAIL"


# ---------------------------------------------------------------- static
def static_checks(ck, contract, paths):
    seams = contract.get("seams", {}) or {}
    params = contract.get("params", {}) or {}
    gate = contract.get("health_gate", {}) or {}

    # 1) 契约自洽
    depth = _get(seams, "depth.topic")
    pose = _get(seams, "camera_pose.topic")
    goal = _get(seams, "goal.topic")
    ck.add("契约:三条边非空", bool(depth) and bool(pose) and bool(goal),
           {"depth": depth, "camera_pose": pose, "goal": goal})
    ck.add("契约:阈值合法(min_hz>0, max_skew_s>0)",
           float(_get(seams, "depth.min_hz", 0) or 0) > 0
           and float(_get(seams, "camera_pose.min_hz", 0) or 0) > 0
           and float(_get(seams, "camera_pose.max_skew_s", 0) or 0) > 0,
           {"depth_min_hz": _get(seams, "depth.min_hz"),
            "pose_min_hz": _get(seams, "camera_pose.min_hz"),
            "max_skew_s": _get(seams, "camera_pose.max_skew_s")})

    # 2) 规划器 launch 必须与契约一致（这是"消费端"的字面量所在）
    lt = _read(paths["launch"])
    ck.add("接缝:规划器深度 == 契约深度",
           _launch_arg(lt, "depth_topic") == depth,
           {"launch": _launch_arg(lt, "depth_topic"), "contract": depth})
    ck.add("接缝:规划器位姿 == 契约位姿",
           _launch_arg(lt, "camera_pose_topic") == pose,
           {"launch": _launch_arg(lt, "camera_pose_topic"), "contract": pose})
    ck.add("接缝:规划器目标 == 契约目标(禁 /move_base_simple/goal 直连)",
           _launch_arg(lt, "goal_topic") == goal and goal != "/move_base_simple/goal",
           {"launch": _launch_arg(lt, "goal_topic"), "contract": goal})

    # 3) 高度单一来源：px4ctrl takeoff_height == 规划器 manual_goal_z == 契约
    px_h = _yaml_scalar(paths["px4ctrl_yaml"], "auto_takeoff_land.takeoff_height")
    lz = _launch_arg(lt, "manual_goal_z") or _param_value(lt, "fsm/manual_goal_z")
    cz = _get(params, "takeoff_height")
    ok_h = (px_h is not None and lz is not None and cz is not None
            and abs(float(px_h) - float(lz)) < 1e-6 and abs(float(px_h) - float(cz)) < 1e-6)
    ck.add("接缝:起飞高度单一来源(px4ctrl == 规划器 == 契约)", ok_h,
           {"px4ctrl": px_h, "planner": lz, "contract": cz})

    # 4) 目标半径：契约 == 规划器 == 任务脚本
    mr = _launch_arg(lt, "manual_goal_max_distance") or _param_value(lt, "fsm/manual_goal_max_distance")
    cr = _get(params, "goal_radius_m")
    mt = _read(paths["mission"])
    mm = re.search(r"^GOAL_RADIUS\s*=\s*([0-9.]+)", mt, re.M)
    fm = float(mm.group(1)) if mm else None
    ok_r = (mr is not None and cr is not None and fm is not None
            and abs(float(mr) - float(cr)) < 1e-6 and abs(float(fm) - float(cr)) < 1e-6)
    ck.add("接缝:目标半径一致(契约 == 规划器 == flight_mission)", ok_r,
           {"planner": mr, "contract": cr, "flight_mission": fm})

    # 5) 健康门深度必须 == 规划器深度（P0 抓到的真实缺陷）
    st = _read(paths["stack"])
    # 只检查**可执行行**：注释里保留"原来查的是谁"是有价值的考古信息，不算缺陷。
    code = "\n".join(ln for ln in st.splitlines() if not ln.lstrip().startswith("#"))
    gate_depth = _get(gate, "depth_topic")
    uses_contract_var = 'hz "$DEPTH_TOPIC"' in code
    no_wrong_literal = "/camera/aligned_depth_to_color" not in code
    mcur = re.search(r'CONTRACT="([^"]+)"', st)
    stack_contract = (os.path.expandvars(os.path.expanduser(mcur.group(1)))
                      if mcur else None)
    ck.add("接缝:起栈脚本读的契约 == 本次校验的契约",
           stack_contract is not None
           and os.path.abspath(stack_contract) == os.path.abspath(paths["contract"]),
           {"stack": stack_contract, "checker": paths["contract"]})
    ck.add("接缝:健康门深度 == 契约深度(修 P0 缺陷)",
           bool(gate_depth) and gate_depth == depth and uses_contract_var
           and no_wrong_literal,
           {"contract": gate_depth, "gate_uses_contract_var": uses_contract_var,
            "no_aligned_depth_literal": no_wrong_literal})

    # 6) 任务脚本不许把目标直连 RViz 话题
    # 任务脚本现在从契约取 goal topic（GOAL_TOPIC），两种写法都算
    pub_literal = ('Publisher(%r' % goal) in mt.replace('"', "'")
    pub_contract = 'Publisher(GOAL_TOPIC' in mt
    pub_goal = pub_literal or pub_contract
    ck.add("接缝:任务脚本用 Publisher 建 goal_gate（不是只在注释里出现）",
           bool(goal) and goal in mt and pub_goal,
           {"goal_in_mission": goal in mt, "publisher_ctor": pub_goal})


def _param_value(launch_text, name):
    m = re.search(r'<param\s+name="[^"]*%s"\s+value="([^"]+)"' % re.escape(name), launch_text)
    return m.group(1) if m else None


# ---------------------------------------------------------------- live
def _rate(topic, msg_type, seconds):
    """订阅 seconds 秒，返回 (hz, samples)。ROS 不可用时返回 (0.0, [])。"""
    import rospy
    stamps = []
    try:
        rospy.wait_for_message(topic, msg_type, timeout=1.5)
    except Exception:
        return 0.0, []

    def cb(msg):
        stamps.append((rospy.Time.now().to_sec(), msg.header.stamp.to_sec()))

    sub = rospy.Subscriber(topic, msg_type, cb, queue_size=60)
    t0 = time.time()
    while time.time() - t0 < seconds:
        rospy.sleep(0.05)
    sub.unregister()
    if len(stamps) < 2:
        return 0.0, stamps
    span = stamps[-1][0] - stamps[0][0]
    return (len(stamps) - 1) / span if span > 0 else 0.0, stamps


def live_checks(ck, contract, mode):
    import rospy
    import rosgraph
    from sensor_msgs.msg import Image
    from geometry_msgs.msg import PoseStamped

    seams = contract.get("seams", {}) or {}
    depth_topic = _get(seams, "depth.topic")
    pose_topic = _get(seams, "camera_pose.topic")
    goal_topic = _get(seams, "goal.topic")
    cmd_topic = _get(seams, "command.topic")
    depth_min = float(_get(seams, "depth.min_hz", 10.0))
    pose_min = float(_get(seams, "camera_pose.min_hz", 8.0))
    max_skew = float(_get(seams, "camera_pose.max_skew_s", 0.15))

    master = rosgraph.Master("/readonly_flight_interface_audit")
    publishers, subscribers, _ = master.getSystemState()

    def subscriptions(node):
        return sorted(topic for topic, nodes in subscribers if node in nodes)

    def publishers_of(topic):
        # getSystemState() 的形状是 [(topic, [node,...]), ...]：
        # 必须取内层 list 再排序，否则返回 [[node]] 而检查写的是 [node] -> 恒 FAIL
        # （2026-11-08 T4 起飞门自证抓到的：这条 bug 会把每次起飞都拦死）。
        hits = [nodes for t, nodes in publishers if t == topic]
        return sorted(hits[0]) if hits else []

    sellers_of = publishers_of

    def number(path, expected):
        value = rospy.get_param(path, None)
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        ck.add(path, ok and math.isfinite(value) and abs(value - expected) < 1e-6, value)

    # ---- 原有接线检查（保持不变）----
    ctrl = subscriptions("/px4ctrl")
    required_ctrl = {"/mavros/imu/data", "/mavros/imu/data_raw",
                     "/vins_estimator/imu_propagate", "/position_cmd"}
    ck.add("px4ctrl双IMU与控制输入接线", required_ctrl.issubset(ctrl), ctrl)

    planner_inputs = subscriptions(PLANNER)
    required_planner = {depth_topic, pose_topic, "/vins_estimator/imu_propagate", goal_topic}
    ck.add("门控规划器输入接线", required_planner.issubset(planner_inputs)
           and "/camera/aligned_depth_to_color/image_raw" not in planner_inputs,
           planner_inputs)

    # 2026-11-08：这三个值改从契约取（原来硬编码 1/0.15/1.0，改 launch 会误拦）
    for path, key in ((PLANNER + "/grid_map/pose_type", "pose_type"),
                      (PLANNER + "/manager/max_vel", "max_vel"),
                      (PLANNER + "/manager/max_acc", "max_acc")):
        exp = _get(contract, "params." + key)
        value = rospy.get_param(path, None)
        ck.add(path + " == 契约", isinstance(value, (int, float))
               and exp is not None and abs(float(value) - float(exp)) < 1e-6,
               {"runtime": value, "contract": exp})

    takeoff_height = rospy.get_param("/px4ctrl/auto_takeoff_land/takeoff_height", None)
    manual_goal_z = rospy.get_param(PLANNER + "/fsm/manual_goal_z", None)
    manual_goal_max_distance = rospy.get_param(PLANNER + "/fsm/manual_goal_max_distance", None)
    goal_radius = _get(contract, "params.goal_radius_m")
    ck.add("起飞高度单一来源(规划器 manual_goal_z == px4ctrl takeoff_height)",
           takeoff_height is not None and manual_goal_z is not None
           and abs(float(manual_goal_z) - float(takeoff_height)) < 1e-6,
           {"manual_goal_z": manual_goal_z, "takeoff_height": takeoff_height})
    use_msg_z = rospy.get_param(PLANNER + "/fsm/manual_goal_use_msg_z", None)
    ck.add("D1 目标高度不取 RViz 消息 z(use_msg_z 必须 false)", use_msg_z is False, use_msg_z)

    map_z = rospy.get_param(PLANNER + "/grid_map/map_size_z", None)
    ground_z = rospy.get_param(PLANNER + "/grid_map/ground_height", None)
    ceiling = None
    if isinstance(map_z, (int, float)) and isinstance(ground_z, (int, float)):
        ceiling = float(ground_z) + float(map_z)
    ceiling_max = float(_get(contract, "params.ceiling_max", 1.5))
    ck.add("D6 天花板低于箱高(ground_height+map_size_z <= %.2f)" % ceiling_max,
           ceiling is not None and ceiling <= ceiling_max,
           {"ceiling_m": ceiling, "limit": ceiling_max})
    # 2026-11-08（今早四袋）：地图底必须略高于真实地面，否则地板被当障碍
    gh = rospy.get_param(PLANNER + "/grid_map/ground_height", None)
    gh_exp = _get(contract, "params.ground_height")
    # 2026-11-08（独立审计）：近场盲面 vs 膨胀半径 的几何自洽
    mind = rospy.get_param(PLANNER + "/grid_map/depth_filter_mindist", None)
    mind_exp = _get(contract, "params.depth_mindist")
    res = rospy.get_param(PLANNER + "/grid_map/resolution", 0.15)
    infl = rospy.get_param(PLANNER + "/grid_map/obstacles_inflation", None)
    blind = eff_infl = None
    if isinstance(mind, (int, float)) and isinstance(res, (int, float)) and isinstance(infl, (int, float)):
        eff_infl = math.ceil(float(infl) / float(res)) * float(res)   # 实际膨胀（整格施加）
        blind = float(mind) + 0.034 + float(res)                      # 盲面 + 相机前移 + 1 格
    ck.add("近场盲面 <= 膨胀半径(mindist+0.034+res <= ceil(infl/res)*res)",
           blind is not None and eff_infl is not None and blind <= eff_infl + 1e-9,
           {"blind_m": None if blind is None else round(blind, 3),
            "eff_inflation_m": None if eff_infl is None else round(eff_infl, 3)})
    ck.add("depth_mindist == 契约",
           isinstance(mind, (int, float)) and mind_exp is not None
           and abs(float(mind) - float(mind_exp)) < 1e-6,
           {"runtime": mind, "contract": mind_exp})
    ck.add("地图底略高于真实地面(ground_height > 0)",
           isinstance(gh, (int, float)) and gh > 0.0 and gh_exp is not None
           and abs(float(gh) - float(gh_exp)) < 1e-6,
           {"runtime": gh, "contract": gh_exp})

    infl = rospy.get_param(PLANNER + "/grid_map/obstacles_inflation", None)
    ck.add("D5 实机膨胀不低于 0.30(ceil 后 >= 2 格)",
           isinstance(infl, (int, float)) and float(infl) >= 0.30, infl)

    ck.add("目标半径一致(规划器 manual_goal_max_distance == 契约)",
           goal_radius is not None and manual_goal_max_distance is not None
           and abs(float(manual_goal_max_distance) - float(goal_radius)) < 1e-6,
           {"manual_goal_max_distance": manual_goal_max_distance, "contract": goal_radius})

    ck.add("position_cmd唯一来源", publishers_of(cmd_topic) == ["/drone_0_traj_server"],
           publishers_of(cmd_topic))
    ck.add("相机位姿转接发布器", publishers_of(pose_topic) == ["/planner_camera_pose_relay"],
           publishers_of(pose_topic))

    # ---- 新增：三条边的活性与时戳对齐（本次事故的直接缺口）----
    depth_hz, depth_stamps = _rate(depth_topic, Image, 3.0)
    pose_hz, pose_stamps = _rate(pose_topic, PoseStamped, 3.0)
    ck.add("边活性:深度流 %s >= %.1f Hz" % (depth_topic, depth_min),
           depth_hz >= depth_min, round(depth_hz, 2))
    ck.add("边活性:相机位姿 %s >= %.1f Hz" % (pose_topic, pose_min),
           pose_hz >= pose_min, round(pose_hz, 2))
    skew = None
    if depth_stamps and pose_stamps:
        skew = abs(sorted(s for _, s in depth_stamps)[len(depth_stamps) // 2]
                   - sorted(s for _, s in pose_stamps)[len(pose_stamps) // 2])
    ck.add("边对齐:深度与位姿时间戳中位差 <= %.2f s（ApproximateTime 前提）" % max_skew,
           skew is not None and skew <= max_skew, None if skew is None else round(skew, 3))

    if mode == "task":
        ck.add("任务接缝:规划器订阅 %s" % goal_topic, goal_topic in planner_inputs,
               planner_inputs)
        # 注意：起飞前 /position_cmd **没有流**（traj_server 只在收到 bspline 后才发；
        # 20261107_223625 实测：整袋 107 s 里该话题只存在于点目标后的 29.6 s）。
        # 所以这里只能查"话题被 traj_server 广告"，查 hz 会把每次起飞都拦死。
        advertised = any(t == cmd_topic for t, _ in publishers)
        ck.add("任务接缝:%s 已被 traj_server 广告（起飞前不要求有流）" % cmd_topic,
               advertised, sellers_of(cmd_topic))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--task", action="store_true")
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--launch", default=PLANNER_LAUNCH)
    ap.add_argument("--mission", default=MISSION_PY)
    ap.add_argument("--stack", default=STACK_SH)
    ap.add_argument("--px4ctrl-yaml", default=PX4CTRL_YAML)
    args = ap.parse_args()

    # 2026-11-08 二审 F13：--task 优先；--static 与 --live 同时给 = --task；
    # 原来 "--static --task" 会静默只跑 static（live 被吞掉）。
    if args.task or (args.static and args.live):
        mode = "task"
    elif args.static:
        mode = "static"
    elif args.live:
        mode = "live"
    else:
        mode = "task"

    ck = Checker()
    try:
        contract = _load_contract(args.contract)
    except Exception as exc:
        print(json.dumps({"mode": mode, "verdict": "FAIL",
                          "checks": [{"name": "契约可读", "ok": False,
                                      "actual": "%s: %s" % (args.contract, exc)}]},
                         ensure_ascii=False, indent=2))
        return 2

    paths = {"launch": args.launch, "mission": args.mission,
             "stack": args.stack, "px4ctrl_yaml": args.px4ctrl_yaml,
             "contract": args.contract}
    if mode in ("static", "task"):
        static_checks(ck, contract, paths)
    if mode in ("live", "task"):
        # 2026-11-08：先探 master 可达性。rospy.init_node 在 master 不可达时会无限重试，
        # 而这脚本是**起飞硬门**——挂死等于把起飞命令挂死（实测 timeout 40 s 都退不出来）。
        import socket
        socket.setdefaulttimeout(3.0)
        reachable = None
        try:
            import rosgraph
            reachable = rosgraph.Master("/flight_seam_checker_probe").getPid()
        except Exception as exc:
            ck.add("ROS master 可达", False, repr(exc))
        else:
            ck.add("ROS master 可达", True, "pid=%s" % reachable)
        if reachable is not None:
            try:
                import rospy
                rospy.init_node("flight_seam_checker", anonymous=True, disable_signals=True)
                live_checks(ck, contract, mode)
            except Exception as exc:
                ck.add("ROS 环境可用", False, repr(exc))

    result = {"checked_at": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": mode,
              "contract": args.contract, "checks": ck.checks, "verdict": ck.verdict(),
              "scope": "接缝（契约/接线/活性/时戳对齐）。RC 未连接不算失败项；"
                       "不代表电池、桨、地面验图。"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
