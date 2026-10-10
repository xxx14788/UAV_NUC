# T1 v11.39 夜报（HAFIX 修复+物理窗执行版收官；2026-10-10 19:4x）

## A. 完成账（双必达判定）

**双必达=①20 轮复验批执行完+终判表落盘 ✓✓（18:08:24 批毕+verdict CSV/终判表落盘，终判 3/20 NOT-PASS 诚实入册）∧②2b+2c 落地+质量报告 v2 出稿+首飞呈报件出件 ✓✓（unit2b_postcal_v1139.md+unit2c_ground_drill_v1139.md+est_quality_report_v2.md+firstflight_gonogo_v1139.md 四件全落台账）——双必达达成后继续穷尽（FAIL 分支二次修复+10 轮增量批亦毕）。**

1. **单元 1 HAFIX 三案+二次修复+增量批**：P-1/P-2/P-3 落码→20 轮复验批毕→梯②③零效实证→**回挖三层机理定案**（hafix_kill_dig_v1139.md：400 被 failsafe 覆写[Commander.cpp:2383 每拍盖用户意图]/179+21196 ACK-无操作[物理证据定案]/**梯①盲降被 decide_land 一拍弹回=px4ctrl 域根因**+SITL GPS 兜底勘误）→**梯①盲降结构二次修复**（ha_blind_land 旁路+双锚+OFFBOARD 重入+idle 门+cleared=disarmed 终态+stage1 流恢复复位保留）→gtest 51/51→干测 7 六环闭环→**10 轮增量批（S1×4/S2×3/S3×3）毕：预注册 9/10 PASS+物理链 10/10 全链达成**（watch→盲降平均 15s 触地 z=0.10→armed drop→disarm；KILL 零依赖=带弹；对照修复前 15/15 悬停不落——修复定案生效）；S1 r4 注入前流拍脸段=watch 复位语义零误触实证
2. **单元 2 物理窗**：2a depth 复活定案（断电救回 Asic，30Hz 在役）；2b 校准复测（ACC Y 翻号级+mag 首写+固件 v1.17.0+FMU v6C 版本行）；2c 不解锁演练（watch 地面态=设计边界非缺陷+监控 v1 告警 60s 链+修复版实机在役）；2d 五袋判读全 IN-EXPECT+报告 v2；2e 贯通输入链（grid_map 吃 depth+odom 直供）
3. **单元 3 首飞呈报件**：五节固定结构无条件出件；行 5=复验 NOT-PASS→二次修复→增量批 10/10 的完整链如实呈报
4. **单元 4 池件**：监控 v1.2 四注记落码；VINS 内存泄漏定案（0.6GB/h 线性+odom 15→5.7Hz 劣化@9.4h+重启即复=实机在役边界 6-8h）；旧批特征化（爆起全部早于断链=USB 劣化渐进期链深化）；.gitignore test/ 根除；p1 五件动态栈补测全绿；VINS RES watch2 在役续采
5. **单元 0 留守件**：static_watch 11.3h/4 周期判读（勘误 v2：ALERT=全量重解析非独立周期；发作滞后 min 17min/p50 65min/无自然恢复）+病理报告 v1.2 追加节+数据回拉 3090 归档

## B. 可做而未做清单（穷尽制）

1. S4 降落段注入时序精化（postgate=40 边界语义欠精；盲降链验证面已由 S1-S3 10/10 覆盖，S4=低优池件）
2. 179+21196 实机 forced-disarm 台架验证（动力套窗；SITL 侧机制源级未闭——px4ctrl 修复已零依赖该路径）
3. planner 实机执行面（goal→poscmd→飞行贯通）待动力套/首飞
4. VINS 内存泄漏 root-cause（特征窗嫌疑；6-8h 边界+重启规程已工程化）
5. 400 生效链推演的 SITL 实证（盲降流不断→failsafe 不活→termination 可应用——修复后 round 的 KILL 全零未触及该面）
6. 增量批 verdict 生成器 20 槽位表头失真（已附修正块；生成器参数化=次任池件）
7. A1 扩批/p1 五件正式基准文书化（数据已收）

## C. 卡点（客观）

1. HAFIX KILL 梯②③ PX4 域失效（SITL 构建 d6f12ad1c4；px4ctrl 修复=梯①盲降自主落地不依赖 KILL——10/10 实证；实机 FMU v6C 待台架）
2. 动力套三项未验（用户裁定跳过——首飞最大未知面，呈报件§④）
3. battery 0.0V 未插电池态（首飞前插电复核即转净面）
4. 静置病理+内存泄漏=长时窗积累族（首飞剖面不阻；>17min 静置重启规程在册）

## D. 资产（t1_evidence/v11_39_2026-10-09/ 全目录）

hafix_reverify/{summary,ev_index,20 轮 log,verdict_v1139.csv,final_verdict_v1139.md,batch_env_checklist.md}；hafix_increment10/{summary,ev_index,10 轮 log,verdict_v1139.csv,final_verdict_v1139.md(含修正终判块)}；hafix_kill_dig_v1139.md；est_quality_v1139.{csv,md}+est_quality_report_v2.md；static_watch_judge_v2_v1139.md+static_watch_cycles_v1139.csv；static_pathology_v12_append.md（已并入 v1 正本=realmachine_static_pathology_report_v12.md）；oldbatch_pathology_timeline_v1139.md；unit2b_postcal_v1139.md；unit2c_ground_drill_v1139.md；unit4_vins_memleak_v1139.md；firstflight_gonogo_v1139.md；night_report_v1139.md（本件）；p1_5piece_bench_v1139.txt；代码=px4ctrl 修复版（梯①盲降+梯②双 kill+梯③扩门）+monitor v1.2+drill 门 v4+两批编排器+判读器参数化版+增量批脚本

## E. 等待

- W-首飞授权（用户物理授权域；呈报件=输入，增量批结果已并入行 5）
- W-T3 影子重判消费（复验批 20 轮+增量 10 轮的 --pattern 一键面在册）

## F. 坑账（今晚新增八条）

1. **批多实例连环互杀（D-1010-T1-01）**：kill 未验尸（PID 未确认死亡）→旧批存活→双批并发→force_clean 互杀+孤儿 drill 跨批注入；根治=PID 文件单例守卫（v1 pgrep 方案自噬：$( ) 替换子壳继承父 cmdline 被自身匹配——v2 PID 文件零 cmdline 匹配）
2. **set -u 遇 ROS 链复发**：批脚本 source ROS 前未 export ROS_DISTRO（drill 脚本有正解模式未复制——复用纪律）
3. **pkill -f 自匹配第三次**：pkill -f "px4ctrl_node" 匹配远程 bash -c 自身命令行秒杀会话——-x 精确名匹配解
4. **近点 goal 落地边界**：S1 类近点到达+降落≈poscmd-live+30-70s，固定 sleep 注入窗必落地面——flying 门 v4 双门（poscmd 存活+armed:True）+postgate 从 armed 起算
5. **land_detector 冻结 odom 伪落地**：盲降期 C1+C2 伪满足→landed 谎报→高位误 idle 坠落风险——idle 门=px4_on_ground||odom_ok
6. **ulog 时间戳=UTC**：rootfs/log 目录名比本地 -8h
7. **catkin build 不重建 gtest 二进制**：--make-args tests 拖累全依赖链（uav_utils tests 链接失败阻塞）——build/px4ctrl 目录直接 make test_fsm_decision 单目标解
8. **长 ssh 前台命令超时截断外层循环**：同步跑轮的 ssh 550-600s 超时会砍在 drill 毕与登账行之间（两轮补登实证）——轮编排必须 setsid 后台化+轮询登账
