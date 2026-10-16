# depth 分歧点诊断报告 v2（③C-甲合流册 v5.2 §一A.2.d；答案义务件·勘误版）

> 执行者：v5.2 执行者，2026-10-17 01:19-04:30 会话。
> **v2 性质=勘误+机制突破版**：v1 报告（01:5x 落盘）的"自愈"结论**错误**——那是采样窗伪影（探针只采前 5 帧，恰好落在死亡前的活帧窗口）。v2 以逐帧长探针重证，机制层取得确定性突破，根因仍未定案。v1 存档不删（时间线证据），以本版为准。

## 一、核心机制定案（逐帧长探针铁证）

**病=传感器渲染在创建后 ~1 秒（10Hz 传感器第 9-10 帧后）确定性永久死亡**：
- 死后传感器话题**继续按 update_rate 发布**（插件定时器重发死缓冲），RGB=均匀色（clear color，均值 102-178、std=0.0），depth=全 NaN——与总设计师三联征完全吻合。
- 逐帧证据（min2，60s 长探）：t+3s 时 8 帧 healthy（rgb_std=48.3/depth 有限像素爬升）→ t+4s 起 578 帧中 0 帧活。**60s 内共 9 帧活**。
- 帧率无关：30Hz 传感器同样 ~1s 死（25/833 活）——**时间基而非帧数基**。
- 悬停/物理无关：/clock 全程 1:1 推进、model_states 持续、模型在。

## 二、存活矩阵（谁活谁死）

| 配置 | 类型 | 结果 |
|---|---|---|
| 静态 world 内传感器（camera 或 depth；min2 或 v9 world；10/30Hz；Xvfb swrast 或真 GPU :0） | 任意 | **~1s 死** |
| 全栈动态 spawn·stereo 双目（v7.3/v9 world，30Hz，camera 型） | camera | **活（571/571、714/714 全程）** |
| 全栈动态 spawn·深度相机（生产 openni 链，v7.3/v9 world） | depth | **死** |
| 旧 NUC（数周末跑过 gazebo、无窗口期操作）min2 同款 | depth | **死（1/600）** |

## 三、排除矩阵（全部阴性）

环境变量（/proc environ 整包回放对照/GAZEBO_*/use_sim_time/PX4 env/devel/setup.sh）、cwd、gazebo master 残留（曾造成一批假阳性，见坑账）、mesa shader cache+rtshaderlibcache（清空复测）、八包重装（gazebo 家族，用户授权域）、X 显示器（Xvfb :99 重启/真 GPU :0 root+gdm authority）、GL 库解析（407 共有 soname 零差）、OGRE 材质脚本集（21=21 同）、真值物理（/clock 正常）——**全部无法阻止或引起**死亡；死亡对上述变量不敏感。

## 四、诊断过程中的三次结论翻转（诚实记录）

1. "自愈"（01:19-02:40 多轮 RECOVERED）→ 伪影：探针采前 5 帧=活帧窗口。
2. "环境绑定（GAZEBO_RESOURCE_PATH 等）"（02:41-02:5x 一批 STILL-BROKEN）→ 伪影：残留 gzserver 占 11345 端口造成 bind 失败降级+探针起跑晚于死亡窗。
3. "机器级（仅 3090）"→ 推翻：旧 NUC 同款 kit 同病。
**方法论教训（入坑账）**：判活必须逐帧长探（≥60s）+ 起跑前残留断言 + 报告死帧占比，禁用"前 5 帧健康=RECOVERED"式短窗判定。

## 五、根因收敛（未定案，候选排序）

- 已证明：非文件态（A.1 三步+总设计师四轮）、非 GPU/GL 后端、非 ROS 环境、非缓存、非 gazebo 包文件（重装无效）。
- 剩余候选域：gazebo 渲染线程调度/条件变量饥饿（gdb 快照：SensorContainer::RunLoop 线程死后阻塞于 pthread_cond_wait；立体相机存活=渲染循环本身健康→**病灶在 depth 传感器/静态传感器的渲染触发链**）；两机同病+3090 无安装记录 → 嫌疑收敛向"两机共享的长期潜伏软件状态/上游 bug 被某共同条件激活"（共同条件候选：同一 Xvfb 参数形态/同一 kit/同一 kernel 时域？未证）。
- 05:42-08:07（10-16）终版批 S 形绕行实证=depth 当时全程活 → **3090 的动态 depth 死亡确有 08:07-11:12 起病窗**；NUC 无起病窗记录（数周未测）。

## 六、止损与呈报（任务书 §一A.5 执行）

- 两轮深诊断已尽（轮1=strace+环境矩阵；轮2=gdb+存活矩阵+rate/clip/cache/GPU/NUC 核查），根因未定案 → **止损触发**。
- **迁移路线（A.5 首选升级路径）已去风险核查：旧 NUC 同病 → 迁移不可行**。
- 呈报用户三径：①深水区（nvidia/内核/还原点——用户域）；②v9 条件态收口（13m 扩展层为主证据层，保底不损——任务书 §二.3 预案）；③工程 workaround 立项（如 stereo 活流→depth 桥接=架构变更，须总设计师+用户裁定）。
- 复发/持续监视：min2+长探针（min2_longprobe.py 60s 逐帧）=新标准复测件（替代 20 秒短窗判定）。

## 七、证据链（全部在 ~/sitl_sim/c3_corridor_20261013/depth_v52/）

- v52_trace_depth/ v52_trace_camera/（修复前双 trace，健康窗采集）、v52_prod_trace/（病态生产栈 trace+ogre.log）、/tmp/v52_gdb_bt.txt（137 线程快照，死者线程栈）、v52_clean_depth/、长探针输出（本报告 §一 数字的原始流）、A1/A3 取证与重装日志。
- 工具：min2_longprobe.py（**新标准判定件**）、min2_probe_v52.py（短窗，保留作对照）、min2_strace_run.sh、prod_strace_capture.sh、bisect_cell.sh、min2_gzplugin.world（纯 gazebo 插件变体）。
- 关键时间线：总设计师 21:00/21:20/22:35/23:05 四行+depth_regression_forensics.md；本册 STATUS 01:08-04:3x 各行。
