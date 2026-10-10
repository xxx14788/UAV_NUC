# T3 任务书 v11.1 完成清账版（四线第十八周期收官；2026-10-10 13:5x）

> 原执行版=plans/2026-10-09_T3_planner_vision_acceptance_v11.1.md（md5 966225b8 三处一致部署）
> ——本件为收官账，v11.1 执行版弃读存史。结构沿 v10.9 清账制：A 完成账/B 剩余/C 卡点/D 资产/E 等待/F 坑账。

## A. 完成账（双必达 ✓✓ + 全单元）

- **双必达一（机制两件）**：①锚点校验哨兵 v1.0 落地（analysis/t3_anchor_sentinel.py：
  j0d/combo/threearm 三表签名识别+冻结锚点机械校验；selftest 7/7=正例三表全中+四负例
  按期爆[含 C-6 列交换事故复现爆锚]；实战首用例=combo 20261010 两代消费门 PASS×2）；
  ②STATUS 双文件机制落地（开工四线通告+收工同步首例：HOME→repo cp+commit，收官时
  双侧 1135 行 md5 ce8dcb56 一致）。
- **双必达二（判读支持全出表+X7）**：①实机静置袋 scen0 j0d 分解✓（口径声明四条先行；
  净轮 j0=3.5mm/coh=0.0007 噪声抖动型 vs sim HVNET1 coh≈1.0=**方向一致度三数量级谱系
  分离**；窗差注记 184.5s<T1 bias 发作 347s）；②r2 批四袋场景判读✓（流形态全净 njf=0/
  maxde≤0.052，与 R2_MANIFEST maxjump 逐袋互证 PASS）+旧批四袋三型病理梯度实锤
  （雪崩 495m/轻度 0.276+图像 46.9Hz/断流<3 帧）；产物=realmachine_j0d_odom_20261010.{csv,md}；
  ③T1 HAFIX 复验批=影子重判工具就绪验证✓（t3_2d_hafix_rejudge --pattern 跑通+判据口径
  正确实走[今晚 drill 轮 HAFIX 行全 0→FAIL]；批本体=T1 让位条款未发射=外因注记，W-T1 维持）；
  ④T2 ②a 臂批统计面✓（16 轮 8 对：**A(box) 12.5% vs B 75.0% = −62.5pp 判负**+方向 2/8
  [单绿对 5/5 全 B 优]+层① indom 100%×8 box 物理生效+层② dbadt 6/8 改善+层③ 条款间
  边界如实→归 T2 裁定；与 T2 box_arm_verdict_v1.0 交叉对照一致）+**超额=②b 到货即出表**
  （16 轮：A(tlock) 25.0% vs B 25.0% = 0.0pp 判负+**tlock_banner=0×8/8=锁未 ENGAGE 无效型**；
  **同夜同栈 B 基线 50pp 落差发现**[②a B 75% vs ②b B 25%,md5 d198718f 全 32 轮一致]=
  夜态分层注记必须性定量实锤）；⑤X7 收敛声明出稿✓（注记五双因子两支族框架+限定五条+
  定量附录 B 饼图[跳变族 37.4pp+慢淋 24.0pp=61.4pp 占失分 76.0% 下界]+附录 C δ 分布+
  补记③+T2 素材包到货增补[δc=配对窗宽 3-4ms+δ≥4ms 安全语义=右目弃用]；追加制验证=
  git diff 85 行纯尾部零删改）。
- **单元 4（在线域 δ 分布）**：17/17 袋 δ≡0.000（sim 含图像在线轮全集 13[全 FAIL]+实机
  r2 对照 4）——在线域压死瀑布带最深端=时戳病理覆盖在线域结构性闭合；D435 δ=0 健康对照
  →病理主因=渲染时戳域本身非 δ 数值；绿组袋无图像=样本域开口如实注记（必要条件面证据）。
- **单元 1e（滚动入表）**：combo 350→416 两代（412→416 同日再生）全程对冻结基 350
  drifted=0/missing=0；added=66（BX 20/TK 17/WU2 17 迟到面/DRILLD1 6/A1OBS 4/WU 2）；
  文档化例外外科恢复×1 重放（E12O json 覆写案，v10.9 纪律同源，工具化=t3_surgical_recovery_
  e12o.py）；j0d 286→286 零漂移（新轮无 j0_decomp 产物=客观注记）；台账=expansion_20261010.md。
- **单元 5（尾件池）**：B2 前基线转录✓（m3_prebaseline_v1.csv 十八轮，源 md5 988af441→
  转录 ca4d4bdd，four_green 6/18，脏行 9 剔除注记——②a/②b 消费已兑现）；bc CSV alive
  伪影回执消费=PASS 销号✓（11 行 0→1 逐位吻合+备份在盘+批尾 join 步未来同口径）；
  goal_adopted 归因面注记✓（协议层 W4-ADOPTED 7/7 修复闭环 vs 激励层 NOT-EFFECTIVE
  两层分离——@T2 约束设计消费件）；B6 provenance 抽验✓（触发条款=本次矩阵消费；新旧
  分层 5+5 全 PASS，banner↔simvins.log 逐轮核，judge_site 恒 3090）；池自补给=B3[nuc3
  冻结]/B5[低优]/HAFIX 影子一键[批到即跑]在册 ≥3。

## B. 剩余（七件）

1. HAFIX 复验批本体影子重判（T1 写码毕+gtest 37/37+干测毕，批让位未发射；批到即
   t3_2d_hafix_rejudge --pattern run_DRILLD1_N8P_<批前缀> 一键）。
2. ②b 配置链审计（banner=0 根因在 T2 域：env 通路/谓词首过阈值/banner 发射）+判临界时
   W∈{5,20} 复验轮判读面。
3. B3 筛选统计章（nuc3 冻结阻塞）。
4. B5 epsilon 带审计实跑（低优池件）。
5. A1 observe 扩批（授权在 T2/用户侧）。
6. TK/BX 批轮 j0_decomp 补跑（T2 批脚本/T1 drill 变体 harness 均不产此件——j0d 面
   吸收通道缺失，批补跑链沿 v10.6 先例）。
7. T1《实机静态病理报告》v1.2 统计侧并入（素材已交 @T1 04:1x 件行；T1 侧改版件）。

## C. 卡点（客观描述；不附方案）

- HAFIX 复验批排程权在 T1（让位条款兑现后未再排）；T3 工具就绪零轮成本等待。
- **同夜基线波动**（②a B 75% vs ②b B 25% 同夜同栈）——臂对判读的"同夜同栈=可比"前提
  被打破，±15pp 级判读均需夜态分层注记（已入 ②b 表注记；后续批判读面沿用）。
- 绿组 δ 对照物理不可得（绿轮袋未录图像——样本域开口；未来录制政策在 T1/T2 侧）。
- nuc3 冻结（用户裁定）维持——B3 整体不触发。
- 判读域 j0_decomp 产物通道单源（T1 标准 harness）——批脚本变体不产件=结构性。

## D. 资产（md5 记档）

| 件 | md5 前 8 |
|---|---|
| t3_anchor_sentinel.py（哨兵 v1.0） | 部署 repo analysis/ |
| realmachine_j0d_odom_20261010.{csv,md} | 8313d391(md) |
| online_delta_stats_20261010.{csv,md} | 1ea0377a(md) |
| warmup_greenrate_bias2a_20261010.{csv,md} | 807f6320(md) |
| warmup_greenrate_bias2b_20261010.{csv,md} | （同批生成） |
| m3_prebaseline_v1.csv | ca4d4bdd |
| goal_adopted_attribution_note_20261010.md | 0da6ce7e |
| combo_matrix_20261010_rounds.csv（416 轮） | 哨兵门 PASS×2 代 |
| j0d_stats_20261010.csv（286 零漂移） | drifted=0 |
| expansion_20261010.md（滚入台账） | repo t3_results/ |
| X7 终稿（追加 85 行） | f4e96bbd 基线零改动验证 PASS |
| STATUS.md（同步首例） | ce8dcb56 双侧一致 |

## E. 等待

- W-T1：HAFIX 复验批发射→影子重判一键（B-1）。
- W-T2：②b 配置链审计回执+W 梯度复验轮→判读面。
- W-用户：A1 扩批授权②nuc3 解冻③（无新增）。
- 池（≥3 维持）：B5/B3[冻结]/HAFIX 影子。

## F. 坑账（本会话三条）

1. STATUS 时间标签纪律自违反×1：长轮询真实耗时误判（多段 sleep 累计>Session 主观时长），
   尾行时间戳写错——date 先行纪律必须逐次执行；python 修正（sed 中文坑规避）。
2. pgrep 自匹配复发×1（轮询命令自身含关键字）：精确锚定模式（'^bash <script>' 或
   pgrep -f <path>）解；与在册 pgrep 坑家族合并。
3. STATUS 尾区显示层乱码误判：Git Bash 终端解码层把 UTF-8 正常字节显示为 GBK 乱码——
   字节级取证（python decode + 特征字节搜索）=文件本体干净的判别法；禁据显示层结论
   动文件。
