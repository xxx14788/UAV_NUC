# hbloop 属主守护面单测凭据 v1.0（2026-10-11；T4 v5.33 会话补做件）

> 承：软件收官合并册 B 清单"锁 hbloop 独立重跑"（未做件移交 T4）+ T4 v5.33 任务书单元 2"锁 v3 hbloop 属主守护面单测（低优顺带）"+ lock_v3_production_conclusion_v1.md §3.4 自认未跑项。
> 被测件=~/catkin_ws/sitl_sim/sitl_lock.sh **v3（md5 d7b3efa0，零改动）**；测试=侧锁制：SITL_LOCK_FILE=/tmp/t4_hbloop_test_v533.lock（永不触碰生产锁 ~/sitl_sim/SITL.lock），SITL_LOCK_SKIP_DISK_GATE=1（非飞行锁用途，脚本头注许可）。
> 脚本本体=hbloop_owner_guard_test_v533.sh（Windows 工作区 t4/v533_out/ 同步存档）。

## 1. 测试设计（四机制点八断言）

| # | 断言 | 守护面语义 |
|---|---|---|
| T1 | get 空场 owner=显式 $$ rc=0 | v3 owner=调用方会话 PID 契约 |
| T2/T2b | heartbeat 匹配前缀 rc=0 且 symlink mtime 刷新 | 心跳=持锁者唯一刷新通道 |
| T3/T3b | 非属主前缀 heartbeat rc=1 且 mtime 零改动 | **heartbeat 属主守卫：拒绝代心跳**（L130-131） |
| T4/T4b/T4c | 易主后 hbloop 一个 300s 心跳周期内自退；新主 get/heartbeat 不受影响 | **hbloop 锁丢/易主自退**（L137 `heartbeat || exit 0`） |

## 2. 实测输出（3090，2026-10-11 15:41-15:47）

```
PASS T1 get 空场 owner=显式$$ (rc=0)
  lock=T4-EHB533A-3154273-154129
PASS T2 heartbeat 匹配前缀 rc (rc=0)
PASS T2b mtime 刷新(1791704489→1791704491)
PASS T3 非属主 heartbeat 拒绝 rc (rc=1)
PASS T3b mtime 未被代刷
PASS T4b 易主后新主 get rc (rc=0)
PASS T4 hbloop 易主自退
PASS T4c 新主 heartbeat 不受旧 hbloop 影响 (rc=0)
== hbloop 属主守护面单测结果: PASS=8 FAIL=0 =
TEST_RC=0
```

## 3. 结论

1. **hbloop 属主守护面 8/8 PASS（rc=0）**：heartbeat 属主守卫（阴性拒代+零副作用）与 hbloop 易主自退两机制点均实证有效；与本日 E1 v3 回归新例 7/7（含 hbloop 相关）互证=守护面双覆盖。
2. v3.1 候选面：本轮测试未发现新缺陷，无候选项产生（守卫面维持 v3 原样）。
3. 销号：合并册 B 清单"锁 hbloop 独立重跑"→本件销号。
4. 测试后场净：侧锁已释放删除（`== 结果` 行前 release+rm），生产锁零接触（全程 SITL_LOCK_FILE 重定向）。
