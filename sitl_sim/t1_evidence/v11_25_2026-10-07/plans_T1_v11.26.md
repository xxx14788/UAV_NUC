# T1 任务书 v11.26 — v11.25r2 完成清账版（2026-10-07 17:5x 落盘；v11.25 弃读）

> 你是 **T1**。执行域=3090（`ssh nuc2`）+实机 NUC（192.168.0.6）。台账=3090 `~/sitl_sim/t1_evidence/v11_25_2026-10-07/`+NUC 侧 `~/sitl_realmachine/`（**至今未建**，见 B.1）。
> 单线纪律不变：全域唯一执行册+代持清单入 DECISION_LOG；红线 1-24+等待协议 v2+默认案推进制；判据/门值零变动；大 IO 错峰自排。
> 本册性质=清账+移交：A=完成账（双线分列，证据锚全列）；B=剩余件；C=卡点客观陈述（**禁方案**）；D=资产 md5 表；E=等待登记。

## A. v11.25r2 完成清账

### A-0 共用段（双线协同）
- 双线并行执行：T1-A 线（14:06 开工）+T1-B 线（14:11 开工，14:14 分工握手固化：A=NUC 实机域/B=SITL 主线）。
- **阶段 0 config 双态收敛已执行**（T1-A 线，commit 6f20eef+D-1007-T1-03）：arm 态 054ddc8d 提交为 SITL 基线（用户裁定②注记），canonical 5c98dc0d 归档于 git 历史；此后 SITL config 正源=054ddc8d。

### A-B T1-B 线（SITL 主线，全账可证；commit 033ba71→cca3286→d6749e3 全推）
- **M2 写码窗（阶段 2，双必达之二）**：腿 B=帧级输入质量门 `t2_input_quality_gate`（三键 corners/depth_r/stereo_r+staging[init/宽限期全放行保 Bgs 解]+fail-open[连续拒 30 放一帧防门致盲飞]；默认关=零栈改动；gtest **7/7**；VINS 新栈 f622bae2/886b1e90）；腿 A=`t1_scene_gate.py`（S1 plain×{E,SE}/S2 gyr 双带/S3 供给双键；selftest **10/10**；S12P 史轮三键不命中=分门非全捕如实注记）；REGEN-PREREG **v1 冻结→v1.1 批前校准**（stereo_r 0.3→0.10；证据=烟测 B 587 帧实测健康带 p5=0.16/p95=0.28，原阈拒 95% 健康帧）；双烟测=A(gate off)健康运行+B(gate on)活性。
- **注入演练五案（阶段 4a，双必达之一；判据=drill_prereg_v1 先冻结）**：D2=PASS 教科书（+5m 注入→止损即时 jump_m=5.0 逐位→17s disarm=1；**止损件在线首验销账**）；D3=PASS（断流 30s 无失控 |v|1.09<1.5；恢复跳捕获→kill S3；DEGRADED 注记）；D4=PASS（planner 冻结 60s 轮仍绿收=F1 修复实证）；**D1=FAIL/不安全**（杀 VINS→盲飞过冲悬停 z=2.43+disarm=0=H-A 炸机路径活体实证）；**D5=FAIL**（监控 v0 三缺陷：起飞段 V/D 阈假阳+一次性告警聋+双发布器交错把慢漂转译为止损跳变）。附 D0 对照轮（PASS）+D1-boot 变体（init 门 300s 兜底零飞行）。报告=drill_report_v1（5ada1d4c）。工具三件=t1_inject_odom/t1_odom_monitor/t1_drill_run。
- **M3 绿率复测批（阶段 3；18 轮格级双列全数字）**：毒格组 Δ**+22.2pp**（S12P 0→33%/S8O 0→33%=史首绿；E8P 维持 0/3）vs 绿格组 Δ**-55.5pp**（组绿率 44.4%<60.5% 线）→ 按 REGEN v1.1 冻结失败语义=**腿 B v1.1 参数集证伪→config 回滚 054ddc8d（复验在案）**。机理钉死=双目配对率**场景依赖**（obstacles 域 stereo_r 健康带 p50=0.08 vs plain 0.16-0.28；N8P_2 253 拒+fail-open 0.3Hz 馈电→到位 8m 级失败）。修复链闭环标准兑现（18 轮数字+机理分布落盘=非虚账）。产物=m3_batch_report.csv+m3_celltable.md+regen_prereg_v1_frozen.md 终账节。
- **4b HAFIX 修复（D1 证据→落码→验证）**：px4ctrl odom 死亡看门梯（0b581422；watch 5s→AUTO_LAND 盲降→kill_s 15s→KILL[CommandLong 400]+disarm 兜底；**默认开**=实机红线姿态；参数缺席=默认无需 yaml）。**D1 复验 PASS**：watch t107.6→LAND t112.6→KILL t127.6→truth 末 **z=0.10 落地**（对照原 D1 盲飞悬停 z=2.43 永不落）。注记=kill≠disarm 缺口未全闭+盲降落点偏 goal ~2m。
- **4c/4d**：P3 计划内 reboot 通告契约**设计件 v1**（c9083356；生产侧 reboot_notify 话题/消费侧 max_recovery 窗+与 HAFIX 交互；代码面下册）；起飞前自检脚本 v0=`t1_preflight_check.py`（CAL 带外拒飞/odom 流活/电压/链路一键 go/no-go）。
- **阶段 5 尾件**：**口径 22 重建 v1**（D-1007-T1-04，用户授权语义：五绿轮袋可删/两 1e 标本+hover85 保全豁免）+**五绿轮袋处置已执行**（判读产物五目录全保留）；X5 59 轮判读联表=**C.10 销号**（j0d_stats v3：风暴 84/中漂 54/净轮 47，19 轮由真实 t2fail 归位风暴）；C.2 判读器截断浮点绕过路径登记（D-1007-T1-05，低优先未执行）。
- 收官：夜报=v11_25_night_report_T1B.md（501c8318）+STATUS 收官行 17:29+残场零残留（进程/锁全零，df 524G）。

### A-A T1-A 线（NUC 实机域）——**可证面仅有以下两件**
- 14:06 开工行（NUC 已上电可达声明+册部署 796e2947）；
- 14:07 config 双态收敛 commit 6f20eef+D-1007-T1-03。
- **此后（14:07-17:35 窗）无任何台账痕迹**：NUC `~/sitl_realmachine/` 未建、3090 STATUS/DECISION_LOG 零更新、git 零提交——阶段 1a-1e 产出（NUC 环境核查报告/算力基准/实机 config v0+溯源表/安全链核查清单/硬件检查矩阵报告）**无在案证据**。本册按客观证据记账：保底①⑤⑥⑦未达（执行状态不明，非判"未执行"——见 C.8）。

## B. 剩余件（按优先序）

1. **NUC 阶段 1 全腿（1a-1e）**：系统盘点+realsense 驱动链三流/时间戳域 60s 漂移+电池运行 ≥10min（1a）；全栈联合负载基准+20min 温度+3090 对照（1b）；实机 config v0+逐键溯源表（上游 d435i 值+t2 增强键合成+标定核对清单；1c）；遥控/失控保护/急停核查+物理配合窗清单（1d）；硬件检查矩阵 11 行报告（含深度流/emitter/飞控校准/电调电源；1e）——**全部待做**（A-A 可证面为零）。
2. **INPUTFACE-SCREEN 后续**：场景分带标定设计+新参数集预注册冻结→M3'（**禁直接再试**——v1.1 冻结失败语义；stereo_r 场景依赖已证）。
3. **监控 v1**（D5 必修③）：相位感知+重复告警语义+单发布器接管语义——实机监控规程依赖件。
4. **kill≠disarm 缺口闭合**：HAFIX 梯②后 disarm 确认/重试（PX4 kill 后 armed 态保持）。
5. **P3 生产/消费侧落码**（设计件在册；与 HAFIX 交互=重启通告重置 ha_dead_since）。
6. **E8P 族（E×plain）深化**：腿 B 门下仍 0/3——触发内容三候选（渲染时序/双目标戳/场景帧）仍未隔离。
7. **HAFIX 实机化**：参数复标（dead_s/kill_s 对实机 d435 时延域）+演练五案实机版（规划册 M1 门消费）。
8. T4 在途件（verdicts 三节+E4 帧级复核）+C.2 绕过执行（低优先）+starve 修复落码（案文在册，与 P3 同窗候选）。

## C. 卡点（客观陈述，禁方案）

1. **stereo 配对率场景依赖（实测）**：plain 域健康带 0.16-0.28 vs obstacles 域 0.05-0.08——单一域校准的阈不可跨域复用；K3 键的跨域标定方法论缺位（两域样本量=1 域各 1 袋烟测+批 18 轮）。
2. **E8P/E×plain 族不响应输入质量门**：M3 下 0/3 维持（史 5/5 跳）——该族触发内容与三质量键（供给饱和/深度全有效）正交，输入面病灶内容仍未隔离（1e 裁决只到"输入内容锚定"层）。
3. **kill≠disarm**：PX4 KILL（CommandLong 400）后 armed 态保持——HAFIX 复验轮 auto_disarm=0（电机停+落地=安全态达成但状态机缺口在）；D3/D4a 的 DEGRADED 同面。
4. **慢漂不可自动检测（实证强化）**：D5 演练=监控 v0 起飞段假阳+一次性聋+双发布器交错三缺陷——该失效族在自动面无可用检测器（与安全盘点件预判一致，现有活体证据）。
5. **HAFIX 验证样本量=1**：单轮 D1 复验 PASS——多轮/多场景（悬停段死亡/降落段死亡/不同高度）未覆盖。
6. **A 线执行状态不明**：14:07 后零台账痕迹——阶段 1 五件产出无法确认是否存在；可能原因域（会话中断/静默执行未落账/执行未开始）本册无法区分，仅记客观缺证。
7. **实机 config v0 前置依赖未落地**：上游 d435i 标定值提取（上游仓定位）+本机 d435 factory 值对照——两者均未开始（依赖 B.1）。
8. **册版本双轨事件**：v11.25 部署曾现两 md5（A 线 796e2947/B 线 7b72decd=Windows 权威 r2）——A 线部署本含旧 r1 嫌疑已在握手行对表，但 A 线未回执确认其执行依据版本。
9. **双线合账未发生**：T1-B 收官行 17:29 已 @T1-A 请求合账——回执未至（等待协议 v2 在计）。

## D. 资产 md5 表（2026-10-07 17:5x 实查）

| 件 | md5/值 | 位置/谱系 |
|---|---|---|
| VINS 栈（M2 腿B 版） | node f622bae2+lib 886b1e90 | devel；IQG 默认关；gate-off 健康/门开活性双证 |
| px4ctrl（HAFIX 版） | 0b581422 | devel；D1 复验 PASS |
| SITL config | 054ddc8d（复验） | M3 证伪后回滚态=git 正源 6f20eef |
| REGEN+M3 终账 | regen_prereg_v1_frozen.md（v1.1+M3 节） | t2_results/e1_verdict/ |
| 演练件 | drill_prereg_v1=f7189b98/drill_report_v1=5ada1d4c | t1_evidence/v11_25/ |
| M3 产物 | m3_batch_report.csv+m3_celltable.md（18 轮+格级双列） | t3_results/ |
| 工具族 | t1_stoploss_watch=be3e0225/t1_scene_gate/t1_inject_odom/t1_odom_monitor/t1_drill_run/t1_preflight_check/m3_batch.sh/m3_analyze.py | sitl_sim 根（cca3286/d6749e3） |
| j0d_stats v3（X5 联表） | t3_j0d_stats_v2.py v1.1 | analysis/；风暴 84/中漂 54/净轮 47 |
| P3 设计件 | c9083356 | t1_evidence/v11_25/ |
| X7 终稿 | f4e96bbd（未动） | docs/ |
| commit 链（v11.25 窗） | 6f20eef(A)→033ba71→cca3286→d6749e3(B) | 全推 UAV_NUC |
| tag sitl-v0.4 | →dd8dfda | 远端 ref 实查 10-07 |
| 夜报 | v11_25_night_report_T1B.md=501c8318 | t1_evidence/v11_25/ |

## E. 等待登记

- **W-A 线合账回执**（17:29 已请求）——阶段 1 五件产出对账后 B.1/C.6/C.7 销号或转执行。
- **W-规划册 v1 用户审定**（plans/2026-10-07_realmachine_migration_plan_v1.md：阶段门序/回环案 A/M1 门定义）。
- **W-NUC 物理窗**（1d 遥控失联/急停拨测+1e 磁力计/电调物理项——需用户在场）。
- W-INPUTFACE M3'（场景分带标定预注册冻结后）。
- 池（≥3）：starve 修复落码（案文 a1ce23df）/E5P CAL boot 机制考古/社区调研收尾（1e 联动）/T4 verdicts+E4。
