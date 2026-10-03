# T3 单元 3.5：auto_disarm 根因清查判读定案（2026-10-04 02:4x；判读面=T3，px4ctrl 行为域归因=@T1）

> 触发：U3′ obstacles 轮 auto_disarm✗ 在册无人追因（避障✓/poscmd✓ 唯此项败）；X4 5/5 判据含此项（prereg §2.6 计数语义下到位/J0/disarm 均不豁免）。本文件=判读面事实链+移交面；@T1 其册 2.7 已并行修复一个面（见 §3）。

## 1. 判据语义与标本

- `round_result.sh`：`disarm_ok = (not armed[-1])`——**袋末 /mavros/state armed 必须为 False**（=录制结束前完成真实解锁；非"指令已发"）。
- 标本：run_U3PO_211438（U3′ obstacles 轮）+ U3″ 舰队 10 臂（x4judge v1.1 D 列全量）。

## 2. U3PO（run_U3PO_211438）判读面定案

**证据链（全袋内实测）**：

| # | 事实 | 读数 |
|---|---|---|
| 1 | 机体从未离地 | truth z≡0.0 全程（峰值 0.0；30-90s 中位/最大/最小全 0.00） |
| 2 | armed 锁定 True | /mavros/state 迁移=[(25.3,False)→(29.5,True)]后再无变迁；mode=OFFBOARD 全程 |
| 3 | 起飞爬升期推力被压 | /mavros/setpoint_raw/attitude thrust：起飞前 0.711(悬停位)→30-60s **≈0.202-0.217**（28%）→末段回 0.71 |
| 4 | VINS 静态机上帧跳变 | RESULT 锚行"帧稳定性 pre-post=2.603m <-- VINS 帧中途跳变"；odom 末 z=-0.262（地面静态下 -0.26m 偏差） |
| 5 | 降落指令链完整未达 | /px4ctrl/takeoff_land cmd 变迁=[(1,28.9)→(2,246.5)]共 60 条（重发至 366.8）；round.log 21:18:54 降落指令(5 轮重掷)→21:21:13 **WARN 降落未确认 disarmed** |
| 6 | extended_state 不在袋 | /mavros/extended_state 零消息（录制缺口；px4ctrl 侧可达性袋外不可判，见 §4-iii） |

**机理链（判读面）**：起飞后 px4ctrl 控制器对静态机上跳变的 VINS odom 做反馈修正 → 推力压至 0.20 → 机体永不离地（z≡0）→ 359s "零 fail 存活"=静态地面机上的 VINS 流（T2/T4 判读面"正样本"语义仅指 VINS 域，机体域从未飞行）→ 到位 4.436m=静止机到目标距离 → 246.5 LAND 命令到达时 px4ctrl FSM 处于 MANUAL_CTRL → **原代码静默丢弃**（@T1 已定位并在其册 2.7 修复，源码注释明引本轮取证）→ 永不 AUTO_LAND → 永不 disarm → armed[-1]=True → `auto_disarm->0`。

**复合性定案**：本轮 auto_disarm✗ 是复合缺陷（未起飞 + MANUAL_CTRL 丢 LAND），**不是**"飞行后降落检测阈值"型——任务书预判的"降落检测阈值/超时小修"在真标本上不成立，真面=FSM 分支缺失。

## 3. 舰队面：系统性画像（x4judge v1.1 D 列）

| 场景族 | auto_disarm | 判读 |
|---|---|---|
| ground ×2 | ✓✓ | takeoff_land 流内闭环,disarm 正常 |
| hover ×4 | ✓✓✓✗（035509✗） | 035509=v1.3 controlled 轮（cost fire@46.5+恢复），其 disarm 败=第二标本（疑同 MANUAL_CTRL 面,重启轨迹致态漂移,袋外不可细判） |
| **route ×4** | **✗✗✗✗** | **系统性**：planner 停止→px4ctrl 回 MANUAL_CTRL→06_land LAND 被丢弃→armed 卡 True |
| R5/A1/A2/A3/U3PO | ✗×5 | 同族（T2 域轮+U3PO 复合型） |

**结论**：MANUAL_CTRL-丢-LAND 面对 **planner 轮（=X 线全部轮）系统性致命**——X4 5/5 若不带修复飞=**D 指标数学上必 0/5**。@T1 U2.7 修复（LAND in MANUAL_CTRL[armed]→AUTO_HOVER→下一拍 AUTO_LAND）恰好堵住此面，承重值=route 全族。

## 4. 移交面与残余（@T1 归因修复域）

- (i) **U2.7 修复验证缺口**：修复已在 src（2026-10-04 注释在册），但**无验证轮**——DoD（X4 首飞前该指标有正面证据或已修复验证）当前态=修复在库未验证。验证轮=任一带降落飞行轮（X1prime 即天然首验）；修复须在 X 线构建栈内（栈号双 md5 于 U4 通告时核对含 px4ctrl 重编）。
- (ii) **未起飞面（U3PO 独有）**：静态机上 VINS 帧跳变 2.6m→推力被压至 0.20→永不离地。FSM 停在何态袋外不可判（px4ctrl stdout 日志静默）；F2 起飞看门狗条件含"disarmed"而 armed=True → 看门狗不触发=永滞留。@T1 若需深挖：px4ctrl 侧 FSM 状态序列 + 推力压制的反馈源分解（odom z 假爬升 vs thrust 模型）。
- (iii) **extended_state 录制缺口**：AUTO_LAND→disarm 链要求 `/mavros/extended_state landed_state==ON_GROUND`；U3PO 袋零消息。X 线轮采集矩阵（runbook §2）建议增录该话题（判读面需要；px4ctrl 消费面与录制面独立，但判读"为什么没 disarm"时此话题是关键证据）。
- (iv) 035509 hover disarm 败=第二标本（重启轨迹后 FSM 态漂移疑同面），修复后复跑受控层素材可顺带验证。

## 5. 账面

- K-2.5 维持开（解锁=验证轮 ✓）；本判读面闭环。DECISION_LOG #3 登记。
- 判读器/判定器零改动（纯取证）；本轮据不改变任何在册判值（U3PO 原判 FAIL 不变,auto_disarm 列语义已由 x4judge v1.1 继承）。
