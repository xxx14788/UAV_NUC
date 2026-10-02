# X1' 判读链干跑预演报告 v1.1（T3 任务书 v8.7 单元 1.5；2026-10-03 01:1x）

> 目的：X 线解锁前把 v1.1 判读链**机器侧端到端**跑通（round_result→wa_gate --online→
> 受控/未受控标注→RESULT 四指标→figs），接缝问题现在暴露不留给黄金窗。
> 样本=prereg v1.1 §6 案卷：U3pp A3/A1/A2（伪 run 目录=硬链接零拷贝）+U3PO（真实 run 目录）。
> 产物落点：~/sitl_sim/t3_results/x11_dryrun_v11/（四样本 RESULT.txt/wa_gate_online.json/
> forensics_v2.json/x11_dryrun.csv/figs/）。判读器改动=红线 24 全流程（备份
> .bak_cf_20261003/双 md5/逐字 cmp/三重验证，见 §4）。

## 1. 样本判定对账表（预期=prereg v1.1 §6 案卷列）

| 样本 | 任务书预期态 | 机器判定（wa_gate `controlled.state`） | 判定证据（自动产出） | 对账 |
|---|---|---|---|---|
| A3 hover/gates | 受控候选→按存档证据判 | **`triggered-no-recovery`** | 触发✓ `COSTGATE-FIRE n=1 first_t=47.024 streak=5 ratio=10.0`；恢复✗：L2a 复流 0<50（odom 末条 46.9 早于触发行 47.024，毒窗 [46.0,57.0] 后零消息）；L2b 无段可判 | ✓ 与 §6 机器预期一致（触发面成立+恢复面无证据=未受控） |
| A1 route/gates | 未受控负样本 | **`uncontrolled-fail`** | 无 cost 触发行+`FAILDET n=1`（legacy Bas 门 49.16s）；odom 流净（j0rev raw=0）但 +29s 死（cov=0.045） | ✓ |
| A2 route/base | 未受控负样本（log 丢失） | **`log-missing`** | simvins.log 缺失（T2 同名覆盖债）；袋侧帧跳 629/ATE 221m 兜底入证据 | ✓（缺失路径正确降级，不冒判） |
| U3PO | 零 fail 正样本 | **`clean`** | fires=0/faildet=0；全判值与 v1.0 判读器 10-02 01:35 产物逐位一致（§4.3） | ✓ 零漂移锚成立 |

四样本 RESULT 四指标（round_result v1.1）：全 FAIL（A3 到位 0.537m 过 0.75 场景门但
J0 跳 25.56m 恒门强制 FAIL=门间互锁正确；A1/A2 到位 8.12/4.17m FAIL；poscmd A3/A1=0Hz
悬停/未起飞臂无规划流=如实；A2 100Hz 但跟踪 p95 529.98m）。

## 2. 接缝问题清单（发现→处置）

- **S1（判读级·重大）A3"恢复健康"存档证据不支持**：T2 U3pp 终判 A3"reboot+恢复健康
  计达标"，但机器链+三重取证（bag odom/truth z/px4ctrl D2 拒帧）=触发真实、恢复无证据、
  物理摔机（truth z 起飞后冲 2.47m→~60s 落地；armed 终态 True）。"袋 err p95=0.094"实为
  触发前主导的全流统计。→处置：prereg v1.1 §2.6-f 已写死"触发-无恢复=未受控"；已 @T2
  STATUS 01:35 通告对账（其 U4 不通告结论不受影响；"hover 瞬态族 RESCUE 成立(单轮)"
  需改写为"触发成立+救援未成"）。**受控路径存档零正样本**——首次真实检验=X 线轮。
- **S2（判读级）A4 样本外发现**：truth z 全程 ≤0.19m=机体从未起飞，而 T2 判 PASS
  （bag 推断+log 被覆盖 [T2fail] 未知）。→处置：@T2 对账（同 01:35 通告）；不入选本干跑
  样本集（任务书未列），登记为 U3pp 判读族问题。
- **S3（数据面）failure 后日志静默**：A1/A3 的 vins log 均终止于 failure detection 行
  （再 init 不打印、[T2gate]/[T2diag] 不复现）。→处置：恢复判据落在袋侧 odom 流
  （L2a/L2b）；L2c 诊断复流降级为报告项（prereg §2.6-b/seam-1 已冻结）。
- **S4（数据面）紧凑袋 odom 结构性截断**：A1/A3/A4 odom 流均 ~30s 终止（A4 健康亦然）
  ——紧凑袋结构不可判"恢复"。→处置：X 线轮 flight.bag 全程录制+轮内任务持续（L2a 的
  [毒窗后 10s 窗 ≥50 条]在 X 线轮长下可满足）；prereg seam-2 已冻结。
- **S5（数据面）两流分工**：px4ctrl 吃 imu_propagate（A3 拒帧 851+、|p| 至 67m+ 在 prop
  流），恢复证据必须用求解器流 /vins_estimator/odometry（prop 无视觉自由积分）。
  →处置：识别器 L2a 固定读 odometry 流（实现如此）；prereg seam-3 已冻结。
- **S6（工具面）log 缺失降级路径**：A2 伪目录验证 log-missing 态正确降级（不冒判
  uncontrolled，证据走袋侧帧跳）；round_result 标注行在 log 缺失时静默缺失（设计使然，
  wa_gate 侧同判）。X 线轮每轮独立 run 目录无同名覆盖面。
- **S7（工具面）forensics 再生成**：伪目录无 forensics_v2.json 时自动生成（吃硬链接袋，
  无图像秒级完成）；j0rev 读数（A3 raw=5=毒窗五连跳/A1 raw=0/A2 raw=629）与手工探针
  逐个对上。figs 链尾 fig1/4/5 出图、fig2/3/6 为回填期占位（既有设计，非新缝）。

## 3. 判读链就绪结论

链**可用**：四样本全链零手工干预跑通；三种降级路径（触发无恢复/未拦截/无日志）均正确
落态；U3PO 零漂移证明 v1.0 判值不受 v1.1 分层影响（审计双读：`xline.pass`=v1.0 语义保留，
`xline.counting_pass`=v1.1 计数语义，`verdict` 增 PASS-CONTROLLED 态仅受控轮可达）。
**保留项**：L2a/L2b 阈值（50 条/10s/0.5m）与中毒窗 10s 为从严首版冻结，受控正样本零存档
→首个带触发的 X 线轮=首次实证，若阈值不适配=新版本号+理由（prereg §2.6-c），不追溯。

## 4. 工具改动与三重验证凭据（红线 24）

- 改动件：`analysis/t3_wa_gate.py`（md5 **0d434030**…受控失败层+计数语义+selftest 钉值，
  备份 .bak_cf_20261003=93c5d187）+`round_result.sh`（md5 **b21c8c6e**…COSTGATE/FAILDET
  纯标注行，备份 .bak_cf_20261003=ecc53a98）。上传两段式+三方 md5+cmp 逐字一致。
- 验证①：`--online --selftest` 三格全绿零漂移+新钉值命中（WAOL5R=clean/
  X1_232055=uncontrolled-fail，log 实测 0/0 与 0/1 支撑）。
- 验证②：`--selftest` 回放轴三格全绿（R_CAN cov 0.085/ATE 1.564/215× 等标定值逐位复现）。
- 验证③：U3PO 新旧判读 14 项逐位一致（verdict/four/j0/fj/reboot/coverage/pass_vins…），
  新增面仅 controlled 块。
- 判读链调用面（X 线轮沿用，零新参数）：round_result 由 vins_smoke.sh 内置自动跑；
  `python3 analysis/t3_wa_gate.py --online <run_dir>`；figs `t3_xline_report_figs.py --csv …`。

## 增补 S8（2026-10-03 01:5x；池件②合成单测逼出+已修）

- **S8（工具级·重大）到位解析正则陈旧**：RE_RES_ARRIVE 原为场景门前旧格式 `(<0.5)->`，
现行 round_result（e7120e0 场景门后）输出 `(<0.75,场景门 world=X)->`——新格式轮 four[0] 恒 None
→four_ok 恒 False→**xline_pass 对任何 X 线轮恒不可达（X 线全轮会被误判 FAIL）**。
干跑四样本 four=None 即此症状（初报未追到底，合成单测逼出后定罪）。
- **修复**（红线 24：.bak_regex_20261003 + f0905154→ac1df603）：正则改 `\(<[^)]*\)->` 双兼容。
- **验证**：在线 selftest 三格全绿（旧格式锚 WAOL5R 仍解析）；合成 SYN_CTRL **PASS-CONTROLLED 
端到端首通**（counting=True）/SYN_LATE 迟触发反例命中（l1b=False/onset=50.0）；干跑四样本
判定态零漂移（four 由 None→正确解析 0（到位 0/J0 强制），终判全 FAIL 不变）；U3PO 终判不变。
- 合成夹具=SYN_CTRL/SYN_LATE（x11_dryrun_v11/，真 rosbag+手写 log，仅测试用不入任何判读正源）。

### P-H 注记：U3pp 样本袋 inode 保全语义（2026-10-03 02:3x；登记于判读链手册页）

- 判读链 selftest/干跑的样本袋=A1/A2/A3/A5 四臂紧凑袋（~/sitl_sim/bags/t2v3_{route_035325,route_034144,hover_033842,ground_030355}.bag，域持方=T2）。
- **保全机制**：x11_dryrun_v11/ 伪 run 目录以硬链接持有 flight.bag——即使原袋被持方按 §8.1 序列删除，inode 经判读链目录仍存活，selftest 可复跑（硬链接语义：任一链接在=数据在）。
- **对称提醒**：判读链目录因此是"事实保全点"，清理 x11_dryrun_v11 前须确认样本袋原件仍在（或有意放弃 selftest 复现性）；SYN_CTRL/SYN_LATE 为合成件可随时再生（analysis/t3_synth_controlled_test.py）。
- @T2：若你域未来处置 U3pp 四臂紧凑袋，处置通告请 @T3（判读链样本面，删除前可先复制或知情放弃）。
