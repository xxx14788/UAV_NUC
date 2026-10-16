#!/usr/bin/env bash
# v5.2 生产栈 strace 采集（病灶复现态，修复前铁律件#2）
# 用法: bash prod_strace_capture.sh   （约 4 分钟；自动清场）
set -e
mkdir -p ~/sitl_sim_strace /tmp/v52_prod_trace
cat > ~/sitl_sim_strace/gzserver <<'WRAP'
#!/usr/bin/env bash
# strace 包装（仅采集用；生产 wrapper 本体零触碰）
exec strace -f -e trace=openat,mmap,brk,madvise -o /tmp/v52_prod_trace/prod_depth.trace \
  /usr/bin/gzserver -s libgazebo_ros_api_plugin.so "$@"
WRAP
chmod +x ~/sitl_sim_strace/gzserver

sed 's|PATH="$HOME/sitl_sim:$PATH"|PATH="$HOME/sitl_sim_strace:$HOME/sitl_sim:$PATH"|' \
  /home/ghj/sitl_sim/start_sitl_vins.sh > ~/sitl_sim_strace/start_sitl_vins_strace.sh
chmod +x ~/sitl_sim_strace/start_sitl_vins_strace.sh

source /opt/ros/noetic/setup.bash
pgrep -x roscore >/dev/null || (setsid nohup roscore >/tmp/psp_roscore.log 2>&1 &)
for i in $(seq 1 30); do timeout 5 rosnode list >/dev/null 2>&1 && break; sleep 1; done
pgrep -x gzserver >/dev/null && { echo 'ABORT gzserver residue'; exit 9; }

SITL_WORLD=sitl_world_corridor_v9 SITL_VINS_GRACE=90 \
  nohup bash ~/sitl_sim_strace/start_sitl_vins_strace.sh > /tmp/v52_prod_trace/stack.log 2>&1 &
SUP_PID=$!
echo "supervisor=$SUP_PID waiting 140s..."
sleep 140

python3 - <<'EOF' | tee /tmp/v52_prod_trace/probe.txt
import rospy, time
import numpy as np
from sensor_msgs.msg import Image
rospy.init_node('prod_probe', anonymous=True, disable_signals=True)
rgb = []; depth = []
def rb(m):
    a = np.frombuffer(m.data, dtype=np.uint8); rgb.append((float(a.mean()), float(a.std())))
def db(m):
    a = np.frombuffer(m.data, dtype=np.float32)
    depth.append(float(np.isfinite(a).sum()) / max(len(a), 1))
rospy.Subscriber('/iris_stereo_vins/camera/depth/image_raw', Image, db, queue_size=2)
rospy.Subscriber('/iris_stereo_vins/camera/rgb/image_raw', Image, rb, queue_size=2)
t0 = time.time()
while time.time() - t0 < 40 and (len(rgb) < 5 or len(depth) < 5):
    time.sleep(0.5)
if rgb: print('RGB n=%d mean=%.1f std=%.1f %s' % (len(rgb), rgb[-1][0], rgb[-1][1], 'BLACK' if rgb[-1][1] == 0 else 'ALIVE'))
else: print('RGB NO-FRAMES')
if depth: print('DEPTH n=%d finite_ratio_max=%.4f %s' % (len(depth), max(depth), 'NAN-DISEASE' if max(depth) == 0 else 'HAS-FINITE'))
else: print('DEPTH NO-FRAMES')
EOF

kill -TERM "$SUP_PID" 2>/dev/null
sleep 8
pkill -f 'make px4_sitl gazebo-classic_iris_stereo_vin[s]' 2>/dev/null
pkill -x gzserver 2>/dev/null; pkill -x px4 2>/dev/null
sleep 5
ls -la /tmp/v52_prod_trace/
wc -l /tmp/v52_prod_trace/prod_depth.trace 2>/dev/null
echo PROD-TRACE-DONE
