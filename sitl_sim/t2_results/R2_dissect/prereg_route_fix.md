# 预注册：route 假盆地修复面两案复裁（prereg_route_fix，2026-10-04 v1）

> T2 v8.9 单元 1/2。先于任何复裁数据冻结。判据禁放宽（任务书红线，永久）。
> 依据链：v8.3 单元 3 depth-gate 臂证伪（冲突约束：载体清除 vs init 质量）→ 修复面改判两案（分阶段门/W4 线可配化）→ 用户 10-03 晚批两案同窗写码。
> 三题收缩定案（10-03 深夜）：A 假盆地=唯一堵点；机理=猛动态×障碍→双目匹配几何性失败→负深伪注入 13-28/帧→init 后 4.3-78.7s 脆弱窗拖 Bas；点火=异步时序运气。

## 修复面（两案分臂禁混测）

- **案 A 分阶段门**（`t2_staged_depth_gate:1` + `t2_staged_n_sec:80`，W4 线默认 0.5）：INITIAL 填窗期+init 完成后 80s 恩典窗（VR2 十五段再造起点 4.3-78.7s 的保守上界）保留 INIT_DEPTH 伪注入（solveGyroscopeBias 特征量保底）；NON_LINEAR 且过恩典窗的稳态期，stereo/motion2/svd 三分支与 t2_depth_gate 同策略拒收（负深/量程外 track 剔除）。clearState 归零=再 init 自动回填窗期（活锁结构防御）。
- **案 B W4 前置线可配化**（`t2_w4_bgs_thresh:5.0`，staged=0，depth gate 关）：前置门 Bgs 线 0.5→5.0。臂值依据=depth-gate 活锁窗实测 Bgs 越线带 0.62-5.63（7 连 gate reject）；5.0 覆盖带主体、保留 5.63 极值拦截（极端保护不全撤）。语义=特征弱期 Bgs 解劣的 init 尝试不再被前置门掐灭（活锁另一半路径解除），init 质量交给后置门+优化自修。
- canonical config 零新键=逐位不变（默认 staged=0/w4=0.5）；[T2GATECFG]/[T2gate]/cost 触发行格式零改动，自证走新 banner [T2RFIXCFG]。

## 栈纪律

- 凭据栈=**fixface-3**（本 build 换代：lib+vins_node 双件存档+双 md5 登记；fixface-2 1d7d2302/47d4308e 退役存档保留）。
- 每轮起飞前实读双 md5 复核；config-only 生效以 [T2RFIXCFG] banner 字段核验。
- 复裁轮全部在线（红线 11：route 假盆地回放不可判；急冻回放不可达）；回放仅做单元 1 预筛（零回归/活锁粗筛，不判生死）。

## 轮次设计

route 复裁 4 轮（两案分臂各 2 起）：轮序 **A1, B1, A2, B2**（时序偏差防聚簇；goal 3,-2,1→0,0,1；obstacles world；紧凑袋；RECORD 全程）。每轮双 md5+紧凑袋+log 归档+CPU 采样；跳变计数 @T1。

obstacles 场景×2（终版补格：U3″ 10 臂无 obstacles、U4 五场景新栈缺此格）：判据=VINS 域零 fail/受控+到位记录（证据格语义非案间比较）；臂选择规则预注册：两案均达 R1→案A（载体清除面更根本）；仅一案达→达标案；均未达→案A。

## 判据（预注册，禁事后改）

**主判 R1**：route 复裁 4 轮中 ≥2/4 无假盆地成熟。成熟签名沿用 prereg_route_readj_v1（满足任一即成熟）：
  a. imu_propagate 位置离起点最大偏移 >10m（起飞后）
  b. 跳变计数（|Δp|>0.5m，imu_prop 口径）>10
  c. vins 日志 [T2fail] / cost gate 触发 / reboot 行出现
  d. 任务中止（未到 leg2 即落地/悬停超时）
  修复成败判读补充：成熟轮中"尾段假盆地"（尾 60s |P|p50>10m）与"爆窗瞬态后恢复"（尾段回归）分记——R1 计"无假盆地成熟"=四条全不满足**或**仅瞬态（尾 60s |P|p50<1m）。

**次判**（修复质量面，全部如实读数）：
- R2a init 质量不劣化：W4 拒收（gate reject 行）计数、banner 连发形态、首解 Vs/Bas 与健康带（Vs 0.008-0.020/Ps 0.01-0.02 级）对照。
- R2b 零活锁：无 depth-gate 臂型 1.1s banner 连发（活锁签名）。
- R2c 正常域零回归：canonical config 逐位自证（本 build 默认路径）+ hover/ground 域健康（若复裁窗内含 hover 轮则读，无则以回放预筛零回归+fixface-2 hover 战绩为基线引用）。

**到位对照列**（每轮必记）：truth→goal min（goal 3,-2,1 腿）vs 健康带基线 0.79-1.10m（三题收缩 C：040932 0.871-1.029/noise-off R1 1.095-1.10）——精度红利锚，不作门。

## 分支处置（预注册）

- 达 R1（≥2/4 且至少一案分臂内 ≥1/2 无成熟）→ 单元 3 U4 通告；案分胜负→胜者默认开、败者 flag-off。
- 两案各 1/2 → 平局不弃：加时各 1 轮（A3,B3），仍平→案A 胜（载体清除面优先，机制依据=R2 载体判决）。
- 均 0/2 未达 → **自主开下一轮假设表**（狂飙动力学占比从第二嫌疑升主嫌，poscmd×GT 动力学画像开工），判据门值禁放宽；STATUS 通告+DECISION_LOG 登记。
- 磁盘 df<20G 停（PR2+R5 45G 保全勿动）。

## 边界

- 判据/门值放宽永远禁（治理条款例外域）。
- 受控失败口径（10-03 12:09 裁定②）：任意门拦截+完整恢复=受控（legacy 与 cost 同等，误触发不算）；U4 证据表内 route 格若含受控轮须注记。
- 单轮异常（ENV-FAIL 签名：rosbag/gzserver 断/process 崩）不烧判据，重跑同臂补轮。
