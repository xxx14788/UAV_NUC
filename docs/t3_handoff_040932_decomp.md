# T2 移交件 040932 消费判读（T3 ← T2 04:27 移交；2026-10-03 09:5x）

> 移交原文："034032 leg1 27.2m到位异常(VINS健康)移交你/T1查planner/EKF2面"。
> 判读=正源工具三件（round_result.sh 官方口径+到位分解探针+t3_r3_planner_domain 四门）。
> 产物=x11_dryrun_v11/R040932_decomp/（RESULT.txt+硬链接袋/log）+/tmp/pd_040932_*。

## 1. 轮号裁定

"034032" 无对应袋/目录；按"VINS 健康"唯一匹配 **040932**（T2 唯一零失败计入 route 臂，
log=flight_logs/20261003_041235_route/ faildet=0 实核）。判为笔误。
**目录↔袋映射勘误（编排债再现）**：flight_logs 目录名=着陆归档时刻非起飞时刻——
035043 目录(faildet14+fire5)=033941 风暴臂；040903 目录(faildet2)=035800 臂；
041235 目录(faildet0)=040932 臂。判读吃 log 必按指纹配对，勿按名字。

## 2. 核心结论（三段分解）

| 面 | 读数 | 判 |
|---|---|---|
| 规划段 poscmd→goal min | **0.013m**(leg1,goal 3,-2,1) / 0.009m(leg2) | **planner 无罪**（ego 收 goal 即规划到点，同 U3PO 模式） |
| odom 系内闭环 cmd-odom p95 | **0.195m**（RESULT 信息项） | px4ctrl 跟踪紧，无病 |
| VINS odom 对 truth 漂移 | p95 0.59m / max 0.64m（planner-domain 工具） | 健康（VINS 无罪级） |
| **执行段 truth→goal min** | **0.871m**(leg1) / 0.934m(leg2)，VINS 自报 0.030/0.028m | 差 0.12-0.18m 不过 0.75 门 |

**机理**：truth→goal(0.871) ≈ odom 自报到位(0.030) + odom-truth 瞬时刻画误差(~0.84m)。
到位 FAIL 的主残差=VINS odom 对 truth 的漂移刻画（0.6-0.9m 级）压过门余量，**非 planner
非 px4ctrl 非 EKF2**（W1 构型 px4ctrl 直吃 odom，EKF2 不在位姿控制环）。EKF2 面排除。

## 3. 27.2m 不成立（对账请求 @T2）

正源判读 leg1 真值 min=**0.871m**，与移交文 27.2m 差 30 倍。可能的口径分歧：
①轮号实指他臂（035800 成熟段 69-91m 域?但该臂 VINS 不健康）；②round_result goal 参数
用了 7,-4,1（X 线默认）而非实飞 3,-2,1——即便如此实测也仅 ~4m；③odom 系未锚定读数。
请对账 27.2m 出处。**X 线启示**：到位门 0.75 对"VINS 漂移 0.6-0.9m+规划/跟踪近满贯"的
组合余量仅 0.1-0.15m=历史域到位全红的机理画像再添一例（U3PO 4.436m→本轮 0.871m 的
改善来自零事件窗，非架构变化）。

## 4. 附带发现

- J0 锚差 0.587m 边缘超 0.5 恒门=T1-D1 域新样本（vins 域健康+j0jump>0.5 → 不计 5/5 入回挖）。
- auto_disarm ✗（armed 终态 True）=U3pp 族同款，px4ctrl failsafe 落地未 disarm，归 T1 G-1 域。
- planner-domain 四门在低 active_frac(0.1) 轮的 G2 cos 反向读数=悬停帧主导伪影，不入判。
