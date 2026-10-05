# 3090 恢复后执行清单（T1 v11.7 交接契约；2026-10-05 夜拟）

> 机器态：192.168.0.4 ARP 应答正常（MAC ec:1a:c3:05:b1:3e,Ugreen 网卡）但 ICMP/全 TCP 端口
> （v4+v6）全丢——内核网栈半死或防火墙吞包,**需物理介入**（接显示器看控制台/硬重启）。
> 恢复判据：`ssh nuc2 true` 通。看门狗=Windows 侧后台轮询 60s×4h（.nuc2_watch.log）。
> 远程已完成件（全部已推远端,3090 侧 `cd ~/catkin_ws && git pull UAV_NUC main` 即得）：
> 2f67d89 池①t4_ref_closure NUC 腿 v2/58e4e9e v11.7 三件套（disarm 取证准备+prereg v1.4 草案
> +对审 v1.4 重判）/caf5d5a prereg 栈槽换代 streamguard v4。

## R0. 恢复首检（5 分钟）

1. `ssh nuc2 'date; df -h /home | tail -1; uptime; pgrep -cx gzserver rosbag px4 2>/dev/null'`
   — 磁盘水位（红线 df<20G 才动大 IO）+ 残留进程面。
2. `cd ~/catkin_ws && git status -s | head` —— **先看有无未提交残留**（断电前 T2/T3/T4 会话
   可能留脏树;有则先按属线处置再 pull）→ `git pull UAV_NUC main`（预期快进到 caf5d5a+）。
3. STATUS/DECISION_LOG 补登记（顺序勿倒）：
   - D-1005-T1-01 [代持 T4 域] 池① t4_ref_closure NUC 腿 v2（2f67d89）
   - D-1005-T1-02 [代持 T3 域] prereg 栈槽换代+streamguard v4 正源追认（caf5d5a,D-1004-T2-01 同型）
   - D-1005-T1-03 判据变更类·对审 v1.4 守卫+A⁻→B 重判（58e4e9e,**待用户过目行**）
   - STATUS 通告三连+3090 断连事件本身（时段/签名/处置）
4. 若 df 异常或 gzserver 残留 >2：先处置（W2 僵尸清理=池②,PID 定向）再飞行。

## R1. 单元 1 disarm 五轮取证（最高优先,X4 前置②）

素材=3090 ~/sitl_sim/t3_runs/（X2g1/X2g3/X2g4/X3l2a/X3l2b 各轮 px4ctrl stdout——
在 simvins.log 或 round.log 内）+ 06_land 段 stdout。

判读签名表+假设树（H-A..H-E）=已入册 `sitl_sim/t1_evidence/v11_7_2026-10-05/
unit1_disarm_forensics_prep.md`,按 S1-S10 逐签 grep:

```
S1 "AUTO_HOVER(L2) --> AUTO_LAND"     降落是否启动
S2 "From AUTO_LAND to MANUAL_CTRL(L1)!"(无 disarm)  出口①odom/rc 掉
S3 "Reject LAND in MANUAL_CTRL (RC manual priority"  U2.7 拒续发
S4 "U2.7: LAND accepted in MANUAL_CTRL"  U2.7 接纳
S5 "From AUTO_LAND to AUTO_HOVER(L2)!"   出口②中止
S6 "Wait for abount 10s"(无后续成功行)   卡 on_ground/landed
S7 "DISARM rejected by PX4!"             PX4 拒
S8 1Hz fsm_state 串 landed=/odom_recv=  时间线
S9 "Reject AUTO_LAND, which must be"     CMD_CTRL 期拒
S10 "Reject AUTO_HOVER(L2). P1/P2"       HOVER 不建立
```

定案→若 H-A/U3′族（S2+S3 主证）:预注册修复判据→AUTO_LAND 出口①加地面兜底 disarm
（extended_state OR |v|+z 判;纯视觉红线内）→gtest→单元5 供给轮降落段 disarm=1 验证。
若深问题（状态机级）→DECISION_LOG+W-deep 等用户。

## R2. 单元 3 anchor 案③实施（判读器红线 24 全流程）

1. prereg v1.4 冻结:草案已在册（v11_7 dir）,**入 docs/xline_prereg_v1_1.md 升 v1.4**
   （阈值 σ0.03/IQR0.06/N50/0.4s/δ0.15 已定标,J0 末端锚=不同规裁定在内）。
2. round_result.sh 改双锚取稳:.bak_v14+双副本 md5+三重验证;[T1 代持]入 t3 台账。
3. selftest L1（R1-R5 合成用例,含压线样本）/L2（X 五轮 C_sta 与探针在册值逐位等:
   0.036/1.16-3.42）/L3（22+X+U3′/MACH/BL/RA 全库重算双列,**预期唯一翻绿 X2g3**,
   其他任何翻转=停机复核）。
4. t3_wa_gate selftest 扩 anchor 用例;STATUS 通告（X2g3 1/5）。

## R3. 单元 4 收尾（轻件）

- A.4 销案通告（X4 前置④）+ 对审 v1.4 重判 STATUS 同波;
- 判据库条目 IMG-XAUDIT-GUARD-v1.4 落库（文本在册 img_xaudit_v14_guard_rejudge.md §3）。

## R4. 单元 5 供给轮 → R5. X 线复飞 → R6. tag

按任务书 v11.7 单元 5/6/7 原文执行（栈=b7de133d/59548c6a,每轮双 md5+[T2SGCFG]
banner 核验;净轮口径=j0<0.5∧0fail round_result 实读;四件同窗消费;X4 五连飞 5/5
→tag sitl-v0.4,打前五查）。

## 挂起提醒

- 池① 3090 侧权威重跑：`python3 sitl_sim/analysis/t4_ref_closure.py`（修复版在库;
  产物带新日期后缀,勿覆写历史 20261005 报告）。
- E-4 袋身份指认/探针 jump 面首验读数——按任务书池③④。
- T3 残留 rosbag（NUC 侧 PID 见 pgrep;**禁代杀**,在册正本对照优先原则）。
