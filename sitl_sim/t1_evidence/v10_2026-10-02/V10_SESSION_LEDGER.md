# T1 v10.1 会话台账（2026-10-02 00:55-03:1x；GLM5.3 会话）
## 首件
- push 债 3 件（d7c28e4/7d80ff5/fb3b631）+WAN 瘫（ping 8.8.8.8 Network unreachable）挂账，会话内 3 次重试未恢复；会话产出 6 commit 追加同队列（合计 12 件待推，含他线）
- EXP-2 周检：无退化再现（最近两轮 boot 探针=master 已死删失值，fd13/thr9 健康）；watcher 因 NUC 23:20 重启死，重部署 pid 120119（01:03 start 入账；教训：ssh 常驻部署须 ssh -f，-n+& 会不脱离）
## 单元战果（commit 链）
| 单元 | commit | 战果 |
|---|---|---|
| U1 EV 行签认 | ea0583c | 与 e2061e4 无矛盾+正向支持；T4 C-3 半闭 |
| U2 跳变分析面 | a979382 | 四型分法（H-S1 急性 Bgs 领先/H-S2 慢性 55-64s 载体窗跨证据收敛/H-S3 帧跳/H-S4 盲漂）+H-J4 胜出+D1 可救性签名表+A.4 双分流口径；栈勘误（任务书 E4-R2=285278cc 误标，实为 cf0384）；Bgs 领先 3/3；gate 全盲四轮实证；§6 探针盲区（E2uls 对匀漂盲） |
| U3+U4 研究+源码读 | a03a537 | C-7 翻案：ev_hpos 非 never-scheduled（22s 活窗被 33.2s 爆走毒化熄灭，cs_ev_pos 7.78%）；ev_vel 恒 0 根因=vins_to_mavros 只发 vision_pose 丢 twist（vel NaN frac=1.0 实证）；E-5a 链升级臂（odometry/out）设计并入矩阵；上游 Fast-Drone-250 #74/#31 零回复=上游无 odom 毒化处理（D2 门正确）；E4 报告勘误已注 |
| U5a 判据预注册 | a48e5cf | J1-J6 锁定（J6=Bgs 双分流并入；J2 分臂预期 L-pose cs_ev_vel=0/L-odom>0）；矩阵面四 E-5a 臂并入=7 轮+回归；R2F 条件预期预注册 |
| U6 P1-1b | 059978f | 管线跑通；U3PH compact 定案不可用（fail 轮 257 事件/漂 678cm/min）；探针盲区发现回补 U2 |
| U9⑥ F6 取证 | 5ea2358 | 35 轮零病理性中段 gap；两启动模板登记；F5 修复事后验证；G1 日志面无实例 |
| U9① w2b 调研 | b9ce4c3 | 七候选（M1 谱分析 2608.10623 最适配/M4 cost-gate 与 T2 收敛/M5 自有 Bgs/M7 悬停一致性）；双路组合建议 |
## 挂起登记
- U5b E-4 复排：T2-R2F 未开跑（01:22 R3 判决刚出），W-A 维持
- U7 F3 接线：与 U5 同批排窗+P12 三不硬接理由仍立，等窗
- U6 预算袋：U3PH 排除后袋源仍缺（复排轮/T2 验证轮 hover）
## 跨线交互
- @T2：U2 交付 t1_u2_jump_typology_for_r2f.md（其 R2F 判读引用 §3 口径）；T2-R3 cost×10@t50 与我 U2 ic 同拍+107% 同向收敛；T2 @T1 移交件=px4ctrl 无健康源 failsafe 缺口（受害者非元凶）——登记待办（下窗与 D2 门族合并评审）
- @T4：C-3 半闭回执（U1）
