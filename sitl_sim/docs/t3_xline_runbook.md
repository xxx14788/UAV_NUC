# T3 X 线预演 Runbook(v7.4-R2 彩排修订;2026-10-01;前版 v7.2-Y1.5)

> 目标读者:零上下文新会话执行者。**解锁门(v7.4 总设计师口径,2026-10-01)**:
> ①STATUS 尾部有 T2 **U4 正式通告**(其 U3 六轮在线矩阵 VINS 全部零 failure 零 reboot
> +到位统计与跳变计数如实上报,附统计表)且 ②U2 双签判决表完成(`docs/t3_wa_fullregression.md`
> 双签)。**在线为主判,回放为机理分析不作 gate**(红线 11;原"回放三判据全绿"门废止)。
> X4 打 tag 前置另加:**T1-E2 跳变修复落地**(2.45m 级跳变致 J0 FAIL 的轮,修复前不计入 5/5)。
> 架构红线:纯视觉(VINS 唯一位置源);判读 zb 轴;帧跳变锚差>0.5m 一律 FAIL 定性
> (测法双注明:帧间 |dp| vs 锚差)。

## 0. 解锁门与预检(每批次开工前逐项打钩)

1. STATUS 尾部有 T2 **U4 正式解锁通告**(点名 @T3)。有争议时跑
   `source /opt/ros/noetic/setup.bash && python3 ~/catkin_ws/sitl_sim/analysis/t3_wa_gate.py --online --selftest`
   确认在线判决器双侧绿(WAOL5R/X1_232055 对账);回放模式 `--selftest` 亦应双绿(工具完整性)。
2. U2 双签判决表在档(`docs/t3_wa_fullregression.md`,双签时戳+回放域局限声明随表);
   其结论只入机理账,不阻塞 X 线(红线 11)。
3. 批量占锁 STATUS 宣告(锁章 1:N 轮×~12min+每轮轮号);**顺序发射**:轮 N+1 等轮 N 锁释放+RESULT 落盘。
4. `df` 余量>20G(水位线);`pgrep -a "vins_node|gzserver|px4|mavros|rosbag"` 现场干净;
   读 STATUS 尾 30 行避让 T2 验证窗口/T1 飞窗(让位序:T3-X4>T2 复跑>T1)。
5. 配置代快照:`git -C ~/catkin_ws log --oneline -1` + `md5sum src/VINS-Fusion/config/sim_stereo/*.yaml`
   记入台账(双记账的栈代一致性凭据)。
6. 工具自测四件(t3_wa_gate --online --selftest / t3_wa_gate --selftest(回放) /
   vins_divergence_forensics --selftest / t3_library_forensics selftest)——
   改过任何工具必须重跑过再上岗(总纲 3)。
7. 探针链预检(T1-P0A1 修复后新增,d55c710):起栈前可跑
   `bash vins_smoke.sh --probecheck --tag PC`(~2min,无锁不起飞,自测 REANCHOR_DEBUG 探针链
   E2uls/clamp/gap 在线打印);批量轮前 1 次即可,不必每轮。

## 1. 五轮总表(X2 ①③④ + X3 ②⑤;X1'=①同形)

| # | 命令(~/sitl_sim 下) | 世界 | goal | 两段 | 预期时长 |
|---|---|---|---|---|---|
| ① | `bash vins_smoke.sh --tag X1final` | sitl_world_obstacles | 7 -4 1 | 否 | ~12min |
| ③ | `bash vins_smoke.sh --tag X2g3 --goal 8 -1 1` | sitl_world_obstacles | 8 -1 1 | 否 | ~12min |
| ④ | `bash vins_smoke.sh --tag X2g4 --world sitl_world_obstacles_v2 --goal 8 -1 1` | sitl_world_obstacles_v2 | 8 -1 1 | 否 | ~12min |
| ② | `bash vins_smoke.sh --tag X3l2 --goal 7 -4 1 --leg2 1 0 1` | sitl_world_obstacles | 7 -4 1→1 0 1 | 是 | ~15-18min |
| ⑤ | `bash vins_smoke.sh --tag X3l5 --goal 7 -4 1 --leg2 0 0 1` | sitl_world_obstacles | 7 -4 1→0 0 1 | 是 | ~15-18min |

- X1' 验收轮=①同形:四指标全绿**且帧跳变判据过**(§3 J0)。连败 2 轮即回挖,不放宽(任务书 X 线)。
- **全带图纪律(v7.4,反转 v7.2 旧口径)**:全部轮 `VINS_SMOKE_IMAGES=1`(素材供 T4,一轮两用);
  每轮起飞前 `df>15G` 门;**录后先通告 T4 提帧,判读确认后再清理**;袋 5-9G/轮量级。
- **袋保全强制**(历史 11 组清盘教训):清盘前评估重扫价值;清列 STATUS 报备。
- ENV-FAIL 用三签名口径(§4);整机死亡系人为原因不立案(v7.4 U3 机器前置注记)。
- 每轮结束脚本自动产 RESULT.txt(四指标)/ARRIVE_WATCH(双口径)/flight.bag(带图)。

## 2. 每轮采集矩阵(判读输入,逐项落盘)

| 采集项 | 来源 | 判读用途 |
|---|---|---|
| **一行全判决(新)** | `python3 analysis/t3_wa_gate.py --online <run_dir>`(自动:四指标+J0 锚差+J0 修订+ENV 硬证据+零failure/reboot+Bas+ATE对齐+forensics 摘要→`<run_dir>/wa_gate_online.json`) | **主判入口**;批用 `--online --csv xline_wa_gate.csv <run_dir>...` |
| 四指标 | RESULT.txt(脚本自动;wa_gate 直读不重算) | 主判 |
| 双口径到位 | ARRIVE_WATCH1/2 行:min_truth(GT)与 min_vins(EKF2/VINS 自报) | 到位判决 GT 口径<0.5m;EKF2 口径登记 |
| 双口径 p95 | RESULT 行 `跟踪 p95=… m (cmd-odom, 信息项)` | 跟踪质量(信息项不作门) |
| 帧跳变(在线域 raw 有效) | forensics_v2 `frame_jumps_raw_odom`/`frame_jumps_smoothed_odom`(wa_gate --online 自动取/生成) | J0 判据 |
| 形态/t*/分叉/污染 | 同上 forensics_v2.txt 判决行 | 失败归因 |
| Bas/Bgs/tic/track | wa_gate_online.json `vins.bas`(peak/tail/over/run/track_med);或 t3_library_forensics DB 行 | W-A 修复有效性旁证 |
| --leg2 锚差漂移(②⑤) | forensics_v2 `end_state.final_drift_prop_truth_m`(末段 3s 均值锚差) | 两段式不重启 ATE 的替代判据,门<0.5m |
| 特征数 | wa_gate_online.json `vins.bas.track_med`(T2diag 中位) | 观测层健康 |
| legs 入账 | Y3 框架(leg_database.py)逐轮行 + t3_experiments.md 表格 | X4 5/5 自动判定 |

## 3. 判据表(全过=绿轮;任何一项不过=FAIL 该轮)

| 代号 | 判据 | 门 |
|---|---|---|
| A1 | leg1 到位(真值) min_truth | <0.5m(T2-W3 曾建议 0.75m 协商门——**未获用户裁定前按 0.5 原口径**) |
| A2(②⑤) | leg2 到位(真值)+ 锚差漂移 | min_truth<0.5m 且 final_drift<0.5m |
| B | 避障 min_dist | >0.349m(harness 既有口径) |
| C | poscmd 频率 | ≥50Hz |
| D | auto_disarm | =1(到位后自动降落解散) |
| J0 | 帧跳变 | forensics_v2 `frame_jumps_raw_odom`=0 且 `frame_jumps_smoothed_odom`≤10(**Y1.4 好轮校准**:ground 0/hover 1/route-PASS 7,坏轮 422-686,取 10=好轮 1.4× 上界;**锚差>0.5m 一律 FAIL 定性,不做锚点技巧**(红线 2)兜底) |
| P0 | 污染嫌疑 | forensics_v2 poisoning_suspect 为空(imu_hdr/clock 回退>1000 即判废) |

信息项(登记不判):p95、EKF2 口径到位、track_med、Bas/Bgs 尾段、悬停窗 |v| 峰。

## 4. ENV-FAIL 决策树(环境性≠失败轮;判据=三类签名,T4-E4 口径)

```
轮中异常
├─ /gazebo/model_states 停流(gazebo 死/真值流断)
│   → ENV-FAIL(签名:truth 帧数骤停+gzserver 退出)→ 环境性重试(不计预算)
├─ poscmd 归零(planner 死;C 项 0Hz)
│   → 若 VINS 流仍健康 → ENV-FAIL(planner 域)→ 重试;复现则移交 T3 规划面回挖
├─ SITL/px4/mavros 死(armed 丢/D 流断)
│   → ENV-FAIL(签名:mavros connected=False/px4 退出)→ 重试
└─ 三类签名均无(VINS 爆/漂/跳)
    → 真失败轮,入 §5 回挖;环境流健康 273s+ 型证据可拒"环境性"定性
```

- 每轮 ENV-FAIL 允许 1 次环境性重试(任务书 X4 节);重试轮绿→计入;ENV-FAIL 本身**不断"连续"计数**。
- ENV-FAIL 判定必须在台账写明签名证据行(topic 停流时刻/进程退出码),禁拍脑袋。

## 5. 常见失败分支回挖预案(每种失败→查什么→判给谁)

| 失败面容 | 查什么 | 判给谁 |
|---|---|---|
| J0 爆/跳 + T2diag Bas 同刻爆(173345 型) | forensics_v2 + T2diag tic/Bas + t3_wa_gate --online 复判;带图轮(v7.4 全带图,df>15G) | **W-A 漏网→登记+通告 T2,X 线暂停**(Y4 纪律) |
| J0 跳但 vins 域健康(WAOL5R 型 2.45m 级) | wa_gate_online.json `xline.t1d1_domain=true`(自动标注) | **T1-D1 跳变域**:按 J0 判 FAIL+标域,不计 5/5,入回挖清单(任务书 X4 条款);T1-E2 修复落地前该型轮不计 |
| A1/A2 miss 但 J0 净+Bas 尾稳 | forensics_v2 final_drift + 慢漂斜率(0.468m/3min 架构属性对照) | 架构慢漂→登记;0.75m 门协商呈用户裁定;非 VINS 病 |
| B 不过(GT 擦障碍) | planner.log 轨迹 vs 真值最近距;VINS 漂移致 GT 偏航→归 VINS;规划轨迹本身贴障→T3 规划域回挖(ego_planner 参数) | T3 自身或 VINS |
| C 0Hz/低频 | poscmd_hz.txt+planner.log 尾部;TCPROS 建连失败(G1 域)→ENV 树;goal 竞态(已重发两轮)复核 goal.txt | ENV 或 T1-G1 |
| D 不 disarm | px4ctrl.log+takeoff_land 流;FSM 状态机 | T1 px4ctrl 面 |
| 双流污染(P0) | forensics_v2 hdr/clock 回退计数;查同时段谁的 rosbag play 挂默认 master | 污染判废+通告肇事线;重试 |
| EKF2-EV 失稳(W2 型:GT 本身疯狂/机体振荡) | ulog EV innovations+真值速度谱;对照 T1-E1 域 | **T1 域**(EKF2-EV@223Hz),X 轮记 ENV-域分离 |

回挖纪律(v7.2.1):回挖=带新证据/新假设的针对性轮,禁无改动重掷;连续 2 轮同因失败停跑转分析(总纲 6③)。

## 6. X4 五连飞与 tag sitl-v0.4

- 序列:①②③④⑤(§1 表);**双记账**:X2/X3 阶段已全绿且栈代一致(§0.5 快照相同)的轮直接计入
  五连飞,不重飞;判据不降(该轮判据表逐项过才算)。
- **连续 5 绿即 X4 达成**:判决表中 5 轮全绿且其间无 FAIL(ENV-FAIL 不计不断);
  5/5 判定用 Y3 框架脚本自动出,不手工数。
- 未达 5/5 → §5 回挖重飞(带新证据/新假设,禁无改动重掷);轮次不设抱怨上限,只受磁盘/环境物理约束。
- tag 前检查单(全打钩才打):
  1. 5/5 台账行齐(legs 框架+实验台账),每轮 forensics_v2/wa_gate_online.json 附件在档;
  2. **查 T2 STATUS 尾**(锁章 5:打 tag 前确认 T2 无未决异议);
  3. **T1-E2 跳变修复落地凭据在档**(v7.4 新增前置:提交链+在线验证轮;2.45m 级跳变
     致 J0 FAIL 的轮修复前不计入 5/5);
  4. git 干净+远端一致;X6 收口件齐(README §3 并账:外参 z/est0/图像开关/odom_gate
     enabled/j0 口径/gyr_w 六项;rviz 截图;legs 重扫表;vision_inputs);
  5. STATUS 宣告 `| T3 | v7 收口 | 完成 |` 后 `git tag sitl-v0.4 && git push --tags`。
- X7 验收全数据包:**骨架已预搭**(`docs/t3_xline_acceptance_report.md` SKELETON v0,
  62a9651;数字槽 [DATA:*] 零预填)——tag 后按槽回填+图再生(`analysis/t3_xline_report_figs.py`)。

## 7. 已知坑位(vins_smoke.sh 头注+X 线实战,全部实证)

- 空 world 无特征 init 必败——world 参数别手滑;
- `rostopic echo` 输出 frame_id 带引号,grep 须兼容 `"?world"?`;
- 串口 511 默认 50Hz:提频 mavcmd long 511 105 4000(223Hz 实测见 IMU 频率网格锁);
- ROSTimeMovedBackwards 杀 watcher——轮中禁起任何带 --clock 的回放(双流红线);
- goal 竞态:脚本已两轮重发;判读以 goal.txt+planner.log 双源;
- 降落投递随机:到位判据用 min(窗口最小距),不用末值;
- 磁盘 100% 会杀全场:录前 df 门;
- vins "terminate without active exception" Aborted=收尾析构非中途崩(判崩溃先看 diag 尾帧是否到袋尾);
- 重放/回灌一律私有 master(ROS_MASTER_URI=11312/11313),泄漏进默认 master=双流污染(043355 判废教训);
- pkill 禁名字级,只 kill 自记 PID;在飞 bash 脚本禁编辑(锁测试侧锁铁律)。

## 8. 台账与推送节奏

每轮即登记即推(t3_experiments.md 表格行:轮号/tag/四指标/双口径/J0/P0/判决/证据路径;
X 线轮加 `wa_gate --online` 一行判决+`--csv` 汇总行),每工作单元一 commit;X4 达成与
tag 各一 commit。STATUS 批次通告与轮间 RESULT 落盘后再发下一轮(顺序发射纪律)。
**袋保全**:带图轮录后先 T4 后清理;清盘前重扫价值评估+STATUS 报备(11 组历史清盘教训)。

## 9. 判读链版本凭据表（§9.1;每版本=三层验证全绿证据;opcard §8.1 步 4 版本核对正源）

| 版本 | md5 | 日期 | 变更摘要 | 三层验证 |
|---|---|---|---|---|
| v1.1 | ac1df603 | 10-03 | 受控失败分层五态+S8 正则修复(RE_RES_ARRIVE 双兼容) | selftest+SYN×5 |
| v1.2 | 4cb6acc7 | 10-03 | 毒窗锚 min(onset,fire)-1;L1b 10s;R5 首真受控正样本 | 在线三格+SYN+舰队 10 臂 |
| **v1.3** | **6fb9ccb4** | 10-04 | L1 任一门拦截(用户 10-03 12:09 裁定②)+§2.6-h 误触发排除三面签名;SYN 电池扩至 8 夹具 | 离线绿+在线 4 格绿+18 样本 re-regression 判值面零漂移+SYN 5 断言全绿;035509→controlled(唯一翻转,与任务书预期精确命中) |

- 判读器任何改动走红线 24 全流程:双备份(.bak_<ver>_<date>+/tmp 副本)+补丁唯一命中
  断言+md5 入本表+三层验证;备份清理条件=X1' 轮后(.bak 凭据族统一处置)。
- 合成电池正源=`analysis/t3_synth_controlled_test.py`(5 断言:SYN_CTRL/SYN_LATE/
  SYN_LEG/SYN_FALSE/SYN_LEG_A1)+`x11_dryrun_v11/SYN_MULTI/SYN_NOBAG/SYN_NOTC`(边界×3)。
- 受控层期望态速查(判读链对抗样本扩充池的种子集):cost 真触发→controlled;
  legacy 真触发双面证据→controlled;迟触发(L1b)→TNR;零证据触发→误触发处置
  uncontrolled-fail;真触发+流死→TNR(A1 型);log 缺失→log-missing 降级。
