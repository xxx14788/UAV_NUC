# 预注册：odometry 重燃（X 线触发器 ζ）修复——伪深因子排除 t2_pseudo_drop（2026-10-04 v1）

> T2 v8.9 任务书自演进单元（治理条款：追加新单元须 DECISION_LOG 登记+STATUS 通告）。先于一切验证数据冻结。
> 触发=T3 04:33/09:58 在册：X 线唯一堵点=T2 odometry 重燃（2.6m 跳变假常量，X1prime 到位定责，宽判 6 例）；T3 轮询等待本线修复通告。
> 栈基线=fixface-3（lib e7044319/node 08a46d0a，gates config 含案A staged=1/n=80）。

## 机理（四证链，2026-10-04 12:1x-12:3x 取证，素材=run_X1final_040643 袋+log）

1. **e(t) 剖面**：出生锚定误差 t=0-30s ≈0.03m（悬停完美）→ t=35-40s（transit 加速段）离散跳变簇（单步 0.84-3.07m，误差向量摆动 2.5→5.4→2.6m）→ **2.56m 偏移冻结 120s**（变化<2cm）——非平滑尺度型、非单帧重锚型。
2. **估计器自画像（T2diag bag 60.5-62.9）**：P 在两解带逐帧翻转（y: -1.0..-1.5 ↔ -2.3..-2.6；x: 3.1↔4.6）=**双稳态**；V 同步震荡。
3. **跟踪饥饿**：翻转窗 [T2diag] track=9-33（悬停带 120-140）。
4. **伪深喂料剂量**：transit 期 [T2gate] init_replace=5-40/帧（ir_st 1-16+ir_m2 0-30；悬停 0-6）——INIT_DEPTH=5.0 假深以**满权重**进投影因子。
5. **剂量-响应**：A1/A2（route goal 4.2m 温和 transit，同在恩典窗内）同病轻症（end 误差 0.62-0.98m，步幅 0.2-0.5m）；X1prime（goal 8.6m 激烈 transit）重症 2.56m——"2.6m 假常量"=同 goal 剂量带，非魔数。
6. **案A 盲区**：X1prime transit 在恩典窗内（init bag≈26+80s=106 > 爆簇 60-64）——案A 稳态拒收不覆盖；且案A 恩典窗设计本就为保再 init 的 Bgs 解（不能简单缩短）。

**机理链**：激烈 transit → 双目匹配几何性失败（负深→伪深注入 10-40/帧满权重）+ LK 跟踪退化 → 视觉约束=假深主导×欠定 → 优化器在假深极小值与 IMU 先验极小值间双稳态翻转 → 运动结束 track 恢复后锁进错解（-2.6m）→ 边缘化先验冻结=**odom 帧一次性重燃偏移**。与 R3"吸引子"、悬案池"双稳态（降级）"同族复活。

## 修复设计（单变量）

- **t2_pseudo_drop**（int，默认 0=关=逐位不变）：NON_LINEAR 解算的投影因子构造中**排除伪深特征**（estimated_depth 来自 INIT_DEPTH 注入路径者）——不删 track（防 depth-gate 活锁教训的饥饿螺旋：跟踪继续、几何质量保留在窗口，仅假测量不入解）；INITIAL 期完全不动（恩典窗语义保留：solveGyroscopeBias 特征量保底）。
- 伪深标记：FeaturePerId 增 t2_pseudo 旗，三注入点置位（stereo init_neg/motion2 init_neg/svd<0.1），真深清位。
- 边缘化构造同条件排除（先验一致性）。
- 自证：新独立 banner 行 **[T2PDROPCFG] pd=%d**（启动+setParameter 复打；冻结行 [T2GATECFG]/[T2gate]/cost 触发/[T2RFIXCFG] 零改动）。
- 与案A 关系：互补不互斥——案A=稳态（恩典窗外）整 track 擦除（含后续帧）；pseudo_drop=全 NON_LINEAR 期仅当前解算排除（含恩典窗内 transit）。双开时 pseudo_drop 覆盖恩典窗盲区。

## 验证判据（预注册，禁事后改；生死=在线，回放=机制探针）

**V0 机制预验证（回放 A/B，写码前，用既有旋钮）**：X1prime 袋 × staged_n_sec:0（transit 期拒收激活）vs 基线 staged_n_sec:80。判读=odom 流翻转签名（P 双解带逐帧翻转计数）与出生-末端漂移。预期：拒收激活→翻转显著减弱/漂移下降=伪深驱动证实。若**无改善**→机理证伪，停写码转分析（禁盲试）。

**V1 回放 A/B（写码后）**：X1prime 袋 × {pseudo_drop:0, pseudo_drop:1}（staged_n_sec 恒 80 单变量）。判读同 V0 + 末段 60s |P|p50 健康性。改善方向成立→V2。

**V2 在线验证轮（生死）**：X1prime 型（obstacles world，goal 7,-4,1，budget 180）×2 起 + hover ×1 + ground ×1（健康回归）。
- **主判**：≥1/2 X1prime 型轮 **j0（出生-末端锚差）< 0.5m**（T3 round_result 恒门口径）且无 [T2fail]。
- 次判：①另一轮 j0 显著下降（<1.5m）或同过 0.5；②hover/ground 零 fail 零回归（健康带内）；③到位读数并记（预期修复→anchor 持稳→到位读数反映真实精度 0.6-1.0 带）。
- 双 md5 每轮+[T2PDROPCFG] banner 核验+紧凑袋归档。

**通过→STATUS 通告 @T3（触发器 ζ 解除语义=修复验证通过通告）+@T1（D2/P1 域）+@T4**；未达→自主开假设表（候选：饥饿窗 IMU 权重提升/特征端 max_cnt-LK 金字塔强化），判据门值禁放宽。

## 边界

- 判据/门值放宽永禁；V0 无改善=停手不写码（反盲试）。
- X1prime 型在线轮与 T1 飞窗互斥（锁纪律）；build 窗 STATUS 预告 15min 异议窗。
- 回放判读只作机制探针；j0<0.5 的生死判定只认在线（红线 11 同源纪律：回放非确定域不判生死）。
