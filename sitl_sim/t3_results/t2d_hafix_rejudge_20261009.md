# 2d(HAFIX 多场景批) 统一重判读（T3 判读面）

> 生成器 t3_2d_hafix_rejudge_v1.0 (T3 v10.9 单元2d; C-9 销号件; OUT=repo 正源) | 生成 2026-10-09 04:15:46 | 输入=/home/ghj/sitl_sim/vins_smoke_runs/run_DRILLD1_N8P_2*
> 正源面: [HAFIX]=px4ctrl.log 实读（批脚本 stdout grep 假象勘误=T1 C-9）; landed=RESULT.txt LANDING z_end<0.15。
> 预注册判据（t1_batch_3d.sh 冻结）: 每轮 HAFIX≥1 ∧ landed=1; 场景 PASS=5/5; 3d PASS=4 场景全 PASS。

| round | ts | 场景(映射源) | rep | HAFIX行数/maxstage | landed(z_end) | disarm | GATEHIT | RESULT | 轮判 |
|---|---|---|---|---|---|---|---|---|---|
| run_DRILLD1_N8P_214206 | 214206 | S1_hover_1m [summary映射] | 1 | 5/stage1 | 1(0.105) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_214621 | 214621 | S2_hover_3m [summary映射] | 1 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_214950 | 214950 | S3_transit [summary映射] | 1 | 0/stage0 | 1(0.134) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_215405 | 215405 | S4_land_1m [summary映射] | 1 | 0/stage0 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **FAIL** |
| run_DRILLD1_N8P_215653 | 215653 | S1_hover_1m [summary映射] | 2 | 5/stage1 | 0(1.445) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_220559 | 220559 | S2_hover_3m [summary映射] | 2 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_220927 | 220927 | S3_transit [summary映射] | 2 | 5/stage1 | 0(0.916) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_221832 | 221832 | S4_land_1m [summary映射] | 2 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_221950 | 221950 | S1_hover_1m [summary映射] | 3 | 7/stage1 | 1(0.104) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_222406 | 222406 | S2_hover_3m [summary映射] | 3 | 3/stage0 | 0(1.028) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_223311 | 223311 | S3_transit [summary映射] | 3 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_223339 | 223339 | S4_land_1m [summary映射] | 3 | 5/stage1 | 0(1.022) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_224245 | 224245 | S1_hover_1m [summary映射] | 4 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_224313 | 224313 | S2_hover_3m [summary映射] | 4 | 5/stage1 | 0(0.973) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_225218 | 225218 | S3_transit [summary映射] | 4 | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_225546 | 225546 | S4_land_1m [summary映射] | 4 | 4/stage1 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_225838 | 225838 | S1_hover_1m [summary映射] | 5 | 0/stage0 | 1(0.136) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_230253 | 230253 | S2_hover_3m [summary映射] | 5 | 3/stage2 | NA(—) | — | — | FAIL | **FAIL** |
| run_DRILLD1_N8P_230621 | 230621 | S3_transit [summary映射] | 5 | 5/stage1 | 1(0.105) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_231037 | 231037 | S4_land_1m [summary映射] | 5 | 0/stage0 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **FAIL** |
| run_DRILLD1_N8P_231439 | 231439 | 非本批(批毕后) [batch_done=23:14:31] |  | 7/stage1 | 1(0.104) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **PASS** |

## 场景汇总（预注册口径）

- S1_hover_1m: 2/5 轮 PASS → FAIL
- S2_hover_3m: 0/5 轮 PASS → FAIL
- S3_transit: 1/5 轮 PASS → FAIL
- S4_land_1m: 1/5 轮 PASS → FAIL

**3d 批总判: NOT-PASS(如实)**（4 场景全 5/5 才 PASS; 轮数≠5 的场景面如实注记）

> 场景映射审计注: S1/S4 同 goal 靠窗长消歧(bag 时长; --skip-bagdur 时退化为时长缺省=S1 偏置,映射表全部列在上表可复核; 若 D5_L2 带监控 drill 轮混入 pattern, 其 note/RESULT 面会示异)。
