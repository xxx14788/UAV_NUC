
### 场景分门口径勘误与正源落地（2026-10-01 20:5x-21:0x；第二波勘误+round_result 分门+runbook 核签）

**勘误声明**：18:36 落地的 wa_gate 场景门（第二波）把 xline 的 **J0 锚差门**改成了场景门（obstacles 锚差门被放宽到 0.75）——**改偏了对象**。任务书 v8.0 原文="到位门=场景分门 0.5/0.75；**双口径与 J0 判据（锚差>0.5m 一律 FAIL）不变**"：分门对象=四指标的**到位距离门**（判定在 round_result.sh），J0 锚差门恒 0.5 不分场景。第三波修正回滚 j0 门恒 0.5；历史轮无实质影响（今晚分门后无轮发生判决翻转——历史 j0 值域两端远离分界，且 18:36-21:00 间无人用分门版 wa_gate 判过新轮）。

**修正后的正源分工**：
- **round_result.sh**（双副本 md5 对齐）：到位门场景分门——`GATE = 0.75 if 'obstacles' in world else 0.5`（world 参数本来就在手，第 5 参，原用于 box_D/E）；leg1/leg2 到位与打印带门值+场景审计痕；J0 跳变门/避障/频率/降落门不动。
- **t3_wa_gate**：J0 锚差门回恒 0.5（xline_pass/t1d1/failed 三处）；scene_of_run/gate_m 保留为审计报告面（xline 增 `j0_gate_m: 0.5` 常量字段，一行判决标签 `arrive_gate=`）；four 继承 RESULT.txt 读值不重算（保判读一致）——round_result 分门后 four[0] 自动继承场景门。
- **回归四绿**：回放轴 selftest 3 cell PASS+在线轴 4 cell PASS（合成 cell 重写=双门语义断言：J0=0.6 两场景一律 FAIL+到位 0.6 按 round_result 语义 no_obstacles 不过/obstacles 过）；round_result.sh 用 WC2OBS1 袋双 world 对拍（obstacles→`<0.75`/sitl_world→`<0.50` 打印生效，该轮 min=1.288 两门均不过，J0 369.8 门恒定性一致）。
- **历史轮重判影响=零**：现存轮 j0_jump 值域（0.1 级健康/2.4+爆）两端远离 0.5 分界；到位指标方面 WC2OBS1 系列 min>0.75 亦无翻转；X 线新轮起分门生效。

**T4 runbook §3 核签**（sim2real_runbook.md 场景分门建议稿，T4 v5.0-W5a）：T3 已核签转正式，三注记=①数值与 wa_gate/round_result 实现逐字一致；②正源分工如上；③书-器差如实标注——建议稿"连续 3s"为实机域判读语，SITL 实现口径=航段窗内 min<门（历史判据，任务书"双口径不变"支持），SITL 若需改连续驻留判据属判据增改须用户另行裁定。

**Z1.2 前置现状登记**：任务书前置"E-4 的 0.5 接线结果"——查 t3_z1_failsafe_design.md 35 行，"0.5 接线分叉"系输出侧防线（max_angle=25° 限幅+thrust 饱和）与 D8/EKF2 消费方式的分叉，**挂 C01 卡点+T1-E1 裁决后一并接线**；T1 P1-2 已把 v2 代码入库（enabled_v2=false，翻转权归 T3-Z1.2）+E-4 首窗已产 EV 域数据（EV_CTRL=15 激活实证/ev_vpos ratio 0.32 门内零超）但 E1/0.5 分叉裁决未见落定——Z1.2 翻转维持等待（双前置之 E-4 侧未闭），@T1：E1 裁决/0.5 接线分叉定案请 STATUS 示下。
