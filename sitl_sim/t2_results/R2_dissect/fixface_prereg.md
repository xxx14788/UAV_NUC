# R2F 判别格预注册正式化(2026-10-02 02:0x;升格自 fixface_design.md;先于任何格回放写定)

## 开关与参数(已实现,默认关=逐位不变)
- t2_min_disparity(px,默认0=关;stereo=|Δu_L−u_R|×FOCAL_LENGTH,motion2=帧间像素位移×FOCAL_LENGTH)
- t2_fardrop_min_near(饥饿保底,默认30;上一帧近距供给(过视差门特征数)<30 时本帧不剔远)
- census:[T2depth] flag=far_drop(src=stereo/motion2)+[T2gate] 增 fardrop=%d/%d near=%d/%d 字段(老字段位置不变)

## 格设计(6+1 格,执行顺序预注册)
| 格 | 袋 | 开关 | 目的 |
|---|---|---|---|
| G0 | t2_C_033818_shift | **off(新二进制,canonical)** | 默认关逐位不变验证(对照=既有 R2DET1 baseline 的 vins_out.bag,判据=odom 逐位一致或统计等价,预注册选**逐位**) |
| G1 | t2_C_033818_shift | on@0.5px | 温和档(拒 Z>93.6m) |
| G2 | t2_C_033818_shift | on@1.0px | 中档(拒 Z>46.8m) |
| G3 | t2_C_033818_shift | on@2.0px | 强档(拒 Z>23.4m,≈R2 垃圾带 p75 边界) |
| G4 | t2v3_ground_210307 | on@2.0px | 正常轮回归 |
| G5 | run_U3PO_211438/flight.bag | on@2.0px | 存活导航轮回归+vis_n 不劣化 |
| G6(追加) | t2v3_route_213717 | on@2.0px | R3 合流后 route 袋格(R3 定因=非视觉载体,预期**无救**——预注册为"机理独立性验证格":若 R2F 恰好救 route=意外证据需回挖,若不救=R2/R3 载体独立的确认) |

## 判据(预注册,先写后跑)
- **G0(零回归)**:vins_out.bag 的 /vins_estimator/odometry 与 R2DET1 baseline **逐位一致**(md5 对比;若 vins_out.bag 录制含时间戳噪声则退 odom 数值序列逐位;再退=预注册统计等价 p99<1mm——但首选逐位,本格管线确定性已由 R2 三向互证)。
- **G1-G3(RESCUE 判定)**:主判据=死亡袋原 fail 窗(baseline 首 [T2fail]/Bas 爆时段)**消除或推迟>30s**;辅判据=①far_drop 计数>0 且集中在 fail 前窗(门活性)②vis_n(track)不坍塌:fail 前窗 track p50 ≥ baseline 同窗×0.8③[T2gate] near 供给不长期=0(饥饿未触发)。
- **pass 级别**:G1-G3 任一档 RESCUE 且 G4/G5 零回归 → R2F 生效档进入在线轮候选;全部不救 → 回挖门参数(轴:近距阈值/供给参数)而非放宽(禁放宽条款)。
- **G4/G5(正常轮零回归)**:预注册=**统计等价**(非逐位,因为开关开必然改变数值):判据=①全程零 [T2fail](baseline 也是零)②ATE_p95 变化 <0.05m(ground)/<0.5m(U3PO,baseline 2.48m)③vis_n p50 不降 >10%④far_drop 率 <30%(过严信号)。
- **G6(route)**:无救=预期(载体独立);任何"改善"按意外证据回挖。

## 失效模式预注册(任务书单元3.1 新增条款)
- **FM-① 特征饥饿**:任一格出现 vis_n(p50 track)<50 持续 ≥10s,或 near 供给=0 持续 ≥5s → 判"门过严",处置=提 fardrop_min_near 或降档,禁直接判 R2F 失败。
- **FM-② 爆点不消除**:G1-G3 门活(far_drop>0)但 fail 窗不变 → 判"门未触达载体",处置=回挖(载体段特征的 disparity 分布 vs 门值,判是视差轴还是深度量程轴),禁放宽深度门(T2_DEPTH_GATE 已在别的格证明无效)。
- **FM-③ 正常轮回归**:G4/G5 任一指标越预注册容差 → 该档禁入在线轮,记回挖(区分饥饿 vs 数值扰动)。
- **连续 2 格同因失败停跑转分析**(任务书纪律)。

## 执行纪律
- 每格前 pgrep 守卫;私有 master 11312(t2_replay.sh 管线);每格 vins_node md5 登记(285278cc 分水岭之后的新栈=本 build,栈号=编译后 md5,README §3 登记)。
- 判读工具:r2_judge.py 复用+新 far_drop 字段解析(先 dry-run 验证解析器,后跑正式格)。

## 实现差异如实记录(2026-10-02 02:1x,判别格开跑前)
1. [T2gate] census 行**未增字段**(编辑器传输层反斜杠锚失配×3 后放弃该行修改)——far_drop 观测走 [T2depth] flag=far_drop 行(判读按行聚合),t2_near_supply 内部记忆不变;判读脚本聚合 [T2depth] 即可,判据不变。
2. t2_min_disparity 参数类型=**double**(非 int):0.5px 档需要;yaml 键名不变。
3. G0 逐位对比**降级**:285278cc 栈存档仅 vins_node 可执行(动态链当前 lib,跨栈 A/B 不可行)——改为 G0a 双跑逐位(新栈 canonical 确定性自证)+代码审计(新增分支全在门守卫内)+gtest DefaultOffBitIdentical 逻辑级证明。**教训入 README §3:栈存档必须 lib+可执行双件,凭据登记双 md5。**
