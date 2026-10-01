# R3 调研方向A — route 漂移/发散已知案例(2026-10-02;喂 R3 假设表,判读=R3_forensics/r3_verdict.md)

> 调研时点:R3 判决已落(急冻型/在线载体)。本清单作为"社区已知案例对照面"入台账,每条附适用性判断。

## Fast-Drone-250(ZJU-FAST-Lab)
1. **[#74 imu_propagate 漂移明显而 out_path 稳](https://github.com/ZJU-FAST-Lab/FAST-Drone-250/issues/74)**(Open,无回复)——D435i+NX 实机,fusion GPU 版。症状=高频外送流(imu_propagate)漂移而 vio 输出稳。**适用性:中**——与我们"发布流 vs 优化器状态"表面相似,但我们实测两者同源一致(PR2 冻结值=diag 终态);该 issue 无诊断,不能作机理依据,只证明"发布流单独病变"社区有见。
2. **[#65 VINS 飘一直未找到原因](https://github.com/ZJU-FAST-Lab/FAST-Drone-250/issues/65)**(Closed 无评论)——静置时位置累积至上百,extrinsic 估计不动。**适用性:低-中**——"静置累积漂移"与我们 route 急冻形态不同(我们是急性冻结),但"extrinsic 不更新"与我们 Bas 逐位冻结同款"估计器梯度死寂"味道;无结论,仅现象参照。
3. **[#96 起飞左飘/实际与规划轨迹误差](https://github.com/ZJU-FAST-Lab/FAST-Drone-250/issues/96)**(Closed)——起飞漂移+真值 vs 规划轨迹 mismatch。**适用性:中**——消费域症状同款(机体偏航迹);我们的五线取证把这类症状定位到 VINS 域首发,方法论可复用给社区;无修法。
4. [#92 odom 频率低](…)——频率问题非本形态,不适用。

## EGO-Planner(ZJU-FAST-Lab)
5. **[#120 真机前飞急速掉头后乱飞](https://github.com/ZJU-FAST-Lab/EGO-Planner/issues/120)**(Open 无回复)——RViz 轨迹看着正常但实机乱飞,换机后出现。**适用性:高(症状级)**——"显示正常+实机乱飞"=估计器/控制域病变而规划显示层无感,与我们 route 轮完全同症状族(cmd 健康、GT 失控);评论建议查坐标系/里程计源方向——与我们"px4ctrl 吃毒 imu_propagate"定因一致方向。无定论。
6. [#117 重规划速度解算异常](…)(Open)——replan 初值异常。适用性:低(我们 cmd 无病态)。
7. [#9 规划不考虑当前 odometry](…)(Closed)——Planner 忽略 odom 的讨论,与"planner 冻结输出"行为侧面相关,适用性:低。

## XTDrone(robin-shaun)
8. **[#57 VINS 悬停正常而 ego-planner 出错](https://github.com/robin-shaun/XTDrone/issues/57)**(Open)——实际是 ego_planner SIGSEGV 崩溃,非 odom 质量问题。**适用性:低**(排除性参照:社区"planner 出错"多数是崩溃/装配,不是慢漂)。
9. [#53 EKF 视觉观测协方差](…)(Closed)——EKF2 EV 协方差调参讨论。适用性:中低(EV 链我们已由 T1-E4 主导)。

## VINS-Fusion(HKUST)
10. drift 族 issues(#11/#41/#42/#53/#56/#79/#123/#157/#184/#217 等 25+ 条)——绝大多数=标定/相机/时间同步问题(ZED/D435 标定、外参、曝光),**无一条是"导航中急性冻结+零 failureDetection"形态**;failureDetection 相关 issue=0(无人报过零触发盲区)。**适用性(元结论):高**——(a)我们的形态在上游社区无已知同款=新形态报告价值;(b)社区 VIO 漂移排查起手式(外参/同步/标定)与 R3 取证互证:我们已排除栈差/config(gyr_w 盲轴)/袋数据(回放健康),指向在线时序机制。
11. [#201 stereo+imu 漂移的 sqrt_info 解法](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/201)(Open 无验证)——调 sqrt_info 权重缓解漂移但出现轨迹形态异常。适用性:低-中(权重轴,我们未动权重;其"改后轨迹下沉回升"提示权重对 z 轴敏感——与我们 z 冲天形态的脆弱轴呼应)。

## 汇总判断
社区无 route 急冻同款已知案例;消费域症状(机体飞偏/乱飞 while cmd 正常)在 EGO#120/FD250#96 有呼应但无根因定论。我们的"五线对齐+回放对照"取证法可作为该症状族的定因范式。修复面(failureDetection cost 门)在上游 issues 无先例=首创修复(需 README/上游回馈准备)。
