# M1 门检查单（首飞 go/no-go）— T1 v11.28 单元 4（2026-10-08 03:35 中程更新）

> 规则：任一行未 PASS=禁首飞呈报；每夜 STATUS 末尾追加 M1 状态行（N/11+缺项）。
> 同步：本地 v11_28_local/M1_gate/ ↔ 3090 t1_evidence/v11_28_2026-10-07/local_staging/M1_gate/

| # | M1 门材料 | 产出来源 | 状态（03:35） | 说明 |
|---|---|---|---|---|
| 1 | 台架环境+全栈基准报告（1a/1b） | T1 单元 1 | **PASS（10-08 16:20）** | 1a✓；1b-p0✓；**1b-p1=全栈基准 p1✓（时延 p50=3.0ms/p95=5.0/p99=5.4ms N=60009+负载 CPU≤27%/51°C 门 PASS；3090 SITL 对照 τ_pipe~15ms 优域）**——证据 v11_31/unit2_realmachine/2a2b_2c_remote_status.md；附注记：CSV 两列探测假阴+odom_alive 启动窗 VINS calib 崩（已修，T2 同款坑） |
| 2 | 实机 config v0+溯源表+标定核对 | T1 1c | **PASS 带注记 A/B（10-08 1a 审签 95f0211e）** | 上游逐键全一致+factory 387.508 实装+增强键 cauchy4 平移；**注记 A=Allan 补审条款（采集 15:29-17:49，差>3x 呈报）**；注记 B=IMU 流率 50Hz 登记；审签回执 v11_31/unit1_greenrate/1a_config_v0_review_receipt.md |
| 3 | 硬件检查矩阵 11 行三态 | T1 1d/1e+物理窗 | **相机面 3/3 数据齐**（行 1 流频✓/行 3 emitter[off 3.3 倍优+白天复测注记]/行 4 曝光锁定✓） | 行 2 深度面待台架贯通（随 1f）；行 5-9 飞控五面**阻 FC**；行 10/11 物理窗 |
| 4 | 失效注入演练五案+实机地面版 | T1 单元 3 | D1-D4 过；**D5=监控 v1 L1 六用例 6/6 PASS**（L2 链路级待飞行窗） | 实机地面版=阶段 1 后下周期（注记不变） |
| 5 | HAFIX 多场景验证+实机化复标（3e） | T1 3d/3e | **半成（10-08 3e✓）** | **3e 复标定案=三参数全保持 SITL 值（59f054e7：实机 p99 5.4ms 优于 SITL 15ms 地板，零放大）**；3d(2d) 多场景=今晚飞行窗（预热批后） |
| 6 | 基线机器=旧机（自动定案） | T1 单元 1 | **生效** | 筛选冻结中 |
| 7 | OS 级实时调优 | T1 1h | **PASS 带注记（10-08）** | 调优已应用✓；**负载对照随 1b-p1 落地✓（全栈 20min CPU≤27% 51°C 无降频证据）**；持久化模板待用户审（注记保留） |
| 8 | failsafe 缺口+P3 落码 | T1 3b/3c | **半成（10-08）** | failsafe 参数 dump ✓（**NAV_RCL_ACT=2(RTH)=纯视觉机 P1 隐患已呈报**+COM_ARM_WO_GPS=1✓）；**P3 源码全落（生产 3+消费 5+gtest 5 测，build 挂三臂后=栈冻结冲突）**——v11_31/unit2_realmachine/2f_p3_luoma_status.md |
| 9 | 起飞前自检脚本 v1 | T1 1c 后 | v0 在册/v1 待 | 1c 审签后适配 |
| 10 | 实机处置手册 | T1 1g | **v0 已落**（含上游五 case/VINS 飘五查/命令参照） | 实机参数适配随 3e→v1 |
| 11 | 止损件实机语义复核 | T1 3e 同窗 | **PASS（10-08）** | 59f054e7 §3：实机止损=监控 v1（J 阈）+HAFIX 梯双防线；VINS 自报口径 SITL/实机同构✓；真值轨实机不可用注记在案 |

**计数：1/11 全 PASS（行 6 定案生效）+3 行半成（1/2/7）+1 行核心推进（4：L1 达成）。**

### 硬阻塞清单（用户物理介入项）
1. **FC 断链**（10-07 22:37 USB disconnect 未复现，与 AP 离线同窗=共同断电嫌疑）：阻 1d 远程项/1b-p1/1f/Allan/1e 飞控五面 → 请物理检查飞控供电+USB 线
2. 物理配合窗五项（清单 v1 已呈报件）

### AP 离线事件影响最终账
开工前 4h+ 离线（22:30-02:11），期间本地产出 24 件全部同步 3090（MANIFEST 零失败）。


### v11.31 更新（2026-10-08 16:4x，T1 单线日班）
- **计数：5/11 全 PASS（行 1/2/7/11+行 6 旧）+3 半成（3/5/8）**；行 2 注记 A（Allan 补审）与行 3 深度面（零帧阻塞）为呈报挂起项
- 行 3 推进：相机 3/3 数据齐+**飞控参数面 5/9 落袋**（固件版本号待 AUTOPILOT_VERSION 通道/mag 校准物理窗/GPS 无硬件注记/EV_CTRL=0 同构/SD_LOG_MODE=0）
- 硬阻塞清单更新：FC 断链**已解除**（10-08 15:06 用户重连+探测触发续跑链全走）；剩余物理窗五项+磁力计重校（P1）

### v11.34 更新（2026-10-09 05:0x，T1 实机主线+安全链收官夜）
- **计数：9/11 全 PASS（行 1/2/4/6/7/8/9/10/11）+2 半成（行 3 深度面阻/行 5 多场景 FAIL 侧）**
- 行 4 → **PASS**：D5 L2 链路级 PASS（night_chain 实弹: 注入→TIMEOUT NEW→PERSIST×4→alarm.json 落盘全通；三注记=D 检测器压线误报面/phase 横跳/收尾刷屏——监控 v1.2 候选）；实机地面版（2e）仍挂物理窗顺带件（注记）
- 行 5 → **FAIL 侧半成（多场景证伪）**：2d HAFIX 批统一重判=3d FINAL FAIL（4 场景全 FAIL；13 有效/7 无效；KILL 行 8 轮生效率 37.5%）；根因=KILL fallback 实现 command400 param1 缺省=reboot 非 kill+log 打在调用前+reboot 残留毒化下轮（6 FATAL 中 5 例紧跟 KILL 轮）。修复面 P-HAFIX-1/2/3 在册（v11_34/hafix_multiscene_verdict_v1134.md）；单场景复验（v11.28）属生效路径运气侧，代表性被证伪
- 行 8 → **PASS**：P3 build 修复三处（CMakeLists src 跃点+test tid+gtest main；PX4CtrlFSM.h stray private:）后 catkin 6/6 绿+gtest 5/5+消费侧验证（生产 reboot_notify latched ↔ 消费订阅+HAFIX watch 交互契约一致）
- 行 9 → **PASS**：自检 v1（t1_preflight_check_v1.py）实机参数适配+实弹全项工作（fetch→get bug 修+gyro 带 0.005 全过+4S min-v 14.0+第 6 项 |Bas|/cost 病理带）；实弹捕获 battery 0.0 真实拒飞+|Bas|med 1.31 病理 FAIL（与 2d 采集互证）
- 行 7 → **注记闭合 PASS**：持久化默认案落地（rc.local 三项 performance/swappiness10/usb-on+rc-local active=断电重放；任务书通知非请示条款）
- 行 10 → **PASS**：处置手册实机参数适配毕（3e 复标+自检 v1 联动）
- 行 1 → 注记追加勘误：p1 全栈基准实为四件栈（single_run_in_exp.launch 不存在→planner 件从未起，v11.31 同款；负载面欠估计，时延结论方向不变）
- 行 3 → 维持半成：深度面阻（复苏栈 rs 漏 depth_width 显式 640→depth 流 848 超带宽零帧；修复排静置窗后串行）；物理窗行项不变
- 附：E5P CAL 考古池件消费=实机 CAL 对照实测 addendum v1.1（实机 gyro 三轴全在带内=现役健康实证；ACC Y/Z 偏大 P1 核对项）
