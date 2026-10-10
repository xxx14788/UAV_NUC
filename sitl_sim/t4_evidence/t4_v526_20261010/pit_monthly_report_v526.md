# T4 第五坑月报 v5.26（2026-10-09 夜，任务书单元4，全增量并入）

执行=第五坑月报员（T4 单元4，无外部依赖）。远端时钟=08:03（nuc2 `date +%H:%M` 实测）。
红线声明：本文为登记面文书，不含任何 PASS/FAIL 三态判读；全程零删除、零提帧、零重放、零大 IO。

---

## 0. 扫描口径与来源清单（数一数）

| 来源类 | 文件 | 坑条目产出 |
|---|---|---|
| 记忆·t4-*（11 件全读） | t4-eline-closure-and-j1-assets / t4-j3-sixdim-outcome / t4-jr-batch-2026-10-01 / t4-u3p-j13-verdict / t4-v54-night-campaign / t4-v57-night-outcome / t4-v514-workflow-design / t4-v517-3090-first-night / t4-v526-workflow-built / t4-vision-acceptance-outcome / t4-w3w5-waiting-batch（均在 C:/Users/ShiyuFang/.zcode/cli/memories/projects/drone_vins-87017f42c93ca0a1/memory/） | 41 条 |
| 记忆·nuc-ops/night-ops/sitl-*（5 件全读） | nuc-ops-pitfalls-round2 / night-ops-toolchain-pitfalls-v61 / sitl-debug-toolbox-lessons / sitl-env-ops-e-line / sitl-imu-rate-grid-lock | 22 条 |
| 记忆·补充（2 件，超出命名模式但为全增量并入） | disk-chain-w0-complete-2026-10-01（腾位先例）/ network-20261006-ap-dhcp-recovery（AP 病挂史，任务书 L6 背账点名） | 6 条 |
| 本地 reports/工作件（4 件） | t4_work_3090_20261005/reports/t4_v517_night_report.md（§6 坑位汇总）、同目录 memory_draft_t4_v517.md（登记面/通道坑位两节）、t4_work_3090_20261005/pool5_audit_increment.md（第五坑审计 §8-15）、t4_work_20261002/reports/t4_v57_night_report.md（C-14 修复面） | 9 条 |
| 远端 verdicts 正源（3090:/home/ghj/catkin_ws/docs/t4_verdicts_v2.md，3 段实读） | L118-121（J-R 工具链坑位五条）、L270-285（EX-FAIL 工具坑位表①-④+C-14 四修复 commit）、L445/447/485/529/547（第五坑定案与收货面） | 8 条 |
| 任务书存档（v5.26 前） | plans/2026-10-03_T4_v57_night_workflow.md：仅 1 处池件引用（L82"EX-FAIL 坑位表下游消费审计"），零新坑条目；t4_work_20261007/t4_v522_workflow.ts 与 t4_work_20261008/t4_v524_workflow.ts grep"坑"零命中；v4.1/v5.1/v5.5/v5.9 等更早任务书**本地 plans/ 无存档**（仅记忆交叉引用，实查 `ls plans/` 确认） | 0 条 |

**并入合计**：原始坑记录约 103 条 → 重复合并（标"复发"）后 **86 条**（域A 通道载体 23 + 域B 并发锁盘网 19 + 域C 判读工具口径 37 + 域D 流程方法论 7）。其中"已落"对冲 77 条、"待落/待核实/待裁"9 条（§4 清单）。

**扫描范围声明（诚实边界）**：记忆目录共 97 件，本次实读 18 件（任务书命名模式 t4-*/nuc-ops/night-ops/sitl-* 全 16 件+补充 2 件）。未读：MEMORY.md（索引件）、nuc-wifi-watchdog/nuc-wifi-only-ssh/nuc-tailscale（nuc-* 但非 nuc-ops 模式；Tailscale 备用腿已经 w3w5 记忆入表）、e1-ev-fusion-never-enabled、lock-testing-sidefile-rule、dual-agent-collision-protocol（其纪律已分别经红线⑤⑥⑦与本表 A2/B2 内化）、t1-*/t2-*/t3-* 各件（他线域）。pool5_audit_increment.md 为任务书《本地资产》点名件，已并入。

---

## 1. 名义项：EX-FAIL 第五坑（compact 袋零图像）专项状态

- **坑定义定案原文**（verdicts L485）："EX-FAIL 新增第五坑：在线轮 compact 袋零图像话题——W1 图像链适用以'袋含立体图像话题'为前提，收货先查话题面再走链"。
- **消费审计账**（pool5_audit_increment.md §10/§15，快照 2026-10-05 03:4x）：踩中 0（累计 0）；他线引用 3 条证据行不变；T4 自域+主会话引用累计 15 行（verdicts×4+DECISION_LOG×1+3090 STATUS×5+NUC 镜像×2+审计在册面）；规避 3 实例（024434 compact 残余禁硬提帧/run_T2BL1..12 十二袋只登记不提帧/024434 权属等待注记）；gate-first 正向运用 3 面（t2v3_hover_134845 先 rosbag info 后裁定等）。
- **登记面判定**：暴露面如期出现（T2 v9.1 prereg ef8c2db"compact-recording default"产出 BL 系 12 袋）→抽样先查→只登记不提帧→verdicts H 章定稿（4dfec04）。**对冲已生效，零踩中**；登记面=verdicts:447 处置闭环（"坑位表五坑维持在册不改"）。
- **在册永久缺**：BL1..12 十袋+024434 compact 残余（282.8MB）+U3PR1 等图像侧收货/判读面**永久缺**，只登记不提帧；其判读依赖 T2 侧 odom/诊断面。
- **锚位维护**：坑五锚自 verdicts L440 漂移至 **L485**（追加章所致，原文逐字未变）——引用前先 grep 重锚（本表 C36）。
- **跨机注记**（pool5 §12，待主会话裁）：W1 回执两行仅存 NUC STATUS:820/821，3090 正源缺，按 3090 行号引用会扑空（本表 B19）。

---

## 2. 全量坑位表（86 条；格式=日期|机理|对冲（状态）|来源|复发）

状态：已落=对冲机制已在册/已修复；待落=对冲未完成；待核实/待裁=权属他人。

### 域A：ssh/远端通道与工作流载体（23 条）

| # | 日期 | 机理 | 对冲机制 | 状态 | 来源 | 复发 |
|---|---|---|---|---|---|---|
| A1 | 09-27 | ssh 复合命令含 pkill 模式串→自匹配杀掉自己会话（exit 255） | 清理落脚本文件（t3_clean.sh）+清理与启动分两次 ssh；模式串用 [x] 字符类 | 已落 | sitl-debug-toolbox-lessons | 复发：ssh 纪律③ pgrep -f [x] 规避内化 |
| A2 | 09-29 | ssh heredoc/echo 写中文必乱码（GBK/UTF-8 转码层破坏） | 红线⑥：本地 UTF-8 写→scp→远端 cat 拼接 | 已落 | nuc-ops-pitfalls-round2#1 + night-ops-v61#4 | 复发2（变体=复合命令 echo 进 STATUS） |
| A3 | 09-30 | ssh heredoc 引号错位→尾随空格文件名，git 显 ?? 内容进错文件 | `ls \| cat -A` 查验 | 已落 | t4-j3 工具三坑③ | |
| A4 | 10-01 | 非交互 ssh 无 ROS 环境（ros 工具/rosbag 不在 PATH） | bash -lc 显式 source（ssh 纪律①） | 已落 | t4-jr-batch→J-R 五坑⑤（verdicts L121） | 复发：10-04 rosbag 不在默认 PATH（v514） |
| A5 | 10-01 | `set -u` 在 ROS setup source 前杀脚本（setup 内未绑定变量）且报错被 2>&1 吞 | 先 source 后 set -u/作用域化 set +u | 已落 | J-R 五坑①（L118）+v57 工具坑② | 复发2 |
| A6 | 10-01 | ssh 后台+管道→退出码/输出双双失真 | 远端落日志文件+REMOTE_RC 显式回传 | 已落 | J-R 五坑④（L121） | |
| A7 | 10-01 | rosbag 探测 pgrep -x 探不到 python 包装、pgrep -f 被外层含"rosbag"字样命令自命中毒计数 | `ps -eo comm=\|grep -cx rosbag` | 已落 | J-R 五坑②（L119） | 与 A1 同族 |
| A8 | 10-01 | 重定向手滑 `>/`（根目录）静默废掉 roscore | 远端命令禁根目录重定向手滑（纪律在册） | 已落 | J-R 五坑③（L120） | |
| A9 | 09-29 | 本地 sleep≠远端墙钟（实测 ssh 命令延迟数小时落地） | 时间窗一律远端 `date` 轮询+`ls -dt run_*` 核实真实启动 | 已落 | nuc-ops-r2#3 | |
| A10 | 09-29 | Windows 侧写 shell 脚本 CRLF→bash 语法错 | `ssh -T nuc2 "tr -d '\r'\|bash" < 本地脚本` 通道（v5.17 定型） | 已落 | v57 工具坑③+memory_draft_v517 | 复发2 |
| A11 | 10-05 | cmd/Git Bash 命令行 `%` 转义坑（date +%H:%M 等） | 含 % 远端命令必走 A10 同一通道，禁命令行直写 | 已落 | memory_draft_t4_v517 | |
| A12 | 10-03 | 回归门 world.run 在 NUC 本机执行不加载 ~/.ssh/config→别名坠 DNS 必死 | regressionCmd 写环境自适应形态（本机 bash 直跑/ssh 回退） | 已落 | v57 工具坑① | |
| A13 | 10-09 | world.run 在 win32 直接 spawn，Git Bash sleep/builtin 不可用→spawn sleep ENOENT（v5.26 首跑 dwfrun-74309377 死于此） | 等待必须 `ssh 远端 sleep N` 或 `ping -n N 127.0.0.1` | 已落（本夜新钉） | t4-v526-workflow-built | |
| A14 | 10-04 | 工作流 artifact.file/脚本 path 解析基线跟随 shell cwd，cd 过子目录必错位 | 发布用裸相对名+文件先放 cwd，或绝对路径 | 已落 | t4-v514 | 复发2（v5.19 夜 10-06 同坑再现） |
| A15 | 10-01 | scp 目标路径被改写覆写本地编辑产物（两次实锤一次丢编辑）+rtk 改写 diff/scp banner 不可信 | 红线⑤两段式上传 scp→/tmp+远端 cp+md5 对账；判定以 python difflib/md5sum/grep 为准 | 已落 | t4-w3w5 | 实锤2 次 |
| A16 | 10-05 | ssh 输出管道接 grep -v 过滤 banner 吃掉真实 exit code（grep 空输出返回 1） | 传输/命令成败判据=远端 md5sum/回读，不看本地管道返回值 | 已落 | memory_draft_t4_v517 | |
| A17 | 10-05 | STATUS/verdicts 文件尾追加前未核 LF、追加后无对账→字节级不可证 | 追加前 `od -c` 核文件尾、追加后 `tail -c delta \| md5sum` 对账 | 已落 | memory_draft_t4_v517 | |
| A18 | 10-06 | bash heredoc→python→TS 三层转义 `\n` 逐层降级成真换行（假修复实锤两次） | 跨层字符串修补一律用 Edit 工具 | 已落 | t4-v514（v5.19 段） | 实锤2 次 |
| A19 | 10-04 | Edit/Write 工具对 Bash 侧改过的文件拒写（state 失步） | 补丁式修改不如整体重写 | 已落 | t4-v514 | |
| A20 | 09-28 | sed 替换串含 `2>&1` 时 `&` 未转义→展开全匹配改坏脚本（v1_flight.sh L70 事故） | `&` 写 `\&`；全局改名后双向查残留 | 已落 | sitl-imu-rate-grid-lock 新坑② | 复发：10-05 mig/migrator 两轮编译错（v517） |
| A21 | 10-04 | ssh 内联中文 commit message 实测无损，但 STATUS/文件写乱码史在册 | 纪律按件型分立：仅 commit message 可内联，STATUS/文件必 scp | 已落 | t4-v514 | |
| A22 | 10-05 | 3090 ~/.ssh/config 无 Host nuc（仅 github 别名）→NUC 存在性批量查证扑空 | NUC 查证经本地控制机 `ssh nuc` 只读中转代查 | 已落 | t4_v517_night_report §6.1 | |
| A23 | 10-02 | bags/ 直下袋直接喂排队器→父目录名出错 out_dir | staging 符号链接成 run_* 目录再入链 | 已落 | t4-u3p-j13 | |

### 域B：并发互斥/锁/磁盘/网络（19 条）

| # | 日期 | 机理 | 对冲机制 | 状态 | 来源 | 复发 |
|---|---|---|---|---|---|---|
| B1 | 09-27→09-29 | 三方并发（回放×删盘×带图轮/5 路带图回放）NUC 整机死机两次（01:21 crash+02:20 重启）——回放互斥是物理约束不是礼节 | 红线④大 IO 互斥：pgrep 查在飞+STATUS 预告+让路；空窗判断=pgrep rosbag play/record 双 0 | 已落 | sitl-env-ops-e-line+nuc-ops-r2#4+night-ops-v61#5 | 复发3 |
| B2 | 09-29 | pkill 名字级=跨 master 误杀兄弟实例（一夜三次实锤互杀） | 清理只 kill 自己记录的 PID；pkill 前 pgrep 全场+读 STATUS 尾 | 已落 | nuc-ops-r2#2 | |
| B3 | 09-29 | 锁冲突+僵尸实例（FATAL 锁被占双流抢锁+4 孤儿 start_sitl_vins PPID=1 挂机） | E1 锁 v2（sitl_lock.sh 14/14 绿）+setsid 监督五退出路径零残留 | 已落 | sitl-env-ops-e-line+t4-eline | |
| B4 | 09-29 | E1 锁 v2 开发期 3 bug（pgrep -c 双值/target_pid off-by-one/force 内嵌 ts 不可伪造） | v2 修复收敛，全绿测试表在册 | 已落 | t4-eline | |
| B5 | 09-29 | sitl_lock v2 死锁接管只拿锁不清进程→残留 px4/mavros 与新栈冲突废飞窗 | 接管后先清死栈（t3_clean）再起新链 | 已落 | night-ops-v61#3 | |
| B6 | 10-03 | t4wf 孤儿锁事件（10-03 02:19-02:39）：回归 runner EXIT trap 只保正常退出，会话异常死亡路径缺 release=锁泄漏工具债 | **待落**：异常退出 release 路径未修（T2 force 接管在册） | 待落 | v57 工具坑⑤ | |
| B7 | 10-03 | E1 锁测试误删活锁+恢复（T3 引用"T4 02:05 预批"实为锁事故勘误） | 红线⑦：测试必走 SITL_LOCK_FILE 侧锁；勘误在册 | 已落 | v57 | |
| B8 | 10-05 | T3 残留 rosbag record（PID 3608527，5h11m）堵空窗门——他线进程处置权属线 | T4 禁代杀他线进程（权序=其余），清理权在属线且必须 PID 定向；四步裁示先例在册 | 已落 | t4-v517 | |
| B9 | 09-29 | T4-E 僵尸治理器会杀 113xx 私有 master 上 roslaunch 进程（在线注入测试 4 次阻断根因） | **待核实**（当时挂"待 T4 核实"未销） | 待核实 | night-ops-v61#5 末句 | |
| B10 | 09-27 | 夜战前不巡检遗留脚本（T1 repro 僵尸杀 PX4 毁一轮持锁飞行）+他人改共享文件即时进入你的会话 | 动 NUC 前 ps 巡检+pgrep 全场纪律 | 已落 | sitl-debug-toolbox#6 | |
| B11 | 10-04 | 锚袋事故#2："注册≠保护"——§8.1 顺位删 WC2×2 合规但毁 T3 判读活锚（03:05 注册先于删袋） | 腾位前置双门=§8 三面核对+删袋前必 grep t3_xline_runbook §9.2 锚表（D-08）；watcher 增锚表变更触发面 | 已落 | t4-v514 | 事故#2（#1 在更早册） |
| B12 | 09-29 | 盘满（/ 98% 余 6.3G）rosbag 静默失录 | df<20G 硬水位禁起新轮+logrotate 部署+腾位双门红线③ | 已落 | sitl-env-ops-e-line | |
| B13 | 10-01 | 65G 素材不可整体共存（56G<85G）；W2 七轮 21G 贴水位→W2 前必须腾挪 | 滚动管线预案（跑完即腾）+候选腾挪清单在册 | 已落 | t4-jr-batch | |
| B14 | 10-01 | df 波动剧烈（一晚 70G→33G，T2 矩阵录制 -37G）→旧波次表 70G 结论作废 | 决策前必现场 df 实测（不引用隔夜数字） | 已落 | t4-w3w5 | |
| B15 | 09-27 | whoopsie（Ubuntu 错误上报）常态 21% CPU | 已禁用（E4.3） | 已落 | sitl-env-ops-e-line | |
| B16 | 10-02 | NUC 仓库远端名叫 UAV_NUC 非 origin→push origin 必失败；且 C-9 NUC WAN 瘫（8.8.8.8 unreachable/DNS 死，LAN/ssh 正常）push 断两夜 | remote 名钉 UAV_NUC；C-9 已闭（31 笔全推清，v57）；备用腿=ssh nuc-ts（Tailscale，DERP 慢但稳） | 已落 | sitl-imu 新坑①+t4-u3p/t4-v54/t4-v57/t4-w3w5 | 复发：WAN 瘫持续两夜（10-01→10-02） |
| B17 | 10-06 | AP 重启后 DHCP 分配器损坏：对 Windows/NUC 两 MAC 重复发 .5→ARP 冲突致 Windows→3090 100% 丢 | 过渡定局：NUC 静态 .6（用户裁定"必须 .6 不得随意改"口径后又裁定终局回 .5，未执行）；断连复发先查 .5 冲突再查 3090 本体；nuc-ts 腿不依赖 LAN IP | 已落（过渡）**待落（终局回 .5 裁定未见执行）** | network-20261006-ap-dhcp-recovery | |
| B18 | 10-07 | nuc3 系统不符（22.04.5 vs 栈需 20.04.6+Noetic）→用户裁定自行重装不写入任务书；装机坑=apt 无 install candidate（update 未跑）/用户名 uav0 误记（实机器名，用户名=uav） | nuc3 冻结待用户侧重装（就绪判据=ssh 免密通+20.04.6）；任务书背账"nuc3 冻结"一致 | 已落（冻结口径） | network-20261006 + 任务书 L6 | |
| B19 | 10-05 | STATUS 跨机分叉：W1 收货回执两行仅存 NUC STATUS:820/821，3090 正源缺（执行域迁移时点差） | 引用走 NUC 冻结侧或 3090 repo 件（t4_w1_reception_20261004.md:60,61）；**是否补镜像行=待主会话裁** | 待主会话裁 | pool5_audit §12 | |

### 域C：T4 判读工具/算法/口径（37 条）

| # | 日期 | 机理 | 对冲机制 | 状态 | 来源 | 复发 |
|---|---|---|---|---|---|---|
| C1 | 09-27→10-02 | rubric/词表未先于素材全覆盖（V2 漏嵌入→轮 2 的 19 张被迫 inconclusive 返工亲判） | 红线①判据未预注册不出 PASS/FAIL（10-02 E4 双峰实录后实操确立） | 已落 | t4-vision-acceptance + t4-u3p-j13 | 复发2（同源两阶段） |
| C2 | 09-27 | judge 子代理把输出 category 字段改写成自由文本 | 分类用判读单元标准类别显式传参，不信输出回传值 | 已落 | t4-vision-acceptance | 复发：t4-eline fan-out 两坑沿用 |
| C3 | 09-27 | 欧拉角提取假象：yaw>90° 时公式分母变负→±180° 假"倒扣" | 判读姿态用旋转不变量 zb 轴=R 第三列（zb.z<0 才真倒扣） | 已落 | sitl-debug-toolbox#1 | |
| C4 | 09-27→09-29 | 管道/包装吃退出码：catkin_make run_tests 吞 gtest 失败（exit 0 但 [FAILED] 在输出）；build 后 grep rc 假成功跑旧码 | 直跑 gtest 二进制查输出行；真退出码+devel 二进制 mtime+编译行三者齐 | 已落 | night-ops-v61#1 + sitl-debug-toolbox#3 | 复发2 |
| C5 | 09-27 | .bag.active 直读返回空 | cp 后 rosbag reindex 再读 | 已落 | sitl-debug-toolbox#4 | |
| C6 | 09-27 | goal pub 到刚起 planner 有建连停滞窗（发布丢失） | 发布后验证 cmd 偏移并重发（t3_verify_flight.sh 内置） | 已落 | sitl-debug-toolbox#5 | |
| C7 | 09-29 | 共享 rosgraph 双 agent 同时 rosbag play→双 clock/双图像串流（T3 重放外参被污染 tic=[-8.7,-4.1,-15.6]） | 重放必私有 master（113xx+roscore -p）；T4 链用 11314 避 T2 的 11313 | 已落 | night-ops-v61#2 + t4-jr-batch | 复发2（两次钉口径） |
| C8 | 09-29 | VINS config cam0/cam1 yaml 相对路径→cfg 复制移目录即失效 | cfg 复制必须留在原目录 | 已落 | night-ops-v61#2 | |
| C9 | 09-29 | throttle 段错误（/var/crash 实证）已架构性消除（全链路零 throttle 节点） | 勿再找 respawn 方案 | 已落 | t4-eline | |
| C10 | 09-28 | IMU 50Hz=MAVLINK_MODE_ONBOARD 硬编码；125Hz=lockstep 4ms 网格量化锁死（5000µs 请求量化到 8ms） | mavcmd 511 105 4000 对齐网格→223.7Hz（commit 632e0ee 全链落码）；要 >224Hz 需 world 500Hz+（收益有限已否决） | 已落 | sitl-imu-rate-grid-lock | |
| C11 | 09-28 | mavcmd 在链路建立前发出即丢且 topic 形式 exit 恒 0 无 ACK→t1_evidence/w2_sweep 全 50Hz 无效数据 | 该批数据勿引用；测频率用 bag header-stamp 直方图非 rostopic hz | 已落 | sitl-imu-rate-grid-lock | |
| C12 | 09-28 | topic_tools throttle 只能封顶不能钉住（100→84.2Hz）且多实例同话题叠加虚高 | 已否决入案；两侧统一名义 250Hz（用户拍板） | 已落 | sitl-imu 二轮补充 | |
| C13 | 09-28 | 探针三坑：roscore 后于 gzserver 则 gazebo_ros 相机插件阻塞；/tmp/px4-sock-0 残留锁报"already running"；pxh 经 FIFO 首字符易吞 | roscore 先行+清 sock 残留+pxh 命令重发校验 | 已落 | sitl-imu-rate-grid-lock | |
| C14 | 09-28 | ~/sitl_sim（运行时）与 ~/catkin_ws/sitl_sim（仓库副本）两目录已分歧 | 改脚本两边同步（preflight py 例外：仅仓库侧绝对路径引用） | 已落 | sitl-imu 新坑③ | |
| C15 | 09-30 | 双目同 ts 消息提取用单 ts 键→右目全丢 | (topic,ts) 复合键 | 已落 | t4-j3 工具三坑① | |
| C16 | 09-30 | OpenCV 点阵列 (N,1,2) 上 norm(axis=1) 打在"1"轴输出 (M,2) 矩阵 | 先 reshape(-1,2) | 已落 | t4-j3 工具三坑② | |
| C17 | 09-30 | 帧间差分 σ̂ 在移动序列被运动伪差分抬高 1-2 数量级 | 强制 P25 口径（16×16 patch 25 分位；stairs 6.56→0.044 实证）；j3_image_metrics.py | 已落 | t4-j3 | |
| C18 | 09-30→10-02 | 密度分母污染：全量外接框被远点污染（139×139m 失真）→P1-P99 修剪框；后跑飞段云再污染修剪框（袋2 ground 107129m²/air 3.21e8m³） | P1-P99 修剪框已落（jr3）；**漂移轮分区密度一律不可判读、分母方案（裁爆停窗或场景框）未拍板=C-4 待落** | 已落+待落 | t4-j3+t4-u3p+disk-chain-w0③ | 复发3（三代分母问题） |
| C19 | 10-01 | X1img2 重放物理性失败：跨域 dt 26.67s 钳制不可吸收→wait for imu 饿死→vins_node 18.2s segv | 物理性禁重放登记在册（重放层可复现实锤） | 已落 | t4-jr-batch | |
| C20 | 10-02 | W1.0 自纠：j3_replay_features.sh 吃原始袋（rosbag play）非帧目录——帧在袋亡=特征重放永久不可行（X1final 实锤入挂账） | 红线：重放吃原始袋；帧样仅供图像侧指标 | 已落 | t4-u3p-j13 | |
| C21 | 10-02 | 重放栈分水岭（10-01 20:35 cf0384→285278cc）跨栈数值不可比 | 每轮重放必登记当时 vins_node md5（红线在册） | 已落 | t4-u3p-j13 | |
| C22 | 10-04 | 对 route/ground 袋套注入代门=未预注册外推 | 红线②cohort 外不出三态（v5.14 H 章同律：MACH/hover 袋画像收录不出三态） | 已落 | t4-v514+v517 报告 | |
| C23 | 10-03 | EX-FAIL 坑位①零告警空统计：全帧不可读时工具退出 0 且输出合法 JSON n=0 | C14-FIX-1 `3a2722f`：零可读帧 rc=2+顶层 error 字段；下游 n_primary>0 禁只看退出码 | 已落 | verdicts L274-279 | |
| C24 | 10-03 | 坑位②NaN 字面量落盘（全白/黑帧→per_frame 34 处 NaN，allow_nan 未禁） | C14-FIX-2 `d2bb538`：逐字段 null+allow_nan=False | 已落 | verdicts L280 | |
| C25 | 10-03 | 坑位③density 复现性陷阱：fresh 默认 shift vs 在册逐袋实测 shift→总点数逐位同但 zone 计数差 2-50 点 | C14-FIX-3 `282a707`：shift 来源单一化（explicit/legacy/shift-file，无声明 rc=3）+shift_source 字段；对账必带逐袋 shift | 已落 | verdicts L281 | |
| C26 | 10-03 | 坑位④键集代差：在册 base json 缺 supply/grid 两键（W3 增量前代）→完整键集对账误判缺面 | C14-FIX-4 `ea4d12b`：schema_version 落盘+legacy_keys 兼容读+未知版本 rc=3 | 已落 | verdicts L282 | |
| C27 | 10-03 | 第五坑：在线轮 compact 袋零图像话题→图像链全程白跑 | 收货先 rosbag info 查话题面再走链（登记面生效：踩中 0/规避 3，详见 §1） | 已落 | verdicts L485+pool5_audit 全文 | |
| C28 | 10-02 | 勘误三则：p_sat v1"全零"=截断显示（真值 P50 1.30e-5）；年代效应 +112%→+182.22%（归一 0.30→0.8467）；45=云侧 vs 37=图像侧口径出入 | 勘误在册（verdicts §v5.4 勘误二则+d4 §5.7 闭合） | 已落 | t4-v54 | |
| C29 | 10-02→10-03 | odom csv 同 stamp 双行双解（诚实/虚构源交错）→按行游程分段误判；判别难点=echo（同消息重发）vs 双解（异载荷） | 分段按窗边界不按行游程；bit 级签名=同 stamp 双行 max2+重复组数相等，载荷逐位同/异判别（C-15 机制注记跨线复用） | 已落 | t4-v54 + t4-v57 | |
| C30 | 10-02 | PROV-DEV：B0 空窗判定 c1=c2=2（T2 R2F 回放在飞）仍对 3 袋只读 rosbag info——违规已发生 | 违规登记 verdicts；后续缺口任务全部补写空窗前置 | 已落 | verdicts L270-273 | |
| C31 | 10-03 | E4 切点细网格：U3PG cut×1.2 占比 0.5556→0.1389 落三态映射空隙翻型 | 降级注记在册+预注册无需修订；x08 注册口径未复现已注记 | 已落 | t4-v57 | |
| C32 | 10-04 | n=6 产额分位门与 cell CI 端点精确相等（PR1 seg1 M1 门=0.82=CI_lo），float64 噪声翻转判定 | 判据十进制定点（Decimal）+严格跨门不等式（prereg §2a 已写） | 已落 | t4-v514 | |
| C33 | 10-06 | 批处理脚本 truth 提取预注册模型名匹配 'iris' 漏 'iris_stereo_vins'（3090 袋实际模型名）→末端位置差 N/A 假阴性 | **待落：修口径重跑**（断连后恢复面挂起） | 待落 | t4-v514（v5.19 段） | |
| C34 | 10-05 | 引用闭环 t4_ref_closure.py NUC 存在性腿静默失败计为缺失→missing-both 抽 29 有 8 实存，报告数值不可引用（HIGH）；10-06 AP 事件补证=该腿硬编码 .5 而 NUC 实际 .6 | **待落：修脚本（存在性腿+地址口径）+重跑+recommit**（池件"引用闭环 NUC 腿 v2"在册） | 待落 | t4-v517 + network-20261006（.5 硬编码自查令） | |
| C35 | 09-27 | show_track:0 源码门控+VINS 未启动→特征跟踪判读 0 图；rviz_traj 0 张→渲染验收样本不足 | 当场改门控重启；样本不足如实登记不硬判 | 已落 | t4-vision-acceptance | |
| C36 | 10-05 | verdicts 坑五锚漂移 L440→L485（追加章致行号漂移，原文未变） | 引用前先 grep 重锚；§G/G2 登记体例=行 md5 前 8 位 | 已落 | memory_draft_t4_v517+pool5 §8 | |
| C37 | 10-05 | v5.16 P-N 系列第四池件在册定义缺（v5.17 任务书括号只列三件；v5.16 本体双侧皆缺） | **待主会话补定义**（执行面只做括号内三项口径不变） | 待主会话裁 | pool5 §14 | |

### 域D：流程/审核/方法论（7 条）

| # | 日期 | 机理 | 对冲机制 | 状态 | 来源 | 复发 |
|---|---|---|---|---|---|---|
| D1 | 10-03→10-05 | 工作流/夜报初版连被用户否决三次同型（v5.7"深度不够+有遗漏"、v5.14 八缺漏、v5.17 二遍 11 处）——单元名对齐≠条款覆盖 | "任务书条款→脚本机制"逐行映射表法（红线/卡点/附录/环境事实四类都有着落）；卡点各条=等待条件清单必须落轮询触发面 | 已落 | t4-v57 + t4-v514 + t4-v517 | 复发3（三夜三否三修） |
| D2 | 10-03 | 回填与数据包由同一执行者自核→不可信 | 回填与数据包必须独立复核员（107/107+34/34 逐位对账先例） | 已落 | t4-v57 | |
| D3 | 10-04 | watcher 自监测文案含"@T4"字样→grep 自吞自我触发 | 自监测文案排除自身关键词+心跳行带 heartbeat 标记供 grep -v 排除 | 已落 | t4-v514 | |
| D4 | 10-05 | 判定串"不一致"用子串匹配→含"一致"即误报 | 判定函数全词/反向集合匹配（v5.17 审核抓出） | 已落 | t4-v517 | |
| D5 | 10-02 | 子代理模型未钉死→首投被拒 | 子代理模型必须 `account:bigmodel-individual-coding-plan/GLM-5.3-Flash`（钉死串） | 已落 | t4-v54 | |
| D6 | 09-27 | 域标签式移交=偷懒甩活（"EKF2 归 T1"，用户两次纠正）——对方任务书没排这项=移交无人接手卡自己验收 | 拆成具体步骤看材料工具在谁手+核对对方任务书真排了；真协调面仅=共享源码修改（STATUS 异议窗）与锁窗排期 | 已落 | sitl-debug-toolbox#7 | |
| D7 | 09-29 | bag_extract_moments.py 三坑：不 source ROS 即跑挂；goal 用 bag 接收时间非 header.stamp=0；land 取末态 | 工具注记在册（vision_materials.md）；land 末态如实标注 | 已落 | t4-eline | |

---

## 3. 复发热点 TOP（合并条 15 处，按复发次数排序）

1. **并发互斥/大 IO**（B1，复发 3）——三次死机/险情换来红线④，仍是最高风险面。
2. **工作流初版被否**（D1，复发 3）——逐行映射法是现行对冲，勿省。
3. **密度分母污染**（C18，复发 3）——三代问题，漂移轮分母方案仍未拍板（唯一带数据面的活复发点）。
4. 中文通道（A2，复发 2）、ROS env×set -u（A4/A5 各复发 2）、CRLF 通道（A10，复发 2）、path cwd 基线（A14，复发 2）、sed 转义/残留（A20，复发 2）、退出码管道（C4，复发 2）、私有 master（C7，复发 2）、预注册（C1，复发 2）、category 传参（C2，复发 2）、scp 改写（A15 实锤 2）、三层转义（A18 实锤 2）、WAN 瘫（B16 持续两夜）。

## 4. 待落清单（9 条，本表唯一"未闭合"面）

| # | 条目 | 权属 |
|---|---|---|
| 1 | B6 t4wf 孤儿锁：异常退出 release 路径未修（工具债在册） | T4 工具面 |
| 2 | B9 僵尸治理器误杀 113xx 私有 master 进程——"待 T4 核实"挂未销 | T4 核实 |
| 3 | B17 AP 终局回 .5 用户裁定未见执行；跨机脚本 .6/.5 地址口径分裂风险 | 用户/各线自查 |
| 4 | B19 STATUS 跨机分叉（W1 回执仅 NUC 侧）是否补镜像行 | 主会话裁 |
| 5 | C18 漂移轮密度分母方案（裁爆停窗或场景框）未拍板（C-4） | 主会话/T2 联合 |
| 6 | C33 truth 模型名 'iris'→'iris_stereo_vins' 修口径重跑 | T4（断连恢复面） |
| 7 | C34 引用闭环 NUC 腿 v2：修存在性腿（ssh 静默失败+.5 硬编码）+重跑+recommit | T4 池件 |
| 8 | C37 v5.16 P-N 第四池件定义缺 | 主会话补 |
| 9 | C27 派生：compact/零图像袋族图像侧收货永久缺——月报口径=只登记不提帧（维持性，非修复项） | 各线收货面 |

## 5. 本夜探测注记（环境事实核实）

- nuc2（3090）：`ssh -o BatchMode=yes -o ConnectTimeout=8 nuc2 "date +%H:%M"` → **08:03，rc=0，可达**。
- nuc（NUC .6）：同命令 → **08:03，rc=0，可达**。
- 与任务书 L22"NUC .6 上电[当前断电中]"表述**矛盾**：实测可达，与用户 2026-10-09 口径（两机均应可达）一致。以实测为准；任务书断电前提已过时，待主会话在下册任务书更正。本单元零远端写操作（唯一远端动作=STATUS 心跳追加+verdicts 只读 grep），未依赖该矛盾面。
- post-quantum 警告按纪律忽略（ssh 纪律⑥）。

---
（本报告完。第五坑月报 v5.26=全增量并入版；下任并入基线=本文 86 条+§4 待落 9 条。）

---

## 第十九周期增补（2026-10-10 夜 T4 v5.31 单元 6：第十八周期到货 23 条全量并入+本夜 T4 新增 2 条=25 条）

> 来源四族：T1 v11.39 夜报 F 节八条（3090 t1_evidence/v11_39_2026-10-09/night_report_v1139.md）+T2 v10.11 完成清账版 F 节六条（~/catkin_ws/sitl_sim/plans_T2_v10.11.md）+T3 v11.1 收官 F 节三条（STATUS 13:5x 行）+总设计师预录六条（v5.31 任务书单元 6）。机理全文转录，零删改。

### T1 八坑（v11.39 战役）

1. **批多实例连环互杀（D-1010-T1-01）**：kill 未验尸（PID 未确认死亡）→旧批存活→双批并发→force_clean 互杀+孤儿 drill 跨批注入；根治=PID 文件单例守卫（v1 pgrep 方案自噬：$() 替换子壳继承父 cmdline 被自身匹配——v2 PID 文件零 cmdline 匹配）。
2. **set -u 遇 ROS 链复发**：批脚本 source ROS 前未 export ROS_DISTRO（drill 脚本有正解模式未复制——复用纪律）。
3. **pkill -f 自匹配第三次**：pkill -f "px4ctrl_node" 匹配远程 bash -c 自身命令行秒杀会话——-x 精确名匹配解。
4. **近点 goal 落地边界**：S1 类近点到达+降落≈poscmd-live+30-70s，固定 sleep 注入窗必落地面——flying 门 v4 双门（poscmd 存活+armed:True）+postgate 从 armed 起算。
5. **land_detector 冻结 odom 伪落地**：盲降期 C1+C2 伪满足→landed 谎报→高位误 idle 坠落风险——idle 门=px4_on_ground||odom_ok。
6. **ulog 时间戳=UTC**：rootfs/log 目录名比本地 -8h。
7. **catkin build 不重建 gtest 二进制**：--make-args tests 拖累全依赖链（uav_utils tests 链接失败阻塞）——build/px4ctrl 目录直接 make test_fsm_decision 单目标解。
8. **长 ssh 前台命令超时截断外层循环**：同步跑轮的 ssh 550-600s 超时会砍在 drill 毕与登账行之间（两轮补登实证）——轮编排必须 setsid 后台化+轮询登账。

### T2 六坑（v10.10 战役）

9. **sed 替换含字面反斜杠的文本不匹配**：批脚本 banner grep 模式没换成→CSV 列 bug，join 修复。
10. **批脚本 VINSMD5 捕获薄壳**：vins_node≠真实栈 libvins_lib.so（应记 lib md5）。
11. **awk NR==FNR 跨文件 FS 陷阱**：map 空格文件被逗号 FS 吞键。
12. **Windows 本机无 python3**：编辑走专用工具勿依赖本机脚本。
13. **nohup 后台 ssh 挂壳**：setsid+stdin 重定向+本地任务及时 stop。
14. **锁 owner PID=$$ 构造脆弱（D-1010-T2-01 根因）**：锁脚本子进程 PID get 返回即死→活轮锁被"合法"接管；锁侧已修（场忙防御）+**根治已由 T4 v5.31 单元 5 落地**（sitl_lock.sh v3 owner=调用方会话 PID 契约，md5 d7b3efa0，E1 回归 21/21，commit 7e8aa32）——本条就此闭环销号。

### T3 三坑（v11.1 战役）

15. **STATUS 时间标签自违反**：写行内嵌时间须先 date 取远端时间再落笔（自报时间与实际脱节）。
16. **pgrep 自匹配**（T1 同族第三实例）：pgrep/pkill 模式匹配到自身命令行——[x] 字符类或 -x 精确名。
17. **显示层乱码≠文件坏（误判判别法）**：终端显示乱码先 md5+hexdump 验文件本体，再判编码；显示层与存储层分离。

### 总设计师预录六坑（实机预录会话，v5.31 任务书转录）

18. **USB CDC 断链自愈**：USB 串口断链有自愈窗口但劣化累积（r2 批换线+固定后零断流=单一根因证据链闭合）。
19. **rsync --partial**：大袋传输必带 --partial（中断续传），否则重传整袋。
20. **rostopic hz 首采假象**：频率采样首窗偏低，须弃首采段取稳态窗。
21. **分母陷阱**：比率指标先核分母口径（帧数/时长/轮数三选一错即全错）。
22. **引号嵌套**：多层引号（ssh+bash+awk 三层）先写模板再逐层展开，禁手拼。
23. **/tmp 易失**：/tmp 产物即产即固化到 evidence 目录（重启清空；本夜九袋/75 袋/批收货/重放产物全部按此纪律落盘 t4_v531_20261010/）。

### T4 本夜新增（v5.31 战役，收货链实战）

24. **bash 5.0.17 `local a="$1" b="$a/x"` 一行多赋值非左到右**：b 展开取旧值（实测 b="[/x]"）；38 行 NOBAG 假象根因。与引用闭环 v1 tilde 缺陷（I5b 三源之三）同族=展开时序/展开域缺陷。修复=拆行赋值。
25. **awk POSIX ERE 无反引用**：`\1` 回引匹配全假阳性（100 行 N/N 等值被判 MISMATCH=100）——等值校验在 awk 不可用，改 grep -P 或分布核读。

（第十九周期并入完：86+25=111 条为下任并入基线。）
