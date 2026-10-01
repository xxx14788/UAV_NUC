# X 线判读预注册 v1.0（T3 v8.3 单元 2.1；2026-10-02 冻结）

> **预注册声明**：本文件在 X 线任何验收轮起飞前冻结。执行中不得改判据/阈值/脚本参数；
> 若客观需要修改=新版本号（v1.1…）+理由入台账，已飞轮不追溯重判。
> 正源依赖：round_result.sh（场景名正源，e7120e0）+ t3_wa_gate.py --online（判读继承）。
> 凭据栈：vins_node md5=285278cc（起飞前 §0.5 实读记台账；分水岭 10-01 20:35）。

## 1. 轮次位形表与 5/5 计数集

| 轮 | 命令 | world（实际生效） | 到位门 | 计入 5/5 |
|---|---|---|---|---|
| X1' | `vins_smoke.sh --tag X1final` | sitl_world_obstacles（默认） | **0.75** | ✓ |
| X2① | `vins_smoke.sh --tag X2g1 --goal 7 -4 1` | sitl_world_obstacles | 0.75 | ✓ |
| X2③ | `vins_smoke.sh --tag X2g3 --goal 8 -1 1` | sitl_world_obstacles | 0.75 | ✓ |
| X2④ | `vins_smoke.sh --tag X2g4 --world sitl_world_obstacles_v2 --goal 8 -1 1` | sitl_world_obstacles_v2 | 0.75 | **附加对照轮**（全绿要求同判，不入分母） |
| X3② | `vins_smoke.sh --tag X3l2a --goal 7 -4 1 --leg2 1 0 1` | sitl_world_obstacles | 0.75 | ✓ |
| X3⑤ | `vins_smoke.sh --tag X3l2b --goal 7 -4 1 --leg2 0 0 1` | sitl_world_obstacles | 0.75 | ✓ |

- **5/5 计数集 = {X1', X2①, X2③, X3②, X3⑤}**（任务书 v8.3 + K-5 定案口径：五轮不带 --world 全落 obstacles world → 全 0.75 门；J0 恒 0.5 不分场景）。
- X4 打 tag sitl-v0.4 前置：①5/5 全绿 ②T1 跳变落地凭据或重估销案通告（K-2）。允许 1 环境性重试（ENV-FAIL 三签名）。
- tag 命名沿用 --tag 参数（上表）；RESULT 判读以 run 目录 RESULT.txt + wa_gate --online 双源。

## 2. 判据冻结（四指标双口径 + J0 + 出生点对齐 + 场景名到位门）

### 2.1 四指标（正源=round_result.sh，wa_gate 继承不重算）
1. **到位（真值）**：leg1 min < **0.75**（obstacles world）；--leg2 轮 leg2 min 同门合并判；**VINS 帧跳变（J0 锚差 |pre-post|>0.5）→ 到位强制 FAIL**（恒门，不分场景）。双口径：leg1/leg2 (VINS 自报) 同打印（信息项，不入 PASS）。
2. **避障**：truth 全程对 box_A/B/C（+v2 轮 box_D/E）min_dist > **0.349 m**。
3. **poscmd 频率**：≥ **50 Hz**（全程均值，poscmd_hz.txt 交叉）。
4. **auto_disarm**：轮末 armed=False。

### 2.2 J0 修订口径（X1' 验收口径，恒门）
- j0_jump_m（锚差跳变，goal 前 vs 末段锚）< **0.5** —— 一律 FAIL 恒门。
- **J0 修订**（wa_gate online_j0_rev）：`frame_jumps_raw_odom == 0` 且 `frame_jumps_smoothed_odom ≤ 10`。
- j0_jump ≥ 0.5 且 VINS 域健康（零 fail/零 reboot）→ 标 **T1-D1-domain**（不计 5/5，入回挖，受跳变域影响轮 J0 判 FAIL 标 T1-D1 域）。

### 2.3 出生点对齐
- 正源锚点=round_result.sh「goal+5s 窗均值对」（X1_234437 实证：中途锚误判，goal 前锚废弃）。
- 对齐为平移锚（无尺度）；J0 pre-post 锚差=帧稳定性测量。

### 2.4 环境性分口径（ENV-FAIL）
- 三签名：sitl.log「Connection closed by client」/ round 类 log「px4 亡,进程组整组清场」/ EV 目录 ENVDEAD 文件。
- ENV-FAIL 且四指标非全绿 → RESULT=ENV-FAIL：**不计飞行预算、不计连败**；X4 全程允许 1 次环境性重试。

### 2.5 wa_gate --online 调用（参数冻结）
```
python3 analysis/t3_wa_gate.py --online <run_dir>     # 判据器内部默认阈值即本预注册值
```
- xline_pass = four_ok AND j0_jump<0.5 AND vins 域零 fail（存活统计=bag 全跨度）
- json 报 scene/arrive_gate（审计面）；P95 双口径与特征数随附（信息项）。

## 3. 判读流水（每轮，锁窗内）
1. 轮毕即跑 `bash round_result.sh <bag> <gx> <gy> <gz> <world> <evdir> <arr1> <arr2> <hasl2> <l2x> <l2y> <l2z>`（vins_smoke.sh 已内置自动跑，核对参数与上表一致）。
2. `python3 analysis/t3_wa_gate.py --online <run_dir>` → xline_pass 行入台账。
3. --leg2 轮附 `--leg2 锚差漂移` 读数（wa_gate legs 面）。
4. df 检查点：起飞前 >15G、轮毕记录 df。

## 4. 连败 2 轮回挖分支（预写；触发=同型 FAIL×2）

**同型定义**：FAIL 归因同一指标（到位/避障/频率/disarm/J0）且形态签名同类（如均为 j0_jump>0.5、均为 poscmd 不足 50Hz）。

触发后动作序列（不放宽、不换判据）：
1. 冻结第二败轮素材：bag/RESULT/planner.log/px4ctrl.log/arrive_watch 全目录 tar 索引+md5。
2. 跳变型（J0）→ 交 @T1-D1 域回挖（跳变域轮已标 T1-D1-domain 不计 5/5，此处为域外新形态）。
3. poscmd 缺席/频率型 → 跑 t3_r3_planner_domain.py（单元 1 工具）出规划域四门+traj_segments；ego 主节点死活用"新 goal 无反应"判据（同 PR1 手法）。
4. 到位型（真值 min 达标而 VINS 自报不达）→ 分解规划段 vs 执行段误差（对照组表=单元 3 产出）。
5. 复盘输出回挖报告入 docs/，**回挖不改 5/5 计数**（连败照计，除非 ENV-FAIL 签名补证）。

## 5. 已知坑对照（执行时核对）
- vins_smoke 默认 goal=(7,-4,1)/world=obstacles/BUDGET=100——X2③/④ 必须 --goal 显式（防默认吃 7,-4）。
- mavros 50Hz 顶/pkill 自匹配/goal 竞态（2×8s 重发已内置）——勿提前发 goal。
- 判读禁吃 /mavros/local_position（EKF2 融合链）——正源=truth+imu_propagate。
- 降采样/紧凑袋硬链接；Aborted core 按 T3 红线 29 判读法。
- 每轮重放登记 vins_node md5（T4 红线；分水岭 285278cc）。
