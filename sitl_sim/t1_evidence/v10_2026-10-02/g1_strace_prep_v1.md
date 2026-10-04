# G1 TCPROS 挂点诊断 strace 预备稿 v1（池件①；零实例不部署）

- 登记：T1 / 2026-10-04 19:4x / 任务书 v11.2 单元 9 池①
- 纪律：**预备稿性质——不部署到活实例**；仅当挂点事件发作窗内才按本稿附着（且禁在判读轮/judging 轮附着）。

## 1. 诊断目标

TCPROS 连接挂点（历史嫌疑：慢连/投递随机 50%/Connection-closed 类事件的 syscall 级定位）——回答"哪一个 connect()/accept()/poll() 停住、停多久、对端是谁"。

## 2. 目标进程与附着方法（发作窗内）

- 目标：mavros（fcu_url 14580 侧）、vins_node、px4ctrl_node、（如在场）探针。
- 附着（网络面限迹，开销最低档）：
  ```
  strace -f -e trace=network,poll,epoll_wait,ppoll,futex -tt -T -p <PID> -o /tmp/g1_strace_<name>_<ts>.log &
  ```
- 捕获窗：≤60s 或事件结束即 `-p` 分离（`kill -INT <strace_pid>` 温和收尾，禁 -9）。
- 旁证同采：`ss -tnpea > /tmp/g1_ss_<ts>.txt` 两拍（间隔 5s）+ `/proc/<pid>/net/tcp` 快照。

## 3. 判读面（预注册描述）

- 挂点定义：单 syscall 持续 >1s（-T 列）或 connect() 返回 ETIMEDOUT/ECONNRESET 序列。
- 输出对账：挂点时刻 × 话题投递缺口（bag/probe 时间线）——挂点仅在"投递缺口同窗"才算因果候选。
- 三个预期形态：①connect 停滞（慢连型）②poll 长等待+对端 RST（Connection-closed 型）③futex 停滞（进程内锁，非网络——转 G2）。

## 4. 风险与红线

- strace 使目标进程降速 2-5×：**禁判读轮/验收轮附着**；仅诊断轮且事件已发生（事后附着仅捕获后续同型事件）。
- 磁盘：60s 网络迹 <50MB（预算内）；轮转单文件，不跨轮累积。
- 部署触发=挂点事件再现 + STATUS 通告；撤除=事件窗结束。

## 5. 事件历史（部署判据参考）

- 慢连不可复现（T1 v4 定案）；投递随机 50%（fcu_url 14580 域，v4 在册）；Connection-closed=cleanup 产物（T3 勘误在册，非挂点）；EXP-3 慢连长窗=本稿首选触发面。
