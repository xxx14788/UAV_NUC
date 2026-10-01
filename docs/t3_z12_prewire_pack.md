# Z1.2 v2 接线预备包（T3 v8.3 单元 4 等待期预写；2026-10-02）

> 前置②未满足（E-4 的 0.5 接线结果挂 C01+T1-E1 裁决，t3_z1_failsafe_design.md:35 分叉）。
> 本包=解锁即翻转的全部预写件：①STAMP-AGE 在线评估脚本 ②E5 悬停 A/B 判据预注册
> ③接线操作序列。**v1 零变动**（enabled_v2=false 期间 v1 逐位不变，T1 P1-2 已验）。

## 1. STAMP-AGE 在线评估脚本（已入库）

`analysis/t3_z12_stampage_eval.py`——接线后在线轮 bag 上出截龄分布+0.2s 门模拟+判读带
（HEALTHY/SUSPECT/TRIGGER-FACE）+stamp 回退计数。口径：age 代理=bag rcv time − header.stamp
（C07 勘误④一阶口径，单机 SITL 同源）；接线后与 px4ctrl 进程内 rejected_stamp 对拍定真触发面。

**接线前可先跑历史袋出基线分布**（无风险，只读）——解锁后首轮在线数据与之对拍。

## 2. E5 悬停 A/B 判据预注册（冻结于接线前）

- **A 轮**：`enabled_v2=false`（v1 现役）；**B 轮**：`enabled_v2=true`（v2 六层全开）。
- 位形：E5 悬停（takeoff→悬停→land；无 goal；BUDGET 同值；同 world/栈/时段相邻发射）。
- **主判据：悬停保持差 <0.01m**——两轮 truth 悬停窗（起飞后 20s 至降落前 5s）位置
  相对各自悬停中点的 |Δ| p95 之差 <0.01m（v2 门零行为变化面验证）。
- 副判据（全同面）：四指标位全同；poscmd 频率差 <2Hz；Bas/Bgs 面板同带；
  v2 计数器（rejected_*）A 轮恒 0，B 轮健康轮应≈0（>0=登记逐帧证据）。
- 样本：n=1 对（判据=点对照非统计推断；CI 注记不适用，如实登记）。
- 失败处置：B 轮悬停保持劣化 ≥0.01m → v2 回滚 enabled_v2=false+逐层归因
  （先 STAMP-AGE 误伤对拍，再 R 层 0.08 域检查）+登记，不重试不改判据。

## 3. 接线操作序列（解锁即执行）

```
0. 前置核验：T1-E1/0.5 分叉定案通告（K-3）；锁（T3 窗）；df 门
1. sed -i 's/enabled_v2 = false/enabled_v2 = true/' src/px4ctrl/src/odom_sanity_v2.h
   （若接线形式改为 yaml 参数，以 t3_z1_failsafe_design.md 接线节最新版为准）
2. catkin build px4ctrl --no-deps && catkin run_tests px4ctrl --no-deps
   （gtest 14/14；退出码以结果文件为准——run_tests 吞码坑）
3. A 轮发射+判读 → B 轮发射+判读（相邻时段）
4. python3 analysis/t3_z12_stampage_eval.py <B轮bag>   # STAMP-AGE 健康度
5. A/B 判据判读（§2）→ 台账+STATUS @T1 @T2
```

## 4. 红线对齐
- 接线动作在异议窗条款下（VINS C++ 读改=px4ctrl 域同规）：STATUS 预告 15min 后动手。
- v2 分层阈值不随接线改动（stamp_age_max=0.2/r=0.08 等定案值）；接线=开关翻转+验证。
- 回放域不可标定 r 层（红线 7）；本包全在线域。
