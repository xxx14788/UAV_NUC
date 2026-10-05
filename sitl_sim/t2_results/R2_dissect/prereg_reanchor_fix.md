# prereg_reanchor_fix — odometry 重锚/帧跳恒量族修复预注册（T2 v9.5 §1；2026-10-05 12:0x 落盘，先于写码）

> 任务书=Windows `plans/2026-10-05_T2_vins_quality_v9.5.md`（重锚修复执行版）。判据冻结：执行禁改门值。

## 1. 机理分解（本会话取证，2026-10-05）

**发作标本 MACH1（双风暴轮）**：
- 风暴走爬：t=80.5 起 latest 状态 |V| 20→39m/s（truth 静止悬停），**低于发布有界性门（|P|<1e3, |V|<50）全程放行** → imu_propagate 525 帧 >0.5m 跳变 / odometry(10Hz) 580 帧垃圾投喂；
- 拦截：t=87.22 failureDetection insane 门（|V|=50.3 首越）→ [T2fail] → t2_failure_reboot_request → reinit_request 消费者 clearState+setParameter → solver_flag=INITIAL → **发布黑out**（inputIMU 仅 NON_LINEAR 发布，1.3s）；
- **恢复重锚跳：重 init 完成（updateLatestStates(true)）恢复发布，新解世界锚 ≈0 vs 黑out 前已发布走爬位置 ≈−270m → 单帧 294m 跳变**（任务书 293.7m 实测即此）。2.6m 恒量族=同机制温和形态（走爬小/无、新旧锚差 ≈2.5-2.6m）。
- 次风暴 t=148.69 同型（|V|=50.4 触发）。

**既有基建盘点**：T1-D1 平滑器（reanchor_smoother）+ULS 捕获路径（updateLatestStates 影子链）已建成且 gtest 覆盖，但 **REANCHOR_SMOOTH 默认 0=从未启用**；ULS 捕获仅覆盖 NON_LINEAR 内覆写（ζ 翻转族），**reboot 恢复路径无任何连续性逻辑**（黑out 后首帧直接跳）。

## 2. 修复面选型（预注册定案）

**选型=delta 补偿（publish-side，发布侧连续性保持）**，不选 estimator 内核改动。依据：①T1-D1 先例同 Doctrine（kernel untouched，发布侧叠加偏移，守恒律已 gtest）；②判据消费面=发布流（T3 j0d 读 imu_propagate；round_result 帧跳读袋内流）——流级连续即达标；③内核改动=改变求解器行为，回归面不可控。

**四组件（config 键 `t2_stream_guard` 总开关，默认 0=逐位 legacy）**：
- **A. 发布 sane 门收紧**：键 `t2_pub_sane_p`（默认 1e3）/`t2_pub_sane_v`（默认 50.0）——发布前有界性检查改用此值；越界=停发（stop-flow，消费方各自 failsafe=T1-E2 escape(b) Doctrine）。验证 config 设 50/15（正常域 |P|max≈10m/|V|max≈5m/s，3×/7× 余量）。
- **B. 恢复连续性**：跟踪 last_pub（P/V/t）；当发布流缺口 >0.15s（覆盖 reboot 黑out+ sane 门 hold 释放），以 delta=(last_pub−当前值) 喂 reanchor_smoother，**自适应帧数=clamp(ceil(|dP|/0.4), 15, 750)**（单帧步幅 ≤0.4m<0.5m 判读线）。
- **C. D1 ULS 捕获联动启用**：guard=1 时 ULS 覆写捕获+平滑发布路径激活（等价 REANCHOR_SMOOTH=1 语义，ζ 翻转族/悬停微重锚同覆盖；gap_skip 守卫沿用）。
- **D. odometry(10Hz) 流同治**：pubOdometry 应用同偏移+同 sane 门（Ps[WINDOW_SIZE] 基；偏移快照在 mProcess→mPropagate 既有序下取）。
- banner：`[T2SGCFG] guard=%d sane_p=%.1f sane_v=%.1f resume_gap=0.15`（本线行族；冻结行零改动）。

**局限注记（诚实）**：姿态（yaw）连续性不覆盖（偏移仅 P/V）；正常域因组件 C 微重锚偏移非恒零→零回归判据用运营带宽非逐位（见 §4）。

## 3. 实施约束

- gtest：新增 test_t2_stream_guard.cpp（gap 检测/ sane 门阈值/自适应帧数/守恒/恢复 delta 数学，纯值逻辑）+ 全量既有 gtest 必须全绿（含 test_reanchor_smoother）。
- build：catkin build vins；新栈双 md5 登记；异议窗 15min（STATUS 12:05 通告起算）。
- config：新建 `cfg_streamguard/`（=cfg_zeta_cauchy 三件逐位复制+3 新键），cfg_zeta_cauchy 冻结不动。
- 判读脚本资产：t2_jump_timeline.py（双流帧跳扫描，本会话已入册）。

## 4. 验证判据（冻结）

**轮型**（全 3090，栈=新栈，config=cfg_streamguard）：
- X1prime 型 ×2（obstacles，goal 7,-4,1，budget 180，紧凑）
- route 型 ×2（obstacles，goal 7,-4,1 --leg2 0,0,1，budget 240，紧凑）
- 零回归带：hover 型 ×1（goal 0,0,1 budget 60）+ ground 型 ×1（不起飞，preflight 后即收）

**主判（过=修复验证通过）**：
1. **风暴轮（发生 [T2fail] 的轮）恢复重锚跳消灭**：帧跳扫描（t2_jump_timeline.py，双流）单帧 |ΔP| 最大值 ≤0.5m——基线 MACH1 单帧 293.7m；
2. **走爬投喂截停**：|V|>15 后 imu_propagate 无新帧（sane 门）→ 风暴窗内 >0.5m 跳变帧计数较基线（MACH1=525）**下降 ≥90%**（残余=|V| 越线前 ≤0.15s 窗 × |V|≤15 × 帧率 ≈ 上限 18 帧内小步（≤0.12m/帧@125Hz）——主判线 0.5m 上残余应为 0）；
3. **j0 jump 分量趋零**：净轮/风暴轮 j0_decomp（T3 工具 1f5a806d）jump_m ≤0.10m（基线带：BL5 0.018 健康/MACH8 0.52）。
4. **正常域零回归（运营带宽）**：hover j0 ≤0.35（历史带 0.090-0.341）；ground=0 [T2fail]+init 正常；route/X1prime 干净轮 j0 与 0.664 基线差 ≤0.15m；[T2GATECFG] 四行 banner 逐字段不变+[T2gate] 触发行为不变（判读器消费面零扰动）。
5. **净窗顺带**：任一轮 j0<0.5 ∧ 0 [T2fail] → 即时 STATUS 通告 @T1（净窗三合一）。

**失败分支（预写）**：主判 1/2 未过→恢复逻辑再取证（缺口检测时刻/偏移应用路径）；3 未过而 1/2 过→j0d 口径对账 @T3；4 未过→组件 C 关闭重验（单变量回退：guard 保留 A/B/D 关 C 的键 `t2_sg_uls`，若预写）——**禁门值动作**。
**连续 2 轮同因 harness 崩→停跑转分析**（沿纪律）。

## 5. 基线（在册+本会话重测口径统一）

| 指标 | 基线值 | 来源 |
|---|---|---|
| 恢复重锚跳单帧 | 293.7m | MACH1（任务书+本会话袋级复测） |
| 风暴窗 prop 跳变帧(>0.5m) | 525 | MACH1 t2_jump_timeline.py |
| 2.6m 族跳幅 | 2.45-2.60m | T1 四例+X1prime 2.594（在册） |
| j0d jump_m 健康带 | 0.018（BL5）/0.0076（MACH3） | T3 j0d 在册 |
| hover j0 带 | 0.090-0.341 | M0/135108/134845 |
| X1prime 干净 j0 | 0.664 | BL5 |

## prereg_reanchor_fix 附录 A — v1 验证失败分支执行与 v2 设计（2026-10-05 12:5x；判据零变动）

**v1 战果（RA1-RA4，栈 ed4b8181/acd9ba78）**：RA5 hover 零回归 PASS（j0=0.232 带内+四冻结 banner 不变）；RA1/RA2 静默带（0fail×j0 4.08/3.83，无重锚事件=修复无作功面）；**RA3 route 主判未过**（预注册失败分支命中）：2×[T2fail]+2×[T2RESUME]（gap 43.0/39.0s，dP 49.98/52.43m，frames 125/132）后，init-finish 时刻发布流仍录得 284m 级单帧步（odom 55 帧 big>2m/prop 408 帧）。

**根因（袋级原始 P 序列取证）**：发布 P 在 init-finish 起自 −1037.85 以恒定 12.2m/帧矢量推进——**ULS 捕获（组件 C）在 reboot 后收敛期把解间大摆动当重锚 δ 补偿**（shadow=旧发散链 vs latest=新解 → 每捕获注入巨量偏移），发布 P=latest+毒偏移被拖回老风暴帧；且发布门只查 raw latest（新解本身 |V|<15 健康）漏过偏移毒值。温和走爬（|V|<15 段）累计 ~50m 漂移被放行 25s 为 dP 50m 的来源（v1 预判"≤0.15s 窗"错误）。

**v2 修复（预注册失败分支"恢复逻辑再取证"的执行；判据/门值零变动）**：
1. **沉降窗 hold**（POST_INIT_SETTLE=2.0s）：t2_pub_had 时 init-finish 后 2s 内停发（首 init 不 hold=legacy 时序不变）；
2. **捕获窗停用**：同一沉降窗内 ULS 捕获 skip+计数（防收敛期野 δ 入平滑器）；
3. **init 时平滑器复位**：updateLatestStates(true) 内 reanchor_smoother.reset()（陈旧偏移清零，resume 重算）；
4. **发布值域门**：guard 分支对 P_pub/V_pub（含偏移）做 sane 域复检，越界停发不 step 不更新 last_pub（防任何残余偏移毒性出门）。
gtest 增例：settle 窗谓词/发布值域门谓词。判据=prereg §4 原文（主判 1/2/3/4+净窗）不变；v2 验证轮=RA7-RA10（X1prime×2+route×2）。
