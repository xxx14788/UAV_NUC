#!/bin/bash
# 飞前检查 v2.3（流式输出）——栈未起时跑；每项打印实测内容
# v2.1 变更（2026-10-21，随录制脚本 v1.1 联动）：磁盘门 25G→40G（对齐录制门）；record 指纹 57508a→a97bd9
# v2.2 变更（2026-11-02，用户批准）：record 指纹 a97bd9→3269680b（对齐 10-22 正式版=Win scripts/实飞 正本；仅指纹登记更新，判据/门限零改动）
# v2.3 变更（2026-11-15，用户批准）：record 指纹 1fed2e→cbdc1b（对齐 11-14 在役正式版：
#   录 30/15 + 保留 /mavros/altitude；仅指纹登记更新，判据/门限零改动）
PASS=1
echo "===== 飞前检查 $(date '+%F %T') ====="
echo "--- [信息] 系统状态 ---"
echo "时间: $(date '+%F %T')  负载: $(uptime | awk -F'load average:' '{print $2}')  内存: $(free -h | awk '/Mem:/{print $3"/"$2}')"
AVAIL=$(df -BG --output=avail $HOME | tail -1 | tr -dc '0-9')
echo "--- [1/5] 磁盘（需 ≥40G，对齐录制门）：实测 ${AVAIL}G ---"
if [ "$AVAIL" -ge 40 ]; then echo "  ✓ 通过"; else echo "  ✗ 不够——先清理再飞"; PASS=0; fi
echo "--- [2/5] 残留进程（应无输出=干净）---"
STALE=$( { pgrep -a -x rosmaster; pgrep -a -x vins_node; pgrep -af "mavros_node|realsense2_camera|run_planner|roslaunch"; } 2>/dev/null | grep -v realflight )
if [ -z "$STALE" ]; then echo "  ✓ 无残留"; else echo "  ⚠ 残留（起栈脚本会清）："; echo "$STALE" | sed 's/^/    /'; fi
echo "--- [3/5] 脚本在位（2026-11-15 用户裁定：md5 指纹只打印，不作判据）---"
for f in realflight_record_v1.sh realflight_verify_v1.sh realflight_stack.sh realflight_vins_restart.sh; do
  if [ -f "$HOME/$f" ]; then echo "  ✓ $f 在位($(md5sum "$HOME/$f" | cut -c1-6))"; else echo "  ✗ $f 缺"; PASS=0; fi
done
echo "--- [4/5] 录制目标目录与文档 ---"
[ -d ~/flight_data ] && echo "  ✓ ~/flight_data 在位" || { mkdir -p ~/flight_data && echo "  ✓ 已自动创建 ~/flight_data"; }
ls ~/sitl_sim/docs/2026-10-18_VINS首飞教程_v3.md >/dev/null 2>&1 && echo "  ✓ 首飞教程 v3 在位" || echo "  ⚠ 教程文档未见（不影响飞行）"
echo "--- [5/5] 依赖路径（起栈脚本的四个引用件）---"
for f in ~/sitl_realmachine/realmachine_2a_reboot_stack.sh ~/sitl_realmachine/03_realmachine_config/vins_stereo_realmachine_v0.yaml ~/sitl_realmachine/tools/t1_preflight_check_v1.py; do
  [ -f "$f" ] && echo "  ✓ $f" || { echo "  ✗ 缺 $f——禁飞，找总设计师"; PASS=0; }
done
if [ $PASS -eq 1 ]; then echo "===== 检查 PASS，可起栈（bash ~/realflight_stack.sh）====="; else echo "===== 检查 FAIL ====="; exit 1; fi
