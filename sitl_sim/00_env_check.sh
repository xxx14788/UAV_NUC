#!/usr/bin/env bash
# ============================================================
# 00_env_check.sh  —  PX4 SITL 阶段一 / M1.0 体检（只读）
# ============================================================
# 本脚本【不安装任何包、不修改任何系统配置】。
# 唯一的磁盘写入：
#   1) 调用方 tee 生成的报告文件
#   2) 结尾写入 ~/sitl_sim/ 下的三个快照文件
#      pre_dpkg.txt / pre_pip.txt / pre_catkin_md5.txt
#
# 用法（在 NUC 上执行）：
#   mkdir -p ~/sitl_sim
#   bash ~/sitl_sim/00_env_check.sh 2>&1 | tee ~/sitl_sim/sitl_env_check.txt
# ============================================================

set -u          # 只防拼写错误；刻意不用 set -e —— 体检必须跑完全程

SNAP="$HOME/sitl_sim"
mkdir -p "$SNAP"

hr()   { printf '\n================ %s ================\n' "$*"; }
sub()  { printf '\n--- %s ---\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
run()  { printf '\n$ %s\n' "$*"; timeout 20 "$@" 2>&1; local rc=$?;
         [ "$rc" -eq 0 ] || printf '  [退出码 %s；124=超时]\n' "$rc"; }

printf '00_env_check.sh  ——  %s\n' "$(date '+%F %T %Z')"
printf '主机 %s   用户 %s   内核 %s\n' "$(hostname)" "$(whoami)" "$(uname -r)"


hr "1. 系统与资源"

sub "1.1 架构 / 发行版"
run uname -m
run dpkg --print-architecture
run lsb_release -a
run cat /etc/os-release
if [ -f /etc/nv_tegra_release ]; then
  sub "1.1b Jetson L4T（若存在，Gazebo 在 Jetson 上有额外坑）"
  run cat /etc/nv_tegra_release
fi

sub "1.2 CPU / 内存"
run nproc
lscpu 2>/dev/null | grep -E '^(Architecture|Model name|Vendor|CPU\(s\)|Thread|Core|BogoMIPS)' || true
run free -h
run grep -E 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo

sub "1.3 磁盘（\$HOME 所在分区）"
run df -h "$HOME"
run df -BG --output=source,fstype,size,avail,pcent "$HOME"


hr "2. ROS"

sub "2.1 已安装的 ROS 发行版"
run ls -1 /opt/ros

sub "2.2 当前 shell 环境变量"
printf 'ROS_DISTRO = %s\n' "${ROS_DISTRO:-<未设置>}"
printf 'ROS_ROOT   = %s\n' "${ROS_ROOT:-<未设置>}"

sub "2.3 source Noetic 后的探针"
if [ -f /opt/ros/noetic/setup.bash ]; then
  set +u
  . /opt/ros/noetic/setup.bash >/dev/null 2>&1 || true
  set -u
  printf 'source 后 ROS_DISTRO = %s\n' "${ROS_DISTRO:-<未设置>}"
  run rosversion -d
  run rospack find mavros
  run rospack find mavros_msgs
else
  echo "!! /opt/ros/noetic/setup.bash 不存在"
fi


hr "3. Gazebo"

sub "3.1 二进制版本"
if have gazebo; then run gazebo --version; else echo "!! 没有 gazebo 命令（未安装）"; fi
for b in gzserver gzclient gz; do
  if have "$b"; then printf '  %-10s -> %s\n' "$b" "$(command -v "$b")"; else printf '  %-10s -> 缺失\n' "$b"; fi
done

sub "3.2 dpkg 记录"
sh -c "dpkg -l | grep -E 'gazebo|sdformat|ignition|gz-' || echo '(无匹配)'"

sub "3.3 包来源 —— 决定 M1.2 走哪条路（关键）"
echo "== apt-cache policy gazebo11 =="
apt-cache policy gazebo11 2>&1
echo
echo "== apt-cache policy libgazebo11-dev =="
apt-cache policy libgazebo11-dev 2>&1

sub "3.4 apt 源文件（看有没有 OSRF 源）"
run ls -l /etc/apt/sources.list.d/
grep -rhi -E 'osrfoundation|packages\.ros\.org|gazebo' \
     /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null \
  || echo "(sources 里没有 osrf/ros/gazebo 相关行)"


hr "4. MAVROS 配置"

PX4LAUNCH=/opt/ros/noetic/share/mavros/launch/px4.launch
if [ -f "$PX4LAUNCH" ]; then
  run grep -n -E 'fcu_url|gcs_url|tgt_system' "$PX4LAUNCH"
else
  echo "!! 找不到 $PX4LAUNCH"
fi
sh -c "dpkg -l | grep -E 'ros-noetic-mavros|ros-noetic-mavlink' || echo '(mavros 不是通过 apt 装的，或未安装)'"


hr "5. PX4 源码现状（期望：不存在 = 干净起点）"

FOUND=0
for d in "$HOME/PX4-Autopilot" "$HOME/Firmware" "$HOME/px4" "$HOME/PX4-Autopilot-1.17"; do
  if [ -d "$d" ]; then
    FOUND=1
    printf '存在: %s\n' "$d"
    ( cd "$d" && { git describe --tags 2>/dev/null || echo '  (不是 git 仓库)'; } )
    du -sh "$d" 2>/dev/null || true
  fi
done
ls -d "$HOME"/px4* "$HOME"/PX4* 2>/dev/null | grep -v '^$' || true
[ "$FOUND" -eq 0 ] && echo "(没有发现已有的 PX4 源码目录 —— 符合预期)"

sub "5.1 已有的 sitl_sim 目录"
run ls -la "$SNAP"


hr "6. Python 环境"

run python3 --version
run which python3 pip3
run pip3 --version
run python3 -c "import sys; print('executable:', sys.executable); [print('  path:', p) for p in sys.path]"

sub "6.1 empy —— PX4 依赖，必须 >=3.3,<4 且带 RAW_OPT"
python3 -c "import em; print('empy', getattr(em,'__version__','?'), '| RAW_OPT =', hasattr(em,'RAW_OPT')); print('位于', em.__file__)" 2>&1 \
  || echo "(未安装 empy)"

sub "6.2 已有的 --user 安装（会遮蔽 apt 包的关键区，见方案 R4）"
run ls -1 "$HOME/.local/lib/"
sh -c "ls -1 $HOME/.local/lib/python3.*/site-packages/ 2>/dev/null || echo '(空)'"

sub "6.3 PX4 关键 Python 依赖现状"
for m in jinja2 yaml numpy packaging six toml lark kconfiglib pymavlink; do
  python3 -c "import $m; print('  %-12s OK  %s' % ('$m', getattr($m,'__version__','')))" 2>/dev/null \
    || printf '  %-12s 缺失\n' "$m"
done


hr "7. 工具链"

for t in git cmake ninja ccache gcc g++ make python3 pip3 astyle cppcheck \
         rsync unzip zip protoc pkg-config shellcheck; do
  if have "$t"; then printf '  [有] %-12s %s\n' "$t" "$(command -v "$t")"; else printf '  [缺] %-12s\n' "$t"; fi
done
run gcc --version
run cmake --version
run git --version


hr "8. 网络 / GitHub 可达性（风险 R3）"

sub "8.1 代理环境变量"
env | grep -i -E 'proxy' || echo "(未设置代理变量)"

sub "8.2 能否拉到 v1.17.0 的 tag"
run timeout 25 git ls-remote https://github.com/PX4/PX4-Autopilot.git refs/tags/v1.17.0

sub "8.3 TCP 443 直连"
sh -c "timeout 10 bash -c '</dev/tcp/github.com/443' 2>/dev/null && echo 'TCP 443 通' || echo 'TCP 443 不通'"


hr "9. 现有仿真环境 / 端口占用（风险 R9）"

sub "9.1 相关进程"
pgrep -a -f 'gazebo|gzserver|gzclient|px4|mavros|rosmaster|roscore|sim_ws' 2>/dev/null \
  || echo "(无相关进程 —— 干净)"

sub "9.2 监听端口（14540/14557/11311 等被占会冲突）"
run ss -lunp
run ss -ltnp

sub "9.3 sim_ws"
run ls -la "$HOME/sim_ws"

sub "9.4 build2.log（之前编译过什么）"
if [ -f "$HOME/build2.log" ]; then
  printf '大小: %s\n' "$(du -h "$HOME/build2.log" | cut -f1)"
  printf '修改时间: %s\n' "$(date -r "$HOME/build2.log" '+%F %T')"
  printf '末尾 15 行:\n'
  tail -n 15 "$HOME/build2.log"
else
  echo "(不存在)"
fi


hr "10. 快照（用于日后 diff / 回滚）"

sub "10.1 dpkg 全量"
if dpkg -l > "$SNAP/pre_dpkg.txt" 2>/dev/null; then
  printf '已写 %s（%s 行）\n' "$SNAP/pre_dpkg.txt" "$(wc -l < "$SNAP/pre_dpkg.txt")"
else
  echo "!! 写 pre_dpkg.txt 失败"
fi

sub "10.2 pip 包列表"
if ! pip3 list --format=freeze > "$SNAP/pre_pip.txt" 2>/dev/null; then
  pip3 list > "$SNAP/pre_pip.txt" 2>/dev/null || true
fi
printf '已写 %s（%s 行）\n' "$SNAP/pre_pip.txt" "$(wc -l < "$SNAP/pre_pip.txt" 2>/dev/null || echo 0)"

sub "10.3 catkin_ws/src 全量 md5（排除 .git/build/devel）"
if [ -d "$HOME/catkin_ws/src" ]; then
  (
    cd "$HOME/catkin_ws/src" || exit 1
    find . -type f \
        -not -path './.git/*' -not -path '*/build/*' -not -path '*/devel/*' \
        -print0 | sort -z | xargs -0 -r md5sum > "$SNAP/pre_catkin_md5.txt"
  ) 2>/dev/null
  printf '已写 %s（%s 个文件）\n' "$SNAP/pre_catkin_md5.txt" \
         "$(wc -l < "$SNAP/pre_catkin_md5.txt" 2>/dev/null || echo 0)"
else
  echo "!! $HOME/catkin_ws/src 不存在"
fi


hr "11. 自动判读（仅供参考，最终以方案 §M1.0 的人工判读表为准）"

ARCH=$(uname -m)
UBU=$(. /etc/os-release 2>/dev/null; printf '%s' "${VERSION_ID:-?}")
DISK_G=$(df -BG --output=avail "$HOME" 2>/dev/null | tail -1 | tr -dc '0-9')
MEM_G=$(awk '/MemTotal/{printf "%d", $2/1024/1024}' /proc/meminfo)
CPU_N=$(nproc)

chk() {  # chk 标签 ok|warn|bad 说明
  case "$2" in
    ok)   printf '  [ OK ] %-20s %s\n' "$1" "$3" ;;
    warn) printf '  [注意] %-20s %s\n' "$1" "$3" ;;
    *)    printf '  [ !! ] %-20s %s\n' "$1" "$3" ;;
  esac
}

[ "$ARCH" = "aarch64" ] \
  && chk "架构" ok "aarch64，符合预期" \
  || chk "架构" warn "$ARCH（预期 aarch64，需确认）"

[ "$UBU" = "20.04" ] \
  && chk "Ubuntu 版本" ok "20.04，符合约束链（§3.1）" \
  || chk "Ubuntu 版本" bad "$UBU —— 不是 20.04，方案要重新推导"

if [ -n "$DISK_G" ] && [ "$DISK_G" -ge 20 ] 2>/dev/null; then
  chk "可用磁盘" ok "${DISK_G} GB（需 ≥20）"
else
  chk "可用磁盘" bad "${DISK_G:-?} GB（需 ≥20，见 R7）"
fi

if [ -n "$MEM_G" ] && [ "$MEM_G" -ge 4 ] 2>/dev/null; then
  chk "总内存" ok "${MEM_G} GB（需 ≥4）"
else
  chk "总内存" bad "${MEM_G:-?} GB（需 ≥4，见 R7）"
fi

if [ "$CPU_N" -ge 4 ] 2>/dev/null; then
  chk "CPU 核数" ok "${CPU_N} 核"
else
  chk "CPU 核数" warn "${CPU_N} 核（偏少，编译会很慢，建议 -j2）"
fi

if [ -d /opt/ros/noetic ]; then
  chk "ROS Noetic" ok "/opt/ros/noetic 存在"
else
  chk "ROS Noetic" bad "缺失 —— 与真机链路不符，先停下"
fi

if [ -f "$PX4LAUNCH" ]; then
  chk "mavros px4.launch" ok "存在"
else
  chk "mavros px4.launch" bad "缺失 —— 阶段一需要它"
fi

if have gazebo; then
  chk "gazebo 命令" ok "$(gazebo --version 2>/dev/null | head -1)"
else
  chk "gazebo 命令" warn "未安装 —— M1.2 会装 gazebo11"
fi

if [ -d "$HOME/PX4-Autopilot" ]; then
  chk "PX4 源码" warn "已存在 —— M1.1 需先确认版本再决定是否重下"
else
  chk "PX4 源码" ok "不存在，干净起点"
fi

if python3 -c "import em" 2>/dev/null; then
  chk "empy" ok "$(python3 -c 'import em; print(getattr(em,"__version__","?"))' 2>/dev/null)"
else
  chk "empy" warn "未安装（M1.2 会装）"
fi

if pgrep -f 'gzserver|rosmaster|roscore' >/dev/null 2>&1; then
  chk "占用冲突" warn "有 gazebo/roscore 在跑 —— 见 9.1、9.2，跑 SITL 前先清掉（R9）"
else
  chk "占用冲突" ok "无 gazebo/roscore 在跑"
fi


hr "报告结束"
printf '报告：%s/sitl_env_check.txt\n' "$SNAP"
printf '快照：%s/pre_dpkg.txt  pre_pip.txt  pre_catkin_md5.txt\n' "$SNAP"
echo "把这一整份输出贴回来即可。"
