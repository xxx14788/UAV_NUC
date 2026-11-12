#!/bin/bash
# ctrl_mode.sh -- px4ctrl 控制模式原子切换（2026-11-06 顾问）
#
# 为什么要这个脚本：`ctrl_v2/enabled` 与 `thrust_model/hover_percentage` 是**绑定的**。
#   v2 打开时 hp 必须 0.53（偏高，靠积分往下拉）
#   v2 关闭时 hp 必须 0.48（legacy 是 P-only，偏高会冲到 0.75 m —— "飞太高"复发）
# 手改单个键就会出现"v2 关了但 hp 还是 0.53"这种组合，飞行行为立刻错。
#
# 用法：
#   ~/ctrl_mode.sh            # 只看当前状态（增益/限幅从 ctrl_core.h 只读展示）
#   ~/ctrl_mode.sh v2         # 切到 v2（enabled=true,  hp=0.53）
#   ~/ctrl_mode.sh legacy     # 切到 legacy（enabled=false, hp=0.48）
#
# 切换后必须重启 px4ctrl 才生效：rosnode kill /px4ctrl   （roslaunch 会重新拉起）

set -euo pipefail
YAML="$HOME/catkin_ws/src/px4ctrl/config/ctrl_param_fpv.yaml"

show() {
  python3 - "$YAML" <<'PY'
import sys, os, re, yaml
d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
v = d.get("ctrl_v2", {})
print("  文件: %s" % sys.argv[1])
print("  ctrl_v2.enabled     = %s" % v.get("enabled"))
print("  hover_percentage    = %s" % d["thrust_model"]["hover_percentage"])
mode = "v2" if v.get("enabled") else "legacy"
print("  => 当前模式: %s" % mode)
# 2026-11-06 砍旋钮：增益/限幅已锁进 ctrl_core.h，这里读出来给你看（只读，改不了）
core = os.path.join(os.path.dirname(sys.argv[1]), "..", "src", "ctrl_core.h")
if os.path.exists(core):
    s = open(core, encoding="utf-8").read()
    def g(k):
        m = re.search(r"constexpr\s+double\s+%s\s*=\s*([^;]+);" % k, s)
        return m.group(1).strip() if m else "?"
    print("  [锁在 ctrl_core.h，不可调]")
    print("    kp_p/kp_v/ki = %s / %s / %s   (PX4 MPC_Z_P/Z_VEL_P/Z_VEL_I)" % (g("kV2Zp"), g("kV2Zv"), g("kV2Zi")))
    print("    i_lim_z      = %s            (0.3g)" % g("kV2Zilim"))
    print("    cos_min      = %s            (=cos60deg)" % g("kV2CosMin"))
PY
}

if [ $# -eq 0 ]; then
  echo "== px4ctrl 当前控制模式 =="
  show
  echo
  echo "用法: $0 v2 | legacy"
  exit 0
fi

case "$1" in
  v2)     WANT_EN=1; WANT_HP=0.53 ;;
  legacy) WANT_EN=0; WANT_HP=0.48 ;;
  *) echo "未知模式: $1（只接受 v2 | legacy）" >&2; exit 2 ;;
esac

[ -f "$YAML" ] || { echo "找不到 $YAML" >&2; exit 2; }
BAK="$YAML.bak_mode_$(date +%Y%m%d_%H%M%S)"
cp -p "$YAML" "$BAK"
echo "备份: $BAK"

python3 - "$YAML" "$WANT_EN" "$WANT_HP" <<'PY'
import sys, re, io, yaml
path, en, hp = sys.argv[1], sys.argv[2], sys.argv[3]
s = io.open(path, encoding="utf-8").read()
orig = s

# 精确锚定 ctrl_v2 段，只改该段内的 enabled（yaml 里还有 odom_gate 等多个 enabled）
m = re.search(r'(?ms)^ctrl_v2:\s*\n(.*?)(?=^\S|\Z)', s)
assert m, "找不到 ctrl_v2 段"
seg = m.group(0)
seg2 = re.sub(r'(?m)^(\s*enabled:\s*)(?:true|false)(\s*)$',
              lambda mm: mm.group(1) + ("true" if en == "1" else "false") + mm.group(2), seg)
assert seg2 != seg, "ctrl_v2.enabled 未替换"
s = s[:m.start()] + seg2 + s[m.end():]

m2 = re.search(r'(?m)^(\s*hover_percentage:\s*)([0-9.]+)(\s*)$', s)
assert m2, "找不到 hover_percentage"
s = s[:m2.start()] + m2.group(1) + hp + m2.group(3) + s[m2.end():]

# 写前自检：能解析、且两个值都对
d = yaml.safe_load(s)
assert d["ctrl_v2"]["enabled"] == (en == "1"), "enabled 自检失败"
assert abs(float(d["thrust_model"]["hover_percentage"]) - float(hp)) < 1e-9, "hp 自检失败"
io.open(path, "w", encoding="utf-8", newline="\n").write(s)
print("已写入（自检通过）")
PY

echo "== 切换后 =="
show
echo
echo "⚠ 生效需重启节点：  rosnode kill /px4ctrl"
