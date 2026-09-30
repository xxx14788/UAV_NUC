# P0-B F4a：vins_kill_watch.sh 自查判定书（T1 v8.0 夜1，2026-10-01 02:4x）

结论：**不坐实为杀手——排除**。T2 21:20 点名系名称模式误报（"kill_watch" 名字联想），
未读脚本正文。本件为正式排除证据，入悬案池（SIGTERM 案维持 open，头号候选仍=同名节点注册杀）。

## 1. 脚本杀逻辑审计（全文逐行）

`/usr/local/bin/vins_kill_watch.sh`（1284B，mtime 2026-09-30 02:40:38）：
- **零 kill 面**：全文无 kill/pkill/SIGTERM 任何形态。仅 pgrep -x vins_node（读）/ ps -eo（读）/
  journalctl（读）/ dmesg（读），转储到 /var/log/vins_kill_watch/。
- 身份=**T1-F4 E5 自家伏击相机**（脚本头自述 "T1-F4 E5: vins_node kill ambush …
  Designed to catch the 10:40:26-type killer"），2026-09-30 夜由 T1 v7 部署。
- 资源面：@2Hz pgrep，转储仅发生于 vins_node 起/死/换 PID 瞬间，单份 ~22KB，上限 200 份——无性能威胁面。

## 2. 自启机制与触发史（journal 对表）

- 自启=crontab `@reboot`。journal 实锤**双注册缺陷**：uav 与 root 两个 crontab 各一条
  （10:49/10:55/19:22/20:26/20:58 五次开机均成对触发 `(uav) CMD` + `(root) CMD`）。
  运行态 4 PID=双实例，解释转储目录 1s 间隔成对文件（112026/112027 等）。
- **10:40:2x 案发对时**：案发在 09-30 01:06–10:49 开机段（last reboot 实锤）；脚本 02:40:38 落盘于该段，
  但 `@reboot` 要下次开机才触发——首次触发 10:49:39。**伏击晚到 9 分钟错过案发**，
  与"案发时刻零转储"自洽。首个转储 11:20:26 = T2 矩阵轮正常起 vins_node（`[] -> [50171]`）。
- 82 份转储全部为矩阵轮正常起停形态；无未解释死亡被捕获（案发时段不在覆盖窗内）。

## 3. 修复动作（本次已执行）

1. **去重**：删除 uav crontab 的 @reboot 条目（保留 root 侧——脚本头声明需 root 方可
   journalctl -k/dmesg 全量）。下次开机起单实例。
2. **在跑双实例清理**：精确 PID 杀 uav 实例（753/747），root 实例（750/748）存活继续伏击。

## 4. 对 SIGTERM 悬案的意义（移交 F4 续办）

- 排除一支后，头号候选维持 F4 中判定的**同名节点注册杀**（roslaunch XML-RPC：新 vins_estimator
  注册→master 令旧同名节点 shutdown→精确单点 SIGTERM，外观与 10:40 现场完全匹配）。
- 伏击相机保持武装：再现即捕获全进程表(含父链)+journal 前 20s——正是锁定"第二启动主体"所需证据面。
- F4 剩余：E5 bpftrace/auditd 信号伏击、10:40:2x 第二 vins_estimator 启动者追踪、E6/E7 清毒+验收。

## 5. 通告面

@T2：你 21:20 点名的 vins_kill_watch.sh 已正式排除（零杀逻辑，系 T1 伏击相机），双注册缺陷已修，
10:40 悬案头号候选仍=同名节点注册杀。@T3：同知会（6.5 卡点可引用本件）。
