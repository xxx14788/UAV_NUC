# 退役生成器归档（T3 v10.9 单元1：目录收敛+生成器消歧，2026-10-09）

## t3_j0d_stats_v1_retired.py（原 analysis/t3_j0d_stats.py）

- 产出：`t3_results/j0d_stats_20261006.{csv,txt}`（113 袋轮切口，v9.9 j0d 批时代）
- OUT 路径：repo 侧 `~/catkin_ws/sitl_sim/t3_results/`（本身正确）
- 退役原因：**双谱系病源**——与 v2（`t3_j0d_stats_v2.py`，OUT 曾硬编码 HOME 侧）并存且
  无版本自描述，同形异表两处落盘，导致 j0d_stats_20261007/08 需人工拷贝同步（两起实害
  见 v10.6/v10.7 坑账"双 t3_results 目录"）。2026-10-09 起统一由
  `analysis/t3_j0d_stats_v2.py`（v2.1：argparse 化+版本自描述+OUT 默认 repo 正源+
  combo 联表自动取最新）承担，v1 归档禁跑。
- 零漂移验证：v2.1 以 combo_matrix_20261008 联表重生成 20261009 表，对 20261008 表
  205 轮逐字段 expand_check=PASS-纯加性 drifted=0（验证链见
  `t3_results/dir_convergence_20261009.md`）。

## 纪律

- 禁止运行本目录内脚本产出新表；新表一律走 `analysis/t3_j0d_stats_v2.py`（v2.1+）。
- 旧表（20261006/07/08）冻结不动；扩切口=新日期戳全量重生成+加性校验。
