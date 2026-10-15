# C-4 供给门 v2（五面正式版）+ 待核①收尾 + 待核④处置

> 终局册 §四 C-4。v1 三面（2026-10-13 整改册单元 2）+面 4/面 5 扩展；判读兼容=sim 配对率 p50 语义不变。

## 一、供给门 v2 五面定义

| 面 | 判据 | 数据源 | 状态 |
|----|------|--------|------|
| 面 1（生死线） | stereo 配对率 p50 ≥0.10 | simvins.log T2IQG-METRIC（stereo_r） | 承 v1（v6 批 p50=0.810 PASS） |
| 面 2 | supply_frac 对照 plain 基带（corners 供给不塌） | T2IQG-METRIC corners | 承 v1（飞行段 150 恒饱和） |
| 面 3 | odom 健康（imu_propagate 流活+init 负深零） | simvins.log/袋 | 承 v1 |
| **面 4（新增）** | **贴箱窗（<1.2m）stereo 配对率 ≥0.3**（预估默认=C-2 精算与 H-dJ2 同值；**C-5 试录实测分布定正式值后冻结、禁 C-6 中途改**） | C-5 试录 T2IQG 贴箱窗切片 | C-5 承载（v6 同窗历史 0.01 阴性在册） |
| **面 5（新增）** | **慢漂带：悬停漂移率 ≤0.65m/min**（C-1 冻结口径=稳定主段 z≥0.9 XY 首末/时长）+伴生约束（配对率 p50≥0.10+起飞面不回退） | 悬停轮 truth | C-3/C-5 承载（当前 1.136/1.669，调参中） |

## 二、待核①收尾：相机参数级对照表（四行补齐；差异文档归档本件）

| 行 | sim（sim_stereo） | 实机（realsense_d435 config v0） | 差异与影响 |
|----|------------------|--------------------------------|-----------|
| **双目基线** | **100.0mm**（body_T_cam0/1 平移 (0.12,±0.05,−0.02)） | **49.3mm**（config 标定值；机械规格 55mm D435） | **sim 基线 ≈2× 实机** → 同距视差角 sim 大 ~2 倍 → 深度精度 sim 乐观侧（代表性边界主声明项） |
| **帧率/时戳源** | gazebo camera sensor update_rate 30Hz；VINS 前端 freq 10；戳=gazebo_ros_camera（hardware sim time） | D435 infra 30Hz（rs_camera.launch）；戳=rs 流 | 时戳域不同构：sim=渲染节拍 transit 慢淋（在册慢漂主源）vs 实机=readout/USB（物理）——机理差异如实注记（C-1 层次诚实承袭） |
| **IMU 噪声先验** | acc_n **0.2**（T2-R5 轮 2 定值：223Hz+闭环放大下 Bas 瞬态稳健点）/gyr_n 0.01/acc_w 0.001/gyr_w 0.0001（T2-WA C-line 终值） | acc_n **0.1**/gyr_n 0.01/acc_w 0.001/gyr_w 0.0001 | 唯一异=acc_n（2×，sim 域在册定值有注释链）；其余三参逐位同 |
| **畸变模型** | PINHOLE k1/k2/p1/p2 全 0 | PINHOLE k1/k2/p1/p2 全 0 | 同（D435 出厂去畸变流+sim 无畸变） |

（内参行承待核①草案：fx 467.7 vs 387.5（sim 长 20.7%）/HFOV 68.8° vs 79.2°/1.2m 视野 1.65 vs 1.97m——sim 视野窄、同距占幅大，供给面 sim 偏乐观侧注记。）

## 三、待核④处置（实机 param 对照）

仓内实机 PX4 param dump 存档检索：`t4_evidence/realmachine_pre_record/`（bags/日志/IMU jitter CSV）与全仓 `*.params` 均**无实机 param 导出件** → 按任务书**注记挂起不阻塞**（禁起旧机栈/禁要求旧机在线）。后续实机域有 dump 时对照成表补挂。

## 四、执行挂点

- 面 4 正式值冻结动作在 C-5 试录判读后（本册 C-5 条款）；C-6 禁中途改。
- 面 5 与 C-1 基线件联动（判读口径冻结 6386fc30）。

——凭据：sim config=src/VINS-Fusion/config/sim_stereo/（md5 随轮落盘 vins_config.md5）；实机=src/VINS-Fusion/config/realsense_d435/（config v0）；生成脚本=tools_b4/（基线平移解析）；2026-10-15。
