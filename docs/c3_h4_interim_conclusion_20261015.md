# H4 修复中期结论（B5·阶段 B 平台修复毕移交件）

> 执行册 §二。上游证据链：B2_B3_彩排判决书.md → B4_验证批判决书.md（git 7f6ad7f，docs/c3_b4_verdict_20261015.md）。

## 一、起飞彩票发生率前后对照（一律 Wilson 95% 区间 + N）

| 面 | 样本 | 发生率 | Wilson 95% 区间 | 注 |
|----|------|--------|-----------------|-----|
| 前（修复前） | 彩排 PRE 臂 3 轮 | 1/3（P2） | [6.1%, 79.2%] | P1/P3 干净（th@8s 0.714/0.714，z≤1.01） |
| 前（合并） | PRE 3 + 在册 221911 族 1 | 2/4 | [15.0%, 85.0%] | **小样本如实注记**：区间宽，仅作方向性前锚 |
| 后（修复后） | B4 批起飞面 8 轮 | **0/8** | **[0, 32.4%]**（z=1.96；禁绝对零表述） | 起飞窗证据计（thrust/z），非 RESULT 域 |
| 后（附加） | +2 轮 60s 悬停轮 | 0/10 | [0, 27.8%] | 附加面，非主判据样本 |

**结论**：H4 修复后起飞面 8/8 干净（三判据全绿：max_win 0.764–0.767≤0.82、z_peak_win 0.775–0.957≤1.5m、th@8s 0.714–0.719 与彩排 G 臂同带+零饱和），彩票形态在 B4 批零复现。前锚（P2 th@8s 0.9908/饱和 38.6s/z 12.28m；221911 同型 z 66.5m）与后锚悬停带无重叠——分叉消失可复现。

## 二、thrust 证据回链

- B4 判决书 §三（重抽表+三判据）＝主证据正本；重抽证书=`h4_validation/thrust_run_C3V*.json+_curve.csv`（8/8 ulg md5 互异门过，`reextract_summary.json` 在案）。
- 彩排前后对照=`h4_rehearsal/C3B2{P,F,G}*.json`（P2 暴走前锚 / G1-G3 修复后 3/3 绿 / F1-F3 健康透明性）。

## 三、J2/慢漂残留注记（域归阶段 C，非 H4 域）

- 导航面 0/8（暴走 3：VE1/VE4/VNE1 路程 62–72m；停滞 5），全部属 J2 贴箱配对塌陷/跳变/慢漂族——阶段 C 治理对象（C-1 慢漂对齐+C-2 world v7 富特征+C-3 调参）。
- j0d 帧级净轮带 6/8；超带 3（VE4 56.38/VNE1 0.662 边际/VNE4 1.737）均为导航段跳变族。
- VNE4 z 域崩落（odom z −42.1m）与 VNE3 z −26.2m：z 分量独立账面挂 C-3 慢漂/时戳域治理。

## 四、抽取器 bug 事件记录（certify 单源复制）

- **现象**：B4 批 8 轮 thrust JSON 逐位同值（.45s 曲线 md5 全同 3c92b08e）。
- **根因**：h4_validation_batch.sh L59 `ls -t rootfs/log/*/*.ulg | head -1` 在"8 轮跑完后统一 certify"流程下恒取最新 ulg（=VNE4 会话），单源复制到全部轮。
- **次生伪影**：日志尾聚合行 `lottery_family=8/8` = 单源复制 + 45s 窗混入导航段饱和（eject_flag 为 45s 参考族）双重伪影，作废禁引用。
- **修复**：轮末快照参数化（/tmp/c3_ulg_\<tag\>.txt）+certify 读快照+ulg 拷贝落轮目录+summary 前置 md5 源指纹门（红线⑪制度化对策）；修复版 e06ffa8b。
- **重抽验证**：8/8 ulg md5 互异（GATE-1），映射时差 +15~16s 恒定单调一致；原伪影存档 `h4_validation/invalid_single_source_20261015/`。

## 五、移交四件物料（阶段 C 绑定件）

1. **px4ctrl 指纹全串**：`59d84e4e46e4f8a5753e044c96702bbd`（devel/.private 与 devel 双位一致；源码备份=px4ctrl_prefix_backup_20261015/；C 期冻结红线②）。
2. **PX4 param 快照**：基线三件（v6 ulg 提取：FULL e0093708 / prefix 0b0ba9c9 / neglist 6f4537f8，已在仓 docs/c3_px4_param_snapshots_20261015/）+ **B4 批新提取三件**（px4_param_snapshot_{FULL,prefix,negativelist}_b4_20261015.txt，战役目录；8 轮 870 参数，核心域 MC_/MPC_/EKF2_/COM_ARM/NAV_ 跨轮零差异，32 处差异均为会话噪声：UUID/时间戳/CAL_MAG 微差）。
3. **生效参数变更表**（yaml `auto_takeoff_land` 域，5 参数）：

| 参数 | 旧值（off） | 新值 | 机理假设 | 证据轮 |
|------|-------------|------|----------|--------|
| takeoff_thrust_cap | 0 | **0.80** | F1：起飞爬升 collective 帽，断"Kp2*dz 积累→0.93-1.0 饱和×倾斜→弹道弹射"链 | 彩排 G 臂 3/3 + B4 8/8 |
| takeoff_tilt_max_deg | -1 | **20.0** | F2：期望加速度 xy 缩放限角（thrust 不变性纯函数），断倾斜分量 | 彩排 G 臂 + B4 |
| takeoff_cap_release_z | 0 | **0.30** | F1/F2 释放高度（odom_z−锚>0.30 后解帽，健康路径透明） | 彩排 F 臂健康透明性（峰 0.767 未触帽） |
| takeoff_att_gate_deg | -1 | **45.0** | F3：实际倾角超门→进入改平域（回炉增补，预注册 §11 先于代码） | 彩排 F3 首判 FAIL→回炉后 G3 绿 |
| takeoff_gated_thrust | 0 | **0.40** | F3：改平域推力帽（capped-thrust-into-tilted-body 侧向力 0.80×sin70°≈0.75g 翻滚教训） | 同上 |

4. **修复轮 forensics 指针**：彩排=`vins_smoke_runs/run_C3B2{P,F,G}*/`（bag+RESULT+ulg）；B4 批=`run_C3V{E,NE}1-4_*/`（含 VNE3/VNE4 forensics/ + j0_decomp + goal_pollution_watch.jsonl）；悬停收口轮=`run_C3B4HOV{,2}_*/`；判决书三处（本地 t1/2026-10-15_③C终局/ + 战役目录 + 仓 docs）。

——落盘：战役目录 + 仓 docs/c3_h4_interim_conclusion_20261015.md；git 逐件提交。
