# 2d(HAFIX 多场景批) 统一重判读（T3 判读面）

> 生成器 t3_2d_hafix_rejudge_v1.0 (T3 v10.9 单元2d; C-9 销号件; OUT=repo 正源) | 生成 2026-10-10 19:58:14 | 输入=/home/ghj/sitl_sim/vins_smoke_runs/run_DRILLD1_N8P_1[6-9]*
> 正源面: [HAFIX]=px4ctrl.log 实读（批脚本 stdout grep 假象勘误=T1 C-9）; landed=RESULT.txt LANDING z_end<0.15。
> 预注册判据（t1_batch_3d.sh 冻结）: 每轮 HAFIX≥1 ∧ landed=1; 场景 PASS=5/5; 3d PASS=4 场景全 PASS。

| round | ts | 场景(映射源) | rep | HAFIX行数/maxstage | landed(z_end) | disarm | GATEHIT | RESULT | 轮判 |
|---|---|---|---|---|---|---|---|---|---|
| run_DRILLD1_N8P_160603 | 160603 | ? [无300s内启动事件] |  | 418/stage1 | 0(1.084) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_161514 | 161514 | ? [无300s内启动事件] |  | 414/stage0 | 0(1.007) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_162425 | 162425 | ? [无300s内启动事件] |  | 416/stage1 | 0(0.865) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_163333 | 163333 | ? [无300s内启动事件] |  | 0/stage0 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **FAIL** |
| run_DRILLD1_N8P_163614 | 163614 | ? [无300s内启动事件] |  | 121/stage0 | 0(0.652) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_164037 | 164037 | ? [无300s内启动事件] |  | 414/stage0 | 0(0.973) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_164946 | 164946 | ? [无300s内启动事件] |  | 120/stage0 | 0(0.946) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_165410 | 165410 | ? [无300s内启动事件] |  | 0/stage0 | NA(—) | — | — | FAIL | **FAIL** |
| run_DRILLD1_N8P_165918 | 165918 | ? [无300s内启动事件] |  | 2/stage1 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_170157 | 170157 | ? [无300s内启动事件] |  | 118/stage0 | 0(1.044) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_170617 | 170617 | ? [无300s内启动事件] |  | 414/stage0 | 0(0.941) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_171526 | 171526 | ? [无300s内启动事件] |  | 119/stage0 | 0(1.074) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_171833 | 171833 | ? [无300s内启动事件] |  | 5/stage1 | 1(0.104) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_171947 | 171947 | ? [无300s内启动事件] |  | 0/stage0 | 1(0.105) | 1 | n=1 abort:0,land:1,disarm:1,not2fail:0 | PASS | **FAIL** |
| run_DRILLD1_N8P_172227 | 172227 | ? [无300s内启动事件] |  | 120/stage0 | 0(1.033) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_172651 | 172651 | ? [无300s内启动事件] |  | 414/stage0 | 0(1.029) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_173320 | 173320 | ? [无300s内启动事件] |  | 2/stage1 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_173555 | 173555 | ? [无300s内启动事件] |  | 0/stage0 | NA(—) | — | — | — | **NO-JUDGE** |
| run_DRILLD1_N8P_173559 | 173559 | ? [无300s内启动事件] |  | 118/stage0 | 0(0.964) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_174020 | 174020 | ? [无300s内启动事件] |  | 4/stage1 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_174258 | 174258 | ? [无300s内启动事件] |  | 118/stage0 | 0(0.940) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_174719 | 174719 | ? [无300s内启动事件] |  | 414/stage0 | 0(0.799) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_175628 | 175628 | ? [无300s内启动事件] |  | 416/stage1 | 0(0.892) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **FAIL** |
| run_DRILLD1_N8P_180538 | 180538 | ? [无300s内启动事件] |  | 2/stage1 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_181817 | 181817 | ? [无300s内启动事件] |  | 4/stage2 | 1(0.105) | 0 | n=0 abort:0,land:0,disarm:0,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_182423 | 182423 | ? [无300s内启动事件] |  | 6/stage2 | 1(0.105) | 1 | n=1 abort:0,land:1,disarm:1,not2fail:0 | PASS | **PASS** |
| run_DRILLD1_N8P_183020 | 183020 | ? [无300s内启动事件] |  | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_183259 | 183259 | ? [无300s内启动事件] |  | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_184009 | 184009 | ? [无300s内启动事件] |  | 6/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_184248 | 184248 | ? [无300s内启动事件] |  | 6/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_184528 | 184528 | ? [无300s内启动事件] |  | 6/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_185237 | 185237 | ? [无300s内启动事件] |  | 8/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_185947 | 185947 | ? [无300s内启动事件] |  | 5/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |
| run_DRILLD1_N8P_190228 | 190228 | ? [无300s内启动事件] |  | 18/stage2 | NA(—) | 1 | — | FAIL | **FAIL** |
| run_DRILLD1_N8P_190534 | 190534 | ? [无300s内启动事件] |  | 5/stage2 | 1(0.105) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | FAIL | **PASS** |
| run_DRILLD1_N8P_192242 | 192242 | ? [无300s内启动事件] |  | 6/stage2 | 1(0.104) | 1 | n=0 abort:0,land:0,disarm:1,not2fail:1 | PASS | **PASS** |

## 场景汇总（预注册口径）


**3d 批总判: PASS**（4 场景全 5/5 才 PASS; 轮数≠5 的场景面如实注记）

> 场景映射审计注: S1/S4 同 goal 靠窗长消歧(bag 时长; --skip-bagdur 时退化为时长缺省=S1 偏置,映射表全部列在上表可复核; 若 D5_L2 带监控 drill 轮混入 pattern, 其 note/RESULT 面会示异)。
