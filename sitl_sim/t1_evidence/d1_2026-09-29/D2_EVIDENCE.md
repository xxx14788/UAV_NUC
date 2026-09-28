# T1-D2 px4ctrl 垃圾 odom 合理性门：取证、设计、实现与验证（2026-09-29 夜）

状态：门已实现（本地部署脚本就绪，NUC 网络中断待部署）+ gtest 9 用例就绪；部署与双门禁待 NUC 恢复

## 1. 离线取证（D2-1）：垃圾 odom 签名 + px4ctrl 行为时间线

工具：`sitl_sim/analysis/d2_route_scan.py`（新增，topics 过滤+10s 桶统计+真值抽稀+armed/fsm
时间线；遵守 24.3GB bag 只做过滤+时间窗读取纪律——route7 为单遍低频骨架扫，爆散窗细扫按需）。

### 1.1 垃圾 odom 签名（量化）

| 特征 | 健康链（hover/ground/route7 前 20s） | 爆散爬升期（峰值前 10-20s） | 爆散期 |
|---|---|---|---|
| v_mean (m/s) | 0.01-0.3 | 1.4 → 9 | 25 → 3800（route7） |
| v_max (m/s) | 1.2-1.35 | 3.8-35 | 26-3800 |
| 帧间位置跳变 (m) | ≤0.05 | 0.2-1.6 | 5-66 |
| p_max (m) | ~1.3 | 12-90 | 173 → 891,491（route7） |

数据源：route7（t2v3_route_215016.bag 23G 单遍桶扫）、X1 爆散三轮
（run_X1_232055 / 235025 / 001817，vins_smoke_runs 小袋）。

### 1.2 px4ctrl 行为时间线（X1_232055， fsm_state 全程在袋）

| t (s) | 事件 |
|---|---|
| 4.1 | armed |
| 9.0 | AUTO_HOVER（入口速度门通过，此时 odom 尚正常） |
| 21.1 | CMD_CTRL（开始跟随 planner） |
| 30-50 | odom 爆散爬升（v_mean 1.36→5.25→14.55，jump 0.59→1.56→2.09） |
| 50-108 | odom p_max 58→1000 m，v_mean 20-25，jump 至 64 m；**fsm 全程停在 CMD_CTRL 无任何降级**；thrust 满 1.00 |
| 89.1 | disarm（T3 台账：真值仅飘 3.7m + auto disarm——真值全程 (1.01,0.98,0.10) 附近） |
| 108.7 | MANUAL_CTRL（disarm 后） |

**px4ctrl 跟随垃圾值 68 秒（21.1→89.6 CMD_CTRL）而新鲜度门零拦截**——odom 一直"新鲜"。
route7 同型：armed 全程 700+ s，真值 flyaway 至 (17.97,-4.11)（18 m），odom 同报 89 万米；
该轮（21:50）早于 T2 发布端有界性防线入库（23:45，8de82a9），毒值无阻出门。
235025/001817 同类（173m/414m；001817 在 60.2s 有 MANUAL_CTRL 切换但为 disarm 之后）。

### 1.3 结论

- 新鲜度门（PX4CtrlFSM.cpp:579 odom_is_received，唯一健康判定）对"新鲜但疯狂"的流零防御；
  入口一次性速度门（:83 |v|>3 拒绝进 AUTO_HOVER）不覆盖运行中。
- EKF2 链有 vins_to_mavros 门（W4：跳变>1m 或速度>5m/s 停转发），**px4ctrl 直供链
  （imu_propagate）无任何门**——T2 22:45 点名核验项，本节实证确认。
- 爆散有 10-20s 可识别爬升期（jump 0.59-1.6、v_mean 1.4-9），值合理性门可在此窗口拦截。

## 2. 设计（D2-2）

`src/odom_sanity.h`（新，header-only 纯函数）+ `Odom_Data_t::feed` 集成：

- 三层门：|v| 幅值（max_vel）、帧间位置跳变（max_jump）、|dv|/dt（max_acc）；NaN 拒收；
  重启窗（流中断 ≥1s 后首帧只做幅值门，防 VINS 重启重锚误杀）。
- **违规帧拒绝更新**：state（msg/rcv_stamp/p/v/q/w）保持最后一个被接受帧 → 持续垃圾 =
  rcv_stamp 停走 → msg_timeout.odom 到期 → **既有**降级路径（AUTO_HOVER→MANUAL_CTRL）触发，
  与真实 odom 停流不可区分。不新增行为类；armed 态断连行为不动（红线）。
- 单帧违规不毒化参考（下一健康帧即恢复接受）；拒绝日志限流（warn_every=50）。
- 参数 `odom_gate/{enabled,max_vel,max_acc,max_jump}`：**默认 enabled=false=旧行为**
  （实机 yaml 不含 key；实机启用与否留给实机线决策并登记）。SITL `ctrl_param_sitl.yaml`
  显式 enabled: true + 5.0/10.0/1.0。

### 阈值标定依据（实测包络）

- max_vel=5.0：健康链 v_max 1.2-1.35（含起飞瞬态）× 裕量；X1_235025 v_mean 26 在此线拦；
  X1_232055 v_mean 越线在 ~52s（bucket5 5.25）。
- max_jump=1.0：健康链 ≤0.05、病链重锚 0.05-0.6、X1 起飞段瞬态 0.24-0.45（<1.0 不误杀）、
  爆散爬升 1.56（232055 bucket4，~42s——**三层里最早的拦截点**）、爆散期 5-66。
- max_acc=10.0：健康悬停 2.5 m/s² 级 × 裕量（对平滑爬升型爆散的补充层）。
- 预期拦截时刻（按 1.1 时间线）：232055 ~42s（jump 门）、001817 ~35s（jump 3.12）、
  235025 ~15s（vel 门）——均在物理偏离失控前（真值 3.7m 飘移发生在此后）。

## 3. 实现

变更文件：src/odom_sanity.h（新）、input.h（Odom_Data_t 成员 sanity_cfg/sanity_st）、
input.cpp（feed 入口门）、PX4CtrlParam.h/.cpp（非 essential 参数读取+启动日志）、
px4ctrl_node.cpp（配置注入）、test/test_odom_sanity.cpp（gtest）、CMakeLists.txt
（test_odom_sanity target，仿 T3-W9 attitude_utils 先例）、config/ctrl_param_sitl.yaml。

## 4. gtest（9 用例，部署后跑）

阈值边界（5.0 收/5.01 拒；jump 1.0 收/1.1 拒）、慢漂不误杀（4.9 m/s 巡航 500 帧 + 位置同步
全收）、加速度门、**爆散签名时间线**（实测爬升复现：v 0.3→6.3 m/s，第 392 帧起 109 帧全拒，
冻结参考后续温和帧也被 jump 门拦）、重启窗、关闭直通（毒值原样通过=旧行为）、NaN、
单帧违规不锁死。

## 5. 双门禁（D2-3，待部署后）

- 门禁 1（失败复现）：flyaway 段 odom 注入——把 X1_232055 爆散段 imu_propagate 序列回放给
  门（gtest 级注入已含时间线用例；在线级=bag play 注入 Odom_Data_t::feed 路径可选）→ 降级不
  跟随。
- 门禁 2（标准回归+V8 韧性复测，锁窗 W-D2）：正常链悬停一轮（门在位）+ 杀 PX4→重启→
  04_takeoff 120s→3/3。
- 入库（D2-4）：README §3 登记 + 实机 yaml 不动声明（门参数默认值进 SITL yaml；实机启用
  留实机线）。
