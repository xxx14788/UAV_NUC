# T4 池件·引用闭环 NUC 腿 v2（2026-10-09，v5.26 单元5-1）

执行=T4 池件线；执行域探测：3090（ssh nuc2，ghj@192.168.0.4）可达（08:27 实测 NUC2_OK）、NUC=192.168.0.6 可达（08:28 实测 NUC_OK，hostname=uav4，用户 uav，HOME=/home/uav）——与"双机应可达"预期一致，无降级。本件全程只读远端（ssh test -e/-f、ls、git show、find，零写入零删除零大 IO；动手前 3090 实测 load 0.00、rosbag/gzserver/px4 全 0，无 T2 在飞）。3090 远端时间戳取 `date +%H:%M` 实测（08:27/08:41/08:52）。

## 0. 结论速览

- v1 缺陷根因定位到行级并实证；v2 副本落盘 **`t4_v526_out/tools/t4_ref_closure_v2.py`（md5 前8 `c3d233c5`，py_compile 通过）**，不复写 v1/T1 任何原文件。
- 自证 **74/74 全判对**（v1 报告缺失清单全量 70 条 + 双向对照 4 条），v2 判定与独立 ground truth 逐条一致，0 mismatch。
- **新实锤：v1 报告 61 条 missing-both 中 14 条实存 NUC**（T1 代持版当年只翻出 3 条——其 find 兜底 head -100 挤出效应在本夜被双向复现），56 条实缺维持。
- 遗留：3090 侧权威重跑（T1 commit 2f67d89 明文 DEFERRED 项）仍待可写腿执行；本夜产出 NUC 腿结果文件可直接回灌。

## 1. 考古：v1 本体与缺陷机理（全部本夜实读）

| 件 | 位置 | md5/commit |
|---|---|---|
| 带病 v1 脚本 | 3090 `~/catkin_ws/sitl_sim/analysis/t4_ref_closure.py` @ git `9c5f129`（git show 只读取回） | `f17ebfcdf10ad947004319bc90579c29`（前8 **f17ebfcd**，与报告自报一致） |
| v1 报告（带病产物） | 3090 `~/catkin_ws/sitl_sim/t4_evidence/t4_ref_closure_20261005.md`（2026-10-05 03:54:06 生成，取回本地镜像 `tmp_v1fetch/`） | 本地 `eea4d214`（远端同） |
| T1 代持原位修复 | 同路径现盘版，commit `2f67d89`（"T4-pool1 [T1 代持 T4 域]: NUC-leg v2 fix"） | `e850bf42` |
| 记忆正录 | `t4-v517-3090-first-night.md`（抽 29 missing-both 有 8 实存、报告不可引、待修重跑）；本地夜报 `t4_work_3090_20261005/reports/t4_v517_night_report.md:35`（高严重项） | — |

**根因（v1 原版 NUC 腿，git 9c5f129 对应行）**：

```python
for tok, anchored in items:
    if anchored:
        cond = '[ -e "%s" ]' % tok      # ← tok 形如 ~/catkin_ws/docs/x.md
```

POSIX sh **双引号内不展开 `~`**，`[ -e "~/..." ]` 测的是字面 `~` 开头路径，恒假 → **一切 `~/` 锚定引用在 NUC 腿一律误判 absent** → 实存文件被计入 missing-both。放大器：v5.17 夜 3090 `~/.ssh/config` 无 `Host nuc`（夜报 L35 实测在案），实际走"本地中继批量代查"回灌 `--nuc-result-file`，中继与脚本同病 → 报告"缺失70=双机皆无61+仅NUC 9"的 NUC 腿分类失实（高严重，报告不可引）。独立复核抽 29 实测 8 实存（记忆正录）；T1 修复 commit 自证抽 61 全量实测 3 翻 present。

**T1 代持版（e850bf42）已修主根因**（$HOME 展开+7 基目录对齐+P2 find 兜底），但四残余缺陷本夜实证仍在（见 §2），且其"权威 3090 侧重跑 DEFERRED"（当夜 3090 网络半死）至今未做——报告正本仍是 f17ebfcd 带病产物，verdicts 82c0fa3 只做了 /tmp 时效 9 项定性勘误。

## 2. v2 改动（基于 e850bf42，`tools/t4_ref_closure_v2.py`，md5 前8 `c3d233c5`）

头注含：v1 md5 前8 **f17ebfcd** + 修复点一句话 + 中间版源流。改动逐条（全部为自证过程实证驱动）：

1. **主根因修复承 T1**：`~/` 锚定 token 经 `$HOME` 展开 probe（`[ -e "$HOME/x" ]`），7 基目录与 3090 本地腿 1:1 镜像。
2. **P2 find 兜底分块加固**：cap 100→400、块 50→40。实证：T1 版全量 61 探仅翻 3 条，v2 同面翻 **14 条**——被挤出命中的失败模式在本夜被双向复现（自证驱动第一版不分块 find 同样漏掉 `v1_ground_salvage_211520.bag`，v2 分块版找到，`ls -ld` 实锤 299MB 袋在位）。
3. **basename 配对策略按锚定分级**：未锚定缺失+basename 命中 → `present (basename hit: 路径)`（与 3090 腿同策略）；`~/` 锚定缺失+命中 → `absent (basename hint: 路径)`（严格路径语义，只出证据不翻案）；**`/` 根锚定缺失 → 恒 plain absent 不配对**（修 e850bf42 残余：根路径 token 可被 $HOME 下同名无关文件误翻 present）。
4. **P2 覆盖面扩到无斜杠 token**（修 e850bf42 残余：`x.bag` 形态袋在 `$HOME/sitl_sim/bags/` 下时七基目录探不到、find 又不覆盖 → 漏检翻案面）。
5. **ssh 探针 bytes 传输**（`input=script.encode()`）：Windows 控制机中继时 text 模式把 `\n` 翻成 `\r\n`，远端 sh `Syntax error: expecting "fi"`、stdout 全空 → 全体静默 skip/缺失——**与 v1 事故同族"ssh 检查静默失败计缺失"**，本夜 live 抓获后加固，v2 因此可在 3090 本机与 Windows 中继双形态运行。
6. 新增 `--probe-tokens TSV` 独立批量核验模式（token\tanchored → token\tstatus），供自证与未来回灌复用；CLI 实测 rc=0。

## 3. 自证证据（ask 第 3 条，逐条可溯）

方法：v1 报告缺失清单 70 条（61 missing-both + 9 nuc-only）由报告表格机械提取（`tmp_v1fetch/tokens_v1report.tsv`）；「当初 8 个实存却被判 missing」的**条目级清单不可寻**（夜报 L35 明文"失实条目级清单=任务书文本截断未载全"），故按 ask 备选口径取"全量 70 ≥ 10 条"覆盖之（含 T1 commit 点名的 3 翻案样本在内）。判定=v2 NUC 腿批量 probe；ground truth=驱动 `tools/t4_ref_closure_v2_selfcheck.py` 独立手写实现（严格路径逐 token `[ -e ]` + 独立 find 兜底 + python 侧配对，不调用 v2 函数）；每条 present/hint 路径再过 `test -f` + `ls -ld` 出证。涉及远端存在性只用 ssh test -e/-f / ls 只读判。

**结果：agree=74 / mismatch=0 / total=74**（70 报告条 + 4 对照）。逐条明细落 `tools/selfcheck_results.tsv`（token|v1类别|anchored|v2判定|GT严格路径|GT basename命中|verdict）。

- **14 条翻案**（v1 判 missing-both，NUC 实存，全部有 FILE_OK+ls 凭据）：
  `EV/RESULT.txt`、`EV/simvins.log`、`EV/sitl.log` → `~/sitl_sim/vins_smoke_runs/run_T2BL6_203956/`（=T1 点名 3 条）；`R1G_g_{chi2,depth,reprop,smooth}/sim_stereo_imu_config.yaml` ×4 → `~/sitl_sim/t2_configs/E15_acc050_gyr001/`；`_j3/manifest.json` → `vision_inputs/U3PR1_212450_j3/`；`online/replay_frames.csv` → `t2_results/R1_dissect/`；`out-root/queue_state.json` → `vision_inputs/`；`realsense_d435/left.yaml` → `t2_configs/E15_acc050_gyr001/`；`t2v3_ground_205302.bag` → `bags/`（**K-1 迁移参照袋，v1 判双机皆无**）；`t4_work_20261002/.../last_verdict_audit_v58.txt` → `t4_selftest/.bak_lockfix_20261004/`；`v1_ground_salvage_211520.bag` → `catkin_ws/sitl_sim/t1_evidence/v1_2026-09-28/`（299MB）。
- **56 条实缺维持**（clean absent，v1 判缺成立）。
- **双向对照 4/4**：`~/.bashrc`=present、`/home/uav/.bashrc`=present（存在判在）；`~/zzz_v2check_absent_ctrl.bag`=absent、`zzz_ctrl_dir_v2check/zzz_nofind_ctrl.txt`=absent（缺失判缺）。
- **3090 腿抽查 3/3**（v1 报告 3090 侧判定与现盘一致）：`src/VINS-Fusion/config/fast_drone_250.yaml` 实存（符 v1 备注列）；`~/sitl_sim/EV/RESULT.txt` 3090 实缺（缺失输入面成立）；v1 报告本体在位。
- **历史三数对账**：记忆正录"抽 29 有 8 实存"（10-05 凌晨）／T1 版"61 探 3 翻"（10-05，head -100 挤出低估）／本夜 v2"70 探 14 翻"——同族趋势，14 为当前全量口径。

## 4. 遗留（如实）

1. **3090 侧权威重跑未做**：重跑须在 3090 本机跑 v2 全扫描（3090 本地腿=os.path.exists），需把 v2 部署到 `~/catkin_ws/sitl_sim/analysis/` 并 commit——本件 ssh nuc2 权限=只读，不代写。T1 commit 2f67d89 的 DEFERRED 项维持挂账；建议部署腿以 `T4-poolRef` 前缀 commit v2（md5 c3d233c5）后重跑，报告日期后缀不同不覆写历史件。
2. **本夜 NUC 腿结果已可回灌**：`tools/selfcheck_results.tsv` 即 70 token 的 v2 NUC 腿判定，未来 3090 重跑可经 `--nuc-result-file` 合并（省一次跨机批量探查）。
3. **9 条 nuc-only `/tmp/*` 时效定性**已在 verdicts 82c0fa3 勘误在册（tmp 易失，正本零损失），本件未改判。
4. P2 find 边界与 v1/T1 相同：只扫 `$HOME/sitl_sim`+`$HOME/catkin_ws` 两树（maxdepth 7、prune .git/build/devel/logs）；NUC 其他路径的实存不计翻案（56 条实缺按此口径）。
5. **心跳走本地镜像**：本件 ssh nuc2 只读权限不可写远端 STATUS，心跳行落 `D:/drone_VINS/t4_v526_out/STATUS_local_mirror.md`，同文写入本 notes。
6. 带病 v1 报告正本未动（历史件不覆写）；其"不可引"状态以本件 §1-§3 为勘误依据，供主会话定稿。

## 5. 产物清单（全部落 D:/drone_VINS/t4_v526_out/）

| 件 | 说明 | md5 前8 |
|---|---|---|
| `tools/t4_ref_closure_v2.py` | v2 副本（头注 v1 md5+修复点） | c3d233c5 |
| `tools/t4_ref_closure_v2_selfcheck.py` | 自证驱动（独立 GT 实现） | — |
| `tools/selfcheck_results.tsv` | 74 条逐条判定+GT 对账 | — |
| `tmp_v1fetch/t4_ref_closure.py` | 带病 v1 镜像（f17ebfcd） | e850bf42*（注：此为 T1 修复版镜像） |
| `tmp_v1fetch/tokens_v1report.tsv` | v1 报告缺失清单 70 条提取 | — |
| `tmp_v1fetch/t4_ref_closure_20261005.md` | v1 带病报告镜像 | eea4d214 |

（*`tmp_v1fetch/t4_ref_closure.py` 为 3090 现盘 e850bf42 版镜像，双端 md5 一致；带病 f17ebfcd 原文以 3090 git `9c5f129` 为正源，本夜 git show 只读核验其 NUC 腿代码行并引于 §1。）

— T4 池件线，2026-10-09（远端时间戳 08:52 实测）
