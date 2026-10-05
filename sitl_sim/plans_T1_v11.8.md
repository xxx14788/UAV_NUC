# T1 任务书 v11.8 — 完成清账版（2026-10-06 凌晨；用户指令改写；**v11.7 弃读**）

> 你是 **T1（px4ctrl/基础设施线）——单线承接模式**。执行域=3090（`ssh nuc2`）；NUC=对照+归档。
> 单线模式声明/代持纪律/等待协议 v2/治理条款/红线 1-24 全部沿用 v11.7 册头原文（见 plans/2026-10-05_T1_px4ctrl_v11.7.md，弃读但册头纪律条款仍为现行约束）。**判据/门值零变动**——本版只做完成清账与剩余件/卡点客观重述。
> 台账=3090 `~/sitl_sim/t1_evidence/`（主）+本会话证据目录 `v11_7_2026-10-05/`（12 件）；DECISION_LOG/STATUS=3090 侧唯一正源；本会话登记 D-1005-T1-01～06。
> 协同方在册：**T4 线 agent（rick）会话期内活跃**（I5b b8e103f/I5c 3268a42，消费本线 relay 腿，无冲突）；双 agent 碰撞协议继续有效。

## 0. 现状快照（2026-10-06 02:0x）

- **栈**：devel=streamguard v4（node b7de133d+lib 59548c6a，存档 stack_archive/streamguard-1/）双 md5 稳定；px4ctrl=0e832aa7+P2 门（默认 off，参数路径 `/px4ctrl/p2_cmdresp/enabled` 私有 nh）。
- **判读链**：round_result v1.4 双锚取稳（c708151f 双副本）；t3_wa_gate --online 消费正常；prereg=xline_prereg_v1_1.md（b72e5126，现行 v1.4 含 §2.8/§2.8a）。
- **VINS config**：canonical 已复原（5c98dc0d，零 t2 键）；X 线臂装载/复原脚本=~/sitl_sim/arm_xline.sh（臂文件 ca6f7797=10 键 cauchy=0.0 在册）。
- **机器**：3090 当晚两次网络断连（USB WiFi AIC8800）+一次重启（22:00）；02:0x 时刻可达、无活动病灶实锤（dmesg 静默/内存 29G 空闲/负载正常）。3090→NUC 免密腿已补建。
- **磁盘**：597G 空闲；无 gzserver/rosbag/px4 残留；48 僵尸 traj_server 已清零。

## A. 已完成清账（v11.7 单元 1-5 + 池①②）

### A.1 单元 1 disarm 五连败：取证+根因+修复+验证全闭环（D-1005-T1-04；X4 前置②闭）

- **取证（E1-E5 链，全在册）**：五轮 px4ctrl.log 签名=①X2g1_024637/X2g3 纯 S9（CMD_CTRL 拒 LAND 列车 20-30s）；②X2g4/X3l2a=U2.7 接纳后 1s 内 cmd 复鲜回 CMD_CTRL（S4+S9）；③X3l2b=终态 odom 劣化退 MANUAL 后 U2.7 拒（S3）；④X2g1_041203=未建立飞行从属型（在册勘误面）。**五轮 S1（进 AUTO_LAND）=0**。
- **根因**：`kill_planner_all.sh` pgrep 模式（`ego_planner/lib/traj_server` 等）对 catkin build 真实路径（`devel/.private/ego_planner/lib/ego_planner/traj_server`）**全栈失配**（node+traj_server 双漏，J1 回归对照实证）→traj_server 不死、100Hz 续发 /position_cmd→px4ctrl 卡 CMD_CTRL 按设计拒 LAND→teardown 时 armed→auto_disarm=0。**px4ctrl FSM 全程无责**；U2.7 之谜=覆盖面不同（U2.7 修 MANUAL 收 LAND，本族是 CMD_CTRL 拒）。深浅判定=**浅**（harness 面，W-deep 不触发）。
- **修复三件**：F1 模式统一 `lib/ego_planner/<bin>`；F2 06_land 增 /position_cmd 3s 静默门；F3 **双副本部署对齐**（harness 调 `~/sitl_sim/` 运行时副本——修复须仓库+运行时双落，md5 齐）。
- **验证**：J1 模式 4/4+回归对照；J2 活体 48 僵尸→0；J3=CLI-pub 角落异常注记（见坑表）；**J4 飞行验证=auto_disarm=1**（首轮 health_smoke_2 即验，链完成签名 t=200.36 armed=False+LOITER 恢复；后续 7+ 轮复验，含真重启轮）。
- **客观残面（未修，在案）**：VINS 死亡/风暴轮 disarm=0 路径仍在（AUTO_LAND 出口①odom 断→MANUAL 无 disarm 分支+U2.7 拒收死 odom 的 LAND）——当晚 SUPHV2a/b 两轮实证；净轮/健康轮不受影响（全部 disarm=1）。

### A.2 单元 2 prereg 栈槽+streamguard 追认：完成（D-1005-T1-02）

- prereg 栈槽行换代 streamguard v4（b7de133d/59548c6a）+[T2SGCFG] banner 自证条款；正源追认按 D-1004-T2-01 同型登记。commit caf5d5a。

### A.3 单元 3 anchor 案③：判读器改造+历史全面重算完成（D-1005-T1-05；X4 前置 anchor 面闭）

- prereg §2.8 双锚取稳冻结（R1-R5/σ0.03/IQR0.06/n50/0.4s/δ0.15，NUC 袋定标）+J0 末端锚不同规裁定；round_result v1.4 上线（红线 24 全流程，双副本 c708151f，.bak_v14 双树备份）。
- L1 合成全绿（R1-R5+压线 0.150/0.151+std 0.030/0.032+可用性）；L2 五 X 轮 C_sta 与 survey static 列位等价（±0.002）。
- **§2.8a 勘误（待用户过目）**：历史锚构造 prop 侧 `sum(前50)/len(全窗)` 算术 bug——静态窗 prop≈原点隐身、动态窗 prop 5-10m 时系统性污染（X2g3 dyn z 0.814→修正 0.095）；**在册"+0.18~+0.71 动态窗 z 污染(22/22)"相当成分=算术伪影而非物理 VINS 瞬态**；survey 的 dyn/anchor_gap 列引用须注记。
- **L3 全库重算收口（1de177b）**：99 轮（11 no-goal，0 错）**15 轮到位翻转，预注册红线触发后停机复核=全部与 survey static 口径对账一致**：绿→红 2（BL7 0.467→1.810 vs survey 1.865；MACH6 0.673→0.960 位等——survey 数据原样预测）；红→绿 13（E4×5/F3B×3/M0/RA×2/T3U1V/X2g3，旧值 0.75-0.96 边缘带=算术 bug 全库修正效应）；X2g3 0.849→**0.035 到位翻绿兑现**。prereg §7"仅 X2g3"预期行勘误在案（取自 X 五轮分析面，低估全库边缘带）。
- **历史轮重判的客观结果**：X2g3 到位面绿，但**四指标合判仍 FAIL**（auto_disarm=0 为袋内史实不可改）——历史重判轮是否/如何计入 X4 5/5 计数=用户复核点（未裁定）。
- **尾件未做（如实）**：t3_wa_gate selftest（SYN 链）扩 anchor 用例 ≥3 未执行（v11.7 单元 3.4 尾项）；BL7/MACH6/13 边缘轮的在册判读双列注记=T2 域回场对账件（已登记，未落注）。

### A.4 单元 4 销案通告+对审 v1.4 重判：完成（D-1005-T1-03，待用户过目）

- A.4 销案通告已发（X4 前置④闭）。对审 v1.4 守卫（G-n n_C≥30+G-iqr mean-IQR≥0.5，C=X1final 帧级 CSV 定标：病理 0.003 vs 健康 ≥4.45，>1000× 分离）入判据库（IMG-XAUDIT-GUARD-v1.4 文本在册）；v1.3 素材重判 **A⁻→B**；候选①图像内容级三型排除**收官**。
- 尾件未做（如实）：img_xaudit 工具链的守卫代码实现挂下一轮图像对审执行前（当前无新对审排程，不阻塞 X 线）。

### A.5 单元 5 供给轮+四件同窗消费：战役执行完成，四件中三件过一件挂（D-1005-T1-06）

- **轮次（详表=t1_evidence/v11_7_2026-10-05/p2_p3_supply_verdicts.md §0+supply_campaign 双日志）**：20 轮发射（legacy/gates+guard 无 cauchy/guard+sane/P2-A/P3 注入四臂+快速验证轮），13 轮建立飞行、2 never-flew（风暴）、1 never-init、4 快速/瞬态。
- ①**disarm=PASS 多轮**（legacy/guard 臂 7+ 轮 auto_disarm=1；风暴轮=H-A 残面如实记 0）。
- ②**P2-B=PASS**（SUPX1b/SUPHVa 零事件；P2 启动自述行=配置声明非事件，措辞注记在案）；**P2-A=enabled=1 活体+零 latch**（SUPP2Av3，T2fail=0 全程 armed）；**严格版（净轮 j0<0.5 上零 latch）未命中**——窗内无"P2 on 且 j0<0.5"的轮（P2-A 轮 j0=0.823）。
- ③**L-odom A/B（U2.5 终判）未执行**（L-odom 臂接线=E4R2-GOFF-D10-LODOM 先例，本窗未及）。
- ④**P3 reboot 注入=五判据全过**（预注册 v2 先行）：J1 odometry gap 3.47s≥2.0；J2 P1 桥接态正确不锁存（offset>0.75 分支未 exercised，注记）；J3 全程 armed+完整降落+disarm=1；J4 零风暴（带内）；J5 **权威 odometry 流穿真重启步长 max=0.073m**（诊断 prop 流 3.0m 单步=真重启换帧签名，J5 措辞按权威流读的勘误在案）。
- **净窗产出**：DIAGGUARD2=**史上第 2 个净轮面**（j0=0.418∧0 [T2fail]∧jump=0.0∧disarm=1，guard+sane 臂；到位 4.7m=transit 地板面延续，与在册 j0/到位解耦定律一致）；SUPHV3b hover T2fail=0。
- **指定臂（gates+guard）上的有效飞行轮=0**（4/4 风暴，见 C.1）；探针随轮附着（img_fp/[R3xQ]/[W2BB]）未执行（`--probecheck` 语义勘误=仅 init 地面轮，坑表在案；autoattach 守护只盯 T2MACH 轮）。数量面 X1prime 型/hover 型各 ≥2 达成但**臂构成混合**（legacy+guard 臂）。

### A.6 池①②：闭卷

- **池① 引用闭环闭卷**：t4_ref_closure NUC 腿 v2 修复（tilde 展开/基目录 7 对齐/basename 兜底，2f67d89）+3090 双腿权威重跑（**3090→NUC 免密腿补建**：keypair ghj@3090 装于 uav@nuc+alias）→missing_both 61→59、nuc_only=12、skip=0，报告 20261006 **可引**；T4 线 I5b/I5c 两笔已消费收口。
- **池② 僵尸清理闭卷**：48 个（24 对，c015..c01b 系）清零。
- 池③④⑤未动（③E-4 袋身份指认、④探针 jump 面首验读数未做；⑤B 路 HF 重标维持原挂起条件）。

### A.7 运维事件（客观记录）

- 3090 **USB WiFi（Ugreen/AIC8800，接口 wlxec1ac305b13e）两次断连**：20:15-21:30（ARP 应答/ICMP+全 TCP v4v6 丢，未重启自愈后复发→22:00 重启）；23:04-23:07（3 分钟自愈）。重启前后机器态差异见 C.1/C.2。
- 双副本部署分叉盘点：kill/land/round_result 三件已对齐；**5 个既有分叉脚本登记未动**（05_record_bag/env_health_check/t2v3_flight/t3_verify_flight/v1_flight，属 T2/T3 域，是否对齐待属线）。
- 新坑八条入册（附表）。

## B. 剩余待办（按依赖序；判据/门值不变）

1. **X4 臂裁定后的 X 线复飞序列（原单元 6）**：执行序沿用 v11.7 原文（X1' 重飞→X2g1/X3l2a 重判/重飞→X2g3 重判（到位面已绿，合判语义待定）→X2g4/X3l2b 重飞（敌对分母口径+环境性重试 1/轮上限 3 次）→**X4 五连飞 5/5→打 tag sitl-v0.4**（打前五查）+撞门预案响应链原文有效）。**整段被 C.1 阻塞**。
2. **tag 后收尾件（原单元 7）**：X7 骨架回填素材归集（本会话素材已在 v11_7 目录，成稿挂 T3 回场）；代持清单终版入 DECISION_LOG（T3/T2 回场交还依据）；STATUS tag 达成+成色声明。
3. **供给窗尾件**：P2-A 严格净轮版（需一轮"P2 on∧j0<0.5"）；L-odom U2.5 A/B 终判；探针随轮附着（img_fp/[R3xQ]/[W2BB] 面上轮）。
4. **单元 3 尾件**：t3_wa_gate selftest（SYN 链）扩 anchor 用例 ≥3（R1/R2/R5 各一）。
5. **池③④**：E-4 袋身份指认续查；探针 jump 面首验读数。
6. **属线回场对账件（非本线执行）**：BL7/MACH6 双列注记+13 边缘轮注记裁定（T2/T3 回场）；5 个分叉脚本对齐（属线）。
7. **明确挂起件不变（禁越位）**：T4 收货判读链/W1 新袋 SLA/扩样｜T2 静默大发散深挖/MACH8 回放/V2 扩充｜T3 X5 网格/X6/X7 成稿/Z1.2 常规化三步｜A1 场景移植/U5 残件。

## C. 卡点（客观；裁定/处置权标注）

- **C.1 X4 臂不可飞冲突（头号阻塞；裁定=用户）**。事实链：①任务书口径=X 线"gates+guard"（承用户"cauchy 不入 gates"既有裁定）；②当晚 gates+guard（无 cauchy）臂 **4/4 风暴**（T2fail 52-216，cost gate 全打在地面 init 段，never-flew/起飞不建立）；③gates+guard+cauchy4.0（=晨间 RA13/14 同臂）当晚 1 轮 **never-init**（排除 cauchy 缺失为独立原因）；④guard+sane（无 gates）臂当晚干净可飞且产出净轮面；⑤legacy 臂当晚可飞但全部敌对面（jump 4-7m/262m 框滑）；⑥晨间同 gates+cauchy 臂干净=**机器可飞性在 22:00 重启前后发生变化**，且当晚机器经历两次 USB WiFi 断连；⑦重启后无活动病灶实锤（dmesg/内存/负载均正常）。**冲突本质=口径要求的臂与当晚机器态下唯一可飞的臂不一致**。裁定材料（四选项 a-d 及证据）=t1_evidence/v11_7_2026-10-05/p2_p3_supply_verdicts.md §3（本册只引用不背书）。**阻塞：B.1 全段→tag→B.2。**
- **C.2 机器网络不稳（裁定=用户，硬件/环境类）**：USB WiFi 两波断连（间隔约 2.5h）；对 X4 五连飞所需连续窗口（约 40-60 分钟无断连）构成可用性风险；断连期间远程无处置手段（第二次 3 分钟自愈属运气非机制）。根因未定（驱动日志静默期与断连窗不完全对应；AIC8800 为消费级 USB 网卡）。
- **C.3 历史轮重判计数语义（裁定=用户）**：X2g3 到位面已绿但合判 FAIL（disarm=0 史实）；"重判轮计入 X4 5/5"的口径未定——影响 X4 序列里哪些位形需重飞。
- **C.4 H-A 残面（登记在案，未修）**：VINS 死亡轮 disarm=0 路径（AUTO_LAND 出口①+U2.7 拒死 odom）。触发条件=降落段 VINS 失活；净轮不受影响；X4 受控失败轮可能落此面（判读时按四指标如实 FAIL，不豁免）。
- **C.5 用户过目三件（复核=用户，单线期）**：①C.1 臂裁定；②prereg §2.8a 锚算术勘误（机理面：在册污染叙事的伪影成分）；③对审 v1.4 A⁻→B（判据变更类）。
- **C.6 单线模式风险声明（沿用 v11.7）**：串行效率低；判读器代持改动无交叉验证（红线 24+用户复核兜底）；T3 资产回场交还需对账。

## D. 资产与凭据（md5 实读，2026-10-06 02:0x）

| 资产 | 现值 md5 | 状态 |
|---|---|---|
| round_result.sh（判读器 v1.4） | c708151f（仓库+运行时双副本一致） | 现行；.bak_v14_20261005 双树 |
| kill_planner_all.sh | 9bf5c785（双副本） | 修复版 |
| 06_land.sh | 75671efa（双副本） | 修复版 |
| docs/xline_prereg_v1_1.md | b72e5126 | 现行 v1.4（含 §2.8/§2.8a） |
| analysis/t4_ref_closure.py | e850bf42 | v2 修复版 |
| sim_stereo_imu_config.yaml | 5c98dc0d | canonical 复原态（零 t2 键） |
| X 线臂文件（v11_7 目录内） | ca6f7797 | 10 键 cauchy=0.0，未装载 |
| t1_evidence/v11_7_2026-10-05/ | 12 件 | 本会话证据总目录 |
| 栈凭据 | node b7de133d+lib 59548c6a | 每轮实读+banner 核验流程在位 |
- commit 链（本会话）：2f67d89→58e4e9e→caf5d5a→62b0213→0c87233→3a31e16→148cc9a→1de177b（全推）；T4 线插入 b8e103f/3268a42。DECISION_LOG D-1005-T1-01～06。

## E. 等待状态登记（长档）

- **W-X4arm（新，头号）**：C.1 臂裁定——阻塞 B.1/B.2 全段；醒来首件=按裁定装载臂（arm_xline.sh 一键）+X1' 重飞。
- **W-machine（新）**：机器网络稳定性观察（C.2）；X4 窗口前建议先确认连续可达时长（用户侧）。
- **W-过目三件（C.5）**：STATUS 已标行。
- W-tag（v11.7）→并入 W-X4arm；W-deep→已闭（浅）；W-E（EXP-2 NUC 归档态）→不变。

## 悬案池（open）

gates 臂×机器态耦合可飞性（C.1 面）｜H-A 残面（C.4）｜走爬带残余（边界外）｜hover j0 带变宽（观测）｜机器层指纹载体（NUC 归档侧低优）｜P1 判据②｜goal 竞态｜G1 strace（就位待事件窗）｜实机 EV（暂不启用+回环同形态注记）｜CLI rostopic pub→echo 跨进程零消息角落异常（挂查：真实链 C++↔CLI 正常，仅 CLI↔CLI）｜双副本 5 脚本分叉（属线）。
已闭（v11.7 全部承件+disarm 五连败/对审候选①/引用闭环/锚算术 bug 定案/48 僵尸）。

## 附：本会话新坑（八条，均已 STATUS/commit 注记）

1. pgrep/pkill 模式串出现在自己 ssh 会话 cmdline=自匹配自杀（**四连实锤**；杀进程一律文件化脚本）。
2. harness 调 `~/sitl_sim/` 运行时副本——仓库副本修复≠生效（双副本部署纪律：md5 双落）。
3. catkin build 产物路径=`devel/.private/<pkg>/lib/<pkg>/X`——进程匹配模式须用共同后缀 `lib/<pkg>/<bin>`。
4. `--probecheck`=仅 init 地面轮模式（RA18gnd 先例语义），非"飞行轮挂探针"。
5. `set -u` 与 ROS profile 链共存必爆（source 之前禁 set -u）。
6. subprocess `text=True` 走 locale（非交互=C locale）——跨进程中文输出须显式 `encoding="utf-8"`。
7. 非交互 ssh 无 source ROS 时 rosbag 读静默空（复发一次；驱动脚本必须自带 source）。
8. 自写正则与判读器输出格式对不上的排查顺序：先字节级 repr 对照（本例=缺 `<`，"(<0.75" 格式）。
