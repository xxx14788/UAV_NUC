# T1 任务书 v11.15 — 完成状态+客观卡点版（2026-10-06 晨；v11.14 弃读；纪律溯 v11.7）

> 你是 **T1（px4ctrl/基础设施+飞行批执行线）**。执行域=3090（`ssh nuc2`）。
> 本版=v11.13 会话的完成/未做/卡点客观清账（用户指令款：问题描述与方案建议分离）。
> 会话窗口：10-06 03:52-05:30；boot-2；判读工具链=rejudge_rounds.sh（补判制，权威）。

## 一、完成了什么

### 1. 单元 1 排查双刀 → 风暴根因定案（D-1006-T1-09）

- **静态 diff 六项**（boot_diff_report.md=ad177c91）：①banner 四轮逐字段全同=对 loss/cauchy/staged/cost_gate 完全盲 ②config 双副本路径分叉（RA13/14 走 T2 域 cfg_streamguard=5e688943；VRFY/VRG 走 canonical，飞时被覆写）③实际生效键值表（VINS 自打印 T2 knobs 行）：RA13/14=loss=1+cauchy=4.00；VRFY1=loss=1+cauchy=0.00；VRG1=loss=0 —— **RA13/14 与 VRFY1 非同键，"boot-0 同键干净"支柱勘误** ④PX4 参数导出不在案（如实登记）⑤栈代差：RA13/14=v3-rc（vins_node 10-05 14:34 重建前），VRFY/VRG=v4 ⑥sed 残迹=arm_xline v1 单行替换无守卫。
- **机理链定案**：estimator.cpp:1337 `CauchyLoss(T2_CAUCHY_DELTA/1.5)`，delta=0.0 → ρ(s)=0·log(∞)=NaN。风暴形态 ⇔ loss=1∧cauchy=0.00，**5/5 跨 boot（boot-1×4+boot-2×1）无一例外**；机器态假设对风暴面降级（NaN 机理无机器依赖）。与 T2 独立推导（commit 623202c）互证；T3 全库矩阵（GATE 臂 43 轮 0 四绿）合流。
- **修复部署**：arm_xline.sh v2（062d406e，vision_loss=0 替代"cauchy 置 0"错误关闭法+sed 源值守卫）；x4_batch.sh 臂门双升级（9592f96c，preflight config 四键校验+轮内 T2 knobs 行 loss=0 校验）。
- **VRFY2 验证轮全绿闭环**：boot-2/同栈/同位形 (8,-1,1)/同 guard 族，唯一变量 vision_loss——init 102s→3s，T2fail 110→0，NaN 1066→0，四指标 1/1/1/1 PASS（到位 0.176m，jump 0.100）。

### 2. 单元 2 X4 五位形批 → 执行完毕，结果=0/5 FAIL 汇总，不打 tag（D-1006-T1-10）

- 8 物理轮：分母 fail 4（X1final 到位 5.026/jump 5.765；X2g1R 到位 8.331 未动/jump 0.011；X2g3R 到位 4.792/**jump 24.219**；X3l2b 到位 4.181/jump 1.200）+ hostile 1（X3l2a，FAILDET×14，按预注册不计分母）+ 未定案 1（X2g1_041509，判读阶段进程被杀，RESULT 未落，bag 保全）。终判文=x4_final_verdict_v1113.md（b5ca92a6）。
- **三病灶分离**：①NaN 面=v2 臂批级消灭（8 轮全零 NaN，T2fail 除 X3l2a 外全零）②goal 段 VINS 帧跳变族 5/8 轮（巨幅 24-37m 两例；**X2g3 同位形 04:05 绿 0.100→05:01 跳 24.219**）③planner starve 2/8 轮（planner INIT→WAIT_TARGET 全静默，goal 重发无效，VINS 面极稳）。
- 遵裁定②诚实认证：0/5 不打 tag sitl-v0.4；双链核验链未触发（内嵌全绿前提未满足）。
- **judge_round 三 bug 首真轮暴露并修复**（RES 带前缀全分支失配=绿轮永不计绿；grep -c 零匹配双 0；NEVER 未 local）：dry-run 不跑 judge 故从未现形；修后以 rejudge_rounds.sh 补判全部轮（权威）；新增 --skip 续跑参数。
- 批事故四件在册：批进程死于启动会话关闭连带（BATCH END 手动补）；串行补飞链被 pkill 自匹配杀（cmdline 含 vins_smoke.sh 字样）；T3 拷贝窗重叠嫌疑窗登记（run_X2g1_041203=NUC 历史轮副本混入 3090 runs 目录，证据保全，非撞机）；X1final/X2g1 窗口与 T3 操作重叠的污染嫌疑（X2g3 轮 starve 与此窗相关，未定证）。

### 3. 单元 3 对照批（contrast_batch_verdict=8404bbff）

- HVNET1（悬停/v2 臂）：物理净（真值到位 0.077m）∧ VINS 跳 2.985m——"物理净/VINS 跳"标本，与 boot-1 SUPHV3b（3.9m）同型=悬停面跳变跨 boot。
- HVNET2：四指标全绿净轮（到位 0.115/jump 0.136）。净轮序列：DIAGGUARD2 0.418/VRG1 0.137/VRFY2 0.100/HVNET2 0.136。
- **RAREP1（cauchy=4.0 全家桶=RA13/14 精确复刻@v4 栈+boot-2）：PASS 全绿**（到位 0.095/jump 0.166/init 3s）。boot-1 DIAGCAUCHY never-init 未复现；17 分钟前同位形 v2 臂跳 24m=臂间对照材料。
- 终版三歧：Z=NaN 臂专属（已解）；C=cauchy 依赖排除（cauchy=4.0 全家桶跨栈绿）；M=跳变族呈时间维度性质（非 boot 维度）。
- 批后 canonical 已 restore（5c98dc0d）核验。

### 4. 单元 4 本线域件

- L-odom U2.5 考古=**负结果闭卷**（六路径穷尽：bash_history/ROS log/launch 参数/untracked/stash/轮脚本均无接线脚本；灭失定性；不阻塞——U2.5 已判 L-odom 臂=mavros 1.20.1 odom 插件 TF 缺陷修复面；lodom_archaeology_20261006=6772768d）。
- 探针 jump 面扩样闭环（jump_probe_expansion）：VRFY1 4 事件/峰 1.771 vs VRFY2 0 事件/0.093；批轮 X1final 5 事件/max_dP 18m、X3l2b 2 事件/7m；**prop 流全库恒净**（IMU 前端与跳变/NaN 无关旁证）。
- G1 strace 就位确认（t1_g1_strace.sh+prep 在册，待事件窗）；兜底硬件清单预写（hardware_escalation_playbook.md；触发条件=guard 族连挂 3 轮跨位形，未触发）；池≥3 无欠账。

### 5. 单元 5 代持件交还（STATUS 05:22 @全体）

T3 域=签收完毕（DECISION_LOG 390 行回执+背书抽验）；T2 域=净轮素材+NaN 标本链+never-init 特异性线索+臂间对照材料指针已通告；T4 域=X4 0/5 不打 tag 收账通告（wake 条件不触发）。

### 6. 收尾件

commit 15dc20d（12 件全 T1 零裹挟）已推 UAV_NUC；v11.14 双端 md5 0a463c00（本版取代）；会话记忆已写。

## 二、还有什么没做

1. **X4 五位形目标本身未达成**：0/5（目标=5/5 绿+tag sitl-v0.4）。序列现处 FAIL 汇总待裁态（见三.1）。
2. **X2g1_041509 未定案轮未补判**：bag 与日志保全完好，RESULT 缺失；补判未执行（工具在位=rejudge_rounds.sh/wa_gate --online）。
3. **planner starve 修复未做**：现象在册（2/8 轮），根因假设（goal 话题订阅竞态）未验证，修复未写码。
4. **autoattach 扩名未做**：X2g3R/RAREP1/HVNET1/HVNET2 四轮无探针数据（名段缺 HVNET|RAREP），jump 面读数缺口；补名未执行。
5. **双链核验链零实弹**：T3 复核→tag 机制已编码，本批未触发 PENDING 流程，机制未经真实流程验证。
6. 历史遗留未动：P2-A 严格净轮版（P2 on∧j0<0.5 轮本窗口未产生）；C.4 H-A 残面；E-4 袋指认（等对侧）；B 路 HF 重标（@T2 域）。

## 三、卡点与阻塞（客观问题描述）

### 3.1 X4 序列终态待用户裁定（头号等待，W-X4-final）

事实：X4 以 0/5 收束。轮次失败的两大主因（帧跳变族、planner starve）均无已验证的消除手段（见 3.2/3.3）；裁定②要求判据门值零放宽、仅 5/5 真绿打 tag。当前状态下重飞无改善依据、tag 无触发条件。裁定材料=终判文+对照批汇总+本节 3.2/3.3。

### 3.2 goal 段 VINS 帧跳变族（机理未定案；归因域=T2，本线供材已毕）

- 现象：goal 发布后的飞行段，VINS odometry 出现大幅帧跳（24.2m/anchor y=-37m/偏 41m 级两例，1.2-5.8m 三例），5/8 轮；悬停面亦现（HVNET1 2.985m）。判读口径归"T2 瞬态发散类"；T3 矩阵已归因 (7,-4,1) 簇=T2 瞬态族。
- 已钉死的事实：①同 boot/栈/臂/位形 (8,-1,1) 04:05 绿（jump 0.100）→05:01 跳 24.219（56 分钟间隔）——**时间维度转折，配置不可归因** ②17 分钟间隔臂间对照（v2 臂跳 24m vs cauchy=4.0 全家桶全绿）——臂不可归因 ③跳变轮 prop 流恒净（探针）④非 NaN/非 faildet 主导（除 X3l2a 伴生 14 次）⑤跨 boot 存在（boot-1 SUPHV3b 同型）。
- 未知的：触发条件/时间窗机理；T2 域主战在册（T2 v9.8/9.9），本线无进一步压缩手段——飞行线侧该问题**阻塞于 T2 定案**。

### 3.3 planner starve（间歇性，本线域，未修复）

- 现象：五件套起栈后 planner FSM 停留 WAIT_TARGET 全静默；goal 2×8s 首发重发+poscmd 三查均失败；机体起飞悬停不前进；VINS 面稳定（jump 0.011/0.042）。
- 频率 2/8（X2g3_042025/X2g1R_045147），轮内缓解无效；触发条件未知；与 T3 拷贝窗的时间相关性未定证。后果：任何轮可随机因此失败，且按判读口径计入 fail 分母（X2g1R 即如此——非 VINS 域失败占据分母）。

### 3.4 批处理无人值守可靠性（基础设施事实）

- 两实测失败模式：批进程随启动会话关闭连带死亡（04:48 X3l2b 判读后被杀，BATCH END 未落，setsid 未解耦）；bash -c 串行轮链 cmdline 含"vins_smoke.sh"字样被轮清理 pkill 模式自匹配杀。
- 现运行方式=单轮发射+人工调度；x4_batch"一发命令"设计意图在现机器机制下不可靠，无人值守全批跑有复发风险。

### 3.5 judge/dry-run 覆盖缺口（已修复，坑在册）

dry-run 不跑 judge → 三 bug（最重者绿轮判 fail）首真轮才暴露。历史轮已全部补判重写，无残留影响面；新建判读类脚本同坑。

### 3.6 跨线未确认项

- T3 背书抽验中发现 goal.txt 正源坑（详见 T3 v9.9 册）；对本线轮判读口径的影响范围未与 T3 核实。
- X2g1_041509 判读被杀的外部原因（会话关闭 vs 并发操作）未定证；污染嫌疑窗（04:12-04:16）在册。

### 3.7 环境面（在册，当前非阻塞）

USB WiFi（AIC8800）病态史在册（10-05 两波断连+驱动开机刷屏）；本会话 03:00 后稳定；兜底触发条件（guard 族连挂 3 轮跨位形）未满足。硬件两节点（eno1 插线/AIC 黑名单）待用户，未动。

### 3.8 控制侧（Windows）LAN 腿中断（本版落盘时实测，阻塞本线一切 3090 直连操作）

- 实测事实（09:40-09:5x）：Windows→192.168.0.4 ssh 超时 ∧ ICMP 100% 丢 ∧ 路由表无 192.168.0.0 条目；Windows WLAN 接口=已断开连接（无线电硬件开），扫描列表 15 SSID 无 uav123-5G，本机 WLAN 配置文件仅 Tsinghua22/WXchinainns（无实验室网段凭据）。
- **3090 本体存活**（经 NUC-tailscale 腿从 LAN 内证实）：NUC（192.168.0.5@uav123-5G，AP 正常）ping 192.168.0.4 通（2/2，rtt 4.6-535ms 抖动大）。
- 通路缺口：3090 不在 tailnet（成员仅 uav4/ipad/Windows 三台）；NUC→3090 无免密腿（实测 Permission denied；在册免密方向=3090→NUC 单向）；tailnet 无子网路由。
- 后果：本版任务书 3090 侧备份/STATUS 通告/git push 均阻塞，经 NUC 腿走 git 交付（push 到 UAV_NUC；3090 网络恢复后首件=pull+运行时副本同步+STATUS 补行）；**3090 侧操作面恢复依赖 Windows 侧重连实验室网（WLAN 手动连 uav123-5G 或插网线）——需用户动作，本线无凭据无手段**。

## 四、资产 md5（3090）

round_result=c708151f / prereg=b72e5126 / 栈=b7de133d+59548c6a / canonical=**5c98dc0d（restored）** / arm_xline.sh=062d406e（v2）/ x4_batch.sh=9592f96c / rejudge_rounds.sh（新，补判权威）/ boot_diff_report=ad177c91 / x4_final_verdict=b5ca92a6 / contrast_batch_verdict=8404bbff / lodom_archaeology=6772768d / x4_batch_report（批原始+事故登记） / 磁盘 593G（本会话 ~9 袋增量，下任 df 自查）。

## 五、等待登记

W-X4-final（用户，头号：材料=终判文+对照批汇总+本册 3.1-3.3）；W-网络（用户：Windows 侧重连实验室网——WLAN 连 uav123-5G 或插网线；恢复后 3090 首件=pull+运行时副本同步+STATUS 补行）；W-硬件（两节点确认，未触发）；W-E EXP-2 归档态；W-对侧：T2=跳变族材料消费、T3=goal.txt 坑核实+未定案轮补判可收、T4=0/5 收账回执。

## 六、交付注记（本版落盘时网络态）

本版写于 Windows 本地；因 3.8（Windows LAN 腿中断），3090 侧文件与 STATUS 未同步——本版经 NUC-tailscale 腿 push 至 UAV_NUC 仓（plans_T1_v11.15.md + DECISION_LOG D-1006-T1-11），双端 md5 以 Windows 本地与 git 仓为准；3090 端 md5 待网络恢复补验。v11.14 弃读。

## 悬案池

①跳变族时间维度转折（04:05-04:09 窗机理）②planner starve 间歇竞态（2/8，触发未知）③批/链会话关闭连带死亡机理（setsid 不足面）④X2g1_041509 补判⑤autoattach 名段缺口轮探针回填。
