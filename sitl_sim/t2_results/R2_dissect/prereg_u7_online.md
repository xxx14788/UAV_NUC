# U7 重应用在线验证轮预注册（prereg_u7_online）

- 写表时刻：2026-10-01 19:52，U7 源码编辑/重建/在线轮全部开跑之前（零 U7 数据产生）
- 解锁依据：任务书 v7.2 U7 单元（解锁=R2 定案排除栈差变量；R2 判决=carrier_input_domain，04d1a73）
- 改动面：parameters.h:23 FOCAL_LENGTH 460.0→467.7427（=bccc962 原改动重放；作用点=投影因子 sqrt_info est:112 + 视差归一化 fm:126-127/parameters.cpp:131）；其余全 canonical；重建后新 vins_node md5 记账+README §3 追加行；gtest 三件套须 22/22（reanchor7/propagate9/depth_gate4/imu_factor2，bccc962 同口径）

## 在线轮判据（写死，先于飞行）

- 载具：SMOKE_OWNER=T2-U7 bash vins_smoke.sh（T1-E4 轮后窗口，锁纪律照旧）
- **U7OL1**：--world sitl_world_obstacles --goal 7 -4 1 --budget 180 --tag U7OL1
  - **PASS-U7** ⇔ 全程零 [T2fail] 且四指标 RESULT 达标 → U7 无害性在线正向成立（C-2 闭）
  - **SCENE-CARRY** ⇔ [T2fail] 落 134±5s 带或位置跑飞型且四指标形态与凭据栈先例（030927/032005）同型 → 判=输入域载体表现（R2 已预期，不构成 U7 罪证），追加 U7OL2 取正向证明
  - **U7-SUSPECT-REVIVE** ⇔ [T2fail] 落上述带外或新形态（Bas 爆型于巡航段等）→ U7 嫌疑复活：立即回退（git revert 重应用提交+重建回 cf0384 等价栈）+回放复现单变量定位
- **U7OL2**（仅 SCENE-CARRY 后触发）：--world sitl_world_obstacles --goal 0 0 1 --budget 120 --tag U7OL2（悬停）
  - **PASS-U7** ⇔ 零 [T2fail] + odom 连续（无 >1s 断流）+ Bas/Bgs 正常带（|Bas|<0.8 巡航值域）→ 悬停域 U7 无害性正向成立，C-2 以「场景分门」口径闭（obstacles 导航域死亡=场景载体,悬停域干净=栈差无恙）
  - FAIL 任一 → 同 U7-SUSPECT-REVIVE 处置
- 观测列：[T2fail] 次数×时刻；vins.log 全程（[T2diag] Bas/Bgs 带）；odom 契约字段（frame_id/child_frame/rate）；四指标 RESULT；bag 留档（帧包正源+tag 轮保全=用户裁定）

## 运行纪律

- U7 编辑+catkin_make 仅在 T1-E4 窗口结束后执行（STATUS 回执或进程面双确认）
- 每轮跑前 pgrep 清场断言（vins_smoke 自带）；磁盘水位 df≥65G
- 若 gtest<22 或重建异常 → 全线停，不飞
- 回放域结论红线 11 沿用；本轮全部=在线域（即生死判据域）
