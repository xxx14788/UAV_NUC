# 坑账：③C 甲合流册新增（2026-10-16 初版；2026-10-17 v5.2 会话扩写 N9-N17+N5 勘误）

> 承前：甲册 16-21（C2B 判决书）+终局册 13 条+丙册域。本册新增 N1-N8（v4.2 会话）+N9-N17（v5.2 会话）。

| # | 坑 | 证据 | 处置 |
|---|---|---|---|
| N1 | **c6_stratified_stats.py geom 文件名双 run_ 前缀 bug**（构造 geom_run_run_*.json → 永远找不到 → S 计数误报 0/25） | /tmp/v70_layer_stats.txt 全行 path_len=None；NE2 JSON 四门实过 | 已修：c3a_layer_stats.py 重建三层判读（正确 5/25）；旧工具弃用注记 |
| N2 | **flight.bag 无 depth/无双目话题**（录制器录 odom/truth/goal/cmd 族） | run_C3F73NE2 flight.bag 话题清单实测 | 丙册"只录 depth"口径勘误；实飞录制清单已按 §八.4 强制双目 |
| N3 | Windows md5sum 二进制模式 `*` 前缀+双空格格式 → shell diff 误报 MD5-DIFF | atlas 对账首报 DIFF，python 集合比对 30/30 一致 | 对账用 python hash 集合比对（shell diff 禁用于跨端 md5 清单） |
| N4 | ssh 复合命令内 `&` 后台化丢输出/丢进程（引号嵌套） | /tmp/v9_dry_sitl.log 首轮不存在 | 远端脚本文件落盘+setsid nohup 正解 |
| N5 | ~~depth 传感器渲染全 NaN 机器级回退（…type=camera 正常…）~~ **勘误（10-17 v5.2）**：type=camera 同病——"camera 正常"为短窗采样伪影（见 N10）；真机制=传感器渲染创建后 ~1s 确定性死亡（N5 主体"全 NaN 回退"成立，机理注记全面升级） | depth_分歧点诊断报告_v2.md §一/§二 | 机制定案+根因未定案+止损呈报在案（depth_v52/） |
| N6 | gz model `-p` 是**输出** pose 非设置；设置须分项 `-x/-y/-z/-R/-P/-Y` | gz model --help + 实测 | 干测转 heading 用分项旗标 |
| N7 | 自建 dry harness roscore 竞态：`pgrep -x roscore` 匹配不到 rosmaster → 栈起在无 master 上自杀 | v9_dry 首两轮 "No ROS master" 死 | 栈操作一律走权威入口 vins_smoke.sh / start_sitl_vins.sh（其 roscore 管理已处理） |
| N8 | Xvfb 必须 `-screen 0 1280x1024x24`（vins_smoke 配方）——裸 Xvfb 无 24 位深缓冲 | vins_smoke.sh:115 对照 | 正字在册（非本次卡点根因，但配置纪律） |
| N9 | **round_result.sh 避障 min_dist 判读双错配**（箱表=odom 系锚移位+v6 版本冻结 vs truth=gazebo 原帧直比；v1.5c 注释自称 GAZEBO frame 实现反向）——corridor 时代全 RESULT 避障行/TRICHOTOMY true_fail 参与量污染；0.000=轨迹穿幻影箱区（悬停漂移轮 t+148s 入 cN1+导航轮空地穿越均实证） | P02_判读双口径立案.md（代码级+argmin 实证） | min_dist 全量禁引；min_surf 唯一正源；修复属判读器域（乙册/维护者裁定，红线禁本册改） |
| N10 | **短窗判活伪影**：探针采"前 5 帧"判 RECOVERED——恰落在传感器死亡前活帧窗（10Hz 传感器第 1-9 帧活）→ 假阳性"自愈/环境差异/机器差异"三连误判 | 本册三次结论翻转记录（报告 v2 §四） | **纪律：判活一律 60s 逐帧长探（min2_longprobe.py 标准件）+报死帧占比；禁短窗判定** |
| N11 | **残留 gzserver 占 gazebo master 11345**：后续 run 报 "Address already in use" 降级运行 → 判读串扰（假阴假阳均出现过） | T7 系日志 addr-conflict 行+pgrep 实锤 PID 93584 | 起跑前 `pgrep -x gzserver` 残留断言+跑后确认死；批脚本已有同款门（ABORT_RESIDUE） |
| N12 | apt 中文 locale：`grep 'Candidate'` 匹配不到"候选:"行 | apt-cache policy 输出实证 | 脚本读 apt 状态加 `LANG=C` 或按 locale 兼容匹配 |
| N13 | `set -u` 撞 ROS setup 链（ROS_DISTRO 未绑定）——在案旧坑本册再踩 | min2_strace_run.sh 首跑死 | ROS 环境先 source 后 set -u，或不 set -u |
| N14 | Windows python 写远端 shell 脚本 CRLF 行尾 → bash 语法错（`do\r`） | min2_usim.sh 首传 | `io.open(...,newline='\n')` 写 LF；或远端 dos2unix |
| N15 | 无 DISPLAY 时 DepthCameraSensor 创建**硬失败=无话题**（与"有帧但空渲染"是两种签名）——诊断分型用 | 01:12 首跑 gz 日志 | 签名分型入报告：无话题查 DISPLAY；有死帧查渲染死亡 |
| N16 | strace/最小环境复刻生产栈必须带 `LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/gazebo-11/plugins`——否则 openni 插件链断（libDepthCameraPlugin.so 找不到）=NO-FRAMES 假签名 | 本册两次踩（3090+NUC 同款） | 最小 env 模板带插件路径段（bisect_cell.sh 正字） |
| N17 | **depth 事件全链+重装事件注记**（10-16 08:07-11:12 起病窗→10-17 v5.2 机制定案）：渲染 ~1s 死亡跨静态/动态 depth+静态全类型+两机同病；立体动态 camera 独活；重装八包+缓存清+GPU 切换+环境矩阵全阴性；止损=两轮深诊断尽→用户三径裁定挂起 | depth_v52/ 全证据链+报告 v2 | 呈报在案（STATUS 04:35 行）；复发监视=min2 长探标准件 |

## 交接注记

- 判读器扩展（corridor_geom_audit v9 表+LAB+推导门）旧版本回归 BIT-IDENTICAL（v7 老袋逐位复核）——扩支持面纪律可复验。
- 生成器确定性：gen_corridor_world_v9.py 同参数重跑 md5 逐位一致（5f3d48eb）。
- 箱表口径坑（承 C66 延伸，N9 同族正字）：cling_pairing_bybox 的 BOXES_V7 是 **odom 系**（与 audit 的 gazebo 系表差 (1.01,0.98)）——复用时先核坐标系。
- 月报正本并入：N1-N17 及 depth 全链事件待月报正本定位后按模板 v1.1 并入（本会话三机检索未定位正本文件——v4.2 曾以"月报 131 条@3090 ~/sitl_sim/"口径引用但现无独立文件，疑并入项目进度与未来方向.md 或待 NUC 域核）。
