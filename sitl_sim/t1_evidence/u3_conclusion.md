# U3 R3 投递停滞 — 结论(2026-09-28 夜,T1 v4)

证据:u3v2_2026-09-28/(armed 矩阵+gdb+ss) u3v3_2026-09-28/(稳态/重启矩阵)
u3v4_2026-09-28/(随机性确认) u3_2026-09-28/(建连时延基线);master.log 各轮。

## 现象定界(实测矩阵)

| 实验 | 场景 | 结果 |
|---|---|---|
| u3v2 | 稳定链 baseline | armed 2.4s ✓ |
| u3v2 | SITL 重启 r1/r3(T+2s takeoff) | 24s 窗零投递 ✗;r2 3.8s ✓ |
| u3v3 | 稳态连续 4 pub | 1 成 3 败 ✗ |
| u3v3 | 重启窗连续 4 pub | 0 成 4 败 ✗ |
| u3v4 | 稳态连续 3 pub | p1 ✓ p2 ✓ p3 ✗ |

**新 pub→px4ctrl 的 takeoff 投递随机失败(≈50%),与 SITL 重启无关(稳态同样发生)。**
旧的"15-40s 重启窗口"描述是采样偏差:真实变量是"pub 进程实例",不是时间窗。

## 机制层已钉死的环节

1. **master 侧无责**(master.log 全轮核对):+PUB 注册成功 → publisherUpdate 推送
   px4ctrl,sec=0.00,result=[1,'',0](px4ctrl 的 XML-RPC 立即 ACK)。
2. **px4ctrl 进程健康**(gdb 6 线程栈,停滞窗口内):主循环 WallRate 正常、XMLRPC
   线程 poll 空闲、内部回调队列线程 callAvailable 空闲、PollManager epoll 空闲。
3. **TCPROS 连接从未发起**(ss 全量 TCP 表,停滞窗口):px4ctrl 与 pub(rostopic)
   之间零 TCP 连接(连 SYN_SENT 都无)→ roscpp 收到 update 后的协商(requestTopic
   → connect)未执行或未产生任何 socket 动作;gdb 时点(窗口尾)线程均空闲,与
   "协商超时已返回、后续不再重试"一致。
4. **roscpp 单次协商失败后不主动重试**:订阅侧只在收到新 publisherUpdate 时重新
   尝试;master 只在注册变化时推送 → **每轮新 pub 进程 = 重掷骰子**。这解释了
   04 重试制"窗口过后必达"的真实机制(不是窗口自愈,是新一轮 pub 的新 update)。

## 未定位环节(诚实边界)

失败瞬间 pub 端(rospy)与 px4ctrl 端(roscpp)之间"哪一侧、哪一行"丢掉协商,
未取得直接证据(roscpp DEBUG 日志未能在运行节点上激活;/opt/ros 系统 DSO 符号
有限;SYN 级 tcpdump 未做)。候选:rospy TCPROS/XML-RPC 线程在特定边界卡
(rospy.sleep 的 sim-time 分支无 wall 兜底,rostime_cond.wait(0.5) 循环,
/opt/ros/.../rospy/timer.py:116)——但稳态失败时 /clock 正常,该假设不充分。
**修复点位于 ROS noetic 系统栈(/opt/ros 发行版二进制),不在本仓库可修范围**,
按任务书例外条款:workaround 已实现且边界如下。

## workaround(04_takeoff.sh v3.1)

- 12s 短轮 × -r 2 + 并行 armed 监视,90s 总预算(~7 轮重掷,50% 失败率下
  全败概率 <1%)。
- 边界:极端背运下仍可能 90s 全败(重跑即可);px4ctrl 若在非 MANUAL_CTRL 状态
  会静默忽略 takeoff(幂等设计),不构成风险。
- U3d 验收(T+2s 连续 3 次即时起飞)**不通过**(随机 50%),04 长窗重试仍为
  必要兜底,不降级;此为 ROS1 系统栈约束下的真实边界。
