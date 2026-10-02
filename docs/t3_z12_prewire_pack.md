# Z1.2 v2 接线预备包（T3 v8.3 单元 4 等待期预写；2026-10-02）

> 前置②未满足（E-4 的 0.5 接线结果挂 C01+T1-E1 裁决，t3_z1_failsafe_design.md:35 分叉）。
> 本包=解锁即翻转的全部预写件：①STAMP-AGE 在线评估脚本 ②E5 悬停 A/B 判据预注册
> ③接线操作序列。**v1 零变动**（enabled_v2=false 期间 v1 逐位不变，T1 P1-2 已验）。

## 1. STAMP-AGE 在线评估脚本（已入库）

`analysis/t3_z12_stampage_eval.py`——接线后在线轮 bag 上出截龄分布+0.2s 门模拟+判读带
（HEALTHY/SUSPECT/TRIGGER-FACE）+stamp 回退计数。口径：age 代理=bag rcv time − header.stamp
（C07 勘误④一阶口径，单机 SITL 同源）；接线后与 px4ctrl 进程内 rejected_stamp 对拍定真触发面。

**接线前可先跑历史袋出基线分布**（无风险，只读）——解锁后首轮在线数据与之对拍。

**【基线已出 2026-10-02 14:2x（t3_results/stampage_*.json）】**

| 袋 | 类型 | n | age p50/p95/max (s) | >0.2s 门帧 | stamp 回退 | 判读带 |
|---|---|---|---|---|---|---|
| U7OL2_202043 | 健康悬停 | 39195 | 0.008/0.036/0.056 | **0** (0%) | 0 | HEALTHY |
| WC2OBS1_030927 | 爆散轮（vins 域异常但流时戳健康） | 24543 | 0.012/0.036/0.052 | **0** (0%) | 0 | HEALTHY |
| U3PO_211438 | 健康导航（223Hz 全程 359s） | 74750 | 0.012/0.036/0.056 | **0** (0%) | 0 | HEALTHY |
| X1final_043355 | 毒轮（stamp-back 族） | 20907 | 12.864/158.204/158.268 | **15706 (75.1%)** | 1814 | TRIGGER-FACE |

**读数**：健康链路截龄 max=56ms → 0.2s 门裕度 3.6×（健康带确认）；毒面 75.1% 帧超门+中位
12.9s 陈旧+1814 回退 → STAMP 双层在 043355 型上将大面拦截。注意 WC2OBS1 型爆散轮流时戳
本身健康（值域爆、时戳不爆）——**STAMP-AGE 不是爆散轮防线**（那是 ACC/JUMP/R/VEL 层域），
此对照正好划清层间分工。接线后在线首轮对拍=健康带（p95<0.06s+零超门）。

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
