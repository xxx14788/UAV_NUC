#!/usr/bin/env python3
# Unit-4 C-15 attribution: is the 55m-scale track in the replay product a
# bit-level echo of the SOURCE bag's own odom stream (replay assembly
# artifact), or a genuine estimator output (bistability candidate)?
import rosbag, math, sys

SRC = '/home/uav/sitl_sim/bags/t2v3_route_213717.bag'
PROD = '/home/uav/sitl_sim/xtdrone_ref_exp/canonical_route_out.bag'

def stream(bag, topic):
    out = []
    with rosbag.Bag(bag) as b:
        for tp, msg, tt in b.read_messages(topics=[topic]):
            p = msg.pose.pose.position
            out.append((round(msg.header.stamp.to_sec(), 6),
                        round(p.x, 6), round(p.y, 6), round(p.z, 6)))
    return out

src = stream(SRC, '/vins_estimator/odometry')
prod = stream(PROD, '/vins_estimator/odometry')
src_set = set(src)
print('source odom n=%d span=%.2f-%.2f' % (len(src), src[0][0], src[-1][0]))
print('product odom n=%d span=%.2f-%.2f' % (len(prod), prod[0][0], prod[-1][0]))

in_src = sum(1 for r in prod if r in src_set)
print('product frames bit-identical to source stream: %d/%d (%.1f%%)' % (
    in_src, len(prod), 100.0*in_src/len(prod)))

# split product by magnitude
big = [r for r in prod if math.sqrt(r[1]**2+r[2]**2+r[3]**2) > 10]
small = [r for r in prod if math.sqrt(r[1]**2+r[2]**2+r[3]**2) <= 10]
big_in = sum(1 for r in big if r in src_set)
small_in = sum(1 for r in small if r in src_set)
print('big-track (|P|>10m, n=%d): bit-in-source %d (%.1f%%)' % (len(big), big_in, 100.0*big_in/max(1,len(big))))
print('small-track (|P|<=10m, n=%d): bit-in-source %d (%.1f%%)' % (len(small), small_in, 100.0*small_in/max(1,len(small))))
# also: source-side coverage — does every big product frame appear in source?
# and count source frames with |P|>10
src_big = sum(1 for r in src if math.sqrt(r[1]**2+r[2]**2+r[3]**2) > 10)
print('source frames |P|>10m: %d/%d' % (src_big, len(src)))
