[2026-10-09 03:35] T1 v11.34 开工（ZCode 会话）。首件=night_chain 消费（2d HAFIX 重判/D5 L2/P3 build 处置）。旧机 uav4 重上电已确认可达→单元 2 待启动。
[03:58] 单元0-① 2d HAFIX 重判毕: 3d FINAL=FAIL(4场景全FAIL;13有效/7无效;KILL行8轮生效率37.5%);根因=command400缺param1(实为reboot)+log打在调用前+reboot残留毒化下轮(5/6 FATAL链)。M1行5=复标✓多场景✗维持半成。报告=hafix_multiscene_verdict_v1134.md
[04:02] 单元0-② D5 L2 判定=PASS(链路级): 注入23:17:43→TIMEOUT NEW@silence5.0s→PERSIST×4→odom_alarm.json 落盘全通。三注记: D检测器压线误报面(0.302>0.300+pursuit段15.5s RECOVERED)/phase横跳8次/收尾pub_poll_err刷屏(监控退出晚于roscore)——监控v1.2候选改进项。M1行4补强(D5 L2 链路级)。
[04:22] 单元1 自检脚本v1落地: t1_preflight_check_v1.py (fetch→get bug修+实机参数[gyro带0.005全过/min-v14.0=4S实证]+第6项|Bas|/cost病理带) 实弹首跑全项工作: CAL 6项PASS+odom 15Hz+mavros True+battery 0.0真实FAIL(台架未插电池)+|Bas|med=1.31>0.8病理FAIL(与2d采集窗互证)→NO-GO正确。E5P池件消费=实机CAL对照实测addendum(v1.1)入e5p评估件。
[04:33] 单元2d 静态病理报告v1落盘(双端): 第一周期完整闭合[收敛0.42→冻结5.8min→首破0.8@347s→1.31台阶→发射2.50@540.8s→软重置0.003@542.9s→新周期冻结]; cost未爆+Eigen崩未复现=发射后双结局修订; 第二周期19min+未发作=非确定发作; 任务含义四条落码(重启优先/自检v1第6项/3.2min预警窗/HAFIX与监控分工定案)。微动对照挂物理窗; rs depth修复+planner贯通排静置窗后串行。
[04:40] 单元2 OS 调优持久化默认案落地(旧机): rc.local 三项[governor performance/swappiness 10/usb power on]+rc-local 服务 active=断电重放达成; 转义灾难现场一次(多层引号吃 $c/$d)按禁 heredoc 教训改本地 Write+scp 修复; setserial 行不适用注记(ttyACM0)。M1 行 7 持久化件闭合。

## T1 v11.34 夜班 STATUS 报（2026-10-09 03:31-05:0x；实机主线+安全链收官）

### 0. 双必达判定：✓✓ 达成
- 腿① night_chain 三项消费完毕：2d HAFIX 统一重判终判（3d FINAL FAIL+根因链源码级）/D5 L2 判定 PASS（链路级）/P3 build 失败修复+gtest 5/5 全绿 ✓
- 腿② M1 状态行推进有果：5/11 → **9/11**（行 4/7/8/9/10 本夜新过；行 5 转 FAIL 侧半成=多场景证伪如实）✓

### 1. night_chain 三消费（单元 0）
| 件 | 结果 | 要点 |
|---|---|---|
| 2d HAFIX 重判 | **3d FINAL FAIL**（4 场景全 FAIL） | 批 summary 禁引用（grep 错文件 bug）修正后按 ev/px4ctrl.log+RESULT.txt 统一重判：13 有效/7 无效（6 FATAL=SITL 未清+1 never-flew）；KILL 行 8 轮生效率 37.5%（3 落地/5 悬停 armed=True）；**根因=command 400 param1 缺省=reboot 非 kill+ROS_ERROR 打在调用前+reboot 残留毒化下轮（6 FATAL 中 5 例紧跟 KILL 轮）**；修复面 P-HAFIX-1/2/3 在册；PASS 轮 armed 亦恒 True=disarm 全程未生效（唯一跳变=FC auto_disarm 路径） |
| D5 L2 | **PASS（链路级）** | 注入 23:17:43→TIMEOUT NEW@silence5.0s→PERSIST×4→alarm.json 落盘全通；三注记=D 检测器压线误报面（0.302>0.300）/phase 横跳 8 次/收尾 pub_poll_err 刷屏（监控 v1.2 候选） |
| P3 build | **修复+全绿** | 三处修复（vins CMakeLists src 跃点+test_p3_notify tid+gtest main；PX4CtrlFSM.h stray private: 埋掉原 public 段）；catkin 6/6+gtest 5/5+消费侧验证（reboot_notify latched↔订阅+HAFIX watch 交互契约一致） |

### 2. 实机主线（单元 2，旧机 00:13 上电 FC 已挂载）
- **2a 复苏序列全落地**：mavros connected=True+armed=False/rs infra 30Hz/VINS imu_propagate 50Hz/v2m+px4ctrl PID/Allan 袋断电后复验（md5 a4018158+rosbag 8399s 全帧 RC0）/df 32G（86% 偏高注记）/planner 件勘误=single_run_in_exp.launch 不存在（p1 基准实为四件栈——v11.31 负载面欠估计注记）
- **2d 静态病理（头号件）**：51min 静置窗**两周期同构循环实证**——周期一完整闭合（收敛 0.42→冻结 5.8min→347s 首破 0.8→1.31 台阶→540.8s 发射 2.50→542.9s 软重置 0.003）；周期二同构复现（0.0158 冻结 12min→0.46→0.08→29min 再破 0.8→1.39→1.46 冻结+打印稀疏化，至窗闭合未发射）；cost 两周期均未爆；v11.31 三症状链修订=发射后双结局（软重置 vs Eigen 崩）；**任务含义四条落码**（间隔>5min 重启 VINS/自检 v1 第 6 项/3.2min 预警窗/HAFIX 管断流-监控管变质分工）。报告 v1.1 双端落盘
- **2b 台架批（降级实况）**：纯静置域（用户不在场+桌面平移亦需人动）→《实机域估计质量报告 v1》出稿（流面全优 PASS/质量面=静态病理 FAIL 带注记/场景覆盖注记如实四件挂物理窗）；**rs depth Asic 硬件卡死**（热杀进程后 Hardware Error+USB 卡死；sysfs authorized 重置救回 infra 双目 30Hz 但 depth 模组仍挂→复位需整机断电=物理窗）→depth+planner 贯通挂物理窗
- **OS 调优持久化默认案落地**：rc.local 三项（performance/swappiness10/usb-on）+rc-local active=断电重放（转义灾难一次按禁 heredoc 教训本地 Write+scp 修复）

### 3. 安全链收官（单元 1）
- 自检脚本 v1 落地实弹（fetch→get bug 修+实机参数[gyro 带 0.005 全过/4S min-v14.0 实证]+第 6 项 |Bas|/cost 病理带）——首跑全项工作：battery 0.0 真实拒飞+|Bas|med=1.31 病理 FAIL（与 2d 采集互证）→NO-GO 正确
- E5P CAL 考古池件消费=实机 CAL 对照实测 addendum v1.1（gyro 三轴在带内=现役健康；ACC Y=-0.258/Z=-0.093 偏大=P1 物理窗核对项）

### 4. M1 门终值：**9/11 PASS**（1/2/4/6/7/8/9/10/11）+行 3 半成（深度面阻物理窗）+行 5 半成（多场景 FAIL 侧）——检查单 v11.34 更新段已追加

### 5. 可做而未做清单（穷尽制）
1. HAFIX 修复面 P-HAFIX-1/2/3（呈报件，判据零变动——未擅动栈；修复+复验批=下窗首件候选）
2. 微动注入对照（2d②对照臂）+桌面平移+手持两场景+depth 断电复位+planner 贯通——全挂物理窗（用户在场）
3. 2c 物理窗四项（磁力计重校 P1/固件 QGC 直读/不装桨怠速/急停拨测+电池压测）——清单 v1 在 04_safety_chain
4. 2e 实机地面版演练（不装桨怠速态杀 VINS/毒 odom）——物理窗顺带件
5. 监控 v1.2 候选改进（D 检测器阈值口径/phase 抖动/收尾退出时序）——非阻塞注记
6. 第三周期静态数据（static_watch 循环留守自动累积，明窗首件消费）
7. planner launch 实机适配稿（depth 话题+内参——待 depth 复活落码）

### 6. 坑账（本夜新）
1. 批脚本 grep 错文件（drill stdout vs ev/px4ctrl.log）——summary 列全零型假象（重判修正）
2. 批轮 ev= 时间戳与实际目录差 1s（220558/220559, 231036/231037）——重判回退匹配
3. .gitignore 吃 test/ 第四次复发（git add 整体失败——force-add 例行动作）
4. P3 埋雷形态：.h 的 public 段前插 private: 块埋掉原 public 成员（编译错误远在调用点）
5. mavparam 子命令= get 非 fetch（自检 v0 实弹 bug）
6. 热杀 rs 进程→IR/depth 硬件启动失败（USB 设备态卡死；sysfs authorized 重置可救 IR 救不了 depth Asic——rs 操作规程入病理报告 §5）
7. 多层引号转义灾难（\$c/\$d 被 eat）——禁 heredoc 教训再验证（本地 Write+scp 即愈）
8. STATUS 硬编码时间戳超前（本夜中段时刻感知漂移；本报告时间戳按 date 实测勘误——03:31 开工/05:0x 收工）
9. pgrep 自匹配两现（循环查询/t1_stoploss 清理）——pgrep -f 查询串必避自身路径

### 7. 等待登记
- W-物理窗（用户在场：2c 四项+微动对照+手持场景+depth 断电复位+planner 贯通+2e 地面版）
- W-HAFIX 修复批复（P-HAFIX-1/2/3 呈报件）
- W-M1→首飞 go/no-go 呈报（9/11 达预期下限；行 3/5 收口均需上两项）
- 留守: static_watch 循环（旧机）持续快照
2026-10-09 04:50:24
