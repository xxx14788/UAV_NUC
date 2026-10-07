# 注入演练预注册 v1（T1 v11.25 阶段 4a；2026-10-07 14:3x 冻结；判据先冻结防跳步）

> 依据=任务书 v11.25 阶段 4a+安全盘点件 1a475cf4 §6c 草案→本 v1 细化冻结。
> 通过标准（任务书原文）：每案系统反应符合预注册安全态分层=PASS；任一案≠安全态=登记必修项+修复+复验。
> 演练域=SITL（vins_smoke 现行 harness；栈=f622bae2/c22e4071，IQG 门=关（批臂 config 不带 IQG 键——演练测安全链非质量门））。
> 注入时点=起飞确认后 pursuit 相位（t_takeoff+~30s，goal 已投递巡航段）。

## 安全态分层定义（预注册）

- **S1 受控降落**：auto_disarm=1 ∧ 着陆 z_end<0.15m ∧ RESULT 落盘（最优）。
- **S2 悬停+告警**：机体存活悬停（truth |v|<0.3m/s 持续 ≥5s）∧ 告警文件/日志在案（次优；等待人工/超时链）。
- **S3 缓降/电机停**：kill 链触发+disarm=1（兜底；SITL 语义=电机停）。
- **不安全**：失控飞行（truth 位置发散 >5m 或持续 |v|>1m/s 未收敛）/坠机外形态/无任何响应静默继续原任务。

## 五案预注册（注入方法×期望安全态×判据）

| 案 | 注入 | 方法 | 期望安全态 | PASS 判据（冻结） |
|---|---|---|---|---|
| D1 | 杀 VINS 进程 | `kill -9 <vins_node>`（pursuit 相位） | **S1**（px4ctrl odom 超时→LAND 链）或 **S2**（cmd 超时悬停） | disarm=1 ∧ (z_end<0.15 ∨ 悬停存活≥5s)；不安全=继续原任务飞行 |
| D2 | 毒 odom 跳变 | 竞争发布器 /vins_estimator/odometry 单帧 +5m（t1_inject_odom.py --jump 5） | **S1 经止损件**（stoploss→controlled-abort→FAIL 收卷） | stoploss_<tag>.json 在 ∧ RESULT=FAIL(STOPLOSS-ABORT) ∧ disarm=1；不安全=无响应继续 |
| D3 | 毒 odom 断流 | `kill -STOP <vins_node>`（发布冻结≥30s 后 CONT） | **S2**（流断→悬停/告警；恢复后继续或安全收尾均计过） | 注入窗内 truth 无失控（|v| 峰 <1.5m/s）∧ 无坠机形态；恢复或 LAND 收尾 |
| D4 | planner 饿死 | `kill -STOP <ego_planner_node>`（60s 后 CONT 或 kill） | **S2/S1**（traj_server 不续发旧终点[F1 已修]+starve 检测/poscmd 稳定性） | poscmd traj_id 冻结>60s 死签名**不出现**（traj_server 收敛）或 STARVE-DETECT 恢复；不安全=机体追旧轨迹飞出 goal 带 |
| D5 | 连续错误流（慢漂） | 竞争发布器接管发布 0.15m/s 慢漂 odom 30s（--drift 0.15） | **告警链触发**（t1_odom_monitor 双阈值告警）+S2（人眼规程登记；SITL 不期待自动中止） | monitor 告警文件在（drift 告警 ≤20s 内触发）∧ 注记=实机处置依赖监控+人工（不可自动检测型在册） |

## 工具契约（随案落码）

- `t1_inject_odom.py`：竞争发布器；`--jump X`（单帧位姿 +X m z 向）/`--drift V`（以 V m/s 持续位移接管发布）/`--hold`（复发布末帧=断流等效 alt 面）；发布前先订阅原流承接位姿与 twist；留痕=inject_<mode>.json。
- `t1_odom_monitor.py`：监控告警器；双阈值=|v|>0.5m/s 持续 ≥3s（速度阈值）∧ 位置位移率 >0.3m/s 滑窗 10s（漂移阈值）任一触发→alarm 文件+STOPLOSS 风格日志行；实机监控规程载体。
- 注入时序驱动=演练编排脚本（t1_drill_run.sh：<case> <run_dir>：起 vins_smoke 后台→等 pursuit→注入→收尾取证）。

## 判据零变动自查

本演练不改任何现行判读门值；新增=演练专属判据（上表）与工具，零触判读链。

## 结果登记格式（逐案）

`D<n> | PASS/FAIL/不安全 | 安全态实达=S? | 证据=（RESULT/stoploss/alarm/poscmd traj_id/truth 轨迹摘要）| 必修项（FAIL 时）`
