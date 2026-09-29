# T1-F4 外部 SIGTERM 源：E1-E4 阶段性裁决（2026-09-30 夜）

状态：C06 执行序 E1（核 0.08s 真伪）/E2（对时）/E3（三候选）/E4（系统层）完成；
E5（设伏）/E6（清毒）/E7（验收）未做。执行者：T1 v7 夜 1。0 锁。

## 1. E1：0.08s/0.3s 读数核验

- 台账记录（t2_experiments.md:962，行号自 C06 时代的 1001 漂移）：转述口径"failure detection 后
  0.08s vins(198812)被 -15 杀死 + 0.3s 后未知者重启 sim_vins"。
- log 侧独立时基：t2v3_simvins_route.log **无墙钟戳于死亡点**（nohup stdout，roslaunch INFO 行
  才带墙钟）——0.08s/0.3s 无法从 log 复验，为 T2 现场观察转述，**时基可信度中等**。
- **但事件本身实锤**（log 证据链完整，见 §2）。

## 2. log 侧现场重建（新事实）

时间线（unix 墙钟锚点=log 内 [INFO] 行）：

| 时刻 | 事件 | 证据 |
|---|---|---|
| 10:39:35 | route 轮 bag 启动 | bag 名 103935 |
| ~10:40:2x | vins_estimator 第一实例输出**戛然而止**（t=678.03 T2diag 正常打印，track=125 健康，**无 failure 打印、无正常关闭**） | log :19490-19506 |
| 10:43:20 | `[INFO][1790653400.21]` vins_to_mavros gate 打印——**vins_to_mavros 仍活着** | log :19507-19509 |
| 10:44:47 | `[INFO][1790653487.38]` "20 stable frames, forwarding RESUMED" | log :19510 |
| 10:44:47+ | **第二次 roslaunch（pid 220363）**启动 sim_vins（vins_estimator 220378 / vins_to_mavros 220379 started）→ **立即被终止**（killing on exit 序列） | log :19511-19550 |

**关键推断**：
1. vins_to_mavros 在 vins_estimator 死后存活 4+ 分钟 ⟹ 10:40:26 的杀是**精确单点杀**（只杀 vins_estimator 198812）
   ——不是 pkill 名字级（会同时杀 vins_to_mavros/所有 vins_node 实例）
2. 第二次 roslaunch 的输出**追加**进同一 log ⟹ 启动方式与 flight.sh 的 `>` 截断模式不同（手动/脚本 `>>` 或 fd 继承）
3. T2 观察到的"新实例 0 init"（漫游 x=27）⟹ 10:40:2x 存在一个**启动过第二个 vins_estimator** 的主体
   （其输出去向不明——非本 log）

## 3. E3：三候选对时裁决（全部削弱）

| 候选 | 判 | 依据 |
|---|---|---|
| a) 锁接管清场（pkill 名字级） | **削弱** | 名字级会同时杀 vins_to_mavros——与单点杀矛盾（§2.1）；10:40 无锁接管记录 |
| b) T4-E2 治理器 | **削弱** | E 线 09-29 已收口（891696d 锁 v2 14/14），当时无治理器常驻 |
| c) t3_verify 看门狗 | **削弱** | T3 11:04 撇清（10:40 前后只有 date 轮询）+ journal 佐证：10:40:17 短 SSH 会话（开闭同秒，date 类特征） |

**新头号候选：同名节点注册杀（roslaunch XML-RPC 机制）**——新 vins_estimator 注册 → master 通知
旧同名节点 shutdown → roslaunch 对子进程发 SIGTERM ⟹ 精确单点 + "-15" 外观，与现场完全匹配。
触发源=10:40:2x 启动第二个 vins_estimator 的主体（与 10:44:47 的 220363 是否同一主体未定）。

**journal 窗记录**（10:39-10:47）：10:39:03 SSH 会话开（保持）；10:40:17 SSH 短会话开+闭（来自 192.168.0.2
工作机，date 类轮询特征，与杀事件差 ~9s，无直接证据链）；无其他异常。

## 4. E4：系统层排除

- dmesg：无 OOM/kill 记录（仅 rfkill 噪声）
- journal：无 systemd/OOM 类 kill 事件
- **系统层杀手（OOM-killer 等）排除**，维持"用户态主体"定性

## 5. 待办（F4 剩余）

1. **E5 设伏**：bpftrace/auditd 伏击 15 号信号+roslaunch 启动审计（再现即定案）——需检查 NUC 工具可用性
2. **10:40:2x 第二个 vins_estimator 启动者的追踪**：候选=bash history 审计/其他 agent 会话的命令日志
   （T2/T3 当时的命令记录对表）
3. E6/E7：全仓 pkill 清毒 + 双实例验收（工作量主体，另夜）

## 6. 与 C06 的偏差登记

- C06 预设三候选框架被现场证据全部削弱，同名注册杀升头号——**C06 因子树需补此支**（其 02 源码册
  的 XML-RPC 分析覆盖了机制细节，属"已有弹药未上膛"）
- 0.3s 重启的读数与 log 侧 10:44:47 的重启存在 4.5min 差——T2 转述的"0.3s"可能为"杀+新实例注册"的
  紧邻间隔（10:40:2x 内部），10:44:47 的 220363 是第三次事件；两事件是否同主体待 E5 伏击
