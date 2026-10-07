> [日期限定注记 2026-10-07 T1 v11.23] 本报告=X4 无门基线批(2026-10-07 03:15-04:00,终态 5/5 全物理+tag sitl-v0.4);正源终账=x4_final_tally.md(206506c5),wl-bug 批级账目失能段在册

[2026-10-07 03:15:58] # X4 五位形冲刺批报告(2026-10-07 03:15:58;臂=guard=1 sane_p=50.0 sane_v=15.0;栈=721cad40/5bacc2e9 cfg=054ddc8d;gate=/home/ghj/sitl_sim/t1_gate_params.json;goals_md5=b8483c34;规则预注册=任务书 v11.20 单元1d/3+T3 v10.3 三列分账v1;融合版注记见脚本头)
[2026-10-07 03:15:58]   --no-gate 模式(预注册分支:门不可靠→无门基线,判读不带门语义,5/5 全物理才算数)
[2026-10-07 03:15:58] preflight OK stack=721cad40/5bacc2e9 cfg=054ddc8d gate=/home/ghj/sitl_sim/t1_gate_params.json df=568G arm_banner='guard=1 sane_p=50.0 sane_v=15.0' goals_md5=b8483c34 cells=5
[2026-10-07 03:15:58] 
[2026-10-07 03:15:58] == position X4_E12O (物理轮 #1/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:15:58]   DRY: would run vins_smoke --world sitl_world_obstacles --goal 13.010 0.980 1.0 --budget 200
[2026-10-07 03:15:58] 
[2026-10-07 03:15:58] == position X4_NE8O (物理轮 #2/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:15:58]   DRY: would run vins_smoke --world sitl_world_obstacles --goal 6.667 6.637 1.0 --budget 200
[2026-10-07 03:15:58] 
[2026-10-07 03:15:58] == position X4_NE12O (物理轮 #3/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:15:58]   DRY: would run vins_smoke --world sitl_world_obstacles --goal 9.495 9.465 1.0 --budget 200
[2026-10-07 03:15:58] 
[2026-10-07 03:15:58] == position X4_S12P (物理轮 #4/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:15:58]   DRY: would run vins_smoke --world sitl_world_plain --goal 1.010 -11.020 1.0 --budget 200
[2026-10-07 03:15:58] 
[2026-10-07 03:15:58] == position X4_E8O (物理轮 #5/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:15:58]   DRY: would run vins_smoke --world sitl_world_obstacles --goal 9.010 0.980 1.0 --budget 200
[2026-10-07 03:15:58] 
[2026-10-07 03:15:58] == BATCH END 物理绿=0 门拦截计入=0 合计=0/5 (PAUSE=no) — FAIL/PAUSE 汇总待人工 ==
[2026-10-07 03:15:58] == 成色注记（三列分账 v1）== 物理绿=0 / 门拦截计入=0 / 物理绿下限 ≥3(默认案) / 明细=/home/ghj/sitl_sim/t1_evidence/v11_20_2026-10-07/x4_gatehit_stats.log ==
[2026-10-07 03:18:17] # X4 五位形冲刺批报告(2026-10-07 03:18:17;臂=guard=1 sane_p=50.0 sane_v=15.0;栈=721cad40/5bacc2e9 cfg=054ddc8d;gate=/home/ghj/sitl_sim/t1_gate_params.json;goals_md5=b8483c34;规则预注册=任务书 v11.20 单元1d/3+T3 v10.3 三列分账v1;融合版注记见脚本头)
[2026-10-07 03:18:18]   --no-gate 模式(预注册分支:门不可靠→无门基线,判读不带门语义,5/5 全物理才算数)
[2026-10-07 03:18:18] preflight OK stack=721cad40/5bacc2e9 cfg=054ddc8d gate=/home/ghj/sitl_sim/t1_gate_params.json df=568G arm_banner='guard=1 sane_p=50.0 sane_v=15.0' goals_md5=b8483c34 cells=5
[2026-10-07 03:18:18] 
[2026-10-07 03:18:18] == position X4_E12O (物理轮 #1/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:20:54]   banner: [T2SGCFG] guard=1 sane_p=50.0 sane_v=15.0 resume_gap=0.15 | knobs: loss=0 cauchy=4.00
[2026-10-07 03:20:59]   RESULT=PASS T2fail=0 neverflew=0 jump=0.252 arrive=0.278 auto_disarm->1 cf=clean
[2026-10-07 03:20:59]   DUAL-ANCHOR v1.4: A*=(1.010, 0.980, 0.105) rule=R1 gap=0.017 flag=AGREE | sta=(1.010, 0.980, 0.105)(n=150,span=0.7s,stab
[2026-10-07 03:20:59]   run_X4_E12O_031818: FAIL [scene=obstacles/arrive_gate=0.75 four=1/1/1/1 j0jump=0.252 j0rev=False(raw=2,smj=0) env=- | vins=✓ reboot=0 gaps=0 cov=0.999 bas_pk=0.4723 bgs_pk=0.00215 ate=0.1831 morph=爆散 
[2026-10-07 03:20:59]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:20:59]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
[2026-10-07 03:20:59]   class=[2026-10-07 03:20:59]   RESULT=PASS T2fail=0 neverflew=0 jump=0.252 arrive=0.278 auto_disarm->1 cf=clean
[2026-10-07 03:20:59]   DUAL-ANCHOR v1.4: A*=(1.010, 0.980, 0.105) rule=R1 gap=0.017 flag=AGREE | sta=(1.010, 0.980, 0.105)(n=150,span=0.7s,stab
[2026-10-07 03:20:59]   run_X4_E12O_031818: FAIL [scene=obstacles/arrive_gate=0.75 four=1/1/1/1 j0jump=0.252 j0rev=False(raw=2,smj=0) env=- | vins=✓ reboot=0 gaps=0 cov=0.999 bas_pk=0.4723 bgs_pk=0.00215 ate=0.1831 morph=爆散 
[2026-10-07 03:20:59]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:20:59]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
phys_green
[2026-10-07 03:20:59] 
[2026-10-07 03:20:59] == position X4_NE8O (物理轮 #2/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:23:26]   banner: [T2SGCFG] guard=1 sane_p=50.0 sane_v=15.0 resume_gap=0.15 | knobs: loss=0 cauchy=4.00
[2026-10-07 03:23:30]   RESULT=PASS T2fail=0 neverflew=0 jump=0.034 arrive=0.037 auto_disarm->1 cf=clean
[2026-10-07 03:23:30]   DUAL-ANCHOR v1.4: A*=(1.011, 0.981, 0.104) rule=R1 gap=0.008 flag=AGREE | sta=(1.011, 0.981, 0.104)(n=150,span=0.7s,stab
[2026-10-07 03:23:30]   run_X4_NE8O_032059: FAIL [scene=obstacles/arrive_gate=0.75 four=1/1/1/1 j0jump=0.034 j0rev=False(raw=4,smj=0) env=- | vins=✓ reboot=0 gaps=0 cov=0.999 bas_pk=0.7547 bgs_pk=0.01254 ate=0.0437 morph=小跳/
[2026-10-07 03:23:30]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:23:30]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
[2026-10-07 03:23:30]   class=[2026-10-07 03:23:30]   RESULT=PASS T2fail=0 neverflew=0 jump=0.034 arrive=0.037 auto_disarm->1 cf=clean
[2026-10-07 03:23:30]   DUAL-ANCHOR v1.4: A*=(1.011, 0.981, 0.104) rule=R1 gap=0.008 flag=AGREE | sta=(1.011, 0.981, 0.104)(n=150,span=0.7s,stab
[2026-10-07 03:23:30]   run_X4_NE8O_032059: FAIL [scene=obstacles/arrive_gate=0.75 four=1/1/1/1 j0jump=0.034 j0rev=False(raw=4,smj=0) env=- | vins=✓ reboot=0 gaps=0 cov=0.999 bas_pk=0.7547 bgs_pk=0.01254 ate=0.0437 morph=小跳/
[2026-10-07 03:23:30]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:23:30]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
phys_green
[2026-10-07 03:23:30] 
[2026-10-07 03:23:30] == position X4_NE12O (物理轮 #3/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:26:06]   banner: [T2SGCFG] guard=1 sane_p=50.0 sane_v=15.0 resume_gap=0.15 | knobs: loss=0 cauchy=4.00
[2026-10-07 03:26:10]   RESULT=PASS T2fail=0 neverflew=0 jump=0.234 arrive=0.220 auto_disarm->1 cf=clean
[2026-10-07 03:26:10]   DUAL-ANCHOR v1.4: A*=(1.010, 0.980, 0.105) rule=R1 gap=0.014 flag=AGREE | sta=(1.010, 0.980, 0.105)(n=150,span=0.7s,stab
[2026-10-07 03:26:10]   run_X4_NE12O_032330: FAIL [scene=obstacles/arrive_gate=0.75 four=1/1/1/1 j0jump=0.234 j0rev=False(raw=3,smj=1) env=- | vins=✓ reboot=0 gaps=0 cov=0.999 bas_pk=0.6651 bgs_pk=0.01402 ate=0.1714 morph=爆散
[2026-10-07 03:26:10]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:26:10]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
[2026-10-07 03:26:10]   class=[2026-10-07 03:26:10]   RESULT=PASS T2fail=0 neverflew=0 jump=0.234 arrive=0.220 auto_disarm->1 cf=clean
[2026-10-07 03:26:10]   DUAL-ANCHOR v1.4: A*=(1.010, 0.980, 0.105) rule=R1 gap=0.014 flag=AGREE | sta=(1.010, 0.980, 0.105)(n=150,span=0.7s,stab
[2026-10-07 03:26:10]   run_X4_NE12O_032330: FAIL [scene=obstacles/arrive_gate=0.75 four=1/1/1/1 j0jump=0.234 j0rev=False(raw=3,smj=1) env=- | vins=✓ reboot=0 gaps=0 cov=0.999 bas_pk=0.6651 bgs_pk=0.01402 ate=0.1714 morph=爆散
[2026-10-07 03:26:10]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:26:10]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
phys_green
[2026-10-07 03:26:10] 
[2026-10-07 03:26:10] == position X4_S12P (物理轮 #4/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:32:11]   banner: [T2SGCFG] guard=1 sane_p=50.0 sane_v=15.0 resume_gap=0.15 | knobs: loss=0 cauchy=4.00
[2026-10-07 03:32:32]   RESULT=FAIL T2fail=0 neverflew=0 jump=4.700 arrive=11.106 auto_disarm->1 cf=clean
[2026-10-07 03:32:32]   DUAL-ANCHOR v1.4: A*=(1.010, 0.980, 0.104) rule=R1 gap=0.055 flag=AGREE | sta=(1.010, 0.980, 0.104)(n=150,span=0.7s,stab
[2026-10-07 03:32:32]   run_X4_S12P_032611: FAIL [scene=no_obstacles/arrive_gate=0.5 four=0/1/1/1 j0jump=4.7 j0rev=False(raw=32,smj=47) env=- T1D1 | vins=✓ reboot=0 gaps=0 cov=1.0 bas_pk=1.9382 bgs_pk=0.01875 ate=1.5352 morp
[2026-10-07 03:32:32]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:32:32]   TRICHOTOMY: class=true_fail detail=无门干预的非 PASS(红面);chain 四条=不适用(行内显示 0=n/a)
[2026-10-07 03:32:32]   class=[2026-10-07 03:32:32]   RESULT=FAIL T2fail=0 neverflew=0 jump=4.700 arrive=11.106 auto_disarm->1 cf=clean
[2026-10-07 03:32:32]   DUAL-ANCHOR v1.4: A*=(1.010, 0.980, 0.104) rule=R1 gap=0.055 flag=AGREE | sta=(1.010, 0.980, 0.104)(n=150,span=0.7s,stab
[2026-10-07 03:32:32]   run_X4_S12P_032611: FAIL [scene=no_obstacles/arrive_gate=0.5 four=0/1/1/1 j0jump=4.7 j0rev=False(raw=32,smj=47) env=- T1D1 | vins=✓ reboot=0 gaps=0 cov=1.0 bas_pk=1.9382 bgs_pk=0.01875 ate=1.5352 morp
[2026-10-07 03:32:32]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:32:32]   TRICHOTOMY: class=true_fail detail=无门干预的非 PASS(红面);chain 四条=不适用(行内显示 0=n/a)
fail
[2026-10-07 03:32:32] 
[2026-10-07 03:32:32] == position X4_E8O (物理轮 #5/15;满足 0/5|phy=0 gate=0)
[2026-10-07 03:34:59]   banner: [T2SGCFG] guard=1 sane_p=50.0 sane_v=15.0 resume_gap=0.15 | knobs: loss=0 cauchy=4.00
[2026-10-07 03:35:02]   RESULT=PASS T2fail=0 neverflew=0 jump=0.081 arrive=0.156 auto_disarm->1 cf=?
[2026-10-07 03:35:02]   DUAL-ANCHOR v1.4: A*=(1.010, 0.979, 0.105) rule=R1 gap=0.045 flag=AGREE | sta=(1.010, 0.979, 0.105)(n=150,span=0.7s,stab
[2026-10-07 03:35:02]   
[2026-10-07 03:35:02]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:35:02]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
[2026-10-07 03:35:02]   class=[2026-10-07 03:35:02]   RESULT=PASS T2fail=0 neverflew=0 jump=0.081 arrive=0.156 auto_disarm->1 cf=?
[2026-10-07 03:35:02]   DUAL-ANCHOR v1.4: A*=(1.010, 0.979, 0.105) rule=R1 gap=0.045 flag=AGREE | sta=(1.010, 0.979, 0.105)(n=150,span=0.7s,stab
[2026-10-07 03:35:02]   
[2026-10-07 03:35:02]   GATEHIT-STAT: n=0 ts=NA val=NA kind=NA chain=abort:0,land:0,disarm:0,not2fail:0
[2026-10-07 03:35:02]   TRICHOTOMY: class=phys_green detail=无门干预全绿;chain 四条=不适用(行内显示 0=n/a 非未达成)
phys_green
[2026-10-07 03:35:02] 
[2026-10-07 03:35:02] == BATCH END 物理绿=0 门拦截计入=0 合计=0/5 (PAUSE=no) — FAIL/PAUSE 汇总待人工 ==
[2026-10-07 03:35:02] == 成色注记（三列分账 v1）== 物理绿=0 / 门拦截计入=0 / 物理绿下限 ≥3(默认案) / 明细=/home/ghj/sitl_sim/t1_evidence/v11_20_2026-10-07/x4_gatehit_stats.log ==
