# 全域收尾清零任务书 v1.0（2026-10-12 晚；第廿二周期；单册制收官——承专项① B-1+T4 池件+月报终并+旧机腿）

> 你是**全域收尾执行者**（工程+文档混合域，轻量收官）。执行域=3090（`ssh nuc2`）+旧机（`ssh nuc`）+本地 Windows。
> **旧机通道现状**：本机 Windows→旧机直连 22 端口拒连（ping 层亦不可信——今日下午 .6 应答疑似非旧机本体，AP DHCP 重复发址前科在案）；**旧机操作一律走 3090 中继** `ssh nuc2 "ssh -o StrictHostKeyChecking=no nuc '…'"`（已验证可用）；文件传输在 3090 侧 `scp nuc:…` 拉取。直连若中途恢复可并用，恢复与否不构成等待。
> **总设计师裁定（已生效，直接执行不再询问）**：①昨晚 23:51:54 旧机重启=用户主动操作（T4 v5.37 卡点 C1 就此结案销号，"疑供电"假说撤销）；②旧机今日 18:40/19:04 两次重启=用户在场物理操作——**本册禁起旧机全链栈**（恢复时机归用户明示），旧机腿只做只读+轻件；③SITL 后续轮构建基准=**0bac7286**（F1 取证态，与在役证据链同指纹，行为等价三源对齐已验；c5afa5a7 为 git 嵌入验证件非标准件）；④专项② A/B 合流终版由总设计师同窗产出——**你禁触碰两版报告原文与合流版**（写边界），月报/夜报可引用其 md5。
> **核心纪律（全沿用）**：穷尽制收工+判据/门值零变动+会话驻留四条（①在途件禁结束会话-前台轮询②轮询间隙=穿插件③收工唯一条件=全单元毕∧在途毕且消费∧穷尽④外因断开=事故非收工，重启首件=消费在途件+STATUS 补行）+新发现件当场深挖制+心跳=每单元 STATUS 一行+开工 30min 内首心跳+禁工作流+git 查 staged 逐件 add+pathspec 提交+大 IO 前 STATUS 预告+两段式上传（scp→/tmp→远端 cp）+md5 对账+中文写远端走 scp 通道+侧锁测试（SITL_LOCK_FILE）+锁 v3 语义（owner=调用方会话 PID）。
> T4 域已清零退役（v5.37=末册）、工程册 v1.6 清零、专项①/② 双必达收官——本册=**专项制收官册**，收工=软件侧全零终态。本册双必达：**单元 1 五件全毕（含判据/修复自证）∧ 单元 2/3/4 全毕或条件挂起注记（外因不可达=如实注记，禁静默跳过）**。

## 单元 0 开工收件（≤30min）
STATUS 开工行+git pull（3090 catkin_ws，HEAD 应=8a2e630 或其后）+残场核查（pgrep roscore/gzserver/px4 全 0；锁零残留）+df 两机（3090 红线 20G/旧机 28G 留观带）+六工具锚抽验（j3 族三件 3090 双位 md5=3721399e/08cb8829/7f45974b）。

## 单元 1 专项① B-1 五件（域内可完成遗留，双必达①）

- **1.1 N6 修正操作序列端到端重放（SITL）**：彩排 N6 已证 direct-LAND 被 planner cmd 流消费=静默无效（fsm_decision.h CMD_CTRL 分支）。本件=修正路径的**直接彩排实证**：①CH6 拨低等价（停 position_cmd 流）→等 1-2s→再发 LAND；②先 `kill_planner_all.sh` 再发 LAND。判据预注册（跑前写入轮目录 prereg.txt）：LAND 生效=FSM 进入 LANDING/下降态（px4ctrl 日志或 state 主题）∧ 真值 z 出现下降沿至触地；对照组=direct-LAND 路径复现无效（z 保持+armed 保持）=与 N6 判决同构。轮数=修正路径×2 案各 1 轮+对照 1 轮（3 轮下限，异常加轮）。起栈复用 vins_smoke 五件套+坑防线（plain world 纹理不足致 init 负深/ego_planner 包名 plan_manage/fsm echo 引号——彩排三废轮根因，禁重踩）；彩排脚本正源=Win `t1/2026-10-11_专项①首飞准备/rehearsal.sh`（v6 终态 857f3f5e；catkin_ws 内为 v5 旧形态，先部署 v6）。PX4 SITL 构建=0bac7286 基准（裁定③；彩排六轮即此构建，指纹连续）。SITL 栈窗 STATUS 预告（IO/CPU 面）。产物=轮目录+补验判决（rehearsal_n6fix_verdict.md）落 3090 台账 preflight_boost_20261011/。
- **1.2 A3 自动判定 grep 修复**：rehearsal.sh 的 dashboard 联动检测四次模式失配（英文 JUMP→中文"单帧跳变"→闩锁格式）——对齐终版判决口径（010939 轮 A3=PASS-人工核正的数据面签名：`单帧跳变=(max …)[RED]` 行+csv alarms 列）。修复后自证：对 010939 轮已落盘 dashboard.csv/日志重跑判定段=A3 自动 PASS（数据在 3090 台账 rehearsal_010939/；若日志文件不足以重跑，则 1.1 轮顺采一次毒窗验证——两路至少走通一路并如实注记）。注意教训：grep 检测词四连坑（坑账在册），修复=直接对齐 dashboard 实际输出格式（先看 3 行实物样例再写模式）。
- **1.3 sampler.tsv 1Hz 采样器修复**：heredoc python 进程组被 ssh 会话吞（六轮零输出）——修复=本地写 python 脚本→scp 通道部署→`setsid nohup … >log 2>&1 &` 全重定向发射+本地短窗验证（sleep 后 tail log 有输出行；坑账 setsid 家族三坑对冲）。1.1 轮挂载验证=1s 粒度 fsm/armed 轨迹落盘。
- **1.4 彩排袋 j0d 顺手画像**：rehearsal_004513/010939 两轮 bag（3090 台账在位）跑 j0d 判读器（t3 域工具，路径/用法见台账既有轮）——若袋含 odom 话题则画像+滚入 j0d_stats 表（滚入规则=分类加性+注记轮源）；缺话题则如实注记零画像收口（彩排袋以真值监控为主，缺 odom 非缺陷）。
- **1.5 手册 v2.1+检查单 v1 3090 双份部署**：Win docs/ 正源（手册 7ef4b8b5/检查单 8174415a）→3090 `~/sitl_sim/docs/`+`~/catkin_ws/sitl_sim/docs/`，md5 三处一致（两段式上传）+git pathspec 入库。

## 单元 2 T4 池件（承 T4 v5.37 B2/B3；收尾条件件）

- **2.1 nuc_only 应同步 2 袋搬运**：`t2v3_ground_205302.bag`（1.6GB，旧机 `~/sitl_sim/bags/`）+`v1_ground_salvage_211520.bag`（30MB，旧机 t1_evidence）。流程：3090 侧先跑 citation_closure_v2 确认两袋引用源所指 repo 相对路径→3090 `scp nuc:…` 经中继拉取至该路径→md5 双端对账（对账表追加）→IO 预告先行（1.6GB LAN 经中继约分钟级）。旧机侧只读零改动。
- **2.2 引用闭环 v2 NUC 侧实例+双侧差集表**：旧机 repo 同步（中继 `git pull`+工作树干净核）→closure v2 工具 NUC 侧实例跑→双侧 present 差集表落盘（3090 t4_evidence 追加凭据）→若差集含新缺失项按既有五族口径归类（预期族=登记不修）。旧机只读。

## 单元 3 月报终并（并入后=实飞前夜终本注记）

专项① 8 坑（夜报 night_report_preflight_boost.md F 节：&& 复合后台化短路/setsid 吊 ssh 会话/python CRLF/rostopic echo 缩进 grep/heredoc python 被吞/非交互无 ROS env/双坐标系错位/grep 检测词四连）按模板 v1.1 并入 137 基线（fb0cc25e）→新读数；本册新坑同步追加。纪律：前后读数+加总校验+节头节尾算术闭合；并入后注记一行"实飞前夜终本（后续新坑进当期夜报）"。

## 单元 4 旧机腿（只读+轻件；禁起栈——裁定②）

- **4.1 5hwin3 第五数据点评级**：CSV=旧机 `~/sitl_realmachine/09_reboot_stack_2026-10-09/vins_mem_watch_v537_5hwin3.csv`（536 行）。已知：01:22 起（出生证=watch2 转录行 transition_20261012_012200）→**10:22:17 止采**，终值 RSS≈6.92GB@9.0h≈**0.75GB/h 新低带**（前带 1.44-2.3GB/h；静态无人扰窗，方向与统一模型 2.18GB/h×健康帧占比自洽）。待查：止采原因（10:22 VINS 死或采样器死——机器 18:40 才再启=非整机截断；中继查 `journalctl -k --since "2026-10-12 10:20" --until "10:30"` grep oom/vins+`journalctl -u …`/dmesg；OOM killer 杀 VINS@6.9GB 则与 15GB 机+桌面共存实况自洽）。产物=数据点评级小节（速率/截断原因/模型自洽三面）落 3090 t1_evidence 追加（memleak 域）。
- **4.2 旧机 STATUS.md 陈旧副本回收**：旧机侧 sitl_realmachine 那份止于 10-06+一行误写通告（专项① C7）——处置=`mv` 改名 `STATUS.stale_20261006.bak`+原路径落指针文件（两行：正源=3090 `~/sitl_sim/STATUS.md`+改名声明）；不删内容。经中继执行+ls 凭据。
- **4.3 旧机 git 状态核（轻）**：`git status --short`+`git log --oneline -3`（中继）——漂移/落后则 pull；结果入 4.2 凭据。

## 单元 5 收尾

夜报（含三态对账表+可做而未做清单——按穷尽制，本册应收全零，若有条件挂起件如实列外因）+git 全推（3090 catkin_ws，pathspec）+STATUS 收工镜像+产物归位（Win t1/t4 按域+`tmp/` 自清）+ZCode 记忆落盘。

## 保底清单

①单元 0-5 全执行 ②N6 修正路径彩排实证（判据预注册+对照）③dashboard 联动判定自动 PASS 自证 ④1Hz 采样器实采验证 ⑤两袋搬运 md5 对账 ⑥closure NUC 侧差集表 ⑦月报终并读数闭合 ⑧第五数据点评级三面 ⑨STATUS 陈旧副本回收 ⑩夜报+三态对账。

## 等待登记

- W-用户：旧机全链栈恢复时机（用户在场操作期，本册不触碰）；动力套窗预授权链维持（修复+最小验证→首飞窗，支撑件已全交付）。
- W-总设计师：合流终版落盘后若月报/夜报需引用其 md5，取 STATUS 行为准。
