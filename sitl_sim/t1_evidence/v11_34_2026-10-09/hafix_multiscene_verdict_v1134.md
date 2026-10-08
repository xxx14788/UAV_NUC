# 2d HAFIX 多场景批 统一重判终判报告（T1 v11.34 单元0-①）

- 日期: 2026-10-09 03:5x；重判人: T1 (ZCode v11.34 会话)
- 批正源: v11_28_2026-10-07/unit3_3d_hafix_multirun (4 场景×5 轮, night_chain 2026-10-08 21:42-23:14 执行)
- 重判动机: 批 summary HAFIX 列全零 = grep 错文件 bug（批脚本 `t1_batch_3d.sh:34` grep drill stdout log，[HAFIX] 行实际落 ev/px4ctrl.log）——**批 summary 禁引用**（任务书既定）
- 重判正源: 每轮 ev 目录 `px4ctrl.log` [HAFIX] 行 + `RESULT.txt` LANDING/auto_disarm 行；gatehit.json 在 drill-D1 轮**全部不存在**（harness 产物面，如实注记；landed 由 RESULT.txt LANDING(<0.15) 收）
- ev 匹配修正: 批轮 log `ev=` 行时间戳与实际目录差 1s 者 2 例（220558→220559, 231036→231037）已回退匹配
- 重判脚本: `~/sitl_sim/t1_rejudge_hafix_v1134.py`（CSV: `hafix_rejudge_v1134.csv`）+ bag 探针 `t1_hafix_landed_probe.py`/`t1_hafix_armed_probe2.py`

## 一、预注册判据终判: 4 场景全 FAIL

判据原文（批脚本文末）: 每轮 HAFIX_lines>=1 ∧ landed=1；场景 PASS=5/5；3d PASS=4 场景全 PASS。

| 场景 | PASS/5 | 判定 |
|---|---|---|
| S1_hover_1m | 2/5 | FAIL |
| S2_hover_3m | 0/5 | FAIL |
| S3_transit | 1/5 | FAIL |
| S4_land_1m | 1/5(+r5 修正纳入后仍 1/5) | FAIL |

**[3d FINAL] FAIL**。**M1 行 5 维持半成（复标 ✓ 但多场景覆盖不成立）**。

## 二、有效性分账（20 轮）

- **有效轮 13**；**无效轮 7**：
  - 6×FATAL 拒跑（S1r4=224245, S2r1=214621"双目话题未出现", S2r2=220559, S3r3=223311, S3r4=225218, S4r2=221832 —— 后 5 个均 "SITL 未清(px4=1 gz=1)"）
  - 1×never-flew（S2r5=230253, truth z=0.1042 未离地）

## 三、有效轮 13 的形态分型（重判表+bag 探针）

1. **PASS 4 轮**（S1r1=214206, S1r3=221950, S3r5=230621, S4r4=225546）: 梯触发、真值 z 尾=0.10（地面）。**但 armed 恒 True——disarm 全程未发生**（唯一 armed 1→0 在 S4r4@96.0s = FC AUTO_DISARM 参数路径，非 HAFIX）。S4r4 实为 hafix=4 无 KILL 段（watch/cleared×2），落地=正常降落流程——按判据字面 PASS，语义注记=HAFIX 未实战走梯。
2. **悬空 FAIL 5 轮**（S1r2=215653, S2r3=222406, S2r4=224313, S3r2=220927, S4r3=223339）: 梯走完（含 KILL 行），**真值 z 冻结悬空 0.91-1.44m + armed=True + mavros state 持续到 bag 末 = 机体保持悬停，KILL 命令未生效**。
3. **无触发 FAIL 4 轮**（S1r5=225838, S3r1=214950, S4r1=215405, S4r5=231037）: hafix=0（注入时已非 @flying/降落流程接管; S4r1/S4r5 auto_disarm=1=FC 路径完成落地; S4r5 整轮 phys_green PASS 但 HAFIX 零触发）。

**KILL 行触发轮 8 中: 落地 3 / 悬停 5 = 生效率 37.5%**。

## 四、根因定位（源码级，PX4CtrlFSM.cpp L138-152）

```cpp
ROS_ERROR("[HAFIX] still armed ... -> KILL + disarm fallback");   // log 打在调用前, 无成功确认
mavros_msgs::CommandLong kill_srv;
kill_srv.request.command = 400;                                   // param1 未设=0 = REBOOT AUTOPILOT, 不是 KILL
kill_srv.request.confirmation = true;
reboot_FCU_srv.call(kill_srv);                                    // 实为 FC reboot 请求
mavros_msgs::CommandBool disarm_srv; ... arming_client_srv.call(disarm_srv);  // 空中 disarm 必被 PX4 拒
```

1. **KILL 语义错**: command 400 param1 缺省 0=reboot autopilot。PASS 轮"落地"= reboot 副作用停电机→自由落体；标准路径应为 MAV_CMD_DO_FLIGHT_TERMINATION / PX4 KILL 模式（set_mode）/ command 400 param1=3。
2. **log≠生效**: ROS_ERROR 行在 call() 之前，call 返回值不检查——5 轮悬空即"打了 KILL 行但请求未生效"（reboot 请求丢失/被拒/超时未查）。
3. **reboot 副作用毒化批编排**: FC reboot → SITL px4 进程残留 → 紧邻下一轮 "SITL 未清(px4=1 gz=1)" FATAL。**6 个 FATAL 中 5 个紧跟 KILL 结尾/异常轮**（215653→220559, 220927→221832, 222406→223311, 223339→224245, 224313→225218）——批有效性 13/20 的直接根因链闭环。

## 五、修复面（呈报，不擅动——判据零变动）

- P-HAFIX-1: KILL 路径改标准 kill（PX4 KILL 模式或 flight termination）+ param 补齐；log 行移到服务返回成功之后；失败重掷+失败必打 FAIL 行。
- P-HAFIX-2: disarm 空中必拒 → AUTO_LAND 落地检测（landed 输入）后再 disarm；或接受 kill-后-armed 残留并在监控 v1 里以"电机停+真值落地"为终态判据。
- P-HAFIX-3: 批编排轮间清场加固（drill 前强清 px4/gz 残留）+ 批轮 log 的 ev= 时间戳差一秒修正（drill 脚本目录名生成）。
- 与 M1 行 4 的关系: D1 单轮复验（v11.28, 落地 z=0.10）属于"生效路径"运气侧——多场景批证伪其代表性。

## 六、证据链

- 重判 CSV: `~/sitl_sim/t1_evidence/v11_34_2026-10-09/hafix_rejudge_v1134.csv`
- bag 探针输出（armed 跳变/z 尾序列）: 本文件 §三 + 探针脚本可复跑
- FATAL 链: 各 FATAL 轮 round.log `took-over from ...` 行
- 源码: `~/catkin_ws/src/px4ctrl/src/PX4CtrlFSM.cpp` L138-152（commit 栈=0b581422 HAFIX 引入）
