# P0-A.1：REANCHOR_DEBUG 探针传导断点定位与修复（T1 v8.0 夜1，2026-10-01）

结论：**断点=代码侧占位符，非脚本侧**。修复落库+验证 PASS（PROBECHECK，E2uls=42 行）。
此后一切飞行轮默认带探针（v8.0 P0-A.1 要求），T2 W-C2/T3 X 线起飞前置解除。

## 1. 断点定位（git 地质学）

| 层 | 事实 |
|---|---|
| 探针门控 | estimator.cpp `static reanchor_dbg`，唯一赋值点=文件头声明处；[E2uls]/[E2clamp]/[E2gap] 三探针行全在 reanchor_dbg 门内（:2039/:2102/:2108 一带） |
| 原始形态 | a5cd330（09-30 03:59，E2 修复包重放）：`static const bool reanchor_dbg = (getenv("REANCHOR_DEBUG") != nullptr);` + `#include <cstdlib>` |
| **断点** | **c7d901d（09-30 09:10，T2-WA）把上述两处换成中性占位符**（`static bool reanchor_dbg = false;`，注释自述 "T1 placeholder swap; T1 free to reapply"）；此后 T2-WA 系列提交延续至今 |
| 连锁后果 | E3 在线验收轮（09-30 20:15 二进制，晚于占位符）探针行从未打印；当晚"E2uls 判据"由袋侧 dP 计数顶替——与 v8.0 任务书"不修好 W-C2 不起飞"判断一致 |
| 脚本侧 | vins_smoke.sh 此前无 export REANCHOR_DEBUG（发射链本身环境变量就不通，与代码侧断点叠加） |

## 2. 修复（9a26918 后提交）

1. estimator.cpp：恢复 a5cd330 原始两行（env 读取 + cstdlib），加恢复注记。
   行为面：REANCHOR_DEBUG 未设时 reanchor_dbg=false=占位符语义，**对探针关闭轮零行为差**。
2. vins_smoke.sh：①sim_vins 发射前默认 `export REANCHOR_DEBUG=1`（一切飞行轮默认带探针）；
   ②新增 `--probecheck` 模式：起栈→VINS init→grep simvins.log 三探针行→PASS/FAIL→自动清场放锁
   （不飞不录，全栈自检 ~2min，供 T2/T3 起飞前验探针链）。

## 3. 验证（PROBECHECK 轮，run_E2PROBE_022152，02:21-02:24）

```
[02:22:16] VINS init 完成 (+3s)
[02:22:16] PROBECHECK: E2uls=42 E2clamp=0 E2gap=0 (init-only round, no takeoff)
[E2uls] flag=1 sh_t=10.720 new_t=10.720 dP=[0.0039 0.0004 0.0002] |dP|=0.0039 first_dt=-1.0000
[E2uls] flag=1 sh_t=10.804 new_t=10.804 dP=[-0.0000 -0.0009 -0.0007] |dP|=0.0011 first_dt=0.0005 ...
[02:22:16] PROBECHECK PASS: probe chain transmits (E2uls lines in simvins.log)
```

- E2uls 42 行、|dP|=0.0005-0.0039（常规 solver 刷新量级，与 D1 p99=0.0055 基线同阶——
  假设表 §0.F3 预注册基线得到首轮印证）；
- E2clamp=0/E2gap=0（健康悬停预期，同基线）。
- DoD 口径"simvins.log 出现 E2uls/E2clamp 行"：E2uls 确定性达成；E2clamp 需钳制事件才打印
  （健康流为零=预期行为，非缺陷），首个带机动/异常的飞行轮自然覆盖。

## 4. 现场与协调

- 本修复与 T3 夜间两轮 X1img（01:59/02:07，均 FAIL，probe-less 盲轮）无交叠：
  我的文件编辑 mtime 02:12:34/02:13:08 均晚于其第二轮结束 02:10:45；锁/栈零冲突。
- 02:21 起新二进制+新脚本生效：**此后所有 vins_smoke 轮自动带探针**（simvins.log 会多
  E2uls 流，~10Hz，量级 1e-3 级，属正常基线非异常）。
- P0-A.2 数据采集约定与对号入座流程见 E2_jump_hypothesis_prereg.md（预注册于任何带探针
  数据轮之前——本轮 X1img 两轮在修复前，不计入假设表证据面）。
