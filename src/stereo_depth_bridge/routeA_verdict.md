# §一 路A：空洞填充工程修复判决件（2026-10-17 v8.2）——FAIL 定案（近距未达+延迟超门）

> 任务书条款：SGBM 后加形态学闭运算（5×5）+边缘感知插值（inpaint TELEA，限有效区域边界内）；
> 填充率/填充误差逐帧登记；plane-truth 复测不劣化（≤3.29%+2pp）；复测近距→≥60% 过。

## 实现（v7 节点，已入仓待提交）

- `fill_holes()`：valid-mask 5×5 形态学闭运算定义小洞（≤3×3）→ TELEA inpaint 于**视差域**
  （uint8 天然覆盖 0-96 SGBM 范围免缩放；TELEA 边界内传播=限有效区域边界内构造性成立）。
- 管线序：SGBM→填充→深度→>60m/非有限剔除→纹理门控 T8/w25（门控后置=白静区幻影防线不变）。
- 开关：rosparam `~hole_fill` 默认 **false**（v6 存档行为逐位保持，T4 单测）+launch arg `hole_fill`+v7.1 运行时热更（5s 重读）。
- 逐帧登记：SDB-STAT 增 hole_fill 块（on/frames/hole_px_med/hole_px_max/fill_rate_med）。
- 单测 9/9（合成洞正确性/无洞 no-op/大洞不填/默认 OFF 逐位恒等/低视差丢弃）。

## 三次复测证据链（gate2A 系列；判读器已校准：同器 v6 基线=49.4% vs v6.2 官方 43.7% 同带）

| 次 | 状态 | plane-truth relmed | 近距 med | lat_wall p95 |
|---|---|---|---|---|
| r1 | teleport 位错事故（bag 保留 .badteleport） | — | — | — |
| r2 | hole_fill 未激活（launch-arg 传递断链，SDB-STAT hole_fill=null 铁证；bag .r2_noarg） | 2.09% ✓ | 49.2% | 41.5-47.9 |
| **r3** | **激活铁证 hole_fill={"on":true,frames=199,hole_px_med=10633,fill_rate_med=3.46%}** | **2.20% ✓ PASS** | **50.3%（GE60 ✗）** | **206ms（门 50 ✗ 爆表）** |

## 判决

1. **plane-truth 不劣化：PASS**（2.20% ≤ 5.29%，120 万点 57 帧；激活前后 2.09→2.20 无实质劣化）。
2. **近距 ≥60%：FAIL**——50.3% vs 基线 49.4%（+0.9pp=噪声级）。**机理定案：近距失效面主因=纹理门控 T8/w25 杀白静区（管线末端），非 SGBM 空洞**——填充作用于视差洞（SGBM 失配域），白静区像素即便填出正确深度仍被门控整格杀除。填充与失效面正交=零效果实证。
3. **延迟门：FAIL**——TELEA 大洞域实测成本 ~160ms（r2 41.5-47.9 → r3 206），p95≤50ms 门击穿 4 倍。近距 tag 场景洞面积中位 10633px=TELEA 最坏工况。
4. **处置：hole_fill 默认 false 收档**（v7 节点保留在仓，默认路径=v6 行为逐位一致，T4 单测+第二次采集 41.5-47.9 实测背书）；v9 全部批次 hole_fill=false。
5. **路 C 触发条件成立**（A 未过近距门）+路 B 条款判过在案（红线 20 已闭合）——近距几何门 60% 的唯一剩余路径=tag 白静区注入可匹配纹理（IR 投射器仿真）。

## 坑账（承月报）

- **N18 teleport 位=机体系原点非相机位**：第一稿滚转段把机体 teleport 到相机位 (1.13,1.005)→真 dZ=0.33 非 0.45；实测深度 0.318 与错误几何自洽（深度本身正确）——采集脚本位姿一律用机体原点（gate2j 惯例=机体不动）。
- **N19 launch arg→private param 传递断链（根因未定案）**：dump-params 验证 /stereo_depth_bridge/hole_fill: true 解析正确、launch 单处 node 无条件分支、脚本命令行正确——运行时节点却读到 False（SDB-STAT hole_fill=null 铁证）。修复=节点 v7.1 运行时热更（5s 重读）+起栈后 rosparam set 双保险（r3 激活铁证=热更路径有效）。根因（roslaunch arg 到达节点 get_param 的哪一环断的）未定案，如实注记。
- **N20 inpaint TELEA 大洞延迟陷阱**：>10⁴px 洞域 TELEA ~160ms/帧——实时管线禁用；离线处理可用。

## 指纹

- 节点 v7.1（含热更）：md5 abdd094a（仓内+bridge_pkg 双处一致）
- 采集/判读：gate2A_run.sh / gate2A_analyze.py（判读器几何校准 0.441 vs 官方 0.442 逐位带）
