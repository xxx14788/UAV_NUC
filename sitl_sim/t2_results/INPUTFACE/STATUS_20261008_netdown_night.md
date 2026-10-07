# T2 v10.4 断网夜 STATUS 夜报 + 恢复执行清单（2026-10-08 凌晨）

> 会话：T2 v10.4（INPUTFACE 分带标定主战版）。执行环境：Windows 主机（D:\drone_VINS）。
> **外部阻塞**：AP（uav123-5G）自本会话开工起从空气中消失（多轮 netsh 扫描+隐藏网络连接+接口重置尝试[无管理员权限]均失败）；NUC tailnet 离线 4h+；**3090（执行域）不可达**——任务书 3090 侧全部实测件阻塞。
> 应对：AP 监测后台运行（`plans/ap_watch.sh`，45s 周期，恢复即退出通知）；本夜转本地可完成件（工具+设计件+预注册，零偷懒全落）。

## 一、本夜完成清单（本地）

### 工具件（3 个，全部 py_compile/语法+功能验证过）

| 工具 | 版本 | 验证态 | 位置 |
|---|---|---|---|
| t2_bag_editor.py（输入编辑回放器：retstamp/retiming/repaint 三模式+dry-run+域检查+参数化重生成 manifest） | v1.1 | py_compile ✓ CLI ✓；**3090 rosbag 功能验证待网** | scripts/ |
| t2_bias_probe.py（1b 第 0 步 mavros bias 话题有效性探测：存在/非零/频率/合理性四判定） | v1.0 | py_compile ✓；**实测待网** | scripts/ |
| t2_domain_quantiles.py（1a 分域分位采样：world 实读域标签+三键模糊匹配+p5-p95 带+充分性检查） | v1.0 | py_compile ✓ **功能冒烟 ✓**（双域假数据分位带正确） | scripts/ |
| t2_m3p_batch.sh（M3' 批编排器：单轮发射制+侧锁+pgrep 互斥预检+STATUS 预告） | v0.9 框架 | bash -n ✓；**LAUNCHER/GATE_YAML 两适配点待 3090 核对** | scripts/ |

### 文书件（5 份，含 2 份冻结级预注册）

| 文书 | 性质 | 位置 |
|---|---|---|
| 1c 三臂设计件+判据预注册（判据逐字冻结：消除=j0<1m/改变=时刻>2s 或幅值>30%；δ 梯度 6 点冻结；34 轮预算） | **预注册冻结级** | staging/INPUTFACE/1c_design/ |
| 1b bias 三件套设计件+预注册（第 0 步判定门+③预热段参数冻结[8s/±30°yaw/±0.3m]+①FEED 三风险审计+②约束设计+SITL 外推性声明） | **预注册冻结级** | staging/INPUTFACE/1b_bias_route/ |
| 1a 方法论定案（三案对比+推荐案甲分域阈值+保守回退条款+§5 推导规则冻结[m=0.5/最小分离度门]） | 定案文书（推荐已定，数字待采样） | staging/INPUTFACE/calib_domainspec/ |
| REGEN-PREREG v2 模板（语义/规则/判据三层冻结+数字槽位；失败语义预注册：绿格降>10pp 或毒格假绿↑=回滚） | 模板（填数即 v2.0-FROZEN） | staging/INPUTFACE/regen_v2/ |
| C.10 勘误索引 v0.5（本地 9 行注记**已执行已验证**+3090 待扫清单） | 索引（本地部分完成） | staging/INPUTFACE/c10_jump_caliber_errata/ |

### 补丁执行

- C.10 口径注记：b_line_report 5 行+migration_plan 4 行（行尾 HTML 注释，diff 验证恰 9 行变更零误伤；.c10bak 备份在位）。

## 二、诚实对账（对任务书保底清单）

| 保底项 | 状态 |
|---|---|
| ①跨域分布数据+方法论文书 | 方法论 ✓；**分布数据阻塞**（袋在 3090） |
| ②REGEN v2 冻结 | 规则层冻结 ✓（模板）；**数字层阻塞**（依赖①） |
| ③M3' 批执行或错峰记录 | **阻塞**（编排器就绪，3090 不可达） |
| ④IMU-CAL-FEED 第 0 步验证+设计件+预注册 | 设计件+预注册 ✓；**第 0 步实测阻塞**（需 SITL 活会话） |
| ⑤STATUS 诚实夜报 | 本件即是 |

**双必达对账**：单元 1a 分带标定=方法论+工具+规则就绪，**数字层未达（机器不可达）**；REGEN v2 冻结=同。按 T1 册同款条款"机器不可达除外"如实登记——**非收工违规情形，但恢复后双必达为第一优先**。

### 单元 0b 审签件状态

T1 单元 1c 实机 config v0 出稿依赖 3090/NUC（T1 同样断网阻塞）——本夜无稿可审；**恢复后主动查 T1 台账**（审签回执 90min 时限从见稿起算）。

### 单元 0 承件核对

v10.3 断档承件（M2/M3 产物在盘确认+悬停 8.5m 销号）——**阻塞**（盘在 3090），并入恢复清单第 0 步。

## 三、网络恢复后执行清单（契约：按序速决）

```
0) 连通性：ssh nuc2 date+df；git pull；v10.3 承件核对（M2/M3 产物+悬停 8.5m NUC bag 指针=T1 已答，销号）
   STATUS 开工行补登（含断网夜说明）；本 staging 目录 scp 上 3090 入 t2_results/INPUTFACE/
1) 1b 第 0 步（30-60min）：起 SITL+mavros → t2_bias_probe.py --duration 10 →
   报告落 1b_bias_route/step0_probe_report.json → VALID/NO_VALID 按预注册分叉
2) 1a 采样：名册冻结（plain/obstacles 健康轮各 ≥5）→ 适配 t2_domain_quantiles.py 读真实指标文件 →
   domains_dist.json → 充分性 PASS → §5 规则生成 gate_params_v2_draft.yaml
3) REGEN v2.0-FROZEN：模板填数+基线抄录（v1 十八轮格级绿率，台账正源）→ 冻结声明+sha256
   ★ 至此双必达闭环 ★
4) M3' 批：t2_m3p_batch.sh 适配点核对（LAUNCHER/GATE_YAML）→ --dry 全预检 → v2 臂 18 轮
   （STATUS 预告+锁；与 T4 E4 错峰；1c 回放互斥遵守）
5) t2_bag_editor.py 3090 功能验证（E8P 标本 dry-run：域检查+配对率+mono-viol=0）→
   1c baseline 重放 2×2 → 三臂按设计件 §4 预算
6) C.10 3090 侧扫（t2_experiments.md 等全库 grep+判行）→ 索引升 v1.0
7) 台账 t2_experiments.md 双落账（断网夜+执行夜）+git push
```

- 互斥提醒：4 与 5 同机互斥（M3' 飞行窗禁 1c 回放）；5 的编辑袋用后即删+df 对账。
- 若 AP 长期不恢复：本清单即下夜开工序；用户侧需物理重启 AP（远程不可修复——SSID 消失+隐藏连接失败=设备级故障）。

## 四、坑登记（本夜新增）

1. **AP 消失型断连**（与 10-06"原路由 SSID 消失"同族）：netsh 接口重置需管理员权限（非提权 shell 无解）；隐藏网络 nonBroadcast 连接对非目标隐藏 SSID 无效。应对=ap_watch.sh 监测+本地转产。
2. Windows 原生 Python 不识别 MSYS 路径（/d/...）——本地脚本验证一律用 D:\ 绝对路径。
3. Git Bash 终端 UTF-8 显示乱码≠文件损坏——文件级验证必须走 Python utf-8 读回断言（本夜 C.10 补丁验证实操）。
