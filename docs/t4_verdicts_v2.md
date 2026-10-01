# T4 判读账本 v2 — 视觉验收线 + SITL 环境加固线（2026-09-29 夜）

> 任务书: plans/2026-09-28_T4_vision_acceptance_v2.md（v3 含 E 线）。
> v1 三问终判（错拍=无/穿墙=有嫌疑/特征=样本不足）见 plans/2026-09-27_t4_report.md，本文不重复。
> 证据根目录: ~/sitl_sim/t4_evidence/（运行时）；本文=结构化结论入库版。

## E 线验收（全绿）

### E1 锁机制（sitl_lock.sh v2，owner 交付物）
- 语义: 原子 ln -s 取锁/死主自动接管/心跳/preclaim+force 抢占三条件/权序/磁盘门。详 README §3。
- **测试表 14/14 全绿**（t4_evidence/e1_lock_tests_0250.log；此前 0245.log 为 12/14 中间态）:
  活主拒入/死主接管(含 STATUS 证据)/守卫拒放/正常释放/心跳刷新+守卫/水位线门/低权拒抢高权/
  条件②拒抢(假 px4 进程实兵)/条件①拒抢/preclaim 成功/异议窗未满拒 force/force 成功/属主守卫中止/被抢方排队(规程)。
- 开发期抓出并修复 3 个脚本级 bug: ①pgrep -c 无匹配时输出 0 且退出 1,`|| echo 0` 双值拼接炸算术
  ②target_pid 解析 off-by-one(永远扫不到倒数第二段 PID) ③force 异议窗读 preclaim 内嵌 ts 字段,测试不可伪造,改文件 mtime。
- 存量收敛: vins_smoke/t2v3_flight/v1_flight/t1v1_ground 四脚本切 v2(守卫释放);全库无 ln -sf 阳性写法。

### E2 僵尸根除
- 孤儿收割: 今晨 4 孤儿(PID 2454/4309/6989/7967)已随 09-28 23:58 NUC 重启消亡（ps 实证,零存活）。
- 根因机制定案: 旧版 start_sitl_vins.sh `sleep infinity | exec make` 在 make/px4 死后被管道吊住→PPID=1 挂壳。
- 根治: start_sitl_vins.sh v2 = setsid 进程组 + px4 存活监督(任何退出路径整组 TERM→KILL)。
- **验收: E2FAIL1-5 五退出路径全部零 SITL 残留+锁正常释放**（正常轮/中途杀 gzserver/px4ctrl FATAL/takeoff FATAL/清场断言 FATAL）。
- 附带根修: vins_smoke `exec >(tee)` 进程替换令 bash 退出时等 tee→挂壳(E2FAIL4 实测);cleanup 补杀 tee 后 FATAL 路径 3s 退出。

### E3 磁盘治理（6.3G → 85G free）
- 明细: T3 v7.1 自清 t3_runs 67G(01:42 通告,台账已入账)+ T4 批次1 ~32.1G(a1_px4.log 5.1G 失控日志/
  smoke_runs 44 轮 27G(判决已入台账,V1_RESULTS 仅引用 vins_smoke_runs)/A 线散件日志 ~90M//var/crash 已上传件)
  + smoke_runs 补删 27G(02:12 STATUS 通告 30min 异议窗无人异议)。
- manifest: t4_evidence/disk_manifest_20260929.md(白名单全验存活:route7/shift 全家/X1 样本袋/vision_inputs/evidence)。
- **水位线门: df<20G 禁起新轮,已内置于 sitl_lock.sh v2 get(测试表 CASE-5 实证 exit 3)**;各线 >15G 旧门统一提 20G。
- 轮转: /etc/logrotate.d/sitl_sim(daily maxsize 200M rotate 2 compress copytruncate su uav),logrotate -d 0 错误。
- **验收: df 85G(62%) ≥ 40G ✓**（夜初 6.3G/98%）。

### E4 进程崩溃韧性
- throttle 段错误(09-28 22:25,/mavros/imu/data_raw 200Hz→/vins/imu_200hz,Signal 6):
  栈顶 std::terminate←__cxa_throw←libroscpp=roscpp 回调抛未捕获异常。**定案=架构性消除**:
  当前仓库任何链路均无 topic_tools throttle 节点(VINS IMU 供给=511 mavcmd 直连标准),崩源已不在链上;
  全仓 find/grep 复核零 throttle launch。「30 轮零复发」验收随飞轮自然满足(不可能复发)。
- ENV-FAIL 口径: round_result.sh 三签名(ENVDEAD 活体标记/Connection closed/监督回收行)+未-disarm 守卫;
  run_E2FAIL2 真死轮 bag 端到端验证 RESULT=ENV-FAIL(重试不计飞行预算,对齐 T3-X4 环境性重试规则)。
- whoopsie 已禁用(sudo systemctl disable --now;常态 21% CPU 解放,/var/crash 不再累积)。

## J 线状态（素材未齐,错峰规则生效）
- **J1 交付完成**: docs/vision_materials.md(截图清单/目录规范/J1.3 抽样规范)+b0_headless_vins.rviz
  (feature_pts 特征云+VINS odom)+bag_extract_moments.py(四指标时刻对齐,X1img_015950 真轮 4/4 时刻
  提帧验证,帧 116-258KB 全有效)。
- J1.3/J2/J3: **素材不足 5 轮带图轮,不判**(现 2 轮: run_X1img_015950 9.2G+run_X1img2_020706 9.3G)。
  素材到货(STATUS 通告)后 24h 内出数值判读。run_X1img2 待 T3 抢修(.bag.active,断电毁轮)。
- J2 协同位: T2-R1 判决(REJECTED,R3 升主线)已见 6f54ad4,纹理增强对照判读待其 W4 决策点。

## 事故记录（方法论输入）
1. **02:05 锁误删**: E1 测试表直接操作生产锁,用例间隙清场删掉 T3-D0 活锁;按 ps lstart 重建 owner 串
   原子恢复(T3-vsmoke-25236-0159),飞行未损。铁律: 测试必走 SITL_LOCK_FILE 侧锁(v2 已支持)。
2. **02:20 NUC 死机重启**: T1 replay(重载)×T3 带图轮(18G bag 写盘)×E3 删盘三方并发叠加。T1 已自省入账;
   E3 侧教训: 大批量删除避开活跃飞行写盘窗(manifest 纪律增补"查 pgrep 负载再动手")。

## 遗留与移交
- T2 任务书 v4.1 锁指针已核对其头注(09-29 晨增补"锁规范指针"),与 E1 无口径冲突;T1 §3.3/T3 锁章指针同。
- X1 30 轮 throttle 零复发验收: 归后续飞轮自然统计(架构性消除,预期恒绿)。
- vision_inputs 素材池随 T3-D0 批次增长;T4 下一执行者按 vision_materials.md §4 错峰规则切判读。

## J3 sim-to-real 视觉六维基线（2026-09-30, C09 dossier E1→E8 快胜序执行）

**结论**: 六维表已并入 docs/sim2real_runbook.md §6（数字正源=docs/t4_j3_e1e2_evidence.md）;
runbook CF-1 勘误（848×480=能力口径, 驱动实读 infra/depth 均 640×480）+README R6 表 CF-2 分行
（VINS 双目 fx 467.74 vs 387.51, 深度流 454.68 单列）+CF-6 IMU 行核对无冲突, 已随 commit 入库。

- **E1 口径两方锁**: rs_camera_vins.launch（infra 640×480@30/emitter=0）↔ realsense yaml（640×480, fx=387.508, 零畸变）一致, P1 预言成立
- **E2 FOV 行**: sim 68.75°H/54.32°V（1.042sr）vs real 79.10°H/63.54°V（1.368sr）, fx 比 1.2071=迁移尺度一阶 ~+21%; 样张 camera_info 换算法与 color 规格互证 <1°; 帧级极线复核缺（四公开源 infra 双目全阴: 官方样张×3/M2DGR/M3DGR/OpenLORIS 逐一实查）
- **E3 噪声行**: sim 侧 X1img σ̂ 直筛=**0.0 实锤注入前袋**（M4 调和注记 C12-EXP2 步骤 0 裁决读数, 平坦区梯度严格 0=T2-R3 根因图像侧证据）; 实机侧 IR σ̂=数据缺口挂账（color 上界 1.16-3.0 仅边界）; **P25 口径方法论**（patch σ̂ 分布 25 分位抗运动污染, depth 流 6.56→0.044 两数量级实证）入 T3-D0 复验强制口径
- **E7 曝光/模糊行**: sim 曝光常数零假设两侧通过（p_sat=0/γ=1.0/hist 恒 139）; t_exp=8ms 样张实测落账; 模糊行 L=f·v·t_exp/Z 公式链+t_exp 锚, 方向能量 sim 0.200=纹理本底非模糊
- **E6 纹理行**: 对照先行交付（sim 37/帧@640×480 vs 样张 117-150/帧@1080p, 场景类禁跨类比; 方向集中度 sim 2×）; 正源挂账 T3-D0
- **E5 深度行**: 划界后 INIT_DEPTH 占比引 T2-WA1 census（n_init_replace）不另测; depth 流 σ_z 双口径示范; 分区域残差两侧正源挂账
- **E4 FB 残差**: 注入前袋对照边界登记（时序 pool P90=30.7px 运动主导/立体 0.71px, 无 FPN 时时序尾>>立体尾反向）——双峰检验挂账等四件套后袋
- **挂账四项**（禁静默省略）: 实机 IR σ̂+H6（解锁=实机帧/新代位源）; sim σ 送达复验+E4 双峰+E6 正源+深度正源（解锁=T3-D0 四件套后带图袋, 年代门双通道+P25 口径）; 联动待办=T1-F2 位置环架构拍板后入 runbook
- **J1.3/J2 维持挂账**: 素材仍 2 带图轮（1 毁损）; T2-WA 轮无图像流不产素材; 24h 时效红线待素材到货触发
- 工具入库: sitl_sim/analysis/j3_{extract_frames,image_metrics,fb_residual}.py（三 bug 修复记录在案: 双目同 ts 键碰撞/short_of 覆盖/(N,1,2) 点形状 norm）

## J3 补遗：X1img2 双袋验证 + 素材台账更新（2026-09-30 04:50）

- **run_X1img2_020706 已修复可用**（flight.bag 9.9G 完整索引, 147s, 双目各 5340 帧; 此前台账"待 T3 抢修"状态解除）。**素材池=2 完好带图轮**（X1img_015950 4:33 + X1img2_020706 2:27）, J1.3 判读门槛 ≥5 轮仍差 3。
- **σ̂ 直筛双袋交叉验证**: X1img2 P25 口径 σ̂=**0.0**（n=68, pool=6.90 系 goal 型轮运动污染——P25 口径价值再证）; 与 X1img（P25=0.0）一致 → **两袋均裁决为注入前袋**, C09/C12 共用的 C12-EXP2 步骤 0 读数扩展到双袋。
- grad_med P50=0.0 双袋一致（平坦区梯度严格 0）。
- **γ 帧间方法边界登记**: X1img2 γ_pair P90=2.105 系 goal 型轮视角剧变伪影（med_gray 87→178 为内容变化, 非增益变化; p_sat=0 渲染无削顶佐证）——γ 帧间统计仅在近静止段纯净, 曝光常数结论不受影响（X1img 恒 1.0+渲染管线无曝光模型）。
- 证据: vision_inputs/X1img2_j3/（149 帧双目+manifest）; metrics_X1img2_sim.json。

## J-R 批次（2026-10-01 夜, 任务书 v4.0 T4 执行）

- **J-R1 runbook 位置环架构行**: §1 表补行+§6 卡点5闭环（F2 分支 B 裁决, 双 yaml false 同构本地核对,
  凭据 t1_evidence/v7_2026-09-30/F2_closure.md）→ commit 0775211。
- **J-R2 P3 差距决策包**: docs/p3_gap_decision_pack.md（b53324a+勘误 ea68579）——阻断 3（外参实测
  标定/地面 init 纪律/瞬态 W-C2 硬前置）/高 4（慢漂双层/重锚尖峰/EV 启用三选一/FOV fx 迁移）/中 4
  （IR σ̂ 缺口=首飞自产解锁/Allen 重标/yaw 慢漂/INIT_DEPTH）+用户决策 4 问（EV 口径/到位门统计化/
  首飞包络/素材清单）+X7 并入钩（T3 出稿后并入, 责任 T4）。勘误: B3 采信 T1 v8.0 W2 层2改写
  （"EKF2-EV 失稳"命题对象不存在, EV_CTRL=0 实锤）; **runbook §4「EV 失流劣化 w2b z 飙」行机制
  描述待 T1/T2 联合勘误**（T4 标记不代改）。
- **J-R3 素材管线吞吐预演**: docs/t4_jr3_pipeline_dryrun.md（本文档提交链随行）。
  ①排队器 j3_extract_queue.py 入库（df 门 25G+rosbag 双 0 空窗+manifest 断点续跑+串行; 自检
  done/fail/续跑三态实测过）; ②特征重放 j3_replay_features.sh（私有 master 11314, canonical 冻结
  口径=e2_debug_smooth.yaml+devel vins_node）+判读 j3_feature_density.py（offset/density 双模式）
  入库; **袋1 X1img_015950 dry-run 实跑**: features.bag 4.4M（2001 云+3993 odom, 覆盖 207s）,
  108,995 点, 每云点数 P50=45/P90=90/max=154（供给率 0.30@max_cnt=150）, 三区密度=障碍区 40.0%
  465.3 点/m²(面)/1247.1 点/m³(体), 地面带 137.9 点/m², 空域 1573.9 点/m³——**标注 dry-run 非正式
  判读**（素材 2 轮<5 轮门槛, 仅工具/阈值校准）; 分母口径修正=全量外接框被远点污染(139×139m 失真)
  →P1-P99 修剪框为默认。③磁盘预案: 65G 来袭不可整体共存(56G<65G+20G), 滚动管线+分波排程
  （W1 六轮波谷 26G/W2 七轮 21G 贴水位→W2 前必须腾挪）+删除纪律四条+X4 保全范围裁决钩。
  **X1img2 补跑已收口(03:2x)=重放物理性失败**: vins_node 18.2s 段错误(core), 签名=跨域 dt
  26.67s 钳制不可吸收→wait for imu 饿死→segv——Y4 黑名单在重放层可复现实锤, **X1img2 物理性
  禁重放**; 同窗 T2 插桩行复现 WA9 签名(motion2 depth=0.0096, track=2)@T2 采信; J1.3 可重放池
  仍=1 袋, ≥5 轮缺口扩至 4, 押新带图轮。
- **等待池③ J2 阈值口径准备**: docs/t4_j2_threshold_prep.md——参数锚点全 repo 实证（max_cnt=150/
  quality 0.01 硬编码/min_dist=30/F_THRESHOLD=1.0px 系 F-RANSAC 非角点质量/三配置 freq=10 两域
  同口径）+指标 M1-M6 三域划界+产额分位标定协议+文献锚点（二级）。
- **等待池⑤ 六维敏感性分析**: runbook §6.1（1172beb）——逐维量级×余量计算, 先爆排序=噪声(#1,
  0→1.16-3.0σ̂ 六维最大跳变) > 运动模糊-近距(#2, 7.7px 余量 2×) > 深度(#3) > 纹理(#4, 供给率
  0.30 余量 1.5×) > 视场(#5 纪律型) > 曝光(#6 锁曝光即坍缩); 前三维共因=sim 正源缺失, 首飞素材
  自产共同解锁。
- **工具链坑位（本夜实锤, 供后续 T4 执行者）**: ①`set -u` 在 ROS setup.bash source 前会杀脚本
  （setup 内未绑定变量）→先 source 后 set -u; ②rosbag 探测 `pgrep -x` 探不到 python 包装进程、
  `pgrep -f` 会被外层含"rosbag"字样的包装命令自命中毒计数 → 用 `ps -eo comm=|grep -cx rosbag`;
  ③重定向手滑 `>/`（根目录）静默废掉 roscore; ④ssh 后台+管道会让退出码/输出双双失真 → 远端
  落日志文件+REMOTE_RC 显式回传; ⑤非交互 ssh 无 ROS 环境 → bash -c 显式 source。

## W-0 跨线提帧回执（2026-10-01 下午, 任务书 v4.1/v5.0 T4 执行）

- **WC2 两轮全链（提帧→特征重放→三区密度→σ̂ 年代门, 全部 dry-run 口径非正式判读, 2 轮<5 轮门槛）**:
  - 轮1 run_WC2OBS1_030927: manifest=vision_inputs/WC2OBS1_030927_j3/manifest.json（139 帧条目/
    72 主帧, t25.86-402.1s）; features.bag=vision_inputs/jr3_replay_WC2OBS1_030927/features.bag
    （odometry 900+point_cloud 454）; 密度表=vision_inputs/metrics_WC2OBS1_030927_density.json
    （非空云 393/454=86.6% 供给率, 34061 点, 每云点数 p50=97/p90=141/max=156, 覆盖 43.7s; 三区
    obstacle 159.34 点/m³·59.46 点/m²面 | ground 17.45 点/m²(564.61m²) | air 0.67 点/m³(27607m³),
    分母=P1-P99 修剪框默认口径）; metrics=vision_inputs/metrics_WC2OBS1_030927.json。重放 t=71.87s
    复现爆炸（insane states |P|=391 reboot→failure detection, track=66/|Bas|=0.178 前端健康）,
    云止于 ~72s/袋 376s——与 U3R1REP"爆炸在数据里"互证。
  - 轮1R run_WC2OBS1_032005: manifest=vision_inputs/WC2OBS1_032005_j3/manifest.json（73 主帧）;
    features.bag=vision_inputs/jr3_replay_WC2OBS1_032005/features.bag（2,107,784B, odom 2036+非空
    云 609）; 密度表=vision_inputs/metrics_WC2OBS1_032005_density.json（36037 点, 每云点数
    p50=51/p90=128/max=157, 覆盖 102.0s; obstacle 117.11 点/m³·43.70 点/m²面; **ground 0.26 点/m²
    与 air ~0 点/m³ 分母被跑飞段云污染**——P1-P99 修剪框失效（107129.58m²/3.21e8m³ vs 轮1
    564.61m²/27607m³）, 不可直接判读, 工具口径未改如实登记）; metrics=vision_inputs/
    metrics_WC2OBS1_032005.json。重放 [T2fail] t=128.5120（|Bas|=2.772 爆, track=60）→failure
    detection, play 放完全袋 375.7s——轮1R 在线 134.8s 爆的离线复现。
  - **σ̂ 年代门验收步（两袋均 canonical 时代, 预期非零）**: 轮1 d12_sigma_p25 p50=1.02899（n=67,
    p10-p90=1.02447-1.03438）; 轮1R p50=1.02978（n=66, p10-p90=1.02125-1.03403）——两袋均非零=
    噪声注入在, 年代门过, 无「年代门异常」登记。
  - 密度 world-boxes 无既有调用先例: 取 worlds_fix/sitl_north.world 三盒（box_A=4.51,-0.52,0.9+
    size 1,1,1.8 与 j3_feature_density.py docstring 示例一致）, shift 各袋 offset 实测（轮1
    [1.0142,0.9668,0.1012] / 轮1R [1.0094,0.9812,0.1036], 出生点先验 1.01,0.98,0.104 吻合）。
- **X1final_173345 提帧（W-0②, 仅提帧无重放无判读）**: manifest=vision_inputs/X1final_173345_j3/
  manifest.json（140 帧条目, 3 段×12 帧×双目 pairs, t26.24-171.852s, 17.4s done=1 fail=0）;
  帧目录=vision_inputs/X1final_173345_j3（沿用 <run标识>_j3 命名约定）。回执 @T3: 清三袋前置齐备。
- **清三袋执行（同日 17:00 收口, T3 v8.0 单元 2+袋口径 22）**: 实删 run_X1img2_020706（9.3G, 判废
  袋, 定性=本文 §J-R 批次"物理性禁重放"行）、run_X1img_015950（9.2G, 注入前袋, 帧包正源
  features.bag 4.57M 在库 jr3_replay_X1img_015950/）、run_X1final_173345（4.9G, manifest+帧目录
  X1final_173345_j3 实存）——三袋逐条字面路径 rm, 删前逐袋核对证据全过; 删前通告 16:52+5min
  异议窗过（基线 464 行, 窗内新增仅 T2 16:56 R1 收口记录非异议）。**df 47G→70G**（+23.4G 与
  通告一致, ≥65G 目标达成）。磁盘预案波次表回填: W2 前腾挪压力解除——X 线七轮 ≈+35G 落 70G
  底座波谷 ≈35G, 高于 25G 提帧门与 20G 硬水位, §3.5 腾挪降级为后备。删除经磁盘链授权代执行
  （plans/2026-10-01_prompt_disk_chain.md, T4 代 T3）, 处置记录=STATUS 16:52 通告+17:00 收口。
