# 探针 img_fp 面开销预算预注册 v1

- 登记：T1 / 2026-10-04 18:3x / 任务书 v11.2 单元 1 ③（开销预算预注册要求）
- 实现：t1_r3x_probe.py 新增 face=img_fp（随 5s 窗口聚出账，与既有面同构）。

## 语义

- 订阅面：`/iris_stereo_vins/vins_cam_left/image_raw`（仅左目）。
- 每帧：md5（原始字节）+ 灰度 mean/std（mono8 直读；bgr8/rgb8 通道均值；其他编码仅 md5）。
- 窗口聚（每 5s 一行 jsonl）：`n / dup_n / dup_run_max / gap_p50_ms / gap_max_ms / mean_med / mean_iqr / std_med`。
- **判别器语义**：`dup_run_max≥2` = 字面冻结帧运行（相机流停止更新但仍在发的直接证据）；`mean` 阶跃/漂移 = 内容级异常线索；`gap` = 流饥饿。
- **判读口径：在线面=发现面，不进门**——任何线索记录为事件证据供离线对账（与 img_xaudit 判据体系分离），不做 PASS/FAIL 门。

## 开销预算（冻结）

- 单帧处理 ≤5 ms（md5@640×480 mono8 ≈1 ms + numpy mean/std ≈1.5 ms；@30Hz ≈7.5% 单核）。
- 订阅 `queue_size=1` + `buff_size=2MB`：背压时丢帧不阻塞发布链路；探针永不反向施压被测系统。
- RAM 增量 <1 MB（3×4096 环 + 计数器）；磁盘增量 <0.1 MB/h（每 5s 一行聚）。
- **超预算处置**：该面作废声明（沿用 v11.0 探针预算作废条款），其余面不受累。

## 部署模式

- 随轮手工附着：`t1_r3x_probe.py <round>/r3x_probe.jsonl --mode online`（默认 `--max-run 1800` 防僵尸——本日 6 僵尸事故的机制修复，进入轮字典典）。
- harness 内建接线挂池⑤"栈号跟随机制"（T2 裁示后落，协调窗纪律）；并轮战役期间由本线按轮手工附着并在 STATUS 报点。
