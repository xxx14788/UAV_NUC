# 2d(HAFIX 多场景批) 统一重判读（T3 判读面）

> 生成器 t3_2d_hafix_rejudge_v1.0 (T3 v10.9 单元2d; C-9 销号件; OUT=repo 正源) | 生成 2026-10-11 10:07:01 | 输入=/home/ghj/sitl_sim/vins_smoke_runs/run_DRILLD1_N8P_0*
> 正源面: [HAFIX]=px4ctrl.log 实读（批脚本 stdout grep 假象勘误=T1 C-9）; landed=RESULT.txt LANDING z_end<0.15。
> 预注册判据（t1_batch_3d.sh 冻结）: 每轮 HAFIX≥1 ∧ landed=1; 场景 PASS=5/5; 3d PASS=4 场景全 PASS。

| round | ts | 场景(映射源) | rep | HAFIX行数/maxstage | landed(z_end) | disarm | GATEHIT | RESULT | 轮判 |
|---|---|---|---|---|---|---|---|---|---|
| run_DRILLD1_N8P_003520 | 003520 | S1_hover_1m [goal推断] | 1 | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_003905 | 003905 | S2_hover_3m [goal推断] | 1 | 8/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_004613 | 004613 | ? [goal推断] | 1 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_005122 | 005122 | S3_transit [goal推断] | 1 | 6/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_005401 | 005401 | S1_hover_1m [goal推断] | 2 | 8/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_010109 | 010109 | ? [goal推断] | 2 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_010618 | 010618 | S1_hover_1m [goal推断] | 3 | 8/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_010857 | 010857 | S2_hover_3m [goal推断] | 2 | 10/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_011605 | 011605 | ? [goal推断] | 3 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_012114 | 012114 | S3_transit [goal推断] | 2 | 6/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_012355 | 012355 | S1_hover_1m [goal推断] | 4 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_013354 | 013354 | S1_hover_1m [goal推断] | 5 | 10/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_014102 | 014102 | ? [goal推断] | 4 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_014611 | 014611 | S2_hover_3m [goal推断] | 3 | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_015320 | 015320 | ? [goal推断] | 5 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_015829 | 015829 | S3_transit [goal推断] | 3 | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_020107 | 020107 | S1_hover_1m [goal推断] | 6 | 0/stage0 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **FAIL** |
| run_DRILLD1_N8P_020450 | 020450 | S1_hover_1m [goal推断] | 7 | 6/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_020731 | 020731 | S2_hover_3m [goal推断] | 4 | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_021439 | 021439 | ? [goal推断] | 6 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_021948 | 021948 | S3_transit [goal推断] | 4 | 8/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_022657 | 022657 | ? [goal推断] | 7 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_023206 | 023206 | S1_hover_1m [goal推断] | 8 | 2/stage1 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_023444 | 023444 | S1_hover_1m [goal推断] | 9 | 8/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_023725 | 023725 | S2_hover_3m [goal推断] | 5 | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_024435 | 024435 | S3_transit [goal推断] | 5 | 8/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_025144 | 025144 | ? [goal推断] | 8 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_025653 | 025653 | S1_hover_1m [goal推断] | 10 | 0/stage0 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **FAIL** |
| run_DRILLD1_N8P_033808 | 033808 | S1_hover_1m [goal推断] | 11 | 0/stage0 | 0(0.623) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | ENV | **FAIL** |
| run_DRILLD1_N8P_034137 | 034137 | ? [goal推断] | 9 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_034505 | 034505 | ? [goal推断] | 10 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_034833 | 034833 | ? [goal推断] | 11 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_040715 | 040715 | ? [goal推断] | 12 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_042425 | 042425 | S3_transit [goal推断] | 6 | 190/stage0 | 0(0.592) | 0 | n=1 abort:0,land:0,disarm:0,not2fail:0 | ENV | **FAIL** |
| run_DRILLD1_N8P_045450 | 045450 | S3_transit [goal推断] | 7 | 0/stage0 | 1(0.105) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_050141 | 050141 | S1_hover_1m [goal推断] | 12 | 0/stage0 | 1(0.121) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_051357 | 051357 | S1_hover_1m [goal推断] | 13 | 0/stage0 | 1(0.140) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_054131 | 054131 | ? [goal推断] | 13 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |

## 场景汇总（预注册口径）

- S1_hover_1m: 7/13 轮 PASS → FAIL
- S2_hover_3m: 5/5 轮 PASS → PASS
- S3_transit: 5/7 轮 PASS → FAIL

**3d 批总判: NOT-PASS(如实)**（4 场景全 5/5 才 PASS; 轮数≠5 的场景面如实注记）

> 场景映射审计注: S1/S4 同 goal 靠窗长消歧(bag 时长; --skip-bagdur 时退化为时长缺省=S1 偏置,映射表全部列在上表可复核; 若 D5_L2 带监控 drill 轮混入 pattern, 其 note/RESULT 面会示异)。
