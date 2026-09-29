# T1-G2 快胜序：EXP-0 存量挖掘 + EXP-1 分配器判据（2026-09-30 夜）

状态：EXP-0/EXP-1 完成（C05 §6 快胜序）；G2 其余（EXP-2 被动仪表/EXP-3 密度复刻/EXP-4 两臂）未启动。
执行者：T1 v7 夜 1。全部 0 锁。

## EXP-0 结果

### 1. 存量快照（止损线触发 + 新发现）

`cat ~/sitl_sim/t1_evidence/u2v2_2026-09-28/master_pre_boot*.json`：**全部 3 个文件均为 Traceback 错误产物**
（`ValueError: too many values to unpack (expected 2)`，源自快照器 u2_repro2.sh:22-46 的 set comprehension）。

判定：
- nodes_dead 逐 boot 序列**从未真正入账**（C05 I6 所引数据源实为坏产物）——按止损线"json 不存在等效"，
  直接按 EXP-3 预载设计执行，不追查历史。
- 新发现：快照器本身有 bug（API 返回值解包假设错误）。EXP-3 前需修快照器（三值解包→二值假设），
  否则预载数据集同样是 Traceback。

### 2. 版本现势（I1/I2 出局项复核）

- ros-noetic-ros-comm 1.17.4-1focal.20250520 ✓（与 pre_dpkg.txt 一致，无版本漂移，C1 排除维持）
- ros-noetic-rosgraph 1.17.4-1focal.20250519 ✓
- kernel 5.15.0-139-generic ✓（≥4.16，C2 排除维持）

### 3. 内核/资源一次性判据（P8 素材）

| 项 | 实测 | 判读 |
|---|---|---|
| ip_local_port_range | 32768–60999（P=28232） | 端口池基线 |
| nf_conntrack_count/max | 114 / 262144 = **0.04%** | **conntrack 逼近 max 的复活条件不成立（排除向）** |
| ulimit -Sn / -Hn | 1024 / 1048576 | 软限低（背景风险项，按 C05 排除表口径不采集为主因） |
| ss -s | TCP 61（estab 38，timewait 1） | 当前低载正常 |

## EXP-1 分配器顺序性（100 connect 实测）

```
first5: [45228, 45234, 45240, 45250, 45260]
last5:  [46106, 46110, 46126, 46134, 46142]
diff: min=2 max=16 unique=8, monotonic_increasing: True
```

**判定：连号（顺序游走），非随机均匀。** P8 复活向的核算路径激活：
- n* ≈ P/E = 28232/E；E∈[50,300] ⇒ n*∈[94, 565]
- 起病区 50-70 boot：若 E≈400+ 则 n*≈70 命中起病区；E≤300 则 n*≥94 略高于起病区
- **E 的实测（每 boot 匿名注册数）成为 H6 生死判据，挂 EXP-3 窗采集**

## P8 归档结论

两向中：conntrack 向**排除**；分配器顺序向**复活待 E**（顺序游走使环绕共振在 n≥n* 可发生）。
H6 保持开放，权重随连号实测轻微上调。宿主终裁待 EXP-4 A 臂（P10 四带）。

## 产物

- 本文件：t1_evidence/v7_2026-09-30/G2_EXP0_EXP1_results.md
