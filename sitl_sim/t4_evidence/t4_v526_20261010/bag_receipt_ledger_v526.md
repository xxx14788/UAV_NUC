# T4 v5.26 新袋收货汇总台账（单元3，2026-10-09）

## 0. 盘点依据与环境口径
- 3090 探测：`ssh nuc2 'date;hostname'` → 07:23 / ghj-System-Product-Name，RC=0；NUC 探测：`ssh nuc` → 07:23 / uav4，RC=0。**双双可达，无降级注记**（与用户 2026-10-09 可达预期一致）。
- remoteUp=true（盘点员口径，本汇总各单元 ssh 全程畅通互证；本夜末次远端接触 07:58 RC=0）。
- df 口径：盘点员实测解析失败（未获数字）；任务书基线自查 524G（红线 20G）。**本汇总未重测 df**，腾位件无涉（全夜零删除、零大 IO 除锚袋 md5×3）。
- 袋实物盘点口径：`find ~ -maxdepth 4 -name '*.bag' -newermt '2026-10-07'`（盘点员执行，全窗口 180 袋，四袋 magic 抽验 #ROSBAG V2.0 过）。本汇总收货范围=盘点 cohort 清单 7 项；滚动新增（如 DFS 细扫回放产物）见 §6 W-T2 登记。
- 判据总口径（红线①，全 cohort 一致）：7 个 cohort **无一存在 T4 预注册收货判据**——t4-w3w5 §3 场景分门口径经 grep 实测归属 T3 实验到位门（阈值"连续 3s"命中 /home/ghj/catkin_ws/sitl_sim/t3_experiments.md 等，非 T4 收货判据，且 10-01 时点为"建议稿待 T3 核签"）；各批实验级判决（T1/T2 域）已在 STATUS/t2_results 落盘者以描述性引用记录。**故 78 袋实物全部只记"收讫-待判"，零三态。**

## 1. cohort 1/7 预热对照批（定义16/实物15）
缺失：run_WU_E8P_A_* 不存在（昨夜）；补飞证据链=WU_FIX_E8P_A{,_r2}（cohort5，STATUS:1089 T2 判 r2 干测 PASS）+复验批 E8P_A_054552（cohort2）。
```
run_WU_E8P_A_*|-|-|-|A(预期,未到货)|未到货-缺失注记
run_WU_E8P_B_160512|379s|odom=11379,imu_raw=87460,pcmd=32323,goal=15,img=0|-|B|收讫-待判
run_WU_S12P_A_161957|391s|odom=11738,imu_raw=87646,pcmd=34172,goal=92,img=0|-|A|收讫-待判
run_WU_S12P_B_161217|392s|odom=11770,imu_raw=90549,pcmd=33197,goal=18,img=0|-|B|收讫-待判
run_WU_S8O_A_162735|390s|odom=11729,imu_raw=87394,pcmd=34172,goal=92,img=0|-|A|收讫-待判
run_WU_S8O_B_163510|104s|odom=3131,imu_raw=23596,pcmd=4415,goal=15,img=0|-|B|收讫-待判
run_WU_E12O_A_164025|391s|odom=11734,imu_raw=87243,pcmd=34171,goal=93,img=0|-|A|收讫-待判
run_WU_E12O_B_163747|105s|odom=3172,imu_raw=24023,pcmd=5575,goal=14,img=0|-|B|收讫-待判
run_WU_NE8O_A_164759|399s|odom=11973,imu_raw=88613,pcmd=34172,goal=93,img=0|-|A|收讫-待判
run_WU_NE8O_B_165541|158s|odom=4763,imu_raw=35743,pcmd=4416,goal=28,img=0|-|B|收讫-待判
run_WU_N8P_A_170142|391s|odom=11744,imu_raw=89534,pcmd=34170,goal=92,img=0|-|A|收讫-待判
run_WU_N8P_B_165914|94s|odom=2838,imu_raw=21928,pcmd=4416,goal=14,img=0|-|B|收讫-待判
run_WU_E12P_A_170921|391s|odom=11740,imu_raw=86776,pcmd=34173,goal=92,img=0|-|A|收讫-待判
run_WU_E12P_B_171659|89s|odom=2673,imu_raw=20024,pcmd=3260,goal=15,img=0|-|B|收讫-待判
run_WU_S8P_A_172142|391s|odom=11733,imu_raw=86900,pcmd=34170,goal=92,img=0|-|A|收讫-待判
run_WU_S8P_B_171914|94s|odom=2834,imu_raw=21223,pcmd=4404,goal=14,img=0|-|B|收讫-待判
```
issues：①E8P_A 实物缺失（见上，缺失交汇总）；②无预注册收货判据→全部收讫-待判；③B 臂多袋短时长（89-158s vs A 390-399s）与 STATUS.md:1065 T1 定案"NOT-EFFECTIVE(A 0%/B 50%,FSM 不采 mission goal)"形态一致，描述性。size/mtime 全录 cohort1_WU_warmup_receipt_20261009.md。

## 2. cohort 2/7 预热复验批（定义16/实物16，另 1 env 壳目录）
T2 冻结判据"≥15pp+方向一致≥6/8"（D:/drone_VINS/plans/2026-10-09_T2_vins_quality_v10.7.md:19）属 T2 实验域且已用毕=STATUS:1095 NOT-EFFECTIVE(A 12.5% vs B 50%,-37.5pp,3/8<6/8)。
```
run_WU2_E12P_A_063516(目录)|无flight.bag|仅hwmon/round.log/sitl.log/vins_config.md5|-|A-复验(env失败r1)|env失败壳目录-被r2替换,无袋可收
run_WU2_E12P_A_r2_070112|131s|odom=3950,imu_raw=29596,pcmd=6111,goal=95,img=0|-|A-复验-修复后(env补轮r2)|收讫-待判
run_WU2_E8P_A_054552|131s|odom=3945,imu_raw=30085,pcmd=6103,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_E12O_A_061543|424s|odom=12751,imu_raw=97385,pcmd=36039,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_N8P_A_063157|143s|odom=4291,imu_raw=32277,pcmd=7261,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_NE8O_A_062352|137s|odom=4122,imu_raw=30971,pcmd=7262,goal=92,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S12P_A_055841|159s|odom=4793,imu_raw=36005,pcmd=7699,goal=95,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S8O_A_060217|145s|odom=4367,imu_raw=32732,pcmd=7259,goal=93,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S8P_A_064155|427s|odom=12811,imu_raw=97830,pcmd=33174,goal=94,img=0|-|A-复验-修复后|收讫-待判
run_WU2_E12O_B_061302|108s|odom=3252,imu_raw=24383,pcmd=5795,goal=14,img=0|-|B-复验-修复后|收讫-待判
run_WU2_E12P_B_063712|89s|odom=2674,imu_raw=20449,pcmd=3260,goal=15,img=0|-|B-复验-修复后|收讫-待判
run_WU2_E8P_B_054850|73s|odom=2216,imu_raw=16757,pcmd=3261,goal=15,img=0|-|B-复验-修复后|收讫-待判
run_WU2_N8P_B_062929|94s|odom=2827,imu_raw=21306,pcmd=4415,goal=14,img=0|-|B-复验-修复后|收讫-待判
run_WU2_NE8O_B_062703|94s|odom=2823,imu_raw=21361,pcmd=4415,goal=14,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S12P_B_055049|404s|odom=12128,imu_raw=93542,pcmd=33195,goal=17,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S8O_B_060537|382s|odom=11463,imu_raw=87395,pcmd=33185,goal=15,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S8P_B_063927|94s|odom=2839,imu_raw=21879,pcmd=4427,goal=14,img=0|-|B-复验-修复后|收讫-待判
```
issues：①E12P_A r1=env 失败壳目录（无袋，T2"16+1 env 补轮"口径吻合）；②昨夜缺失的 E8P_A 槽本批补上；③A 臂 6/8 短飞 vs B 臂 6/8 短（全长袋：E12O_A/S8P_A/S12P_B/S8O_B），goal 计数 A 92-95 vs B 14-17 同昨夜形态，描述性。size/mtime 全录 cohort2_WU2_reverify_receipt_20261009.md。

## 3. cohort 3/7 三臂昨批（定义29/实物29；ta=A臂）
scope 修正：`3ARM_*` 全部 vins_out.bag=41（=本批 29+bc 12 属 cohort4，零重叠）。topics 结构=每袋恒 2 topic（/vins_estimator/imu_propagate + /vins_estimator/odometry）。
```
3ARM_base_MA_r1_flight|13.1s|vOdom=343,vProp=6333,img=0|-|base(无ta)|收讫-待判(异常短13.1s中止轮,r1b已补)
3ARM_base_MA_r1b_flight|354s|vOdom=4368,vProp=100382,img=0|-|base(无ta)|收讫-待判
3ARM_base_MA_r2_flight|354s|vOdom=4209,vProp=97912,img=0|-|base(无ta)|收讫-待判
3ARM_base_MB_r1_flight|358s|vOdom=6898,vProp=159712,img=0|-|base(无ta)|收讫-待判
3ARM_base_MB_r2_flight|358s|vOdom=6899,vProp=159731,img=0|-|base(无ta)|收讫-待判
3ARM_A_MA_d0_r1_ta_*|354s|vOdom=4332,vProp=100980,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d0_r2_ta_*|354s|vOdom=4113,vProp=94458,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+2_r1_ta_*|354s|vOdom=4219,vProp=97130,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-2_r1_ta_*|354s|vOdom=4471,vProp=103547,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+2_r2_ta_*|354s|vOdom=3804,vProp=88607,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-2_r2_ta_*|354s|vOdom=5059,vProp=117361,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+5_r1_ta_*|354s|vOdom=2325,vProp=54116,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-5_r1_ta_*|354s|vOdom=2325,vProp=54126,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+5_r2_ta_*|354s|vOdom=2325,vProp=54119,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-5_r2_ta_*|354s|vOdom=2325,vProp=54119,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+10_r1_ta_*|354s|vOdom=2325,vProp=54121,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-10_r1_ta_*|354s|vOdom=2325,vProp=54116,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+10_r2_ta_*|354s|vOdom=2325,vProp=54120,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-10_r2_ta_*|354s|vOdom=2325,vProp=54118,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+20_r1_ta_*|354s|vOdom=2325,vProp=54120,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-20_r1_ta_*|354s|vOdom=2325,vProp=54116,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d+20_r2_ta_*|354s|vOdom=2325,vProp=54119,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MA_d-20_r2_ta_*|354s|vOdom=2325,vProp=54118,img=0|-|ta(A臂)|收讫-待判
3ARM_A_MB_d0_r1_ta_*|358s|vOdom=6898,vProp=159698,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d0_r2_ta_*|358s|vOdom=6875,vProp=159203,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d+10_r1_ta_*|358s|vOdom=3454,vProp=80196,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d-10_r1_ta_*|358s|vOdom=3454,vProp=80199,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d+10_r2_ta_*|358s|vOdom=3454,vProp=80199,img=0|-|ta(A臂,MB机型)|收讫-待判
3ARM_A_MB_d-10_r2_ta_*|358s|vOdom=3454,vProp=80199,img=0|-|ta(A臂,MB机型)|收讫-待判
```
（目录名尾部"_ta_3ARM_…_edited"双重后缀为远端原样，"ta_*"缩写）
issues：①组成与盘点精确一致（base5+A_MA 18+A_MB 6=29，任务书'昨18'差=base5+MB6）；②A 臂 δ 扫描已有判决=δ 相变实锤（T2 v10.7:6）；③base_MA_r1=13.1s 中止轮（r1b 已补）；④|δ|≥5 袋 vOdom 恒 2325 帧 vs |δ|<5 及 d0 为 3800-5059，帧数分档与 δ 强相关，描述性。size/mtime 全录 cohort3_3ARM_yesterday_receipt_20261009.md。

## 4. cohort 4/7 三臂今补批（定义12/实物12；bc=B/C臂 editor修复后）
B8+C4 与 T2 v10.7:24"臂 B 8 轮+臂 C 4 轮（editor dry 双 PASS 已验）"精确一致；本批=三臂终判表前置尾欠。
```
3ARM_B_drop3_r1_bc_*|354s|vOdom=3488,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop3_r2_bc_*|354s|vOdom=3490,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop10_r1_bc_*|354s|vOdom=4062,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop10_r2_bc_*|354s|vOdom=3976,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_down15_r1_bc_*|354s|vOdom=3692,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_down15_r2_bc_*|354s|vOdom=3614,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_reord2_r1_bc_*|354s|vOdom=4161,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_reord2_r2_bc_*|354s|vOdom=3874,ntopics=2,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_C_ctr_r1_bc_*|354s|vOdom=4001,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_ctr_r2_bc_*|354s|vOdom=4108,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_full_r1_bc_*|354s|vOdom=4101,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_full_r2_bc_*|354s|vOdom=4106,ntopics=2,img=0|-|bc(C臂-editor修复后)|收讫-待判
```
issues：B_reord2 对 r1 mtime(05:24:30) 晚于 r2(04:41:58)——命名序与落袋时间倒挂，照录。size/mtime 全录 cohort4_3ARM_bc_receipt_20261009.md。

## 5. cohort 5/7 WU_FIX 干测（定义2/实物2）
```
run_WU_FIX_E8P_A_052657|119s|odom=3587,imu_raw=27736,pcmd=无,goal=无,img=0|-|A-修复后干测r1(失败轮)|收讫-待判(无pcmd/goal topic=planner未出指令)
run_WU_FIX_E8P_A_r2_053539|205s|odom=6179,imu_raw=46947,pcmd=6104,goal=107,img=0|-|A-修复后干测r2|收讫-待判(T2已判PASS见STATUS:1089,非T4三态)
```
issues：r1 无 /position_cmd 与 goal topic（干测未过形态），r2 两 topic 在且 goal=107（提频重发形态）——与 T2 r1 失败→r2 PASS 路径自洽。

## 6. cohort 6/7 候选 A1（定义2/实物3，另 1 env 壳目录）
两档口径已寻得=D:/drone_VINS/t4_work_20261008/t4_v524_workflow.ts:18,355-356,333-336；三袋 imgTopics=0 → 全部紧凑零图像档。锚袋 md5 已履行（见 §8）。T2 判决=1c_runs/a1_observe_verdict_v1.md：r1 PASS(0.094)/r2 FAIL(5.435)/r3b FAIL(3.350)→1/3 混合带→证据不足，扩批挂池（STATUS 尾部 T2 07:2x 行同口径互证）。
```
run_A1OBS_N8P_r1_070732|94s|odom=2829,imu_raw=21703,pcmd=4406,goal=14,vinsTopics=2,img=0|782619d5|A1-observe臂|收讫-待判(紧凑零图像档;T2判r1 PASS 0.094)
run_A1OBS_N8P_r2_070959|400s|odom=12020,imu_raw=93055,pcmd=33195,goal=17,vinsTopics=2,img=0|06eaaca2|A1-observe臂|收讫-待判(紧凑零图像档;T2判r2 FAIL jump5.435)
run_A1OBS_N8P_r3b_072300|105s|odom=3161,imu_raw=23819,pcmd=4494,goal=16,vinsTopics=2,img=0|52483365|A1-observe臂(env补轮)|收讫-待判(紧凑零图像档;T2判r3b FAIL jump3.350)
run_A1OBS_N8P_r3_071747(目录)|无flight.bag|仅hwmon/round.log/sitl.log/vins_config.md5|-|A1-observe(env失败r3)|ENV-FAIL壳目录(双目话题未现),无袋可收
```
issues：实物 3 袋非盘点 2 袋（r3b 07:25:25 落袋，盘点 07:30 快照漏计）；T2 判决文件自证批次设计=N8P×3+1 env 补轮，r3b 属本 cohort 一并收讫。

## 7. cohort 7/7 未归类（定义1/实物1）
```
run_WU1b_E8P_A1_154907|402s|odom=12084,imu_raw=90065,pcmd=34161,goal=94,vinsProp=90056,vinsOdom=3814,img=0|-|无(未归类:结构证据指预热试飞,A1字样待T2口径)|收讫-待判(未归类-归属待T2;TIMEOUT未到位8.918m;T3 j0d已消费)
```
issues：归属未定案（grep WU1b 全库 0 命中 T1/T2 文字）；结构证据=候选 A1 预注册格子 N8P+A1OBS 命名+本袋早于预注册 12h 且为 E8P 格→指预热 1b 试飞（非 A1）；arrive_watch=TIMEOUT min_truth=8.918；T3 j0_decomp.json（04:06）已消费（jump 0.1587m/1 帧，transit 主导）。

## 8. 臂配对标注口径（后续判读者照此认袋）
- **识别顺序**：目录名批前缀（run_WU_/run_WU2_/run_WU_FIX_/run_A1OBS_/3ARM_/run_WU1b_）→ 臂段或尾标 → env 补轮标记（r2/r3b 后缀、壳目录）。
- **预热对照批** `run_WU_<场景>_<A|B>_<HHMMSS>`：臂=文件名 `_A_`/`_B_` 段（盘点口径"A/B臂标记在文件名后缀"）；8 场景×2 臂=16 配对基线。
- **预热复验批** `run_WU2_*`：臂段识别同上；**全批两臂均标"复验-修复后"**——依据=T2 v10.7 单元2"修复后配对 ≥8 对同夜重跑两臂（B 臂旧数据禁跨夜复用）"，即两臂皆 goal 修复后同夜新飞，不存在"旧 B 臂"；E12P_A 的 r2=env 补轮（r1 壳目录无袋），标"env补轮r2"。
- **三臂批** `3ARM_*`：尾标 `_ta_`=A 臂、`_bc_`=B/C 臂（盘点口径；B_* 变体=B 臂、C_* 变体=C 臂）；`base_*_flight`=base 基准轮（无 ta/bc，标 base）；bc 批 12 轮为 editor 修复后（T2 v10.7 单元3），标"editor修复后"。任务书'昨18'与实测 29 的差=base5+MB6（已在册）。
- **WU_FIX**：A 臂 goal 修复干测 r1/r2（r1 失败轮无 pcmd/goal，r2 为 T2 判 PASS 轮）。
- **A1OBS**：A1-observe 臂（预注册命名，N8P 格，T2_IQG_OBSERVE=1）；r3b=env 补轮。
- **run_WU1b_E8P_A1**：未归类——"A1"字样两读（候选 A1 vs A 臂 r1 试飞），结构证据指后者，**归属以 T2 口径为准，判读者暂按非 A1 序列处理**。

## 9. 锚袋台账（md5 凭据）
- **候选 A1：a1_flown=true**（A1OBS_N8P r1/r2/r3b 三袋实物在+T2 判决落盘；"未飞"条款不触发）。锚袋三袋 md5（红线④/⑤协议全程：07:51 查进程见 T2 回放在飞→备让路；07:53 复核进程=0→STATUS 预告行（scp 中文通道，tail 复核 RC=0）→进程复核 T2_ACTIVE_CHECK=0→串行 md5sum 全 rc=0）：
  - run_A1OBS_N8P_r1_070732/flight.bag = `782619d5`（782619d5a4be7e79c367ee9b3787d79f）
  - run_A1OBS_N8P_r2_070959/flight.bag = `06eaaca2`（06eaaca203353cc9655fa00036735f0c）
  - run_A1OBS_N8P_r3b_072300/flight.bag = `52483365`（524833659a87f7bc5d6b164e1dec1826）
- 其余 6 cohort 无预注册锚袋定义（任务书"工具正源 md5 前 8"指工具源非袋）→ md5 栏='-'，以 size+mtime 代记（各 cohort 分册全录）；红线④下不做非必要大 IO。

## 10. W-T2 滚动件登记
- 今晚滚动件三样**盘点时已实物在盘、本夜全部收讫**：预热复验 16 轮（05:48-07:04，含 E12P_A_r2_070112 补轮，§2）、三臂今补 12（03:53-05:24，§4）、候选 A1（07:09/07:17/07:25 三袋，§6）——明细见各 cohort 节。
- **滚动新增未收**：07:46 实测 T2 DFS δ 细扫回放窗在飞（rosbag play /tmp/dfs_DFS_A_MA_d4_r1_edited.bag + record 写 t3_results/DFS_A_MA_d4_r1_*/vins_out）——DFS 系产物不在盘点 cohort 清单内且持续产出，留滚动增量由下任按同口径收（红线②：本汇总不下任何三态）。
- 滚动快照末次核查=07:56（cohort7 单元）。

## 11. 心跳（单元3）
（见 §12 执行记录；STATUS 已追加一行，格式"<HH:MM> | T4 | 心跳 | v5.26 | 单元3: …"）

## 12. 执行记录与分册索引
- 每袋 rosbag info 均 `ssh nuc2 bash -lc 'source /opt/ros/noetic/setup.bash; rosbag info <bag>'`，逐袋退出码回收；78 袋全部 rc=0、chunks N/N 完整、imgTopics=0（索引可读=袋可读）。
- 分册（含 size+mtime 全表与逐 cohort 判据核查）：cohort1_WU_warmup_receipt_20261009.md / cohort2_WU2_reverify_receipt_20261009.md / cohort3_3ARM_yesterday_receipt_20261009.md / cohort4_3ARM_bc_receipt_20261009.md / cohort5_WU_FIX_receipt_20261009.md / cohort6_A1OBS_receipt_20261009.md / cohort7_WU1b_unclassified_receipt_20261009.md。
- 心跳执行：07:58 取远端时间→本地 UTF-8 写行→scp /tmp/t4_tmp_hb.txt→remote cat >> STATUS.md→tail 复核（结果见返回 notes）。

## 13. 滚动件补收（W-T2 到货）
- 到货确认：**新增 0 袋**（三样滚动件盘点时已在盘）；本节=复验批 16+三臂今补 12+候选 A1 3 袋的合并补收登记。逐袋 rosbag info 于本夜 07:42/07:47/07:5x 三轮实测，滚动批合并复核一轮（28/28 rc=0、chunks N/N 完整、img=0，数值与前轮逐位一致）。

### 台账行
```
run_WU2_E12P_A_r2_070112|131s|odom=3950,vOdom=1133,img=0|-|A-复验-修复后(env补轮r2)|收讫-待判
run_WU2_E8P_A_054552|131s|odom=3945,vOdom=1261,img=0|-|A-复验-修复后|收讫-待判
run_WU2_E12O_A_061543|424s|odom=12751,vOdom=4116,img=0|-|A-复验-修复后|收讫-待判
run_WU2_N8P_A_063157|143s|odom=4291,vOdom=1369,img=0|-|A-复验-修复后|收讫-待判
run_WU2_NE8O_A_062352|137s|odom=4122,vOdom=1315,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S12P_A_055841|159s|odom=4793,vOdom=1529,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S8O_A_060217|145s|odom=4367,vOdom=1414,img=0|-|A-复验-修复后|收讫-待判
run_WU2_S8P_A_064155|427s|odom=12811,vOdom=4097,img=0|-|A-复验-修复后|收讫-待判
run_WU2_E12O_B_061302|108s|odom=3252,vOdom=1051,img=0|-|B-复验-修复后|收讫-待判
run_WU2_E12P_B_063712|89s|odom=2674,vOdom=725,img=0|-|B-复验-修复后|收讫-待判
run_WU2_E8P_B_054850|73s|odom=2216,vOdom=541,img=0|-|B-复验-修复后|收讫-待判
run_WU2_N8P_B_062929|94s|odom=2827,vOdom=904,img=0|-|B-复验-修复后|收讫-待判
run_WU2_NE8O_B_062703|94s|odom=2823,vOdom=894,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S12P_B_055049|404s|odom=12128,vOdom=3860,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S8O_B_060537|382s|odom=11463,vOdom=3660,img=0|-|B-复验-修复后|收讫-待判
run_WU2_S8P_B_063927|94s|odom=2839,vOdom=914,img=0|-|B-复验-修复后|收讫-待判
3ARM_B_drop3_r1_bc_*|354s|vOdom=3488,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop3_r2_bc_*|354s|vOdom=3490,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop10_r1_bc_*|354s|vOdom=4062,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_drop10_r2_bc_*|354s|vOdom=3976,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_down15_r1_bc_*|354s|vOdom=3692,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_down15_r2_bc_*|354s|vOdom=3614,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_reord2_r1_bc_*|354s|vOdom=4161,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_B_reord2_r2_bc_*|354s|vOdom=3874,img=0|-|bc(B臂-editor修复后)|收讫-待判
3ARM_C_ctr_r1_bc_*|354s|vOdom=4001,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_ctr_r2_bc_*|354s|vOdom=4108,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_full_r1_bc_*|354s|vOdom=4101,img=0|-|bc(C臂-editor修复后)|收讫-待判
3ARM_C_full_r2_bc_*|354s|vOdom=4106,img=0|-|bc(C臂-editor修复后)|收讫-待判
run_A1OBS_N8P_r1_070732|94s|odom=2829,imu_raw=21703,pcmd=4406,goal=14,vinsTopics=2,img=0|782619d5|A1-observe臂|收讫-待判(紧凑零图像档;T2判r1 PASS 0.094)
run_A1OBS_N8P_r2_070959|400s|odom=12020,imu_raw=93055,pcmd=33195,goal=17,vinsTopics=2,img=0|06eaaca2|A1-observe臂|收讫-待判(紧凑零图像档;T2判r2 FAIL jump5.435)
run_A1OBS_N8P_r3b_072300|105s|odom=3161,imu_raw=23819,pcmd=4494,goal=16,vinsTopics=2,img=0|52483365|A1-observe臂(env补轮)|收讫-待判(紧凑零图像档;T2判r3b FAIL jump3.350)
```
（壳目录注记：run_WU2_E12P_A_063516 与 run_A1OBS_N8P_r3_071747 均无 flight.bag=env 失败壳，见 §2/§6，无袋可收）

### W-T2 销记行
**W-T2 销记：滚动件三样到货已全部收讫入账**——预热复验 16 轮（§2/本节）+三臂今补 12 轮（§4/本节）+候选 A1 3 袋（§6/本节，a1_flown=true，锚袋 md5×3 凭据在册）＝31 袋收讫-待判、零三态。W-T2 到货等待关闭。遗留滚动增量：DFS δ 细扫回放产物（07:46 实测 record 在写 t3_results/DFS_*，不属盘点 cohort）留下任按同口径收；W-IO 无挂起（锚袋 md5 已毕）。判据口径不变：无 T4 预注册收货判据（复验批冻结判据 ≥15pp+≥6/8 属 T2 实验域已用毕=STATUS:1095），全节零三态。
