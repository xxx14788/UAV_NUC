# R2 修复面设计笔记——前端观测质量筛查（far-feature observability screen）

- 写表：2026-10-01 19:45（T2 R2 收口后设计稿，供下场实施；本轮未写码——按任务书「可修→单变量修+gtest+README§3 登记+在线验证轮」流程）
- 前提（R2 九格实证）：估计器内部六类防线全数无效；载体=55-64s 场景段观测内容×0.1m 基线立体几何的量程内垃圾深度（motion2 ok p95=487m / stereo ok p95=39.5m），经 est:1324 入场门无筛查腐化任意窗口状态。
- 设计原则：**把筛查看守从解算环前移到观测入环前**（唯一未被九格触达的环节），且必须同时覆盖 stereo 与 motion2 两源（单禁 motion2 已证不救）。

## 候选机制（按证据强度排序）

1. **视差-深度可观测性门（首选）**：0.1m 基线下深度相对不确定度 ≈ 基线不确定度/视差。立体分支入口（fm.cpp:394 前）对每特征计算 disparity=|u_L-u_R|；disparity < d_min（如 3px ⇒ Z>~15m@fx468/B0.1）的特征**不入 estimated_depth 写点**（跳过或直接 erase），等价于「远特征深度不可观测则不产测量」。
   - 理由：stereo ok 垃圾集中在 p75=24m+（远距），近距立体解在九格中从未单独定罪；远特征深度方差是 est-svd 分家（rel P50 0.849@远距）的机理根源。
   - 风险：远特征全删可能弱化尺度/俯仰约束（悬停期远地面点）→ 需保底：仅当窗内近距特征数 >N_min 时才启用远特征剔除（自适应），或保留但不写深度（不产测量=不约束位姿）。
2. **解算侧 inv_dep 先验加权（次选）**：入场门处给 inv_dep 加先验因子（均值=stereo 解，σ 按 disparity 传播）而非无信息初始化。改 ceres 图，工作量大于机制 1。
3. **出场阀对称修复（观察项，非独立修复）**：px10 已证保池不救——排除其独立成修的价值，仅作机制 1 的配套观察列。

## 开关化纪律（沿用 t2_* 族约定）

- 新键建议：`t2_min_disparity`（px，默认 0=关=上游行为逐位不变；canonical 不动，验收矩阵仍跑 cf0384 栈）
- 作用点：feature_manager.cpp stereo 分支（L394-445）与 motion2 分支（L461-511）入口各一处判据 + [T2depth] census 增 `flag=far_drop` 标签（可观测性要求：每格可判开关活性）
- 判别格设计（预注册要点，下场先写全表再跑）：canonical vs t2_min_disparity=3 两格于 032005 袋；判据=首 fail 时刻带 [129,139] 外移或消失 + vis_n@60s bin 不坍塌 + far_drop 计数>0；回放域结论入机理账，RESCUE 则进在线轮（SITL 锁窗）
- gtest：仿 test_t2_depth_gate.cpp 增 test_t2_min_disparity.cpp（构造已知 disparity 特征验证门行为/关闭时逐位一致）
- README §3 登记：键名/默认值/作用行号/证据指针（R2 台账行）

## 关联挂账

- init_replace 计数器补 shift 再注入计数（fm:662 处 +1 或 judge 侧用 census 口径）——低成本工具债，下场随手修
- 在线 adjudication（C-4）：若机制 1 RESCUE，在线轮同场景验证=对 R2 输入域判决的在线复核，一石二鸟
