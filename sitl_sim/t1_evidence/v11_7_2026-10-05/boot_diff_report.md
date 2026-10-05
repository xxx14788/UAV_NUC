# 排查双刀·静态 diff 报告（boot_diff_report v1；2026-10-06 04:1x；D-1006-T1-09 附件）

> 任务书 v11.13 单元 1。对象：RA13/14（boot-0 "干净"轮）vs VRFY1（boot-2 风暴轮），VRG1（boot-2 全绿）为对照。
> 方法：全部取运行时工件（simvins.log 的 VINS 自打印行=实际生效值，非 config 文件静态值）。

## 0. 结论速览

**风暴根因实锤 = X 线臂 sed 产出 vision_loss=1 ∧ cauchy_delta=0.0 → ceres::CauchyLoss(0.0) 数值病态 → 求解器 NaN。**
"机器态×gates 键耦合"假设对风暴面**不再必要**（降级为 never-init 残线的次级嫌疑）。

## 1. banner 逐字段（四轮 [T2SGCFG]）

`guard=1 sane_p=50.0 sane_v=15.0 resume_gap=0.15` — **四轮逐字段全同**。
发现①：banner 仅覆盖 guard 族，**对 vision_loss/cauchy/staged/cost_gate 完全盲**——x4_batch --arm-banner 门对臂配置错误不可检（流程缺陷，本批修复）。

## 2. config 双副本 md5 与实际生效键

| 轮 | config 路径 | md5 | loss | cauchy | staged | guard |
|---|---|---|---|---|---|---|
| RA13/14 | t2_results/R2_dissect/cfg_streamguard/…yaml（T2 域副本） | 5e688943 | 1 | **4.00** | 1 | 1/50/15 |
| VRFY1 | src/VINS-Fusion/config/sim_stereo/…yaml（canonical，飞时被 arm_xline.sh sed 覆写） | (运行时覆写) | 1 | **0.00** | 1 | 1/50/15 |
| VRG1 | 同上（guard-only 改写） | (运行时覆写) | **0** | 0.00* | **0** | 1/50/15 |

*loss=0 时走 HuberLoss(1.0)，cauchy 值无效应（estimator.cpp:1337-1341）。
发现②：**RA13/14 与 VRFY1 并非"同键"**——唯一"干净"gates 轮带 cauchy=4.0；verify_verdict_v119 嫌疑收敛表的"boot-0 同键干净"支柱不成立，需勘误。
发现③：config 双副本路径分叉本身是 confound 源（RA 系从未过 arm_xline.sh 流程）。

## 3. sed 残迹（arm_xline.sh 审计）

`sed s/^t2_cauchy_delta: 4.0/t2_cauchy_delta: 0.0/ "$D" > "$X"` — 单行替换，源值非 4.0 时**静默不生效**（无守卫）；且"cauchy 关"的实现=delta 置 0 而非 vision_loss=0——**设计错误，NaN 之源**（§5）。

## 4. PX4 参数导出

**不在案**（RA13/VRFY1 轮目录无 param dump，preflight.txt 无参数段）——如实登记；对-boot 面留有缺口，不阻塞主线（风暴是 VINS 求解器 NaN，PX4 参数面无关）。

## 5. 机理链（代码取证）

estimator.cpp:1337-1341:
```
if (T2_VISION_LOSS == 1)
    loss_function = new ceres::CauchyLoss(T2_CAUCHY_DELTA / 1.5);   // 0.0/1.5 = 0.0
else
    loss_function = new ceres::HuberLoss(1.0);
```
ceres::CauchyLoss(a): ρ(s)=a²·log(1+s/a²)。a=0 → 0·log(∞) = **NaN**（IEEE 0×∞），每残差每迭代注入 NaN → 求解器状态 NaN。
与 VRFY1 取证全对齐：后端数值发散型（-nan×1066 行，自 t=10s 起）∧ 首双目深度正常（3.896/3.918，前端健康）∧ T2fail=110。

## 6. 跨 boot 组合矩阵（在线飞行轮，实际生效键值，全库枚举）

| 轮组 | boot | 栈 | loss | cauchy | 判读 |
|---|---|---|---|---|---|
| RA13/14 | 0 | **v3-rc**(vins_node 14:34 重建前) | 1 | 4.00 | VINS 干净（到位 FAIL=规划域，T2fail=0） |
| SUPX2a/X2b/HV2a/HV2b | 1 | v4 | 1 | **0.00** | **风暴 4/4** |
| DIAGCAUCHY | 1 | v4 | 1 | 4.00 | never-init（另一种死法，非 NaN 风暴） |
| DIAGGUARD2 | 1 | v4 | 0 | – | 干净+净轮面 j0=0.418 |
| VRFY1 | 2 | v4 | 1 | **0.00** | **风暴**（never-flew+NaN×1066） |
| VRG1 | 2 | v4 | 0 | – | 四指标全绿+净轮 j0=0.137（X2③ 首例） |
| SUPHVa/HVb/X1b | 1 | v4 | 0 | 4.00* | FAIL（到位类；cauchy 无效应） |
| SUPP2A 系/P3INJ/HV3 | 1 | v4 | 0 | – | 干净面（供给轮） |

**绑定律：风暴形态 ⇔ loss=1 ∧ cauchy=0.00，5/5 无一例外，跨 boot-1/boot-2。**

## 7. 栈代差对账（src 树 git）

- 949bea4（T2 v9.5 stream guard v2-v4）commit=10-05 15:24；vins_node 重建=10-05 14:34。
- RA13/14 飞于 13:47/13:54 → **v3-rc 栈**；VRFY1/VRG1 → v4 栈（b7de133d/59548c6a）。
- confound 残留：cauchy=4.00 在 v3-rc 干净 vs v4 never-init（DIAGCAUCHY）——**栈代×cauchy4 交互或 boot-1 机器态，二不可分**，归 T2 域 never-init 线（不再是风暴主线）。

## 8. 三歧断案（任务书单元 1.0 条件化输出，供 T3 矩阵工具）

1. ~~零成功轮=gates 三键交互缺陷~~ → **否**：风暴绑定的是 vision_loss×cauchy=0 二元组合（CauchyLoss(0)），cost_gate/staged 无罪证（RA13/14 同开无害）。
2. ~~cauchy 依赖~~ → **半对，重新表述**：表象"gates 臂需 cauchy=4.0"实质是"cauchy=0 配 vision_loss=1 即 NaN"；cauchy=4.0 自身在 v4 栈另有 never-init 问题（T2 域）。
3. ~~机器态~~ → **风暴面对账后不再必要**：NaN 机器跨 boot 恒定复现（CauchyLoss(0) 无机器依赖）；机器态仅存于 never-init 残线嫌疑（且与栈代 confound 不可分）。

## 9. 分支裁定（任务书单元 1 第 2 条）

走**实锤分支**：修复=arm_xline.sh 臂定义修正（vision_loss: 1→0，即 Huber；保留 cost_gate=1+staged=1+guard——原口径 gates 在线防线的可保留部分）+ x4_batch 臂门升级（banner 盲区→T2 knobs 行校验）→ gates+guard 验证轮×1（X2③ 位形）→ 绿则 x4_batch 原口径发射。
判据门值零变动；臂=实验条件修正（bug fix），非判据放宽。

## 10. 本报告证据指针

- 四轮目录：~/sitl_sim/vins_smoke_runs/run_{T2RA13_134733,T2RA14_135448,VRFY1_023908,VRG1_025100}
- T2 knobs 提取：`grep -m1 "T2 knobs" <dir>/simvins.log`
- 代码：estimator.cpp:1337（CauchyLoss 分支）、parameters.cpp:258（banner）
- 时间线：git log 949bea4=10-05 15:24；vins_node mtime=10-05 14:34
