# P3 计划内 reboot 通告契约——设计件 v1（T1 v11.25 阶段 4c；2026-10-07 16:2x）

## 缺口（正源=u2_failsafe_gap_review + 安全盘点件 6b）
- streamguard v4 发布侧连续性=真重启对消费者不可见（max step 0.073m 实测）——已缓解"流断"面;
- 残缺=消费者无法区分"自愈中"与"死亡"：F5 硬编码 1.0s 重启窗 vs A1 实测计划外窗 592s——
  语义重载待契约化（通告+max_recovery 参数）。

## 契约设计（v1）

### 生产侧（VINS/streamguard）
- 新话题 `/vins_estimator/reboot_notify`（std_msgs/UInt32，latched）：
  failureDetection 重启时 +1 发布（累计计数+header stamp）；streamguard resume 时发布
  resume 事件（同话题第二消息约定=resume 计数）。
- banner 面：[T2SG] REBOOT/RESUME 行已有（simvins.log grep 面）——话题化=程序可订阅面。

### 消费侧（px4ctrl/监控）
- 订阅 reboot_notify：收到→进入"计划内恢复窗"（参数 `reboot_tolerance/max_recovery_s`，
  默认 30.0，替换 F5 的 1.0s 硬编码语义）——窗内 odom 断/迟滞不触发 HAFIX 梯
  （**与 HAFIX 的交互=HAFIX dead_s 计时在收到 reboot_notify 时重置一次**=计划内恢复让路）;
  窗满流未恢复→按死亡处理（HAFIX 梯继续）。
- 监控面：t1_odom_monitor v1 增订阅=告警行区分"计划内恢复窗"（降级告警等级）。

## 实施状态（本窗如实）
- 设计件=本件（4c 底线交付）；
- 生产侧落码=批后窗视余量（与 HAFIX build 同窗候选）；
- 消费侧接线=px4ctrl HAFIX 交互项一行（reboot_notify 收到重置 ha_dead_since）——随 HAFIX
  验证轮后评估；未落码=下册件（跨夜里程碑，@DECISION_LOG 登记）。

## 判据零变动自查
P3 全部新增=新话题+消费窗参数；现行判读门值零触碰。
