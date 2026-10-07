# REGEN-PREREG v2.0 — 全域单阈参数集预注册冻结件

> 任务书：2026-10-07_T2_vins_quality_v10.4.md 单元 2。**双必达件之二**。
> 规则层正源=regen_v2/REGEN_PREREG_v2_template.md（本地起草版）+1a 方法论 v1（含附注 A1 入池口径修正）。
> **数据基础**：1a 采样批 2026-10-08 02:36-03:32（10 轮，22971 帧 METRIC，observe 模式零拒帧）+补采第 5 obstacles 轮（本件 §5 复核条款）。
> 依据链：模板 §1/§2 规则冻结 → 采样数据 → 本件填数（机械执行）。

## 1. 语义冻结（填数版）

- **域语义=全域单阈**（分带被数据否决——见 §3 重大发现）。无 unseen-domain 回退需求（无域分支）。
- 门行为：stereo_r 按 [L,U] 带拒收；corners 下界拒收（保持 v1.1 值）；depth_r 下界拒收（保持 v1.1 值）；max_depth=100m 不变；staged 宽限+fail-open 机制不变（max_consec=30 原值）。
- **模板"禁回退单域全局阈"条款失效**——因 v2 本身即全域阈（语义上无分域可回退）。

## 2. 参数集 v2.0（冻结数字）

```yaml
domains:
  global:                      # 全域单阈（分域否决后唯一域）
    stereo_r: {L: 0.095, U: 0.895, p5: 0.150, p25: 0.700, p50: 0.780, p75: 0.810, p95: 0.840, n_frames: 22971}
    corners:  {L: 80,    U: null, note: "退化常数分布(p5=min=150 配额饱和,IQR=0)——分位公式失效,保守保持 v1.1 值;min=41 帧在阈下=v1.1 行为不变"}
    depth_r:  {L: 0.5,   U: null, note: "全池常数 1.0(min=1.0,零变异)——键无信息量,保持 v1.1 值"}
sample_basis:
  plain_runs:      [1aP1_N8P(FAIL/VINS-clean), 1aP2_N8Pr(PASS), 1aP3_S12P(FAIL/VINS-clean), 1aP4_W5P(FAIL/VINS-clean), 1aP5_S8P(PASS)]
  obstacles_runs:  [1aO1_E12O(PASS), 1aO3_S8O(FAIL/VINS-clean), 1aO4_E8O(PASS), 1aO5_NE12O(PASS), 1aO6_E8O(补采,§5)]
  excluded:        [1aO2_NE8O(T2fail=1 病轮, A1 口径剔除)]
sampler: t2_metric_extract.py + 分位脚本（/tmp/t2_1a_metrics.csv 正源,池刷新后 sha256 见附表）
```

推导（模板 §2 公式机械执行）：stereo_r 全域池化 p5=0.150/IQR=0.110 → L=0.150−0.5×0.110=**0.095**；p95=0.840 → U=0.840+0.5×0.110=**0.895**。**不四舍五入**（防事后凑整嫌疑）。

## 3. 重大发现（数据否决预设假说,如实入册）

1. **两域输入分布几乎重合**：stereo_r p50 plain 0.780 vs obstacles 0.770（diff 0.010 << max IQR 0.120）；最小分离度检查 FAIL → 按冻结规则退全域单阈。
2. **M3 v1.1"场景依赖"归因勘误**：v1.1 时代的 plain 0.16-0.28 vs obstacles 0.05-0.08 带差=**门拒帧-饥饿反馈循环的产物**（observe 零拒帧条件下消失）——非纯场景输入差。此发现修正 M3 定案的场景依赖归因。
3. **v1.1 阈 0.10 与健康带推导 L=0.095 几乎重合**：阈值本身不是 v1.1 失败主因；fail-open（0.3Hz 馈电）反馈循环才是（0.8% 健康帧在 0.10 阈下被拒 → 拒帧 → 特征饥饿 → 配对率再掉 → 循环放大）。
4. corners/depth_r 健康分布退化（饱和/常数）——两键在健康域零判别信息。

## 4. M3' 批预注册（判据冻结）

- 名册=六格×3 轮（v1 冻结样本设计同）；臂=v2（本件参数,gate=1）vs base（gate=0,T2_VINS_CONFIG unset）；批脚本臂序固定 base→v2。
- **基线口径**=史绿率（E8P 0%/S12P 0%/S8O 0% + E12O 100%/NE8O 100%/N8P 100%,REGEN v1.1 冻结数字,m3_analyze.py BASE 表）。
- **成功语义**：3 绿格组绿率相对基线降 ≤10pp 且 3 毒格跳变复现率不升。
- **失败语义（预期分支,预注册）**：
  - 若 N8P 复现饥饿（绿格崩）→ **定案：输入质量门参数化路线整体证伪**（参数空间已被 1a 健康带钉死：L 不可低于健康 p5 缓冲、不可高于拒健康帧——无自由度）→ 修复面正式转"拒帧反馈循环打破"（fail-open 加速/拒帧退避/弃门转 1c 输入编辑）。此为有价值的正式定案非虚账。
  - 放病理（毒格假绿升）→ 同上回滚+登记。
- 执行：t2_m3p_v2.sh（臂 config 由 gate yaml 机械生成,v2 臂 config md5 落 regen_v2/）；STATUS 预告+与他线飞行窗错峰。
- 注记：vins_smoke.sh 的 vins_config.md5 落盘仍记录默认 config——v2 臂轮的权威 config md5=t2_results/INPUTFACE/regen_v2/v2_arm_config.md5（批脚本双落）。

## 5. 补采复核条款（obstacles 第 5 轮）

- 1aO6_E8O 补采（T1 HAFIX 窗后执行）入池后重算全域分位带：若 stereo_r p5/p95 变化 ≤0.01 → v2.0 冻结生效（本件时间戳补登）；若 >0.01 → 升 v2.1 复核（新 prereg 条目,不静默改数）。
- **冻结生效条件=本条款复核 PASS。**（时间戳：待补采后定）

## 附表

- [x] stereo_r 全域带：p5=0.150 p25=0.700 p50=0.780 p75=0.810 p95=0.840（n=22971）
- [x] 两域分位带（否决分域的证据）：plain p50=0.780 / obstacles p50=0.770
- [x] v1 基线六格史绿率：见 §4
- [ ] 冻结时间戳+池 sha256（补采复核后）

## 冻结生效登记（2026-10-08 04:1x）

- 补采 1aO6_E8O_040815：PASS，A1 入池 True（j0=0.116/T2fail=0/pmax=9.21），METRIC 1146 帧。
- 刷新池 n=24117：p5=0.150（delta 0.000）p95=0.840（delta 0.000）——**复核条款 PASS，v2.0 生效**。
- 生效参数（草案字面）：**stereo_r L=0.095 / U=0.895**（n=22971 基准）。一致性附注：刷新池 IQR 0.110→0.120 使 L=0.090/U=0.900——差异 0.005，不触发 v2.1（条款只锚 p5/p95）。
- 池正源 sha256=6fdfee63ed6bf687（/tmp/t2_1a_metrics.csv,24117 帧,11 轮入池 10/11 剔 1）。
- **FROZEN：2026-10-08 04:15 本地时间。跑后禁改；M3prime 判据即本件 §4。**
