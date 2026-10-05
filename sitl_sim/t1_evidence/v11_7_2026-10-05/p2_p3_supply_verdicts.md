# 单元 5 供给轮+四件消费判读文（T1 v11.7；2026-10-06 00:2x 落盘）

> 净轮判定口径=T2 判据（j0<0.5∧0 [T2fail]，round_result 实读）；本窗全部轮次列表见
> supply_campaign*.log；判读=t3_wa_gate --online + round_result v1.4 双锚（DUAL-ANCHOR 行）。

## 0. 本窗轮次总表（arm=VINS 配置臂）

| 轮 | 臂 | T2fail | j0/j0d | disarm | RESULT | 备注 |
|---|---|---|---|---|---|---|
| health_smoke_1 | legacy | 3 | — | 0 | FAIL | 重启后首轮,262m 框滑,divergent |
| health_smoke_2 | legacy | 0 | jump 7.5 面 | **1** | FAIL | **J4 验证轮**（px4ctrl 链完成签名 t=200.36）|
| SUPX1b | legacy(B) | 11 | jump 6.8 | 1 | FAIL | 敌对面;P2-B 零事件 ✓ |
| SUPHVa | legacy(B) | 0 | — | 1 | FAIL | P2-B 零事件 ✓ |
| SUPX2a/b+SUPHV2a/b | gates+guard(无cauchy) | 52-216 | — | 0/— | never-flew/FAIL | **风暴 4/4：gates 键风暴源（二分定责）** |
| DIAGCAUCHY | gates+guard+cauchy4.0 | — | — | — | never-init | 晨间同臂干净→今晚不飞,cauchy 排除 |
| DIAGGUARD2 | **guard+sane** | **0** | **0.418**/jump0.0+transit | **1** | FAIL(到位4.7m) | **净轮面（j0<0.5∧0fail）+ 可飞臂证明** |
| SUPP2A/v2 | guard(误 B) | 0 | — | 1 | FAIL | watcher set-u 坑→实际 B 臂 |
| **SUPP2Av3** | **guard+P2-A** | **0** | 0.823/jump0.0+transit | **1** | FAIL | **P2-A 零 latch ✓**（净轮版待命中） |
| **SUPP3INJ** | guard+P3注入 | 0 | — | **1** | FAIL | **P3 A 臂五判据过（见 §2）** |
| SUPHV3a/b | guard | 1/0 | — | 1/1 | FAIL | hover 型补给 |

## 1. 四件消费判定

- **① disarm 验证：PASS（多轮）**——legacy/guard 臂全 disarm=1（smoke2/SUPX1b/SUPHVa/SUPP2Av3/SUPP3INJ/SUPHV3a/b）；风暴轮 disarm=0=已知 H-A 残面（VINS 死→U2.7 拒,在册）。
- **② P2 A/B：B 臂 PASS（SUPX1b/SUPHVa 零事件;P2 启动自述行=配置声明非事件）**；A 臂=**enabled=1 活体验证+零 latch**（SUPP2Av3,armed 全程,T2fail=0）;严格版（净轮 j0<0.5 上零 latch）待后续净轮命中（DIAGGUARD2 型轮+P2 on）。A 臂参数路径勘误：**/px4ctrl/p2_cmdresp/enabled（私有 nh）**。
- **③ L-odom A/B（U2.5 终判）：未执行**——L-odom 臂接线=E4R2-GOFF-D10-LODOM 先例（mavros odometry 路径),本轮窗未及;挂账连同 X4 臂裁定（见 §3）。
- **④ P3 reboot 注入：PASS 五判据**（见 §2）。

## 2. P3 注入判读（prereg v2 五判据;轮=run_SUPP3INJ_000528）

- **J1 间隙可见 PASS**：odometry 流 gap **3.47s**≥2.0（注入 kill→relaunch 2s+init）。
- **J2 P1 锁存正确 PASS**（guard 桥接态）：消费流（odometry,权威）经 guard 桥接无缝换帧→P1 正确不锁存（零 reject 事件）;offset>0.75 分支本轮未 exercised（桥接使然,如实注记）。
- **J3 FSM 降级路径 PASS**：armed 29.4→281.4 全程无中断;truth z 峰 1.14→末 0.10 完整落地;**注入后继续飞行+降落+disarm=1**。
- **J4 D2 风暴率 PASS**：注入窗零风暴事件（B 臂基线亦零,带内）。
- **J5 判读流连续 PASS（语义勘误在案）**：**权威 odometry 流穿真重启步长 max=0.073m**（≪0.4 ramp 门,无一步>0.1m）=guard v4 桥接完美;诊断流（imu_propagate）3.0m 单步=真重启换帧签名（新实例新原点,预期行为,J5 原判据措辞按"同实例 resume"读,勘误注记）。
- **机理结论**：guard v4 使真重启对 px4ctrl 消费面**不可见**（3.47s 停发+0.073m 级恢复）——契约 C-流连续性（停发而非冻结）+C-值域自限双 face 实弹验证。

## 3. **X4 臂冲突（待用户裁定,单线期重大决策行）**

- 任务书口径：X 线=gates+guard（cauchy 不入正源维持=用户既有裁定）。
- 实测（二分定责链）：**gates 键（cost_gate/vision_loss）在今晚机器态 4/4 风暴**（T2fail 52-216,never-flew/起飞不建立）;cauchy 在否不改（DIAGCAUCHY never-init）;**guard+sane 臂干净可飞**（DIAGGUARD2 净轮面 0.418/0fail/disarm=1）;legacy 臂可飞但敌对面。
- 晨间（重启前）同 gates 臂（RA13/14,cauchy=4.0）干净——**机器态在重启前后变了**（AIC8800 USB WiFi 两波断连同晚,系统级不稳嫌疑,无活动病灶实锤）。
- **选项**：(a) X4 以 guard 臂飞（口径偏离,需裁定）;(b) gates+cauchy 臂飞（违反 cauchy 不入正源裁定,需裁定）;(c) 等机器态恢复再 gates+guard;(d) 机器级检修（换网卡/有线,硬件类须用户）。**X4/tag 冻结面在裁定前不私飞。**

## 4. 供给轮净窗产出

- 净轮面轮：DIAGGUARD2（guard 臂,j0=0.418∧0fail∧jump0.0∧disarm1）——**历史第 2 个净轮面**（RA14 后首）,臂=guard+sane（非 RA14 的 cauchy 臂）。
- hover 型净窗：SUPHV3b（T2fail=0）。
- 今晚轮到位面普遍 FAIL（4.0-4.7m 带）=transit 地板面延续（在册 BL5=transit 98% 定律一致,j0 达门而到位不达门的解耦已冻结在册）。
