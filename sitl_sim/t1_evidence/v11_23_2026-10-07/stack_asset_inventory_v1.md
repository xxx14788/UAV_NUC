# 栈资产清点 v1（T1 v11.23 阶段 4f；2026-10-07 13:4x；纯清点——明日实机迁移规划输入）

## 1. VINS 栈（3090 ~/catkin_ws/devel）
| 件 | md5 | 状态注记 |
|---|---|---|
| vins_node | 721cad40 | =X4 批栈/X7 在册值（零变动复核 10-07 11:41+本窗） |
| libvins_lib.so（.private/vins/lib） | 5bacc2e9 | 同上（栈双 md5 对） |

## 2. sim_stereo config 双态（关键：工作树≠git HEAD）
| 态 | md5 | 内容 |
|---|---|---|
| **工作树 arm 态（现行）** | 054ddc8d | canonical 全部 + T2 臂键追加：t2_cost_gate:1 / t2_depth_gate:0（证伪禁用） / t2_staged_depth_gate:1+n80（案A） / t2_vision_loss:0+t2_cauchy_delta:4.0（cauchy4） / t2_stream_guard:1+sane 50/15（streamguard v4）——=「v2+cauchy4+guard」臂 |
| **canonical（git HEAD）** | 5c98dc0d | 基态（至 gyr_w:0.0001 止，无 T2 臂键）——git 未提交臂态（工作树 M 在案） |
| 迁移提示 | — | 实机 d435 config=sim_stereo 外另一份（待明日规划）；臂键语义谱系=T2 在册（staged/cauchy/guard 三族各有判读史） |

## 3. 控制面
| 件 | md5 |
|---|---|
| px4ctrl_node | a653e982 |
| PX4 参数 | 逐轮快照在批轮目录（px4_params_*.txt，样本 879 参数行）；CAL_* 开机易变族谱系=v11.21 L1 在册 |

## 4. 工具链 md5 谱系（sitl_sim 树,2026-10-07 13:4x 实读）
| 工具 | md5 | 谱系注 |
|---|---|---|
| vins_smoke.sh | dafa65c2 | 本窗+止损挂点/rtf 常态化版（前代 9f647af1=9/10-07 早态） |
| round_result.sh | 7e907b7d | v1.4（换代确认值） |
| t1_gate_watch.py | 70c8ea98 | 三模式 pregate/inflight/replay |
| t1_stoploss_watch.py | be3e0225 | v1.0 本窗落码 |
| t1_rtf_probe.py | e257bd11 | 已常态化（4c） |
| analysis/t3_wa_gate.py | bee17577 | 判读器（冻结，nan+SYN 代） |
| analysis/t3_trichotomy.py | de47b1a0 | 三列分账权威 |
| analysis/t3_replay.sh | c0fbd8c0 | 回放配方（set -u 需调用侧预置 ROS_DISTRO/MASTER_URI——本窗坑注记） |
| analysis/t3_j0d_stats_v2.py | 5a728959 | 本窗扩切口版（185 袋轮） |
| analysis/t3_endorse_rerun.sh | 5c1a0145 | 末列缺陷修复版（本窗） |
| t1_gate_params.json | d4f6ea44 | 门参数（PLACEHOLDER→P2 填参谱系在册） |

## 5. git 锚（catkin_ws @UAV_NUC）
- HEAD 链（本夜）:247dc7f(X7 终稿)→5cd4bd0(止损 4a/4c)→e6e5544(4b/4d/4e+R10)；tag sitl-v0.4→dd8dfda（远端 ref 实查）
- 唯一未提交工作树差异=VINS config 臂态 M（=§2 双态设计；实机迁移时按需择态）
