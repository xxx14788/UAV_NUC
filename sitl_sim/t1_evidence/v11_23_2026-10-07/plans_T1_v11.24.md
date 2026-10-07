# T1 任务书 v11.24 — v11.23 完成清账版（2026-10-07 13:1x 落盘；v11.23 弃读）

> 你是 **T1（单线承接模式）**。执行域=3090（`ssh nuc2`）。台账=`~/sitl_sim/t1_evidence/v11_23_2026-10-07/`（v11.23 战役目录沿用至本册周期）。
> 单线纪律不变：全域唯一执行册，跨域产物落各自目录契约+代持清单入 DECISION_LOG；红线 1-24+等待协议 v2（轮询等待制，醒来不靠人）；判据/门值零变动；大 IO 件错峰自排。
> **tag sitl-v0.4 已打已推**（dd8dfda，远端 ref 实查 10-07）——后续任何动 tag 操作仍需用户明示。
> 本册性质=清账+移交：A=v11.23 完成账（证据锚全列）；B=剩余件；C=卡点客观陈述（**禁方案**）；D=资产 md5 表；E=等待登记。

## A. v11.23 完成清账（双必达 ✓✓ + 保底九件全落）

- **A.0 开工与代持启动**：STATUS 开工行 11:40；册部署 md5 17b93ada 双端一致；残场核查零残留（df 527G/进程/锁）；tag 复核实在（本地+UAV_NUC 远端 ref→dd8dfda）；**悬停 8.5m 最后通牒已答=指针在案**（实物=NUC(192.168.0.6)`~/sitl_sim/bags/t2v3_hover_130226.bag` 68M/md5 7e3d56f1 单副本注记+判读文=t1_evidence/v10_2026-10-02/u3_hover_drift_verdict.md+工具三件；文书=06c69fc9）；工具链对账 round_result=7e907b7d ✓。
- **A.1 1e 回放裁决=输入面实锤**（判据=x4_bagench_design_v1 §3 冻结逐字；栈 721cad40+054ddc8d 零变动×4 回放 alive=1 全程播完）：
  - j0d 前置分型：E8P=mixed（j0_total 3.122=jump 11.9/transit 10.4，njf=409）/HVNET1=transit 90% 主导（njf=4，"悬停跳 4.12m"=慢淋非帧跳，判别价值降级如实注记）。
  - E8P 2/2：在线全部 11 个 >5m 巨跳同刻（±2s，多处 0.01s 逐位）同幅值带（≤1.1×）复现；**重 init 后段逐位一致**（t=232.05=49.59↔49.59 等）。
  - HVNET1 2/2：慢漂确定性复现（终态 z 差 0.04-0.10m/1-2.4%，轨迹对齐 p50=9mm）。
  - 机理两面=输入扣扳机（触发层）+估计器定弹道（r1↔r2 分支 10/28 bin 差=路径层非确定性）。
  - 产物：`t2_results/e1_verdict/verdict_v1.md`（c2d75688）+5 判读 json+4 回放目录（t3_results/1e*）。
  - **预授权行动链首件已落**：INPUTFACE-SCREEN 立项书 58a4a027（设计件两腿+实机 d435 对照注记+修复链闭环标准预注册写死+REGEN-PREREG-v0 初稿）+DECISION_LOG D-1007-T1-01 里程碑开行。
- **A.2 X4 九轮 j0d+统计扩切口+悬停谱系**：9 目录 j0_decomp.json 零覆写（五绿全 njf=0；S12P"B 型跳 4.7m"=transit 4.42m 主导+0.30m 跳帧勘误；S8O=mixed）；`j0d_stats_20261007.{csv,txt}`=113→**185 袋轮**（X4 9+X5 59 并表，CAMPAIGN_ARM 映射+provenance 注记；净轮 48/中漂移 72/风暴 65）；悬停谱系定案 d07fcd60（hover 自跳 ≈5/8-6/9 与导航同族，"悬停=安全格"直觉数据否证）。
- **A.3 X7 终稿出稿**（硬底线 04:15 前达成，余量 ~15h）：同名去 _DRAFT=**f4e96bbd**（三处一致；出稿 247dc7f+R10 追加 e6e5544）。七槽销号（§2 续飞如实注记未执行/§3 九轮逐轮表全列/§4-bis 无门批 5/5+tag 双链/§5 引尾节/§6 CI+j0d v2/§7.10 综合陈述含概率面 70.5%/17%/§9 figs1-5 终版+fig6=x5_passmap 正源注记）；R12 终措辞=输入面分支；R2/A2 状态刷新；R10 回挖位=E5P gyro 行。figs CSV=16 轮（13 轮取 wa_gate_online.json 正源+3 轮 RESULT 面行补，收集器留档）。残留清理三件齐：X4_TAG_PENDING 归档（.resolved_20261007_tagged）+x4_batch_report 双份日期限定注记+背书重跑器末列聚积 FAIL 缺陷修复（5c1a0145 双树）；.bak 凭据族九件归档 sitl_sim_archive。
- **A.4 工程件**：4a 止损件 t1_stoploss_watch v1.0（be3e0225；selftest 6/6；7 例历史袋 replay 定位复现=5 触发含 E8P t=68.696/dp=1.029 与在线流首事件逐位+2 慢漂型不触发=设计边界如实；vins_smoke `--stoploss` 挂点+gate_abort 模式参数化[stoploss=RESULT=FAIL/exit43]；commit 5cd4bd0）；4b wl-bug 同骨架排查 615 文件**零真命中**（唯一命中=修复注释文本误报；x4/x5 双确认 wl 文件化在位；34c40a82）；4c rtf 探针常态化（移出 GATE 块，--no-gate 亦挂载）；4d starve 审计 a1ce23df（execFSM timer 生命周期本体无缺陷；冻结载体定位=waypointCallback spinOnce 循环 sim 时钟永眠主嫌[+spinOnce 重入次嫌]；**高风险分支=维持重启绕行**，修复案文本化未落码）；4e E5P gyro CAL 评估 bfed27bf（CAL_GYRO0_ZOFF=-0.0403rad/s≈2.3°/s 假偏航率=绿格带 40×；入 EKF2/姿态控制链；VINS data_raw 阻断非该轮因果[380× 分离]；X7 R10 已注记）；4f 栈资产清点 6f351d2a。
- **A.5 T4 代持收货**：X4/X5 两档收清单 30a4debd（X5 紧凑 59+X4 九轮分标本/带图/紧凑三支）；**两 1e 带图标本袋保全标记已置**（PRESERVE_DO_NOT_DELETE.md）；**X4 批轮袋处置未执行**（如实：口径 22 原文 3090 不可定位+df 527G 零腾位压力+锚表 v3 删除纪律→移交 @T4）；verdicts 三节+E4 帧级复核=在途移交注记（IO 错峰条款）。
- **A.6 实机安全盘点件**（用户"炸机不可接受"红线落地首件）=realmachine_safety_audit.md（1a475cf4）：6a H-A 残面升格=实机前安全关键阻塞项（触发条件全谱/历史实证轮/修复面三候选文本化）；6b G1-G3×P1-P3 逐件对账（G-2=P2 已落地已验证/G-3=Z1.2 已接线残留帧级差未裁/G-1=根因改判低优先；未落地清单=P3 正式契约+6a 修复面择一+止损件实机语义复核）；6c 注入演练四案（杀 VINS/毒 odom 跳变/毒 odom 断流/planner 饿死×安全态分层判据草案）；6d 失效安全原则登记。DECISION_LOG D-1007-T1-02。
- **A.7 收官**：夜报 v11_23_night_report.md（d533f7b0）+STATUS 收官行 12:56+残场零残留（进程/锁全零）+commit 链 **247dc7f→5cd4bd0→e6e5544→34e1754** 四笔全推。

## B. 剩余件（按优先序）

1. **INPUTFACE-SCREEN M2**：写码+gtest（腿 B=帧级输入质量门[阶段化：init 期放行/稳态期拒收]+腿 A=场景分门脚本[S1 world×direction/S2 gyr 档/S3 图像供给键]）；同窗候选=starve 修复落码（WallDuration+循环上界+重入门，案文在 a1ce23df）。
2. **INPUTFACE-SCREEN M3**：SITL 代表格批+绿率复测 ≥10 轮（毒格 E8P/S12P/S8O+绿格对照 E12O/NE8O/N8P；判据=REGEN-PREREG-v0 初稿**未冻结**——冻结是批前置动作）。
3. **止损件在线实战首轮**：`--stoploss` 真轮零样本（replay 面已验，inflight rospy 面未实战）。
4. **实机安全盘点件执行面**：6c 注入演练四案未跑（SITL 可执行）；6a 修复面三候选未择一落码；P3 正式契约未接线。
5. **X4 批轮袋处置**（待 C.1 解锁）；**hover 8.5m 证据包镜像决策**（@T4，单副本在 NUC）。
6. **T4 域在途件**：verdicts 草稿三节+E4 帧级复核（已移交注记，未消费）。
7. **明日实机迁移规划**（总设计师域；输入件在盘=安全盘点件+栈清点+两档收清单）。

## C. 卡点（客观陈述，禁方案）

1. **口径 22 原文不可定位**：X7/runbook 对 X4 袋处置引用"口径 22"，但该条款定义文本在 3090 两树（sitl_sim+catkin_ws）T4/T3 域文档中检索不到，仅存在引用无定义——处置动作无机械执行依据；锚袋注册表 v3 流程条款（删前 grep 锚表+@T3 回执）另加一道跨线等待。
2. **判读器截断浮点崩溃**：t3_wa_gate bee17577（冻结 md5）在 10-07 窗三轮（X4_E8O/1e_E8P/1e_HVNET1）vins.log 尾行截断科学计数浮点（如 `1.92946e`）上 parse_vins_log 崩溃——该三轮 wa_gate_online.json 不存在；figs CSV 已用 RESULT 面行补（vins 内部列空，provenance 注记在 X7 §9），但该三轮 vins 内部判读面（bas/ate/spike 等）当前无产出路径（重判同因崩溃；判读器红线禁改）。
3. **1e 输入面实锤的病灶内容未隔离**：判据只到"输入 vs 运行时"分水面；输入内部三候选（Gazebo 渲染时序/双目标戳微差/场景帧内容）均未证伪/证实——T2 设计件原文即如此框定，输入内部分型无在册判据。
4. **starve 注入验证依赖不存在的工具**：/clock 受控停摆注入 harness 不存在——修复（文本化案）无法按"注入验证"标准闭环；重启绕行检测器为现役缓解（S8O/W8P 两轮实战恢复在案）。
5. **止损件慢漂盲区**：transit 族失败（X2g1/X3l2a 型，7 例验证中 2 例不触发）在执行面无止损覆盖——止损面仅覆盖帧跳族；慢淋族的执行面止损（若需要）为未立项状态。
6. **config 双态未收敛**：工作树 arm 054ddc8d（v2+cauchy4+guard 臂）vs git HEAD canonical 5c98dc0d——工作树 M 未提交是设计态（4f 在册），但后续批/实机迁移前"以哪态为正"的决策未做。
7. **E5P 型 gyro CAL 异常的 boot 生成机制未查**：sim 侧 CAL_GYRO0_* 逐 boot 变动的写入触发条件（何时/何种状态触发标定）未考古——实机 preflight 检查项已立（安全盘点件），sim 侧根因悬置。
8. **VR3 袋未录 imu_prop 话题**（历史录制缺口，u3_hover_drift_verdict §36 在册）：双流对质直证永久缺——该证据包复验价值受此上限约束。
9. **REGEN-PREREG-v0 未冻结**：M3 批判据处于初稿态；预注册纪律=冻结前禁跑批（防跳步 DoD）。
10. **X5 59 轮判读联表缺**：j0d v2 表中 X5 轮 t2fail/four_green/arrive 为空列（如实注记）——X5 判读史正源在 x5_passmap，但全系统计表该 59 轮无四指标列（两口径未互备）。

## D. 资产 md5 表（2026-10-07 13:1x 实查）

| 件 | md5/值 | 位置 |
|---|---|---|
| X7 终稿 | f4e96bbd | docs/（双树+Windows 本地；commit 247dc7f+e6e5544） |
| 1e verdict_v1 | c2d75688 | t2_results/e1_verdict/ |
| INPUTFACE 立项书 | 58a4a027 | 同上 |
| 止损件 | be3e0225 | sitl_sim 根+catkin 树 |
| vins_smoke.sh | dafa65c2 | 同上（--stoploss 挂点+rtf 常态化；前代 9f647af1） |
| round_result.sh | 7e907b7d | 判读 v1.4 |
| t3_wa_gate.py | bee17577 | 冻结（截断浮点崩溃面见 C.2） |
| t3_trichotomy.py | de47b1a0 | 三列分账权威 |
| t3_endorse_rerun.sh | 5c1a0145 | 末列缺陷修复版 |
| t3_j0d_stats_v2.py | 5a728959 | 185 袋轮版 |
| j0d_stats_20261007.{csv,txt} | 6745744f/bea777a9 | t3_results/ |
| xline_wa_gate_20261007.csv | （16 行） | t3_results/ |
| 悬停谱系定案 | d07fcd60 | t3_results/ |
| 安全盘点件 | 1a475cf4 | t1_evidence/v11_23/ |
| 栈清点 | 6f351d2a | 同上 |
| 两档收清单 | 30a4debd | t4_evidence/ |
| wl-bug 排查 | 34c40a82 / starve=a1ce23df / E5P=bfed27bf / hover85=06c69fc9 / 夜报=d533f7b0 | t1_evidence/v11_23/ |
| VINS 栈 | node 721cad40 + lib 5bacc2e9 | devel（X4 批栈零变动复核） |
| sim_stereo config | arm=054ddc8d（工作树）/ canonical=5c98dc0d（git HEAD） | 双态在册（C.6） |
| px4ctrl_node | a653e982 | devel |
| tag sitl-v0.4 | →dd8dfda | 本地+UAV_NUC 远端 ref 实查 10-07 |
| commit 链（v11.23 夜） | 247dc7f→5cd4bd0→e6e5544→34e1754 | 全推 |

## E. 等待登记

- **W-INPUTFACE-M2 写码窗**（含 starve 修复落码同窗候选）→解锁 M3 绿率复测。
- **W-REGEN-PREREG 冻结**（M3 前置；冻结权=T1 自持，冻结时点自排）。
- **W-实机迁移规划**（总设计师域；输入件在盘=安全盘点件 1a475cf4+栈清点 6f351d2a+两档收清单）。
- **W-T4 回执**：口径 22 原文（C.1）+verdicts/E4 消费+hover85 镜像自裁+X4 袋处置执行。
- **W-X7 下游消费回执**（用户/总设计师；X7=f4e96bbd）。
- 池（≥3）：E5P CAL boot 机制考古（C.7）/A3 臂差因果化（转实机前若需）/社区调研收尾（1e 联动）/X5 59 轮判读联表（C.10）。
