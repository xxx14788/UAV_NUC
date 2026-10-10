# bias 路线整体证伪定案文书 v1.0（2026-10-10 13:5x——任务书 v10.10 单元 3 第三分支）

预注册链：bias_constraint2_design_v1.md（c16f59c1）→box_arm_batch_prereg_v1010.md
（16960eb5 含补条 A/B）→box_arm_verdict_v1.md（2db067fb，②a 判负）→
tlock_arm_batch_prereg_v1010.md（1824df1f）→本件。判据全程零变动。

## 1. ②b 批判读（2026-10-10 12:23-13:40，8/8 对完整 16 轮）

**NOT-EFFECTIVE**：A(tlock W=10) 绿率 25.0% vs B(base) 25.0%，差 **+0.0pp**；
方向一致（单绿对）**0/8**（双绿 2 对：E12O/NE8O；双败 6 对）。

格级（正源 tlock_pairs_v1010.csv；banner 列 join 修复 8×A=1/8×B=0——批脚本
grep 模式 sed 转义坑=纯记录缺陷已修，臂身份 env 通路 8/8 banner 自证）：

| 格 | A:vd/jump/arrive | B:vd/jump/arrive | dbadt A<B |
|---|---|---|---|
| E12O | PASS/0.179/0.269 | PASS/0.101/0.087 | yes |
| E12P | FAIL/NA/NA | FAIL/NA/NA | yes |
| E8P | FAIL/NA/NA | FAIL/NA/NA | yes |
| N8P | FAIL/0.098/7.914 | FAIL/1.264/0.047 | yes |
| NE8O | PASS/0.034/0.081 | PASS/0.159/0.161 | yes |
| S12P | FAIL/0.142/11.245 | FAIL/3.885/0.206 | yes |
| S8O | FAIL/2.691/4.877 | FAIL/4.118/7.278 | yes |
| S8P | FAIL/0.691/7.244 | FAIL/1.475/5.639 | yes |

- 层② 机制面：**transit dbadt A<B 8/8+jump A<B 5/6**——温和锁把漂移指标全面
  治好（与 ②a 同向但无自伤）。
- 层① 适用性注记：indom>95% 仅 5/8（E8P 72.2/E12P 61.3/S8P 0.5）——tlock 语义
  =窗锁非全程硬界，窗后/init 段自由漂属设计语义；全程 indom 对 ②b 是不适用
  指标（②a 专属），窗内偏差约束由 ENGAGE/RELEASE banner+dbadt 8/8 承证。
- 夜态漂移注记：②b 批 B 臂绿率 25%（②a 批同批式 B 臂 75%）——批间夜态漂移
  显著（S8O B：②a 0.160 PASS→②b 4.118 FAIL）；同批 A/B 配对内对照不受影响
  （同夜同栈），跨批判读以配对差为准。

## 2. bias 路线三件套终局（两批合并证据链）

| 修复面 | 案 | 结果 | 夜 |
|---|---|---|---|
| ①激励（FEED） | 预热段喂 bias 激励 | **证伪**（NO_VALID_CARRIER） | 10-08 |
| ①激励（WARMUP） | 预热对照批 8/8 对 | **NOT-EFFECTIVE**（-37.5pp，预热自伤） | 10-09 |
| ②a 硬界 | box ±0.5/±0.05 全程 | **NOT-EFFECTIVE（-62.5pp，过紧型自伤：box 生效 8/8+慢淋被治 7/8+绿率反降=误差转移进位姿）** | 10-10 |
| ②b 温和锁 | transit 相对锁 W=10 | **NOT-EFFECTIVE（+0.0pp 方向 0/8；机制面全治：dbadt 8/8+jump 5/6）** | 10-10 |

**定案**：bias 路线整体证伪——
1. **约束漂移本身可治**（两案的机制面指标全治）；
2. **但绿率对 bias 约束无响应**（硬界自伤/温和锁无效——两案夹逼出结论：SITL 域
   绿率主导路径不在 bias 漂移面）；
3. 与 10-09 归因收敛（渲染时戳域病理+输入质量门证伪+预热证伪）互洽：SITL 域
   在线跳变族=渲染时戳域病理，bias 面非主导。
4. 实机适用性边界（设计件 §3.4 沿袭）：SITL 结论=该域内 bias 约束不修复绿率；
   实机真温漂场景 box/锁的工程价值**未被本定案否定**（实机域真绿率度量=终局
   三件之一，另窗执行）。

## 3. 绿率修复面收敛定案（用户裁定路线的落地态）

- **选格收窄**：健康格带（plain A 型+gyr≥2.5 带）绿率 70.5%（10-07 门科学包
  定案）=当前可用绿率面。
- **止损件兜底**：jump 后置止损件 v1.0 在库（7-8 定位率）——真 FAIL 提前终止
  形态已入 trichotomy。
- **架构级 transit 地板注记**：transit 主导族（j0_decomp BL5=98% 地板实证）=
  架构级地板（回环不接入裁定维持——用户 10-04 裁定）。
- bias 路线关闭后 SITL 域无在册未试修复面（穷尽制清账：FEED✗/预热✗/box✗/
  tlock✗/门参数化✗[10-08]/选格✓[非修复=规避]/止损✓[兜底]）。

## 4. W 梯度未消费注记（诚实账）

W∈{5,20} 扫未跑：②b W=10 判据面 +0.0pp+方向 0/8——梯度扫描在"机制面已全治
而绿率零响应"的证据下无信息增益（扫更弱/更强的锁不改变"绿率不响应 bias 约束"
结论）；判据面止损，如实进《可做而未做清单》（复审条件=实机域真温漂场景开启）。

## 5. X7 收敛声明素材增补（@T3）

X7 素材包（x7_convergence_material_v1010.md f4b21500）§5 增补一条：
"bias 路线四案终局（FEED✗/预热✗/box✗/tlock✗，2026-10-10 双批 8/8+8/8 对
完整判负）——SITL 域绿率对 bias 约束无响应（机制面可治+绿率不动夹逼定论），
归因线收敛声明（渲染时戳域病理定性）获第四支柱"。文书=本件；git 落库。

## 6. 产物清单

- tlock_pairs_v1010.csv（+bak_banner_fix）——②b 批正源
- box_pairs_v1010.csv——②a 批正源
- box_arm_verdict_v1.md（2db067fb）+本件
- 代码：t2_bias_box.h（②a+②b 谓词）+estimator.cpp L1429 盒界+L1511 区
  transit 锁+parameters 三键（t2_bias_box/t2_bias_tlock/t2_bias_tlock_w 全
  默认 0/10=legacy 逐位同）+gtest 7/7
- 工具：t2_box_diag.py/t2_box_pair_verdict.py/t2_tlock_pair_verdict.py/
  t2_bc_alive_join.py+批脚本两件
