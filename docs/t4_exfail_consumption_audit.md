# T4 池件④：EX-FAIL 坑位表下游消费审计（2026-10-03）

登记性质：文本面证据扫描与引用核对，全程只读、未改任何他线文件；本文=统计事实登记，不含 PASS/FAIL 判读语，处置语义待主会话定稿。执行=T4 池件线（锁名流 t4wf，未取锁——纯文本扫描无大 IO 无重活，未触锁语义/空窗前置/df 门）。

## 0. 任务口径与正本差异（必读）

- 任务书四坑清单：n>0 禁只看退出码 / density 双 shift / 键集代差 / **帧目录非袋**。
- 正本坑位表（`docs/t4_verdicts_v2.md:274-278`，定稿 commit 7032a2d 2026-10-02）四坑：①零告警空统计（全帧不可读时 metrics/fb **退出 0 且输出合法 JSON n=0**，下游必须验 n_primary>0 与键完整性，禁只看退出码/可解析）②NaN 字面量落盘 ③density 复现性陷阱（fresh 默认 shift vs 在册逐袋实测 shift，对账必须带逐袋 shift）④键集代差（在册 base json 缺 supply/grid 两键，按完整键集对账会误判缺面）。
- **差异声明**：任务书第四坑"帧目录非袋"不在正本坑位表单列四坑内；其对应实锤在 `docs/t4_verdicts_v2.md:179`（W1.0 勘误：j3_replay_features.sh 吃**原始袋**（rosbag play）非帧目录，2026-10-02）与 `sitl_sim/t4_evidence/v54_20261002/derived/exfail_matrix_synthetic.md:10,41,42`（density/1a、1b 格帧目录路径喂入→`IsADirectoryError(rosbag/bag.py:1450)`→干净拒绝）。本文按任务书四坑口径逐坑审计；坑② NaN 附带登记。

## 1. 方法与范围（实际执行面）

- 扫描器：本地写 `scan_exfail.py`（UTF-8）→ scp 至 `nuc:/tmp/t4wf_pool4_scan.py`，md5 双端对账一致 `3a6acd675cc4e32788d516a3656334b1` → 远端 `python3` 执行 → 原始输出 `/tmp/t4wf_pool4_scan_out.txt`（241 命中行，已留档）。
- 关键词族（python 子串匹配）：P1=[退出码, n_primary, n>0, n=0, 零告警, 空统计, 假绿, 只看退出, exit code, exit_code, 退出 0, 退出0]；P2=[NaN, allow_nan]；P3=[shift, density, 复现性陷阱, 逐袋 shift]；P4=[键集, 代差, schema_version, legacy, supply/grid, 两键]；PF=[帧目录, 非袋, frame_dir, 帧样目录, 目录非袋]。
- 范围=任务点名三面：① `~/sitl_sim/STATUS.md` 全史 617 行；② `docs/` 他线判读文 t2_*(7 文件)+t3_*(4 文件)；③ git 提交消息全史 298 条（`~/catkin_ws` branch main），他线判定=subject 不含"T4"（GIT-OTHER 24 条命中），T4 自身提交单列对照（GIT-T4SELF 2 条）。
- 补充面（任务范围外延伸，结论同零）：`t1_vins_odom_contract.md` 零命中；`xline_*(5 文件)` 4 命中全伪；`docs/sim2real_runbook.md` grep `j3|EX-FAIL|exfail` 仅 `:13/:81` 两处为 FOV 数据源文件名引用（t4_j3_e1e2_evidence.md），**非判读链工具引用**——T3 判读链凭证表（commit 9e7cc31/9bb9939 所指 sec-9.1）未含 T4 j3 工具；`docs/t4_t2_handoff_tracking.md`（T4 跟办文）见 §4。
- 局限：关键词法对措辞变体（"空产出""计数为零"类）会漏检；241 条命中已逐条人工语义核对归类（伪命中清单见 §2/§3），结论按"关键词口径下的零消费"表述，不声称穷尽自然语言变体。

## 2. 逐坑消费计数（主结论）

### 坑① n>0 禁只看退出码（零告警空统计）——他线踩中 0 次 + 引用 0 次 = 零消费

- 同型独立实践 2 处（非坑位表引用、对象非 j3 工具，**不计消费**，登记供主会话定夺）：
  - `docs/t3_z12_prewire_pack.md:48`（2026-10-02）："gtest 14/14；退出码以结果文件为准——run_tests 吞码坑"——同族纪律（退出码不可信须看结果），对象=catkin run_tests，全文无坑位表字样。
  - commit `9a632ec`（T1 前缀，2026-10-01）："4套直跑53/53绿…退出码纪律"——对象=gtest 常规化补缺。
- 伪命中排除：STATUS:78/266/494/495（T3/T1 的 grep/catkin/构建退出码语境）、STATUS:337/342 与 t2_experiments.md:1129/1178/1732-1735（acc_n=0.2、depth n=0、"n=0"数字巧合）、`docs/t3_r3_planner_domain_evidence.md:83`（ego_planner **exit code -11 段错误**=进程崩溃观察，与"退出 0 假绿"方向相反）。
- T4 自域引用（对照面，非他线）：`t4_verdicts_v2.md:285`（"修复前在册轮次的下游判读仍按上方坑位表 + n>0 禁只看退出码纪律执行"）、commit `3a2722f`（C14-FIX-1"全帧不可读退出0+n=0假绿→零可读帧拒绝"）、commit `9d810aa`（C14-LEDGER"坑位表+n>0 禁只看退出码"）、STATUS:587（02:32|T4）。

### 坑③ density 双 shift（复现性陷阱）——他线踩中 0 次 + 引用 0 次 = 零消费

- 伪命中排除：`t2_experiments.md` 全部 41 条 shift 命中（2026-09-27～10-02）均为 t2_[BCDE]_shift.bag / t2_shift_img_stamps.py 图像时戳平移族（跨域 1.79e9s 修正），与 j3_feature_density 的 shift 参数无涉；`t2_wa_fullregression.md:24,36` 为袋名 Y4W_t2w5_p1b_shift；STATUS:117/215/240/251/306/419/439/479/592/593 同为袋名/矩阵代名。
- T4 自域引用（对照）：commit `282a707`（C14-FIX-3"来源单一化 explicit/legacy/shift-file"）、STATUS:609（04:52|T4）、exfail_matrix_synthetic.md 修复复跑登记节。

### 坑④ 键集代差——他线踩中 0 次 + 引用 0 次 = 零消费

- 伪命中排除："legacy"在他线文本全部为 VINS legacy 二进制/防线门语义（t2_experiments.md:1732/1734/1735、STATUS:298/301/357/370/381/409/545/603、T1 提交 a793b57/0b8a80c/966003e/11e67ac/8d8bf6f/3997b36）；补充面 `xline_opcard_v1.md:67`"两键"=x4judge 读 wa_gate_online.json 两键（T3 自有判读链 json），均非 base json 键集代差。`schema_version`/`legacy_keys` 关键词在他线文本零命中。
- T4 自域引用（对照）：commit `ea4d12b`（C14-FIX-4）、STATUS:610（04:58|T4）、`t4_verdicts_v2.md:278-279,290`。

### 坑PF 帧目录非袋（任务书口径第四坑；正本坑位表未单列）——他线踩中 0 次 + 引用 0 次 = 零消费

- 该坑实锤均在 T4 自域：`t4_verdicts_v2.md:179`（W1.0 勘误"j3_replay_features.sh 吃原始袋（rosbag play）非帧目录"，2026-10-02）；`derived/exfail_matrix_synthetic.md:10,41,42`（density/1a、1b 格帧目录喂入→IsADirectoryError→干净拒绝，30 格自测面）。
- 伪命中排除：STATUS:463（T4 提帧回执）、STATUS:466（T3 清袋收口"manifest+帧目录实存"=**删前存在性核对**，非误当袋喂工具）、`t2_experiments.md:1747`（"①**非袋**内数据"=route 定因排他论证，词语巧合）。

### 坑② NaN 字面量落盘（附带登记，任务四坑清单外）——他线踩中/引用 0 次

- 伪命中排除：`t3_experiments.md:158-163`（attitude_utils NaN 防护）、`t2_experiments.md:1107`（深度域防 NaN）、commit f76278e/88ecd21/a03a537（gtest 协方差 NaN）——均 VINS/测试域。T4 自域：commit `d2bb538`（C14-FIX-2）、STATUS:607。

## 3. 他线提交消息面（298 条全扫）

- 计入他线（subject 无"T4"）命中 24 条；22 条语义无关（排除理由见 §2）；其余为 C14 系列。
- **C14 系列 6 commit（3a2722f/d2bb538/282a707/ea4d12b/8c5392e/9d810aa，均 2026-10-03）归属判定=T4 自线**：协作通报板 STATUS.md L587(02:32)/L607(04:36)/L609(04:52)/L610(04:58)/L611(06:03) 五条通报的作者列全部为 T4，修复→回归→登记→收口全链在 T4 通报链内；故不计他线消费。归属最终裁定待主会话定稿（author 均为 rick，无法从 author 区分，依据=通报板行作者列）。

## 4. 坑位表对他线的可见性/传播面（零消费的背景事实）

1. `docs/t4_verdicts_v2.md:274`（2026-10-02，commit 7032a2d）："EX-FAIL 工具坑位表（**T2 验证轮判读前必读**，详=derived/exfail_matrix_*.md 30 格）"。
2. `~/sitl_sim/STATUS.md:546`（2026-10-02 05:25 | T4 | v5.4战役收口@T2 @T3）：行尾"T2验证轮判读请先读EX-FAIL坑位表"——坑位表上板对他线指路的唯一 STATUS 节点。
3. `~/sitl_sim/STATUS.md:611`（2026-10-03 06:03 | T4 | C-14收口）："T2 验证轮判读请按新版工具与更新后期望分类表走（详=…exfail_matrix_synthetic.md §0a/§0b）"。
4. `docs/t4_t2_handoff_tracking.md:62`（T4 跟办文）："T2 回归结果待其验证轮回跑——T2 v8.2 收口（04:32）扫描面内未见其对四缺陷新工具的回归回执"；`:67`："①U3PR2 供给嫌疑复核：待 T2 回执（输入面=STATUS:546 嫌疑清单+EX-FAIL 坑位表）"。
5. `docs/t4_t2_handoff_tracking.md:10`：T4 已于 2026-10-03 对 t2_experiments.md（repo 副本 1757 行+运行时台账 1892 行全文）做过含"坑位/EX-FAIL"的关键词扫描并确认覆盖——与本审计独立结论互证（T2 台账无坑位表引用）。

## 5. 覆盖度对账（扫过且零命中的文件）

- t2_*：t2_a2_xtdrone_audit.md、t2_bias_observability.md、t2_u5_drift_mitigation.md、t2_wa_prophecy.md 零命中；t2_experiments.md 41、t2_wa_fullregression.md 2、t2_marginalization_anatomy.md 1（均伪命中）。
- t3_*：t3_experiments.md 3、t3_r3_planner_domain_evidence.md 1、t3_xline_u3p_baseline.md 1、t3_z12_prewire_pack.md 1（z12 见 §2 坑①同型实践）。
- STATUS.md 全史 41 命中（伪命中+T4 自身通报+C14 链）；git 298 条中 T4 自身命中 2（709530f/3c62aad，均 T4 域工具语境）。

## 6. 结论（统计事实，待主会话定稿）

任务书四坑在他线（T1/T2/T3 的 STATUS 全史行、t2_*/t3_* 判读文正文、他线前缀提交消息）的下游消费=**四坑全部零踩中、零引用**（关键词口径，见 §1 局限）。坑位表当前消费完全在 T4 自域（定义 verdicts L274-278 / 自测矩阵 exfail_matrix 30 格 / C14 修复登记四 commit）；对他线的传播节点已就位（§4 五条）但尚无回执性消费。该结果与挂账状态一致：C-14"T2 验证轮回执挂账"（commit 1f7c730，2026-10-03）——下游消费窗口=T2 验证轮尚未完成，属消费未发生，非传播缺失。

留档：扫描器本机 `D:/drone_VINS/t4_work_20261002/pool4_audit/scan_exfail.py`；远端原始输出 `/tmp/t4wf_pool4_scan_out.txt`（241 行）。
