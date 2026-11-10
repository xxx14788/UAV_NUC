#!/usr/bin/env bash
# verify_audit_closure.sh — 整改闭合矩阵的**机械复算**（轨 B）
#
# 用途：任何人（不看我的说明）都能一条命令复跑 P0 九条的判据，输出 PASS/FAIL 表。
#       盲评（轨 A）负责"判得对不对"，本脚本负责"跑得出来吗"，两者必须一致。
# 用法：tools/ci/verify_audit_closure.sh [--batch P0]
# 退出码：0 = 全 PASS；1 = 有 FAIL；2 = 环境问题（缺文件/未构建）。
#
# 设计纪律：每项只断言"能被代码证伪"的事实，不解析人类日志。
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PX="$REPO/src/px4ctrl"
LAUNCH="$REPO/src/launch/sim_vins.launch"
SMOKE="$REPO/sitl_sim/vins_smoke.sh"
FAIL=0
PASS=0

chk() { # chk <ID> <描述> <命令...>
  local id="$1" desc="$2"; shift 2
  if "$@" >/dev/null 2>&1; then
    printf '  [PASS] %-6s %s\n' "$id" "$desc"; PASS=$((PASS+1))
  else
    printf '  [FAIL] %-6s %s\n' "$id" "$desc"; FAIL=$((FAIL+1))
  fi
}

echo "== verify_audit_closure (batch ${1:-P0}) @ $(date '+%F %T') =="
echo "repo = $REPO"

# ---- F-04: 配置路径不再指向他人机器；$(find vins) 解析出的文件存在 ----
# 注释里保留 /home/ghj 作为历史说明（有意），故只看非注释行。
chk F-04 "sim_vins.launch 非注释行无 /home/ghj" \
  bash -c "! sed '/<!--/,/-->/d' '$LAUNCH' | grep -q '/home/ghj'"
chk F-04 "vins_config 默认值解析到真实文件" \
  python3 - "$LAUNCH" <<'PY'
import sys, os
import roslaunch.substitution_args as sa
ctx = {'filename': sys.argv[1]}
expr = "$(eval optenv('T2_VINS_CONFIG') or find('vins') + '/../config/sim_stereo/sim_stereo_imu_config.yaml')"
os.environ.pop('T2_VINS_CONFIG', None)
sys.exit(0 if os.path.exists(sa.resolve_args(expr, ctx)) else 1)
PY

# ---- F-03: 两份 yaml 键集一致（白名单可解释） ----
chk F-03 "param_face_diff 差集 ⊆ 白名单" \
  python3 "$REPO/tools/ci/param_face_diff.py" --json

# ---- F-06: 无僵尸键/孤儿键 ----
chk F-06 "param_consumption_audit ZOMBIE=0 ORPHAN=0" \
  python3 "$REPO/tools/ci/param_consumption_audit.py"
chk F-06 "已删符号不在代码行、也不在 yaml 键（注释除外）" \
  python3 - "$PX/src" "$REPO/src/px4ctrl/config/ctrl_param_fpv.yaml" "$REPO/src/px4ctrl/config/ctrl_param_sitl.yaml" <<'PY2'
import os, re, sys
import yaml
pat = re.compile(r'low_voltage|pose_solver|accurate_thrust_model|rotor_drag|k_thrust_horz|'
                 r'Kvi[012]|Kvd[012]|KAng[RPY]|config_full_thrust|bat_is_received|recv_new_odom')
bad = []
for root, _, files in os.walk(sys.argv[1]):
    for name in sorted(files):
        if not name.endswith(('.cpp', '.h')):
            continue
        for ln in open(os.path.join(root, name), encoding='utf-8', errors='replace'):
            if pat.search(ln.split('//')[0]):
                bad.append('%s:%s' % (name, ln.strip()[:60]))
def leaves(node, prefix=''):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            kk = '%s.%s' % (prefix, k) if prefix else str(k)
            out.update(leaves(v, kk)) if isinstance(v, dict) else out.setdefault(kk, v)
    return out
for y in sys.argv[2:]:
    for k in leaves(yaml.safe_load(open(y, encoding='utf-8'))):
        if pat.search(k):
            bad.append('%s:key %s' % (os.path.basename(y), k))
print('\n'.join(bad) if bad else 'clean')
sys.exit(1 if bad else 0)
PY2

# ---- F-01: 四杆遍历 + 常量存在 ----
chk F-01 "check_centered 按 RC_STICK_COUNT 遍历（不再是四遍 ch[0]）" \
  bash -c "grep -q 'i < RC_STICK_COUNT' '$PX/src/input.cpp' && ! grep -q 'abs(ch\[0\]) < 1e-5 && abs(ch\[0\])' '$PX/src/input.cpp'"
chk F-01 "test_rc_centered 全绿" \
  bash -c "test -x '$REPO/devel/.private/px4ctrl/lib/px4ctrl/test_rc_centered' && '$REPO/devel/.private/px4ctrl/lib/px4ctrl/test_rc_centered' >/dev/null"

# ---- F-05: advertise 在 connected 等待之后（静态顺序） ----
chk F-05 "advertise 位于 FCU 连接等待之后" \
  python3 - "$PX/src/px4ctrl_node.cpp" <<'PY'
import re, sys
s = open(sys.argv[1], encoding='utf-8').read()
i_wait = s.find('!fsm.state_data.current_state.connected')
i_adv = s.find('nh.advertise<mavros_msgs::AttitudeTarget>')
sys.exit(0 if i_wait > 0 and i_adv > i_wait else 1)
PY

# ---- F-07: process() 内无阻塞等待 ----
chk F-07 "PX4CtrlFSM.cpp 无 while(ros::ok()) / 0.01s 盲等（注释除外）" \
  bash -c "! grep -nE '^[^/]*while \(ros::ok\(\)\)|Duration\(0\.01\)\.sleep' '$PX/src/PX4CtrlFSM.cpp'"
chk F-07 "延迟 arm 状态存在且被消费" \
  bash -c "grep -q 'takeoff_arm_at_ = now_time' '$PX/src/PX4CtrlFSM.cpp' && grep -q 'now_time >= takeoff_arm_at_' '$PX/src/PX4CtrlFSM.cpp'"
chk F-07 "单拍耗时探针存在" \
  bash -c "grep -q 'struct CycleTimer' '$PX/src/PX4CtrlFSM.cpp' && grep -q 'const CycleTimer cycle_timer' '$PX/src/PX4CtrlFSM.cpp'"

# ---- F-08: bodyrates 零初始化 + 启动期拒绝 ----
chk F-08 "bodyrates 显式零初始化" \
  bash -c "grep -q 'bodyrates{Eigen::Vector3d::Zero()}' '$PX/src/controller.h'"
chk F-08 "use_bodyrate_ctrl 启动期拒绝" \
  bash -c "grep -q 'bodyrate controller is NOT implemented' '$PX/src/px4ctrl_node.cpp'"

# ---- F-02: 判定外置 + 旧缺陷写法消失 ----
chk F-02 "stream_health selftest 通过" \
  python3 "$REPO/sitl_sim/tools/stream_health.py" --selftest
# 只禁止"只传 1 个实参却读 argv[3]"那种写法；本文件第二处 heredoc 传了 3 参，合法。
chk F-02 "vins_smoke 无「单参 heredoc 读 argv[3]」" \
  bash -c "! grep -qF 'python3 - \"\$EV\" <<' '$SMOKE'"

# ---- N-02: 双时钟域分离 + 纯函数测试 ----
chk N-02 "断流用墙钟、跳变用消息戳（两量分离）" \
  bash -c "grep -q 'vins_pose_recv_t_' '$PX/src/PX4CtrlFSM.cpp' && grep -q 'vins_pose_msg_t_' '$PX/src/PX4CtrlFSM.cpp' && ! grep -q 'msg->header.stamp - vins_pose_recv_t_' '$PX/src/PX4CtrlFSM.cpp'"
chk N-02 "test_pose_jump 全绿" \
  bash -c "test -x '$REPO/devel/.private/px4ctrl/lib/px4ctrl/test_pose_jump' && '$REPO/devel/.private/px4ctrl/lib/px4ctrl/test_pose_jump' >/dev/null"

# ---- 汇总：整包测试必须 0 failures ----
SUMMARY=$(catkin_test_results "$REPO/build/px4ctrl/test_results" 2>/dev/null | tail -1)
if printf '%s' "$SUMMARY" | grep -q '0 failures'; then
  printf '  [PASS] TESTS  %s\n' "$SUMMARY"; PASS=$((PASS+1))
else
  printf '  [FAIL] TESTS  %s\n' "${SUMMARY:-<无测试结果，先跑 catkin run_tests>}"; FAIL=$((FAIL+1))
fi

echo "== 结果: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ] || exit 1
