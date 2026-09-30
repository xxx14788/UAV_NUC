# T2-W-C3/U2 全库回归（canonical 重放）— T2 执行侧记录（2026-10-01 夜）

> 任务书 v6.0 U2：canonical（gyr_w 修复后）串行重放全部历史失败袋；T2 跑、T3 判。
> **回放域局限声明（红线 11）**：本件结论只入机理账，不作 X 线解锁 gate；最终验收域=在线（v6.0 双口径裁定）。
> T3 判决侧（t3_wa_gate 四轴+W-P 预言勾销+双基线不劣化确认）见双签栏；本表 T2 数据=执行凭据。

## 1. 执行凭据

- canonical 冻结：HEAD `e29d3d3`；config md5/二进制 md5 见 `~/sitl_sim/t2_u2_freeze.txt`（binary 21:05 > src 21:03 现行；gyr_w 0.0001 已含）。
- 队列定义：T3 Y4 DB 驱动 20 袋（`t3_library_forensics_db.json`，污染袋 043355/020706 自动剔除）∩ **图像话题扫描可回放子集 = 6 袋**。14 袋（X1 系全族 7+E2FAIL2+WD1b×2+X1final 101627/104720/105449/172424）无 `vins_cam_*` 话题，VINS 回放物理不可能——历史判读维持 DB 在线原判；对应任务书"X1 系**可回放**袋"限定。
- 执行：`~/sitl_sim/t2_u2_queue.sh`+`t2_u2_resume.sh`（t3_replay.sh 复用，私有 master 11313，单机一路，逐袋 pgrep 自检）；日志 `~/sitl_sim/t2_u2_replay_queue.log`；02:14-02:4x。
- 产出目录：`~/sitl_sim/t3_results/Y4*`（6 个，t3_wa_gate 直接消费格式）。

## 2. 逐袋结果（T2 法证；判决以 T3 gate 为准）

生成：`t2_u2_forensics.py` → `~/sitl_sim/t2_u2_forensics.json`（02:4x）。out_dur=vins_out.bag 录制时长；bgs>0.01=[T2diag] 行任一 Bgs 分量>0.01 的帧数（P-C-4 轴）。

| tag | alive | failure | bas_max | bgs>0.01 帧 | out_dur | [T2diag]行数 |
|---|---|---|---|---|---|---|
| Y4_X1final_173345 | 1 | 1 @38.79s | **2.511** | 0 | 84.6s/146s | 108 |
| Y4_X1img_015950 | 0† | 0 | 0.742 | 0 | 248.2s/276s | 2375 |
| Y4B_CTRL2_route112652 | 1 | 0 | 0.951 | 33/1723 | 177.5s/178s | 1723 |
| Y4B_hover_203248 | 1 | 0 | 1.812 | 19/1319 | 138.4s/138s | 1319 |
| Y4W_t2w5_p1b_shift | 1 | 1（wall 时戳,袋前段） | **4.991** | 4/250 | **32.5s/248s** | 250 |
| Y4W_t2w5_p2_215545 | 1 | 0 | 1.763 | 35/1434 | 150.0s/150s | 1434 |
| Y4W_t2v3_w2b_121141‡ | 1 | 0 | 2.250 | 17/956 | 100.8s/103s | 956 |

† 收尾死亡伪影：odom 连续至 275.4/276s，末帧健康（track=39），零 failure——非中途崩溃。
‡ 第 7 袋为 T2 补录：P-C-4 预言引用的 W2B 袋不在 Y4W glob（只匹配 t2w5_*），按穷尽纪律补跑；tag 命名随 Y4W 族，gate 可直接消费。

## 3. 机理账要点（T2 侧）

1. **袋 1 X1final_173345**：历史 FAIL-数值溢出在 canonical 下 **failure 复现 @bag 38.8s**，Bas_max 2.511（历史在线值 2.61@t=35，T3 11:04 STATUS——回放域同刻同幅复现，互证）；VINS 自动 reboot 后存活至袋末（alive=1，重启续命型；odom 重启后稀疏=84.6s 覆盖）。
2. **袋 2 X1img_015950**：零 failure，odom 连续至 275.4/276s（4763 帧≈19Hz），Bas_max 0.742 全场最驯——**历史数值溢出未再致死**；alive=0 为收尾伪影（†）。
3. **双基线**：均存活零 failure（CTRL2 Bas 0.951/hover 1.812）——W-A 基线不回退第一信号（ATE 轴不劣化确认归 T3）。
4. **W2 p1b_shift：canonical 下显形新形态**——Bas_max 4.991（全场最大）+failure（袋前段）→重初始化失败→**僵尸存活**（进程活、odom 仅 32.5s/248s 覆盖=13%）。W2 毒域（t2b 跨域史）在 canonical 裸栈下不可自愈，防线开关族的存在理由+1；按红线 12 默认关、在线推荐形态不含 W2 场景，此形态只入机理账。
5. **W2B 补录**：alive 零 failure，Bas 2.25，bgs>0.01 帧 1.8%（956 帧中 17）——P-C-4 的"11%（107 帧）"基线为旧栈旧口径，canonical 下该轴大幅走低，勾销判读归 T3。
6. **teardown core-dump 形态**（袋 1/W2B 收尾 abort after-check）：与 R5REP Bus error（中途崩溃）不同类，录制先于 abort 完成，不立案。
7. **14 无图袋排除凭据**：`rosbag info` 逐袋扫描（img=0）——X1 系全族/E2FAIL2/WD1b×2/X1final 无图 4 袋；物理不可回放，历史判读维持 DB 在线原判。

## 4. 双签栏

| 方 | 判决摘要 | 签名时间 |
|---|---|---|
| T2（执行侧） | 6 袋产出完整、凭据链齐、机理账如上；回放域结论不入 gate | 2026-10-01 夜（本文件） |
| T3（判决侧） | t3_wa_gate 四轴批量判决+W-P1..P7 勾销+双基线不劣化确认；**待签** | — |
