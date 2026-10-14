# 全域收尾清零任务书 v1.1·完成态改写版（原 v1.0 2026-10-12 下发；2026-10-14 夜收官改写）

> **改写说明**：本册=第廿二周期单册制收官册，2026-10-14 夜执行完毕，本文件由执行者按实际完成情况改写为完成态（原 v1.0 的单元结构/保底清单/等待登记骨架保留，逐项加完成注记与凭据指针；文尾按收工双写制补三节）。原 v1.0 全文要点已内嵌于各单元注记，独立清账版=同目录 `2026-10-12_全域收尾清零_v1_close.md`。
> 执行者=全域收尾执行者（ZCode 会话，2026-10-14 18:51-20:10）。执行域=3090+旧机（中继）+本地 Windows。git=**78b8a2b**（五笔全推 abd1032→f681906→97e8746→7c58608→78b8a2b=UAV_NUC/main=HEAD，ahead=0）；夜报=3090 `~/sitl_sim/night_report_closure_v22_20261014.md`（三态 10/10 PASS）。
>
> **双必达终态：✓✓ 单元 1 五件全毕（含判据/修复自证）∧ 单元 2/3/4 全毕（零条件挂起）——软件侧全零终态收官。**
> 总设计师四裁定执行情况：①23:51 重启=用户主动（C1 结案销号，未再质疑）✓；②旧机禁起栈（本册旧机腿零起栈，只读+轻件）✓；③SITL 指纹在役 c5afa5a7 沿用+注记（三轮彩排 sitl.log 在位，未重编未换栈）✓；④专项② A/B 报告原文与合流版零触碰（月报/夜报仅引用 md5 572f965f 给定值）✓。
> 通道实况（v1.0 预案生效）：3090 直连 192.168.0.4 全程超时（本机 Windows 已实测不在 0.x 网段——以太网=10.236.232.219/16）→备份腿 nuc2j（nuc-ts 跳板）全代偿；DERP 中继下 ssh ConnectTimeout=20s 必超时、≥45s 稳（新坑入月报 59）。与 ③C 续作册 SITL 栈窗串行互斥全程无冲突（19:35 STATUS 排程通告在案）。

## 单元 0 开工收件 —— ✓ 完成（19:02 STATUS 开工行）

- **git 状态核**：本地相对 UAV_NUC/main **ahead=0**——v1.0 预设的"先 push 再 pull"处置免执行（③C 前任 6 笔已由其续任自推，现场 HEAD=2d1f60a=C3 round_result v1.5h；v1.0"以现场为准"条款生效）。工作树他册在改件（合流终版 M/t1_three_arm M/t2_m3p M+untracked）注记不动，本册五笔提交全 pathspec。
- **残场核查**：roscore/gzserver/px4/vins_node 全 0（③C 无活栈）。
- **df**：3090 402G（红线 20G 余量足）；旧机 28G（留观带边界，注记不动作）。
- **六工具锚抽验全中**：j3_image_metrics 3721399e+j3_fb_residual 08cb8829+j3_feature_density 7f45974b 双位一致；round_result.sh 双副本一致（048edae7=v1.5h 态，历史 mind 伪影勘误归 ③C 册在案）。

## 单元 1 专项① B-1 五件 —— ✓ 全毕（双必达①）

- **1.1 N6 修正操作序列端到端重放 ✓**：三轮下限达标+两废轮注记，判据预注册（轮目录 prereg.txt 跑前锁定，门值零变动）。
  | 轮 | 轮目录（3090 台账 preflight_boost_20261011/） | 判定 | 关键证据 |
  |---|---|---|---|
  | ctrl 对照 | rehearsal_n6fix_ctrl_194040 | **REPRODUCED** | CMD_CTRL 态 direct-LAND 90s 零反应（z drop=0.003m+armed 恒 True+fsm 恒 CMD_CTRL）=N6 判决同构复现，对照成立 |
  | fix1 修正① | rehearsal_n6fix_fix1_195548 | **PASS** | 单点停流（rosnode kill traj_server）→2s→LAND→t=9s AUTO_LAND→t=21s 触地 z=0.105+disarm |
  | fix2 修正② | rehearsal_n6fix_fix2_194738 | **PASS** | kill_planner_all→1s AUTO_HOVER（cmd_recv=0）→LAND 2s 消费→t=39s 触地+disarm；VINS 全程 220Hz 活=排除 HAFIX 盲降替代解释 |
  - 机理链双源：代码级=fsm_decision.h decide_cmd 的 `!rc_cmd→AUTO_HOVER`/`!cmd_ok→AUTO_HOVER` 两支（CMD_CTRL 态 LAND 被 REJECT[RJ_STATE]=N6 根源）；时序级=fix2 轮 sampler.tsv 1Hz 逐拍吻合（CMD_CTRL→AUTO_HOVER[cmd_recv=0]→AUTO_LAND）。
  - **fix1 RC 路深挖定案**：首版 RC 注入（CH5=2000/CH6=1000）被预注册防线正确拦截（/mavros/rc/in 有 mavros 发布者）；根因=px4ctrl 在役栈参数 **no_RC=true 根本不订阅 /mavros/rc/in**（px4ctrl_node.cpp L65+上游注释"mavros will still publish wrong rc messages although no RC is connected"）——真 RC 拨杆面在 SITL 栈结构性不可达=归首飞窗现场件（rc_cmd 断分支与已实证 cmd_ok 断分支 fsm 同构）。fix1-v2 按 v1.0 等价定义（"CH6 拨低等价=停 position_cmd 流"）改走单点停流，与 fix2 形成停流粒度对照。
  - 废轮 2 个留档：ctrl_193122（首版脚本 fsm_now() 抄漏 `awk '{print $1}'` 致 FATAL no_CMD_CTRL——栈行为实际正常）；fix1_194334（RC 防线 ABORT=设计正确的行为）。
  - 起栈防线全执行：全名单清场核验（x4_batch force_cleanup 名单∪rehearsal cleanup+pgrep 逐项核零）+栈窗锁（.n6fix_stack.lock 持 PID，收工已清）+STATUS 排程通告（19:35）。
  - 产物：判决书 `rehearsal_n6fix_verdict.md`（md5 9b55f06a）+三轮轮目录（prereg/obs.tsv/sampler.tsv/n6fix.bag/round_verdict.txt）；脚本 n6fix_rehearsal.sh v3=93b19163（Win/3090 双位，git 7c58608）。
- **1.2 A3 自动判定 grep 修复 ✓**：rehearsal.sh v7（02ed76a7，git abd1032）。根因确证=旧四模式与实物全不符（毒窗 01:17:12-22 实测：plain.log 1s 行流有空洞且全程无"跳变=非零"行；唯一可靠面=csv alarms 列中文告警串"单帧跳变:RED"，01:17:08/18 两行在案）。自证=a3_recheck_v7.sh 对 010939 轮已落盘数据重跑判定段 **A3_RECHECK=PASS** ∧ v6 旧模式同数据 **FAIL**（对照成立=修复真实改变结果非数据变化）；第一路走通，未动用 1.1 顺采备用路。
- **1.3 sampler.tsv 1Hz 采样器修复 ✓**：heredoc 内嵌→外置 rehearsal_sampler.py（4f78e836，git abd1032；setsid+nohup+三重定向+stdout 摘要行）。验证双面：短窗（roscore+发射+tail=1Hz 行流六行+清理净，evidence/sampler_shortwin_test_20261014/）+三轮彩排实载（1Hz fsm/armed/z 轨迹落盘，fix2 因果链判定正源）。
- **1.4 彩排袋 j0d 顺手画像 ✓**：两袋均含 odom 话题（004513 imu_propagate 12 万条），画像非零画像收口。004513=transit 主导健康形态（jump=0.0002m 地板/njf=38/n_prop=119576）；010939=jump 主导（26.06m/njf=96=D4 毒窗帧在袋的预期形态）。滚入 j0d_stats_20261011.csv（437→439，轮源注记行，git 7c58608）。产物：`~/sitl_sim/t3_results/j0d_rehearsal_20261014/`（两 j0_decomp.json，硬链接零拷贝）。
- **1.5 手册 v2.1+检查单 v1 双份部署 ✓**：Win docs/ 正源（7ef4b8b5/8174415a）→3090 `~/sitl_sim/docs/`+`~/catkin_ws/sitl_sim/docs/`，md5 三处一致，git 入库（abd1032）。

## 单元 2 T4 池件 —— ✓ 全毕

- **2.1 nuc_only 两袋搬运 ✓**：closure v2 先行确认引用源所指路径（t2v3_ground_205302←docs/t4_w1_reception_20261004.md:43→~/sitl_sim/bags/；v1_ground_salvage_211520←flight_log.md:42→catkin_ws t1_evidence/v1_2026-09-28/）→3090 侧 scp 经中继拉取（19:14-19:18，IO 预告先行）→**md5 双端逐位一致**（664e881e/28fe5193，对账表在 closure_dual_diff）。旧机只读零改动。
- **2.2 引用闭环 v2 双侧实例+差集表 ✓**：旧机 repo 同步（pull 89dc2a1→abd1032，工作树干净核=两 untracked 注记不动）→v2 实例旧机侧跑（--no-nuc）→双侧差集：present 199 共同+3090-only 3（T4 域载体单侧在位）+NUC-only 3（2 项经 2.1 搬运闭环+1 衍生 stem）→**新缺失=0**（既有五族口径零新增，"登记不修"族确认）。产物：`closure_dual_diff_20261014.md`+两实例报告（git f681906）。

## 单元 3 月报终并 —— ✓ 完成

137 基线（fb0cc25e）+9 新条=**146 终本**（md5 6b53cbcb 双位，git 97e8746）。来源分账：专项① 夜报 F 节 8 坑→新条 5（52-56）+复发 3；③C 前任清账版 4 坑→新条 2（57-58）+复发 2；本册新坑→新条 2（59-60）+复发 1；复发标注共 6 处按模板规则 4 不增条数（坑2→#51/坑3→A10/坑6→A4A5/③C 双副本→#47/③C DHCP→B17/本册 awk 三层转义→A18）。纪律执行：前后读数+加总校验+节头节尾算术闭合（5+2+2=9；3+2+1=6）；终本注记"实飞前夜终本（后续新坑进当期夜报）"落盘。范围纪律：可视化平台项目（③书系/③A/③B）零条目；③C 续作在役新坑以其自身清账版为界（前任 4 坑已按 v1.0 指定提取）。

## 单元 4 旧机腿 —— ✓ 全毕（零起栈，裁定②遵守）

- **4.1 5hwin3 第五数据点评级 ✓ 三面**：速率面（n=535 回归 R²=0.837 整体 0.77GB/h；**两段结构新发现**=前 300min 稳定 1.12-1.28GB/h+后 234min 骤降 0.20GB/h）；截断面（**翻案**=boot -4 终点 10-12 10:22:38 整机非正常停机实证[CSV 止采 10:22:17 领先 21s；journal 末尾无任何 shutdown 序列=硬停；OOM 全程零记录]——v1.0"机器 18:40 才再启=非整机截断"推测被 boot 历史勘误；5h 拐点 06:28 journal/内核零事件=进程内在拐点）；模型自洽面（前段隐含健康占比 51-59% 合理带；整体均值偏离以两段结构解释）。产物：`memleak_5hwin3_rating_20261014.md`（2c94b23d）+CSV 副本（git f681906）。
- **4.2 旧机 STATUS 陈旧副本回收 ✓**：`~/sitl_sim/STATUS.md`→`STATUS.stale_20261006.bak`（411999B 原样保留不删）+原路径指针文件（313B 两行=正源声明+改名声明）+ls 凭据（经中继执行）。
- **4.3 旧机 git 状态核 ✓**：`git status --short`（两 untracked：.catkin_tools/preview launch——注记不动）+pull 至 abd1032+log 凭据入 4.2 链。

## 单元 5 收尾 —— ✓ 完成

夜报（三态对账 10/10 PASS+可做而未做=应收全零+条件注记 3 件）=3090 `~/sitl_sim/night_report_closure_v22_20261014.md`（git 78b8a2b）；git 五笔全推（pathspec 逐件，零裹挟）；STATUS 收工镜像行（20:10）；Win 清账版三节=`2026-10-12_全域收尾清零_v1_close.md`；产物归位（Win t1/正源件+tmp 自清[他册在途件不动]）+ZCode 记忆落盘（closure-v22-campaign-20261014）。

## 保底清单 —— ⑩ 全过（10/10 PASS）

①单元 0-5 全执行 ✓ ②N6 修正路径彩排实证（判据预注册+对照）✓ ③dashboard 联动判定自动 PASS 自证 ✓ ④1Hz 采样器实采验证 ✓ ⑤两袋搬运 md5 对账 ✓ ⑥closure NUC 侧差集表 ✓ ⑦月报终并读数闭合 ✓ ⑧第五数据点评级三面 ✓ ⑨STATUS 陈旧副本回收 ✓ ⑩夜报+三态对账 ✓。

## 等待登记（终态处置）

- **W-用户：旧机起栈时机**——维持等待（用户在场操作期归用户明示；本册零旧机起栈）。动力套窗预授权链维持（支撑件已全交付：手册 v2.1+检查单 v1+N6 修正序列彩排实证+监控/止损件）。
- **合流终版**（572f965f）——月报/夜报按给定值引用，原文零触碰（裁定④）。
- **③C 互斥**——本册 3+1 轮起栈均在 19:35 排程通告窗内完成，零冲突。

---

## 二、接下来还有什么没做

1. **首飞窗现场确认件**（SITL 覆盖不到的域边界，非本册可做件）：CH5 手动终极接管面；**CH6 真 RC 拨杆面（本册新增定案：no_RC=true SITL 栈结构性不可达——rc_cmd 断分支与已实证的 cmd_ok 断分支 fsm 同构，代码级证据在判决书）**；RViz 2D Nav Goal GUI 面；实机 ulog 通道复验。
2. **W-用户面等待件**：旧机起栈时机（用户明示）；Windows↔192.168.0.x 网段连通恢复（见卡点 1）。
3. **③C 续作册仍在役**（主项目推进册，其收口归其自身清账版/夜报；本册已按 v1.0 指定范围提取其前任 4 坑入月报，其后新坑不在本册范围）。
4. 彩排三轮 n6fix.bag 未做 j0d 判读（v1.0 未要求；1.4 范围=004513/010939 两轮袋已毕；n6fix 袋以 prereg/obs/sampler 三源判定闭环，bag 留档备复盘）。

## 三、卡点与阻塞（客观描述：现象/证据/缺什么条件）

1. **3090 直连不可达（本窗全程）**：
   - 现象=Windows→192.168.0.4:22 连接超时；ping 100% 丢包；ARP 表无 .4 项。
   - 证据=本机 ipconfig 实测以太网 IP=10.236.232.219/16（**Windows 已不在 192.168.0.x 网段**——网络环境已变更）；tailscale status 显示旧机 uav4 active（经 DERP hkg 中继，RTT~480ms）；nuc-ts 跳板腿+DERP 高延迟下 ConnectTimeout≥45s 才稳定（20s 必超时，四连失败实测）。
   - 缺什么=Windows 与 192.168.0.x LAN 的物理/路由连通条件（网络环境属用户域：是否换了网络/路由器/AP，本册无从判断）。本册经 nuc2j 跳板全代偿完成全部单元（代价=通道延迟与偶发闪断，批处理已 setsid 自治化对冲）。
2. **无其他卡点**：本册双必达全达成、应收全零；软件侧全零终态。上表等待件均为用户域时机问题或域边界确认件，非工程阻塞。
