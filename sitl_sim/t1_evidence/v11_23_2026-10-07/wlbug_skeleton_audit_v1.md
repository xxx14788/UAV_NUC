# wl-bug 同骨架排查清单 v1（T1 v11.23 阶段 4b；2026-10-07 13:1x）

## 坑定义（正源=x5 19:35 事故+judge_round 两代）
函数 `w()` 用 `tee -a $SUM` 往 stdout 写 → 调用点若在 `$( )` 捕获内，诊断多行被捕获变量吃掉
→ `case` 永落 fail（绿数/重试/撞门保护三失能；E8O/S8O 两 PASS 误判在案）。

## 扫描面与方法（扫描器=wlb_scan.py，615 文件）
- 域=sitl_sim 全域+catkin_ws/sitl_sim（跳过证据/bag 大目录）
- 交叉判定=「函数体含 tee」×「$() 或反引号捕获内调用该函数」双条件

## 结果：**零真命中**
- 唯一命中=x5_batch.sh `$(judge_round ...)` ——**误报**：judge_round 体内 "tee" 仅出现于
  修复注释文本（HOTFIX(19:35) 行），活代码=wl 文件化（`wl(){ echo ... >> "$SUM"; }`）
- x4_batch.sh（64f81b8 热修版）与 x5_batch.sh（"沿 x4_batch 修复版逐字"）双确认：
  judge_round 内诊断全走 wl 文件写，无 tee-stdout 活路径
- x5 的全局 w() 仍 tee（合法——批级诊断行主用），但无任何 $() 捕获调用点（扫描器交叉面为空）

## replay 类工具副作用清点（同窗件）
- j0d 批跑写 j0_decomp.json 入各 run 目录=设计输出（10-06 先例口径），零覆写其他产物 ✓
- CSV 收集器只读 wa_gate_online.json ✓（脚本已留档本目录 collect_xline_csv.py）
- 判读重跑路径=vins.log 尾行截断浮点崩（bee17577 零触碰，$() 面不涉）——已在 X7 §9 provenance 注记

## 回归
- bash -n x4_batch.sh/x5_batch.sh 语法面 ✓（扫描期顺检）
- 结论：骨架族无活实例，无需修复；x5 侧"沿修复版逐字"移植已生效
