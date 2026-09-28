# T1-D1 重锚尖峰：取证、根因、修复与验证（2026-09-29 夜）

状态：修复已实现+gtest 7/7 绿；A/B 重放门禁因 NUC 网络中断待完成（本文件随进度更新）

## 1. 现象与取证（D1-1）

### 1.1 素材与工具

| bag | 场景 | 大小 | 工具 |
|---|---|---|---|
| v1_ground_salvage_211520.bag / _2115.bag | 地面静置 67-69s（真值速度恒 0） | 29M/31M | sitl_sim/analysis/spike_scan.py（本次新增） |
| t2v3_ground_202520.bag | T2 W1.1 地面静置 45s | 1.5G | 同上 |
| t2v3_hover_203248.bag | T2 W1.2 悬停 138s | 4.7G | 同上（--jumpth 0.05/0.02 两档） |

spike_scan.py 输出：尖峰清单（时刻/|v|/|dv|/dP/方向/与 odometry 帧对齐/重锚差对照）+ 对齐率 + JSON。

### 1.2 静止锯齿结构（salvage 双袋，实锤）

- imu_propagate（125Hz）速度**基线锯齿**：谷 0.30-0.41 m/s → 每帧 +0.024 m/s 线性爬升（8ms 帧
  ×~3 m/s² 等效加速度偏差，方向恒定 (-x,+y)）→ 峰 0.6-0.8 → 下一个 odometry 帧重置回谷。
- **锯齿周期 ≈ odometry 帧周期（~88-100ms，10-11Hz）**；V1.2 台账记录的"|v| 尖峰 1.15 m/s"
  即锯齿峰值时刻。
- 位置对偶：每周期净漂 ~0.004m/帧 × 11 帧 ≈ 0.05m 被重锚阶跃拉回（jump 0.046-0.061 中位，
  67s 内不衰减反缓慢增长 0.046→0.061）。
- **652/652 全部 odometry 帧都伴随 dP>0.02m 的位置阶跃**（salvage_211520）。

### 1.3 因果钉死：尖峰=优化器解更新瞬间

| 证据 | 数值 |
|---|---|
| 尖峰-odometry 帧对齐率（±50ms） | salvage_211520: **96%**（8056/8370）；salvage_2115: 96%（8237/8563） |
| 跳变量=重锚差数值对照（同量级同方向） | 588/588 与 600/600 全匹配（\|jump\| ∈ [0.5,2]×\|odo−prop\|，逐轴方向一致，比例 ~0.77-0.80 恒定=回放自然增量混入） |

### 1.4 飞行态（hover 203248，jumpth=0.05）

- 138.4s 悬停窗仅 **2 个大重锚阶跃**：t=31.27s（jump (-0.112,+0.041,-0.170)，dP 0.207）与
  t=31.41s（(-0.114,+0.075,-0.190)，dP 0.234），z 向主导，2/2 对齐 odometry 帧，jump≈重锚差匹配。
  悬停窗整体为"健康链"形态。
- 其余 136s 无 dP>0.05 阶跃（正常重锚差 < 0.02-0.05）。

### 1.5 健康链对照（t2v3_ground 202520）

T2 W1.1 地面轮：45.3s 内 **零尖峰**（|v|>0.3: 0 帧、dP>0.02: 0、|dv|>0.5: 0）。
同 config 同链路形态下的干净态 → **重锚锯齿不是全时态常态，是特定状态的病态**
（salvage 轮 = v1_flight 链 init 后早期，疑 Ba/重力对齐/外参收敛不足致传播加速度偏差 ~3 m/s²
恒向；该机制层归 T2-W3 外参/偏置线，本修复在发布侧对两类链都成立）。

## 2. 根因定位（D1-2，VINS-Fusion 源码）

调用链（全部钉到行）：

1. **重锚写回**：`vins_estimator/src/estimator/estimator.cpp:1736-1738`
   `Estimator::updateLatestStates()` 内 `latest_P/Q/V/Ba/Bg = Ps/Rs/Vs/Bas/Bgs[frame_count]`
   ——把 125Hz 传播链状态直接覆写为滑窗最新帧优化解。
2. **稳态触发源**：`estimator.cpp:698` `processMeasurements()` 每帧优化完成后调用
   updateLatestStates（~10Hz，与图像帧同步；L512/L598/L640 为初始化一次性调用，非稳态源）。
3. **发布点**：`estimator.cpp:211-220` `inputIMU()` 每条 IMU（125Hz）→ `fastPredictIMU()`
   （L1714，latest_* 积分前进）→ 有界性检查（T2-v3 加）→ `pubLatestOdometry(latest_*)`
   → `/vins_estimator/imu_propagate`。
4. **消费方**：`px4ctrl/launch/run_ctrl_sitl_vins.launch:17` `~odom → /vins_estimator/imu_propagate`
   ——px4ctrl 直接吃该流，重锚阶跃原样进入控制链（悬停静止门 0.1 m/s 直接受威胁）。

跳变机制：两帧图像之间传播链以 ~3 m/s²（病链）等效偏差积分；优化解把 latest_* 拉回滑窗解；
发布流阶跃 = 重锚差（1.3 节数值对照实锤）。

## 3. 修复（D1-3）：发布侧平滑重锚（b 案）

两案评估：a 案（把 Δ 分摊进 latest_* 本身）经查 latest_* 仅被发布链与 updateLatestStates 自身
消费、滑窗解不读它——a 与 b 效果等价但污染诊断状态并使下一帧 shadow 差计算失真，故选 b。

### 3.1 设计

- **纯值结构** `src/estimator/reanchor_smoother.h`（新文件，header-only，gtest 直接覆盖）：
  `addJump(JP,JV)` 捕获重锚差并入未消化补偿（总量守恒）；发布侧 offset 线性分摊 N=15 帧
  （125Hz → 0.12s）；`step()` 每次发布后步进，idle 期严格清零（防陈旧 offset 慢漂）。
- **shadow 传播链**：`updateLatestStates()`（estimator.cpp）在覆写前快照连续传播状态，回放
  accBuf/gyrBuf 时用**旧 Ba/Bg** 同步积分（`propagateOnce()` 单源积分函数，fastPredictIMU
  重构为其薄包装，热路径行为等价），得到**同时刻纯重锚差**（排除回放自然增量混入，残余跳变
  为零级）。
- **发布叠加**：`inputIMU()` 发布处 `P_pub = latest_P + offset`（估计器内核 latest_* 语义不变，
  仅输出叠加）；有界性防线（T2-v3）仍在原始状态上先行检查。
- **参数**：`reanchor_smooth`（默认 **0**=旧行为；实机 yaml 不含 key 即关闭——实机启用与否留给
  实机线决策，README §3 登记）+ `reanchor_smooth_frames`（默认 15）。SITL
  `config/sim_stereo/sim_stereo_imu_config.yaml` 置 1/15。
- 变更文件：estimator.h/.cpp、parameters.h/.cpp、rosNodeTest.cpp（frames 注入）、
  reanchor_smoother.h、test/test_reanchor_smoother.cpp、CMakeLists.txt（gtest target）、SITL yaml。

### 3.2 gtest（7/7 绿，二进制直跑验证）

守恒（单跳/叠加跳：每帧释放量之和==捕获跳变量）、首帧连续性（offset 立即全额生效）、
线性释放形状、frames=0 防御、idle step 零副作用、发布流级端到端（0.06 阶跃→最大帧步进 0.004，
40 帧后收敛回锚链）。

> 教训入库：①catkin run_tests 退出码会吞 gtest 失败，必须看测试输出/直跑二进制；
> ②"Σoffset==J"不是守恒不变量（正确的是释放量之和），测试与实现必须共享同一语义模型。

### 3.3 行为语义（对消费方的影响）

- 发布流帧间阶跃：病链 0.05-0.1 m → ≈ 自然步进（0.004-0.01 m/帧）；速度阶跃 |dv| 0.35 →
  ~0.025/帧；大重锚（hover 型 0.21m）→ 0.014/帧。总量守恒（0.12s 内补齐），无净漂移注入。
- 速度锯齿被拉平为均值常值（病链均值 ~0.5 m/s 偏置**不变**——它是传播加速度偏差的积分净量，
  属估计内核域，见 1.5；发布均值=内核均值，平均行为零变化）。
- 健康链（ground 型）重锚差≈0 → offset≈0 → 无行为变化（安全性论证的另一半）。

## 4. 双门禁验证（D1-4）

- 门禁 1（失败复现/修复对比，**完成**）：hover bag 重放 A/B，同一修复后二进制 `reanchor_smooth=0 vs 1`。
  - 首轮教训：config 相对路径引用 cam yaml → cfg 必须留在 sim_stereo 目录（`shared_ptr<Camera> Assertion` 崩溃）。
  - smooth2 教训：**与 T3 并发 bag play 在共享 rosgraph 串流**（双 clock/双图像流把外参污染到 tic=[-8.7,-4.1,-15.6]）——重放一律私有 master（ROS_MASTER_URI=113xx）。
  - 终局数据（smooth3 隔离重放，私有 master）：sim 域 17290 帧/138.4s 全程，**常规重锚阶跃 8904 帧（legacy 同袋 138s）→ 0 帧**；全帧 dP 中位 0.0001m、**p99=0.0055m**（验收线 0.02 的 1/4）。
  - 同窗对比修正：legacy 重放前 27.3s 亦零阶跃（重放的 VINS 进入稳态重锚期晚于原 bag），故对比取全程统计而非同窗切片。
- 门禁 2（标准回归，锁窗 W-D1）：vins_smoke 一轮全指标 + 修复后悬停窗包络对比（与 W-D2 同夜执行）。

## 5. 遗留注记（非阻塞，已深挖至机制层）

**47s 型大重锚事件的部分补偿之谜（smooth3 t=47.176/47.320）**：
- 签名：dP=0.207/0.234（z 向 -0.17/-0.19）**与 dV=0.613/0.585 同帧**（位置速度同步跳）=标准重锚签名；
  odometry 流在该窗连续（55 帧 gap~0.1s 正常）→ 排除 re-init/中断。
- 但 offset 只补偿了 ~0.05/0.207（分摊期步进 0.0033/帧×15≈0.05，实测吻合）——存在
  updateLatestStates 之外的 latest_* 写点或双 ULS 连发路径把剩余 0.157 直接写入。
- **非回归**：修复前原 bag 同款事件（31.3s 的 0.207/0.234）本就存在；常规重锚（每帧 0.02-0.05 级，
  占 96%+）100% 被消除。候选路径（下轮深挖）：double2vector 后的二次 ULS 调用 /
  processMeasurements 内对 latest_* 的其他写点；W-D1 飞行态悬停 bag（真值参照下）可提供更多线索。
- 量化影响：单次 0.2m 阶跃对悬停包络的贡献 ≈ 0.2m 瞬时（D3 分解中单列）。

## 6. 结论与移交

- T1 份额（发布流阶跃）：根因到行 + 修复 + gtest 7/7 + 门禁 1 完成 + 入库 b1b2eb6。
- T2 份额（跨域，带量化移交）：病链传播加速度偏差 ~3 m/s² 恒向 (-x,+y)（静止真值 0 下由锯齿
  斜率 0.024 m/s / 8ms 实测；67s 不衰减）+ 47s 型大重锚的未补偿路径（§5），候选排查：
  estimate_extrinsic:1 在线收敛轨迹与锯齿幅度相关性（salvage 病链 vs t2v3_ground 健康链同
  config 不同收敛态对照数据在 1.2/1.5）。修复方向：外参先验精化（T2-W3 头号候选已在办）。
  发布侧平滑重锚与之正交互补。
