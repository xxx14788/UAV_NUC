# U3″ 在线验证轮预注册(2026-10-02 02:2x;先于任何起飞写定;栈=lib 5dde4d7e+vins_node 86c5c6a3 双 md5)

## 背景(判别格结论驱动)
回放域对 R2F/cost 门判别无判别力(回放输出非确定,|dP|p50=0.5m>门效应)——**生死判定=在线轮**(红线11)。本轮=canonical vs t2gates(min_disparity=2.0+cost_gate on)双臂在线对照。

## 臂设计(5 轮,全紧凑袋口径=无图;带图素材由 T4 注入代供给,本轮判据不需图)
| 臂 | 场景 | VINS_LAUNCH | 目的 |
|---|---|---|---|
| A1 | route | sim_vins_t2gates.launch | cost 门对 R3 急冻形态的 RESCUE 判定主臂 |
| A2 | route | sim_vins.launch(默认) | canonical 基线臂(急冻形态复现期望=零 fail+漂移) |
| A3 | hover | sim_vins_t2gates.launch | R2 载体域门臂(33.7s Bas 爆形态对照) |
| A4 | hover | sim_vins.launch | hover 基线臂 |
| A5 | ground | sim_vins_t2gates.launch | 纯回归臂(R2F 饥饿面:悬停/静置 far 特征剔除的供给安全) |

## 判据(预注册)
1. **门活性**:每 gates 臂 vins.log banner 实读(T2_MIN_DISPARITY: 2.000/T2_COST_GATE: 1)+far_drop 计数>0+supply(near)不长期 0(饥饿未触发);[T2depth] far_drop 行可聚合。
2. **cost 门生死(主判据)**:A2 若复现急冻形态(odom 对 GT 误差>10m 急窗)且 A1 ①无急冻或②出现 "cost gate: streak" 触发 reboot 后恢复跟踪→**RESCUE 成立**;A1/A2 同现或同缺→**不成立如实记**(禁放宽/禁阈值回调,按预注册分支回挖)。A2 零复现(在线非确定性)=单轮不定案,记 inconclusive,不外推。
3. **R2F 形态级**:A3 vs A4 的 Bas 爆(>2.5 fail)/首 fail 时点/存活时长形态对照;门开臂无恶化(首 fail 不提前>5s 且 vis_n(track)不坍塌>30%)=无害底线。
4. **回归门**:A5 零 [T2fail]+对齐后 ATE_p95≤0.1m(U3PG 基线 0.03m 的容差带)+v_max<1m/s(静置)。
5. **跳变计数交付(@T1)**:每轮 odom 流 |ΔP|>0.5m 计数/maxdP/v_max 表(A.4 重估输入)。
6. **到位统计**:round_result 口径(场景分门:route 0.5m/连续 3s;无图紧凑袋含 model_states 可判)。
7. 慢漂域标注(按 R3):急冻形态=odom 误差曲线阶跃+冻结;如实区分于慢漂。
8. ENV-FAIL 三签名(无 vins banner/无 odom 流/无 GT)+每轮 pgrep CLEAN+每轮起飞前双 md5 实读。
9. 达标门(单元6 触发条件):**VINS 域零 failureDetection 触发(自然死亡)×5 轮**且 cost 门若有触发则其 reboot 后恢复=按预注册算达标;U3PH 型 Bas 爆若 A4 复现而 A3 消除=R2F 贡献;两臂同爆=Bas 爆非本门可治如实记(达标门只看零 fail——[T2fail] 含 Bas 爆=fail,故 Bas 爆即不达标,如实)。
10. 磁盘:紧凑袋 0.3-0.5G/轮×5≈2G,df 33G 前→后≥30G 预期;若任一轮 df<20G 禁下一轮。

## 执行纪律
- SITL 锁:本轮占锁前 STATUS 预告 15min 异议窗(任务书单元4 条款);与 T1 X 线冲刺互斥(T1 已声明等 U4 通告,顺序=T2 在线轮→U4 通告→T1 X 线)。
- 每轮间 pgrep CLEAN+锁活性验。
- 轮序:A5(回归最快出)→A4→A3→A2→A1(基线先于门臂,形态预期锚定)。
