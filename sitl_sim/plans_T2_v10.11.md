# T2 任务书 v10.11 — 完成清账版（2026-10-10；四线第十八周期收工；bias 路线终结版）

> 你是 **T2（VINS 质量线）**。执行域=3090（`ssh nuc2`）。红线 1-24+预注册先行。
> **通用纪律（四册同源，全沿用）**：穷尽制收工（双必达=下限/可动面穷尽/《可做而未做清单》进夜报/窗口穷尽编排）+**会话驻留（四条完整版，四册同源逐字）**：①等待任何在途件（批/链/build/采集/判读材料/IO 窗）禁结束会话——前台轮询（sleep 60 盯产物/STATUS/进程存活）保持在场；②轮询间隙=穿插件时间（禁空转也禁离场）；③会话收工唯一条件=任务书全部单元完成 ∧ 在途件全部毕且结果全部消费 ∧ 穷尽制三条件；④会话因外因（网络/token）断开=事故而非收工模式——重启首件=消费在途件产物+STATUS 补行+继续；默认案推进制；判据/门值零变动；nuc3 冻结。
> STATUS 双文件机制（T3 v11.1 裁定）：工作正源=~/sitl_sim/STATUS.md（唯一实时写入点）；git 镜像=~/catkin_ws/sitl_sim/STATUS.md——收工 cp 随 commit。
> 台账=3090 `~/sitl_sim/t2_experiments.md`；产物=`t2_results/INPUTFACE/`；git 远端名=UAV_NUC（非 origin）。
> v10.10 执行版（c739427d）弃读存史；本件=权威现行。

## A. 完成账（2026-10-10 夜，v10.10 全单元）

1. **单元 0 编译环境复测**：catkin build vins+px4ctrl RC=0 全绿；册部署三处 md5 c739427d；现场勘定=零飞行进程/零锁/df 458G。
2. **单元 1 ②a box 落码+验证**：estimator.cpp L1429 盒界（共享帮助头 `t2_bias_box.h`：产线+gtest 同一代码路径）+键 `t2_bias_box` 默认 0（=legacy 逐位同）+env 旁路+banner `[T2BIASBOX]`；gtest 4/4（冻结域锁/off 逐位同/on 钳界/域内不扰动）+邻近回归零漂移（zeta 6/route 7/propagate 9）；干测两轮终判=**消歧式**（栈健康链 2/2 全过+行为面全落历史跳变族带——今夜跳态语境下单轮 verdict 失去判别力，预注册补条 A/B 在案 16960eb5）。
3. **单元 2 ②a 臂批（双必达①）**：8/8 对完整（16 轮+1 env 重试 E8P_B，05:38-06:41，同夜同栈+config md5 逐位同）——**NOT-EFFECTIVE：A(box) 12.5% vs B(base) 75.0% = -62.5pp**；三层判读全消费=层① box 生效 8/8（indom 100%+max_bas 0.41-0.65 全域内）∧层② 慢淋被治（dbadt A<B 7/8）∧层③ 过紧型（生效+被治+绿率反降+jump A>B 5/6+S12P 到位完美却降落失败 z1.039）=**误差转移进位姿实锤**；判决文书 box_arm_verdict_v1.md（2db067fb）。
4. **单元 3 判负分支全链兑现（双必达②）**：②b transit 相对锁落码（WA7G InitialBiasFactor 复用+窗口谓词共享纯函数 T2BiasTlockLogic+键 `t2_bias_tlock` 默认 0/`t2_bias_tlock_w` 默认 10+banner `[T2BIASTLK]`/`[T2TLOCK]` ENGAGE/RELEASE）+gtest 7/7+干测 banner 链实飞验证（ENGAGE@V=0.322 快照+RELEASE 完整窗）+②b 臂批 8/8 对完整（12:23-13:40）——**NOT-EFFECTIVE：A(tlock W=10) 25.0% vs B 25.0% = +0.0pp，方向一致 0/8**（双绿 2+双败 6）；机制面全治（dbadt A<B 8/8+jump A<B 5/6）；**bias 路线整体证伪定案文书** bias_route_final_verdict_v1.md（33020dc7）：四案终局 FEED✗（10-08）/预热✗（10-09，-37.5pp）/box✗（-62.5pp 过紧自伤）/tlock✗（+0.0pp 无效）——**约束漂移可治但绿率对 bias 约束零响应（两案夹逼定论）**；绿率修复面收敛定案=选格 70.5%+止损件兜底+架构级 transit 地板（回环不接入裁定维持）；实机真温漂场景工程价值未否定（域边界声明）。
5. **单元 4 尾件六件**：M3′ 36 轮袋路径指针回执 @T4（m3p_36round_manifest.txt；v2 N8P_3=NO-RESULT 零袋轮如实注记）；bc CSV alive 伪影修复 @T3（11 行 0→1 judge 正源重生成+批尾 join 补丁+原件备份）；X7 收敛素材包 @T3（x7_convergence_material_v1010.md f4b21500）；E8P_A 补飞注记销号 @T4（总设计师裁定不补）；W2 就绪门时序余量=仅注记不修（判据零变动纪律）；B2 前基线转录到货消费+回执（m3_prebaseline_v1.csv 18 轮，三方对照语境 10-08/09/10）。
6. **单元 5 X7 素材对接**：素材包交付（STATUS 通告）+定案后 §5 增补素材（bias 路线第四支柱）在册；T3 已消费部分（ca3d4d3 注记 2b tlock stats 消费在案）。
7. **事故 D-1010-T2-01 闭环**（详见 C-4/C-5）：干测首射误杀 T3 drill 活轮 042425（ENV-FAIL 收场）——登记+道歉+赔偿（受害轮复验 045450 完成）+锁侧修复（死主接管加场净门，侧锁四用例+真实 px4 场验证）+owner 构造根治提案 @T4。
8. git 推至 de655b0（交付经 T3 裹挟提交 ca3d4d3+归属注记 a899d01 入库，content intact 已验证；台账 HEAD=HOME 逐位同 a5817d70）。

## B. 剩余件（按优先序）

1. **实机域真绿率度量**（绿率终局三件之三——用户裁定路线最后一件；非 SITL 域）：实机静态/悬停/短任务窗的绿率分母建立+|Bas| 漂移-绿率相关性首测。**被 C-1 实机链阻塞**（非本线可动面）。
2. **A1 observe 扩批**（N8P≥6+E8P/S8O 各 3，同夜同栈 base 对照；判据沿 a1_observe_prereg_v1.md 冻结）：1/3 混合带证据不足的池件——需整夜飞行窗（~2h）。
3. W∈{5,20} 复验轮（②b 梯度扫描余下两档）：判据面止损在案——复审条件=实机真温漂场景开启（SITL 域已无信息增益）。
4. ②b 层①窗内偏差度量工具（全程 indom 对窗锁语义不适用；dbadt 8/8 已承证——纯精度装饰件，最低优）。
5. B2 转录深度对照（18 轮详单 vs 本夜两批 B 臂逐格——夜报回执已发，深度对照为可选增强）。
6. 批脚本 VINSMD5 改记 libvins_lib.so（薄壳盲区修复——下批前改，5 分钟件）。

## C. 卡点（客观描述，禁方案）

- **C-1 实机链断（阻塞 B-1 主件）**：旧机（192.168.0.6）2026-10-09 22:58 被用户断电——驻留栈全灭（mavros/rs/px4ctrl）+FC 一并断电（需重探测 /dev/ttyACM0）+磁盘断电完整性待验；栈重起命令正源在 T1 台账（2f/2c 件）——实机窗恢复是用户物理动作+T1 域前置，非本线可推进。
- **C-2 夜态漂移（跨批判读结构性限制）**：同批式同栈 B 臂基线跨批 75%↔25%（50pp 波动，S8O B 臂 0.160 PASS→4.118 FAIL 实证）——同夜配对内对照有效，但跨夜/跨批横向比较需按夜分层；单轮干测 verdict 对"基线不变"问题在跳态夜失去判别力（v10.10 补条 A 教训在案：干测门预设了稳定夜态，预设不成立）。
- **C-3 SITL 域绿率修复面穷尽（工作面真空）**：四案证伪+门参数化证伪（10-08）+选格/止损=规避兜底——SITL 域无在册未试修复面（穷尽制清账在 bias_route_final_verdict_v1.md §3）；绿率工作面下一站=实机域（被 C-1 阻）——本线在实机链恢复前无可动绿率主件。
- **C-4 锁 owner PID=$$ 构造脆弱性（根治在 T4）**：sitl_lock.sh owner=锁脚本子进程 PID，get 返回即死——活轮锁可被"合法"接管（本夜事故根因）；锁侧场净门已修（接管时场忙必拒），但 owner 构造根治（PID 载体 redesign）属锁设计归属 T4-E1——已提案待裁定。
- **C-5 vins_smoke.sh 进场断言后置（未动）**：进场"场净断言"在取锁之后——断言失败路径上已接管锁+EXIT trap 全场扫杀=事故杀伤链；本线不动该共享脚本（T1/T3 在途依赖+双副本守卫+非本线所有权），已记 @T4/@T1。
- **C-6 E8P plain 毒域当夜即耗尽**：两批 E8P 对均双败（NO-RESULT→r2 仍败/断流止损形态）——补轮至完整条款已用（1 重试/轮上限），该格绿率证据面结构性缺失（毒域当夜态），非分母不足可补。
- **C-7 跨批栈指纹不可追溯**：批脚本 VINSMD5 记录薄壳 vins_node（10-04 起恒定 d198718f）≠真实栈（libvins_lib.so）——②a 批的真实 lib md5 未在批 CSV 逐轮记录（批毕后无法精确追溯；banner 族=代码指纹兜底在案）。B-6 修复前此盲区续存。

## D. 资产（md5）

- 判据链：bias_constraint2_design_v1.md（c16f59c1，全程零变动兑现）/box_arm_batch_prereg_v1010.md（16960eb5 含补条 A/B）/tlock_arm_batch_prereg_v1010.md（1824df1f）/a1_observe_prereg_v1.md（038d41f9）
- 判读链：box_arm_verdict_v1.md（2db067fb）/bias_route_final_verdict_v1.md（33020dc7）/box_pairs_v1010.csv+tlock_pairs_v1010.csv（正源，banner 列 join 修复版+bak）
- 落码：src/estimator/{estimator.cpp 盒界 L1429+transit 锁 L1511 区, t2_bias_box.h, parameters.{h,cpp} 三键}+test_t2_bias_box.cpp（gtest 7/7）——全默认 off=legacy 逐位同
- 工具：t2_tools/{t2_box_diag.py, t2_box_pair_verdict.py, t2_tlock_pair_verdict.py, t2_bc_alive_join.py}+sitl_sim/{t2_bias_box_arm_v1010.sh, t2_bias_tlock_arm_v1010.sh, sitl_lock.sh 场净门修复}
- 对外件：x7_convergence_material_v1010.md（f4b21500）@T3/m3p_36round_manifest.txt @T4/bc 修复件 @T3
- 台账 t2_experiments.md=HEAD 逐位同（a5817d70）；git=de655b0（UAV_NUC/main 同步 0/0）

## E. 等待登记

- W-实机链恢复（用户断电→FC 重探测+栈重起[T1 台账正源]→实机窗——B-1 解锁前置）
- W-T3 判读支持回执（X7 素材包+bc 修复件已交付；T3 部分消费在案 ca3d4d3——完整回执未至）
- W-T4 M3′ 指针消费确认+锁 owner 构造根治提案裁定（C-4）
- W-T1/@T1 vins_smoke.sh 进场断言后置处置归属（C-5——共享脚本所有权协调）

## F. 坑账（六新，v10.10）

①sed 替换含字面反斜杠的文本不匹配（批脚本 banner grep 模式没换成→CSV 列 bug，join 修复）；②批脚本 VINSMD5 捕获薄壳 vins_node≠真实栈 libvins_lib.so（应记 lib md5）；③awk NR==FNR 跨文件 FS 陷阱（map 空格文件被逗号 FS 吞键）；④Windows 本机无 python3（编辑走专用工具勿依赖本机脚本）；⑤nohup 后台 ssh 挂壳（setsid+stdin 重定向+本地任务及时 stop）；⑥锁 owner PID=$$ 构造脆弱（事故根因，锁侧已修+根治提案 @T4）。
