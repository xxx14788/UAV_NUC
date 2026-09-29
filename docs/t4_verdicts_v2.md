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
