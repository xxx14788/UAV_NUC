# 跳变族定因表初稿（T1 v11.20 单元4 机械腿产出；@T2 复核签认）

生成：2026-10-07 03:0x CST ｜ 出表线：T1（v11.18 1a-1d 解剖原作者，独立出表权在册）
数据：X5 批 47 轮随轮四件（PX4 dump/config md5/hwmon/goal_trace）+ flight.bag odom 重读
对照组（预注册，承 T2 v10.1 册）：巨跳 6 = N8O(5.49)/SE8O(5.58)/E5O(12.15)/E8P(30.42)/E5P(30.57)/E12P(35.97) vs 绿格 11；held-out 跳例 2（E8P_a 40.63/E8P_L2 25.99，不入门判）
判别门：先于看对账结果写定（t1_causation_legs.py 脚本头预注册），T2 签认权保留
原始数据：`causation/{leg1_px4,leg2_config,leg3_hwmon,leg4_rtf}.json + round_index.json + cost_curves/`

## 定因表（五大假设闭合）

| # | 假设 | 判决 | 证据行 |
|---|------|------|--------|
| H1 | config 漂移 | **排除** | 全 19 轮（6+11+2）vins_config.md5 同一=054ddc8d（批内零漂移）；当前仓库=5c98dc0d 系批后 canonical restore（v11.17 收官在册），非飞行窗写回，git log 可验 |
| H2 | PX4 参数写回 | **排除** | ①结构参数：绿格 11 轮 858 参数全一致（stable 集内零漂移），跳轮对绿格稳定集零偏离；②开机易变参数（CAL_/COM_FLIGHT/LND_FLIGHT_T_，共 14 个）绿格内本就逐 boot 变动=自动标定态非配置；跳轮出绿格界仅 3 例且 2 例仅越 ~3%（E5O MAG0_ZOFF 0.0500 vs 界 0.0487；E12P MAG0_XOFF 0.00752 vs 0.00731）；③机理阻断：VINS imu_topic=/mavros/imu/data_raw（原始流，不过 PX4 CAL 偏置），CAL_* 不入 VINS 输入 |
| H3 | 机器态（hwmon） | **排除** | 预注册门（freq<0.85×自身前段基线 ∧ ctxt/load>绿格同段 p75×1.5）0/6 跳轮过门；发作窗内 freq_avg/thm_flag/ctxt_rate/load1 中位全在绿格带内（leg3_hwmon.json green_window_stats） |
| H4 | 负载过载（RTF） | **排除** | 跳组 RTF 中位 1.017 vs 绿组 1.049（差<10pct 门内，绿组反高）；无任何轮 <0.80；slack=disarm↔bag_end 0-15s 未扣（两组同向、组间比较稳健）；连续 sim/wall 曲线历史轮未录=如实注记（X4 批已加 rtf 探针=前瞻面） |
| H5 | 估计器内部 或 输入面 | **存续（指向判决）** | L1-L4 全排除的合取；与 v11.18 解剖链一致：跳轮 t15 起 cost 3-8×（轮级前状态）+悬停型 \|Bas\|2.2× 先于 cost 平台 55s+z 塌落；上游 case2 表型吻合（sim 域候选维持） |

**闭合口径（T2 册同款）**：五大假设各有"排除（带证据行）或实锤"结论=闭合；全排除=合法闭合（收窄指向带图裁决），非失败。

## 交叉注记（诚实面）

- **分叉未汇流**：H5 内部"估计器内部 vs 输入面"两支未分离——X5 紧凑袋零图像（1e 不可行判决在册），输入面不可回验；分离面=X4 批带图 2 轮（本表附议 T2 册单元 4 启动件；VINS_SMOKE_IMAGES=1 通道现成，13.9G/轮预算 568G 盘内可容）。
- **t_jump 对齐口径差**（如实）：round_result "帧跳变"=odom-vs-truth 终态漂移口径（E12P 35.97≈final_drift 36.18 复核一致）；本表 bag 重读 max_step=单步最大（SE8O 单步 49.3>其 pre-post 5.58）。两口径窗口对齐差 30-60s 级——L3/L4 为负结果且机器指标全程无异常，窗口 slop 不翻转结论（slack-不敏感性）。
- **E8P_224044 RTF=None**：该轮 round.log 无"已 disarm"行（hostile 收尾路径），锚点缺如实登记。
- **前兆检测器粗版**：2×基线持续 5s 门在绿格亦触发（绿格 cost 峰比 10-104 瞬态）——证实"绝对比门不可直接用"，门阈值须 T2 科学包分阶段分位带（本表 side-finding，喂 T2 单元 2）。
- cost 峰比（跳轮 2.88-1010 / 绿格 10-104 重叠）→ 单一"峰值比"不具判别力；判别力在"平台持续性"（跳轮 sustained vs 绿格 transient），正是双门设计的自适应基线窗动机。

## 附：腿级原始结论

- L1 json：volatile_outlier 3 轮明细 + 绿格稳定参数 858 个
- L3 json：绿格参考窗分布 p25/50/75（freq/load/ctxt）+ 逐跳轮窗值
- L4 json：逐轮 RTF_global
- cost_curves/：19 轮 [T2slv] 全序列 TSV（t/phase/init_cost/final_cost/iters/slv_ms）

签认栏：T2 复核 ＿＿＿（回执=STATUS 行或 t2_experiments.md 引用行）
