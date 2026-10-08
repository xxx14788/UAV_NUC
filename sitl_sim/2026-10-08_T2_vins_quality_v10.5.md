# T2 任务书 v10.5 — 输入门证伪后清账版（2026-10-08 晨；v10.4 收卷；承账+剩余+卡点）

> 你是 **T2（VINS 质量线）**。执行域=3090（`ssh nuc2`）。红线 1-24+预注册先行+大 IO 错峰+STATUS 预告制沿用。
> 台账=3090 `~/sitl_sim/t2_experiments.md`；产物=`~/sitl_sim/t2_results/INPUTFACE/`（v10.4 建成；git 镜像=catkin_ws 仓 `sitl_sim/t2_results/INPUTFACE/`）。
> **v10.4 终态（git dfd36ba，四笔 c0836b0/8cfe93e/5d6685a/dfd36ba）**：双必达达成（1a 分带标定+REGEN v2.0 冻结）；**输入质量门参数化路线证伪定案**（M3' N8P 铁证对照）；1b 第 0 步=NO_VALID_CARRIER 定案；1c 编辑器验证 PASS。
> 四线分工沿用：T1=实机工程/安全链（其 3d HAFIX 批被本线 launch 事故所阻已修复，重跑窗本线避让）；T3=筛选判读统计；T4=在途件。

## 〇、v10.4 承接账（已完成件索引——执行细节正源=台账 v10.4 战役账两段）

| 件 | 终态 | 正源产物 |
|---|---|---|
| 1b 第 0 步（mavros bias 有效性） | **NO_VALID_CARRIER 定案**：imu/data 50Hz 与 data_raw 49.9Hz 无 bias 字段（结构无槽）；estimator_status 1Hz 无字段；data_raw−data 差分噪声主导（gyr std/mean≈10×，acc≈10-20×，同戳对齐率 17%）；sys_status 系 hint 误匹配（'ba' in battery）。**FEED 臂前提不成立，搁置如实登记**；②③不受影响 | `1b_bias_route/step0_probe_report.json`+设计件附表 |
| 1b 三件套设计件+预注册 | 冻结：③预热段参数（8s/yaw±30°@0.25Hz/pitch,roll±10°/xy±0.3m@0.2Hz/z0.5m；收敛指标=末 2s 变化率<初 2s 的 20%）+①FEED 三风险审计+②约束设计要点+SITL 外推性声明 | `1b_bias_route/1b_bias_three_prereg_v1.md` |
| 1a 采样+方法论 | observe 基建（T2_IQG_OBSERVE env 旁路，默认 0=逐位同原语义，c0836b0）+11 轮健康采样（24117 帧，A1 入池口径=VINS 健康三条件与任务面解耦）+分位带+方法论定案。**重大勘误：无门条件下两域输入分布几乎重合（stereo_r p50 plain 0.780 vs obstacles 0.770）——M3 v1.1"场景依赖"=门拒帧-饥饿反馈产物非场景差；分域被数据否决** | `calib_domainspec/`（run_roster+A1 附注+方法论）+池 CSV（sha256 6fdfee63ed6bf687） |
| REGEN v2.0 | **FROZEN 2026-10-08 04:15**：全域单阈 stereo_r L=0.095/U=0.895（n=22971 草案基准，复核条款 p5/p95 delta=0.000）；corners（p5=min=150 饱和）/depth_r（全池 1.0）退化常数→保 v1.1 值 80/0.5 | `regen_v2/REGEN_PREREG_v2_FROZEN.md`+`gate_params_v2.yaml`（md5 26c544dc） |
| M3' 批 | 36 有效轮（base 18+v2 18）+1 A/B 判别轮。**N8P 100%(base 3/3)→0%(v2 0/3) 饥饿病理复现→按 §4 预注册失败语义：REGEN v2 判负，输入质量门参数化路线整体证伪定案**。数据面：绿格组 base 7/9→v2 5/9（−22.2pp>10pp 门）；N8P 仅 3-4 次拒帧即 3.94m/1.22m 跳变（拒帧-饥饿-跳变雪崩，格子×时序敏感：S8O 137 拒仍 PASS 反证）；v1.1 阈 0.10 与健康带 L=0.095 逐点重合=参数空间无自由度 | `regen_v2/m3p_results.md`+`t3_results/m3p_{base,v2}_report.csv`+`config/sim_stereo/t2_m3p_v2_arm.yaml` |
| 1c 工具+材料 | t2_bag_editor.py v1.1 3090 验证 PASS（E8P 标本 dry-run RC=0：domain PASS/453073 消息盘点/6776 右目配对/mono-viol=0）；三臂设计件+判据冻结（消除=j0<1m；改变=时刻>2s 或幅值>30%；δ 梯度 6 点冻结）；**M-A 标本 md5 首冻=59c0b013f7**（run_X4_1e_E8P_035301，12GB/354s/6776×2，image topic 真名=/iris_stereo_vins/vins_cam_{left,right}/image_raw）；M-B=run_X4_1e_HVNET1_040009 | `1c_design/1c_three_arm_design_prereg_v1.md`+附表①②+`t2_tools/` |
| C.10 勘误 | 本地 9 行+3090 台账 12 行注记执行（.c10bak 双端备份，行数零变动验证）；STATUS.md 111 处=流式历史行不注（例外声明在册）；**索引收卷 v1.0** | `c10_jump_caliber_errata/c10_errata_index_v05.md`（含 §6 收卷节） |
| 工具族 | t2_bias_probe v1.0（修 3 bug：roslib 类加载/init_node/hint 词界）、t2_domain_quantiles v1.0、t2_metric_extract、t2_1a_pool_admit、t2_warmup_segment（selftest 4/4）、t2_1a_sample_batch.sh、t2_m3p_v2.sh——全在 `~/sitl_sim/t2_tools/`+git 镜像 | git 5d6685a |

**事故账（在册勿复发）**：T1 3d 批 4 轮 ENV-FAIL 根因=本线 launch 嵌套 substitution 语法错（roslaunch 禁 `$(optenv X $(env Y))`）——已修复 8cfe93e+STATUS 勘误+道歉登记；v2 臂两次无效重启（banner `%.2f` 将 0.095 显示"0.10"致误判停批；config 副本放 /tmp 致 calib 相对路径 left.yaml 解析失败→camodocal 相机空指针断言崩，修复=副本入 config 原目录）。坑账新增 7 条（台账收卷行）。

## 一、剩余未做件（v10.4 交办但未执行——无虚账）

### 单元 1：1c 三臂执行（材料齐备，纯时序未跑）

- **A 标戳**：M-A 全套 δ∈{0(align same),±2,±5,±10,±20}ms 6 点；M-B {0,±10}ms 3 点。副产物=td 敏感性曲线（@T1 1a 时间戳核查解读框架，联动条款在册）。
- **B 帧节奏**：M-A 四操作（drop-periodic 3/drop-random 0.10 seed7/downfreq 15Hz/reorder swap2）。
- **C 帧内容**：M-A 中央 60%×60%+全图两档 black 涂抹，窗=baseline 定位的跳变带±2s。
- 前置=baseline 重放 2×2（零编辑复现判据：j0 终态≥1m+时刻落原带±5s；不可复现换标本）。
- 预算 34 轮回放（每轮≈354s 袋长+起收）；回放管线=t3_replay.sh（私有 master 11313 系+--clock）；**同机互斥=与一切 SITL 飞行窗错峰**（M3' 教训：04:26 事故+本周期 launch 事故两案在册）；编辑袋用后即删+df 对账。
- 产出=三臂判决表（消除/改变形态/无作用三值×臂）+td 曲线。**三臂全无作用=回到"估计器内部独大"收窄**（判据已预注册）。

### 单元 2：预热段 ③ 写码验证+对照臂批（线二头号件——慢淋七成主因，唯一未遭证伪的 bias 路线件）

- t2_warmup_segment.py 本地 selftest 4/4 过；**3090 端到端未验证**（goal 话题/类型/频率三适配点+与 harness 起飞链串联）。
- 对照批=预热臂 vs 无预热臂配对 **≥8 对**（毒格名册 E8P 族+plain 毒带共享表）；指标=格级绿率（≥15pp+方向一致 ≥6/8 判有效）+bias 收敛曲线（冻结口径）+j0/失败分型；**新病面预案已预注册**（预热自伤=激励段内跳变率高于基线悬停段则如实收卷）。
- 控制变量铁律（在册）：与 1c/其他批完全独立，**任何其他批不加预热段**。

### 单元 3：证伪后路线的两候选（M3' 判读 §2 预注册分支——数据在册未执行）

客观依据（非方案推荐）：
- **候选 A（拒帧反馈循环打破）**：机理证据=N8P 3-4 拒帧即跳变雪崩+格子×时序敏感（S8O 137 拒仍 PASS）；子案三支已列（fail-open 加速 max_consec 30→3 量级/拒帧退避/报警不拒帧旁路）。observe 基建（c0836b0）已入库=报警子案的零开发基础。
- **候选 B（弃运行时门，转 1c 输入编辑/场景改造）**：机理依据=1e 输入面实锤（E8P 2/2 同刻同幅复现+慢漂确定性）；1c 三臂若臂 C（内容）命中=场景改造立项的触发条款在册。
- 两候选不互斥；**任何门行为改动（含 max_consec）=新预注册条目先行**（REGEN v2 §5 纪律沿用；判据门值动作守红线）。

### 单元 4：尾件池（低优先机会件）

- **社区调研收尾（v10.4 单元 4 未做）**：IMU-CAL-FEED 上游先例检索（VINS-Mono/Fusion issue+Fast-Drone-250 仓）+1e sim 域特有收案——产出 `1b_bias_route/upstream_survey.md`（无论有无先例如实登记）。
- **②transit 前 bias 约束**：设计要点在 1b §4（作用窗/权重梯度 {5,10,20}×基线/侵入面），写码前置条件=①③出果后评估或独立验证。
- **A3 臂差因果化**（转实机前若需）。
- **M3' 判读的 @T3 消费对账**：格级前后绿率数字已落盘（m3p_results.md），T3 侧三列分账口径的正式消费/复核未发生——对账回执待 T3。

## 二、卡点与阻塞（客观描述）

1. **T1 1c config v0 审签（单元 0b 债）**：T1 侧出稿阻塞于**旧机 FC（飞控）USB 断链**——dmesg 实证 10-07 14:52 注册 ttyACM0→22:37 USB disconnect 后未复现（/dev/ttyACM* 零设备）；与 AP 消失同窗（22:30-22:37），T1 判定共同断电事件嫌疑；AP 已 02:11 自愈、FC 未愈。**需用户物理检查**（飞控供电/USB 线两端/电源灯态）——T1 已呈报（通知非请示），恢复前 T2 审签件无稿可审。
2. **3090 环境漂移面**：v10.4 当夜毒格 base 臂整体偏绿（S8O 3/3、S12P 2/3 vs 史 0%）——同夜 base/v2 配对对照不受影响，但**格级绿率的绝对口径**（对史基线）受环境波动污染；跨夜比较毒格绝对绿率时须带同夜对照轴（判读纪律已在 m3p_results 注记）。
3. **拒帧致跳变的时序窗未定位**：N8P 3-4 拒即崩 vs S8O 137 拒不崩——致命拒帧发生在哪个窗口（起飞段/init 完成前后/transit 起点附近）**未知**；候选 A 的子案选择依赖此定位（现状=只有"格子×时序敏感"的二元事实）。
4. **mavros bias 面结构性缺失**：标准 MAVLink 消息族不外发 EKF2 bias 估值（第 0 步实测定案）——FEED 路线若重启，工程路仅剩 PX4 侧自定义 uORB→MAVLink 桥（侵入上游）或 data_raw−data 差分滤波（实测噪声主导、对齐率 17%，质量不足）。
5. **1c 回放/一切 SITL 飞行同机互斥**：1c 批（34 轮×~6min）+预热臂批（16 轮）+T1 3d 重跑窗共享 3090——时序编排约束（非硬阻塞），STATUS 预告+锁纪律沿用。
6. **nuc3 冻结中**（用户 10-08 裁定"先不管"）：不探测不提醒不等待，四线按旧机默认推进——对本线无直接任务影响，实机相关联动的范围以 T1 册为准。
7. **AP 断连复发风险**：AP 与 FC 疑似同插座断电事件在案（AP 02:11 自愈 FC 未愈=非同时恢复）——若 AP 再消失，本线配方=ap_watch.sh 后台监测+本地文书转产（v10.4 已验证）。

## 三、保底清单（禁提前收工）

①1c 三臂执行+判决表落盘（或 baseline 不可复现的如实收窄）②**预热段 3090 端到端验证+≥8 对对照批执行**③两候选推进的材料面（候选 A 子案预注册件或 1c 判决对候选 B 的触发裁决，至少其一落盘）④社区调研件（upstream_survey.md）⑤STATUS 诚实夜报。
**双必达：1c 三臂判决落盘 ∧ 预热段对照批执行；其一未达=收工违规（机器不可达除外）。**

## 四、等待登记

- W-T1 config v0 出稿（阻塞链=T1 FC 物理检查→T1 恢复→出稿）→本线 90min 时限审签。
- W-T3 M3' 判读消费回执（对账口径=格级前后绿率表）。
- W-飞行窗/IO 窗编排（与 T1 3d 重跑、T4 大 IO 件 STATUS 协调）。
- 池（≥3）：②transit 约束写码评估/A3 因果化/observe 报警模式的毒格绿率侦察批（若单元 3 排程有余量）。
