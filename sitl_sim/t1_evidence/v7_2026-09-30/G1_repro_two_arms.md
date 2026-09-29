# T1-G1 TCPROS 复现器：建成+双臂 pilot（2026-09-30 夜）

状态：E1 前置核对 + 复现器建成自检 + 两臂各 50 轮（简化探针版）；E3 主量批与条件对齐续臂未做。
执行者：T1 v7 夜 1。0 SITL 锁（私有 master 11399 / 共享 11311 各一轮，深夜无他线在跑）。

## 1. E1 前置核对（C04 判读表权重改写项）

| 项 | 实测 | 判读 |
|---|---|---|
| rosversion roscpp | **1.17.4** | >1.15.12 ⟹ W4/#2185 不因版本上调（维持排除） |
| getent hosts uav4 | 127.0.1.1 uav4 ✓ | hostname 解析健康，H9"解析失败"前提当前不成立 |
| px4ctrl 历史 log resolve 失败 | 无命中 | H9 可达性无历史坐实 |
| 04_takeoff.sh md5 | 2cb42d8ba3d2 | 例行登记 |

## 2. 复现器（工具，可复用）

- `/tmp/g1_sub`（roscpp 长活 sub，手编 260KB，px4ctrl 同构：tcpNoDelay+queue10；构建命令在源文件头注）
- `/tmp/t1_g1_pub_once.py`（每轮新 pub 进程=新协商骰子，U3 同构）
- `/tmp/t1_g1_run_batch.sh`（批跑+判定；**坑登记：`$(grep -c||echo 0)` 在 grep exit1 时叠加输出致判定恒假——已修**）
- 判定：pub 发 20 条@50ms，3s 窗内 sub 收到即 PASS

自检：最小链路（roscore+sub+rostopic pub）52/20 消息全达 ✓；pub_once 对照 20/20 ✓。

## 3. 双臂结果

| 臂 | master | N | 失败 | 判读 |
|---|---|---|---|---|
| ARM1 私有 | 11399 | 50 | **0** | 纯 ROS 裸链无失败 |
| ARM2 共享默认 | 11311 | 50 | **0** | master 共享非失败条件 |

（另：历史一批 41/50 FAIL 系判定 bug 假阳产物，数据作废登记——修复前后混批不可用。）

**结论：U3 失败条件不在 {裸 roscpp sub, rospy pub, master 共享性}**。按 C04 E2 止损分支，
条件对齐续臂（每项 50 轮）：①px4ctrl 本体（devel 二进制直接挂 8 订阅）②大消息带宽（图像尺寸
payload）③SITL 满栈 env/负载（RTF 0.1x 时代）④armed echo churn。留 E2 续夜。

## 4. 过程发现（非 G1 本体）

- **同名注册杀现场实证**（复现器调试期抓到）：两个 g1_sub 实例并存时，旧实例收到
  `Shutdown request received / Reason: new node registered with same name` 后退出——F4 头号候选
  机制的活样本（本文件即为证据引用）。
- pkill 自匹配坑三犯（`pkill -f "11399"` 匹配自身 ssh 命令行自杀）——已入记忆清单。

## 5. 产物

- 本文件 + 工具三件（scp 自 D:\drone_VINS\work\，入库随本提交拷贝至 sitl_sim/tools/g1/）
