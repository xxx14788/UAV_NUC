# T1-E2 快胜序裁决：H0 / H3 双证伪 + smoother 零捕获新事实（2026-09-30 夜）

状态：H0/H3 裁决完成（C03 E-1/E-2 两命令+补扫）；E2 单元剩余（写点全枚举/并发审计/修复/门禁）未开工。
执行者：T1 v7 夜 1。所有命令 0 锁纯读。

## 1. 执行记录（命令与原始输出摘要）

### 1.1 C03 E-1 命令 1：`rosbag info replay_out_smooth3.bag`

```
duration: 2:18s (138s)  start 15.91 end 154.26
messages: 18989
/vins_estimator/imu_propagate  17624 msgs (2 connections)
/vins_estimator/odometry        1365 msgs (2 connections)
```

### 1.2 C03 E-1 命令 2：spike_scan smooth 袋（--jumpth 0.15 --vth 5 --vjump 5 --out）

```
prop: n=6698 t=[15.908..43.232] span=27.3s
odo : n=517  t=[15.844..43.192] span=27.3s
spikes: n=0 (|v|>5:0, dP>0.15:0, |dv|>5:0)
```

注：smooth 袋窗仅 27.3s（15.9–43.2），不含 47s 型事件窗——零尖峰是窗约束非修复证据。

### 1.3 补扫 A：原袋 `t2v3_hover_203248.bag`（同参数，--out scan_orig_gate.json）

```
prop: n=17290 t=[15.908..154.268] span=138.4s
odo : n=1331  span=138.4s
spikes: n=2 (dP>0.15: 2), aligned 2 (100%), jump↔reanchor_delta match 2 ok / 0 bad
31.268  |v|0.683 |dv|0.613 dP=0.2071 dt_ms=8.0  jump(-0.112,+0.041,-0.170)
31.412  |v|0.204 |dv|0.585 dP=0.2341 dt_ms=4.0  jump(-0.114,+0.075,-0.190)
```

### 1.4 补扫 B：smooth3 袋（--out scan_smooth3_gate.json）

```
prop: n=17624 span 显示 1790502948s（末帧 header 戳 unix 域污染，bag 域正常 15.9-154.3）
odo : n=1365
spikes: n=2, aligned 2 (100%), match 2 ok / 0 bad
31.268  |v|0.683 |dv|0.613 dP=0.2071 dt_ms=8.0  jump(-0.112,+0.041,-0.170)
31.412  |v|0.204 |dv|0.585 dP=0.2341 dt_ms=4.0  jump(-0.114,+0.075,-0.190)
```

**与 legacy 原袋逐位一致（含 |v|/|dv|/jump 全列）。**

## 2. 裁决

### 2.1 H0 证伪（P1 第二分支命中）

P1 预言：≈8s/≈1000 帧 imu/odometry≈80 帧 ⟹ F1 成立（T1:84 降级）；真是 138.4s/17290 帧 ⟹ 日志-袋脱钩第二运行，H0 停摆-流死链证伪，T1:84 复活。

实测 smooth3 袋：138s / 17624 imu / 1365 odo（9.9Hz≈正常 odometry 率，覆盖全程）。
**判定：H0 证伪。** replay_vins_smooth3.log（28283 行、尾段 wait-for-imu）与 smooth3 袋脱钩（第二运行）；
"47s 型未修全"观测出自健康运行的产物袋，证据有效。**T1:84 复活为活案。**

### 2.2 H3 证伪（P2 第一分支命中：dt_ms≈8ms）

P2 预言：dt_ms≈8ms ⟹ M3/M4（gap 类）死，事件=ULS 覆写类；100-900ms ⟹ gap 类成立。
实测：31.268 帧 dt_ms=8.0，31.412 帧 dt_ms=4.0 —— **8ms 级，无中间带。**

**判定：H3 证伪。事件=ULS 覆写类机制（latest_* 被优化解直接覆写）。**
P8 联动：T1:54 病链行（"加速度偏差 3-11 m²/s"→应为 m/s²）独立留 T2-W-A 账，C03 侧登记"事件非间隙机制"。

### 2.3 新事实（超出 C03 预案）：smoother 对 47s 型事件零捕获

- legacy 臂事件帧 dP=0.2071/0.2341；smooth 臂（reanchor_smooth:1，配置链完整：cp→sed→vins_node，
  d1_replay_isolated.sh:13-14）同帧 **dP 逐位相同** ⟹ smoother 在事件帧零释放。
- 若 smoother 捕获该事件，首帧至少释放 J/15≈0.0138，事件帧 dP 应≈0.193——实测 0.2071 ⟹ addJump 未被调用或调用时 Δ≈0。
- 与 D1 §4 门禁 1 对照：常规重锚阶跃 8904→0 帧、p99=0.0055m（smoother 工作正常）。
  **区分度结论：常规重锚走 ULS 主路径（已全吸收）；47s 型大事件走捕获点之外的写点（全幅通过）。**
- 修正 D1 §5 口径："offset 补偿了 ~0.05/0.207" 不成立于事件帧——实测零补偿；
  0.05=15 帧×0.0033 的累计是别处释放（可能对应同窗常规重锚分量），不是事件帧补偿。
- 事件双连发 144ms 间隔（31.268→31.412）、jump 向量近同（Δ<0.03）⟹ 与 C03"相邻两处理帧顺序重锚"相容。

### 2.4 P2 负预言检查（触发）

"不应出现 dt_ms≈8ms 且管线健康但 dP 仍 0.2 级"——**已出现**（smooth 臂管线健康+事件全幅）。
按 C03 预设回 A6：A1-A5（定理 1 前提）有未识别破口 ⟹ E2 写点全枚举（estimator.cpp 全文 latest_P/Q/V 写点清单）为本单元最优先。

## 3. 下一步（E2 单元剩余，全部 0 锁）

1. 写点全枚举：estimator.cpp 全文 latest_P/Q/V 写点清单（函数/行/线程/锁内外）——重点：updateLatestStates 之外、processMeasurements/double2vector 后的路径
2. 并发审计（三线程共享状态+锁覆盖域）
3. 修复：ReanchorSmoother 覆盖全部 Δ 源（C03 W2 主案 β：flag 置位搬入 ULS 临界区首+gap 卫+W3 钳制逃生 (b)）
4. 门禁 A/B（P1-P4 先决内置+发布率 N 复算）

## 4. 产物清单

- scan_smooth_gate.json / scan_orig_gate.json / scan_smooth3_gate.json（d1_2026-09-29/ 目录）
- 本文件：t1_evidence/v7_2026-09-30/E2_H0H3_verdict.md
