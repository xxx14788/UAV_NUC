# SITL 运行时纪律(一页纸,T1-W5)

面向所有会碰 SITL 运行时的人/agent(T1 工程 / T2 诊断 / T3 规划)。违反这些顺序是
2026-09-26 大部分"玄学问题"的来源(证据:当日 STATUS.md 全记录)。

## 1. SITL 运行时锁(三任务共用)

```bash
~/sitl_sim/sitl_lock.sh get T1      # 获取(原子;失败=别人持有)
~/sitl_sim/sitl_lock.sh status      # 查看持锁者
~/sitl_sim/sitl_lock.sh release     # 释放(段结束立即放,持锁上限 30 分钟/段)
~/sitl_sim/sitl_lock.sh force T1    # 抢占(必须先 pgrep -f "bin/px4|gzserver" 为 0)
```
规则:启动任何 Gazebo/PX4/mavros/planner 前必须持锁;不持锁只做离线工作。等锁时做离线部分,每 10 分钟重试。

## 2. SITL 重启序列(杀 → 起,顺序不能乱)

```bash
pkill -9 -f "bin/px4"; pkill -9 -f gzserver     # 1) 先杀 px4 再杀 gzserver
sleep 5                                          # 2) 等端口/共享内存释放
# 3) 重启(不要手敲 make,用脚本——它封装了五个坑):
SITL_WORLD=sitl_world_obstacles nohup bash ~/sitl_sim/start_sitl_depth.sh > ~/sitl_sim/logs/sitl.log 2>&1 &
# 4) 就绪判据是 mavros connected,不是进程存在:
timeout 60 bash -c 'until rostopic echo -n1 /mavros/state 2>/dev/null | grep -q "connected: True"; do sleep 2; done'
```
PX4 重启后 **px4ctrl 不需要重启**(T1-W1 修复后);若仍是旧版二进制,重启 px4ctrl 是临时绕法。

## 3. headless SITL 的五个坑(start_sitl_depth.sh 头注释同步维护)

1. gzserver 需要 `DISPLAY=:99`(Xvfb,相机渲染依赖 X)
2. 先 `source /usr/share/gazebo/setup.sh`(openni 插件库路径)
3. PATH 前置本目录 gzserver wrapper(ROS1 系统插件)
4. pxh stdin 接 `sleep infinity`(EOF 刷爆日志)
5. world 经 `SITL_WORLD` 环境变量选,不散落在命令行

## 4. 起飞前冷态

- planner 必须**冷启动**(先起 px4ctrl 再起 planner;planner 启动前 `/position_cmd` 必须无发布——px4ctrl 的 takeoff 前置检查要求 cmd 冷态)
- goal 只发一次,`timeout 4 rostopic pub -r 1` 模式(单发模式有 TCP 建连竞态,W5 修复)
- 一键全流程:`bash ~/sitl_sim/sitl_smoke.sh`(持锁/起降/分析/清理全自动,四指标 PASS/FAIL)

## 5. px4ctrl 状态观测(T1-W1 新增)

```bash
rostopic echo /debugPx4ctrl/fsm_state    # 1Hz: 状态名 + triggered/state_recv/odom_recv/cmd_recv/landed/armed
```
任何"卡死"10 秒内可定位卡在哪个状态;W1 修复后 PX4 重启会自动回 MANUAL_CTRL 并打
`FSM reset to MANUAL_CTRL` WARN。

## 6. 日志纪律

- 大输出重定向到 `~/sitl_sim/logs/*.log`,不留在终端
- `nohup bash ~/sitl_sim/log_truncate_guard.sh &`(>1GB 自动截断到 10MB,防 5.8GB 重演)
- 状态一律经 `python3 ~/sitl_sim/status_append.py "HH:MM | T1 | <单元> | <状态> | <备注>"`
  追加(ssh echo 中文会乱码)

## 7. mavros 连接与慢连(2026-09-28 U2 定案)

- fcu_url 目标端口=**14580**(PX4 v1.17 offboard 实例,`px4-rc.mavlink`:`-u 14580 -o 14540`)。
  历史 14557 是 2018-09(7f016b5fd4)之前的死约定,靠 libmavconn 的源地址学习才碰巧能用;
  已全量改 14580(b827148),老 master 上 3/3 boot 2.7s 直连。
- `TM: Time jump` 刷屏=timesync 滤波器 50.6s 重收敛周期(500 样本@10Hz),伴生噪音,
  不影响连接,忽略即可。
- **慢连(分钟级)**:仅在 09-27 当日 70+ boot 的累积态出现过;干净系统 29 连 boot 均
  2.7-3.0s(u2loop 曲线),NUC 重启后未复现。**fresh-master 清场(smoke 内置)保留为
  保险不退役**;若白天再现分钟级慢连:先 `ls-remote` 对照当天 boot 数,判定是否回到
  累积态,处置=重启 NUC(有人时段)+ STATUS 记录,不要只做进程级清理(09-27 已证不愈)。

## 8. 磁参数卫生(2026-09-28 U4 定案)

- **写回机制**:EKF2_DECL_TYPE bit1(默认开)在每次 disarm 把 EKF 在线估计的地磁偏角
  写进 EKF2_MAG_DECL 参数(源码 EKF2.cpp:2751)。混磁 world 会话(SITL 切 world)即污染。
- **复发实锤**:09-27 夜 23:35 的复位只写 RAM 未 save,当晚 boot 从 bson 恢复 195°+CAL_MAG ID。
- **根治(已落地)**:bson 设 EKF2_DECL_TYPE=1 + EKF2_MAG_DECL=0(bson 直改;CAL_MAGx_ID
  保留无害——校准 XOFF 从未写入)。GPS 有效时 WMM 短路 saved DECL,即便污染也不伤飞行;
  危害仅在 GPS 失效场景。
- **第二磁力计**:CAL_MAG1_ID=197644=PX4 sensor_mag_sim 第二实例(SIM bus,addr 03;
  197388=addr 02),gazebo 模型里没有任何 magnetometer(sdf 无该传感器)。
- **复位姿势**:改磁参数必须 `param save`(或停 SITL 后直改 bson+核验);
  核验用 `python3 /tmp/bson_read.py` 或 boot 后 param show。
