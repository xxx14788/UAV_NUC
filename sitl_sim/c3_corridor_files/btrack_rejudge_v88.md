# C3-v88 §二.1 B-track：18 轮绕行门 v2 回判表（预注册 schema；零空格）

出生病预注册定义=init 段 30s 内 odom-vs-truth 发散 >1m（T4 型）；健康旗=H(健康)/S(出生病)；族=失控/TIMEOUT/NEVER-FLEW/干净；绕行门 v2=infl<0.2∧ndetour≥2∧maxlat≥0.32∧ratio≥1.07（红 41 主判）；S 门=照报。

| 轮 | 健康旗 | drift_init(m) | infl门 | ndetour门 | maxlat门 | ratio门 | 绕行门 | S门 | 到位 | 族 |
|---|---|---|---|---|---|---|---|---|---|---|
| V82F1 | H | 0.12 | True | True | True | True | True | False | 0.170✓ | 干净 |
| V82F2 | S | 3.16 | True | True | True | True | True | False | TIMEOUT 6.854 | TIMEOUT |
| V82F3 | H | 0.10 | True | True | True | True | True | True | 0.158✓ | 失控 |
| V82F4 | H | 0.08 | True | True | True | True | True | False | 0.446✓ | 干净 |
| V82F5 | H | 0.08 | True | False | True | True | False | False | 0.169✓ | 干净 |
| V82F6 | H | 0.14 | True | True | True | True | True | False | 0.179✓ | 失控 |
| V82G1 | H | 0.14 | True | True | True | True | True | True | 0.173✓ | 失控 |
| V82G2 | H | 0.18 | True | True | True | True | True | True | 0.163✓ | 失控 |
| V82G3 | H | 0.22 | True | True | True | True | True | False | 0.209✓ | 失控 |
| V82G4 | H | 0.16 | True | True | True | True | True | True | 0.164✓ | 失控 |
| V82G5 | H | 0.14 | True | False | True | True | False | False | 0.177✓ | 干净 |
| V82G6 | S | 1.17 | False | True | True | True | False | False | NEVER-FLEW | NEVER-FLEW |
| V86P1 | S | 2.54 | True | False | True | True | False | False | TIMEOUT 1.536 | TIMEOUT |
| V86P2 | H | 0.15 | True | True | True | True | True | False | 0.171✓ | 干净 |
| V86P3 | H | 0.34 | False | True | True | True | False | False | 0.167✓ | 失控 |
| V86P4 | S | 1.72 | True | True | True | True | True | False | TIMEOUT 4.425 | TIMEOUT |
| V86P5 | H | 0.15 | True | True | True | True | True | False | 0.169✓ | 干净 |
| V86P6 | H | 0.17 | True | True | True | True | True | False | 0.171✓ | 失控 |

## 各子门失败率（三种口径）

- infl门：全轮(有效) 1/17；健康域 1/14；健康∧干净 0/6
- ndetour门：全轮(有效) 3/17；健康域 2/14；健康∧干净 2/6
- maxlat门：全轮(有效) 0/17；健康域 0/14；健康∧干净 0/6
- ratio门：全轮(有效) 0/17；健康域 0/14；健康∧干净 0/6
- v2门：全轮(有效) 4/17；健康域 3/14；健康∧干净 2/6

**最大失败子门（健康域）=ndetour 门（2/14）**

## 杠杆命中判定（杠杆表承 v8.6：goal 微调/inflation 微调/桥接帧率）

- 判定：属参数域 → **pilot 带杠杆飞**：杠杆 3 goal 微调 ±0.2m（v8.6 杠杆表次关联：goal 端点/进场角→织行段数间接命中）+ 杠杆 5 桥接帧率（感知滞后→远绕族）
- 几何结构性判定：干净域 v2 通过率 4/6；S 门干净域 0/9 承 13m 层几何简并判例（单侧 C 形=几何最短）——v2 门不含 alternating，若 v2 亦现结构性零通过则属红 44 呈报域（本表实测见上，非零即不触发呈报）。

## §二.2 headline 投影预注册输入（修复假设=失控→0；导航相不受修复影响）

- 起飞安全率（18 轮域）：17/18 = 0.944
- 健康域绕行门 v2 率 r̂=11/14 = 0.786
- 健康域到位率（≤1.0m）=14/14 = 1.000
- 降落成功率假设=1.0（修复后盲降/正常降落 z_end≈0；干测+重放证据链在案）
- **投影综合成功率（headline=v2门主判口径）= 0.944×0.786×1.000×1.0 = 0.742**
- N=6 期望成功数≈4.5，二项 95% 带≈[2, 6]（成功数）
- N=25 期望成功数≈18.6，二项 95% 带≈[14, 23]（成功数）

JSON -> btrack_rejudge_v88.json

## 预注册补章（pilot 烧飞前落锚；时点=悬停回归在飞、pilot 未烧）

1. **杠杆预注册**：最大失败子门=ndetour（健康域 2/14）→ 杠杆 3 goal 微调单变量：pilot goal=**(4.20, 4.40)**（y+0.2m 在径 B 授权域内；机理=端点横移改变末段进场角促织行分段）。杠杆 5 桥接帧率不并用（单变量纪律）。
2. **投影区间双锚**：r̂ 主锚=健康域 11/14=0.786（含失控轮导航相——修复不改导航故其 pre-arrival 门值有效，但整袋门值含飞逃尾伪影偏乐观）；保守锚=健康∧干净 4/6=0.667。投影综合成功率区间 **[0.63, 0.74]**（0.944 起飞 × r̂ × 1.0 到位 × 1.0 降落假设）。
3. **pilot 适配门数学**：P(X≥3 | N=6, p=0.74)≈0.96 / p=0.63 时≈0.84——≥3/6 门槛在两锚下均大概率可达；若 <3/6 → 杠杆重启一次（阶梯 §二.5）。
4. **诊断副产物**：P1/P4 两 TIMEOUT 轮 drift_init=2.54/1.72m 双双出生病——超时织行族与方差族同源（init 发散→贴箱振荡），S 家族=外生彩票口径再添一证。
