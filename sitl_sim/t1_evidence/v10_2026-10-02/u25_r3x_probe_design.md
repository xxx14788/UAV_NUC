# R3x 三面在线插桩探针 — 合流设计稿 v1（T1 v10.4 单元 2.5）
（接 T2 v8.1 单元 0.7 第 6 条侦查需求；探针基建=T1 持有；2026-10-03 01:2x；本稿=设计先行，实现随下个 build 窗；0 锁）

## 0. 需求映射（T2 消费侧）

R3x 急冻机理侦查三方对齐分析需要：**①IMU 到达间隔抖动分布（wall-clock 口径，在线/回放对照）②VINS 回调缓冲积压深度（imu_buf/feature_buf 队列长）③墙钟-仿真钟偏差（RTF 波动面）**，与 T2 的 term 收敛率+CPU 负载曲线共时间线对齐。三面设计如下，统一原则=**探针自身禁引入可感知负载**（开销上界预注册 §4，超限即废）。

## 1. 架构：一外部节点 + 一进程内面

```
t1_r3x_probe.py（单节点·三订阅·一采样器·一 jsonl）
  ├─ sub /mavros/imu/data_raw  → 面① 到达间隔抖动（wall-clock=monotonic_ns 差分）
  ├─ sub /clock                → 面③ RTF=墙钟-仿真钟偏差（滑动窗 dRTF）
  ├─ sub /vins_estimator/{imu_propagate,odometry} → 面②a 积压代理=在线戳龄
  │     （wall_now − header.stamp 分布；与 T3 t3_z12_stampage_eval.py 同口径=袋侧截龄的在线版）
  └─ /proc/<vins_pid>/{stat,statm} 1Hz 采样 → CPU%/RSS 曲线（T2 对齐第四方）
  落盘：vins_smoke_runs/<run>/r3x_probe.jsonl（5s 一条 face-tagged 记录，双钟时间戳）

面②b（进程内，真实队列长）：rosNodeTest.cpp 回调处 imu_buf/feature_buf.size() 计数
  + 1Hz [R3xQ] printf 行 → 走既有 [E2uls] 型控制台通道（gates log 捕获路径，零新管线）
  ⚠️ 默认 off（环境变量 T1_R3XQ=1 启用）——T2 纪律：默认关=逐位不变；gtest=开关两态输出等价
```

## 2. 各面记录格式（jsonl，一行一 face）

| face | 字段 | 说明 |
|---|---|---|
| `imu_jit` | `{t_wall, t_ros, n, p50, p95, p99, max_ms, drop_n, hist[ms 桶 0-2-4-8-16-32-64-∞]}` | 间隔=相邻 msg monotonic_ns 差；drop=间隔>3×p50 计数；在线/回放同格式（argv `--mode replay` 打标） |
| `rtf` | `{t_wall, sim_lag_s, rtf_1s, rtf_10s, rtf_min/max_1h}` | sim_lag=wall−sim 累计偏差；rtf_w=窗口内 sim_dt/wall_dt |
| `stampage` | `{stream, p50, p95, p99, max_ms, n}` | 每流一条（imu_prop/odom 分列） |
| `cpu` | `{pid, cpu_pct, rss_mb}` | /proc 差分 1Hz |
| `qdepth`（②b，控制台行） | `[R3xQ] t= imu_buf= feat_buf= feat_age_ms=` | 1Hz；feat_age=队首特征时戳距今 |

## 3. 在线/回放对照口径（面① 的判别用法）

- 同一节点、同一格式跑两域：在线=随 harness 起；回放=私有 master+白名单 play（T2 echo 污染教训 FM-①，禁全话题回放）。
- 判别假设（预注册，判读归 T2）：若急冻窗内**在线**到达间隔 p99 显著恶化而**回放**同袋健康 ⟹ 投递时序竞态面证据加强；若两域同恶 ⟹ 袋内数据面；若两域皆健康 ⟹ 竞态在 VINS 内部消费序（②b 队列深做旁证）。

## 4. 开销上界预注册（超限即废的硬门）

| 面 | 每消息成本 | 落盘 | 上界声明 |
|---|---|---|---|
| ① | 算术+环形缓冲追加（无分配 steady-state）≤1µs@200Hz | 5s/条 | **CPU<0.5% 单核；RAM<1MB（环 4096）；盘<5MB/h** |
| ②a | 差分+分位桶 ≤1µs@200Hz | 5s/条 | 同上 |
| ③ | ≤2µs@/clock 率 | 5s/条 | 同上 |
| CPU 采样 | 2 次 /proc 读/s | 1Hz | <0.1% |
| ②b（进程内） | 回调内一次 size() 读+计数；**不取锁不进临界区**（读点=push 前同线程） | 1Hz printf | <0.01%；默认 off |

**验证法**：上 build 窗先跑 A/B（探针 on/off 各一轮 hover）对拍 RTF/延迟/输出逐位——任何可感知差异（RTF 降>1%/输出非探针原因差异）即判废回炉。

## 5. 合流与登记

- 单节点=1 个 master 注册（ros anonymous name `t1_r3x_probe_<pid>`）——**D(n) 记账 +1，EXP-2 面注记**（被动订阅不进 anon 计数面，但登记在案）。
- 与既有链合流：②b 与 [E2uls]/[T2diag] 同 log 同窗（时间线天然对齐）；外部 jsonl 以双钟戳与控制台行 join。
- 生命周期：随 harness 起止；不被 flight.sh 误清（sweep 白名单注记）。
- 实现排程=下个 build 窗（与 T2 栈发布协调：②b 进 VINS 需双 md5 登记+gtest；①③②a 独立脚本 0 依赖可先行 dry-run）。

## 6. DoD 对账
- 设计稿本份 @T2（回执投 t2_results/）✅（本会话）
- 实现+开销 A/B 验证：挂下个 build 窗（登记为 P1-3 锁窗表新行）
