# X 线操作卡 v1.0（T3 v8.3 单元 2.4；一页/轮，X 线冲刺窗专用）

> 前提：X 线已解锁（T2 U4 通告点名 @T3，STATUS 尾查验）。判据冻结=docs/xline_prereg_v1.md。
> runbook v7.4-R2 权威；本卡=其执行序列化。凭据栈分水岭 285278cc。

## 0. 每轮通用前置（P0，缺一不飞）
```
1. tail -5 ~/sitl_sim/STATUS.md            # T2/T4 无未决异议指向本线
2. df -h / | tail -1                       # >15G 硬线；<20G 禁新轮
3. md5sum ~/catkin_ws/devel/lib/vins/vins_node   # ==285278cc 记台账
4. bash ~/sitl_sim/sitl_lock.sh acquire T3-X4 <tag>   # 锁 v2；权序 T3-X4 最高
5. pgrep -af 'gzserver|px4|rosmaster|vins|ego|px4ctrl' | head  # 清场核验（残留=死锁接管流程）
6. cd ~/sitl_sim && git -C ~/catkin_ws status --short | head -3  # 树净（或仅本线产物）
```

## 1. 发射（按位形查 prereg §1 表；防默认吃 7,-4）
```
bash ~/sitl_sim/vins_smoke.sh --tag <TAG> [--goal X Y Z] [--leg2 X Y Z] [--world W] 
# 轮中盯：EV/sitl.log（ENV 签名）、arrive_watch*.txt、BUDGET 倒计时
```

## 2. 轮毕判读流水（顺序执行，产物三件）
```
1. cat  $EV/RESULT.txt | head -12           # vins_smoke 内置 round_result 已跑
2. python3 ~/catkin_ws/sitl_sim/analysis/t3_wa_gate.py --online $EV | tee $EV/wa_online.txt
3. df -h / | tail -1                        # 记入台账行
```
台账行格式（t3_experiments.md X 线节）：
`| <tag> | <四指标位 0101> | arrive_min=… | j0=… fj=…/… | vins域=… | df=…G | md5=285278cc |`

## 3. 分支处置
- **ENV-FAIL**（三签名）：记 ENVDEAD 证据 → 允许 1 次重试（同位形）→ 重试轮入 5/5 分母。
- **j0_jump≥0.5 且 vins 域健康**：标 `T1-D1-domain`，不计 5/5，登回挖清单 @T1。
- **同型 FAIL×2**：触发 prereg §4 回挖分支（冻结素材→分型→工具链→报告），不放宽不重跑。
- **poscmd 0 Hz / traj_id 冻结**：跑 t3_r3_planner_domain.py 出四门+段表（planner 域签名）。

## 4. X4 打 tag sitl-v0.4 检查单（5/5 达成后）
```
1. 台账 X 线节五轮行齐+附件（RESULT/wa_online/flight.bag）在档
2. tail STATUS：T2 尾无未决异议（时戳记录）
3. T1 跳变前置：落地凭据或重估销案通告（K-2 二者其一，时戳记录）
4. git status 净 → git tag sitl-v0.4 && git push UAV_NUC sitl-v0.4
5. STATUS 通告 @全体（tag 凭据+五轮一行表）
```

## 5. X5 窗口（X4 全绿后；设计稿=xline_x5_grid_design_v1.md）
- 优先级 1 起（E/S×8m×两 world）；紧凑模式；每 6 轮查 df；汇总 xline_x5_passmap.csv。

## 6. 中断恢复
- 轮中死亡：Aborted core 按 T3 红线 29 判读（不急判 ENV）；bag 保全；锁不释放直到判读完。
- NUC 不可达：nuc-ts 路径（Tailscale）+ STATUS 远端 date 为准；重连后先查锁与半开轮。

## 追加走查注记（2026-10-03；池件 P-B：X2④ obstacles_v2 适配面）

- **代码路径走查（三件全绿）**：①round_result.sh `world.endswith("_v2")` → BOX 增 box_D(6.4,-2.0,z0-2.8)
  /box_E(6.4,0.5,z0-2.8)，避障 min 距离把 D/E 计入 ✓；②场景门钥匙 `obstacles in world` →
  sitl_world_obstacles_v2 判 obstacles 系 0.75 门（round_result GATE 行与 wa_gate scene_of_run 双侧一致）✓；
  ③vins_smoke.sh --world 透传 → round.log "SITL up (world)" 行为场景正源 ✓（prereg §5 已列防默认吃障碍 world 坑）。
- **执行时核对项（并入每轮 P0 六查）**：X2④ 轮毕核对 RESULT.txt 避障行 min_dist 计及 D/E
  （v2 world 下若 min_dist>3m 量级=box 集未生效，疑 D/E 坐标未加载，停轮排查）；round.log world 行逐字核对
  sitl_world_obstacles_v2（防 _v2 拼写滑落到默认 world）。

## 6. X4 5/5 判定 v1.1 集成设计（2026-10-03 池件 P-E；解锁窗零拖拽预备；纸面设计未实施）

- **现状**：x4judge（t3_legs_rescan.py x4judge）按 runbook §3 判据表（A1/A2/B/C/D/J0/P0）出 5/5；
  其 P0/VINS 域面=「零 fail 零 reboot」旧口径，不含受控分层。
- **v1.1 集成点（设计）**：x4judge 的逐轮 P0 判定改为读 wa_gate_online.json 两键——
  ①xline.counting_pass（=零 fail ∪ 受控失败，prereg v1.1 §2.6 计数语义）②controlled.state
  （五态入表列，PASS-CONTROLLED 轮在 5/5 表标受控注记）；其余判列（到位/避障/频率/disarm/J0 锚差）
  x4judge 与 wa_gate 同源继承不重算。
- **实施时点**：T2 U4 通告后、X1prime 首轮起飞前（判读链版本冻结点）；实施=改 x4judge 读 JSON 面
（判据值零变动，属接线非判据改动）+自测（五合成夹具=SYN_CTRL 受控态×5 的模板验证）。
- **回退面**：若 U4 通告的栈号≠t2gates 系（L1 触发行不存在），受控路径自动不适用（prereg seam-4），
  x4judge 退化为 v1.0 等价行为（counting_pass=xline_pass），零额外分支。

## 7. X6 并账预备清单（2026-10-03 02:3x；池件 P-G；X4 全绿后执行面的零拖拽预备）

README §3（参数差异账）将增/核行：
1. **受控分层口径行**（新）：X 线验收口径=「零 fail ∪ 受控失败」计入 5/5（用户 10-02 裁定②）；
   判读链=prereg v1.1+wa_gate ac1df603（受控五态+PASS-CONTROLLED 计数态）；冻结型边界=爆窗未触发
   且无恢复证据=未受控 FAIL（§2.6-e）。
2. **X 线栈号行**（新，槽=T2 U4 定稿）：lib ____+vins_node ____ 双 md5（分水岭 285278cc→U4 定稿值）。
3. 既有行核对（零改动预期）：gyr_w 0.0001 行/FOCAL 467.7427 行/t2_cost_gate 族行/t2_min_disparity
   FM-③ 撤出行——X4 轮起飞前逐行与实盘 diff 核对（防静默漂移）。
4. **git 干净面**：X4 打 tag 前工作树须净——当前在挂的他人 WIP（sitl_sim/analysis/wa_scene_contrast.py/
   t1_evidence e2_debug_replay.log/t1_g2_exp2_watch.sh/VINS-Fusion estimator.{cpp,h}）@各持线清账。
5. rviz 截图→vision_inputs/（口径同 T4 素材面）；X7 figs 全链再生凭据（--csv+--runs-glob 命令行入 §9）。

- **P-M 对齐核对结论（2026-10-03 02:4x）**：X7 §3 表列 ↔ wa_gate CSV 列逐项对齐——
  四指标=CSV `four`（斜线串）；到位双口径=RESULT.txt 行（CSV 不带，X7 表从 RESULT.txt/forensics 取）；
  p95=RESULT.txt 跟踪行；特征数=CSV `track_med`；锚差漂移=forensics `end_state`（legs 面，CSV `t_star`
  为形态时点非锚差——X7 表该列数据源写 forensics/legs_rescan 勿取 CSV `t_star` 防错位）；
  fj_raw/smj=CSV 同名列 ✓；判决=CSV `verdict`（v1.1 增 PASS-CONTROLLED 态入计数）+
  `controlled_state`（在 wa_gate_online.json，CSV 无此列——X7 表受控列从 JSON 取，勿在 CSV 找）。
  列错位风险=1 处（t_star≠锚差漂移），已在本条钉死。

## 8. X 线冲刺序列沙盘（2026-10-03 02:4x；池件 P-J；解锁窗零拖拽终页；判据=prereg v1.1，操作=§1-4）

解锁触发=T2 U4 点名 @T3（STATUS）→ 首轮起飞前四查：①栈号双 md5 实读填 prereg 槽+台账 ②df>15G（起飞门）
③T2 STATUS 尾无未决异议 ④selftest 三格绿（判读链健康证明，输出存档）。

| 序 | 轮 | 命令要点 | 锁 | 判读（轮毕即跑） | 特殊点 |
|---|---|---|---|---|---|
| 1 | X1prime | `vins_smoke.sh --tag X1final` | T3-X4 级 | round_result 自动+wa_gate --online+figs | 首轮定标带图体积（25-45G 预算修正） |
| 2 | X2① | `--tag X2g1 --goal 7 -4 1` | 续 | 同上+受控态登记 | goal 显式（防默认吃） |
| 3 | X2③ | `--tag X2g3 --goal 8 -1 1` | 续 | 同上 | — |
| 4 | X2④ | `--tag X2g4 --world sitl_world_obstacles_v2 --goal 8 -1 1` | 续 | 同上+box_D/E 核对（opcard §5） | 附加对照轮不入分母 |
| 5 | X3② | `--tag X3l2a --goal 7 -4 1 --leg2 1 0 1` | 续 | +legs 面+锚差漂移（prereg §7 互操作） | 两段式 |
| 6 | X3⑤ | `--tag X3l2b --goal 7 -4 1 --leg2 0 0 1` | 续 | 同上 | — |
| 7 | X4 | 五连飞=上表 5 计数轮位形复跑（或按 U4 口径修正位形） | T3-X4 | x4judge v1.1 集成（opcard §6）+5/5 表 | 打 tag 前五查=opcard §4 |

节律纪律：每轮间 pgrep CLEAN+锁活性；df 每轮记录；ENV-FAIL→1 次重试（同位形）；连败 2 同型→prereg §4
回挖分支（不放宽）；T1-D1 域轮（j0≥0.5 且 vins 健康）→不计 5/5 入回挖；受控轮→PASS-CONTROLLED 计数+
回挖查未受控分量。判读产物三件/轮（RESULT.txt/wa_gate_online.json/forensics）+受控态入台账行。

### 8.1 U4 通告消费检查单（池件 P-Q；解锁瞬间按序执行，全部满足才飞 X1prime）

1. **通告面核对**：T2 STATUS 行含 U4 字样+点名 @T3+栈号双 md5（lib+vins_node）；无栈号=向 T2 索要（prereg 槽必填）。
2. **栈号一致性**：若 U4 栈=lib 5dde4d7e 系（t2gates/A1 修复栈）→ 受控层按 v1.2 全量适用；若栈≠该系（L1 触发行不存在）→ prereg seam-4 自动降级（受控路径不适用，零 fail 或 FAIL 二选一），**不改判读器**。
3. **栈号填槽**：prereg v1 头部栈号槽填 U4 值+台账登记（判据冻结时点=此刻）。
4. **判读链健康证明**：`t3_wa_gate.py --online --selftest` 三格绿（输出存档 run 前）+ 版本=4cb6acc7 核对（runbook §9.1 表）。
5. **x4judge v1.1 接线实施**（opcard §6 设计兑现：读 counting_pass/controlled.state JSON 面）+ SYN_CTRL×5 模板自测。
6. **df 门**：>15G 起飞门实测（<20G 禁新轮）；当前 51G=通过面。
7. **T2 STATUS 尾无未决异议**（尤其对我 040932 回执的 27.2m 对账若有回应先消化）。
8. **锁序**：sitl_lock v2 acquire T3-X4（权序最高）+ STATUS 预告。

### 8.2 受控层判读速查卡（池件 P-O；判读现场一页；正源=prereg v1.1+v1.2 修正）

```
五态速判（wa_gate --online 的 controlled.state）:
  clean                 零触发零 faildet → 正常 PASS/FAIL 流程
  controlled            触发+起点窗内+恢复双证 → PASS-CONTROLLED 计入 5/5
  triggered-no-recovery 触发但恢复无证（或迟触发>onset+10s）→ 未受控 FAIL
  uncontrolled-fail     无触发+faildet>0（或帧跳） → 未受控 FAIL
  log-missing           simvins.log 缺 → 触发面不可判（四指标/J0/vins 层照判）

controlled 四查（v1.2 冻结值）:
  L1  触发行 "cost gate: streak=N over Mx ... reboot"（fires_n≥1）
  L1b t_fire ≤ t_onset+10s（onset=首帧跳|ΔP|>0.5 或 出生对齐误差>10m，取更早）
  L2a [t_fire+10s, +20s] 窗 odometry（求解器流，非 imu_propagate）≥50 条
  L2b [t_fire+10s, 轮末] 恢复段自对齐（段首锚）误差 p95 ≤0.5m
  附: 毒窗=[min(onset,fire)-1, fire+10] 窗内帧跳=对号豁免；窗外必须 0；smj≤10 全程

不豁免面（恒门）: J0 锚差 0.5 / 到位场景门 0.75|0.5 / 避障 / poscmd 50Hz / disarm / ENV
豁免面（仅两处）: vins 域 fail 计数 + J0 修订 raw==0 的毒窗分账
反例锚: SYN_LATE（迟 50s 触发）必须 triggered-no-recovery；A3（触发无恢复）必须 triggered-no-recovery
正例锚: R5（onset 98.69/fire 104.5/复流 99/p95 0.229）= controlled；SYN_CTRL = PASS-CONTROLLED
版本: 判读器 4cb6acc7（v1.2）；每改一版 → selftest 三格+全 SYN 电池+历史 re-regression
```

### 8.3 X 线首轮复盘模板（池件 P-N；X1prime 轮毕即填；防复盘面遗漏）

```
X1prime 首轮复盘（run_<TAG>_<ts>；栈=lib ____/node ____；df 前__G后__G）
[A] 判读面: verdict=____ controlled=____ four=__/1/1/__ j0jump=____m fj_raw/smj=__/__
    vins 域: reboot=__ gaps=__ bas_pk=____ bgs_pk=____ track_med=____
    到位双口径: truth=____m vins自报=____m | 规划段 poscmd→goal=____m（planner 有罪面判）
[B] 带图定标: bag 体积=__G（X4 预算 25-45G 修正值=__G/轮×5）
[C] 新形态登记（有则展开）: 触发窗故事=（onset/fire/复流/p95 四点）/ 未拦截故事=（首证/终态）
[D] 与 prereg §6 样本案卷的对表: 新样本属何态=____（受控正样本池扩充?）
[E] 连败计数: 同型 FAIL 连败=__（2 即触发回挖分支 §4）
[F] 回挖件（触发性）: 毒窗外帧跳清单=/触发前中毒预窗差=____s/reboot 后再 init 归因=
[G] 台账行+STATUS 回执时戳=____ | X4 打 tag 前置余量: 5/5 进度 _/5 | K-2(T1 跳变)=状态
```
