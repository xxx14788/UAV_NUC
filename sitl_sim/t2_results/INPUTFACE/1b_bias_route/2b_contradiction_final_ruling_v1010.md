# ②b 判读矛盾终裁文书 v1.0（2026-10-11 00:2x——工程合并册单元 1）

矛盾：T2 自判 tlock NOT-EFFECTIVE（dbadt A<B 8/8 机制面全治）vs T3 影子判读
（tlock_banner=0×8/8 锁未 ENGAGE=A 臂实质第二 B 臂，批不构成 ②b 机理检验）。

## 1. 三候选定位（代码审+TK 批 16 轮日志逐轮取证）

- **候选① env 通路：排除**。A 臂 8/8 simvins.log 启动段 `[T2BIASTLK] tlock=1
  w=10.0 (CONSTRAINT-2b ARMED)`（B 臂 8/8 `tlock=0 off=legacy bit-identical`）——
  env→parameters.cpp L298-301→estimator 通路全通，臂身份自证完好。
- **候选② 谓词首过阈值：排除**。A 臂 8/8 `[T2TLOCK] ENGAGE` 实发（越阈 V=0.301
  -0.426，全在 >0.3 门上）；谓词 ENGAGE_V=0.3/RELEASE_V=0.2（t2_bias_box.h
  L56-57）与预注册冻结口径一致。
- **候选③ banner 发射逻辑：vins 侧排除，缺陷在批脚本抽取侧**。banner 发射
  无条件（estimator.cpp L1525/L1532）；`[T2TLOCK]` ENGAGE/RELEASE 两式 8/8 在
  日志（快照 |Ba|/|Bg|/V 三元组俱全）。根因=**批脚本 t2_bias_tlock_arm_v1010.sh
  L56 grep 模式为 `\[T2BIASBOX\] box=1`（②a 的 box banner——自 box 批脚本复制
  未改）**，tlock 轮日志无 box banner → banner=0 16/16（含 A 臂）。T2 批后已
  CSV join 修复（.bak_banner_fix 存证，A=1/B=0）；**脚本本身本件随裁修复**
  （双副本同步+md5 对账）。勘误：T2 终判文书 v1 §1"sed 转义坑"表述不准——
  实际为 grep 模式错源（copy-paste 继承），非转义问题。

## 2. banner=0 与 dbadt A<B 并存机理裁决

**锁生效+锁窗与度量窗同窗**——两判读各自为真，无实质矛盾：

- dbadt 度量窗（t2_box_diag.py："首帧 |V|>0.3 至 |V|<0.2"）与 tlock 锁窗
  **同谓词同窗**；CSV transit_t0/t1 为相对首帧 diag 时间（工具输出
  `t0-pts[0][0]`），折算后与 ENGAGE 逐位吻合 **7/8 A 臂**（E12O/E8P/N8P/NE8O/
  S12P/S8O/S8P：|Δ|<0.02s；例外 E12P 见 §4）。
- A 臂锁=prior 挂全窗帧锚快照（estimator.cpp L1536-1548）→ 窗内 |d(Ba)/dt|
  被压制 → **dbadt A<B=锁窗内真效应**（构造性预期内：prior 的直接作用）。
- 绿率判据（jump/arrive）由 goal transit 段决定——该段未受锁覆盖（§3）→
  **+0.0pp 与 dbadt 8/8 并存不矛盾**。

## 3. 窗错位机理（本终裁核心新发现）

冻结谓词"V 首过 >0.3"在真实飞行剖面捕获的是**起飞爬升段**，非设计意图的
transit-to-goal 段：

| 事件 | 时间（正常格，sim 时） |
|---|---|
| VINS 地面完成初始化（solver NON_LINEAR） | t≈10.5（首帧 [T2diag]） |
| 起飞爬升=首次 V>0.3 → **ENGAGE** | t≈31.1-32.3 |
| 爬升顶 V<0.2 → **RELEASE+done** | t≈33.3-34.0（单窗语义） |
| goal 首发 | t≈45.8-46.6 |
| 真 transit（V 峰 0.4-0.5，多次阈值抖动） | t≈47.3-53.2——**锁已 done，全程未锁** |

- 6 格（E12O/E8P/N8P/NE8O/S12P/S8O）与上表逐格一致（E8P 无 goal_trace 但
  V 结构同构：首穿越≈31.7=ENGAGE）；S8P 见 §5；E12P 见 §4。
- 机理链：VINS 地面完成初始化 → NON_LINEAR 先于起飞 → 谓词首过=起飞爬升 →
  单窗语义 release 后不重锁 → **设计目标的 transit 段从未入锁**。
- 锁窗实测时长 0.11-4.67s（E12P_A 0.11s=悬停噪声毛刺型；正常格 1.7-2.0s
  ≈爬升段；S8P_A 4.67s 受污染 goal 扰动见 §5）。

## 4. 逐格例外注记

- **E12P_A（毒域格）**：init 滞后（首帧 diag t=30.93）；ENGAGE@51.81
  （banner V=0.340）但 diag 序列首穿越@55.34——solver-V 与 diag-V 同刻分叉
  （init_replace 类状态替换嫌疑，毒域已知病理族）；度量窗≠锁窗 → 该格
  dbadt A<B 不属锁窗效应，**dbadt 证据面按 7/8 计**。
- **E8P/E12P（毒域两格）**：无 goal_trace.tsv（harness 未产 goal 面）——
  goal 时序不可考，V 结构与正常格同构注记。

## 5. S8P goal 污染（附带新发现，@单元 5 波动分解）

S8P 格 seq=0 goal 间歇性污染（3/5 轮，跨两批）：

- TK_S8P_A：goal=(642713.68,4671809.99,0.00)@34.32；TK_S8P_B：
  (642716.41,5722260.78,0.00)@34.21；WU2_S8P_A：(642715.66,5722262.27,
  0.00)@32.95；11-12s 后 seq=1 修正为正常 goal (1.01,-7.02,1.00)。
- 形态=UTM 东经≈642715/北纬 4.67-5.72e6/z=0（正常 goal z=1.00）——疑似
  UTM 坐标误注入 goal 话题（根因候选，未溯源——间歇性非确定性）。
- BX 两臂/WU2_B 正常 → 间歇性（同格同批臂间不一致）。
- 后果：S8P 格灾难指标（indom 0.5%/5.1%，双 FAIL，dbadt B=3.87 全批最大）
  有直接候选根因=格级污染注记；②b B 臂 25% 绿率中的 S8P 分量按污染解读
  （@单元 5 分解报告）；污染 goal@34.2-34.3 落 S8P_A 锁窗 [31.05,35.72]
  内——该格锁窗行为受扰，格级注记。

## 6. 终裁

1. **②b 判负维持**（NOT-EFFECTIVE：A 绿率 25.0% vs B 25.0%，+0.0pp，方向
   0/8——事实层零变动）。
2. **②b 证据面重注记**：本批检验的是"**起飞窗温和锁**"（冻结谓词在真实
   剖面的操作化落点），非"transit 窗锁"；dbadt 8/8→**7/8 有效**（E12P 窗
   错配剔除）=锁窗内机制真效应。
3. **bias 路线整体证伪定案维持**：squeeze 结论由 ②a（全时段硬界含 transit
   段，-62.5pp 过紧自伤）主承载+②b（锁窗内机制可治而绿率不动）辅证；
   transit 段 bias 约束的证据缺口由 ②a 覆盖（box 全时段含 transit 段）。
4. **复验轮裁定：无复验需求**。banner 疑点已由日志实锤闭环（§1）；transit
   窗锁=谓词重设计=新 prereg 新批，且无信息增益（②a 已证全时段 bias 约束
   不抬绿率；SITL 绿率主导路径已定案在渲染时戳域病理）。**单元 3 的 ②b
   复验 8 对取消，窗口让渡 A1 扩批**。
5. 产出动作：批脚本 banner 修复（L56 改 grep `\[T2BIASTLK\] tlock=1`，双
   副本+md5 对账）；本件落盘；T2 终判文书 v1 §1 sed 转义坑表述勘误注记。

## 7. 证据索引（2026-10-11 00:0x-00:2x 会话实录）

- banner 全 16 轮扫描：A 8/8 ARMED+ENGAGE+RELEASE / B 8/8 off（grep 实录）
- 窗折算验证表：16 轮 firstdiag/CSV t0/t0+fd/ENGAGE（7/8 逐位 YES+E12P NO）
- V 剖面解析：N8P_A 全程穿越点序列（RISE 32.08/48.43/49.17/50.77/51.53/
  389.13——末点=降落段）
- goal 扫描：三批（TK/BX/WU2）42 轮 seq=0 goal 全表（S8P 3 污染；WU2_A
  小目标 (0.08,0.29,0.50)=预热臂设计非缺陷）
- 原始件：tlock_pairs_v1010.csv（+.bak_banner_fix）/t2_box_diag.py/t2_bias_box.h
  L54-66/estimator.cpp L1513-1555/parameters.cpp L293-332/t2_bias_tlock_arm_
  v1010.sh L56/TK 17 run 目录（8 对+DRY）
