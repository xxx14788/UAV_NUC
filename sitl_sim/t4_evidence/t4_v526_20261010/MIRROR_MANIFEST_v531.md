# T4 v5.31 单元 2 镜像清单（2026-10-10 夜）

- 动作：v5.26 战役产物系全量镜像 Windows 正源 → 3090 `~/sitl_sim/t4_evidence/t4_v526_20261010/`（两段式 scp→/tmp→cp 落位）→ cp 入仓树 `~/catkin_ws/sitl_sim/t4_evidence/t4_v526_20261010/` 随 commit。
- 双端对账：28/28 文件 md5 逐位一致（`MD5S_local_v531.txt`=Windows 端、`MD5S_3090_v531.txt`=3090 端；对账凭据 /tmp/md5_local.txt vs /tmp/md5_remote.txt diff 空=格式差异外零差异）。
- 锚核验：E4 复核件 `e4_framelevel_recheck_v526.md` md5 **5aed12a1**（在册值一致，零触碰）✓；prereg（未镜像，原位 `t4_work_20261002/docs/t4_e4_bimodal_prereg.md`）md5 **fd750919** ✓；verdicts_v2 正本 3090 `~/catkin_ws/docs/t4_verdicts_v2.md` md5 **4f34d500** ✓。
- **verdicts 草稿 md5 变更登记**：`verdicts_draft_v526.md` 89375403 → **bd042be6**——v5.31 单元 1 增补节（待裁三项处置+销号）追加于尾部，正文 §0-§7 与草稿员签记零改动；本 md5 即增补后凭据。
- 工具件：`tools/t4_ref_closure_v2.py` md5 **c3d233c5**（任务书锚一致）；`tools/draft2verdicts.py` md5 **87593eb4**。
- 集合构成：verdicts 草稿 1 + E4 复核件 2（双名同 content）+ 台账（bag_receipt_ledger）1 + cohort 七分册 7 + 池三件 3 + 月报（pit_monthly_report）1 + 夜报 1 + e4_der 4（防 /tmp 易失）+ tools 6 + staging_hover 判读文 1 + 输入 md5 凭据 2 = 28 件。
- u3_hover_drift.py 补镜像验证：3090 `~/sitl_sim/t1_evidence/v10_2026-10-02/u3_hover_drift.py` md5 **628faa64** 与 Windows 本地副本（tmp/night_1004）一致——补镜像已在位，v5.26 MIRROR_RECORD:9 悬账就此验证销号（v5.31 单元 2）。
- 执行=T4 v5.31 会话（第十九周期）；工程册 T1ENG v11.40 并行在册（共享树逐件 add 纪律遵守）。
