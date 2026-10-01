#!/usr/bin/env python3
import sys, rosbag, numpy as np, time
bag_path, out_npz = sys.argv[1], sys.argv[2]
t0 = time.time()
odom=[]; gt=[]; cmd=[]; goal=[]; vp=[]; tl=[]; st=[]; dbg=[]
with rosbag.Bag(bag_path, 'r') as bag:
    iris_idx = None
    for topic, msg, t in bag.read_messages(topics=[
        '/gazebo/model_states','/vins_estimator/odometry','/position_cmd',
        '/move_base_simple/goal','/mavros/vision_pose/pose','/px4ctrl/takeoff_land',
        '/mavros/state','/debugPx4ctrl']):
        ts = t.to_sec()
        if topic == '/gazebo/model_states':
            if iris_idx is None:
                iris_idx = msg.name.index([n for n in msg.name if 'iris' in n][0])
            p = msg.pose[iris_idx].position; q = msg.pose[iris_idx].orientation
            gt.append((ts,p.x,p.y,p.z,q.x,q.y,q.z,q.w))
        elif topic == '/vins_estimator/odometry':
            p = msg.pose.pose.position; v = msg.twist.twist.linear; q = msg.pose.pose.orientation
            odom.append((ts,p.x,p.y,p.z,v.x,v.y,v.z,q.x,q.y,q.z,q.w))
        elif topic == '/position_cmd':
            p = msg.position; v = msg.velocity; a = msg.acceleration
            cmd.append((ts,p.x,p.y,p.z,v.x,v.y,v.z,a.x,a.y,a.z,float(msg.yaw),float(msg.yaw_dot)))
        elif topic == '/move_base_simple/goal':
            p = msg.pose.position; goal.append((ts,p.x,p.y,p.z))
        elif topic == '/mavros/vision_pose/pose':
            p = msg.pose.position; vp.append((ts,p.x,p.y,p.z))
        elif topic == '/px4ctrl/takeoff_land':
            tl.append((ts,int(msg.takeoff_land_cmd)))
        elif topic == '/mavros/state':
            st.append((ts,msg.mode,int(msg.armed)))
        elif topic == '/debugPx4ctrl':
            dbg.append((ts,msg.des_v_x,msg.des_v_y,msg.des_v_z,msg.fb_a_x,msg.fb_a_y,msg.fb_a_z,
                        msg.des_a_x,msg.des_a_y,msg.des_a_z,msg.des_q_x,msg.des_q_y,msg.des_q_z,msg.des_q_w,
                        msg.des_thr,msg.err_axisang_x,msg.err_axisang_y,msg.err_axisang_z,msg.err_axisang_ang,
                        msg.fb_rate_x,msg.fb_rate_y,msg.fb_rate_z,
                        getattr(msg,'odom_delay_ms',0.0),getattr(msg,'odom_staleness_ms',0.0)))
for name, rows in [('gt',gt),('odom',odom),('cmd',cmd),('goal',goal),('vp',vp),('tl',tl),('st',st),('dbg',dbg)]:
    arr = np.array(rows, dtype=float)
    np.save(out_npz+'.'+name+'.npy', arr)
    print(name, arr.shape if len(arr) else 'EMPTY')
print('done', bag_path, 'in %.1fs' % (time.time()-t0))
