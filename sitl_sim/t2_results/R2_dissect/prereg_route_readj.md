# prereg_route_readj_v1 — route 复裁（v8.3 单元 3；depth-gate 臂；判据先于飞；2026-10-03 13:3x）

## 变更面

- config：sim_stereo_t2gates/sim_stereo_imu_config.yaml 增 `t2_depth_gate: 1`（min/max 用默认 0.15/30.0）——**零二进制变更**，栈=lib 1d7d2302+node 47d4308e 不变（banner depth_gate=1 自证运行时生效）。
- 依据：单元 2 画像（ir_st 13-28/帧 stereo 负深伪注入=再造毒载体；IMU 循环期全净）。

## 轮次（预算 5 轮）

route gates×4（复裁主面）+hover gates×1（回归面：深度门饥饿/健康检查）。

## 判据（预注册）

- **主判 R1（route VINS 域健康）**：≥2/4 轮无假盆地成熟（odom 尾 60s |P| p50<10m 且全程 |P|max<50m）——对照基线=修复前 route 4/4 中 3 轮成熟（032809/033941/035800 型）+本日 VR1/VR2 两轮成熟。
- **主判 R2（风暴断裂）**：若爆发生，reboot 后 Bas 爬坡死亡不再复发（任一轮内 reboot 总数 ≤2；对照 VR2=15）。
- **辅判 R3（到位）**：场景分门口径如实记录（不设硬门——到位受控失败分层属 X 线判据域）。
- **回归判 H1（hover）**：零 [T2fail]+odom 连续+track 无饥饿坍塌（[T2gate] tri 不归零、拒绝率<50%）。
- **受控失败口径**=四裁定②（任意门拦截+恢复）；三段式=四裁定①。
- ENV：df<20G 停；双 md5 每轮登记（应恒为 1d7d2302/47d4308e=二进制不变自证）。

## 分支

- R1 达成（≥2/4 健康）→ depth-gate 定稿入 gates 配置+U3pp route 复裁重判（是否达 2/4 计入达标门）+U4 通告评估 @T3。
- R1 未达 → 如实负+悬置第二嫌疑（真实狂飙动力学贡献占比）进入画像第二刀。
- H1 失败（饥饿/回归）→ depth gate 回退关断，单独分析拒绝率画像。
