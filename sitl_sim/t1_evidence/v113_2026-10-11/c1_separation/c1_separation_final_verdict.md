# C-1 候选分离终局判决 v1.0（2026-10-11；工程合并 v1.6 单元1；取代 c1_verdict_v1.md §4 候选框架）

> 判据预注册于轮前（t1_c1_verify_v2.sh 头部 + 任务书单元 1，执行前冻结，零事后改判）。
> 取证构建 F1 = px4 二进制 md5 0bac7286cf38075f8880880b1eb9c9d2（git HEAD 仍 d6f12ad1c4，
> Commander.cpp 8 处 C1FR 纯打印取证点未提交——构建差异如实登记，行为面零改动）。
> 轮 1=run_C1re_183315（回归，PASS）；轮 2=run_C1se_184008（分离，本判决主证）；
> 轮 3=run_C1v3_disarm_185451（正控 disarm）；轮 4=run_C1v3_term_*（正控 termination）。

## 1. 分离判决：第三发现（候选 ①② 双否证）

| 面 | 观测 | 判 |
|---|---|---|
| 复现形态 | 4×179 全 ACK result=0；注入窗 arming 零翻转；actuator_armed 恒 True；OFFBOARD 悬停稳 | 与 v1 轮/08_24_40 同构（复现成立）|
| C1FR[loop] | 4×179 参数完好到达命令循环（p1=0.0000/p2=21196.0，src=1/240 ext=1，generation 零 PX4_ERR lost，零 COPY-FAILED）| **候选①（uORB 订阅代际/拷贝异常）否证**——拷贝面参数逐位正确 |
| C1FR[armdis] | cmd=179 全程零进入（仅起飞 arm action=1 与落地 disarm action=0 两处正常链）| **候选②（Commander 线程数据不一致窗）否证**——ARM_DISARM case 从未执行，无窗口可言 |
| C1FR[ack] | 4×179 各自 [ack] result=0（从 handle_command 尾部统一出口发）| ACK 合法出自**另一个 case** |
| ulog 全字段 | vehicle_command 4 行 src=1/240 ext=1 tgt=1/1；ack target=(1,240) | 与 [loop] 面一致（"src=1/2"为控制台行宽截断伪影，179_fields 提取器+ulog 双源勘误）|

**真因 = MAVCmd 号错位**：`179 = MAV_CMD_DO_SET_HOME`（非 ARM_DISARM！）；
`400 = MAV_CMD_COMPONENT_ARM_DISARM`；`185 = MAV_CMD_DO_FLIGHTTERMINATION`。
注入的 `179(0,21196)` = "将 HOME 设为指定坐标 (lat=0,lon=0,alt=0)"（param2/3/4 被 SET_HOME
分支解释为 roll/pitch/yaw 并 wrap）→ setHomePosition 成功 → **ACCEPTED + 零电机效果 =
固件的完全正确行为**。"ACK 假确认断链"不存在——ACK 说的和做的一致，只是做的不是我们以为的事。

## 2. 根因坐位（companion 侧，非固件）

`src/px4ctrl/src/fsm_decision.h`（修复前）：

```cpp
constexpr int    HAFIX_KILL_MAVCMD = 400;   // 意图 FLIGHTTERMINATION(=185), 实发 400+p1=1.0 = ARM 请求
constexpr int    HAFIX_KILL2_MAVCMD = 179;  // 注释自称 "MAV_CMD_COMPONENT_ARM_DISARM" —— 错号起源
```

- 梯② 命令① `400(1.0)`：已解锁下 arm() → `isArmed()→NOT_CHANGED` → ACK ACCEPTED，无害空转。
- 梯② 命令② `179(0,21196)`：SET_HOME，被接受，无任何停机效果。
- v1139 close 册"已查明子机理：400 的 termination 意图被 failsafe 每周期覆写"**勘误为幻影**——
  400(1.0) 从未携带 termination 意图（185 才是），该"覆写"观测解释的是 ARM 空转 + 正常 failsafe。
- 08_24_40 实机轮 412×179 / v1139 复验批 15 轮 / v1 轮 / 本分离轮——全链同构，同一根因。

## 3. 处置（终局制：修复面 ≤1 人日 → 当周期落码+回归+验证轮）

- **修复**（commit 89dc2a1）：`HAFIX_KILL_MAVCMD 400→185`（真 termination 语义，p1=1.0 engage 不变）
  + `HAFIX_KILL2_MAVCMD 179→400`（真 forced disarm = 400(0,21196)）+ 注释/日志/gtest 断言同步。
- **回归**：catkin build 绿；test_fsm_decision **51/51 PASS**（新常量断言）。
- **正控验证轮 ×2**（该构建固件侧命令语义终证）：
  - disarm 轮 run_C1v3_disarm_185451：悬停单发 `400(0,21196)` → **45/45 armed False**（在线）
    + ulog arming 2→1 翻转 t=45.252（离线）+ C1FR 全链
    [armdis enter action=0 forced=1]→[disarm enter forced=1]→[**WROTE DISARMED**]→[res=1 CHANGED]→[ack 0]。
    **双面 PASS——该构建（d6f12ad1c4+F1）MAVLink forced disarm 完全可用。**
  - term 轮 run_C1v3_term_*：悬停单发 `185(1.0)` → ACK=0 + nav_state OFFBOARD(14)→**TERMINATION(13)**
    （pub 心跳 45.85s 起两帧 + ulog 2 样本）+ armed 语义正确保持。PASS。
    注记：终止后 simulator_mavlink poll timeout = 坠落副产物（px4 存活，C1FR 112 行），非缺陷。

## 4. 工程结论（呈报件 §④ 措辞换代）

1. **C-1 关闭，定性反转**：从"构建级 ACK 假确认断链（源码级不可能行为）"改为
   **"companion 侧 MAVCmd 号错位（179/400 混用），固件行为全程正确"**。
   v1 判决文书 c1_verdict_v1.md 的五元组观测仍有效，但其 §4 候选框架与 §7"构建级行为"定性被本件取代。
2. **kill 梯可用性换代**：梯② 双命令（185+400(0,21196)）在该构建 SITL 域**双正控验证通过**；
   实机同栈部署见 §5。禁用 179 作为 kill 命令（系统性错号，任何 179 kill 断言均无效）。
3. 梯①盲降为主 + 梯③独立确认设计维持不变（其前瞻性结论不受影响，反而加硬：
   旧梯② 之所以从未生效正是命令号错位，与其 ACK 相关的一切历史判读以本件为准重释）。
4. 历史勘误清单：v1139"termination 覆写"幻影；二次修复注释"179=COMPONENT_ARM_DISARM"错号起源；
   c1_verdict_v1 §6.3"/mavros/cmd/ack 在线 0 行"维持（本轮仍 0 行，ack 面正源=ulog）。

## 5. 部署状态

- 3090 SITL 域：已部署（commit 89dc2a1，本轮正控所验证）。
- 旧机（实机栈）：同一 px4ctrl 源——部署挂 2026-10-11 20:15 VINS 5h 窗重启时执行
  （pull + catkin build px4ctrl + px4ctrl 节点重启；VINS watch2 窗连续性不受影响，部署结果本件 §6 补行）。

## 6. 证据索引

- 分离轮：run_C1se_184008/{round.log, c1fr_console.txt(670 行), ulog_five_tuple.txt, round.ulg, inject.txt}
- 正控轮：run_C1v3_disarm_185451/{同上}, run_C1v3_term_*/{同上}
- 回归轮：run_C1re_183315/{同上}
- 提取器：t1_c1_179_fields.py（ulog 全字段）；t1_c1_extract_ulog.py（五元组，v1 既有）
- 取证补丁：t1_c1_forensic_patch.py（8 打点，幂等守卫）+ build_fingerprint.txt（各轮 EV 内）
- 修复：git 89dc2a1（fsm_decision.h/PX4CtrlFSM.cpp/test_fsm_decision.cpp + 本周期工具族）
- 上游：unit4_c1_killpath_source_v1140.md（静态穷举——其"179→ARM_DISARM case"映射行即错号起源之文献面）；
  c1_verdict_v1.md（v1 判决，观测有效/定性被取代）；08_24_40.ulg（实机原始轮）
