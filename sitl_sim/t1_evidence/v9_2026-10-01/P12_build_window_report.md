# P1-2 合并 build 窗收口（2026-10-01 20:06-20:25；v9.0 P1-2 锚点执行）

## 窗场
- 开窗依据：18:39 T1 提案 + 18:38 T3 无异议在册 + T2 静默无异议（U7OL1 未起，方案 C 维持在其续会账上）。
- 现场核：px4=0/gz=0/锁空/df 69G。范围按 v9.0 P1-2 四件套；v1 零变动保证照守。

## 四件套收口

| 件 | 状态 | 凭据 |
|---|---|---|
| ① Px4ctrlDebug 双字段编译（b2a94a2） | **完成** | devel/lib/px4ctrl/px4ctrl_node 重建 rc=0；rosmsg show 实证 float64 odom_delay_ms / float64 odom_staleness_ms 在册 |
| ② odom_sanity_v2 接线 | **已在码（晨班交付）+本窗验证 flag-off** | T3 26cddc5：v2 设计件 UNWIRED-in-behavior（enabled_v2=false=v1 位等价）；input.cpp:142 已走合并入口；r 门 0.08m 标定在册；**翻转 enabled_v2=true 的决策权=T3-Z1.2 持方，本窗不越权** |
| ③ gtest 常规化 | **完成（本窗实缺口即此）** | 根因=workspace 包级缓存 CATKIN_ENABLE_TESTING 未流入（测试目标从未被构建过）。修复后四目标注册+构建+直跑全绿：**controller_attitude 8/8、odom_sanity 9/9、fsm_decision 25/25、odom_sanity_v2 11/11（计 53/53）**。退出码纪律=直跑二进制（run_tests 吞码教训+ctest 包装缺 catkin python 模块两坑规避） |
| ④ F3 FSM 行为等价重构 | **挂起（本窗不接）** | 晨班 16ffbea 已交付：迁移表审计+镜像 gtest 25/25（fsm_decision.h 纯函数 API=State/Inputs/Outcome 145 行，line-aligned）；重构=FSM.cpp 实调镜像函数。不硬接理由：(a) flight-critical 改动需活飞 A/B 验证轮收尾；(b) 栈代未定（T2 方案 C 裁决悬置），半接线二进制会引入新栈代混杂；(c) 晨班排队决策自带该安全条款。**接线清单已备**：六 case 块逐块（STEP0/MANUAL/HOVER/CMD/TAKEOFF/LAND）Inputs 装填→decide_* 调用→Outcome 应用（offboard toggle/arm/disarm/reject）；验收=53 gtest+悬停 smoke A/B+git diff 逐行对照审计表 |

## 工具坑（新增）
- catkin_make 包级 CATKIN_ENABLE_TESTING 不随顶层缓存流动；gtest 二进制不入默认 all 目标——`make <test_name>` 直名构建；ctest 包装层需 catkin python 模块（非交互 env 缺）→ 一律直跑二进制核退出码。
- 裸 `cmake .` 在 build/<pkg> 目录=污染 CMakeCache（已清污重建，rc=0）。
- CMP0046 双警告=上游遗留（add_dependencies 指向 msg 目标），良性，勿当错误排查。

## τ_pipe 通道 B 解锁说明
- 双字段二进制已就绪：下一任一活飞轮自动携带 /debugPx4ctrl 双字段（publish 侧填充，idle else 分支=晨班 b2a94a2 设计）→ p50/p95 即可出 τ_pipe 终值与 A−B 互证（C10 判读前提两条在册）。
- 骑轮计划：T2 U7OL1 裁决定栈后的首个悬停轮（与 E-4 复排窗共用）。

## 窗后还场
- build 无锁占用（构建互斥仅与起栈/带图回放互斥）；px4ctrl_node 二进制 md5 与构建时间戳入账；field 零残留。
