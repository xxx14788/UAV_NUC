# 起飞段图像指纹对审 预注册 v1（判据先行件）

- 登记：T1 / 2026-10-04 18:1x / 任务书 v11.2 单元 1 ①（带图袋对审分支）
- 性质：判据预注册——本文落盘+commit 后方可计算判读面统计；判据未预注册不出 PASS/FAIL。
- 素材（已盘点，非判读）：
  - H 袋（敌对）：`vins_smoke_runs/run_F3B11_155643/flight.bag`（2.0G；左/右目各 1135 帧；/vins_estimator/odometry 546；/gazebo/model_states 14655；/mavros/state 59）——canonical hover 复现器，F3B10-13 四连灭之一，敌对形态=起飞/爬升段 VINS z 腐坏。
  - C 袋（净轮）：`vins_smoke_runs/run_X1final_040643/flight.bag`（5.5G；左目 3094 帧）——X1prime 型 route 轮，起飞段存活（04:06），带图。
  - 同世界（iris_stereo_vins 资产族）；**任务不同（hover vs route）=已声明的混杂因子**，对策=窗口设计与双窗判读（见下）。

## 1. 时间基准与窗口（冻结）

- arm 时刻 = /mavros/state 首个 `armed==True` 的 header stamp；两袋同法。
- 真值 z = /gazebo/model_states 按名索引 `iris_stereo_vins`（禁用 pose[0]——ground_plane 坑在册）。
- VINS z = /vins_estimator/odometry 的 pose.position.z。
- **onset（敌对发作点，仅 H 袋）**：首个满足 |vins_z(t) − truth_z(t)| > 1.0 m 且此后连续 ≥2 s 保持 >1.0 m 的时刻（两流按最近邻时戳配对，配对容差 0.5 s）。C 袋用同探测器全窗扫（预期无发作；若 C 袋出现 onset 则本对审作废重设计——如实注记）。
- 窗口：
  - `W_arm`  = [arm, arm+30 s]（起飞段全窗）
  - `W_pre`  = [arm, onset−2 s]（因果前置窗；2 s=保护带）
  - `W_gnd`  = [arm, arm+5 s]（近地子窗——混杂最小化窗：两袋机体均在地面/近地，视角差最小）
  - `W_post` = [onset, onset+15 s]（下游症状窗）
- 帧数下限守卫：任一窗任一袋帧数 <30 → 该窗判读降级（W_pre 降级时改用 W_gnd 单窗+注记；W_gnd 也不足则该面=不定）。

## 2. 帧特征（冻结；左目为主面，右目为辅面不参与门判）

对每帧：①md5（原始字节）②灰度均值 mean ③灰度标准差 std ④梯度中位数 grad_med = median(|dx|+|dy|)，dx/dy=相邻像素轴向差分 ⑤4×4 块均值 16 值 ⑥4×4 块标准差 16 值。彩色编码先取通道均值转灰度；记录实际编码。

## 3. 判据（冻结）

- 分离度：`sep(f) = |median_H(f) − median_C(f)| / max(IQR_C(f), 1e-6)`（C 袋为参考带）。
- 标量特征集 = {mean, std, grad_med} ∪ 16 块均值（19 个标量；块标准差仅入报告）。
- **判读 A（图像内容级差异坐实）**：`W_pre` 内 {mean,std,grad_med} 中 ≥3 个 sep>3.0 且 16 块均值中 ≥4/16 块 sep>3.0，**且 `W_gnd` 内同样成立**（双窗皆过才判"坐实"）。
- **判读 A⁻（嫌疑级）**：仅 `W_pre` 或仅 `W_gnd` 单窗满足上述阈值（另一窗不满足）——注记为嫌疑，不判坐实。
- **判读 B（不可分=负结果）**：`W_pre` 内 sep>3.0 的标量特征数 = 0 且块级 <4/16，且两袋 hash 唯一率均 >99%。
- **判读 C（时序倒置=下游症状）**：`W_arm` 满足 A 的阈值组合但 `W_pre` 不满足（分离仅出现在发作后）。
- 其余形态 = **不定**（如实报告混合面貌）。
- hash 面（两袋各窗）：unique_md5/frames 报告值；唯一率 ≤99% 的窗单独注记（重复帧=另一性质线索，不进 A/B/C 门）。

## 4. 判读语义（预绑定）

- A → 残留候选①"图像内容级差异"获得首个正向证据（下一步=内容差异的机理定位，任务书单元 1 主路径素材）。
- B → 候选①被削弱（起飞段不可分），候选②"VINS 进程内非确定性"权重上移（T2 域联合件）。
- C → 图像差异为敌对的下游症状而非原因（因果链注记，候选①排除面扩大）。

## 5. 计算与产物（冻结）

- 工具：`sitl_sim/analysis/img_xaudit.py`（纯 numpy+rosbag+hashlib，无随机性，确定性）。
- 产物：`t1_evidence/v10_2026-10-02/img_xaudit_frames_<bag>.csv`（逐帧）+ `img_xaudit_result.json`（onset/窗口/分离表/判读）+ `img_xaudit_verdict.md`（按冻结判据出判）。
- 环境：source /opt/ros/noetic；只读袋，0 锁；跑前 pgrep 确认无在飞轮（大 IO 纪律）。
- 局限声明：n=1 敌对袋×1 净轮；结论等级=单对样本（不外推为总体；负结果亦然）。飞行取证（单元 1 ②）仍为主路径，本对审=可回溯离线先手。
