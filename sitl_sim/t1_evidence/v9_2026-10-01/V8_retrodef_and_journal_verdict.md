# V8 重定义与执行 + F4b journal 案定案（2026-10-01 20:4x-20:55；用户 10-01 夜授权）

## 一、V8 重定义（重构件，非历史还原）

**出处与授权**：v8.0 册定义遗失（全库考古未中，v8.1/v9.0 只余引用行"V8 驱动脚本修复(0 锁对账)/V8 3/3"）。用户 2026-10-01 夜裁决："根据内容写定义"——本节即重构产物，**登记为勘误/重定义件，声明非 v8.0 历史定义还原**。

**V8 = T1 驱动脚本自检与缺陷修复件（vins_smoke.sh 全家桶）**：

- "3/3" = 三自检全绿：
  1. **PROBECHECK**（探针链自检）：--probecheck init-only 模式，E2uls 行产出且 |dP| 基线级；
  2. **锁自检**：sitl_lock v2 get/status（死主侦测）/release + 侧锁口径（SITL_LOCK_FILE）+ 磁盘水位门；
  3. **清场自检**：轮终四项断言 px4=0/gz=0/锁空/df>20G。
- "驱动先修" = 现存实锤缺陷修复：
  a. arrive_watch 监视器 NO_ODOM 硬化（本件执行，见下）；
  b. 双副本 md5 守卫（已先行落地，fd85eec，计入本件）。

## 二、执行凭据（3/3 全绿，2026-10-01 20:42-20:53）

| 自检 | 结果 | 凭据 |
|---|---|---|
| 2. 锁自检 | **PASS** | 侧锁 get→status（死主侦测 PID=1943543(DEAD) 正确报）→release→锁文件零残留；盘门 71G PASS |
| 1. PROBECHECK | **PASS** | run tag=V8_PROBECHECK，E2uls=44 行，|dP| 3.4e-3..6.2e-3（基线级），E2clamp/E2gap=0 |
| 3. 清场自检 | **PASS** | 轮终 px4=0/gz=0/SITL.lock 空/df=71974704KB，四项断言全过 |

**驱动修复面（vins_smoke.sh @f719e70a，双副本同步）**：arrive_watch 补丁 4 锚点——odom/truth 样本计数（n_odom/n_truth）+ 终印三分支诊断（**NO_ODOM**/NO_GT/TIMEOUT+计数）。原缺陷=E-4 首窗两轮 min_truth=1e9/last=-1 的真根因（见勘误①）：观察窗内 /vins_estimator/imu_propagate 零流入（VINS 爆后停流）→ p0/anchor 永不置位 → 哨兵原样出。新行为=NO_ODOM/NO_GT 明示判别+样本计数，监视器死区可判。修法为纯诊断增强，零控制行为变化。

## 三、勘误链（本件衍生）

1. **E4_window1_report.md 的 watcher 缺陷定性勘误**：原记"对 goal=(0,0,1) 类轮的 watcher 缺陷"——实为 **VINS 停流后的 NO_ODOM 盲区**（与 goal 值无关；goal=(7,-4,1) 类轮若遇 VINS 停流同样触发）。已按新根因修复。
2. **"VINS 存活至预算尾"转述勘误**（对 T2 20:40 判读行的转述）：轮 1 爆后实为**停流**（imu_propagate 断流，观察窗零样本即此）——"进程存活"与"数据流存活"需分账，T2 判读若依赖"存活"表述请以此为准。
3. v8.1"v1.14"→v1.17（已先行勘误，尾件 2）；D.3"16 轮"→13 轮（已先行勘误）。

## 四、F4b 的 10:40:2x SIGTERM 案——journal 定案（boot 表实锤）

- 用户裁决路径="uav 加 adm 组"，执行前实测发现 **uav 已在 adm 组**（groups=...,4(adm),...）——非权限问题，此前失败系探针姿势错（误走 sudo -n 与 journalctl --user）。
- 正读 journal 后：**boot 表显示 09-30 10:55:28 CST 起为本机 boot -3**；10:40:2x 案发于其前一 boot，该 boot 的 journal **已随 log 轮转物理灭失**（现存仅 boot -3..0 四个；09-29 磁盘 98% 危机期的 vacuum 波及）。
- 定案：**journal 证据面灭失，10:40:2x 回溯永久不可达**——按 v8.1 预留的"证据面空则挂账"条款转定案（非挂账）：SIGTERM 悬案仅余设伏相机单证据面（在位），等再现。F4b 的"10:40:2x 追踪"子件闭账。

## 五、引用

- 任务书：v9.0 等待池⑧/⑨、P1-3 表 V8 行
- 关联：E4_window1_report.md（watcher 缺陷原记录）、fd85eec（双副本守卫）、d55c710（PROBECHECK 引入）、C06 DOSSIER（SIGTERM 案与 journal 判据分族）
