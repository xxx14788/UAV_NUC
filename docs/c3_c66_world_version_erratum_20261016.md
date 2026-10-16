# C66 勘误件：C-5/C-6 两批实际加载 world=v7.0（非宣称 v7.3）——证据链与影响面（③C-甲 2026-10-16 03:05）

> 发现人=③C-甲 执行者（开工自检现场核验期，纯只读发现）。
> **域界声明**：本件只做事实取证与影响面陈述；C-5 判决书重判/C-6 收批判读口径调整=**乙册域**（红线⑨⑩），甲册不顺手改。甲册 Phase C 将以正确 world 起终版批，提供干净语料。

## 一、证据链（四重独立实证）

1. **活体 gzserver 命令行**（03:50 时刻在飞轮）：
   `gzserver ... worlds/sitl_world_corridor_v7.world`（PID 1789737，2026-10-16 02:52 抓取）。
2. **run 目录 sitl.log**（gzserver 输出行）：
   - C-5：run_C3V7E1_002333/sitl.log → `Loading world file [.../sitl_world_corridor_v7.world]`
   - C-6：run_C3VFE1_014038/sitl.log → 同上（E lane 各轮同）。
3. **批脚本源码**（c3_trial_batch_v7.sh 与 c3_final_batch_v73.sh 同病）：
   `run_round` 内 `vins_smoke.sh --world sitl_world_corridor_v7`（**名字未随 v7.3 部署更新**）；preflight 校验的是 v73 文件 md5 三处（文件本身没错，**起栈引用名错**）。链路：vins_smoke.sh `SITL_WORLD=$WORLD` → start_sitl_vins.sh `PX4_SITL_WORLD` → `make px4_sitl gazebo-classic_iris_stereo_vins` → 加载 `$(PX4_SITL_WORLD).world`。
4. **文件指纹与时间线**：PX4 worlds/sitl_world_corridor_v7.world md5=159272bd（v7.0），mtime=2026-10-15 23:04:41（C-2 v7 部署时刻，此后未动）；v73.world=383a301a，mtime=00:19:39。C-5 起栈 00:35 / C-6 起栈 01:40 → 两批全程加载 159272bd。

## 二、v7.0 与 v7.3 内容差异（96 diff 行，全部在 4 个 tag 箱的 visual 块）

| 项 | v7.0（实飞） | v7.3（宣称/预期） |
|---|---|---|
| tag 面几何 | `<plane>`×4，pose **全部无偏移（0 0 0）**=四张平面在箱中心十字交叉（±X 朝向两片 1.8m 宽×1.0m 高，±Z 朝向两片水平）——**平面埋于碰撞箱内/穿越箱体** | 薄板 `<box>` 0.02 厚外偏 ±0.501 贴四面（1.0×1.8/面） |
| 材质 URI | `model://c3_tagbox/...`（GAZEBO_MODEL_PATH 含 sitl_gazebo-classic/models，c3_tagbox 在册→纹理大概率可载，但几何形态错误） | `file://media/materials/...`（/usr/share/gazebo-11 系统路径） |
| 箱体主 visual | **无**（仅碰撞箱+四平面） | 无（薄板即面） |
| 碰撞体/箱位/间距 | 与 v7.3 **完全一致**（diff 不含碰撞块） | 同左 |
| 对照箱 cB2/cN2 | 一致 | 一致 |

**实飞形态总结**：tag 箱=1.0×1.0×1.8 实体碰撞箱（不可见）+箱中心四张十字交叉纹理平面（±X 两片对航线横向展宽至 1.8m）。AprilTag 纹理"存在但形态/位置错"：不在四垂直面，而在箱中心交叉面。

## 三、影响面（按判读门分列——乙册重判输入）

| 面 | 影响 | 严重度 |
|---|---|---|
| 门① geom（S 形 2/8） | 箱表（碰撞箱）与 audit `--world v7` 表**一致**（v7/v73 箱位同表）→ ndet/间距判读自洽；但**无人机实际规避的是 1.8m 宽交叉平面**（渲染面≠碰撞面），绕行几何与箱表假设有系统偏差 | 中（定性结论待乙册复估，定量 clearances 偏乐观/偏窄待重算） |
| 门② H-dJ2（tag 贴窗 0.55-0.85 vs 对照 0.03-0.17） | **证据基础受损**：判读宣称"AprilTag 每垂直面 400mm 富特征解除 d↑→塌陷耦合"；实飞 tag 形态=箱中心交叉平面（非垂直面贴板）。分离现象本身（tag 箱族 vs Wood/Bricks 族贴窗分离）在数据中真实存在，但**归因于"垂直面 AprilTag 富特征"的机理表述与实飞形态不符** | 高（乙册重判域：H-dJ2 表述需按实飞形态重写或降级） |
| 门③ 慢漂 | world 域已定案无关（C-5 停止注记归因渲染时戳域），不受影响 | 无 |
| thrust/起飞面 | 世界差异仅在 tag 箱 visual，起飞区无箱；不受影响 | 无 |
| C-4 供给面（stereo_r p50=0.810 等） | 若测量轮在 C-5/C-6 批内→同受 v7.0 形态影响（特征面=交叉平面） | 待乙册核对测量轮归属 |
| N=25 合并口径（C-5 8+C-6 17 同栈） | "同栈"成立但**栈= v7.0 world 栈**（非 v7.3）——两批内部一致，版本标签统一勘误为 v7.0 | 高（版本制记录） |

## 四、甲册处置（本册权限内）

1. 本勘误件+STATUS 通告乙册（收批判读前必读）。
2. **甲册 Phase C 终版批**：批脚本新写（c3_final_batch_v8.sh 族），`--world` 传 v8/v73 **正名** + **新增运行时校验**：每轮起栈后 grep 本轮 sitl.log `Loading world file` 行 md5 比对预期值，不符=该轮作废重跑（坑位 14 入月报：批脚本 world 名实不符+preflight 只验文件不验加载）。
3. Phase B v8 生成器已核（gen_corridor_world_v7.py 输出=薄板+file:// 形态，v7.3 正血统）——**无继承风险**。
4. 判读工具族 `--world v7` 表对 v7.0/v73 箱位同表（碰撞箱一致）→ 历史 geom JSON 不需作废，标注形态差异即可（乙册裁量）。

## 五、遗留问题（乙册裁量项，甲册不越权）

- C-5 门② 判决书（C5_试录双验证判决书.md）表述修正方式。
- C-6 收批判读是否按 v7.0 形态重写 tag 相关判读段。
- git 历史提交信息（f4b492a 等）中 "v7.3 383a301a" 表述的勘误注记方式。

——取证完成时刻：2026-10-16 03:05（C-6 批 NE6 在飞，收批前）。
