# T1-F2 冲突①结案：用户裁决分支 B（2026-09-30 晚）

裁决：**分支 B 胜出**——`use_px4_position_ctrl: true` 系导入源误配/遗留（key 非上游物、
私改作者不可考），位置环归属=**机载 px4ctrl**（上游架构）。用户明示："F2 请你改 false"。

## 执行记录

- `src/px4ctrl/config/ctrl_param_fpv.yaml:10` true→**false**（含裁决注释与证据指针）；
  实机参数变更经用户明示批准（实飞前修正，红线豁免=用户授权）。
- SITL(sitl yaml false) 与实机(fpv yaml false) **同构恢复**——R6 位置控制架构差距项
  由"登记差距"转为"勘误闭合"（09-30 前的差距历史保留在 F2_conflict1_branch_verdict.md）。
- 代码默认值（PX4CtrlFSM.h:52 / px4ctrl_node.cpp:88 的 {true}）未动：三处 launch 均显式加载
  yaml，默认值无行为面；建议后续顺手改为 false 对齐裁决（登记不执行）。

## 对下游的更新

- F2 三账（延迟/裕度/增益）架构层第一句=**机载串级 PID（两域同构）**——C10 D2/P1 闭合。
- W2/EKF2-EV 失稳对实机架构的重要性**降级**（实机不吃 EKF2 位置输出，EV 融合即使启用也只
  影响 mavros local_position 链路（vins_to_mavros→vision_pose→EKF2→?），不在控制主环）。
- C09 sim2real 六维基线：位置控制架构维=同构（勘误后）。
- 记忆 t1-v7-night1-outcome 的"F2 待拍板"项关闭。
