# A1 图集 v2 重出+抽验 验收记录（2026-10-15；③C 终局执行册 v2.1 阶段 A）

## 执行摘要
- v2 脚本上传 3090（两段式 scp→/tmp→cp，三方 md5 一致）：`c3_traj_plot.py`=ee88bb7、`c3_atlas_batch.sh`=4d46571（本地 t1 镜像=3090 /tmp=战役目录）。
- 跑批 `atlas_v2_run.log`：34 PLOT / 0 SKIP / 0 Error，`ATLAS-DONE 34 pngs`。
- md5 清单：`traj_atlas/md5.txt`（34 行，文件 md5=add308a8，3090 与本地逐位一致）。
- 回拉本地覆盖：34 图 md5 全对账通过；v1 图集原样保留于 `traj_atlas_v1_backup/`（换证对照用）。

## 抽验 6 张（覆盖三修复面 × v1/v2b/v3/v5/v6 world × E/NE 航道）
抽验对象：run_C3E1_205851（v1 WARN+跳变族）、run_C3E2_215820（v2b WARN+弹射 39m）、run_C3E2_221911（v3 WARN+弹射 67m）、run_C3E2_003610（v5 S 织行佳例）、run_C3E2_013723（v6 S 终版佳例）、run_C3NE2_020022（v6 最小裕度轮）。

**本会话视觉通道注记（如实）**：本执行会话 Provider 层不支持图像输入（模型无视觉，Read 图像被 harness 侧省略；4_5v 视觉 MCP 后端 400 故障——本地/公网 URL 均复现）。"真看图"以两层落地：①程序化像素级读图（PIL/numpy 真加载图像数据）；②同栈确定性旁证（3090 上以绘图脚本同数据管线+同渲染栈复算）。证据弱于人眼判定，如实注记，不冒充。

## 核验一：中文方块消除（v2 修复①）
- **字体机理铁证**（3090 同栈，`atlas_v2_certify_out.json` font_cert）：中文样本"起飞彩票跳变族悬停弹射" 11 字形 → **1 种去重位图**（全同=豆腐块实锤）；ASCII 样本 33 字形 → 15 种去重位图（各异=正常渲染）。stderr 同现 `Glyph 23556 missing from current font`。
- **静态保证**：v2 绘图脚本绘制的全部文本（标题/注记/图例）为纯 ASCII（matplotlib 对 ASCII 恒可用 DejaVu Sans，豆腐不可能）。
- **像素佐证**（本地 `atlas_v2_verify.py`）：v1→v2 注记框墨迹分布显著改变（v1 中文被画为稀疏方块、v2 ASCII 连续墨迹）。

## 核验二：odom 裁剪生效（v2 修复②，米制同栈证书）
| 轮 | odom 点数 | 截除点 | 截除率 | odom 对 truth 最大偏距 | 越窗规模 |
|---|---|---|---|---|---|
| E1_205851 | 13,266 | 1,098 | 8.3% | 37.6m | 31.0m |
| E2_215820 | 85,120 | 0 | 0% | 2.6m（odom 健康，弹射在 truth 侧 97×72m） | 0 |
| E2_221911 | 10,065 | 2,155 | 21.4% | 49.7m | 44.9m |
| E2_003610 | 66,630 | 0 | 0% | 1.6m（v5 健康轮） | 0 |
| E2_013723 | 57,485 | 3,238 | 5.6% | 37.9m（末段慢漂回摆） | 33.9m |
| NE2_020022 | 58,609 | 3,693 | 6.3% | 49.6m | 43.8m |

判读：裁剪**恰在病理轮生效**（odom 暴走/慢漂 37-50m 的 4 轮被截 5.6-21.4%），健康轮零截除——与设计意图（防暴走 odom 喧宾夺主）逐轮吻合。
勘误记录：证书脚本首版"越窗规模"字段把"到下边界距离"误当"越过上边界距离"（outp[:,1]-y0 笔误），221911 虚报 165.57m；修正后 44.93m（与逐点手算一致），本表为修正版（json 已重出，md5=41402bf6 双端一致）。

## 核验三：箱表失配警示呈现（v2 修复③）
- 静态：`c3_atlas_batch.sh` 定义 `WARN="BOX-TABLE=v4-mismatch(round-ran-on-older-world; box-positions-indicative-only)"`，**10 处 `$WARN` 引用**恰为 v1(4)+v2/v2b(4)+v3(2) 老世界轮；v4+ 轮零引用。
- 像素：34/34 v2 图黄注记框在场（lightyellow 掩码 ≥3000px 全过，无一弱缺）。
- 局限注记：注记框高度 v1→v2 差值因文本整体由中文改写为英文（行高/换行变化）不可作单一归因证据，故以静态+在场性定案。

## 凭据指针
- 3090 `~/sitl_sim/c3_corridor_20261013/`：traj_atlas/（34 png+md5.txt）、atlas_v2_run.log、atlas_v2_certify_out.json（41402bf6）、atlas_v2_certify_err.log、c3_traj_plot.py(ee88bb7)、c3_atlas_batch.sh(4d46571)
- 本地 `t1/2026-10-13_③C避障能力验证/`：traj_atlas/（同 md5）、traj_atlas_v1_backup/（v1 原样）、atlas_v2_verify.py、atlas_v2_certify.py、atlas_v2_*.{log,json}
- 验收判定：**A1 通过**（三修复面全证据链闭合）。
