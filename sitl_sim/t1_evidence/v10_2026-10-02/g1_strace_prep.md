# G1 strace 方案预备稿（T1 v10.4 深挖池⑨；0 锁纸面件）
（2026-10-03 02:0x；背景=u9_F6_silent_stall_forensics.md：G1=TCPROS 回调层挂点假说，35 轮零实例，升级件悬置——strace/DEBUG 对齐=唯一可证伪路径；本稿=触发即用的脚本草案+侵入性预算）

## 0. G1 挂点假说（待证伪对象）

px4ctrl 某回调在 TCPROS 层冻结（socket 读阻塞/锁死），表现为：话题数据在但回调长时间不返、FSM 主循环节拍正常但某流（odom/imu/cmd）停止更新、无崩溃无退出的"半死"。F6 清点=0 实例 ⟹ 本稿**不部署常驻**，仅备触发即用。

## 1. 触发条件（何时启用）

- 周检仪表（EXP-2 boot_summary / FSM 1Hz 自监视 F4 面板）出现：某订阅流 rcv_stamp 停更 >2s 而 `rostopic hz` 该话题发布侧正常；
- 或任何轮后判读发现"消费侧断流但发布侧健康"的 asymmetric gap。

## 2. strace 方案（两档）

### 档 A：事后取证（无侵入，首选）
挂到**活体**疑似进程：
```
strace -f -tt -T -e trace=network,futex -p <px4ctrl_pid> -o /tmp/g1_strace_<pid>.log &
# 60-120s 后或复现停止时取下；配合 gdb -p <pid> -batch -ex 'thread apply all bt' 双取证
```
- 判据：`recvfrom(..., MSG_DONTWAIT)` 长循环无数据 vs `futex(..., FUTEX_WAIT` 长驻——分别指向 socket 层与锁层；
- `pstack`/gdb all-bt 为补充（哪个回调栈冻结一锤定音）。

### 档 B：受控复现轮（半侵入，需窗+锁）
`strace -f -c -o summary`（仅统计不落全量）随轮启动；开销预算见 §3。仅在档 A 不可及且用户裁定后启用。

## 3. 侵入性预算（预注册）

| 档 | 开销声明 | 门 |
|---|---|---|
| A（-p 挂活体） | strace 每系统调用 ~1-5µs 损耗，仅 network+futex 过滤；px4ctrl 空闲 syscalls 低（<100/s）⟹ **<0.1% CPU** | 复现期短窗（≤120s）；取证后立即脱离 |
| B（-c 统计随轮） | 全 syscall 计数，历史经验 **2-8% CPU** | **默认禁用**；仅用户裁定+独立占锁窗；A/B 对照轮（strace on/off）判 RTF 影响 >1% 即废 |

## 4. 产出与判读
- 挂点定位四分类：socket 阻塞（TCPROS 缓冲）/ futex 锁序 / 回调队列积压（rosout 停）/ 其他；
- 与 R3x 探针（面②a 在线戳龄/面②b 队列深）合流：G1 触发时的 strace 时间线与探针 jsonl 双钟对齐——挂点假说与积压假说（R3x②）的判别材料；
- 登记路径：触发即用后本稿升级为实跑 SOP，产物入 v10 目录 `g1_strace_<runid>.log`。

## 5. 现状声明
- 零实例维持 ⟹ 不部署、不占资源；本稿入池=备件状态。
