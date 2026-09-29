# VINS-IMU 紧耦合修复方向研究(2026-09-29 夜;用户点名工作流)

方法:3 路社区/文献检索 fan-out(VINS-Mono/Fusion issues、鲁棒估计经验、场景病理)+ 本地代码解剖 + 量化合成裁决。工作流产物全文含 17 条外部经验;本落盘版为裁决要点+NUC HEAD 复核修正(研究子代理读的本地 checkout 陈旧,已由 T3 在 NUC 复核纠偏)。

## 失效签名(实验实证基础)

滑窗 init_cost 周期性尖峰 78→7068→16871;Bas 运动瞬态跑飞 2.6-3.4(Bgs 有时同爆);场景条件性(无障碍全过 ATE 0.144m / obstacles 必爆);噪声轴免疫(acc_n 0.0065/0.056/0.2 全爆);求解器 3ms 无截断;IMU 原始干净;track 计数健康内容有毒;HuberLoss(1.0) 已启用;223Hz IMU/双目 10cm 基线。

## NUC HEAD 复核后的代码实锤

| 发现 | 位置 | 状态 |
|---|---|---|
| repropagate 禁用 | imu_factor.h ~:61-67 `#if 0`(阈值 0.10/0.01 在注释内) | ✅ NUC 实锤 |
| rejectWithF 注释 | feature_tracker.cpp:173 | ✅ NUC 实锤 |
| INIT_DEPTH 静默伪深度 | feature_manager.cpp:355/390/442/492+SVD 分支 :440(depth<0.1→置 5.0) | ✅ NUC 实锤 |
| HuberLoss(1.0) 启用 | estimator.cpp ~:1179 | ✅(T3 自核) |
| FB 双流阈值 2.0 | feature_tracker.cpp(903e62b) | ✅ **已生效**——研究子代理本地镜像陈旧误报"未落地",以 NUC 为准 |
| failureDetection Bas>2.5 活代码 | estimator.cpp ~:1087-1091 | ✅(与观测 reboot 行为一致) |

## 量化要点(为什么 17k 尖峰来自 IMU/先验而非视觉)

1. 视觉投影因子 Huber 有界:单块 100px 级残差 cost≈65,窗口不足 1000 块——**到不了 1e4**。
2. IMU 因子与边缘化先验是仅有的平方增长项;先验 NULL loss+eps=1e-8+残差滚存=周期性复现的结构来源。
3. IMU 因子 bias 残差为差分结构(Baj−Bai):**全窗一致漂移不被罚**——bias 是视觉与 IMU 撕扯的自由吸水池。
4. repropagate 被禁:ΔBa=2.6 时一阶修正 dv_dba≈−dt 超线性域(Forster 原典:bias 大变必须重积分),
   残差系统性算错且以 5.5e4 级 sqrt_info 加权。
5. failureDetection Bas>2.5 reboot 是循环的**重置边**(清先验→cost 回 78→毒观测再积累),不是缺失件。

## 修复方向排序(签名适配度×证据强度;统一判据=173345 袋回放三判据)

1. **D1 深度域硬门控+双目/SVD 互验**(适配极高×证据高):feature_manager 三角化分支 depth∉[0.15,30] 直接 erase(废 INIT_DEPTH 静默替换)+双解偏差>30% 剔除;唯一同时满足全部四条实证约束的轴。风险=上限过紧致特征饥饿(监控剔除占比)。
2. **D2 先验健康门**(适配高×证据高):求解后边缘化前 init_cost>1e3 或 ||ΔBas||>0.05→跳过边缘化+丢弃污染先验(限频);断滚存链(DM-VIO:FEJ 式先验在 bias 收敛前不安全)。
3. **D3 进窗前 chi-square 门控**(适配高×证据中):滑窗状态重投影残差 e^Te>chi2(0.99)×5 剔整条 track;与 D1 互补(拦"几何一致但深度错");须与 D2 联动防"剔光"前车(OpenVINS #554)。
4. **D4 视觉核 A/B**(适配中×证据中):Huber→Cauchy(delta_px 2/4/6)+rejectWithF 启用;预期"降毒非断链",**反向结论同样值钱**(只延迟不消除=反证主通道在 IMU/先验)。
5. **D5 bias 分级软约束**(兜底):Bas∈[1.0,2.5) 冻结一窗或弱先验;纯症状压制,看 ATE 是否反恶化(残差转移)。
6. **D6 仿真侧纹理/去噪**(条件):仅 D1 拦截率异常时;改仿真不改算法,不迁移真机。

## 两候选裁决

- 特征离群轴=主轴保留(70% 资源)但**升级域**:像素域过滤拦不住"几何一致但深度错"的毒点→深度域(D1)+状态域(D3)。
- bias 护栏=降级辅助(30%)且**改形态**:单纯硬压必残差转移;bias 增量的正确用途=污染指示器(触发 D2/D3)。
- 两轴是同一失效链的入口与出口,**串联部署**;任一单独三判据全绿即结案,另一记冗余防线。

## 主要外部证据

- VINS-Mono issues #54(瞬态发散多人复现)/#58(Huber→Cauchy 真机单例+同款判据)
- Forster et al. On-Manifold Preintegration(TRO 2017,arXiv:1512.02363)——bias 大变必须重积分
- DM-VIO(RA-L 2022,arXiv:2201.04114)——污染先验不安全/延迟边缘化
- OpenVINS 架构对照+issue #554(update 0 feats 前车)+上游 PR #110(无完好性检查)
- VINS-Mono-PNs/UMS-VINS fork(外点剔除/分质量利用思路)

## 已删除的过时方向(勿再做)

恢复/收紧 failureDetection(已在线且被证不足);IMU 侧排查(采样率/时移/单位/噪声对齐——实验免疫);td/外参在线估计(已冻结);RANSAC PnP 与立体视差下限(T2-W4 已落地);重做 FB 2.0(已生效)。

→ 执行单元化版本见 `plans/2026-09-29_T2_vins_quality_v4.3.md` W-A1..W-A7。
