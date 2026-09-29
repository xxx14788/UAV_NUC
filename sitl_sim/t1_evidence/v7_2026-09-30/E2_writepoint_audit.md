# T1-E2 写点全枚举 + 并发审计（2026-09-30 夜 2）

状态：枚举与审计完成；修复（β/gap 卫/dt 钳制/逃生 b/A8）按 STATUS 预告 03:19 起 15min 异议窗后实施。
基线：b1b2eb6（D1 smoother）后的 estimator.cpp（1834 行）。

## 1. latest_* 写点全清单（grep 全文穷尽）

| # | 写点 | 行 | 线程 | 锁 | 写入语义 |
|---|---|---|---|---|---|
| W1 | updateLatestStates() :1808-1817 | 覆写 latest_time/P/Q/V/Ba/Bg/acc_0/gyr_0 = 滑窗解 | T3（processThread：:735 稳态 + :530/:616/:658 init 三点） | mPropagate 全程 | **批量跳变**（重锚本体） |
| W2 | fastPredictIMU :1786 → propagateOnce :1756-1780 | 引用传参积分推进 latest_time/P/V/Q/acc_0/gyr_0 | T1（inputIMU :213，发布线程）+ T3（ULS :1825 重放循环） | mPropagate（两处调用点均在临界区内） | 连续积分（无跳变，除非 dt 异常——W3 缺口） |

**无第三写点**（grep `latest_P|Q|V|time|Ba|Bg` 全文核验；publish 侧 P_pub/V_pub 为局部叠加不回写内核）。

调用图：
```
init 三点 :530/:616/:658 ─┐
                          ├─ updateLatestStates() [mPropagate]
稳态 :735 processMeasurements ┘        │
                                       ├─ 覆写 :1808-1817
                                       ├─ mBuf.lock 快照 buf → 重放 {fastPredictIMU; shadow propagateOnce}
                                       └─ addJump(sh−latest) :1831-1832（REANCHOR_SMOOTH && flag==NON_LINEAR）
inputIMU :213 fastPredictIMU [mPropagate] → 有界性门 → smoother 叠加发布
```

## 2. 零捕获矛盾（夜 1 裁决的行级定位）

实测（夜 1+今夜复验）：smooth3 袋常规重锚 8904→5 帧（REANCHOR_SMOOTH 生效实锤），但 47s 型两事件帧
dP 与 legacy 逐位一致（零补偿）。addJump 条件 `REANCHOR_SMOOTH && solver_flag==NON_LINEAR` 在稳态恒真、
ReanchorSmoother::addJump 无条件捕获（头文件全文复核无防御分支）。

⟹ 剩余通路二选一：①事件帧 `solver_flag != NON_LINEAR`（枚举仅 {INITIAL, NON_LINEAR}，稳态下无改
INITIAL 的路径——failureDetection 会打 [T2fail] 且该轮无）；②**事件帧 sh_P−latest_P ≈ 0**（捕获 Δ 为零
而发布流跳变来自他处）。②的直接候选：**跳变发生在 ULS 覆写与 addJump 之间的重放循环里**（重放首步
dt 异常大/或在重放中 latest 与 shadow 链被同化）——纯推理不可分，**插桩重放裁决**（REANCHOR_DEBUG
env 门控打印：Δ 三轴、flag、重放首步 dt、addJump 值；默认关零开销）。

## 3. 并发审计表（三线程×三锁）

| 锁 | 护域 | 使用点 | 锁序 |
|---|---|---|---|
| mBuf | accBuf/gyrBuf/featureBuf | inputIMU/inputFeature push；processMeasurements pop；ULS :1818-1821 快照 | ULS 内 mPropagate→mBuf（单向嵌套） |
| mPropagate | latest_* 全家 + reanchor_smoother + pub_hold（新） | inputIMU :211-241；ULS 全程 :1796-1833 | 不主动嵌套上级 |
| mProcess | 滑窗状态 Ps/Rs/Vs/Bas/Bgs/Headers/frame_count/f_manager | clearState/optimization/processImage/processMeasurements 大段 | ULS 在 mProcess 持有下拿 mPropagate（mProcess→mPropagate 单向） |

**锁序图**：mProcess → mPropagate → mBuf，无环，无死锁。

发现项：
- **W1 TOCTOU（真 UB，A8 卫生件）**：inputIMU :210 锁外读 solver_flag，与 T3 的置位（init 三点/clearState）
  竞态；后果上限 ~0.005m（C03 L3d，~30× 距 0.157）。β 落地后 init 置位移入临界区，:210 读到的
  NON_LINEAR 必对应"已锚定或锚定中"，剩余竞态面=clearState（failure 重启）瞬间——A8 锁内重读收口。
- **W2 init 捕获缺口（β 修）**：三点 `updateLatestStates(); solver_flag=NON_LINEAR;`——ULS 跑时 flag
  仍 INITIAL ⟹ :1831 addJump 跳过 ⟹ init Δ 裸出。且"ULS 完成→flag 置位前"的窗内 T1 读不到
  NON_LINEAR（INITIAL 期停发，legacy 语义）；但"flag 置位→ULS 已完成"次序保证……实际 legacy 顺序是
  ULS 先、flag 后，故无陈旧发布窗；**真正的缺口只是 addJump 被跳过**（Δ 不捕获）。β 把置位搬入
  mPropagate 首：addJump 条件在 init 点为真 ⟹ init Δ 捕获；INITIAL 期停发语义保持（置位前 T1 读
  INITIAL 不发布）；fork 往返（clearState:76 置回 INITIAL）每次重走三点 ⟹ β 每次生效。
- **W3 propagateOnce 无 dt 界**：:1759 `double dt = tn - t;` 无钳制——跨域/断流后第一步大 dt 直接
  0.5*dt²*un_acc 进 P。修=dt∉[0,0.5] 仅更新 acc_0/gyr_0+时基前移（T2-U1 同款）+pub_hold 逃生 (b)。
- **双 ULS 连发**：非竞态（同一线程 T3 串行，144ms=相邻两处理帧）——C03 已关闭，枚举复核一致。
- clearState :30 持 mProcess；:156/:304 两个额外调用点（setParameter/内联重置路径）同锁域。

## 4. 修复实施单（待异议窗到期动工）

| 件 | 文件 | 内容 |
|---|---|---|
| β | estimator.cpp :530/:616/:658 + :1794 签名 | ULS 加 `bool set_flag=false`；init 三点改 `updateLatestStates(true)` 删外层 flag 语句；ULS 内 mPropagate.lock 后置位 |
| gap 卫 | estimator.cpp ULS 捕获前 | \|sh_t − tmp_accBuf 首样本 t\| > 0.3s → 跳过 addJump + gap_skip_count++（头文件加计数器） |
| dt 钳制+逃生 (b) | estimator.cpp propagateOnce + inputIMU + ULS | dt∉[0,0.5] → 仅 acc_0/gyr_0 更新+latest_time=tn（时基前移）+pub_hold=true；inputIMU 见 pub_hold 跳过发布；ULS 覆写完成清 pub_hold |
| A8 | estimator.cpp inputIMU | mPropagate.lock 内重读 solver_flag，非 NON_LINEAR 跳过发布 |
| 插桩 | estimator.cpp ULS | REANCHOR_DEBUG env 门控 fprintf(stderr)：Δ/flag/首步 dt/addJump |
| gtest | test/ + CMakeLists | 三类新用例：β init 捕获+gap 卫、钳制逃生 (b) 两场景、连发+gap 复合（目标套件 ≥25） |
