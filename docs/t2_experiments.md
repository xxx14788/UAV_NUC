# T2 实验账本（双目同步性 + 离线调参矩阵）

记法: 试验号 | 数据/配置 | 关键数字 | 结论。全部可由 ~/sitl_sim/t2_results/ 与 bags/ 复现。

## 预研（W2 录制前，历史 bag）

| # | 数据 | 发现 | 结论 |
|---|---|---|---|
| P1 | 崩溃夜 flight_2026-09-26_224815.bag /mavros/imu/data | 严格倒退 4.27%、重复 stamp 20.32%、有效唯一 119.3Hz、周期 std 5.1ms | 该话题当晚为脏流；VINS getIMUInterval 假定单调，dt≤0 → 预积分数值不稳（与 A7 "numerical unstable" 现场吻合）→ H-D 候选 |
| P2 | 崩溃夜同 bag 单连接数 | /mavros/imu/data 连接数=1（非双发布者） | 脏流来自 mavlink 流本身或 SCALED_IMU 合并，非 ROS 层 |
| P3 | T1 STATUS 17:52 | T1 实锤 SITL 重启时 sim clock 归零倒跳（px4ctrl Rate 锚定旧值冻结） | sim 时间域存在跨重启跳变；单会话内未观察到 |

## W1 双目同步性（bag 实测）

### t2_A_173156.bag（静置22s+起飞爬升+悬停10s，900帧对，static 830/motion 70）

| 检验 | 静止段 | 运动段 | 比值 | 判定 |
|---|---|---|---|---|
| 1 dy-RMS (px) | 2.159 | 1.614 | 0.7 | 平稳（corr(dy,\|ω\|)=0.11） |
| 2 视差中位帧间步进 (px) | 0.860 | 0.766 | 0.9 | 平稳 |
| 3 光流-IMU 残差 L (px) | 0.285 | 5.424 | 19.0 | 平稳（L/R 残差 corr=+0.98 同相） |
| 3 光流-IMU 残差 R (px) | 0.287 | 5.507 | 19.2 | 同上 |
| 4 互相关错拍率 | 0.526 | 0.071 | — | 平稳（静止段 NCC 平票噪声底；NCC_same 0.9008 vs NCC_next 0.9005） |

**bag-A 判决: H-A 排除**（0/4 异常）。检验3 的 19 倍残差为平移流主导（陀螺预测仅旋转分量），左右同相 → 非错拍签名。规则修正记录: 初版以比值>5 判检验3，被平移流误触发，已按任务书原文改为反相签名（corr<−0.3）。
备注: 静止段 dy-RMS 基线 2.16px（合成数据 0.065px）→ 双目存在静态垂直失配（≈0.24° @ f=468），对 VINS LK 匹配可容忍，关注但不阻断。

### W2 新 IMU 流质量（t2_A bag 实测）

| 话题 | n | 倒退 | 重复 | 有效率 | 周期 std | max 间隔 |
|---|---|---|---|---|---|---|
| /mavros/imu/data_raw | 6705 | 0.00% | 0.00% | 125.0Hz | 1.90ms | 12ms |
| /mavros/imu/data | 2682 | 0.00% | 0.00% | 50.0Hz | 1.55ms | 24ms |

**P1 的脏流在今日会话不复现**（且 P1 脏流在 imu/data 非 VINS 消费的 data_raw）→ H-D 降级为次嫌疑；E06/E07 仍测 td。

## W3 调参矩阵（进行中）
### t2_B/C/D/E 补录批（W1 终局，修正规则后）

| bag | 内容 | 检验1 dy | 检验4 错拍率/margin | 判决 |
|---|---|---|---|---|
| B (65s 慢巡航) | 全程静止级角速度 | — | — | 排除（0/4） |
| C (26.7s 快冲刺, 无静止段) | dy 运动段 0.406px | 错拍率 0.068, margin −0.013(同帧胜) | 排除（0/4；初判"证实"系 nan 基线伪影，规则已修） |
| **D (36.1s 纯 yaw ±120°×3，决定性)** | **dy 0.058px** | 错拍率 0.264 但 margin −0.029（同帧 NCC 恒胜） | **排除（0/4）** |
| E (30.4s 降落) | 缓变 | — | 排除（0/4） |

## W1 结论（H-A 裁决）

**H-A 排除**。四项检验在五段激励（静置/起飞/慢巡航/快冲刺/纯旋转/降落）上全部平稳：
- 极线: 纯旋转 dy 0.058px（亚像素），与角速度零相关 → 两相机旋转完全同瞬
- 互相关: 同帧 NCC 恒 ≥ 次帧（margin 恒负）→ 无一帧错拍
- 光流-IMU: 左右残差同相（+0.98），无单目滞后签名
- 视差: 无运动相关抖动
两个独立 camera sensor 内容同步，A7 崩溃根因不在渲染错拍。主嫌疑转向 H-B（外参）/H-C（参数×20Hz），H-D 降为次要（今日流干净）。
备注: C/D 段光流残差 inf（高空场景角点<15 不可算），检验3 在 C/D 不可用，由检验1/4 承担裁决。

## W5 在线闭环（2026-09-27 深夜）

### 时间域分裂发现（W5 关键卡点与破局）
| 会话 | 图像戳域 | IMU 戳域 | 域差 | VINS init |
|---|---|---|---|---|
| bagA (W2 第一段) | sim (15.7) | sim (15.7) | 0ms | ✓ 16.7s 静态段完成 |
| bagB–E (W2 后续) | unix | unix | ~40ms | ✗（另因：窗口毒槽位） |
| t2w5_p1/p1b | sim (19.9) | unix (1.79e9) | **1.79e9 s** | ✗ 220 次门控拒绝 |
| p1b 戳平移后重放 | unix（平移 +1.79e9s） | unix | 配对 med 偏差 <10ms | ✓ 即刻完成，0 拒绝 |
| t2w5_p2b（sim 域统一配方） | sim | sim | 0 | ✓ 在线闭环 init 成功 |

机制：gazebo 相机戳=sim 时钟；mavros IMU 戳随 use_sim_time 标定域。共享 roscore 的 use_sim_time
被并行会话（或启动序）改变 → 两戳分家 → VINS 永无法对齐。**修复配方：全 sim 域**（use_sim_time=true
在 mavros 启动前置）+ p1b 数据经 t2_shift_img_stamps.py 平移后离线等效验证。

### W5-1 并行 ATE 验收（等效证据）
- **bagA × E20（最终配置+全补丁）: ATE 0.137m / 52.6s / 无发散 / yaw 漂 0.22°** → 达标（<0.3m@60s, yaw<5°）
- p1b（px4ctrl 剖面）平移重放: init 后 26.5s（起飞瞬间）发散——px4ctrl 起飞段 6g 加速度尖峰（IMU |a| max 59.3）超出当前 VINS 20Hz 参数化承受力

### W5-2 VINS 闭环（t2w5_p2_215545.bag）
- ✓ VINS 在线初始化（sim 域配方后首次全链成功）
- ✓ 门控转发工作: vision_pose 1320 帧喂入，无 e17 级爆炸（|P| max 60.9，门控挡住跳变但挡不住平滑漂移——设计边界）
- ✗ VINS 机动段漂移（末端 (-49,0,-36)）；EKF2 odom 到 goal 最小距 7.04m（z 曾 -4.4）
- **到位验收被上游阻断**: goal(7,-4,1) 飞行在 EKF2 基线（无 VINS 参与，t2w5_p1/p1b）同样失败
  （T1 smoke ×4 FAIL @20:12 前，T3 收尾注记 P1 根因=规划链 yaw 甩头 transient+RLS/盲图）→ <0.5m 到位
  验收当夜对任何 odom 源不可达，量化差距 7.04−0.5=6.54m

### W5-3 EKF2 回归
t2w5_p1/p1b 即 EKF2 源控制飞行（VINS 未接管）: 起飞/悬停正常，goal 到位失败同上 → 回归结论与 T1/T3 观测一致，非 VINS 改动引入。

### 量化差距汇总（为何未打 tag）
1. goal 到位: 7.04m vs 验收 0.5m（阻塞在规划/控制链，T3 已根因，非 VINS 层）
2. VINS 在 px4ctrl 剖面下漂移: 60m@240s vs 温和剖面 0.137m@52.6s（加速度尖峰 6g vs <1.5g）
3. bagB–E 离线重放 init 毒槽位（Vs[i]=e25 非有界写入产物，疑上游 UB）未根治，门控转为安全拒绝


# U1 毒槽位根治(2026-09-28 凌晨,T2b)

## 机制级根因(插桩+dump 铁证,证据链完整)

**写入者:processIMU 传播;毒源:跨时钟域 dt=1.79e9s。** 非无界写、非 UB、非 ceres。

四路插桩(estimator.cpp, U1DBG×E20×bag-B 原始重放)第一行即命中:

```
T2POISON src=IMU-prop fc=1 j=1 |V|=1.196e+25 dt=1.791e+09 |acc|=9.873 detR=1.7e30
```

逐帧序列:fc=1 → e25,fc=2..10 → e40(每帧一个新槽位,窗口满后 fc=10 反复累乘)。

### 完整因果链

1. **bag-B/C/D/E 图像戳=sim 域(15.6~149s),IMU 戳=unix 域(1.79e9)**——dump 首帧实测
   (图像 hdr 15.644 vs IMU hdr 1790502951.6,域差 1.79e9s)。W5 账本"bagB–E 均 unix 域"
   系记录错误(混淆 header 与 arrival;arrival 均为 unix 墙钟)。成因与 W5 在线域分裂同源:
   录制 roscore 的 use_sim_time 被并行会话翻面,仅 bagA(W2 第一段)全程 sim 域幸存。
2. VINS `getIMUInterval(prevTime, curTime)`:图像域 curTime≈15.x,IMU 戳 1.79e9 > curTime,
   收集循环 `while(front < t1)` 恒假 → 每帧只交出 1 条 IMU(尾部无条件 push front),
   `dt[0] = 1.79e9 − prevTime` 每帧恒为 1.79e9。
3. `processIMU` 以 dt=1.79e9 传播:`Rs[j] *= deltaQ(un_gyr*dt)` 三角函数溢出 →
   Rs 烂化(插桩 detR=1.7e30);`Ps += 0.5*dt²*un_acc` 与烂化 Rs 的 un_acc 连乘 →
   Vs e25 → 后续帧继承毒值 → e40。
4. 后置 init 门拒绝 → reinit(clearState)→ **域分裂是数据属性,不变** → 下一窗口逐帧
   重演 → "确定性复生"。逐位跨二进制一致 = 同一确定性 dt 序列。
5. 账本未解之谜的槽位分布解释:i=1(每窗口首个传播槽位吃 dt[0])、i=10(窗口满后
   每帧累乘);176/220 落 i=10 因 init 快照时刻它累乘最多。

### 嫌疑清算(任务书 1a)

- α `solveGyroscopeBias` Bgs 无界写:**排除**——写循环 i≤WINDOW_SIZE 有界,且只写 Bgs
- β `Headers[i]` 无界推进:未及深查(α/根因已定,毒源与拷贝循环无关);v3 已修拷贝行界
- γ `ImageFrame.pre_integration` 所有权:**泄漏非 UAF**——`all_image_frame.clear()` 条目
  裸指针直接丢弃不 delete(clearState 已 delete tmp_pre_integration,无 double-free);
  累计泄漏量级:每 reinit 窗口 11 条 × IntegrationBase(~KB 级),不阻断,暂不修(登记)
- 附带发现(死代码):后置门 reject 分支 `return` 写在内联重置代码**之前**,
  重置段 unreachable——实际重置由 processMeasurements 循环头 reinit_request 消费者
  (clearState+setParameter)完成,行为正确,但死代码易误导,已清理(见修复清单)

## 修复(双层)

| 层 | 修复 | 位置 | 性质 |
|---|---|---|---|
| 数据面 | bag-B/C/D/E 图像/camera_info 戳平移到 IMU 域(t2_shift_img_stamps.py,配对中位偏移 +1.79e9,p5–p95 散布 <0.02s) | 生成 ~/sitl_sim/bags/t2_[BCDE]_shift.bag | 存量数据可用化 |
| C++ 防线 | processMeasurements dt 钳制:dt∉[0,0.5] 或非有限 → 置 0(该样本只更新 acc_0,不传播不进预积分),ROS_ERROR 限流告警 | estimator.cpp processMeasurements IMU 消费循环 | 任何跨域/乱序/复位瞬态不再产毒;0.5s=125Hz 步长 62 倍裕量 |

附带修复:后置门 reject 分支 unreachable 内联重置代码删除(死代码,行为已由 reinit 消费者覆盖)。

## 三连回归

| 项 | 结果 | 判定 |
|---|---|---|
| ① bagA×E20 | ATE 0.137m/52.5s/无发散/yaw 0.22°(基线 0.137m) | ✓ 零退步 |
| ② bag-B(shift)×E20 | `Initialization finish`(历史首次)ATE 0.1186m/64.9s/无发散/yaw −2.9° | ✓ |
| ②' C/D/E(shift)×E20 | init 全通(C/D/E 历史首次);ATE 可算:C 31.2m@7.0s 发散、D 767m 立即发散、E 11.0m@15.2s 发散 | ✓(可算);跟踪短板移交 U3/U4(D 不满足豁免条件,记 U4 靶点) |
| ③ 确定性 harness bag-C(shift)×E20×3 | md5 三轮全一致 `a6e07acc9390b6a5c52200e4ed619bfd` n=246 | ✓ 真确定(v1/v2 悬案裁决) |
| 死代码删除后 bagA 终验 | ATE 0.1372m,与基线一致 | ✓ |
| 额外:bagA 首帧 dt=16.7(prevTime 初始 −1)被钳 | 原版靠 fc=0 不传播侥幸无害,钳制后显式安全 | ✓ |
| 额外:bag-B 中途 dt=−0.54ms(IMU 乱序)被钳 | P1 脏流类问题同防线覆盖 | ✓ |

## 对既有判决的冲击(→U2 复审依据)

- W3 矩阵 bag-B/C/E×全 28 变体的行**全部无效**(输入数据跨域,与配置变量无关)
- "E03-on-B td 漂 −190s"极可能是跨域伪影(td 估计器把域差学走)→ U2 重审
- W5 p1b"戳平移后即刻 init"与本根因完全一致(平移消除跨域)
- H-B(外参)/H-C(参数)嫌疑的 B/C/E 段证据全部要重采
