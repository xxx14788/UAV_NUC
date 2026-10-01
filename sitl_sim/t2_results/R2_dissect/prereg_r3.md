# R3 route 慢漂定因 — 预注册判据(2026-10-02 00:5x,先于数据回看写定)

## 判别逻辑(三域切割,任务书 v7.5 单元1原文正式化)
- D-VINS(VINS 自漂): odom 先发散 + poscmd 在 odom 框内自洽
- D-PLAN(归 T3 包对账): odom 尚可 + poscmd 病态
- D-CTRL(移交 T1): poscmd/setpoint 良好 + 机体不跟

## 量化判据(预注册,先于回看)
1. 发散起点 t_div: |odom_pos − GT_pos| 首次 >1m(t_div1)且 5m(t_div5);GT=/gazebo/model_states iris 位置(截去出生偏移(+1.01,+0.99,+0.10)后仍按绝对差,出生偏移单列)。
2. odom 病态: |odom 速度| >5m/s(远超机体包线)首时刻 t_ov;误差>10m 或 |v|>5m/s 任一成立即"odom 已病"。
3. poscmd 病态(任一): |cmd 速度|>6m/s(ego_planner 限速上界量级);相邻两帧 cmd 位置跳变>2m;cmd 发布频率 <50Hz(健康 100Hz)。
4. poscmd 在 odom 框内自洽: |cmd_pos − odom_pos| 持续<3m 且方向连续(无反向抖动>10Hz)。
5. "谁先动"裁决: 比较 t_div1/t_div5 vs t_cmd病态起点 vs t_GT 起飞后偏离期望航迹起点;若 t_div1 < t_cmd 且 GT 跟随 odom 侧(机体沿 odom 假航迹飞)→D-VINS;若 t_cmd < t_div1 且 odom 尚可→D-PLAN;若两者皆良而 GT 不跟→D-CTRL。
6. 慢漂谱: err(t)=|odom−GT| 分段速率(m/s);与 leg 段/速度剖面/高度相关系数(皮尔逊,|r|>0.5 报告)。
7. VINS 内部前兆(离线重放 jr3 vins.log,在线袋 odom 交叉验证): vis_n 首次跌破 50 的时刻 vs t_div1;若 vis_n 坍塌先于发散>2s→视觉前兆成立(与 R2 载体链同源判据)。
8. failureDetection 零触发解释: 全程 Bas/Bgs/td/extrinsic 检查项实值距离各自阈值的最小裕量,确认零触发=量域外检查缺失(结构性)而非阈值碰巧未及。
9. 回放-在线形态一致性: jr3 重放 odom 流与在线 PR2 袋 odom 流形态(发散时刻±5s/末端误差量级)一致→离线内部面可代表在线;不一致→慢漂依赖在线时序,如实注记(红线11 生死判据=在线,离线仅取证辅助)。

## 历史形态对比表(取证面6,形态学判据)
- 瞬态发散族(hover 33.7s 型,WD1b/T1-X1): Bas 爆 2.5+ 先于 odom 病态,死窗<60s
- E4-R2 xy 振荡型: 周期性 xy 振荡,无 Bas 爆
- 134s 慢爆型(WC2 032005): 存活 134s 后 Bas 爆
- route 慢漂(本对象): 零 fail 全程活+误差单调累积至百米级
判据: route 慢漂若 vis_n 坍塌形态=R2 墙段形态→"熟窗慢死在线变体";若 vis_n 健康→第四形态(非视觉载体)。

## 假设表(H 编号)
- H-R3a: VINS 视觉池坍塌(R2 同源载体)在线变体→慢漂
- H-R3b: 规划器消费坏 odom 正反馈(cmd 追 odom 假位置→机体飞偏→视野变→VINS 更坏)
- H-R3c: odom 病态纯属尺度/漂移,planner 只是放大器(非 culpable)
- H-R3d: 控制域(px4ctrl/mavros 链)不跟 cmd
- H-R3e: EKF2/GPS 口径干扰(已预排除:U3′ 零 EKF2 注入,GT 不吃 vision_pose;vision_pose 仅喂 EKF2,判读禁吃 local_position)——验证 vision_pose 流本身是否病态以闭合

证伪/证实按上述量化判据落格。产物: R3_forensics/ 目录 npz+图+verdict。
