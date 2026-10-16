# 夜报：③C 甲合流册 v4.2 会话阶段收口（2026-10-16 18:21-21:20）

## 一、完成（保底交付 v1 全链落袋）

1. **§一 收口件**：geom 补跑核验全过（25/25+抽 4 互异+REDLINE11 空+world=v7 名义注记入 CORPUS_NOTE）；git 三笔全推（1edc630 config dd9fb372 补漏/e186fcd 六文档/f5e64bc 工具族，f4b492a→f5e64bc）+夜报+语料说明。
2. **§二 v9 实验室尺度就绪**：预注册跑前锁定（v9_design_prereg.md：静态表/S 形门推导五门/**ratio≥1.07=数值路径积分锁定源**——交替最短 6.3571m=1.0703 下取，C 形 1.0546 数学排除；**45° 对角支撑勘误 A_geo=0.543**）；生成器六硬门全 PASS+确定性复核（md5=5f3d48eb 四处部署+材质入系统路径）；判读器 v9 表+LAB lane+推导门扩展（**旧版本回归 BIT-IDENTICAL**）；批脚本 v9 适配（GZ=0.8/budget 120/lane LAB）；干测：38 模型清单全对+相机活。
3. **§四 终版判读（两层毕）**：13m v7.3 层五层表（S 3/25=12.0% [4.2–30.0]/跳变 52%/随机 0/**起飞 25/25 全干净**/corners 150 满配额/miss 中位 8.01m）+v7.0 历史层重判（S 5/25=20.0%——**修正旧 c6 工具 geom 文件名双 run_ 前缀 bug**）+三层对照表+H-dJ2 四形态链（**诚实新发现：真 v7.3 批 Bricks 对照未塌 0.81**——H-dJ2 表述分层收窄）。
4. **§五 终版结论 v1 保底版**：九章节全规格+v9 槽位【待飞】标注+附录数字交叉校验表；三处落盘+git d21c9a2。
5. **§六 图集**：F73 批 25+v7.0 S 样例 5=30 张，程序化正判 30/30 PASS 零 SKIP/Error，md5 双端 30/30 逐位一致，拉回 t1/2026-10-15_③C终局/atlas_v9/ + 抽验回执模板（建议 10 张清单）。
6. **§七**：待核②归档（sim near=0.001 vs D435 0.28m 结构性盲区→建议单条款承接）+差异文档回填五节（含新增受限空间差异节四项）+坑账 N1-N8。
7. **§八 实验室首飞建议单 v1**：场地 1:1 布置图+预期基线表+中止判据+录制清单（强制双目）+坐标对齐条款+受限空间工艺+折扣声明+回场对接表；三处落盘。

## 二、卡点（客观描述，禁方案）

- **v9 飞行域被机器级故障阻塞（红线级）**：depth 传感器（type=depth）渲染全 NaN+同传感器 RGB 均匀黑帧=planner 全盲，禁盲烧批。11 项系统排除（世界×3/部署物隔离/显示器×2/位姿空中/包/dpkg/GPU dmesg/suspend/资源/OGRE FBO/缓存清理）均无罪；回退窗口=08:07-19:12，触发因素不明；三周期重探（19:12/20:35/21:15）均 NaN，丙册空闲态亦复现。法证正本=depth_regression_forensics.md；STATUS 20:30 红线告警+@用户（整机重启建议=用户域）+@丙册（10min 隔离窗请求）。**v9 试录 12+终版批 ≥25 待机器恢复即飞（预注册+适配件全就绪）。**

## 三、等待面

- W-用户：①机器重启复测（depth 卡点解锁=v9 批起飞）②图集抽验 ~10 张（回执模板在 atlas_v9/）。
- W-丙册：T/M 定案件（增强批槽预注册，可选无依赖）；空闲窗 10min 隔离复测请求。
- 收工双写（唯一一次）**未做**——战役保持开启，v9 真收口（或条件态收）时执行。

## 四、产物指针

- 3090 ~/sitl_sim/c3_corridor_20261013/：v9_design_prereg.md、gen_corridor_world_v9.py（+v9_gen_run.log）、sitl_world_corridor_v9.world、JUDGE_final.md、layer_v70/、final_v73_jia/{LAYER_STATS,BYBOX_PAIRING,CORPUS_NOTE}.md、traj_atlas_f73/（30png+md5+verdict）、c3a_layer_stats.py、c3_atlas_batch_f73.sh、depth_regression_forensics.md、s2r_diff.md（回填版）、避障能力终版结论.md、实验室首飞建议单_v1.md。
- 仓 docs/：c3_final_conclusion_v1/c3_lab_firstflight_memo_v1/c3_judge_final/c3_s2r_diff(+前四笔)。
- Win t1/2026-10-16_③C甲攻坚/：结论+建议单+坑账；t1/2026-10-15_③C终局/atlas_v9/：图集 30 张+回执；plans/执行中/：阶段清账版。
