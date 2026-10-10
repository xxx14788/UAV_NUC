# 扩表台账 20261010（T3 v11.1 单元 1e：combo 350→412 滚入+加性校验+外科恢复重放）

## 1. combo_matrix_20261009(350) → 20261010(412)

- 触发=②a box 臂批 16 轮（06:41 毕）+近 24h 四线新轮全库吸收。
- **added=62**（批构成：BX 20[16 批轮+DRY2+E8P_B 被替原轮]/WU2 17[10-09 晨迟到面，
  上次重生成在其落地前]/TK 13[T2 IQG 批 10-09 午后]/DRILLD1 6[T1 v11.39 前置干测
  10-10 晨]/A1OBS 4/WU 2）——missing=0。
- **加性校验=drifted_cells=0**（旧 350 轮逐位零漂移；工具=逐轮逐列 set 比对）。
- **文档化例外重放 1 处=外科恢复×3**（run_X4_E12O_031818 j0d_jump/transit/dom）：
  与 expansion_20261009.md §2 例外 2 同源——该轮 wa_gate_online.json 被 10-08 02:30
  背书重跑器冒烟覆写（decomp 降级 available=False），首跑现"值→空"回归；处置=按
  v10.9 冻结纪律从 20261009 表恢复三字段（零重判维持；工具=
  t3_surgical_recovery_e12o.py，恢复后全表复验 drifted=0）。
- 锚点哨兵=新表消费门 PASS（combo 412 行 HVNET1 锚 3/3 中——哨兵实战首用例）。

## 2. j0d_stats_20261009b(286) → 20261010(286)

- 重生成（v2.1，combo 联表自动取 20261010）=**added=0/missing=0/drifted=0**。
- 客观注记：今晚 62 新轮（BX/TK/DRILLD1 等）轮目录均无 j0_decomp.json 产物
  （T2 批脚本与 T1 drill 变体 harness 均不产此件）——j0d 面吸收客观阻塞；
  新轮 j0d 权威通道=后续批补跑 j0-decomp（沿 v10.6 既有批跑链）。

## 3. 终次滚入（②b 批毕后，同日重生成 412→416）

- ②b tlock 臂批（TK 前缀 4 新轮+S8P 对等）吸收：**added=66**（BX 20/TK 17/WU2 17/
  DRILLD1 6/A1OBS 4/WU 2），drifted_cells=0，外科恢复×1 同款重放（E12O 三字段）。
- 同日重生成注记：20261010 表当日两代（412→416），均对冻结基 350 零漂移加性；
  哨兵门两代均 PASS。
- j0d 286 维持零漂移（TK/BX 批轮同无 j0_decomp 产物）。
