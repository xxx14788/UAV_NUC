# Z1.2 gtest 常规化准备——catkin 窗协调方案（v7.4 等待池④；2026-10-01 预备，执行窗=X 线后）

> 状态：方案就绪未执行。执行前置=Z1.2 接线设计定稿（T1 对 Z1.4 移交响应+E-4 的
> 0.5 接线结果出来后 EV_CTRL 实验给答案）。本方案只解决"怎么进常规构建"，
> 接线本体（px4ctrl 改动走异议窗+配对提交+v1 零变动）见任务书 Z1.2 节。

## 1. 现状盘点（2026-10-01 实读）

- `src/px4ctrl/src/odom_sanity_v2.h`：在库（v2 门双轨全绿凭据=T3 v7.2 等待期 Z1 系列，
  台账 54dae6d→a68b244 链）。
- `src/px4ctrl/test/test_odom_sanity_v2.cpp`：**12 个 TEST 在库但未接 CMakeLists**
  ——当前 CMakeLists 只注册 v1（`test_odom_sanity`，T1-D2 件）+attitude/fsm 共 3 个。
- 即：v2 门测试目前**不可由常规构建触达**（手工 g++ 跑过=双轨绿凭据，非 catkin 常规件）。

## 2. 常规化三步（build 窗内 ~10min）

1. CMakeLists.txt test 段追加（v1 块旁，同构）：
   ```cmake
   catkin_add_gtest(test_odom_sanity_v2
     test/test_odom_sanity_v2.cpp)
   target_link_libraries(test_odom_sanity_v2 ${catkin_LIBRARIES})
   ```
2. `catkin_make`（构建核验三件套：退出码/产物存在/警告增量）。
3. 一键全量回归：`catkin_make run_tests_px4ctrl && catkin_test_results`——
   期望 4 个 gtest 二进制全绿（attitude/odom_sanity v1/v2/fsm_decision；fsm=T1-F3 镜像件）。
   注意坑：run_tests 吞 gtest 退出码（夜战工具链坑 v61）——以 `catkin_test_results`
   的汇总退出码为准，不以 run_tests 命令本身为准。

## 3. catkin 窗协调协议（build 互斥纪律）

- **合并窗**：与 T1-F3 通道 B（Px4ctrlDebug 加 odom_delay/odom_staleness 双戳字段）
  **同一个 build 窗**执行（T1 v8.0 P0-D.2 明示合并意图；一次 catkin_make 双线改动
  各自配对提交，互不等待）。
- 起窗流程：STATUS 预告（写明范围=px4ctrl 包+预计时长）→ **15min 异议窗** →
  起窗前 `pgrep -f 'catkin_make|cmake|vins_node|rosbag play'` 全场净 → 执行。
- 避让：T2 U3 在线飞行矩阵窗/T3 X 线锁窗绝对优先（权序 T3-X4 > T2 U3 > T1 > T4）；
  build 与在线轮/带图回放互斥。
- 窗内失败处理：编译错→当场修或回滚（git checkout 单文件级，禁全库 checkout——
  09-30 03:5x T1 checkout 清掉 T2 未提交补丁事故教训）；窗后 STATUS 回执。

## 4. 与 Z1.2 接线本体的顺序关系

- gtest 常规化（本方案）**可先行**：纯测试接线，零运行时行为变化。
- Z1.2 生产接线（odom_sanity_v2 进 px4ctrl 主循环，enabled_v2 默认 false）走异议窗
  +配对提交三件；接线后 STAMP-AGE 层在线评估（Px4ctrlDebug 双戳字段=T1 通道 B 同窗
  数据）+E5 悬停 A/B（<0.01m）终验——均在 X 线后与 T1 合并窗落地。
- v1 零变动红线：v2 默认 false 下 v1 门行为逐位不变（回归以 test_odom_sanity v1
  全绿+X 线轮四指标不劣化为守门）。

## 5. 验收单

- [ ] CMakeLists 追加后 catkin_make 三件套绿
- [ ] run_tests_px4ctrl 4 gtest 全绿（catkin_test_results 退出码=0）
- [ ] 现场净（无残留 build 进程/锁归位）
- [ ] STATUS 回执双线（@T1 合并窗确认）
