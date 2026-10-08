# 新轮滚入扩切口落账（T3 v10.9 单元2a，2026-10-09）

> 任务书单元2 "全部新轮滚动入组合矩阵+j0d 表+加性校验"执行件。判读域全库口径。
> 滚入面=2026-10-08 02:23（combo_20261008 生成时点）之后落盘的全部 smoke 轮。

## 1. 滚入清单（+100 轮入 combo；81 轮有袋入 j0d）

| 家族 | 轮数 | 归属/说明 |
|---|---|---|
| DRILLD1_N8P（夜 2d HAFIX 批+D5_L2） | 27 | T1 night_chain 2d 批 20 轮（场景重判读=t2d_hafix_rejudge）+晨间补采+D5_L2 |
| M3pv2 / M3pbase | 26+18 | T2 M3prime 批（REGEN v2 臂+base 臂） |
| WU（预热对照批）+WU1b | 16 | T1 1c 预热批 8 对+1b 验证轮（统计面=warmup_greenrate 表） |
| 1aO/1aP | 11 | T2 v10.4 observe 采样轮 |
| 排除面（STARVE*/REGCHK*） | 11 | 生成器既定排除（非科学样本），不滚入 |

## 2. combo_matrix 250→350（combo_matrix_20261009）

- 加性校验：**old=250 new=350 added=100 missing=0**；
- **文档化例外 6 处（两类，均有 mtime 证据，零既有值改）**：
  1. **补全型×5**（run_M3RE12O_2_164230 的 j0d_jump/j0d_transit/j0d_dom/njf/wa_verdict 空→值）：
     其 wa_gate_online.json 写入于 10-08 02:31:14（v10.6 判读链产物），晚于 02:23:33 的
     旧表生成时点——属 v10.6 补全事件的迟到面，值源=同判读链非新判（沿 v10.6 补全型先例）。
  2. **外科恢复×3**（run_X4_E12O_031818 的 j0d_jump/j0d_transit/j0d_dom 值→空→恢复旧值）：
     该轮 wa_gate_online.json 于 10-08 02:30 被背书重跑器冒烟测试覆写（bag 已处置[五绿轮
     已知边界]→内嵌 decomp 降级 available=False）；20261009 首跑现"值→空"回归=HALT 拦截，
     处置=从 20261008 表恢复三字段（旧表值=覆写前正源判读，零重判纪律维持）。
- 其余 X4 五绿轮 json 核验：未覆写（mtime=10-07 原版，avail=True）。

## 3. j0d_stats 205→286（j0d_stats_20261009b；20261009=单元1 收敛见证件不覆写）

- j0-decomp 批跑：81 袋 17.9GB（nice 19/ionice idle 避让在途 B/C 回放批）81/81 完成；
- 生成：v2.1 自动联表 combo_20261009；
- 加性校验 vs 收敛见证件（j0d_stats_20261009，205 轮）：**old=205 new=286 added=81
  missing=0 drifted=0 → PASS-纯加性 RC=0**；
- 新 81 轮分类：净轮=55，中漂移=21，风暴=5；
- 总数 **286：净轮=111，风暴=91，中漂移=84**。

## 4. 判读支持件（单元 2 其余交付，同日落盘）

- warmup_greenrate_batch1_v1131_20261009：预热第一批统计面（A 0/8 vs B 4/8=−50pp，
  方向 0/8 → NOT-EFFECTIVE 与 T1 同判；bias 收敛列 8/8 NOT-CONVERGED，复验批到货重跑）；
- three_arm_verdict_view_20261009：三臂终判判读面 v1.0（双口径列；A 臂 strong=0/weak=12/
  noop=12 与 T1 1d 判决逐位同判；B/C 恢复批 CSV 到货自动并入重跑）；
- t2d_hafix_rejudge_20261009：2d HAFIX 批统一重判读（C-9 销号；summary.txt 场景映射 20/20；
  预注册判据下 4/20 轮 PASS、零场景 5/5 → 批 NOT-PASS；7 轮 ENV-FAIL 无判读面如实分栏）；
- t2d_j0d_family_20261009：2d 轮 j0d 分型×悬停谱系同族性（有跳变病理的 5 轮全=transit
  慢淋主导族=**与 sim 悬停自跳同族**；净轮 9=odom 死亡≠跳变病理）。

## 5. 口径边界登记（3ARM 回放轮不滚入 combo/j0d 的理由）

- 3ARM_*（HOME t3_results 36+ 轮）=回放分析产物（无 /gazebo/model_states truth）：
  j0d 冻结口径下 available=False；combo 键=smoke run（材料轮 run_X4_1e_E8P_035301 已在册）。
  其判读面=three_arm_verdict_view 独立表（本日 v1.0）——预注册口径不静默改（扩切口纪律）。
