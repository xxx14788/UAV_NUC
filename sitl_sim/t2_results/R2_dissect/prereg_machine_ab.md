# prereg_machine_ab — 敌对态机器层对照实验判据预注册（T2 v9.3 §1；2026-10-05 落盘）

> 任务书权威=Windows `plans/2026-10-05_T2_vins_quality_v9.3.md`。本预注册先于任何 3090 飞行轮落盘（前置验证 hover 轮除外——其目的=harness 适配验证，不入统计）。
> 判据逐字冻结：执行时禁改门值、禁事后分母调整。灰区分叉条款预写。

## 1. 假说（H-machine）

敌对态（Bas 爆型 z 腐坏：健康输入下进程内病灶，T2 v9.1 单元 4 定名）由旧 NUC 机器层不稳定触发。用户 2026-10-05 裁定执行域迁 3090 后，本实验为其猜想的正式检验。

## 2. 实验设计（与 NUC BL 系 12 轮基线对齐）

- **执行域**：3090（ghj@192.168.0.4），执行链=vins_smoke.sh（md5 5051224d 双副本一致）
- **构型**：X1prime 型 = world `sitl_world_obstacles`，goal (7,-4,1)，budget 180s，紧凑录制
- **配置**：cfg_zeta_cauchy（gates+cauchy 臂）= `~/sitl_sim/t2_results/R2_dissect/cfg_zeta_cauchy/`，**md5 与 NUC 副本逐位一致**（output_path 经 `/home/uav/vins_output` 目录创建适配，config 文件零改动）
- **栈**：W2BB 行为栈 = 3090 devel（vins_node 2ad9676e + libvins_lib 8c3453c0，Designer 2026-10-05 00:30 从 4dfec04 W2BB src 重建；行为≡NUC BL 系 W2BB eea4cb2e/9b88345b：zeta 双旋钮默认关+visualization.cpp 打印超集）。**每轮起飞前实读双 md5 登记**，偏离即停跑。
- **banner 四行核验**（每轮）：`T2 knobs: loss=1 cauchy=4.00 rejectF=0 ...`、`[T2GATECFG] cost_gate=1 ratio=10.0 n=5 win=20 | min_disparity=0 fardrop_min_near=30 depth_gate=0`、`[T2RFIXCFG] w4_bgs=0.5 staged=1 n=80.0`、`[T2PDROPCFG] pd=0 sf=0 sa=1.00`——与 NUC BL 系逐字段一致。
- **轮数**：连跑 12 轮（MACH1-12）。可选带图 2-3 轮（VINS_SMOKE_IMAGES=1，供 T4 判读/T1 图像面；带图不影响判读口径）。
- **同构性注记**：Gazebo Classic 11.15.1 双机一致（2026-10-05 实读）；ROS noetic 双机一致；硬件差异（28C/31G/RTX3090 vs 8C/16G/无独显）=实验变量本身，登记不修正。

## 3. NUC 基线（对照锚，2026-10-04 BL 系 12 轮，本会话从 3090 副本+NUC 归档重建）

| 轮 | T2fail | j0/形态 | 分类 |
|---|---|---|---|
| BL1 | 1 | never-flew z=0.1045 | 敌对 |
| BL2 | 12 | j0=417.63 | 敌对（风暴爆散） |
| BL3 | 1 | never-flew | 敌对 |
| BL4 | 14 | j0=116.22 | 敌对（风暴爆散） |
| BL5 | 0 | j0=0.664（到位 0.736） | **干净** |
| BL6 | 3 | never-flew | 敌对 |
| BL7 | 0 | j0=64.11 | 敌对（静默大发散） |
| BL8 | 3 | never-flew | 敌对 |
| BL9 | 0 | j0=7.76 | 敌对（静默大发散） |
| BL10 | 5 | j0≈20（flown，到位 8.12） | 非敌对（风暴 flown 单列） |
| BL11 | 2 | never-flew | 敌对 |
| BL12 | 3 | never-flew | 敌对 |

**NUC 敌对率 = 10/12 = 83%**。

## 4. 分类算法（客观，NUC 12 轮回放校验=83% 复现）

逐轮按序判定，命中即止：
1. **never-flew**：RESULT.txt 含 `never-flew 离地真值门` → **敌对**
2. **风暴爆散**：T2fail 计数 ≥10（simvins.log grep -c T2fail）→ **敌对**
3. **静默大发散**：T2fail=0 ∧ j0 ≥ 2.6m（j0=RESULT.txt anchor 行 `\|pre-post\|=` 值；2.6=未修剂量带上界，干净带 0.664-1.0 与之无重叠）→ **敌对**
4. **风暴 flown**（BL10 型）：T2fail 1-9 ∧ 离地飞完 → 非敌对（单列记录）
5. **干净**：其余（T2fail=0 ∧ j0<2.6m，含到位 FAIL 但帧稳定轮=BL5 型）

（T2fail 1-9 ∧ never-flew 已被规则 1 吸收。）

## 5. 主判（三档，分母恒 12）

3090 敌对轮数 X（分类见 §4）：
- **X ≤ 3（≤25%）→ H-machine 强支持（NUC 锅）**：敌对态归因机器层，NUC 退役飞行资格，X 线全链转 3090。
- **X ≥ 8（≥60%）→ H-machine 排除（病灶在软件）**：机器层入排除表第十项；Bas 全写点正面攻坚立即启动（任务书 §2-②）。
- **4 ≤ X ≤ 7（26-59%）→ 灰区**：加跑 6 轮（共 18）+双侧对照设计上报，不做单侧结论。

## 6. 次判

3090 干净轮（规则 5）j0 分布 vs NUC 单点 0.664：带位置/离散注记（附带读数，机器层对精度面影响；样本量小不做检验，只报分布）。

## 7. 纪律条款

- 连续 2 轮同因 harness 崩（非敌对形态：launch 坏/无 RESULT/FATAL）→ 停跑转修复，该两轮不入分母、补跑至 12。
- 判据门值放宽禁；灰区不做倾向性解读。
- 每轮归档：flight.bag/RESULT.txt/round.log/simvins.log（紧凑 ~20MB/轮）；带图轮如实标注。
- 台账逐轮登记：双 md5/banner 摘要/分类结果。
