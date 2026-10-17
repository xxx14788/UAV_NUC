# C3-v88 §一.2 确定性断链干测判决书（先于任何烧飞轮；红 42）

> 修复=px4ctrl land_guard（B1 管钳制+B3 近地降速+A 漂移看门→HAFIX 盲降交接；B2 落码默认 off）。
> 判据=fix_design_prereg_v88.md §6。本判决=合成签名 gtest+P3 真实流重放双证据。

## 一、合成签名 gtest（test_land_drift_guard，10/10 PASS）

| 型 | 断链主张 | 结果 |
|---|---|---|
| 型1 z 负漂序列（P3 数值重演：锚 0.96/漂率 0.49/尖峰 8.7） | perceived 全程 ∈[−0.10, 1.26]；壁面接触>1000 帧；重锚目标有界；告警锁存 | PASS（S2 断） |
| 型2 中断闪断（1 帧断+恢复） | episode 存活跨断、恢复帧钳制、锚不重置 | PASS（S3 不复现） |
| 型3 目标游走（6 次 bounce 重锚棘轮） | 每次目标 ∈管、游走总幅 ≤1.40 | PASS（S4 断） |
| 透明性×3 | 健康降落/健康悬停 60s/episode 外：零钳制零告警 | PASS |
| 旧版缺省 | enabled=false 逐位恒等（实机 yaml 无 key=off） | PASS |
| B2/B3/A 单测 | 冻结语义/目标连续性/HAFIX 交接+单变量反证 | PASS |

既有 px4ctrl gtest 94/94 零回归（fsm_decision 51/odom_sanity 9+v2 11/cmdresp 12/attitude 11）。

## 二、P3 真实流重放（replay_land_guard；同一 land_drift_guard.h 头文件）

**输入=P3 袋 /vins_estimator/imu_propagate 全流 42271 帧**（真签名非合成）；模型=episode 锚+>0.5s 断流
闪断+重锚追漂移+HAFIX 盲降重断言+B3 连续目标+落地检测 C1/C2。

| 节点 | 原录（P3 失控行为） | 修复重放 | 改变 |
|---|---|---|---|
| 1 到位 70.65 cmd 停→AUTO_HOVER | — | 透明（episode 未开） | 否（设计内） |
| 2 79.73 AUTO_LAND | 直落 0.5 | 锚 z=0.71；z<0.6 后降速 0.35 | **是**（B3） |
| 3 83.76 MANUAL 闪断 | MANUAL 1s 弹跳 | 闪断被 HAFIX 重断言压制；episode 存活 | **是** |
| 4 86.78 AUTO_HOVER 追漂移目标 | 重锚=漂移 odom | 重锚=钳后感知（钉 −0.10） | **是** |
| 5 87.80 再 AUTO_LAND 追降 | 追漂移再降 | alarm(FSM 84.36)→盲降接管 | **是** |
| 6 183.60 MANUAL（VINS 死流） | 有 | 未达（FSM 87.37 landed+disarm 终局） | **是** |
| 7 飞逃 z_max=95.06m | 物理爆域 | perceived min=−0.10；max|des−perc|=1.50m ≤1.60 界 | **是** |

**6/7 节点行为改变**（节点 1=失效前正常段，透明性按设计不变）→ **回归面② P3 FSM ≥6/7 门 PASS**。
失败链 checkpoints：clamp=FSM 80.82（漂移起点后 0.7s）/alarm=FSM 84.36/landed+disarm=FSM 87.37。

## 三、梯子裁定（红 42 单变量纪律）

- B1 复验门：**过**（S2→S4/S5 放大链断=有界化）；残余有界追踪未终止→按预注册续梯
- B2 复验门：单测过但水平棘轮已被 B1 xy 管覆盖（P3 实测 max|xy|=7.7 vs z=49.4=主失效轴）→ **live off**
- B3 复验门：**过**（S1 触发面缓解=近地缓降+目标连续性单测）
- A 复验门：**过**（终止语义：alarm→HAFIX 盲降梯=D1 演练实证机制复用，零新终止代码）
- **live 集=B1+B3+A**（各档均先独立单测后组合=非未验叠加；组合验证=P3 重放+回归四面+pilot）

## 四、勘误与注记（诚实义务）

1. **时基勘误**：imu_propagate 流 t0=bag+25.34s（VINS 晚起）——FSM 事件钟与 bag 戳差此值；
   首版重放误用 FSM 钟于 bag 戳致 episode 早开 25s（误差虚高 12.43m）；修正 T_LAND=105.07 后
   误差 1.50m=管径 1.36+告警窗内下降目标瞬态（≤0.5 m/s×告警延迟，alarm 重锚后归零）。
2. err 界 1.60 的推导：管径 1.36（zhi−zlo）+告警延迟内下降目标运行 0.5×~0.5s——瞬态有界且终止。
3. 壁面速度清零在 gtest 层=zc/xyc 旗（input.cpp 消费端零速语义在代码审查面）。
4. 指纹：px4ctrl 二进制 59d84e4e→**e5e8a539**（十件套换代第 10 件=land_guard yaml 段+修复 commit）。

## 五、放行声明

干测断链双证据（合成 10/10+真实流 6/7）+既有 94/94 零回归 → **准进回归四面**（禁带病禁跳步遵守）。
回归四面数字门通过前不烧 pilot（§一.3 原文）。
