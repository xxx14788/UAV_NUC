# 留守件判读 v2(勘误版):旧机 static_watch 周期时间线重构(v1.2 追加节素材)

- 数据面勘误: ALERT 123 件=同一累积 vins log 每 ~5-6.5min 全量重解析(t*=347s 全同/span 递增 598→40861s 实锤);
  周期统计正源=末件 ALERT_152204.txt 的 60s 段 |Bas| med 时间线(n=679 段=679min)。
- 事件面: RESTART(回落收敛带)×4 | STEP-UP ×14 | OUTBREAK(>0.8)×17
- 周期长度(相邻 RESTART 间隔): n=3 min=1560 p50=2760.0 max=30360s
- 周期内发作滞后(STEP-UP/OUTBREAK 相对周期起点): n=16 min=1020 p50=3900.0 p90=13230.0 max=18300s

## 结论(同构性+结局分布;v1.1 样本 2→扩展)
- 同构性: 4 次重启循环全部重复「收敛→台阶上移(0.42/0.30 族)→发作(>0.8)→…→回落」节律;
  首周期 t*=347s(与 v1.1 样本及 T3 scen0 窗注记一致);后续周期发作滞后分布见上(重启后病理再发作自持)。
- 结局分布: 无一周期自然恢复(回落=重启事件;发作后 |Bas| 台阶单向上移无回落观察维持)。
- 静置病理定性: 重启循环(约 2760.0s/周期)×10h+ 自持;实机静置任务时长上限=发作滞后下界(1020s)——
  首飞风险评估输入(报告 v2/呈报件§④直接引用)。
- 污染注记: 04:44-04:48 断段维持(v1.1 口径;全量重解析下断段表现为段谱空洞,不影响事件面)。

## 事件时间线(前 30+后 10)
  t=480s OUTBREAK med=1.3098
  t=660s RESTART(recovery) med=0.0158
  t=1740s OUTBREAK med=0.8129
  t=1980s STEP-UP med=1.3883
  t=2040s OUTBREAK med=1.3883
  t=3120s STEP-UP med=2.0881
  t=3180s OUTBREAK med=2.0880
  t=3240s STEP-UP med=2.4746
  t=3300s OUTBREAK med=2.4746
  t=3420s RESTART(recovery) med=0.0000
  t=4440s OUTBREAK med=0.8408
  t=4740s STEP-UP med=2.0255
  t=4800s OUTBREAK med=2.0255
  t=4980s RESTART(recovery) med=0.0000
  t=6120s STEP-UP med=0.3886
  t=7260s OUTBREAK med=1.0957
  t=7620s STEP-UP med=0.5307
  t=8220s OUTBREAK med=0.9935
  t=9060s STEP-UP med=0.4351
  t=9540s OUTBREAK med=0.9151
  t=10920s STEP-UP med=0.5046
  t=11220s OUTBREAK med=1.0050
  t=11520s STEP-UP med=1.3617
  t=11580s OUTBREAK med=1.3617
  t=12600s STEP-UP med=1.0816
  t=12660s OUTBREAK med=1.0816
  t=17880s STEP-UP med=1.4977
  t=17940s OUTBREAK med=1.4965
  t=18060s STEP-UP med=2.3753
  t=18120s OUTBREAK med=2.3753
