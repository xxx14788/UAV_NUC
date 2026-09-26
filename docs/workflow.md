# 工作流规范（怎么干活、什么时候算完成）

适用对象：人类成员与 AI agent。协作纪律（凭据/推送/安全）见 [CONTRIBUTING.md](../CONTRIBUTING.md)，本文只讲工作方法。

## 1. 开工流程

1. `git pull --rebase` 拉最新
2. 读 README §3「与上游差异表」——这是本仓库最重要的资产，动手前先知道自己要改的东西是否已有本地差异
3. 小步修改，随时 `catkin_make` 确认可编译

## 2. 验证门槛（Definition of Done）

一个改动"完成"的判定标准，按改动类型取最严的一档：

| 改动类型 | 完成前必须通过 |
|---|---|
| C++ 代码 | `catkin_make` 零 error，不新增 warning（尽量） |
| launch / xml / yaml | `xmllint --noout <file>` 或 roslaunch 能解析；涉及控制链路时加 SITL 冒烟 |
| px4ctrl / VINS 参数（影响控制行为） | SITL 全流程冒烟一次（`sitl_sim/00→04→06` 起降成功），提交消息写明影响 |
| 实机参数 | 同上，且**永远不与代码改动混在同一提交** |
| 文档 | 公开仓库自查：无 IP / 密码 / 密钥 / 内网信息 |

## 3. 上游差异登记制（本项目特有，最重要）

本仓库 = 上游 Fast-Drone-250 + 少量本地差异。**"与上游差异可枚举"是复现工作的根基**：

- 任何对上游已有文件的修改，必须在 README §3 差异表里登记（文件、改动、原因）
- 禁止大规模 reformat / 重命名 / 风格化上游代码——那会让差异表失效
- 校验方法：`diff -rq <上游浅克隆>/src ~/catkin_ws/src -x .git`

## 4. 分支策略

- 日常工作单元：直接在 main 上做（提交→推送，见 CONTRIBUTING §3）
- 预计超过 1 天或改动面大（>200 行 / 跨包）：开 `feat/<名字>` 分支，小步提交，验证门槛全过后合回 main
- 禁止在分支上长期离线开发（分支也要每天 push）

## 5. 实验记录

每次 SITL 或实机飞行后，在 [flight_log.md](flight_log.md) 追加一行（日期、bag 文件、时长、结果、异常）。bag 本体不入库，记录入库。

## 6. 会话交接（agent 与人通用）

一段工作结束时：工作单元已推送 + `git log --oneline -3` 记入交接记录 + 未尽事项写清下一步入口。

## 参考

- [PX4 CONTRIBUTING](https://github.com/PX4/PX4-Autopilot/blob/main/CONTRIBUTING.md)（验证门槛与分支实践的业界参照）
