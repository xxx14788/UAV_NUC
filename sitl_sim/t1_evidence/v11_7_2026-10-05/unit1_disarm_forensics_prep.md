# 单元1 前置：disarm 五连败源码侧取证准备（2026-10-05 晚，T1 v11.7）

> 3090 网络半死（ARP 活/ICMP+全端口丢，看门狗挂后台），五轮 px4ctrl.log 在 3090 取不到。
> 本文档在 NUC 仓库副本（=远端 main 904f7f5，与 3090 同源）完成**代码侧全链审读**，
> 输出=对仗任务书"指令-状态-确认三面"的 log 判读签名表 + 假设树。
> 3090 恢复后第一件事：按本签名表 grep 五轮 px4ctrl.log 落判。

## 1. disarm 链全图（源码逐行，PX4CtrlFSM.cpp / fsm_decision.h @ 904f7f5）

```
06_land.sh: timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land (cmd=2 LAND)   ← LAND 只发 4s≈4条
   ↓ (前置：kill_planner_all.sh 已在 X 线 harness t3 链先行，cmd 过期→px4ctrl 回 AUTO_HOVER)
AUTO_HOVER: decide_hover → land_trigger → AUTO_LAND（快照 start_pose=当前 odom.p）
   ↓
AUTO_LAND 每拍: decide_land(fd_in)
   A) !rc_hover || !odom_ok → MANUAL_CTRL + offboard_off，【无 disarm 分支】   ← 陷阱出口①
   B) !rc_cmd → AUTO_HOVER（中止降落）                                        ← 陷阱出口②
   C) !landed → 下降中（des = start_pose + (0,0,-speed·dt)，odom 系自洽）
   D) landed ∧ px4_on_ground → MANUAL_CTRL + disarm=true
        ↓ FSM 侧：rotor_low_speed_during_land=true → "Wait for abount 10s..."
        ↓ fd_in.px4_on_ground 再验 → toggle_arm_disarm(false)（限 1Hz 重试）
        ↓ 成功 → "AUTO_LAND --> MANUAL_CTRL(L1)" + offboard off
        ↓ 失败 → "DISARM rejected by PX4!"（每秒重试）
land_detector（px4ctrl 自身）: C1 des.z-odom.z<-0.5 ∧ C2 |odom.v|<0.1 保持 3.0s → landed=true
px4_on_ground = mavros extended_state.landed_state == LANDED_STATE_ON_GROUND(1)
U2.7（MANUAL 态收 LAND, PX4CtrlFSM.cpp:185）:
   no_RC∧armed∧odom_ok∧|v|≤3 → AUTO_HOVER（"U2.7: LAND accepted in MANUAL_CTRL..."）→ 下一条 LAND→AUTO_LAND
   RJ_DISARMED → "LAND in MANUAL_CTRL ignored (disarmed)"
   其他 → "Reject LAND in MANUAL_CTRL (RC manual priority, or no odom / vel>3)"
```

## 2. 三面取证签名表（对五轮 px4ctrl.log 直接 grep）

| # | 签名（原文） | 判读 |
|---|---|---|
| S1 | `AUTO_HOVER(L2) --> AUTO_LAND` 有无 | 降落是否启动（面1=指令到达） |
| S2 | `From AUTO_LAND to MANUAL_CTRL(L1)!`（无 disarm 版） | 出口①：降落中 rc_hover/odom_ok 掉（U3′族入口） |
| S3 | `Reject LAND in MANUAL_CTRL (RC manual priority, or no odom / vel>3)` | 出口①后续：LAND 再发被 U2.7 拒（odom 死/v 超） |
| S4 | `U2.7: LAND accepted in MANUAL_CTRL` | U2.7 接纳路径被走到（MANUAL 起步型） |
| S5 | `From AUTO_LAND to AUTO_HOVER(L2)!` | 出口②：rc_cmd 掉→中止降落 |
| S6 | `Wait for abount 10s` 有、其后无 `AUTO_LAND --> MANUAL_CTRL` | 卡在 landed∧等待 on_ground（面3=确认缺） |
| S7 | `DISARM rejected by PX4!` | PX4 拒 disarm（landed_state≠1 / EKF2 in-air） |
| S8 | 1Hz fsm_state 自监视串 `landed= odom_recv= armed=` 时间线 | C12 是否达成 / odom 流断点时刻 |
| S9 | `Reject AUTO_LAND, which must be triggered in AUTO_HOVER` | CMD_CTRL 期 LAND 被拒（planner 未死透/cmd 未过期） |
| S10 | `[px4ctrl] Reject AUTO_HOVER(L2). P1/P2` | P1/P2 拒绝入 HOVER（降落序列根本没建立） |

面2（状态机收 LAND 时所在态）由 S1/S4/S9/S10 组合定；
面3（等待条件）由 S6/S7/S8 定；被拒点由 S3/S7/S9 定。

## 3. 假设树（预注册；log 落判前不定案）

- **H-A 出口①odom 断型（U3′族主候选）**：低空下洗/图像退化→VINS odom 流断→odom_ok=0→AUTO_LAND 侧滑 MANUAL（无 disarm）；后续 LAND 重发被 S3 拒。
  U2.7 修复不覆盖此路径=「修复不完整」的机理答案（U2.7 只修 MANUAL 起步收 LAND，不修降落中途 odom 断）。
  **与任务书矛盾点对仗**：0e832aa7 含 U2.7 仍五连败 ⇒ 若 log=S2+S3 → 定案 H-A。
- **H-B C12 不达成型**：VINS 速度噪声/landed=false 永等（S6 无 S7）；des-odom 自洽但 v 噪声>0.1。
- **H-C extended_state 型**：px4_on_ground 永假（S6+S7 或 S6 无 disarm 调用）；EKF2 EV 断流→landed_state 卡 IN_AIR/UNDEFINED。
- **H-D PX4 拒绝型**：S7 出现且持续；PX4 侧 land detector 判 in-air（视觉 EV 消失后 EKF2 高度不确定）。
- **H-E 指令面型**：S1 缺（LAND 4s 窗口内 px4ctrl 不在可消费态，如 cmd 未过期回不了 HOVER）；S9 出现。
- 附带核对：P1 latch（birth_mismatch）在 armed 期不清除 → S10 拒 HOVER → 降落链根本不建立（五连败是否同型待 log）。

## 4. 修复方向（取证定案后才动；预注册判据先行）

- H-A：AUTO_LAND 出口①加"已在地面（landed_state 或 |odom.v|+z 判）→ 仍执行 disarm 尝试"兜底，
  或 odom 断时以 mavros/local_position+extended_state 降级继续降落判（**纯视觉红线内**，无 GPS）。
- H-B/H-C：landed 判据加 mavros 侧独立通道（extended_state OR 化）——预注册阈值，不放宽门。
- H-D：disarm 重试从 1Hz 提到 1Hz+落判兜底 timeout（如 landed 后 30s 强制降级 set_mode+disarm 序列）。
- 一律走：预注册判据→小修→gtest→单元5 供给轮降落段 disarm=1 验证（任务书原文）。

## 5. 素材清单（3090 恢复后取）

五轮=X2g1/X2g3/X2g4/X3l2a/X3l2b 的 px4ctrl.log（3090 ~/sitl_sim/t1_evidence/ 各轮目录）+
对应轮 06_land 段 stdout（LOG 文件）+ /mavros/state、/mavros/extended_state 若录袋可回读。
