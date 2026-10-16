#!/usr/bin/env bash
# v5.2 §一A.4 修复后三验一键件（重装完成后执行）
# ②资产核验 + ①min2 三联征 + ③v9 干测（模型清单/深度墙感知/RGB）
CDIR=/home/ghj/sitl_sim/c3_corridor_20261013
WS=/home/ghj/catkin_ws
echo '===== A.4-2 主栈资产完好核验 ====='
ok=0; fail=0
chk() { local got; got=$(md5sum "$2" 2>/dev/null | cut -d' ' -f1); if [ "${got:0:8}" = "$1" ]; then echo "PASS $3 (${got:0:8})"; ok=$((ok+1)); else echo "FAIL $3 got=${got:0:8} expect=$1"; fail=$((fail+1)); fi; }
chk 974a7533 $WS/../PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/stereo_vins_rig/stereo_vins_rig.sdf cam-SDF 2>/dev/null
chk 974a7533 /home/ghj/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/stereo_vins_rig/stereo_vins_rig.sdf cam-SDF
chk 5f3d48eb $WS/sitl_sim/worlds/sitl_world_corridor_v9.world v9-repo
chk 5f3d48eb $CDIR/sitl_world_corridor_v9.world v9-camp
chk 5f3d48eb /home/ghj/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/worlds/sitl_world_corridor_v9.world v9-px4
chk dd9fb372 $WS/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml config
chk 59d84e4e $WS/devel/.private/px4ctrl/lib/px4ctrl/px4ctrl_node px4ctrl
chk cac140b0 $WS/devel/.private/vins/lib/vins/vins_node vins-node
chk 80be3cf2 $WS/devel/lib/libvins_lib.so vins-lib
grep -q "takeoff_thrust_cap: 0.80" $WS/src/px4ctrl/config/ctrl_param_sitl.yaml && { echo "PASS envelope ON"; ok=$((ok+1)); } || { echo "FAIL envelope OFF"; fail=$((fail+1)); }
ls /usr/share/gazebo-11/media/materials/scripts/c3_lab.material >/dev/null 2>&1 && n_png=$(ls /usr/share/gazebo-11/media/materials/textures/c3_*.png 2>/dev/null | wc -l) && echo "c3 materials: script+c3 png x${n_png}" || echo "WARN c3 material script missing"
[ -x /home/ghj/sitl_sim/gzserver ] && echo "PASS gzserver wrapper" || { echo "FAIL wrapper"; fail=$((fail+1)); }
echo "ASSET-CHECK ok=$ok fail=$fail"

echo '===== A.4-1 min2 三联征（重装后） ====='
bash $CDIR/min2_clean_run.sh depth | tee /tmp/a4_min2.txt
grep -q 'MIN2-VERDICT: RECOVERED' /tmp/a4_min2.txt && echo 'A4-1 PASS' || echo 'A4-1 FAIL'

echo '===== A.4-3 v9 干测（模型清单+深度墙感知+RGB） ====='
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://localhost:11397
export DISPLAY=:99
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:/usr/lib/x86_64-linux-gnu/gazebo-11:${LD_LIBRARY_PATH:-}
MASTER_STARTED=0
if ! timeout 5 rosnode list >/dev/null 2>&1; then
  nohup roscore -p 11397 >/tmp/a4_roscore.log 2>&1 & MASTER_STARTED=1
  for i in $(seq 1 40); do timeout 5 rosnode list >/dev/null 2>&1 && break; sleep 1; done
fi
timeout 5 rosnode list >/dev/null 2>&1 || { echo 'A4-3 MASTER-UP-FAIL'; exit 1; }
/home/ghj/sitl_sim/gzserver --verbose $CDIR/sitl_world_corridor_v9.world >/tmp/a4_gz_v9.log 2>&1 &
GZPID=$!
sleep 25
python3 - <<'EOF'
import rospy, time
import numpy as np
from sensor_msgs.msg import Image
from gazebo_msgs.msg import ModelStates
rospy.init_node('a4_dry_probe', anonymous=True, disable_signals=True)
models = []
def mb(m): models.extend(m.name)
rgb = []; depth = []
def rb(m):
    a = np.frombuffer(m.data, dtype=np.uint8); rgb.append((float(a.mean()), float(a.std())))
def db(m):
    a = np.frombuffer(m.data, dtype=np.float32)
    fin = a[np.isfinite(a)]
    depth.append((float(np.isfinite(a).sum()) / max(len(a), 1), float(np.median(fin)) if len(fin) else -1))
rospy.Subscriber('/gazebo/model_states', ModelStates, mb, queue_size=1)
rospy.Subscriber('/iris_stereo_vins/camera/depth/image_raw', Image, db, queue_size=2)
t0 = time.time()
while time.time() - t0 < 25 and (len(models) < 5 or len(rgb) < 5 or len(depth) < 5):
    time.sleep(0.5)
print('MODELS n=%d sample=%s' % (len(set(models)), sorted(set(models))[:8]))
if rgb: print('RGB n=%d mean=%.1f std=%.1f -> %s' % (len(rgb), rgb[-1][0], rgb[-1][1], 'ALIVE' if rgb[-1][1] > 10 else 'BLACK'))
else: print('RGB NO-FRAMES')
if depth: print('DEPTH n=%d finite_ratio=%.3f med_dist=%.2f -> %s' % (len(depth), depth[-1][0], depth[-1][1], 'WALL-PERCEIVED' if depth[-1][0] > 0.1 and 0.3 < depth[-1][1] < 6.0 else 'CHECK'))
else: print('DEPTH NO-FRAMES')
EOF
kill -TERM $GZPID 2>/dev/null; sleep 2; kill -KILL $GZPID 2>/dev/null
if [ "$MASTER_STARTED" = 1 ]; then pkill -f 'rosmaster --core -p 11397' 2>/dev/null; pkill -f 'roscore -p 11397' 2>/dev/null; fi
echo 'A4-DONE（模型数期望 38——与 18:56 基线核对）'
