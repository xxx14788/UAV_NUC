# 里程碑登记（2026-11-13 补记）

> 用户 2026-11-13 指出：第一次悬停成功不在 11-11；项目立项就定了“每步改动 git、成功点必须记住”。
> 本文件补记历史里程碑；tag 见每节；证据 bag 在 NUC `~/flight_data/`（大文件不入 git）。

## 2026-11-04 22:10 首次离地到 0.7 m（悬停脚本 `realflight_round.sh`）
- bag `20261104_221027`；VINS z max **0.71**（p50 0.06，短时；首次起飞/悬停尝试，不算稳定悬停）
- 当时 px4ctrl/VINS 未在本仓跟踪；`7e51877`（11-05 12:39）才把 VINS 实机配置入库

## 2026-11-05 22:27 首次自动悬停成功（悬停脚本）
- bag `20261105_222712`；VINS z max **0.81**（p50 0.45，含起降）
- px4ctrl `f982214`（11-05 12:39“悬停定点定高”）；VINS 配置 `7e51877`；bag 前最后提交 **`fe0ef7e`**（18:25）
- tag **`first-auto-hover-20261105` → `fe0ef7e`**

## 2026-11-06 22:28 首次稳定悬停（z p50 0.68）
- bag `20261106_222806`；bag 前最后提交 **`554b838`**（21:38）
- 之后 `1bac6d6`（23:14）把 z 速度环 4.0/2.0 改为 6.0/3.0（治起飞摆幅）；当前沿用 6.0/3.0
- tag **`first-stable-hover-20261106` → `554b838`**

## 2026-11-11 21:28 首次 VINS+EGO 联合（目标 + 悬停）
- bag `20261111_212822`；CMD_CTRL（首个 EGO 目标）；bag 前最后提交 **`fb8cc69`**（21:10）；其后 `494d7e3`（21:40）
- tag **`first-vins-ego-20261111` → `fb8cc69`**
- 既有 tag `first-vins-ego-flight-20261112`（`963f7d5`，11-11 22:52）是之后的归档点，不是 21:28 现场

## 2026-11-13 planner v3（preflight，未实飞验证）
- commits `45bf730`（实测起点进轨迹/A*/P5/门禁/z差分）、`e47918d`（爬行保留+step-2 保护）、`b122962`（near_goal 距离剖面 + z 差分下沉限定）
- tag **`planner-v3-preflight-20261113` → `b122962`**

## git 纪律（补记）
- 每步改动 commit；成功点 annotate tag；live 工具/配置同步到 `deploy/`（`home/`、`config/`、`sitl_root/`、`config_history/`）；`deploy/verify.sh` 逐文件 sha256。
- 本地工作区 `D:\drone_VINS` 2026-11-13 起也已 git（`.gitignore` 排除 upstream/repos/archive/tmp/shots/大文件）。
