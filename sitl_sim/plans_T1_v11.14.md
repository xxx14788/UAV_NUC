# T1 任务书 v11.14 — 完成清账版（2026-10-06 晨；只含待办；v11.13 弃读，纪律溯 v11.7）

> 你是 **T1（px4ctrl/基础设施+飞行批执行线）**。执行域=3090（`ssh nuc2`）。
> 本版=v11.13 会话完成清账（用户指令款）。A=全清账+证据指针；B=剩余（用户面）；C=卡点；D=资产 md5；E=等待登记。

## A. v11.13 会话完成清账

### 单元 1 排查双刀（~30min 计划，实收 40min，定案级产出）
- **风暴根因实锤 = CauchyLoss(0.0) NaN**：X 线臂 v1 sed 设计"cauchy 关"=vision_loss=1∧cauchy_delta=0.0 → ceres::CauchyLoss(0/1.5)=0·log(∞)=NaN（estimator.cpp:1337）。风暴形态⇔该二元组合 **5/5 跨 boot 无一例外**（boot-1 SUPX2a/X2b/HV2a/HV2b+boot-2 VRFY1）。RA13/14 实为 cauchy=4.0+v3 栈（**非同键**，verify_verdict_v119"boot-0 同键干净"支柱勘误）。机器态假设对风暴面降级。六项 diff+机理链=boot_diff_report.md（ad177c91）。T2 独立推导互证（commit 623202c）+T3 全库矩阵三歧行（43 轮 0 四绿=Z 成立）合流。
- 实锤分支执行：arm_xline.sh v2 臂（vision_loss=0/Huber，保留 cost_gate/staged/guard，sed 源值守卫；062d406e）+x4_batch.sh 臂门双升级（preflight config 四键校验+轮内 T2 knobs loss=0 校验，banner 盲区闭合）。
- **VRFY2 验证轮全绿**（X2③ 同构对照 VRFY1：init 102s→3s/T2fail 110→0/NaN 1066→0/四指标 1/1/1/1 PASS 到位 0.176m）——根因闭环飞行面确认。D-1006-T1-09 在册。

### 单元 2 X4 五位形批（FAIL 汇总收卷，0/5 不打 tag）
- **终态=0/5**（诚实认证条款）：8 物理轮全灭。分母 fail 4（X1final 5.03m/X2g1R 8.33m[starve]/X2g3R 4.79m/X3l2b 4.18m）+hostile 1（X3l2a，FAILDET×14，不计分母）+未定案 1（X2g1_041509 判读被杀）。终判文=x4_final_verdict_v1113.md（b5ca92a6）。
- **三层病灶分离（核心知识产出）**：①NaN 层=v2 臂批级消灭（8 轮零 NaN）②goal 段 VINS 帧跳变族主导（5/8 轮，巨幅 24-37m 两例；**X2g3 同位形 04:05 绿 0.100→05:01 跳 24.2m=时间维度转折材料**）③planner starve×2（harness goal 订阅竞态，VINS 面完美，T1 遗留修复件）。
- 双链核验制：0/5 未触发 tag 链；判读链=补判版权威（rejudge_rounds.sh）。
- 伴随事故四件入册（D-1006-T1-10）：judge_round 三 bug（RES 前缀失配=绿轮永不计绿/grep -c 双 0/NEVER 未 local——dry-run 不跑 judge 故首真轮暴露；修复 9592f96c）+批死于启动会话关闭连带（setsid 不足，改单轮发射制）+串行补飞链被 pkill 自匹配杀（cmdline 含 vins_smoke.sh 字样）+T3 拷贝窗撞车嫌疑窗登记（run_X2g1_041203=NUC 历史轮副本混入，非撞机）。

### 单元 3 对照批（三歧断案器收官；contrast_batch_verdict=8404bbff）
- hover 净轮×2：HVNET2 **全绿净轮**（jump 0.136）+HVNET1 物理净/VINS 跳 2.985m 标本（悬停面跳变跨 boot：boot-1 SUPHV3b 3.9m 同型）。
- **RAREP1 复刻轮 PASS 全绿**（cauchy=4.0 全家桶@v4 栈+boot-2，到位 0.095/init3s）——boot-1 never-init 未复现+同位形 17 分钟前 v2 臂跳 24m=臂间对照素材。
- 终版三歧：Z=NaN 臂专属已解；C=排除（cauchy=4.0 跨栈绿）；M=**收敛为时间维度/会话面嫌疑（非 boot 维度）**。

### 单元 4 本线域件（全清）
- L-odom U2.5 考古=**负结果闭卷**（六路径穷尽未果；灭失不阻塞——U2.5 已判 L-odom 臂=mavros 帧域修复面，重建挂上游修复决策；lodom_archaeology_20261006=6772768d）。
- 探针 jump 面扩样=闭环（VRFY1 4×1.771 vs VRFY2 0×0.093 vs 批轮 X1final 5×18m/X3l2b 2×7m，prop 全库恒净；jump_probe_expansion）。
- G1 strace 就位确认（t1_g1_strace.sh+prep 在册待事件窗）；池恒≥3（等待池件无欠账）。
- 兜底层预写=hardware_escalation_playbook.md（触发条件/四清单/禁令）。

### 单元 5 代持件交还（STATUS 05:22 通告 @全体）
- T2 域：净轮素材（VRG1/VRFY2/HVNET2）+NaN 标本链（boot_diff+T2 互证 623202c）+never-init boot-1 特异性线索+臂间对照素材（X2g3R vs RAREP1）。
- T3 域：签收完毕（DECISION_LOG 390 回执）+X4 批 8 轮新素材袋（五轮带图袋保全至 X7 条款维持）。
- T4 域：X4 0/5 不打 tag 收账（wake 条件不触发，以 05:22 通告行闭卷）。

## B. 剩余（按优先级）

1. **W-用户①：X4 终态裁定**——0/5 收卷材料=x4_final_verdict+contrast_batch_verdict；选项=接受收卷（病灶归因移交 T2/T1 修复件）/修复后重飞（planner starve 修+跳变族属 T2 域）/扩样（时间维度转折验证轮）。
2. **W-用户②：兜底硬件确认**（仅两节点：eno1 插线/AIC 黑名单——hardware_escalation_playbook 待命，触发条件未满足[guard 臂未连挂 3 轮跨位形]）。
3. T1 修复件：planner starve（goal 订阅就绪探测门）+autoattach 扩名补 HVNET|RAREP。
4. T2 域移交件：跳变族机理（时间维度材料全表在册）/never-init 特异性/cauchy 剂量（RAREP1 单样本）。

## C. 卡点

C.1 X4 重飞挂用户裁定；C.2 WiFi=batch 单轮发射制已立（幂等受会话关闭坑约束）；C.4 H-A 残面在案（跳变族时间维度=新面）；E-4 袋指认（等对侧）；B 路 HF 重标（@T2）。

## D. 资产 md5（3090）

round_result=c708151f / prereg=b72e5126 / 栈=b7de133d+59548c6a / **canonical=5c98dc0d（restored）** / arm_xline.sh=062d406e（v2）/ x4_batch.sh=9592f96c（judge 修+--skip+双链）/ rejudge_rounds.sh（新）/ boot_diff_report=ad177c91 / x4_final_verdict=b5ca92a6 / contrast_batch_verdict=8404bbff / lodom_archaeology=6772768d / kill=9bf5c785 / land=75671efa / 磁盘 593G→（袋增量后 df 自查）。

## E. 等待登记

W-X4-final 用户终态裁定（头号）；W-硬件（兜底两节点）；W-E EXP-2 归档态；W-对侧（T2 跳变族材料消费/T3 复核链解除[未触发]/T4 收账回执）。

## 悬案池（本会话新增）

①跳变族时间维度转折（04:05-04:09 窗，同 boot 同臂同位形绿→巨跳）②planner starve 间歇竞态（2/8）③批/链会话关闭连带死亡机理（setsid 不足面）④X2g1_041509 未定案轮补判（bag 保全@T3）。
