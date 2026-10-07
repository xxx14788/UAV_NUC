# T3 v10.6 网络恢复首件 runbook（3090 回场动作序）

> 背景：10-08 01:2x 起 uav123-5G AP 整体离场（SSID 不在空中；NUC Tailscale 同步失联
> =NUC 无上行，证实 AP 侧故障非本机单点）；3090/NUC/nuc3 全部不可达。本地轮询在册
> （.t3_poll_ap.log，60s 周期，恢复即 ssh 探活）。
> 部署包=本目录 staging/t3_v106_deploy/（md5 清单见 DEPLOY_MANIFEST.txt）。

## A. 恢复即做（本会话若仍在→直接执行；否则下任会话首件）

1. **连通确认**：`ssh nuc2 'date && uptime'`；`ssh nuc-ts 'date'`（NUC 回场双证）。
2. **同步状态侦察**（判读支持有无货）：
   - `~/sitl_sim/STATUS.md` 尾部（各线在恢复窗口内的最后状态）；
   - `ls -t ~/sitl_sim/vins_smoke_runs/ | head`（有无 M3′/新批轮——T2 若在断网前跑过）；
   - `cd ~/catkin_ws && git log --oneline -8 && git status --short`（仓库漂移）。
3. **单元 0 补做**：STATUS 开工行（用本地草稿 status_open_draft.txt）+ git pull +
   册部署（plans/2026-10-07_T3_planner_vision_acceptance_v10.6.md → 3090 备份+md5 对账）
   + **VRFY2 回归抽查**：部署 `t3_vrfy2_regress.py` 后跑 `python3 t3_vrfy2_regress.py`
   （阶段1 默认；JUDGE_CMDS 确认后可 --live）——零重判 PASS/漂移呈报。
4. **部署包落位**：
   - 脚本五件 → `~/catkin_ws/sitl_sim/t3_tools/`（t3_md5_reconcile.sh / t3_vrfy2_regress.py
     / t3_combo_expand_check.py / t3_greenrate_ci.py / t3_epsilon_band_audit.py；
     先 `sed -i 's/\r$//'` CRLF 防御+`bash -n`/py_compile 复验）；
   - 文书四件 → `~/sitl_sim/t3_evidence/v10_6_2026-10-08/`（模板/扩切口预案/M3′ 预案/
     C.2 意见）+ repo `sitl_sim/t3_results/plans/` 同步；
   - md5 对账按 DEPLOY_MANIFEST.txt。
5. **M3′ 有货分支**：按 m3p_judge_support_plan_v1.md 执行（统一判读+格级前后对比+
   扩切口）；无货分支：STATUS 记"飞行窗未开=轮询记录如实"（断腿期轮询日志摘录行）。
6. **X7 勘误窗**：若恢复时刻 <10-08 04:15 且断腿前有新勘误素材→窗口内处理（注记版
   追加制）；过窗→终稿定稿态维持，新素材一律注记版（v10.6 单元 3 口径）。
7. **背书重跑器缺陷确认**（v10.6 单元 4）：3090 在线后取 5c1a0145 系资产+册上已知缺陷
   条目→修复确认或如实登记。

## B. 提交与推送

- 部署后 `git add` 逐文件（禁整目录 add——git add 过宽坑）→ commit → push（推送纪律：
  一工作单元一推）。commit 信息带 "T3 v10.6 断腿期就绪件部署" 字样与断腿起止时刻。

## C. 断腿期产出清单（本地已完成，待部署）

| 件 | 状态 | 验证 |
|----|------|------|
| screening_report_template_v1_frozen.md | 预冻结稿 | 骨架五节+P1-P5 前置门+三层判据逐字 |
| t3_md5_reconcile.sh | 就绪 | ref/cmp 同/异/缺件四路功能测试过 |
| t3_vrfy2_regress.py | 就绪 | 阶段1 假样本干跑：一致行零漂移+漂移行 6 处全捕获 |
| t3_combo_expand_check.py | 就绪 | 纯加性 PASS/旧行漂移 HALT 双路测试过 |
| combo_j0d_expansion_plan_v1.md | 预案 | 185→203+ 流程+provenance 三源列契约 |
| m3p_judge_support_plan_v1.md | 预案 | 统一判读链+格级对比落盘口径 |
| c2_logtail_purify_opinion_v1.md | 意见 | 两分支评估+epsilon 带审计推荐结案 |
| t3_greenrate_ci.py | 就绪 | Wilson+Newcombe CI+L1 判据接口+追加批触发面，数值用例过 |
| t3_epsilon_band_audit.py | 就绪 | C.2 结案件：骑门值自适应 ε 标旗，用例 2/4 正确捕获 |
