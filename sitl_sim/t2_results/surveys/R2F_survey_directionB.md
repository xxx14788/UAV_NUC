# R2F 调研方向B — 观测质量门先例(2026-10-02;喂 R2F 门参数与判别格设计,对照 fixface_design.md)

## 1. 上游 VINS-Fusion 现状(源码 grep 实证)
- feature_manager.cpp 仅有的视差逻辑=compensatedParallax2 → **MIN_PARALLAX(关键帧判定,非观测门)**;stereo/motion2 三角化入口**无任何视差/可观测性筛查**(三角化照做,负深度才走 INIT_DEPTH 伪深度路径)。=我们的空白点确认为上游原生空白。
- 上游对"远特征"零处理:0.1m 基线远距深度不确定度无门,R2 垃圾带(stereo ok p75>24m)即从此入环。

## 2. ORB-SLAM2/3:ThDepth=40×基线远近点分类(强先例)
- ORB-SLAM2 双目 TrackStereo:**深度>ThDepth(b×40)的点标记为"远点"**,远点只参与对极/尺度弱约束,**不用其深度做地图点初始化**(MapPoint 仅近点创建);r9765 源码语义(熟知设计,issue [#845](https://github.com/raulmur/ORB_SLAM2/issues/845) 亦引用 40×基线惯例)。
- **适用性:支持机制1**——"远点深度不可信则不产测量"是 ORB 系成熟实践;我们 0.1m 基线 40×=4m 过严(route 场景 15m 内导航),故取视差下限等价深度门(3px⇒15.6m@fx468/B0.1)更贴场景;判别格三档(0.5/1/2/3px)即扫描该轴。
- **特征饥饿处理参照**:ORB 远点仍跟踪(不 erase)只是不建图——对应我们"保留 track 但不写 estimated_depth(不产测量)"的实现选择,而非粗暴 erase。fixface 设计与此一致。

## 3. VINS-Fusion issues 侧
- [#260 / #69 "Not enough features or parallax"](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/260)——特征/视差不足的 starvation 报错(初始化门槛);社区经验=门过严直接卡死初始化。**适用性:修正设计**——我们的饥饿保底(fardrop_min_near,近距供给<N 时不剔远)正是对该风险的预注册防线;判别格必测 vis_n 不坍塌(任务书失效模式①)。
- [#201 sqrt_info 权重](…)——权重型修复先例(次选机制2 的先例),无验证,弱支持。

## 4. 量纲依据:ΔZ = Z²·Δd/(f·B)
- fx=468(sim)、B=0.1m、亚像素匹配误差 Δd≈0.5px:Z=10m → ΔZ≈1.07m(相对 10.7%);Z=15m → 2.4m(16%);Z=24m(R2 垃圾带 p75)→ 6.1m(25%)。垃圾带的相对不确定度=近距(5m,1.3%)的 8-20×,支持"远段深度纯噪声"机理。
- 3px 视差门 ⇒ Z≈15.6m 上限=把 ΔZ/Z>15% 的段整体拒测;2px⇒23.4m;1px⇒46.8m;0.5px⇒93.6m。三档扫描覆盖"温和(拒 94m+)/激进(拒 15.6m+)"谱。

## 5. SVO/OKVIS/MSCKF 侧
- SVO(hkov?/ethz-asl svo_public):特征深度用 filter(inverse-depth EKF)逐点收敛判定,"深度未收敛点不参与优化"(seed 机制)——**先验级支持**"不确信深度不产测量";与机制2(inv_dep 先验加权)同族。
- OKVIS:边缘化保留策略+多约束,无显式视差门,弱相关(不引为依据)。
- MSCKF:立体测量直接用,无门(上游原生),同 VINS 空白。

## 6. 对照 fixface_design.md 的结论
- 机制1(视差-深度可观测性门)**获 ORB ThDepth 先例+量纲计算双重支持**,维持首选;
- 实现形态修正为"保留 track、不写 estimated_depth"(ORB 远点语义),与设计稿"跳过或直接 erase"二选一**取前者**(erase 会破坏跟踪连续性,加剧饥饿风险);
- 饥饿保底(fardrop_min_near=30)获 #260/#69 社区案例支持为必要防线;
- 判别格三档(0.5/1/2px)+3px 补充档=覆盖 ORB 惯例带;R2 垃圾带 p75=24m 对应 ~2px,预期 2px 档对 R2 载体段命中最高(预注册假设,判别格验证)。
