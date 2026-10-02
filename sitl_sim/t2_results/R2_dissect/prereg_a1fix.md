# prereg_a1fix — A1 双问题修复预注册（单元 2；判据先于写码；2026-10-03 02:1x 落盘）

## 取证基础（单元 6⑤⑥，证据=t2v3_route_035325.bag + t2v3_hover_033842.bag + est.cpp 码读）

1. **毒流帧级画像（⑤）**：A1 袋 imu_propagate 209Hz，Bas 门触发（t=49.16）后连续放毒 8.25s 至 t=57.41（|P| 0.27→142.3m，|V|→49.97m/s，平滑二次曲线，零帧跳，量级与 |Bas|=3.17 自由积分吻合）；odometry（解算输出）同刻永寂。A3 同构：cost 门触发（t=46.96）后放毒 6.0s，止于 |V|=50.0 有界检查自然止流（|P|=93.2m），odometry 46.88 后 108s 全寂。
2. **根因（⑥，改写原题设）**：failureDetection 触发分支（est.cpp:725-741）在 processImage 内联调用 clearState()，而 processImage 唯一调用点=processMeasurements est.cpp:388 **已持 mProcess**，clearState（est.cpp:38）**再锁 mProcess**=同线程自死锁（std::mutex 非递归）。后果链：进程线程挂死→odometry 永寂+永不再 init（b 的全部表象）→solver_flag 永不复位→inputIMU 发布早退（est.cpp:219）失效→spinner 线程以中毒 latest_*（Bas=3.17）持续 fastPredictIMU+发布（a 的全部表象）。归属=上游继承（git blame ^1a069ca init 提交即有，非 fork 引入）。
3. **原 2(b) 题设证伪**："地面态无运动无视差→永不再 init"不成立——永寂由死锁造成；地面静态 stereo 初始化可行有 A5 全程地面 NON_LINEAR 先例（U3pp 健康地面轮）。

## 方案选型（三候选 vs 定案）

- **定案：reinit_request 模式（T2-U1 先例）**——failure 分支只置旗（failure_occur=1; reinit_request=true）+return；实际 clearState+setParameter 由 processMeasurements 循环头消费者（est.cpp:317-323，锁外，先例注释明言"实测安全"）执行。一修双病：
  - (a) 毒流：真 reboot 完成→solver_flag=INITIAL→inputIMU 早退=**停发自动生效**；再 init 时 updateLatestStates(true) 重锚 latest_*（锚点复位，残余毒窗=故障帧到循环头 µs 级+早退竞态 ms 级，按 |Bas|≤2.5×t²/2 物理上界 <0.1m）。
  - (b) 永寂：死锁解开→reboot 真正发生→地面静态 stereo 再 init 可行（A5 先例）。
- 弃选理由：①独立"停发开关"=被 solver_flag=INITIAL 早退语义涵盖（冗余）；②收紧 1e3/50 界=毒流末速 49.97/142 全在界内或仅界处止流（A1 8.25s 内不受阻），收紧则健康 v_max 21.17（U3PO 实测）余量不足=量域门无判别力（R3 判死复认）；③冻结最后健康位姿=向消费方供"看似新鲜的谎言"，EKF2 EV 侧陈旧性风险高于停流，弃。
- 保语义核查：failure_occur 双路径均被 clearState 清零（est.cpp:97）=行为等价；reinit_request/failure_occur 读写均在 process 线程（613/655/737 写点同线程）无竞态；故障帧 feature 已在 est.cpp:347 pop，消费者 continue 不双处理。

## 补丁规格

- est.cpp failure 分支：删除内联 clearState()+setParameter() 两行，替换为 t2_failure_reboot_request(failure_occur, reinit_request)（estimator.h 新增 inline 自由函数，含禁锁注释）+return。
- 观测性（并偿单元 6 工具债）：setParameter 尾部增 [T2GATECFG] banner（cost_gate/ratio/n/win + min_disparity/far_drop 参数一行）——每次 reboot 重打=reboot 完成标志（兼作"两门无 banner"债的部分清偿）。
- 回归主张：健康路径逐位不变（分支仅在 failureDetection 真时进入）；故障路径=同打印+同净效果（clearState+setParameter）仅执行点移至锁外+不再挂死。

## gtest（test_a1_reboot_fix.cpp）

- T1 旗语义：helper 置双旗。
- T2 金丝雀：他线程持 mProcess 镜像锁时调 helper，500ms 内返回（防后人往 helper 塞锁调用）。
- T3 死锁形态文档化：旧结构（持锁再锁）try_lock 必败（记录性断言）。
- 全套既有 gtest 回归绿为前置。

## 在线验证判据（与单元 1 配对轮合并设计：gates 臂+修复在场，一轮多判）

- **V-fix 主判**：任一门触发 → odometry 断流 ≤10s → 恢复发布且 |P| 回物理量级（米级，非百米）＝受控失败成立（用户已批口径）。
- **V-fix 辅判**：触发后 imu_propagate 毒段 ≤2s 且 |P| 峰 <5m（锚点物理上界预测）。
- **V-pairing 判**：单元 1 原预注册不变（急冻爆窗内 cost 门触发且 reboot 后恢复跟踪=配对样本到手）。
- 6 轮耗尽配对未发生→如实入账等用户裁（不变）。

## 连带改判（本预注册一并声明）

- **U3pp A3：PASS→FAIL**（"cost 门触发+reboot 恢复"受控失败判据的恢复半不成立：odometry 46.88 后永寂=死锁；门检测半成立保留——门在带内 Bas/Bgs 下唯一捕获者的**检测价值**记载不变）。**达标门 3/5→2/5**（A4/A5）。@T1：跳变表 A3 的"1 次 0.545m=reboot 对号"勘误为=爆窗 solver 运动（reboot 未完成）。
- 历史含"reboot 后恢复"表述的轮次（回放域 dis0 爆后活到袋尾 401s 等）**不自动推翻**——回放域判据本就禁入生死判定（红线 11），仅 A3 在线轮改判。

## 栈纪律

构建后登记双 md5（lib+node）；本栈=单元 1 合并轮在用栈；285278cc 时代缺 lib 存档教训=本轮起存档双件。
