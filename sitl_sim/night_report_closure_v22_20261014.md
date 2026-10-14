# 全域收尾清零册夜报（第廿二周期，2026-10-14 夜；单册制收官）

执行=全域收尾执行者（ZCode 会话）。任务书=plans/执行中/2026-10-12_全域收尾清零_v1.md。
通道：3090 直连超时（DHCP 第三案延续）→ nuc2j 跳板（DERP）全程；旧机腿经 3090 中继只读+轻件（禁起栈裁定遵守：本册零旧机起栈）。
git：abd1032（u1 非栈三件）→f681906（u2/u4）→97e8746（u3 月报）→7c58608（u1.1/u1.4），四笔全推（UAV_NUC/main=HEAD）。

## 三态对账（保底清单 ⑩ 逐条）

| # | 保底项 | 三态 | 凭据 |
|---|---|---|---|
| ① | 单元 0-5 全执行 | **PASS** | 本册全部单元毕（见下逐项+清账版）；单元 0 收件=git 核（ahead=0 ③C 已自推）+残场全零+df 双机+六工具锚全中 |
| ② | N6 修正路径彩排实证（判据预注册+对照） | **PASS** | 判决书 rehearsal_n6fix_verdict.md（md5 9b55f06a，台账在位）：ctrl=REPRODUCED（90s 零反应）+fix1=PASS（单点停流 21s 落地链）+fix2=PASS（全家杀 39s 落地链）；prereg.txt 三轮跑前锁定；机理链代码级+时序级双源；两废轮注记在案 |
| ③ | dashboard 联动判定自动 PASS 自证 | **PASS** | a3_recheck_v7.sh 对 010939 实物重跑=A3_RECHECK=PASS（csv alarms"单帧跳变:RED"两行命中）∧ v6 旧模式同数据=FAIL（对照成立）；第一路走通无需 1.1 顺采（1.1 轮未含 D4 段，两路一路达成即合规） |
| ④ | 1Hz 采样器实采验证 | **PASS** | 短窗验证（roscore+发射+tail：sampler.tsv 1Hz 六行+sampler.out 摘要行+清理净，evidence/sampler_shortwin_test_20261014/）+三轮 N6 彩排实载（1Hz fsm/armed/z 轨迹落盘，fix2 因果链判定正源） |
| ⑤ | 两袋搬运 md5 对账 | **PASS** | t2v3_ground_205302.bag（1.6G，664e881e）+v1_ground_salvage_211520.bag（30M，28fe5193）双端逐位一致；closure v2 确认引用源路径先行；旧机只读零改动 |
| ⑥ | closure NUC 侧差集表 | **PASS** | 双侧实例（3090 含 ssh 探针+旧机 --no-nuc）+差集表 closure_dual_diff_20261014.md：present 199 共同+3+3 单侧载体（2 项经⑤闭环+1 衍生 stem+3 项 3090 域载体），新缺失=0 |
| ⑦ | 月报终并读数闭合 | **PASS** | 137+9=146（新条 52-60：专项①5+③C2+本册2；复发标注 6 处按模板规则 4 不增条）；前后读数+加总校验+节头节尾闭合；"实飞前夜终本（后续新坑进当期夜报）"注记落盘；双位 md5=6b53cbcb |
| ⑧ | 第五数据点评级三面 | **PASS** | memleak_5hwin3_rating_20261014.md：速率面（两段结构：前 300min 1.12-1.28GB/h+后 234min 0.20GB/h 骤降）+截断面（boot -4 终点 10:22:38 整机非正常停机实证，OOM 零记录排除，"非整机截断"推测勘误）+模型自洽面（前段隐含健康占比 51-59%） |
| ⑨ | STATUS 陈旧副本回收 | **PASS** | 旧机 ~/sitl_sim/STATUS.md→STATUS.stale_20261006.bak（411999B 原样保留）+原路径指针文件（313B 两行声明）+ls 凭据；旧机 git 核毕（pull 至 abd1032，两 untracked 注记） |
| ⑩ | 夜报+三态对账 | **PASS** | 本件 |

## 可做而未做清单（穷尽制检视）

**应收全零**。条件注记件（非未做，域边界如实列）：
1. fix1 真 RC 拨杆面（CH6 物理语义）：no_RC=true 栈结构性不可达（px4ctrl_node.cpp L65 不订阅 RC+上游 mavros 假 RC 注释）→归首飞窗现场确认件（与 CH5 手动终极面同类 SITL 覆盖边界；rc_cmd 断分支与已实证的 cmd_ok 断分支 fsm 同构）。
2. W-用户：旧机起栈时机（用户在场操作期，本册未触碰——裁定②遵守）；动力套窗预授权链维持。
3. ③C 续作册坑账：其清账版坑已按任务书指定四件提取并入月报；③C 后续新坑随其自身夜报自理（终本时点界已在月注记）。

## 本册新坑（已入月报 146 终本，此处仅索引）

 DERP ConnectTimeout=20s 必超时（≥45s 稳）/git commit pathspec 漏 `--`/ssh×2+awk 三层转义崩（A18 复发）/n6fix 首版 fsm_now 抄漏 awk 管道段（工具函数抄写逐字符核对教训，月报 56 条族）。

## 产物指针汇总

- 台账（3090 t1_evidence/preflight_boost_20261011/）：rehearsal_n6fix_{ctrl_194040,fix1_195548,fix2_194738}/（三轮全产物+prereg+obs+sampler+bag）+两废轮（ctrl_193122/fix1_194334 注记档）+rehearsal_n6fix_verdict.md（9b55f06a）+a3_recheck_v7.sh+sampler_shortwin_test_20261014/
- 判读（3090 t3_results/）：j0d_rehearsal_20261014/（两袋 j0_decomp.json）+j0d_stats_20261011.csv（437→439 滚入行）
- T4 域（3090 t4_evidence/）：t4_ref_closure_20261014{,_nucside}.md+closure_dual_diff_20261014.md
- memleak（3090 t1_evidence/）：memleak_5hwin3_rating_20261014.md+vins_mem_watch_v537_5hwin3.csv 副本
- 月报：t4_evidence/pit_monthly_report_v526.md（6b53cbcb，146 终本）
- git：abd1032/f681906/97e8746/7c58608（全推）；n6fix_rehearsal.sh v3=93b19163+rehearsal.sh v7=02ed76a7+rehearsal_sampler.py=4f78e836（双位一致）
- 旧机：STATUS.stale_20261006.bak+指针文件；repo=abd1032
