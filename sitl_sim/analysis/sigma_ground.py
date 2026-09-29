import rosbag, math, statistics
BAG = "/home/uav/sitl_sim/bags/t2v3_ground_202520.bag"
imu = []
with rosbag.Bag(BAG, "r") as b:
    for topic, msg, ts in b.read_messages(topics=["/mavros/imu/data_raw"]):
        t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
        a = msg.linear_acceleration
        w = msg.angular_velocity
        imu.append((t, a.x, a.y, a.z, w.x, w.y, w.z))
n = len(imu)
t0, t1 = imu[0][0], imu[-1][0]
rate = (n - 1) / (t1 - t0)
# 去趋势(漂移的 bias 块不进 σ):减 1s 滑窗均值后取残差 std
win = max(2, int(rate))
def resid(vals):
    out = []
    for i in range(0, n - win, win):
        seg = vals[i:i+win]
        m = sum(seg) / len(seg)
        out.extend(v - m for v in seg)
    return out
ax = [r[1] for r in imu]; ay = [r[2] for r in imu]; az = [r[3] for r in imu]
gx = [r[4] for r in imu]; gy = [r[5] for r in imu]; gz = [r[6] for r in imu]
sxa = statistics.stdev(resid(ax)); sya = statistics.stdev(resid(ay)); sza = statistics.stdev(resid(az))
sxg = statistics.stdev(resid(gx)); syg = statistics.stdev(resid(gy)); szg = statistics.stdev(resid(gz))
sigma_acc = math.sqrt(sxa**2 + sya**2 + sza**2) / math.sqrt(3)
sigma_gyr = math.sqrt(sxg**2 + syg**2 + szg**2) / math.sqrt(3)
dt = 1.0 / rate
print("ground bag: n=%d rate=%.1fHz dt=%.5fs" % (n, rate, dt))
print("acc resid std=(%.5f,%.5f,%.5f) -> iso sigma_acc=%.5f" % (sxa, sya, sza, sigma_acc))
print("gyr resid std=(%.6f,%.6f,%.6f) -> iso sigma_gyr=%.6f" % (sxg, syg, szg, sigma_gyr))
print("VINS density convention: acc_n = sigma*sqrt(dt) = %.6f" % (sigma_acc * math.sqrt(dt)))
print("VINS density convention: gyr_n = %.6f" % (sigma_gyr * math.sqrt(dt)))
print("current yaml: acc_n=0.1 gyr_n=0.01 | 125Hz-era per-sample equiv: acc_n/1.784=%.5f" % (0.1 / 1.784))
# bias random walk: 1s 窗均值序列的差分 std / sqrt(1s)
mw = [sum(ax[i:i+win]) / win for i in range(0, n - win, win)]
diffs = [mw[i+1] - mw[i] for i in range(len(mw) - 1)]
rw = statistics.stdev(diffs) / math.sqrt(2)
print("acc bias RW estimate ~ %.6f (yaml acc_w=0.001)" % rw)
