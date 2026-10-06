# T1 任务书 v11.18 — v11.17 完成清账版（2026-10-07 00:4x；用户指令：按完成情况改写，写明已完成/未做/卡点阻塞，卡点=客观问题描述）

> 你是 **T1（单线承接模式）**。执行域=3090（`ssh nuc2`）。单线纪律/红线 1-24/等待协议 v2/判据门值零变动全沿用 v11.17 头部原文。
> 台账=3090 `~/sitl_sim/t1_evidence/v11_17_2026-10-06/`（本战役证据）；VINS 域判读资产=`~/catkin_ws/sitl_sim/t2_results/jump_dissect_v1/` 与 `nan_defense_v1/`。
> v11.17 全文弃读；本册=A 完成清账/B 剩余件/C 卡点与阻塞（客观描述）/D 资产凭据/E 等待登记。
> commit 链=67497bd→c78a9f4→59e3127→e7ec2f4→d036b3e→b40fcee→1c3dd80→44218fe（全推，双端同步）。

## A. 完成清账（v11.17 各单元终态）

### A.1 阶段 1（批前基建窗）— 全毕
- **1.0 网络恢复收尾** ✓：pull 同步；断连前残留两件收账（67497bd：xline_arm yaml=RAREP1 复刻配置唯一存证、flight.png=exfail5 文档配套图）；STATUS 开工行；任务书 3090 双份备份（修订版 md5 bf2eb541）。eno1 件维持挂起（网线未找到，沿用户裁定）。
- **1.1 planner starve 修复** ✓（头号件，commit c78a9f4）：
  - 取证先行定案：X2g3_042025 与 X2g1R_045147 两轮 planner.log **逐字节同型 189B**——构造完成（含 INIT→WAIT_TARGET=首回调已跑、odom 已通）后 1s 心跳全无。任务书判别三支全排除（①goal 传输丢失：心跳无条件于事件循环，缺心跳≠收不到 goal；②前置停等：WAIT_TARGET 空转路径 trivial 且心跳先于 switch；③订阅未建：构造已完成），**实际病灶=第四面：FSM exec-timer 事件循环在第 1~100 回调间死亡**（进程存活无 died 行=冻结非崩溃）。文书=t1_evidence/v11_17/starve_forensics.md。
  - 修复（harness 面）：vins_smoke.sh goal 段重写=订阅就绪门（goal 订阅者∧FSM 心跳首行）+首发 8s 无 target 变更→planner 整栈一次性重启（sick log 保全 planner_starved_1.log）。
  - **d) 发作自动留痕** ✓：t1_goal_trace.py 每轮落盘（goal 发布戳 vs poscmd 首帧戳+FSM 心跳/转移行数）——健康轮滞后 12ms、注入停摆轮 44.9s（重启绕行全记录）。
  - **DoD 四证**：注入式复现 ≥2（A1 ctor 型+STARVEOLD4 postinit 型=真实 189B 签名精确复刻，双 WARN）；新序列通过（STARVENEW2：同款注入→STARVE-DETECT→重启→RESTART-OK 100Hz→**RESULT=PASS 到位 0.107**）；正常回归 ≥1（STARVEREG1 PASS 0.055 零行为差）。批内实战：W8P 轮修复首次实战触发并恢复。
  - 修复有效性收案依据=取证面+留痕面+批内零 starve 失败（46+1 格无 WAIT_TARGET 型失败轮）。
- **1.2 X5 批基建** ✓：x5_batch.sh（自 x4_batch 派生；46 格出生锚定展开 goals_md5=4db51174；干测绿）；批加固三坑=①BATCH END trap 必落 ②清理 pkill -x 名字级零自匹配 ③**rosmaster 域过滤**（force_cleanup 不杀私有 master 回放件）+vins_node master 域过滤杀；**PX4 参数随轮 dump（口径预注册：disarm 后飞行末态，MAVLink 不与起飞投递窗竞争）+VINS config 全键 md5 轮首落盘**；autoattach 扩名 X5|HVNET|RAREP。
  - **plain world 实现与入库链定案**：设计文 §A.2 两档之 no_obstacles 档无现成文件——新建 sitl_world_plain.world（obstacles 同底去 3 箱+26 特征件：地面板/色环/角旗杆/走廊间隙立板/主墙±17°r5.5，全部走廊外或地下，横向净距 ≥0.64m>0.349 门）。**五连失败（PLAINCHK1-5）根因=world 未入库 PX4 worlds 目录→sitl_run.sh 回退空世界→VINS 特征饥饿**（Bas 爆炸 0.56→1.28/地面跳变 0.85-1.9m/内部流停摆 1 例）；入库后 PLAINCHK6 全链走通（FAIL=VINS 跳变 6.88m=跳变族 plain 域标本，非基建缺陷）。x5_batch preflight 补三重校验（repo 存在∧PX4 入库∧md5 一致）。
- **1.3 hwmon 探针** ✓：t1_hwmon_probe.sh（1Hz：核频分布/包温/thm_flag/负载/ctxt+dmesg 尾随；采样面预注册冻结）内嵌 vins_smoke 轮生命周期；历史轮覆盖缺口注记不回填。
- **1.4 轻件三件** ✓：X2g1_041509 补判=FAIL（rejudge：arrive 3.409/jump 面缺行如实 99.9，计红色分母，未定案轮销账）；X2g1R/X2g3R j0d 补跑（X2g1R j0_total=**0.0115 净**=starve 轮 VINS 面完美实证；X2g3R=**24.2189**=jump 12.71+transit 12.32 对半+njf 373）；组合矩阵再生+**测试轮排除面**（STARVE*/PLAINCHK*/REGCHK 注入验证轮禁入矩阵）；对审 v1.4 落库（判据库条目 IMG-XAUDIT-GUARD-v1.4：G-n≥30∧G-iqr≥0.5+对审史 A⁻→B 伪影更正+DECISION_LOG 签认，落库件 985a8c45）。

### A.2 阶段 2（build 窗）— 全毕（commit 59e3127）
- **2.1 NaN 防线四件** ✓（prereg 0d9b81f6 冻结先行）：D2 参数域断言（毒配置 loss=1∧cauchy=0 **拒启实证**：[T2NANDEF] FATAL 行+进程死）；D3 init 后置门求解面扩展（快照成员+纯函数）；D4 cost-median 退化守卫；D5 prior NaN 防线（两 marg 分支，干净 prior 保留）。banner 新行 [T2NANDEF] def=2/3/4/5 armed。**gtest 16/16 二进制全绿（128 现役+3 新增 test_t2_nan_defense，ceres 枚举 static_assert 对齐）**。栈换代登记：vins_node **721cad40**/libvins_lib **5bacc2e9**（批 preflight 引用）。
- **2.2 Z1.2 接线本体** ✓：enabled_v2 参数贯通（PX4CtrlParam.h/.cpp 读取+px4ctrl_node 映射+input.cpp **v2 增强层叠加于 v1 ACCEPT 之后**：运动学残差 R/戳龄/时戳回退）+ctrl_param_sitl.yaml 置位。运行时实证=REGCHK1 px4ctrl banner **enabled=1 v2=1**；缺省面（enabled_v2=false）零调用=v1 逐位不变。
- build 后回归轮 REGCHK1：**RESULT=PASS 到位 0.199**（新栈+四防线+v2 门同窗零行为差；v2 层 263/40000 帧边际拒=ACC 层，结局不变）。

### A.3 阶段 3（批窗）— 批毕；解剖 1a-1d 毕，1e 有判决
- **3.1 X5 批** ✓（三段跑毕 19:22→23:20+补飞至 23:46）：**46+1 格**（首发 35 格→ENV 早死误归 ABORT_ARM 修复后续跑→尾段；E8P 补飞+leg2 六轮补飞）。**绿 11/40=28%**（基础格+R2，每格最新轮口径）+leg2 1/6（S8P_L2 PASS）+R2 1/4（E12O_R2 PASS，与 E12O 网格绿=同格双绿）。批内三修如实入账（见 C.7）。STARVE 修复批内实战触发并恢复@W8P。断连容忍机制未启用（本机自跑全程无断连）。
- **3.2 跳变族三袋解剖** ✓（报告 e1a886fb；commit e7ec2f4）：
  - 前兆窗两段式预注册 5583f526+**v1.1 修正**（判读前：三袋实态=churn 0.5-0.68m/10ms 型非 ≥1m 单帧型，次锚 t_jump2=0.5m 对齐 round_result 门）。
  - 1a 悬停型（HVNET1）：病灶 t≈100-120 **z 向塌落**（0.9→-3.0，慢淋 0.19m/s，零快事件）；**cost 4.4×平台先于病灶 ~55s**+|Bas| 2.2×@t35；塌落后"连续一致但错误"驻留（无 NaN/reboot）。
  - 1b 绿-跳配对：**跳轮全程 3-8× cost 抬升**（X1final t15 即 1495 vs VRFY2 同刻 185，同 boot 4 分钟窗）=轮级前状态非瞬时事件；X2g3R=t66.3-67.1 八连 churn 突发+XY 出轨 24m+尾段 z 再塌。
  - 1c 配置对账三件：四轮目录**零 config 文件副本**（如实登记不可 diff，禁猜）；**banner 面四轮逐字节一致**（config 面排除）；PX4 参数/系统负载=历史盲区如实登记，定因责任移交前瞻面（X5 四件随轮已上线）。
  - 1d 出生偏移两段闭环：段一=REGCHK1 袋实测 VINS t0=(0,0,0)/gazebo iris t0=(1.010,0.980,0.104)→帧偏移=机体 spawn 位姿；到位判读锚点自推导扣除语义有效（完美飞行到位 0.199 实证）。段二=**sitl_run.sh:130 硬编码 spawn（-x 1.01 -y 0.98 -z 0.83→沉降 0.104）复算 |(1.01,0.98,0.104)|=1.417m vs 族实测 1.42-1.46 逐位对上**；跨栈代恒定=spawn 参数与栈无关。**收案：静态仿真脚手架参数，非 VINS 建立链缺陷，与跳变族无涉**。
  - **1e 回放 A/B：判决=材料不可行**（95c1f93e）：三袋紧凑零图像→VINS 回放物理不可能（首件尝试实证：vins_node 停于 waiting for image and imu，输出袋 4KB 空）；EX-FAIL 第五坑同族。判别结构（输入面 vs 运行时面）在带图材料上可重启（X4 重飞带图 ≤2 轮=已在册前瞻件）。
- **3.3 社区调研** ✓（5ff1cc5d）：七病例逐条对照——上游 Fast-Drone-250 官方 case2 表型（快速上升/下降=VINS 失效）与我们 z 塌落**精确吻合**；快速 yaw KLT 失败=gyr_peak 轴依据；低视差退化几何=悬停型机理一致；**完整前兆链无社区病例=sim 域特有注记候选**（挂 1e 裁决，1e 不可行后该注记维持候选态）。可移植经验四条入册。

### A.4 阶段 4（批后窗）
- **4.1 剂量-稳定性曲线** ✓核心/H1 定案（x5_curve.md）：**H1 单调剂量响应成立**——gyr_peak 四分位带绿率 **50%→40%→20%→0%**（p25=1.54/p50=1.90/p75=2.86；距离档 17/33/31% 非单调）=B3 剂量轴网格版独立检验通过。**中间稳定带=弱**：连续≥3 绿序列存在（N8P/N12O/E12O_R2@gyr≈1.6）；**无 ≥80% 绿率带（峰 Q1=50%）**——两支判据结果如实并列。绿格 11 清单（gyr 升序：E12O/NE8O/NE12O/S12P/E8O/S8O/N8P/N12O/E12O_R2/S5O/W5P；前 9 格全在 gyr<1.9）已 STATUS 呈报。**未竟部分见 B.2**。
- **4.2 T4 域代持** 部分：truth 口径修复=**T4 今晨 v5.20 会话已毕**（两值并集修 3cea212+100 袋全量重跑，12:27 STATUS 在册）——本册确认免重；X7_DRAFT 回填三处 ✓（§8-R12 增补+对审史更正+**§6 X5 数据槽**）；**X5 新袋两档收未执行**（见 B.3）。
- **4.3 机会件** 部分：**B1 遥测考古 ✓**（BL5/BL7/VRFY2 三袋 mavros IMU 对比：节律面全同=传输/供给面排除；BL7 |ω|p99=0.61=绿轮 4.7× 旋转激励差=运动剂量面证据，DECISION_LOG D-1006-T1-14）；**MACH8 补全段回放未执行**（见 B.4）。
- 收尾：canonical 已 restore（5c98dc0d）；现场全净；终局 STATUS 收官行+三前置呈报已发。

## B. 剩余件（未做/部分做，含依赖）

1. **X4 重飞**（单元 5）：三前置材料已呈报 STATUS，**裁定=用户**；新五位形从绿格 11 清单选（0.75 门不动）；5/5 真绿+双链核验（单线期第二链=用户复核兜底）后 tag sitl-v0.4。**未飞**。
2. **4.1 判读补齐三件**：①X5 轮跳变族前兆签名**逐轮标注**未做（仅 top-5 跳变行列出）；②**H2 温和剖面对照判读**未做（温和= E/W/N×plain vs 标准=SE/S×obstacles 的通过率对比未正式计算，带内样本量本身不足）；③**H3 transit 主导占比**未做——依赖 **X5 轮 j0d 批跑**（v11.17 批预注册的"每轮 j0d"实为沿 x4 同构未随轮落盘，需批后批跑，未执行）。
3. **X5 新袋两档收**（4.2 遗留）：~50 个新紧凑袋未入 T4 收货链（紧凑=第五坑+odom/truth 行）；带图档=0 轮（批全紧凑，A.4 带图条件未触发）故无六腿全链腿。
4. **MACH8 补全段回放**（4.3 机会件）：t=113-383 带图袋在册可回放，未执行（窗口被主线占用）。
5. **X7 终稿**：X4 定局后 24h 出稿纪律维持（DRAFT 状态，X4 依赖槽占位中）。
6. **T4 回场件**（不代持到底）：verdicts 草稿三节定稿/E4 帧级复核悬置/bitIdentical 采信面/悬停 8.5m 证据包定位。
7. **悬案池长期件**：干预式复现（CPU 突发剂量实验，需设计预注册）；sane 门盲区修复面=transit 前 bias 约束（估计器写码，**挂用户授权**）；A3 臂差因果化（挂随机化批授权）；hover j0 带宽变宽（**X5 设计无 hover 格，本战役未覆盖**）；B1 物理载体（证据已更新，案未闭）。
8. **gyr_peak 提取器口径对齐件**：本战役用全袋峰值+四分位定标；与 T2 [T2diag] 窗口化口径的对齐未做（见 C.5）。
9. **网络终局**：NUC .6 过渡态→终局 .5（用户选 A=Windows 让 .5/B=重启 AP）；eno1 插线件（挂网线实物）。

## C. 卡点与阻塞（客观问题描述）

1. **跳变族定因的裁决实验在现有材料上不可执行**。1e 判别（同输入离线回放：复现=观测面/干净=资源竞争面）需要相机流；历史三袋与本批 X5 全部轮次均为紧凑录制（零图像）。回放物理不可能已实证。带图录制单轮 13.9G 级（F3B 系实测），批设计文 §A.4 将带图档限定为"P3 明确要图像证据的位形才启用、≤2 在盘"，本批未启用。因此**输入面 vs 运行时面的归因裁决目前没有任何可执行的实验材料**。
2. **跳变族间歇性未定因且无同窗机器侧证据**。同位形跨时间绿↔跳并存多例在册（VRFY2 04:05 绿→X2g3R 05:01 跳 24m；X5 E12O 网格绿+复刻绿 vs E12P 35.97m 巨跳；S8O 绿/S8P 跳/S8P_L2 绿）。历史轮无 hwmon/PX4 dump/负载时间线（三盲区），X5 轮起四件随轮才补齐。两个归因框架（估计器内部进程 vs 在线运行时时序）未汇流。
3. **X4 前置 2 的三选一无一完整达成**：①1e 回放定案=材料不可行；②前兆签名定案文书=粗扫段有（cost 平台/|Bas| 先行 35-55s+绿跳对轮级 cost 差），确认窗逐轮走查未做；③X5 批零巨跳实证=**反向**（≥5m 巨跳 6 例：5.49/5.58/12.15/30.42/30.57/35.97，其中 ≥30m 三例——跳变族在网格域活跃）。裁定材料含混是客观事实。
4. **稳定带强度不足**：全部剂量带无一达 80% 绿率（峰 Q1=50%）；连续 3 绿序列仅一段且恰在 gyr≈1.6 窄带。绿格 11 个中 9 个位于 gyr<1.9，但同带内失败格同样密集——**带内无法进一步用剂量降风险**；5/5 全绿的成功概率无先验可估（同格双绿的 E12O 是唯一复刻正例）。
5. **H1 结论的口径局限**：四分位分带为批后数据驱动定标（非预注册；预注册初版 0.3/0.6 阈全落单带不可分后改四分位）；全袋峰值提取器与 T2 B3 的窗口化峰值（[T2diag] 同源）未对齐——跨口径可比性未建立。
6. **plain 档环境为新造**：sitl_world_plain 特征工程后仅 1 次独立验证轮+批内 18 格数据；E5P 30.57m 级巨跳发生在 plain 档；该世界 VINS 健康度无独立长期评估。
7. **批工具三缺陷均为实战暴露后修复**（dry-run 未覆盖）：judge stdout 污染（w 经 tee 回 stdout 被 $( ) 捕获→分类永落 fail，首发段 E8O/S8O 两 PASS 的绿计数丢失——数据在 report，计数以 passmap 重建为准）；ENV 早死误归 ABORT_ARM（SE12P 双目话题未起杀批）；leg2 tag 与网格 tag 碰撞（5/6 leg2 被 skip 吞，事后改名 1+补飞 5）。
8. **补飞轮与批内轮执行环境有差**：leg2 五轮+E8P 一轮为批外手动执行，未经批 preflight 四键/md5 校验链（栈未变，风险面=流程一致性与凭据链断点）。
9. **Z1.2 v2 门存在帧级行为差**：263/40000 帧边际拒（verdict=ACC 层，v2 独立状态机与 v1 的 dt 间距判据差异），轮级结局不变；该差异的可接受性（边际拒 vs 调阈）未裁。
10. **X5 ~50 新袋未入收货链**：T4 域紧凑腿机械数据（odom/truth 行）未收集，X 线判读的袋级账本缺口。
11. **网络布局非终局**：AP DHCP 分配器损坏未根治（新设备可能再冲突 .5）；NUC=.6 静态过渡；终局方案二选一挂用户。
12. **单线模式结构性风险**（沿 v11.7 声明）：全域代持无交叉验证，第二链=用户复核兜底；本战役判读/曲线/解剖全部单链产出。

## D. 资产与凭据（md5/commit）

| 件 | 位置 | md5/凭据 |
|---|---|---|
| 任务书 v11.17（弃读） | plans+3090 双份 | bf2eb541 |
| starve 取证文书 | t1_evidence/v11_17/starve_forensics.md | （repo 副本 461b1556） |
| NaN 防线预注册 | t2_results/nan_defense_v1/prereg_v1.md | 0d9b81f6 |
| 前兆窗预注册(+v1.1) | t2_results/jump_dissect_v1/prereg_prodrome_v1.md | 5583f526 |
| 三袋解剖报告 | jump_dissect_v1/dissect_report_v1.md | e1a886fb |
| 社区调研 | jump_dissect_v1/community_survey_v1.md | 5ff1cc5d |
| 1e runbook/判决 | jump_dissect_v1/replay_1e_{runbook,verdict}.md | ceaf4492/95c1f93e |
| 对审 v1.4 落库 | t1_evidence/v11_17/xaudit_v14_archive.md | 985a8c45 |
| X5 批报告/曲线/passmap | t1_evidence/v11_17/{x5_batch_report.md,x5_curve.md,x5_passmap.csv} | 50 行/40 格 |
| 栈凭据（现役） | vins_node/libvins_lib | **721cad40/5bacc2e9** |
| canonical | config restore | 5c98dc0d |
| commit 链 | 67497bd..44218fe | 8 笔全推 |

工具新增：t1_goal_trace.py / t1_hwmon_probe.sh / t1_x5_passmap.py / t1_x5_curve.py / t2_prodrome_scan.py / inj_starve_test rev4 / x5_leg2_makeup.sh。判读口径：内嵌判读（rejudge 权威制沿用）；X5 判读零门值变更。

## E. 等待登记（长档）

- **W-用户裁定（头号）**：①X4 重飞三前置（材料=STATUS 收官行+x5_curve.md+replay_1e_verdict）；②X4 新五位形（绿格 11 清单）；③网络终局 A/B；④对审 v1.4 落库复核面+臂差随机化批授权面（单线期第二链）。
- W-X4 重飞解锁（前置裁定后）；W-tag sitl-v0.4（5/5 真绿+双链）。
- W-X7 终稿（X4 定局后 24h）；W-T4 回场四件；W-E EXP-2 归档态。
- 悬案池恒 ≥3 维持：跳变族时间维度转折（1e 不可行后挂带图材料）/干预式复现设计/批链会话死亡机理观察/sane 门授权件/A3 随机化批/hover j0（X5 未覆盖面）/B1 载体/悬停 8.5m 包。

## 附：合法收工态声明

本册按等待协议 v2 收工于"轮询等待"态：飞行/批/判读链全收束无在飞件；剩余件全部挂用户裁定或材料/授权前置；悬案池 ≥3；台账/DECISION_LOG/STATUS 三账齐（D-1006-T1-11..15）。
