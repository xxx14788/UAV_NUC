# C.1 定案文书 — VRFY1 -nan 交互链（组件级）+ 三歧判决

**T2 v9.8 单元 1 | 2026-10-06 | 素材: run_VRFY1_023908（gates 臂 loss=1∧cauchy=0.00, boot-2, never-flew FAIL）**
对齐件: T1 boot_diff_report.md（D-1006-T1-09, t1_evidence/v11_7_2026-10-05/）——本文书与其 §5 机理链独立推导一致,并向下深挖三层（§3 交互环/§4 假触发代数/§5 放行门盲区）。

## 0. 口径

- 求解时间线 = simvins.log [T2slv] 2006 帧（phase 0=INITIAL 111 / phase 1=NON_LINEAR 1895）+ [T2OPT] post-solve 111。
- **"-nan×1066"口径勘定 = [T2slv] 含 -nan 955（phase1 844 + phase0 111）+ [T2OPT] -nan 111 = 1066**；两形态分解: `iters=1 term=0`×1066（NaN 求解,ceres 第一步即停）/ `iters=0 term=2`×1051（**FAILURE,0 迭代,init_cost=-1**）。
- gates 键行为 = [T2gate] 3157 帧（tri/rej/xrej/ir_st/ir_m2）; cost 门 = "cost gate: streak" WARN 110 次; guard 恢复 = [T2RESUME] 链; ULS 捕获 = [E2uls]×239。
- 对照轮: VRG1（guard 臂 loss=0,四指标全绿）/ RA13/14（gates+cauchy=4.00, boot-0, T2fail=0）。

## 1. 时间线骨架（量化）

```
t=0     init begins（wall 1791225567.6）
t=10.11 窗口满(fc=10) → T2SNAP pre AIF: Vs/Ps sane（0.004-0.03/0.0003-0.003）
        → solveGyroscopeBias → 前置 bias 门过(Bgs=0.0017 sane)
        → INITIAL 求解 init_cost=-nan (T2OPT 行377) → 后置门(仅查状态有限性)过
        → "Initialization finish!" → NON_LINEAR
t=13.81 第1次 cost gate reboot（此后 init→reboot gap p50=1.64s, min=0.10s, max=5.97s）
t=10.1~215 全程循环: init_finish×111 - 1(初次) = cost_reboot×110 + 存活尾段
轮尾    never-flew FAIL（truth z=0.1045）; odom 6.0Hz n1301; prop 断流 5.5s; 帧跳 odom 4×>0.5m 峰1.771m(T1 探针)
```

## 2. 深度/特征面非判别面（对照排除）

| 面 | VRFY1 | VRG1(干净) | 判定 |
|---|---|---|---|
| [T2depth] init_neg 率 | 26539/74286=35.7% | 5434/19058=28.5% | 同量级,静止机运动三角化固有病态 |
| [T2xcross] rel p50/p90 | 0.900/0.998 | 0.777/0.997 | 同量级 |
| [T2gate] rej/xrej | 全程 0 | 全程 0 | 非判别面 |

**staged 键全程哑火**: staged=1 仅在 NON_LINEAR∧过 80s grace 窗激活(estimator.cpp:589-591),而本轮 init→reboot gap p50=1.64s,NON_LINEAR 段从未活到 80s → t2_dg_on 恒 false → rej=0。防线在本轮形态下结构性失效。

## 3. 交互链五环（组件级定位）

**环1 毒配置（根因）**: 臂装载 sed `t2_cauchy_delta: 4.0→0.0`(arm_xline v1,静默无守卫) × `t2_vision_loss:1` 保留 → estimator.cpp:1337-1339 `CauchyLoss(T2_CAUCHY_DELTA/1.5)=CauchyLoss(0)` → **ρ(s)=0²·log(1+s/0²)=0·∞=NaN(IEEE)**,每个视觉因子每次 Evaluate 注入 NaN。（T1 §5 同源;此处补充:**该 loss 同时进入 preMarginalize 的 prior 固化**——环3 的污染源。）

**环2 INITIAL 100% -nan 且 100% 放行**: 111/111 次 INITIAL 求解 init_cost=-nan,iters=1 term=0(ceres 遇 NaN cost 第一步停,**状态向量不被更新而保持 sane**——这就是后置门全放行的原因); 后置门(estimator.cpp:705-717)只查 Ps/Vs/Rs allFinite∧幅值,**不查 summary cost/迭代健康状况** → 111/111 放行进 NON_LINEAR。对照: VRG1 同位置 init_cost=11115.9→495.2 iters=9(健康)。

**环3 marg prior 污染→FAILURE 帧**: 首批 NON_LINEAR 帧求解后 marginalization 固化 prior 时,视觉因子的 loss 修正 jacobian(NaN)进 prior 数据 → 后续帧 prior 的 Evaluate 返回 non-finite → ceres 直接 FAILURE(**iters=0 term=2, init_cost=-1 未填, 1051 帧**)并 dump "Error in evaluating the ResidualBlock"(**1051 次,块形 13/14 blocks×76/82 residuals=marg prior**,与 -1 帧 1051=1051 一一对应)。**两种死法交替**: NaN 求解帧(1066)与 FAILURE 帧(1051)。

**环4 cost gate 假触发（反直觉核心）**: NaN 比较恒 false → `-nan>10×median` 使 **streak 清零**(NaN 帧不喂 streak); 喂 streak 的是 **-1 帧**: t2_cost_hist 全为 -1/-nan 时 **median=-1,判据 `-1 > 10×(-1)=-10` 恒真** → 连续 5 个 FAILURE 帧即触发 reboot。实测 reboot 前序列: `N N N N N -1 -1 -1 -1 -1` 型(连续 5×-1)或全 -1 型,110/110 全部此形态。**cost gate 的设计意图(cost 暴涨 10x)在退化输入下变成"连续 5 次求解失败"计数器**——设计者未考虑 median 退化代数。

**环5 reboot 风暴自持**: reboot(clearState+setParameter) → gyro 重标定(119 次 WARN) → 窗口重填(~2-3s,11帧) → INITIAL 又环2 → 循环 110 次; guard 侧 [T2RESUME] 恢复链(gap 1.9-63s,dP 0.08-0.56m)持续工作但救不了求解器层; odometry 饥饿 6Hz(仅 NON_LINEAR 段发布)+帧跳(T1 探针 odom 4×0.5m/峰1.771 vs prop 全净)。

## 4. 任务书三歧判决

| 假说 | 判决 | 证据 |
|---|---|---|
| ① staged 拒→窗口特征饥饿→求解退化→-nan | **否** | rej=0 全程(staged 哑火,§2); tri 108-155 无饥饿; 深度面与干净轮同脏 |
| ② cost 触发→reboot→guard delta 补偿与重 init 竞态 | **因果倒置** | cost 触发是环4 假触发(果); guard[T2RESUME]与重 init 无竞态证据(恢复链独立工作); reboot 循环由环2 放行+环3 污染自持 |
| ③ cauchy 缺失→视觉残差厚尾→数值链 | **否(反向)** | cauchy 非缺失而是 **delta=0**: CauchyLoss(0) 直接 NaN,不经厚尾/数值放大路径; RA13/14 cauchy=4.00 干净证明 cauchy 本身无害 |
| **④(实因) 毒配置半键 loss=1∧cauchy=0** | **定案** | 环1-5 全链量化; T1 §6 绑定律: 风暴⇔loss=1∧cauchy=0.00, 5/5 无一例外,跨 boot-1/2 |

**"机器态"降级**: boot-0 晨"同键干净"支柱不成立(T1 §2 发现②: RA13/14 带cauchy=4.0 非同键)。机器态仅存于 never-init 残线(DIAGCAUCHY, §6 矩阵)→归单元 3 init 分布审计。**T1 对照批新样本到货后并案面=§6 矩阵扩行**(预期: 任何 loss=1∧cauchy=0 轮必风暴,与 boot 无关——已被 5/5 支持,新样本只需添行)。

## 5. 修复设计预案（挂起件纪律: 等用户过目,本体不写）

按防线层排序(组件级):
1. **臂装载守卫(已由 T1 v2 做)**: sed 源值守卫+`cauchy>0` 断言——单点止血。已生效(arm_xline v2 = loss=0 路径)。
2. **loss 参数域校验(推荐)**: parameters.cpp 载入处断言 `!(T2_VISION_LOSS==1 && T2_CAUCHY_DELTA<=0)`,violation=启动即拒绝(fail-fast),杜绝一切后续路径的半键注入。一劳永逸覆盖所有臂/手工路径。
3. **init 后置门盲区(推荐)**: 后置门增加 `summary.initial_cost 有限∧termination_type!=FAILURE∧iters>=1` 检查(estimator.cpp:705 init_sane_post 处)——本轮 111/111 会被此门拦截,风暴在源头熄灭(reboot→重 init→仍拦→estimator 停在 INITIAL 不外送毒状态,轮面=never-init FAIL 而非风暴)。
4. **cost gate median 退化防护(推荐)**: streak feed 处(estimator.cpp:1652-1659)加 `hs[median]>0 && isfinite` 守卫,median≤0/非有限时 streak 清零并计数告警——恢复 gate 的"cost 暴涨"设计语义,-1 帧不再假触发。
5. **marg prior NaN 防线(选配)**: preMarginalize 后校验 prior residual/jacobian 有限性,NaN 时丢弃本次 marg(重 marginalization 不带毒 prior)——防 prior 污染跨帧传播(环3)。与 T2_PRIOR_GATE 现有框架可复用。

**修复本体=2+3+4 组合最小集**(1 已在位),等三歧定案文书过目后实施。

## 6. 残留与移交

- DIAGCAUCHY never-init(v4 栈 cauchy=4.00 死法) → 单元 3 init 分布审计(栈代×cauchy4×boot 交互)。
- VRFY1 flight.bag 回放复现(验证修复 2/3/4 在同输入下熄灭风暴) → 挂 T1 批间隙(单元 2 同窗)。
- guard 面[T2RESUME]/E2uls 行为画像 → 单元 6 guard 臂行为库。

## 7. 数据包

nan_dissect_vrfy1/: events.csv(1624 事件)/slv.csv(2006)/gate.csv(3157)/diag.csv/depth_sec.csv/summary.json + 本文书。解析器=/tmp/nan_dissect_vrfy1.py(将入库 tools/)。
