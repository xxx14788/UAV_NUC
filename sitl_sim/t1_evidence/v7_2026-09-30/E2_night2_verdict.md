# T1-E2 夜 2 终稿：修复包落地+gtest 全绿+插桩三发现+崩溃遗留（2026-09-30）

状态：修复代码完成且 gtest 绿，**但因重放域崩溃未定位，修复包不入库**（工作树/备份保留，
devel 二进制回 legacy 安全态）。门禁 A/B 挂账。执行者：T1 v7 夜 2。

## 1. 交付清单

| 件 | 状态 |
|---|---|
| 写点全枚举+并发审计（E2_writepoint_audit.md） | ✓ 完成：latest_* 唯二写点（ULS :1794 批量覆写+fastPredict 积分），锁序 mProcess→mPropagate→mBuf 无环 |
| β（init 三点 flag 置位入 ULS 临界区首） | ✓ 实现并验证（E2uls 打印 flag=1 从 init 起生效） |
| gap 卫（0.3s 阈值+计数） | ✓ 实现（重放零触发=贴管正常） |
| dt 钳制（时基前移+逃生 b pub_hold） | ✓ 实现；**逃生(b)守卫初版漏插**（只有注释），备份副本已补，**未验证** |
| A8 卫生件（锁内重读 flag） | ✓ 实现 |
| REANCHOR_DEBUG 插桩 | ✓ 工作（夜 2 三发现的数据源） |
| gtest（PropagateGuard 9 用例+复合） | ✓ 9/9 绿（手编+catkin 双验）；VINS 侧三套件 7+9+4=20 全绿 |
| 门禁 A/B（P1-P4） | **挂账**（见 §4） |
| 提交 | **挂账**：修复 hunks 不入 main（崩溃未定位）；工作树混合态保留（/tmp/e2fixed_backup 独立副本+逃生守卫补丁） |

## 2. 插桩三发现（夜 2 新知）

1. **重放域 ULS 全程 buf 空**（213/213 first_dt=-1）=贴管正常，gap 卫零触发（设计预期）。
2. **重放域传播链与滑窗解分叉达 50m 级**（t=29.6-30.2 Δ 从 46 涨到 54，每帧 +1.5m）——
   机制=ULS 覆写后 fastPredict 大 dt 追帧步（vins 滞后流 5s 时 dt≈5s 一步）。
   **legacy 无钳制下这些大步直接进发布流**（重锚 8904 帧的 heavy 尾）；钳制后正确拦截
   （P4"无负 dt 积分"判据满足，7805 次触发全程无负 dt 步进）。
3. **袋 t2v3_hover_203248 含 IMU 乱序回退段**（clamp 序列 15.9→28.1→15.9→35.1→22.9）——
   与 T3 04:33 事故的 X1final 污染签名（±13s 跳）同族。**该袋不宜再作门禁基座**；
   候选替换=t2v3_route_112652（W1.3 PASS 白名单袋）。

## 3. 崩溃遗留（入库阻塞项）

- 签名：`trap stack segment`（SIGSEGV 栈段，libvins_lib.so ip 偏移 0x289e8 区）+
  `terminate called without an active exception`；**确定性复现**（两轮同点崩，最后打印=
  ULS 的 E2uls fprintf→addJump 路径）；t=35.1（回退段后）。
- **二分已做**：legacy 无补丁同袋跑完 154.2s 零崩溃 ⟹ **崩溃由补丁引入**（非袋因素、非环境）。
- 定位尝试：addr2line（无符号，build 无 -g）、nm 静态表（strip）、RelWithDebInfo（增量 build
  不吃 build type）——全部未遂。
- 夜 3 二分计划（按嫌疑序）：①ULS 尾部 fprintf+addJump/on_anchor 块单独回退 ②inputIMU A8 块
  单独回退 ③gdb batch（全量重编 RelWithDebInfo：catkin_make --pkg vins 需先 rm build/VINS-Fusion）
  ④逃生(b)守卫补丁合入后重验。
- **红线核对**：armed 态断连行为未改（本包不触 FCU 链路）；实机 yaml 未动 ✓。

## 4. 门禁 A/B 挂账（夜 3）

前置=崩溃定位修复。基座=换 route_112652 袋（或 D1 时代同条件重放窗口）；A/B 同二进制只切
reanchor_smooth；判据=P5（事件帧 dP≤0.03 或事件不发生+p99≤0.02+发布率 N 复算）。
**47s 型零捕获案保持挂账**：本夜重放域未复现 0.2 事件（重放域条件漂移：5s 滞后+袋回退段，
R7 caveat 应验），原袋在线域行为仍需在线插桩轮（或 D1 同条件重放）裁决。

## 5. NUC 现场交接

- devel 二进制=**legacy（03:53，干净基线 HEAD 编译）**——T2/T3 白天可直接用；
  混合树（T2 W-A WIP+T1 E2 hunks）未提交未回滚，T2 白天重编前请知悉工作树含 T1 E2 实验件
  （/tmp/e2fixed_backup 有独立副本）。
- /tmp 产物：t2wip_backup（T2 混合态 8 文件）/e2fixed_backup（T1 修复版 5 文件）/补丁脚本三件。
- 悬案池更新：47s 型案→"修复实现+gtest 绿，崩溃与门禁挂账"；SIGTERM 案→设伏运行中。
