# PX4 取证补丁入库+继任基线声明（T4 v5.37 单元 6a；2026-10-11 夜；用户裁定落地）

> 用户裁定（10-11 晚，v5.37 背景行）：**PX4 取证补丁提交入库，新指纹 0bac7286 为继任基线**。本件=执行凭据。

## 基线换代链

| 态 | 指纹/git | 声明 |
|---|---|---|
| 原干净基线 | px4_git_head=**d6f12ad1c4**（分离 checkout） | **归档声明**：取证补丁入库前基线；判决书链所记 git head 即此值 |
| 取证构建 F1（=继任基线） | 二进制 md5 **0bac7286cf38075f8880880b1eb9c9d2** = d6f12ad1c4+未提交补丁态 | **继任基线声明（用户裁定）**：C-1 取证轮全程在役态；副本保全=px4_forensic_bin_F1/px4（md5 复测 0bac7286 ✓）；判决书回链=c1_separation_final_verdict.md（f7c87ae5）§指纹+run_C1se/run_C1re build_fingerprint.txt×2（px4_bin_md5 全串同值） |
| 入库提交 | PX4 树 commit **2d8cb26c45**（分支 sitl-c1fr-baseline，父=d6f12ad1c4） | Commander.cpp 8 打点取证补丁（33 增行全 PX4_INFO 宏续行=实参 cast+hrt 时戳，零控制流零状态变更——纯度 diff 筛查实锚）；commit message 注明"取证打印零功能改动+用户裁定入库"；原 d6f12ad1c4 归档声明见上 |
| 重编译复验 | touch Commander.cpp+make px4_sitl_default → **rc=0 绿态（14/14）**；新二进制 md5=c5afa5a7（首 8） | 绿态 ✓；c5afa5a7≠0bac7286=预期（新 git head 2d8cb26c45 嵌入 version 段换代，非内容差）；功能面复核=新二进制 strings C1FR 命中 11 处 ✓；**指纹复核一致判据=F1 态三源对齐**（在役时点二进制=0bac7286 全串 ✓+指纹件同值 ✓+副本同值 ✓），库后构建态（c5afa5a7）为信息性记录不承载基线声明 |

## 资产清单

- px4_forensic_bin_F1/{px4(0bac7286), c1fr_commander_patch.diff(101 行)}（~/sitl_sim/t4_evidence/，双树镜像）
- patch_md5=4af367c9838e584dbf8d8f8b734347d3+commander_patched_md5=660ff8dc49692fa3269d1a02286a4365（指纹件原值沿用零改动）
- 本地机架/CMake 本地面（1090/1091 airframe 等）=非本补丁范围，维持原态不入库

## 边界注记

- PX4 树 origin=上游 github.com/PX4/PX4-Autopilot，无推送权——**入库=3090 本地树 commit+分支锚定**；diff 镜像入工程仓 t4_evidence 随本册 push 获远端存档位。
- 重编译覆盖 build/ 内在役二进制（c5afa5a7）——F1 态以副本+md5 链保全，取证轮已毕（判决书 f7c87ae5 在册）零观测面影响。
