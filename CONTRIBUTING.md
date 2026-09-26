# 协作与推送纪律（人类成员与 AI agent 通用）

本仓库是多机多人协作（NUC 机载电脑、成员电脑、AI agent 会话都可能直接改代码）。
所有提交者——**包括 agent**——动手前必须读完本文件并遵守。目的：安全、可追溯、远端永远不落后于实际工作。

## 1. 凭据与安全（红线）

- 每台机器/每个 agent 使用**自己的 deploy key 或 PAT**；禁止共享账号密码，禁止把 token 写进文件、命令行历史或聊天记录。
- 本仓库为**公开仓库**：禁止提交 IP 地址、密码、序列号、密钥、内网拓扑等敏感信息。提交前自查一遍 diff。
- NUC 的推送凭据（SSH 推送密钥）只保存在 NUC 上，不复制到其他机器。
- 真机飞行参数（px4ctrl config、VINS 标定）的改动必须单独成提交，提交消息写清影响范围。

## 2. 提交纪律

- 动手前 `git status` 必须干净。若有他人未提交的改动：停下确认，不顺手打包别人的工作。
- 一个提交只做一件事；消息用 conventional 风格（`feat:` / `fix:` / `docs:` / `chore:`），首行 ≤72 字符，正文说清 why。
- **禁止 force-push；禁止修改已推送的提交**（不 rebase 已推送历史）。推不上去 → `git pull --rebase` 解决冲突后再推。
- 构建产物与大数据永不入库：`.gitignore` 已排除 `build/ devel/ *.bag bags/ logs/`。新增 >1MB 的文件先三思。

## 3. 同步纪律（及时更新）

- **开始工作时**：`git fetch && git pull --rebase`，基于最新 main 干活。
- **完成一个工作单元就推送**：每完成一个提交（一个功能/修复/文档单元）立即 `git push`，禁止积压多个提交攒一次推。
- **结束会话时**：不允许存在未提交/未推送的改动。
- 长时间工作中每 1 小时至少 `git fetch` 一次，避免与他人冲突积累。
- push 后用 `git ls-remote UAV_NUC refs/heads/main`（或 GitHub API）确认远端 SHA 与本地一致，才算完成。

## 4. 实机与仿真边界（安全底线）

- 不改 NUC 上 `~/catkin_ws` 之外的系统配置（udev、串口、MAVROS 设备绑定）——除非单独提交并记录原因。
- SITL 与真机入口永远分离：真机 `run_ctrl.launch`（VINS 里程计），SITL `run_ctrl_sitl.launch`（EKF2 里程计）。
- 涉及解锁/上电的实机操作，任何人（和任何 agent）不得远程擅自触发。

## 5. AI agent 附加纪律

- 会话开始先读本文件与 README，再看 `git log --oneline -10` 了解近期改动。
- 不得自行创建/修改 GitHub 凭据、协作者、分支保护等仓库设置；需要时提请仓库 owner 操作。
- 会话结束时在交接记录（memory/handoff）里写明当前仓库 HEAD SHA 与未推送内容。

## 6. 快速参考（NUC 上的日常命令）

```bash
cd ~/catkin_ws
git status                        # 开工前确认干净
git pull --rebase                 # 拉最新
# ... 编码 / catkin_make / 测试 ...
git add <files> && git commit -m "fix: ..."
git push UAV_NUC main             # NUC 已配推送密钥，可直接推
git ls-remote UAV_NUC refs/heads/main   # 确认远端已同步
```
