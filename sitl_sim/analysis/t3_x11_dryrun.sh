#!/usr/bin/env bash
# x11_dryrun.sh — X1' 判读链干跑预演(T3 v8.7 单元 1.5;prereg v1.1 §6 样本案卷)
# 用 U3pp A3/A1/A2(伪 run 目录,硬链接零拷贝)+U3PO(真实 run 目录)把 v1.1 判读链
# 机器侧端到端跑通:round_result(含 v1.1 标注行)→wa_gate --online(受控失败层)→CSV→figs。
# 伪目录=判读链形状适配(硬链接原袋/原日志+round.log 场景正源存根);不改任何原资产。
set -u
export ROS_DISTRO=noetic ROS_MASTER_URI=http://localhost:11311   # set -u+非交互 source 链已知坑(夜战工具链五坑 v61)
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
S=~/catkin_ws/sitl_sim
DR=~/sitl_sim/t3_results/x11_dryrun_v11
mkdir -p "$DR"

mk_pseudo() {  # mk_pseudo <name> <bag> <vinslog|NONE>
  local d="$DR/$1"
  mkdir -p "$d"
  [ -e "$d/flight.bag" ] || ln "$2" "$d/flight.bag"
  if [ "$3" != "NONE" ]; then [ -e "$d/simvins.log" ] || ln "$3" "$d/simvins.log"; fi
  [ -e "$d/round.log" ] || printf '[03:00:00] SITL up (sitl_world_obstacles)\n[03:00:01] DRYRUN pseudo dir (x11_dryrun, unit 1.5)\n' > "$d/round.log"
}

mk_pseudo A3_hover_gates  ~/sitl_sim/bags/t2v3_hover_033842.bag ~/sitl_sim/t2_results/u3pp_logs/A3_hover_gates.log
mk_pseudo A1_route_gates  ~/sitl_sim/bags/t2v3_route_035325.bag ~/sitl_sim/t2_results/u3pp_logs/A1_route_gates.log
mk_pseudo A2_route_base   ~/sitl_sim/bags/t2v3_route_034144.bag NONE   # log 被同名覆盖丢失(T2 编排债,seam 样本)

echo "== [1] round_result.sh(含 v1.1 COSTGATE/FAILDET 标注行) =="
for spec in "A3_hover_gates 0 0 1" "A1_route_gates 7 -4 1" "A2_route_base 7 -4 1"; do
  set -- $spec
  d="$DR/$1"; gx=$2; gy=$3; gz=$4
  echo "-- $1 (goal $gx $gy $gz)"
  bash "$S/round_result.sh" "$d/flight.bag" "$gx" "$gy" "$gz" sitl_world_obstacles "$d" - - 0 0 0 0 > "$d/RESULT.txt" 2>&1
  cat "$d/RESULT.txt"
done

echo; echo "== [2] wa_gate --online(受控失败层 v1.1) =="
python3 "$S/analysis/t3_wa_gate.py" --online --csv "$DR/x11_dryrun.csv" \
  "$DR/A3_hover_gates" "$DR/A1_route_gates" "$DR/A2_route_base" \
  ~/sitl_sim/vins_smoke_runs/run_U3PO_211438 2>&1

echo; echo "== [3] figs 生成(链尾) =="
mkdir -p ~/catkin_ws/docs/figs
python3 "$S/analysis/t3_xline_report_figs.py" --csv "$DR/x11_dryrun.csv" \
  --runs-glob "$DR/*" --out-dir "$DR/figs" 2>&1 | tail -5
echo; echo "== [4] 判读产物落点 =="
ls -la "$DR" "$DR/figs" 2>/dev/null | head -25
