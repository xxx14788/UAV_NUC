# 坑账：③C 甲合流册新增（2026-10-16；月报并入待办）

> 承前：甲册 16-21（C2B 判决书）+终局册 13 条+丙册域。本册新增 N1-N8。

| # | 坑 | 证据 | 处置 |
|---|---|---|---|
| N1 | **c6_stratified_stats.py geom 文件名双 run_ 前缀 bug**（构造 geom_run_run_*.json → 永远找不到 → S 计数误报 0/25） | /tmp/v70_layer_stats.txt 全行 path_len=None；NE2 JSON 四门实过 | 已修：c3a_layer_stats.py 重建三层判读（正确 5/25）；旧工具弃用注记 |
| N2 | **flight.bag 无 depth/无双目话题**（录制器录 odom/truth/goal/cmd 族） | run_C3F73NE2 flight.bag 话题清单实测 | 丙册"只录 depth"口径勘误；实飞录制清单已按 §八.4 强制双目 |
| N3 | Windows md5sum 二进制模式 `*` 前缀+双空格格式 → shell diff 误报 MD5-DIFF | atlas 对账首报 DIFF，python 集合比对 30/30 一致 | 对账用 python hash 集合比对（shell diff 禁用于跨端 md5 清单） |
| N4 | ssh 复合命令内 `&` 后台化丢输出/丢进程（引号嵌套） | /tmp/v9_dry_sitl.log 首轮不存在 | 远端脚本文件落盘+setsid nohup 正解 |
| N5 | **depth 传感器渲染全 NaN 机器级回退**（RGB 同传感器均匀黑；type=camera 正常 type=depth 全 NaN；世界/部署物/显示器/位姿/包/资源/OGRE/缓存 11 项排除） | depth_regression_forensics.md 全链 | 卡点在案：等用户域重启复测；复测法在法证文件 |
| N6 | gz model `-p` 是**输出** pose 非设置；设置须分项 `-x/-y/-z/-R/-P/-Y` | gz model --help + 实测 | 干测转 heading 用分项旗标 |
| N7 | 自建 dry harness roscore 竞态：`pgrep -x roscore` 匹配不到 rosmaster → 栈起在无 master 上自杀 | v9_dry 首两轮 "No ROS master" 死 | 栈操作一律走权威入口 vins_smoke.sh / start_sitl_vins.sh（其 roscore 管理已处理） |
| N8 | Xvfb 必须 `-screen 0 1280x1024x24`（vins_smoke 配方）——裸 Xvfb 无 24 位深缓冲 | vins_smoke.sh:115 对照 | 正字在册（非本次卡点根因，但配置纪律） |

## 交接注记

- 判读器扩展（corridor_geom_audit v9 表+LAB+推导门）旧版本回归 BIT-IDENTICAL（v7 老袋逐位复核）——扩支持面纪律可复验。
- 生成器确定性：gen_corridor_world_v9.py 同参数重跑 md5 逐位一致（5f3d48eb）。
- 箱表口径坑（承 C66 延伸）：cling_pairing_bybox 的 BOXES_V7 是 **odom 系**（与 audit 的 gazebo 系表差 (1.01,0.98)）——复用时先核坐标系。
