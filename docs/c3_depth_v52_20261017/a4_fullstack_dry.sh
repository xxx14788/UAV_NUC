#!/usr/bin/env bash
# v5.2 A.4-3 全栈干测（18:56 同款：起 gazebo 全栈不飞；模型清单 38/38+深度墙感知+RGB）
# 用法: bash a4_fullstack_dry.sh   （约 4 分钟；结束自动清场）
L=/home/ghj/sitl_sim
source /opt/ros/noetic/setup.bash
pgrep -x roscore >/dev/null || (setsid nohup roscore >/tmp/a4fs_roscore.log 2>&1 &)
for i in $(seq 1 30); do timeout 5 rosnode list >/dev/null 2>&1 && break; sleep 1; done
pgrep -x gzserver >/dev/null && { echo 'ABORT gzserver residue'; exit 9; }

SITL_WORLD=sitl_world_corridor_v9 SITL_VINS_GRACE=90 nohup bash "$L/start_sitl_vins.sh" > /tmp/a4_fullstack.log 2>&1 &
SUP_PID=$!
echo "supervisor=$SUP_PID; waiting 130s for stack+spawn..."
sleep 130

python3 - <<'EOF'
import rospy, time
import numpy as np
from sensor_msgs.msg import Image
from gazebo_msgs.msg import ModelStates
rospy.init_node('a4fs_probe', anonymous=True, disable_signals=True)
models = set()
def mb(m): models.update(m.name)
rgb = []; depth = []
def rb(m):
    a = np.frombuffer(m.data, dtype=np.uint8); rgb.append((float(a.mean()), float(a.std())))
def db(m):
    a = np.frombuffer(m.data, dtype=np.float32)
    fin = a[np.isfinite(a)]
    depth.append((float(np.isfinite(a).sum()) / max(len(a), 1), float(np.median(fin)) if len(fin) else -1))
rospy.Subscriber('/gazebo/model_states', ModelStates, mb, queue_size=1)
rospy.Subscriber('/iris_stereo_vins/camera/depth/image_raw', Image, db, queue_size=2)
rospy.Subscriber('/iris_stereo_vins/camera/rgb/image_raw', Image, rb, queue_size=2)
t0 = time.time()
while time.time() - t0 < 45 and (len(models) < 30 or len(rgb) < 5 or len(depth) < 5):
    time.sleep(0.5)
n = len(models)
print('MODELS n=%d iris_in=%s' % (n, 'iris_stereo_vins' in models))
if rgb: print('RGB n=%d mean=%.1f std=%.1f -> %s' % (len(rgb), rgb[-1][0], rgb[-1][1], 'ALIVE' if rgb[-1][1] > 10 else 'BLACK'))
else: print('RGB NO-FRAMES')
if depth:
    r, md = depth[-1]
    print('DEPTH n=%d finite_ratio=%.3f med_dist=%.2f -> %s' % (len(depth), r, md,
          'WALL-PERCEIVED' if r > 0.1 and 0.3 < md < 6.0 else 'CHECK'))
else: print('DEPTH NO-FRAMES')
print('VERDICT-MODELS:', 'PASS-38' if n == 38 and 'iris_stereo_vins' in models else 'FAIL-n%d' % n)
EOF

echo '===== teardown ====='
kill -TERM "$SUP_PID" 2>/dev/null
sleep 8
pkill -f 'make px4_sitl gazebo-classic_iris_stereo_vin[s]' 2>/dev/null
pkill -x gzserver 2>/dev/null; pkill -x px4 2>/dev/null
sleep 3
pgrep -x gzserver >/dev/null && echo 'WARN gzserver residue' || echo 'clean: no gzserver'
echo A4-FULLSTACK-DRY-DONE
