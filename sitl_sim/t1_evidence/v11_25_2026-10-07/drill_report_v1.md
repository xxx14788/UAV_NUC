# 注入演练报告 v1（T1 v11.25 阶段 4a；判据=drill_prereg_v1 冻结；2026-10-07 16:0x）

> 双必达之二达成：五案全果（含 2 案 FAIL=必修项登记，如实）。
> 栈=f622bae2/886b1e90（IQG 门=关，演练测安全链非质量门）；harness=vins_smoke+--stoploss（止损 v1.0）。

## 逐案结果

| 案 | 判定 | 安全态实达 | 证据（run 目录） | 要点 |
|---|---|---|---|---|
| **D0 对照**（意外自然轮） | PASS | 正常收卷 | run_DRILLD1_N8P_144638 | 健康 N8P+止损挂载零干预：PASS（jump 0.112/到位 0.097/disarm=1）——批注：非预注册案，作为对照样本 |
| **D1 杀 VINS（pursuit 期）** | **FAIL（不安全）** | **无安全态响应** | run_DRILLD1_N8P_150019 | kill@pursuit→系统零响应：机体在冻结 odom 上**盲飞**过冲至 (2.4,10.5,z=2.43) 冻结悬停至袋尾；**disarm=0**（GATEHIT chain disarm:0）；poscmd 100Hz 持续；truth 末 20s 位移 0=悬停非受控。**必修项①** |
| D1-boot 变体（意外） | 安全中止（init 门兜底） | 未起飞 | run_DRILLD1_N8P_145206 | boot 期杀 VINS→harness 300s init 门 FATAL 收场，零飞行=安全；批注价值=boot 期死亡有兜底、飞行期没有 |
| **D2 毒 odom 跳变 +5m** | **PASS** | **S1（受控降落经止损）** | run_DRILLD2_N8P_150926 | 注入 t=107.744→stoploss 即时触发（jump_m=5.0 逐位=注入量）→受控中止→**17s 内 disarm=1**→FAIL 收卷；**止损件在线首验销账**（--stoploss 零样本账闭合） |
| **D3 毒 odom 断流（STOP 30s→CONT）** | **PASS** | S3（恢复跳捕获→kill 链） | run_DRILLD3_N8P_151736 | 注入窗 truth \|v\|峰=1.09<1.5 无失控；CONT 后 VINS 重定位跳>1m→止损捕获→中止链降级② kill（**DEGRADED/disarm=0** 注记：kill≠disarm=必修项②面）；批注=冻结窗本身静默（无流死检测器，恢复跳代捕） |
| **D4 planner 饿死（STOP 60s→CONT）** | **PASS** | 正常收卷（零死签名） | run_DRILLD4_N8P_153612 | 冻结 60s 期间 traj_server 未续发旧终点（F1 修复实证），轮**绿收**（到位+disarm 正常）；首跑 D4a=轮在注入前 pursuit-start 自然跳→止损有机捕获（DEGRADED，链第三次实战实证）——活性校验正确 ABORT 未注入 |
| **D5 连续错误流（慢漂 0.15m/s×30s）** | **FAIL（告警链未按判据）** | 无 | run_DRILLD5_N8P_155544 | **必修项③**：①监控 V/D 双阈在起飞/巡航段**假阳**（t=39.4 告警=正常爬升+初始巡航位移 3m/10s 撞 D 阈——监控缺任务相位感知）②**一次性告警语义**致注入窗（t=107.8+）聋（首告警后 alarmed=True 停检）③慢漂注入被**双发布器交错形态**转译为交替跳变→止损触发中止（RESULT=STOPLOSS-ABORT）——慢漂面无独立检测响应，与安全盘点件"不可自动检测型"预判一致，演练提供活体证据 |

## 必修项登记（实机前阻塞清单，@4b 消费）

1. **飞行期 VINS 死亡无自动安全响应**（D1）：盲飞+disarm=0——H-A 阻塞项活体实证；修复面=4b 三候选择一（D1 证据指向"终极兜底 disarm 定时器"或"px4ctrl MANUAL 态 disarm 分支"）。
2. **kill≠disarm 缺口**（D3/D4a recovery=DEGRADED 共同面）：降级② kill 后 armed 态保持——kill 链后补 disarm 确认/重试。
3. **慢漂监控 v0 三缺陷**（D5）：相位感知（起飞/巡航段禁 V/D 阈或改 cmd-odom 残差面）+重复告警语义+注入器单发布器接管语义（流替换非竞争）；实机监控规程 v1 前不得依赖 v0 自动面。

## 判据零变动自查

通过：五案判定全部按 drill_prereg_v1 冻结表执行；FAIL 两案如实判 FAIL 未放宽；止损/监控工具行为差异=发现非判据改动。

## 谱系

- 预注册=drill_prereg_v1（f7189b98）；工具=t1_inject_odom/t1_odom_monitor/t1_drill_run（033ba71 批+本窗热修：marker 锚定/活性校验/D5 监控目录）；
- 编排器坑四条在册（EV mtime 竞态→marker 锚定；pursuit 前提活性校验；D5 预建目录幻影→/tmp+回拷；两意外轮均转为正样本）。
