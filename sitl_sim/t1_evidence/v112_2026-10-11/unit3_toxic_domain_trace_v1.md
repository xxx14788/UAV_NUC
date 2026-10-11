# E8P/E12P 毒域溯源首步：数据面盘点+溯源设计稿 v1.0（2026-10-11；软件收官合并册 单元3 后半）

> 任务书原文：「前夜状态残留/域内污染源两假说的数据可得性盘点（前夜批轮日志/goal_trace 缺失面）+溯源设计稿」——数据面盘点不烧轮。

## 1. 数据可得性盘点（56 轮全量；R=RESULT 首行形态，gt=goal_trace 存在性，j0d=j0_decomp available）

按轮跑时刻（目录名）时间线（择要，全表可复扫）：

| 时段 | 批 | E8P/E12P 形态 | gt | j0d |
|---|---|---|---|---|
| 10-07 19:27-22:52 | X5 批 13 轮 | **全绿带**（anchor 稳态/到位 1.0 级；2 轮 NONE=M3p 早期形态） | 绿轮全 Y | T |
| 10-08 05:12-05:48 | M3pv2 首波 6 轮 | NONE×6（ENV 型收束） | N | - |
| 10-08 16:07-16:16 | M3R 批 3 轮 | **FAIL(STOPLOSS)×3 转 毒** | N | T |
| 10-09 04:11-06:11 | M3pbase/pv2 7 轮 | FAIL/绿/FAIL 混（**同批混绿**：_1 04:11 FAIL↔_2 04:18 绿） | 混 | T |
| 10-09 15:49 | WU1b 1 轮 | 绿（WU1b_A1 0.989） | Y | T |
| 10-09 05:45 起 | WU2/BX/TK/WU_FIX 10 轮 | **FAIL×9+NONE×1（全灭）** | N | T |
| 10-11 10:42-10:46 | A1X base 3 轮 | FAIL×3（毒域当夜耗尽复现，v11.40 判读注记维持） | N | T |

**四条结构性发现**：

1. **gt 缺失面=FAIL 轮 100%**：全部 STOPLOSS-ABORT 轮 goal_trace 缺失（提前收束致 t1_goal_trace 失收）；绿轮 100% 有 gt。⇒ **域内污染源假说（B）的直接证据面恰好整体缺失**——UTM goal 帧与 E8P FAIL 的交集**不可回查**（历史轮零 goal_pollution 面）。
2. **banner 全列同代 [T2SGCFG]**：跨 X5（绿代）→M3R（毒代）→A1X（复验代）无栈代/配置 banner 差——「前夜状态残留」假说（A）的**栈代残留子假说削弱**。
3. **同批同夜混绿**（M3pbase_1 FAIL @04:11 ↔ _2 绿 @04:18，相隔 7 分钟）：毒域非「夜级开关」而是**轮级彩票带偏毒**（绿率从 X5 代 ≈100% 跌至毒代 0-14%）。
4. **毒域形态=j0d 风暴爆发型**：FAIL 轮 j0_total 5.5~35.2m、n_jump_frames 33~496（jump/transit 混爆）；偶绿轮 njf=0/1（j0 1.8/3.6 边缘绿）。⇒ 非单帧毒注入型、非纯慢漂型——与 CauchyLoss(0) 风暴/饥饿雪崩形态族同谱。

## 2. 两假说盘点结论

- **假说 A（前夜状态残留）**：栈代 banner 面已削弱；残留层剩余候选=gate_params 载荷差异/warmup 段副作用/gazebo 世界状态（三面历史数据可得性：gate_params json 轮内落盘可回查 ✓、warmup 标记文件可回查 ✓、世界状态不可回查 ✗）。
- **假说 B（域内污染源）**：历史面 100% 缺失（§1.1），**当前不可证伪**——但 S8P goal 污染全程监听器（本日单元 3 前半已上线 vins_smoke 落码）未来轮自动补面。
- E12P 关联面：窗错位/banner 判读伪影已终裁（2b_contradiction_final_ruling v1.0，95ae856f）**不重开**；E12P 轮在盘点表内仅作时间线上下游参照（10-07 X5 全绿→10-09 WU2 起 FAIL）。

## 3. 溯源设计稿（三级递进，预注册判读面）

- **L0 零成本（本件已执行）**：56 轮盘点+banner 列+j0d 形态列——产出=四条结构性发现（§1）。
- **L1 低成本（1-2 轮复验，批窗内）**：E8P 复验轮（sitl_world_plain+E8 goal）全探针开：goal_pollution_watch（假说 B 直证面）+δA 监听+starve/配对率既有面+j0d 内置。判读预注册：①复现 FAIL ∧ 监听器捕 UTM 帧→假说 B 直证→L2a；②复现 FAIL ∧ 零污染帧→假说 A 加权→L2b；③不复现→毒域当夜耗尽复发（间歇）如实注记，累积复验面。
- **L2a 污染源定位（若 L1①）**：UTM 帧在场时 `rostopic info /move_base_simple/goal` publishers 实读+帧间隔/seq 域分析→发布者节点定位→（若为系统节点）截断或重映射处置。
- **L2b 状态残留定位（若 L1②）**：毒代 vs 绿代轮的 gate_params json diff+warmup 标记对照；世界状态面=SITL 重启间隔离实验（毒域轮后重启 SITL 再跑 E8P 对照——「残留随重启清除」判据）。
- 判读挂钩：复验轮 RESULT+j0d+监听器三面同表；毒域判读不入门值（结构面注记口径不变）。

## 4. 产物索引

- 盘点表全量=本件 §1（可复扫脚本=ls+RESULT/gt/j0d 三列循环，3090 现场执行 2026-10-11 13:0x）
- 上游：unit3_a1_expand_verdict_v1140.md §2（E8P 0/3 毒域耗尽复现）；unit5_baseline50pp_decomposition_v1.md（毒域两格三批全败结构性）；TK_S8P_B UTM 签名（642716,5722260,0）。
- 工具：goal_pollution_watch（本日上线，057707b3）——L1 的假说 B 证据面。

## 5. L1 复验轮判读（2026-10-11 13:28-13:30 提前执行；run_E8PL1_132824）

- **形态复现 ✓**：STOPLOSS-ABORT@pursuit-start 短轮 2min 收束（recovery=COMPLETE path=KILL）——与 A1X E8P base 3/3 同构；j0d=j0_total 35.52m/njf=138（风暴爆发型，§1.4 形态带内）。
- **判读预注册 L1① 命中=假说 B（域内污染源）直证**：goal_pollution_watch 监听器首战实捕污染帧 `{"type":"polluted","t":56.632,"seq":0,"x":642719.34,"y":4671811.32,"z":0.0}`——UTM 形态（x=642719 与 TK_S8P_B 642716 同族；y=4.67e6 与 S8P 5.72e6 不同带=多污染点候选）；**header.seq=0=独立发布者节点签名**（我方 pub seq 递增从 1 起）。
- **机理链成形**：UTM 污染 goal（t=56.6s）→planner GEN_NEW_TRAJ 向 1e6 级目标规划→VINS 追踪风暴（njf=138）→流断→STOPLOSS 止损→2min 短轮。E8P 毒域=goal 污染间歇彩票（§1.3 轮级彩票语义与此自洽）。
- **L2a 解锁**（发布者定位）：污染帧在场时 `rostopic info /move_base_simple/goal` publishers 实读——需轮内窗口（本轮已收束无法追），列下窗 L2a 首件；候选面=seq 域分析（污染帧恒 seq=0 或独立递增域=发布频率极低的常驻节点）。
- 假说 A（状态残留）：本轮 plain world+全新 SITL 起栈（无前夜状态）仍复现——**跨夜残留子假说进一步削弱**（连同 §1.2 banner 同代，A 假说主证据面基本收窄至 gate 参数/世界状态两冷门面）。
- 工具注记：early_landing_line 首战 $BAG 空展开 NA（显式路径修复已落码；本轮 RESULT 尾行手动补算同口径 z_end=0.104→landed=1）。

## 6. L2a 发布者定位战果（2026-10-11 13:36-14:04 五轮连环：L2A/L2B/L2C/L2D/L2E）

- **5/5 连续复现**（毒域今日全活跃态，另加 L1 共 6/6）——「当夜耗尽」语义修正：毒域=**当日活跃/跨日持续**形态（本日 13:28-14:04 窗全复现）。
- **watch 探针四代迭代**（v1.1 publishers 拍照→v1.2 rosgraph systemState→v1.3 rostopic 进程命令行→v1.4 TCP 连接层→v1.5 **callerid 帧级**）：
  - **发布者节点定案=`/mavros`**（L2E 帧级实证 `callerid:"/mavros"`）；
  - harness 全清白链：我方 rostopic pub 参数逐字正常（L2C/L2D 命令行快照）+seq 域证明（我方 pub seq 递增≠污染帧 seq 0/1 独立域）+全 launch 零 __name 重映射+plain world 零插件+api 插件二进制零 goal 字符串；
  - 排除链在案：gazebo world 插件（0 plugin）/api 插件（strings 无 move_base）/我方 pub（参数+seq 域）/非注册发布者（TCP 连接表全量核）。
- **坐标确定性**：(642719.x, 4671811.x) 六轮七帧微抖（小数级）=**确定性来源**（≈42.20N 118.75E zone50 UTM——地理换算型而非随机型）。
- **待单查（下窗 30 秒件）**：`rosnode info /mavros` 或污染在场时 `rostopic info /move_base_simple/goal`——mavros 插件树（waypoint/global_position 在载）中谁 advertise 了 goal 话题；候选方向=mavros 系统插件对 PX4 端某 MAVLink 消息的桥接转发。
- **机器防线即时价值**：S8P 首发窗预检+全程监听器已在 vins_smoke 默认在役（v1.5）——毒域轮自此带帧级 callerid 取证面。

## 7. 毒域根除链终局（2026-10-11 16:0x-16:2x 收官册补件——插件级定位+修复+双验证）

- **插件级定位终局=`guided_target`**（mavros_extras 1.20.1 src/plugins/guided_target.cpp）：libmavros_extras.so 符号级实证（/move_base_simple/goal 硬编码全局话题+gp_origin 订阅+geographic_msgs 转换助手——UTM 值来源闭环）；mission/waypoint 经两轮黑名单排除法排除（mission 黑名单下 goal 仍在；waypoint 黑名单下 goal 仍在；guided_target 黑名单下 **VERDICT=PASS advertise 面消失**）。
- **修复三件**：noMission pluginlist（mission+waypoint+guided_target 三黑名单，a0cdda9a）+ mavros_nomission.launch 包装（roslaunch CLI 空值 gcs_url:= 不算 set 坑绕过=launch 内 value="" 传递）+ 02_start_mavros.sh v2（ead14328）。本栈五件套零使用所黑三插件面（恢复路径在文件头注记）。
- **终验双判读（E8PFIX_161914）**：①**watch 零污染帧**（vs 修复前六轮 7 帧——goal 污染根除实证，判据命中）②轮仍 STOPLOSS（4min，j0=37.6/njf=270 风暴形态残留）。
- **E8P 毒域双层病理终局定案**：层1=goal UTM 污染（guided_target 桥，**已根除**）；层2=E8P 场景原生 VINS 风暴（无污染下 njf=270 仍在）——修复面归渲染/时戳域（T2 δ 系列在册结论域），非 harness 面。S8P 间歇污染（TK 批 3/5）随层1根除一并闭。
- 附带战果：t1_minimal_mavros_repro.sh（裸链最小复现法）+t1_fix_validate_bare.sh（插件面验证器）两工具入册；v1 首跑 set -u 先于 source 踩回（V3 老坑重申）。
