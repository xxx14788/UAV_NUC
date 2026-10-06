# X4 无门基线批终账（T1 v11.20 单元3；2026-10-07 03:5x）

## 5/5 达成判定（预注册口径机械执行）

**达成面 = 物理绿 5 + 门拦截计入 0 = 5/5；物理绿 5 ≥ 3（phys-floor 默认案）✓**
无门基线支（ROC 零工作点→门不可靠→禁上真轮作绿率提升器，判读不带门语义，5/5 全物理才算数）——本批=该支的机械执行。

## 轮账（trichotomy 全轮形式重账，cf=现场 wa_gate/none）

| 轮 | RESULT | class | jump(pre-post) | 到位(真值) | 备注 |
|---|---|---|---|---|---|
| run_X4_E12O_031818 | PASS | phys_green | 0.252 | 0.278 | 格1 基础 |
| run_X4_NE8O_032059 | PASS | phys_green | 0.034 | 0.037 | 格2 基础 |
| run_X4_NE12O_032330 | PASS | phys_green | 0.234 | 0.220 | 格3 基础 |
| run_X4_S12P_032611 | FAIL | true_fail | 4.700 | 11.106 | 格4 基础；B 型跳(plain)→换格#1 |
| run_X4_E8O_033233 | PASS | phys_green | 0.081 | 0.156 | 格5 基础 |
| run_X4_S8O_033810 | FAIL | true_fail | 0.487 | 6.009 | 替补#1；starve 修复实战触发恢复+TIMEOUT 慢=C 型；带图(1e 条件件 1/2) |
| run_X4_N8P_034553 | PASS | phys_green | 0.094 | 0.083 | 替补#2；带图(1e 条件件 2/2)——达成第 5 绿 |

物理轮 7/15 上限；换格 2/2 耗尽（N8P 绿后批收束）；撞门 0；ENV 0。

## 成色注记（tag 必带）

- **物理绿 5 / 门拦截计入 0**（无门基线：门经 ROC 双线证不可靠，本批判读零门语义）
- 臂=v2+cauchy4（config 054ddc8d=X5 批同款）；栈 721cad40/5bacc2e9（纯脚本面零栈改动红线保持）
- 选格=绿格 11 gyr 升序前 5（E12O/NE8O/NE12O/S12P/E8O）+替补顺位 6/7（S8O/N8P）——T2 科学包验证默认案自动落安全带（绿格 gyr≤2.44）
- 1 真失败格（S12P，B 型跳 4.7m，plain）+1 替补失败（S8O，starve 后 TIMEOUT 慢，C 型）——如实计红，非全绿童话
- starve 修复（v11.17）批内实战触发并恢复 @S8O（FSM 停摆→重启→poscmd 100Hz 恢复）
- wl-bug 如实注记：judge_round w()/tee 被 $( ) 捕获致批级 case 失配（x5 19:35 同款坑，T3 基座修复在融合时被丢失）→ 批级账目失能，本终账=trichotomy 全轮形式重账（判读落盘全程不受影响）；热修 64f81b8 已复植+推送
- 带图 2 轮（S8O/N8P，12G+11G 级）=1e 输入面裁决素材（批内条件件：S12P 跳变族真 FAIL+定因全排除触发）；T2 设计件（E8P+HVNET1）另行执行
- 判读权链：本线内嵌判读全绿（trichotomy 单点权威+四指标）∧ T3 独立复核行（X4_T3_REVIEW_CONFIRM）=双链

## 判据与正源

- 四指标=round_result.sh（到位门 0.75 obstacles/0.5 plain+避障+poscmd≥50Hz+auto_disarm）
- 分类=t3_trichotomy.py v1（T3 v10.3 三列分账，prereg §2.9）
- 复核可复算：python3 sitl_sim/analysis/t3_trichotomy.py <run_dir> --cf <state>
- 批报告=x4_batch_report.md+x4_launch.log（批级账目因 wl-bug 失能段有注记）
