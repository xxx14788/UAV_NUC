# ros2-upgrade 分支章程（BRANCH_CHARTER）

> 本文件 = 本分支的铁律正源，摘自《ROS2 升级战役探索册 v3》§1（2026-10-19，任务书正源
> `D:\drone_VINS\plans\执行中\2026-10-19_ROS2升级探索册_v3.md`）。
> 任何在本分支上工作的人（含 agent）接手前必读；违反任一条 = 停手上报。

## 四铁律（违反任一=停手上报）

1. **全方位升级非兼容迁移**：上位替代为默认答案；选型过证据矩阵；最终选型呈用户裁。
2. **隔离**：主项目（ROS1）资料与运行零干扰；**NUC 禁区**；新增面只进 `t1/2026-10-19_ROS2升级预研/` 与 3090 独立路径。
3. **主仓库分支制**：主仓库=UAV_NUC 正源（origin=`github.com/xxx14788/UAV_NUC`，已核实 HEAD=eee7aae；Lihuaaaa-F 密钥在 3090，对主仓库有写权限）；`ros2-upgrade` 分支=全新 clone（`~/ros2_upgrade/repo`），**绝不 checkout 到 `~/catkin_ws`**；**全程不许合并、不发 PR、不动 main**。
4. **运行态锁定**：主项目正式运行留 ROS1；"换环境"=用户明示口令。［默认］隔离容器内验证实验属"做好准备"。

## 勘误登记（施工时实测，2026-10-19）

- 任务书 §2 URL2 `git@github.com:Lihuaaaa-F/UAV_NUC.git` → **该 fork 不存在**（`Repository not found`）。
  实际推送路径=SSH 别名 `git@github.com-uavnuc:xxx14788/UAV_NUC.git`（~/.ssh/config，密钥 id_ed25519_gh_uav=Lihuaaaa-F，对 xxx14788/UAV_NUC 有写权限——实证=3090 ~/catkin_ws 历史推送全部经此 remote 成功）。
- clone 用 https URL1（匿名读通）；push 走 pushurl 覆盖为上述 SSH 别名。

## 建立记录

- 建分支日：2026-10-19；基=main HEAD `eee7aae`（③C v9.0 战役闭合提交）。
- 施工核查表：Win 侧 `t1/2026-10-19_ROS2升级预研/T0施工核查表_v1.md`。
