# w2b 双流扩展联测 预注册 v1（B 路 prop 流喂入）

- 登记：T1 / 2026-10-04 18:4x / 任务书 v11.2 单元 3
- 性质：判据预注册——先于任何联测统计落盘；未过门不出 PASS/FAIL。
- 背景：w2b 判别器双路——A 路 [W2BA]（Bgs 滑窗跑飞门，已在生产树默认 off；帧跳型 0 触发负结果在册）；**B 路=双流分离（本件）**：/vins_estimator/odometry 与 /vins_estimator/imu_propagate 的 z 分离判别（VR3"prop 谎报/odom 诚实"与 U25FIX"odom 钉死/prop 活"两形态的动机件）。

## 1. 检测器规格（冻结；离线实现=在线实现的逐语句参照）

- 流：z_o(t)=odometry.pose.z（解算流）；z_p(t)=imu_propagate.pose.z（传播流）。时戳=header.stamp；袋时兜底。
- **B1 值分离**：每个 odom 样本与最近 prop 样本配对（容差 0.5 s）；d=|z_o−z_p|；**alert 当 d>1.0 m 连续 ≥2 个 odom 样本**。
- **B2 率分离**：滑动判（逐 prop 样本时刻）：若该时刻前 2.0 s 内 odom 0 个新样本而 prop ≥5 个 → 计一拍 gap 拍；**alert 当 gap 拍连续 ≥2 s**。（健康基线：odom ≈1.8 Hz=间隔 0.55 s，2.0 s 阈=4× 余量。）
- 输出：alert 列表（type=B1/B2, t, d 或 gap 值）+ 全袋流率统计。
- 在线化（后续 build 窗）：同一逻辑进 VINS 进程（env `T1_W2BB`，默认 off，1 Hz printf [W2BB] banner），离线版先行标定与联测。

## 2. 联测素材（冻结）

四型代表袋（各 1 主 + 备份）：
| 型 | 主袋 | 备份 | 台账依据 |
|---|---|---|---|
| T1 z 高估弹道 | run_F3B10_154733 | run_T2ZETA2_132510 | 爬升期 VINS z 4× 高估→死亡→弹道 |
| T2 渲染前平线 | run_F3B11_155643 | run_F3B13_161000 | 起飞前平线至轮尾 |
| T3 原点漂移 | run_F3B12_160420 | — | anchor −258m runaway |
| T4 巡航帧跳 | run_F3B14_163613 | run_F3B6_093203 | 15.805m / 15.69m 帧跳 |

健康对照袋（≥4）：run_F3B2_024006（若在盘）/ run_F3B3_*/ run_F3B4_* / run_F3B8_094417 / run_WD1_024016 / run_X1final_040643——实际在盘者全跑，名单在结果 JSON 登记。

## 3. 联测判据（冻结）

- **过门 = 四型 4/4 主袋各 ≥1 alert（型内主袋；主袋无 alert 时允许备份袋顶替并注记）且 alert 落在该袋 armed 窗内 + 健康对照全袋 0 alert（B1 与 B2 皆零）。**
- 任一型无 alert = 该型未覆盖（如实报，不放宽阈值补检）；任健康袋 alert = 误报（如实报）。
- 判读语义：4/4+0 → B 路双流判别器联测过门，进 build 窗在线化；否则按型覆盖图如实收档（A 路 [W2BA] 帧跳型缺席已有先例，覆盖图=机理分型证据）。
- 附注（非门）：alert 时刻与台账已知腐坏时刻的重叠在判读文档人工对账。

## 4. 产物

- 工具：`sitl_sim/analysis/w2b_dual_offline.py`
- 结果：`t1_evidence/v10_2026-10-02/w2b_joint_result.json` + `w2b_joint_verdict.md`
- 环境：source /opt/ros/noetic；只读袋 0 锁；大袋（2.0G/5.5G）读仅过滤双话题；跑前查无在飞轮。
