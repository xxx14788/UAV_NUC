# 起飞段图像指纹对审 预注册 v1.1（v1 ABORT 后重设计）

- 登记：T1 / 2026-10-04 19:0x / 任务书 v11.2 单元 1 ①
- **v1 中止记录**：v1（md5 7fb0ad14）按其 ABORT 条款中止——onset 探测（|z_o−z_truth|>1.0m 持续 2s）在 H 袋无命中。诊断（材料清点，未算任何窗口判据统计）：F3B11 袋仅 58.7s 早亡、truth zmax 0.386m、odom z 同窗 max 0.798m、max|z_o−z_truth|=0.481m@t−arm=3.1s、fsm 时间线 t−arm≈4s odom_recv=0（≥1s 流饥饿）→ 手动中止；帧率 19.3Hz。**1.0m 阈为 route 死亡轮标定，悬停复现轮签名是亚米级 z 高估+流饥饿，v1 onset 定义不适配=中止原因，非判读结果。**
- v1.1 以下全部冻结后才计算窗口统计。

## 1. 时间基准（v1.1 修正）

- /mavros/state 事件取 **bag 时**（v1 用 header stamp 出现 disarm<arm 非单调伪影，弃用 header stamp）。
- 其余同 v1（真值按名索引；配对容差 0.5s）。

## 2. onset（H 袋；v1.1 重定义=两信号最早者）

- **S1（z 高估）**：首个 |z_odom−z_truth| > 0.35 m（配对 ≤0.5s）且此后 ≥2 s 内每对样本保持 >0.35 m。阈依据=健康悬停典型误差 ~0.12m 的 3 倍；H 袋实测 max 0.481m。
- **S2（流饥饿）**：[arm, arm+30] 内首个 odom 流间隔 >1.0 s（px4ctrl odom_recv 超时域；H 袋实测 t−arm≈4s 有此发作）。
- onset = min(S1, S2)。C 袋安全扫同定义（预期无；若命中则本对审再度作废如实注记）。

## 3. 窗口（v1.1 重设计）

| 窗 | 定义 | 语义 |
|---|---|---|
| `W_static` | [max(bag 图像流起点+1, arm−10), arm−0.2] | **起飞前地面静景**——同世界同出生点、双方未动、无轨迹混杂=最纯净对照面（v1 无此窗，v1.1 新增主面） |
| `W_gnd` | [arm, arm+5] | 早期爬升（H onset≈arm+2~3 可能落入窗内，注记） |
| `W_pre` | [arm, onset−2] | 因果前置窗（预期短/空——H 袋现实如此；空则守卫降级如实报） |
| `W_arm` | [arm, arm+30] | 起飞全窗（含发作） |
| `W_post` | [onset, onset+15] | 下游症状窗 |

- 帧数守卫：任一窗任一袋 <30 帧 → 该窗降级（W_pre 降级=注记不判；W_static 或 W_gnd 降级=对审判读降为"不定"级）。

## 4. 特征（同 v1 冻结不动）

md5 / mean / std / grad_med / 4×4 块均值（16）+ 块 std（报告面）；左目主面右目辅面。

## 5. 判据（v1.1 冻结）

- sep 与 combo 同 v1：sep=|med_H−med_C|/max(IQR_C,1e-6)；combo={mean,std,grad_med} 全 3 个 sep>3.0 且 ≥4/16 块 sep>3.0。
- **判读 A（坐实）**：`W_static` ∧ `W_gnd` 双窗 combo 皆过。
- **判读 A⁻（嫌疑）**：仅 `W_static` 或仅 `W_gnd` 过（单窗）。W_gnd 单独过而 W_static 不过=运动窗分离带 hover/route 轨迹混杂，只授嫌疑级。
- **判读 B（不可分负结果）**：`W_static`、`W_gnd`、`W_pre`（若非空）全部 combo 不过 且 双方 hash 唯一率 >99%。
- **判读 C（时序倒置/下游）**：`W_static` 不过 且 `W_arm` 过（分离仅在含发作的全窗出现）。
- 其余=不定。

## 6. 语义预绑定（同 v1）+ 新增

- A → 图像内容级差异在**静止地面景**即存在=候选①最强证据（先于任何运动/发作）。
- A⁻（W_gnd 单过）→ 运动窗分离但静景不可分：内容差异与运动耦合（或混杂），嫌疑级。
- B → 起飞前与早期爬升不可分：候选①削弱，候选②（VINS 非确定性）上移。
- C → 分离为下游症状（发作后）。
- 局限：n=1×1 单对；hover(H) vs route(C) 任务混杂声明同 v1；W_static 为主对照面。

## 7. 产物

同 v1：frames CSV ×2 + result JSON（含 v1 abort 注记）+ verdict md。工具=analysis/img_xaudit.py（v1.1 分支重写 onset/窗口/判据段）。
