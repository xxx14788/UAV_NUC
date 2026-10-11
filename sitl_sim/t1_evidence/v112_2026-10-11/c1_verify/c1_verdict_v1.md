# C-1 SITL 验证轮判决文书 v1.0（2026-10-11；软件收官合并册 单元1 头号件）

> 判据预注册于轮前（任务书单元 1 + unit4_c1_killpath_source_v1140.md §4，执行前冻结，零事后改判）。
> 轮=run_C1_124411（v2 轮；v1 轮 run_C1_122832 因 logger_topics.txt 配置事故 ulog 空壳弃用，见 §6）。

## 1. 判据（预注册原文）

- **复现** = ACK result=0 ∧ armed 恒 True（在线）∧ ulog arming_state 零翻转（离线）
  → 断链机理动态实锤 → 运行时候选三选收窄（events 补采）。
- **不复现** = disarm 生效（armed→False / arming_state 2→1 / 电机停+落地）
  → 间歇性证据 + SITL 与实机构建差异注记 + C-1 关闭（静态穷举定案+动态未复现）。

## 2. 轮事实

- 栈：3090 SITL（sitl_world_obstacles，五件套减 planner），ver_sw=d6f12ad1c4f70ad3230afd7d86e971421e02fef4（与 08_24_40 实机轮同构建）。
- 时序：起飞解锁 t+22.6 → 悬停稳定（z 带 NED −0.62~−0.76m）→ **单发 cmd179(param1=0,param2=21196) t+50.25**（rosrun mavros mavcmd long，COMMAND_LONG，src_comp=240/from_external=1，与实机同路径）→ 60s 观测窗 → 3 连发补验 t+171.1/174.1/176.9 → land 收卷 → 落地解锁 t+253.2。
- ulog：04_44_27.ulg（86.2MB，全默认主题集，logger 配置已回滚后产物）。

## 3. 五元组判决

| # | 元组 | 观测 | 判 |
|---|---|---|---|
| ① | 命令 ACK | **4×179 全 result=0（ACCEPTED）**；from_external=0，target=(1,240) | Commander 亲答 ACCEPTED |
| ② | arming_state | 注入窗（t+50~177）**零翻转**；全窗仅两翻：起飞 1→2 @t+22.6、落地 2→1 @t+253.2 | disarm 未执行 |
| ③ | actuator_armed | 注入窗恒 True（459 True 集中飞行段；False=地面/落地段） | 电机未停 |
| ④ | mode/nav_state | 注入窗 **100% OFFBOARD(14)**（279 帧）；nav_state=4 仅开机初始态与落地后 | 与实机 failsafe 态不同构仍复现（见 §4） |
| ⑤ | 悬停维持 | 注入窗 z 带 −0.62~−0.76m 稳定，无失高等散 | 悬停未受扰动 |

**判决 = 复现分支确认**（三判据全中，4/4 一致性含 3 连发）。

## 4. 三运行时候选收窄（复现分支产出）

静态穷举（定位文书 §2）三候选：①uORB 订阅代际/拷贝异常（command 循环 generation 校验路径）；②Commander 线程数据不一致窗口；③SITL 与实机构建差异。

本轮收窄：

- **候选③排除**——SITL 同构建（ver_sw 逐位同）复现，无需构建差异解释。
- **新排除：failsafe 态依赖**——08_24_40 实机轮 nav_state=4（AUTO_LOITER failsafe）；本轮注入窗 100% OFFBOARD(14) 健康态同样复现 → 「failsafe LOITER 态特有」假说否证。
- **候选①②维持开放**——且 SITL 可复现使下一步取证路径可行：gdb attach Commander（轮内可控复现点 t+50 注入）或加日志重编译轮（在 disarm()/answer_command 打点，观测返回值与状态写点分离的现场）。
- ACK 签名 from_external=0+target=(1,240) 排除 mavlink 层回声（回声型 from_external=1）——Commander 消费命令并答 ACCEPTED 的链路与 08_24_40 完全同构，分离点维持定位文书 §2 定案：**answer_command 发射条件与 disarm() 返回值语义之间**。
- events/log_message 主题默认 logger 不采（本轮未补采成功，v1 轮配置事故回滚；如需 events 面走重编译轮加采，不再用 logger_topics.txt 路径——见 §6）。

## 5. 与 08_24_40 实机轮同构对照

| 维度 | 08_24_40（实机） | run_C1_124411（SITL） | 同构 |
|---|---|---|---|
| 命令形态 | 412×179(0,21196) 连发 | 1 单发+3 连发 | ✓（连发窗内逐条同签名） |
| ACK | 412× result=0 | 4× result=0 | ✓ |
| ACK 源签名 | from_external=0 target=(1,240) | from_external=0 target=(1,240) | ✓ 逐位 |
| arming_state | 全窗恒 2（零翻转） | 注入窗零翻转（1→2→1 仅起飞/落地） | ✓ |
| actuator_armed | 1235/1235 true | 注入窗恒 True | ✓ |
| nav_state | 4（failsafe LOITER） | 14（OFFBOARD 健康） | **✗（复现不依赖态）** |
| 悬停维持 | 维持 | 维持（−0.62~−0.76 带稳） | ✓ |

## 6. 事故与勘误（本判决过程产生，如实入账）

1. **logger_topics.txt 替换语义事故**（v1 轮）：为补采 events/log_message 配置 rootfs/etc/logging/logger_topics.txt——PX4 logger 的 `initialize_logged_topics` 在该文件存在时**跳过默认主题集**（替换语义非追加，logged_topics.cpp L533 实读）→ v1 轮 ulog 84KB 空壳（仅 2 个空主题）。**已回滚删除配置**（rootfs/tmp 双位），v2 轮恢复全主题 86MB。教训入库：logger 额外主题采集改走重编译/参数路径，logger_topics.txt 禁用。
2. **mavros 订阅触发型流空采**（v1/v2 轮 z 采样全空）：/mavros/local_position/odom 为订阅驱动流，瞬时 `rostopic echo -n1` 首帧延迟>timeout → 60/60 空值。v2 已改持久 z_stream.csv 流（仍空=流文件写入滞后消费时序，z 面最终以 ulog vehicle_local_position 为准——z 带 §3⑤ 来自 ulog，在线面如实注记为缺陷）。
3. **/mavros/cmd/ack 在线 0 行**：话题在线面未采到（mavros 版本话题名/流形态未定），ACK 面以 ulog vehicle_command_ack 为正源（已全量提取，不影响判决）。
4. wa_gate --j0-decomp 无 ROS 环境时静默写 available=False（退出码 0=假成功）——j0d 滚入首跑 12 轮失收，source 后 20/20 复收（单元 2 注记）。

## 7. 工程结论与后续

- **C-1 定性升级：从「静态穷举定案+动态未测」→「静态+动态双定案」**——179(0,21196) 空中 forced disarm 的 ACK 假确认断链是**可复现的构建级行为**（SITL/实机同构建同构，非间歇、非 failsafe 态依赖）。
- 呈报件 §④ 措辞维持并加硬：该构建 179+21196 空中不可依赖且 **SITL 动态复现在案（本件）**；实机 FMU v6C/v1.17.0 路径未测维持（台架动力套窗专项=用户域）。
- kill 梯设计结论不变且再获正据：梯①盲降为主路径+梯③独立确认（不信 ACK）设计前瞻正确；**禁用任何依赖 179 ACK 的 kill 判定**。
- 下一步取证（下周期候选池，非本轮）：SITL 复现点可控 → gdb attach Commander 或 disarm()/answer_command 加日志重编译轮，钉死候选①②之一。

## 附录：证据索引

- round.ulg=04_44_27.ulg（86.2MB 全主题）；ulog_five_tuple.txt（pyulog 提取全量）；state_seq.tsv/hover_base.tsv/inject.txt/ack_online.csv（在线面）；round.log（轮全程）。
- 上游：unit4_c1_killpath_source_v1140.md（静态穷举+断链分离点定案，9112a272）；08_24_40.ulg（实机原始轮）。
- 轮脚本 t1_c1_verify_v1.sh（md5 b2251cf3，repo 正源）+ t1_c1_extract_ulog.py（4af2cb8d）。
