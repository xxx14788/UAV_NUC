# T1 任务书 v11.21 — v11.20 完成清账版（2026-10-07 10:1x 落盘；tag sitl-v0.4 已打；v11.20 弃读）

> 你是 **T1（px4ctrl/基础设施+飞行批执行线）**。执行域=3090（`ssh nuc2`）。红线 1-24 沿用。
> 台账=3090 `~/sitl_sim/t1_evidence/v11_20_2026-10-07/`（本册不新开战役目录，清账续用）。
> 本册性质=完成清账版：A=v11.20 八件完成事实；B=剩余件；C=卡点客观陈述（**只述问题不载方案**，方案归下任会话与用户裁定）；D=资产 md5 表；E=等待登记。
> **头条（双必达齐）**：①定因表闭合（红线级）=四件对账全排除+H5 存续，T2 独立复算四✅签认；②tag 路径走完（打成）——**tag sitl-v0.4 @ 04:10:54**（机器钟，T3 在册），X4 无门基线批 **5/5 全物理**（物理绿 5+门拦截计入 0）∧ 内嵌 trichotomy 全绿 ∧ T3 影子复核 7/7 逐位（X4_T3_REVIEW_CONFIRM，与终账 206506c5 逐位一致）。臂=v2+cauchy4（config **054ddc8d**=arm_xline arm 装载态，当前仓库即此态）；栈 721cad40/5bacc2e9 全程零变动。
> 跨线现行册：T2 v10.2 / T3 v10.4 / T4 v5.22（均 10-08 前后落盘，引用以现行册为准）。

## A. v11.20 完成清账（八件）

### A.1 单元 0 开工收尾 — 完成
四册 Windows 权威+3090 双份备份 md5 逐位一致（T1 cb513090/T2 71476ef4/T3 c87ed84a/T4 f812062f，战役目录内同份再备份）；git pull=e4b63f6；残场零残留（孤儿 rosout 198057 清）。

### A.2 单元 4 定因机械腿（红线件）— 完成，闭合达成
- 四件对账（t1_causation_legs.py，判别门预注册在脚本头；对照组=巨跳 6 vs 绿格 11+held-out 2）：
  - **L1 PX4 参数写回=排除**：绿格稳定结构参数 858 个全一致、跳轮零偏离；CAL_/COM_FLIGHT/LND_FLIGHT_T_ 开机易变参数 14 个绿格内本就逐 boot 变动；跳轮出绿格分布 3 例——E5O（MAG0_ZOFF 越界 2.7%）、E12P（MAG0_XOFF 越界 2.9%）、**E5P（GYRO0_XOFF 7.4×/GYRO0_ZOFF ~40× 大幅出界）**；机理阻断=VINS imu_topic=/mavros/imu/data_raw（原始流，CAL_* 不入 VINS 输入）。注：E5P gyro 偏置异常幅度对 PX4 姿态面（EKF2/px4ctrl 消费 CAL 后 IMU）的含义未评估（见 C.12）。
  - **L2 config 漂移=排除**：全 19 轮同 md5 054ddc8d（批内零漂移）；表内"当前仓库 5c98dc0d"系定因表写作时点值=v11.17 批后 canonical restore（在册），03:15 arm_xline arm 装载后已复处 054ddc8d（X4 批飞态）。
  - **L3 机器态 hwmon=排除**：预注册门（freq<0.85×自身前段 ∧ ctxt/load>绿格 p75×1.5）0/6 跳轮过门。
  - **L4 负载 RTF=排除**：跳组中位 1.017 vs 绿组 1.049（差<10% 门内，绿组反高）、无 <0.80 轮；slack=disarm↔bag_end 0-15s 未扣（组间不翻转；T2 全程 wall 口径 0.86-0.88 复算口径差注记在案）。
- **H5（估计器内部或输入面）=存续**；T2 裁决面收窄=「估计器内部（静默型 6/8 主体）×输入面（plain×E 易感条件）条件性耦合，单支不闭合」（两线结论相容）。
- T2 复核签认四✅（causation_review_t2.md；H3 对齐窗微差 0.25%/H4 口径差注记）。
- 后夜互证：T2 59 轮 j0d 批（v10.2 A.36 行）修正 jump_prepost=终态漂移口径，"巨跳 8"=transit 慢漂主导 5/8+真单帧跳 3/8（E12P/E8P_224044/SE8O）——与本表"t_jump 对齐口径差"注记一致，门结论不翻且更强。
- side-finding：绿格 cost 瞬态峰比 10-104（单峰不判别）→ 被 T2 科学包 §1.2 采纳。
- 产物：`causation/{leg1..4 json, round_index.json, cost_curves 19 轮 TSV, causation_summary.md, causation_table_draft.md(a404013e)}`。

### A.3 单元 1 双门工程落码 — 完成（代码面；参数冻结流程作废见 C.3）
- t1_gate_watch.py(70c8ea98)：同核三模式引擎（--pregate/--inflight/--replay）；cost 主+|Bas| 副、绝对+轮内自适应双门；起飞检测=odom z 主探（0.25m 持续 3s）+V 兜底；0.5s 步进求值；gatehit 字段对齐 T3 trichotomy 契约（t_trig/value/action/landed；pregate 终拒=block）。
- vins_smoke.sh --gate 六挂点：1a 起飞前门（REINIT≤2→ENV-ABORT exit6）；1b watchdog+t1_rtf_probe.py 随轮；gate_abort 受控中止链（降级序①odom 可信段 LAND ②悬停+kill；回写 gatehit landed/disarm；RESULT=GATE-INTERCEPT 带 recovery=COMPLETE/DEGRADED）。
- t1_gate_params.json(12d93bcd)：占位冻结制（version=PLACEHOLDER-T2-PENDING-v0，frozen=false，null=OBSERVE）。
- x4_batch.sh 融合版(6cfef742)：T3 v10.3 三列分账/trichotomy 权威/双链 tag 为基+T1 增量（新五位形/替补顺位 6-7/带图条件件/--expect-cfg 凭据换代/--no-gate 模式/rosmaster 域过滤清场/动态队消费）。
- 干测：合成 gatehit 轮→trichotomy=gate_intercept 契约测试过；绿格 replay 起飞检测稳定 ~31.9s/基线窗落位/OBSERVE 不触发。
- commit a655cae→2e9888f→64f81b8（wl 热修）。

### A.4 单元 2 ROC — 完成，判决=零工作点（门不可靠）
- T2 门科学包收货（gate_science_v1/）：六面检验全负+病理分型 GREEN11/A6/B14/C5+条件绿率实际 30.6%（上限 68.8% 不可达）+起飞前门不成立（E8P 反例 init 健康带内）+选格收窄建议（默认案自动安全）。
- T1 同核 ROC（t1_roc_v1.py，64 组合网格）：**零工作点**——零误拦域最大捕获 2/6；捕获 6/6 需≥6/11 误拦（两端互斥）。
- 双线独立互证→预注册无门基线分支机械生效（门禁上真轮作绿率提升器；判读不带门语义）。
- ROC replay 对历史轮目录写入 43 文件污染已清（引擎副作用，见 C.8）。

### A.5 单元 3 X4 冲刺 — 完成，tag 已打已推
- 批进程内 5 轮（03:18-03:35，E12O/NE8O/NE12O/S12P/E8O 顺序）；wl-bug（judge_round w()/tee 被 $( ) 捕获→CLASS 多行→case 永失配，v9.9 起潜伏）致批级分账/替补入队/带图条件件/5-5 收束全失能，批按序跑完 5 格走 else 收束；轮判读落盘全程不受染（T3 裁定损害边界）。
- 批外手动 4 轮（预注册规则手动执行）：S8O 替补#1（03:38，带图）/N8P 替补#2（03:45，带图）/1e 两轮（03:53/04:00）。
- **七轮 trichotomy 形式重账=终账正源**（x4_final_tally.md=206506c5）：phys_green 5=E12O(0.252/0.278) NE8O(0.034/0.037) NE12O(0.234/0.220) E8O(0.081/0.156；wa_gate cf 字段缺失如实，PASS 轮判读不依赖) N8P(0.094/0.083)；true_fail 2=S12P（jump 4.700 B 型，plain 南向→换格#1）+S8O（jump 0.487 C 型，starve 修复实战触发并恢复后 TIMEOUT 慢）。物理轮 7/15、换格 2/2、撞门 0、ENV 0；phys-floor 5≥3 ✓。
- 双链：内嵌全绿 ∧ T3 影子复核 7/7 逐位（影子三链独立重跑+goal.txt 正源；N8P 补抽含——T3 审计窗 03:51 早于第 5 绿收口，04:05 补审请求→04:08 CONFIRM，与终账逐位一致）。
- **tag sitl-v0.4 @ 04:10:54**（annotated，commit dd8dfda 处，UAV_NUC 已推；成色注记在 tag message：no-gate baseline/phys=5+intercept=0/双链）。批内 tag_if_5_5 因计数失能未触发，tag 打点=批外按三硬条件机械执行。

### A.6 单元 3b 保底六件 — 全落
①双门工程全套代码+干测 ✓；②ROC 材料+灵敏度曲线+失败原因 ✓（零工作点=判别特征不存在，非阈值未调好）；③定因表闭合 ✓（红线级）；④无门基线数据 ✓（超额 7 轮+2 带图标本）；⑤T3 口径落码 ✓（trichotomy 消费融合+wl 热修 64f81b8；T4/X7 件归其册）；⑥STATUS 诚实汇总 ✓（夜报 v11_20_night_report.md=76c14d37）。

### A.7 1e 带图标本（T2 设计件执行）— 飞行面完成，回放裁决=T2 域未消费
- run_X4_1e_E8P_035301：3.12m 跳+带图 13G（E8P 格史 4/4 跳，首份带图标本）。
- run_X4_1e_HVNET1_040009：悬停复刻 4.12m 跳+带图 13G（悬停也跳；无 transit 相）。
- STATUS 已移交 @T2（04:2x 行）；T2 v10.2 清账版（10:08 落盘）C.2/C.3 仍载"新标本未飞/等待 T1 编排"——**其写作时点未收本批，回执义务在 E**。两标本的 j0d 分型（真单帧 vs 慢漂）未验（T2 域）。

### A.8 碰撞与事故处置（如实）
- git 裹挟 T3 staged 三歧件×1（5bfdeee）——STATUS @T3 注记，T3 收认。
- x4_batch 工作树误覆写×1（T3 未 staged 增量被 scp 覆盖）——两版保全（/tmp/x4_batch_T1v1120_overwrite.sh+入库版还原），以 T3 入库版为基融合零语义丢失；/tmp 易失注记。
- wl-bug 谱系勘误：首报"T3 基座丢失"措辞有误——实为 x4_batch 骨架 v9.9 起同坑（T3 版继承原骨架；x5_batch 有 19:35 热修而 x4_batch 无），终账已更正。
- pgrep -f 自匹配假阳性×2（已知坑复发）；ssh 中文直写乱码（scp 通道+字节验证）；T1 STATUS 手写时间戳漂移乱序（见 C.11）。

## B. 剩余件（未做/未完成）

1. **1e 回放裁决未执行**（归 T2 域）：两带图标本在盘未消费；按其 x4_bagench_design_v1 §3 判别判据（≥2 复现=输入面实锤/0 复现=运行时面实锤/1-2 或形态漂移=混合型）回放未跑。
2. **H5 定谳挂起**（依赖 1）：定谳后两条后续均未启动——估计器内部修复立项（init 质量根治/bias 约束族）/输入面场景分门（远期池件在册）。
3. **门工程资产定级未裁**：双门代码在库但参数永未冻结（frozen=false 恒 OBSERVE）；jump 后置检测止损件（10Hz |ΔP|>1.0m，巨跳 7/8 可定位）=唯一有实证价值的门件，未落码未启用。
4. **rtf 连续面零采集**：t1_rtf_probe.py 仅在 --gate 下随轮挂载，X4 批走 --no-gate+1e 两轮手动发射均未带 → 今夜 9 轮全无 rtf.tsv；L4 定因表 slack（连续 sim/wall 曲线缺）依旧未填。
5. **X4/1e 新数据未入 T2 科学件**：S12P（南向 plain B 型=E×plain 聚集带外新跳例）/N8P（plain 绿=plain 非全毒）/S8O（C 型新样本）+9 轮的 j0d 扩表与病理分型更新（T2 域）。
6. **悬停谱系呈报件改写未做**（T2 2d 件材料变化）：历史 hover n=4 全绿+HVNET1 自跳一例 vs 今夜复刻又跳 4.12m——悬停第 5 格候选证据链需重写（T2/用户裁定面）。
7. **wl-bug 同骨架排查未做**：x4_batch 已修，该骨架派生脚本（若有）未排查 $( ) 捕获坑。
8. **X7 终稿**（X4 定局后 24h 窗——tag 04:10:54 起算，截止 10-08 04:10；归 T4/T2 册）。
9. **T4 backlog 消费**（归 T4 册）。
10. **tag 后实机差距清单**（用户域）：sitl-v0.4=SITL 域里程碑，实机迁移差距未盘。

## C. 卡点客观陈述（只述问题；方案归下任会话/用户裁定，本节禁载）

1. **跳变族前兆判别特征不存在（双线否证定案）**：绿轮 cost 天然 lift 10-50×（健康生理性增长 GROUND→POST 8-20×，跨世界基线差 ~10×）；巨跳轮 E12P（35.97m 口径/j0d 修 22.8m 真单帧）cost/|Bas|/track/视差面全程静默。任何基于 [T2slv]/[T2diag] 观测指标的预警门在 X5 域 59 轮上无 (R,N) 工作点（T2 六面+T1 同核 ROC 64 网格独立同结论）。个体级前兆真实存在但仅 2/8（提前 40.7-47.5s），群体级不可用。
2. **H5 两支分叉未定谳**：判别实验=带图回放，材料已备未执行（B.1）；悬停复刻跳将输入面嫌疑收窄至场景静态内容，但 E12P_R2 同配置同格不巨跳=输入面是易感条件非充分原因——两支单方闭合证据均不足。
3. **门参数冻结流程作废后的资产悬置**：t1_gate_params.json 恒 frozen:false；带 --gate 的批会被 preflight ABORT_GATE_PARAMS 拒（防呆在），--no-gate 为唯一可飞路径；"双门代码在库未用"的定级（保留/退役/jump 后置止损件单独立项）无归属决定。
4. **带图取证的结构性矛盾**：13G/轮×磁盘 528G 剩余=全批带图不可行，只能定点取样；跳变发生不可预知（E8P 格 4/4 高发 vs 随机格偶发），定点格选择与"抓到事件"的概率耦合；且两份新标本的 j0d 分型未验——若属慢漂型则对"真单帧跳分叉"判别价值降级。
5. **starve 病灶未除**：S8O 再证修复链有效（FSM 停摆→重启→poscmd 恢复 100Hz），但事件循环冻结根因（timer stop/start 自愈路径失灵面）仍在，每次触发消耗一轮预算。
6. **T3 影子审计窗与批推进窗异步**：审计窗固定（到货+90min 承诺）vs 批终点不可预知——本次审计窗早于第 5 绿收口，靠补审往返闭合（04:05 请求→04:08 CONFIRM）；批终点与审计窗的对齐机制不存在。
7. **plain 世界方向选择性无机理**：E×plain 3 格全 A 型+N8P（北）plain 绿+S12P（南）plain B 型跳——方向×内容交互有统计画像无因果解释；E12P_R2 同格不巨跳=含非确定性成分。
8. **bash $( ) 捕获陷阱谱系**：判读函数内 echo 回 stdout 的写法在批骨架潜伏 v9.9→10-07 两夜实锤；已修 x4_batch/x5_batch，派生未排查；ROC replay 向历史轮目录写 gatehit/pregate 的副作用同族（43 文件已清，replay 评测无自动清理步）。
9. **网络拓扑非终局**：NUC=.6 过渡（用户知情裁定）；3090 不在 tailnet——Win-WLAN 断连窗口 3090 不可达（批自跑本机落盘缓解数据面，操控面不可达仍在）。
10. **悬停格证据链矛盾**：n=4 全绿画像与 HVNET1 自跳一例与复刻又跳并存——悬停是否安全格的现状证据互相冲突。
11. **STATUS 手写时间戳漂移**：T1 三条行手写标签（03:50/04:2x/04:15）与机器锚点漂移且表观乱序（tag 实际=04:10:54）；机器权威锚=git commit 时间/轮目录名/round.log 行/对侧引用。
12. **E5P gyro CAL 偏置异常的非-VINS 面未评估**：GYRO0 偏置出界 7-40× 机理上不入 VINS（data_raw 阻断），但 PX4 姿态面（EKF2/px4ctrl）消费 CAL 后 IMU——该异常对控制链的含义未评估（该轮失败归 VINS 跳变，与姿态面区分度未做）。
13. **批飞行窗互斥=单侧通告**：X4 发射前 STATUS 通告 T2/T3/T4 停回放/大 IO；对侧实际停否未核（T3 j0 批 03:0x 仍在跑，与飞行窗重叠实况未确认），且本轮零 rtf 采集无法事后回查飞行窗机器负载。

## D. 资产 md5 表（3090 `~/sitl_sim/t1_evidence/v11_20_2026-10-07/`；repo 镜像 `~/catkin_ws/sitl_sim/t1_evidence/v11_20_2026-10-07/`；commit 链 5bfdeee→a655cae→2e9888f→64f81b8→dd8dfda→1e1c04b 全推）

| 件 | md5/标识 | 说明 |
|---|---|---|
| 定因表 | causation_table_draft.md=a404013e | T2 签认件=t2_results/gate_science_v1/causation_review_t2.md |
| 四腿原始 | causation/leg{1..4}_*.json+round_index.json+cost_curves×19 | 判别门预注册在 t1_causation_legs.py 头 |
| ROC 判决 | roc_v1/roc_verdict.json=b738af4a（sensitivity 64 行/pregate 面） | 零工作点 |
| X4 终账 | x4_final_tally.md=206506c5 | trichotomy 全轮形式重账正源（T3 背书逐位一致） |
| T3 复核 | X4_T3_REVIEW_CONFIRM=35562b54 | 双链第二链（7/7 含 N8P 补抽） |
| tag | sitl-v0.4 @ dd8dfda（04:10:54，UAV_NUC 已推） | 成色注记在 tag message |
| 夜报 | v11_20_night_report.md=76c14d37 | commit 1e1c04b |
| 双门代码 | t1_gate_watch.py=70c8ea98/t1_gate_params.json=12d93bcd/x4_batch.sh=6cfef742/t1_roc_v1.py=ea3efd4b/t1_rtf_probe.py（sitl_sim/） | vins_smoke.sh 为修改件（--gate 六挂点） |
| 1e 标本 | run_X4_1e_E8P_035301（13G）+run_X4_1e_HVNET1_040009（13G） | 带图 flight.bag；回放裁决=T2 域 |
| 批原始 | x4_launch.log/x4_batch_report.md/x4_gatehit_stats.log/x4_passmap_live.log | 批级账目失能段有注记 |

## E. 等待登记

- **W-T2 回执（本册落盘即发）**：①1e 两带图标本在盘（run_X4_1e_E8P_035301 3.12m+run_X4_1e_HVNET1_040009 悬停 4.12m）——其 v10.2 C.2"新标本未飞"阻塞已解除；②ROC=零工作点收案，t1_gate_params.json 恒 frozen:false（其 W-T1 门材料消费回执两支的答案）；③X4/1e 九轮 j0d 扩表+悬停谱系改写（B.5/B.6）材料在盘。
- **W-T2 1e 回放裁决**（≥2 复现=输入面/0 复现=运行时面）→ H5 定谳 → B.2 两后续解锁。
- **W-X7 终稿**（截止 10-08 04:10；归 T4/T2 册）。
- **W-用户裁定面**：门工程资产定级（C.3）/悬停格证据链矛盾处置（C.10，T2 2d 件联动）/tag 后实机差距清单启动（B.10）/E5P 姿态面评估优先级（C.12）。
