# R3x 终章判读 预注册 v1（B 题定量收口件）

- 登记：T1 / 2026-10-04 20:0x / 任务书 v11.2 单元 7
- 性质：判读预注册（先于统计）；本件=描述性定量收口，无 PASS/FAIL 门（红线遵守——不出未预注册门）。

## 1. 素材与现状（清点）

- 探针数据轮（r3x_probe.jsonl 非空）：
  - run_F3B9_094909（NEVER-FLEW 边缘 z=0.2955=敌对边缘型；139 行=任务书"139 行已采"）
  - run_F3B10_154733（敌对·z 高估弹道）
  - run_F3B11_155643（敌对·平线）
  - run_F3B12_160420（敌对·原点漂移）
  - run_F3B13_161000（敌对·平线）
  - run_F3B14_163613（敌对·巡航帧跳）
- **净轮探针样本=0**（唯晨间全净轮 F3B8 探针 118B 阵亡于坑三；F3B2-7 未接探针）。
- 队列深面（[R3xQ] 进程内）未飞验——三面中 face2 缺席。

## 2. 聚合口径（冻结）

- 窗=各轮 armed 窗（/mavros/state bag 时；探针 t_wall 不可回溯对齐 bag 时——**注记：探针记录为墙钟+ros 时双戳，armed 窗以 ros 时近似袋 sim 时**；无 arm 的轮（NEVER-FLEW）取全程）。
- 每轮每面聚合：
  - imu_jit：p50/p95/p99/max（ms）、drop_n、spike_n、spike_max
  - stampage：odometry/imu_propagate p50/p95/max（ms）
  - rtf：rtf_1s 的 min/median；sim_lag_s max
  - cpu：cpu_pct median/max；rss_mb max
- 轮间散布（"时序彩票"量化）：每特征散布系数 sc=(max−min)/median（跨 6 轮）。

## 3. 判读规则（冻结，描述性）

- **稳定带结论**：全部主特征（imu_jit p50/p95/p99、stampage odom p50、rtf_1s median）sc ≤ 0.30 → "敌对轮三面稳定带成立：可观测时序面不解释轮间彩票"（B 题从定性变数字的收口形态一）。
- **高散布旗**：任一主特征 sc > 1.0 → 该面标"高散布候选"，附轮值表（收口形态二：彩票与该面相关需净侧样本检验）。
- 其余 → 带状如实报（中间态）。
- 净侧=0 样本：终章判读附"净侧空缺"注记；解锁=并轮轮探针随轮采集（W-F 联动）。
- 队列深面缺席注记；[R3xQ] 飞验轮补 face2 后可出增补版（v1.x 追加）。

## 4. 产物

- 工具=analysis/r3x_final.py；产物=t1_evidence/v10_2026-10-02/r3x_final_result.json + r3x_final_verdict.md。
