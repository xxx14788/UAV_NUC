# T1-F4-E6 全仓 pkill 毒点清单与清毒方案（2026-09-30 夜 2）

状态：86 处 pkill 聚群评级完成；脚本级改写挂 owner 确认（跨线件），T1 域核验完成，立约定入库。
证据：`grep -rn pkill sitl_sim/*.sh` = 86 处，10 个脚本。

## 1. 毒点评级表（按 误杀面×可触发性）

| 级 | 模式（聚群计数） | 误杀面 | 实锤前科 | 处置 |
|---|---|---|---|---|
| **P0** | `pkill -f 'roslaunc[h]'`（5 处：t3_clean/sitl_smoke/resume/…） | **全机全部 roslaunch**（含他线在飞 launch、他线私有 master 的 launch） | — | 改精确 PID 或 launch 路径限定；清场语义下须加锁 owner 检查前置 |
| **P0** | `pkill -f 'roscor[e]'`（4 处） | **全部 roscore**（含他线私有 master 11312/11399 等——T1 门禁/G1 复现器正依赖私有 master 存活） | — | 同上；至少排除非默认端口的 roscore |
| **P0** | `pkill -f 'vins_nod[e]'`（5 处+2 处无括号强化） | 所有 vins_node（含他线**回放实例**——回放无锁保护，10:59 T3 误杀 T2 回放即此模式） | **两次实锤**（T3 11:04 认领） | 回放实例改 PID 文件；清场件保留但前加 pgrep 存在性检查+STATUS 广播 |
| **P1** | `pkill -f 'vins_to_mavro[s]'`（5 处） | 所有 vins_to_mavros（在线链+回放链） | F4-E1 现场：单点杀与名字级矛盾的排他证据 | 同 vins_node |
| **P1** | `pkill -x mavros_node`（4 处） | -x 精确名但跨实例（他线 mavros） | — | 锁互斥下可接受；加 owner 检查更稳 |
| **P2** | `pkill -9 -f "gzserve[r]"`（3）/ `bin/px[4]`（6）/ `pkill -x gzserver`（2） | SITL 进程（锁互斥下单实例假设成立） | — | 锁保护下保留；锁外调用即违规（纪律登记） |
| **P2** | `pkill -f "roslaunch.*run_ctrl_sit[l]"`（3）等路径限定族 | 已限定 launch 路径，误杀面小 | — | 保留（良好范例） |
| — | `pkill -f 'vins_node'`（2 处**无括号强化**） | 自匹配面（pkill 自身命令行含 vins_node 时——脚本调用行一般不同名，交互 shell 风险） | 我会话内三犯（pkill 自匹配 ssh 命令行） | 括号强化统一（'vins_nod[e]'） |

## 2. 立约定（回放实例纪律，README_runtime 增补案）

1. **回放实例一律 PID 文件**：启动后 `echo $$ > /tmp/<tag>_replay.pid`；清理 `kill $(cat pid)`
   + 存活性复核，禁按名。
2. **回放前 pgrep 广播**：`pgrep -af 'vins_node'` 非空且非己有时，先 STATUS 通告再动。
3. **清场件（t3_clean 族）锁前置**：持锁才可跑；跑前 STATUS 通告窗。
4. **交互 kill 禁 -f 模式匹配自身**：查 `pgrep -af` 拿 PID，`kill <pid>`。
5. **私有 master 端口登记**：非 11311 的 roscore 使用者开工时 STATUS 报端口（11312/11399 在用），
   清场件 roscor[e] 模式加端口排除。

## 3. T1 域核验（今夜新脚本）

| 脚本 | 杀法 | 评级 |
|---|---|---|
| d1_replay_isolated.sh / e2_debug_replay.sh | kill $vinspid $corepid（精确 PID）+ kill -9 兜底 | ✓ 合规 |
| t1_g1_run_batch.sh / g1_arm2.sh | pkill -f g1_sub（私有 11399 域内） | ✓ 域内无他线 |
| vins_kill_watch.sh（设伏） | 纯观察无杀 | ✓ |

## 4. 脚本级改写挂账（owner 确认后做，非阻塞）

- t3_clean.sh（16 处，T3 owner）——P0 roslaunc[h]/roscor[e]/vins_nod[e] 三族集中地
- sitl_smoke.sh / vins_smoke.sh（共享飞轮，owner=各线共用）——P0 同
- resume.sh / two_leg_flight.sh / v1_flight.sh / t1v1_ground.sh（T1 域可自改）
- 验收（F4-E7）：构造双实例场景演练 0 误杀——待改写完成后统一做

## 5. 与 10:40:26 案的关系

E1-E4 已裁"单点杀非名字级"——本清单 P0 族**不是** 10:40 案的行为人（名字级会连杀
vins_to_mavros）。清单价值=防未来+解释"为什么 pkill 清毒不解决 SIGTERM 悬案"（两案分离，
头号候选仍=同名注册杀，设伏在跑）。
