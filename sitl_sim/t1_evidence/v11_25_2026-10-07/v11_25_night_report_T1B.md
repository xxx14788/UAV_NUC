# T1-B v11.25r2 夜报（2026-10-07 14:11-17:35；SITL 尾件+实机阶段 0 执行版·B 线）

> 双线并行：T1-A（14:06 线）=NUC 实机域（config 收敛 6f20eef+阶段 1，其域自报）；**T1-B（本线）=SITL 主线**。
> 分工握手 14:14（20min 无异议固化）；git 交错纪律遵守（本线四笔全推：033ba71→cca3286）。

## 双必达：✓✓ 全达成

1. **注入演练五案有果**（判据=drill_prereg_v1 冻结）：D2 教科书 PASS（+5m 注入→止损即时
   jump_m=5.0 逐位→17s disarm=1，止损在线首验销账）；D3 PASS（断流 30s 无失控 |v|1.09<1.5，
   恢复跳捕获→kill S3）；D4 PASS（planner 冻结 60s 仍绿收=F1 实证）；D1 FAIL/不安全（杀 VINS→
   盲飞悬停 z=2.43+disarm=0=H-A 活体实证）；D5 FAIL（监控 v0 三缺陷：起飞假阳+一次性聋+
   双发布器交错）。报告=drill_report_v1（5ada1d4c）。附 D0 对照轮+D1-boot 变体（init 门兜底）。
2. **M2 写码完成含 REGEN 冻结**：腿 B=t2_input_quality_gate（三键+staging+fail-open；
   gtest 7/7；栈 f622bae2/886b1e90）；腿 A=t1_scene_gate（selftest 10/10）；
   REGEN v1 冻结→v1.1 批前校准（stereo_r 0.3→0.10，烟测 587 帧实测带证据）。

## M3 批（阶段 3）=腿 B v1.1 参数集证伪（冻结语义执行，数字闭环）

- 18 轮格级双列全数字：毒格组 Δ+22.2pp（S12P/S8O 史首绿各 1/3；E8P 维持 0/3）vs
  绿格组 Δ-55.5pp（组绿率 44.4%<60.5% 线）→ **绿格退化成立=证伪 → config 回滚 054ddc8d（已复验）**。
- 机理钉死：N8P_2 REJECT 帧 stereo_r p50=0.08<0.10 阈——**双目配对率场景依赖**
  （obstacles 0.05-0.08 vs plain 0.16-0.28），plain 校准阈在 obstacles 域成饥饿阈
  （fail-open 周期 0.3Hz 馈电→N8P 到位 8.2/7.8m 失败）。
- 修复链闭环标准兑现（18 轮数字+机理分布落盘=非虚账）；后续=场景分带标定/K3 自适应，
  新参数集须重走预注册冻结→批。

## 4b HAFIX（D1 证据→落码→验证闭环）

- px4ctrl odom 死亡看门（0b581422）：梯=watch(5s)→AUTO_LAND 盲降→kill_s(15s)→KILL+disarm
  兜底；默认开=实机红线姿态；参数缺席=默认无需 yaml。
- **D1 复验 PASS**：watch t107.6→AUTO_LAND t112.6→KILL t127.6→**truth 末 z=0.10 落地**
  （对照原 D1 盲飞悬停 z=2.43 永不落+disarm=0）。
- 诚实注记：kill≠disarm 缺口未全闭（auto_disarm=0，电机停+落地=安全态 S3 达成）；
  盲降落点偏 goal ~2m（保命不保落点精度）。

## 其余交付

- 4c P3 契约设计件 v1（c9083356；代码面=下册）；4d 起飞前自检脚本 v0（CAL 带/odom 活/
  电压/链路一键 go/no-go）；
- 阶段 5：**口径 22 重建 v1**（D-1007-T1-04，用户授权语义）+五绿轮袋处置执行（判读产物
  保全）；X5 59 轮判读联表=**C.10 销号**（j0d_stats v3：风暴 84/中漂 54/净轮 47，19 轮
  由真实 t2fail 归位风暴）；C.2 绕过路径登记（D-1007-T1-05，低优先未执行）；
- X7 R10 联动=E5P gyro（昨日）；A 线域件（NUC 报告/config v0/硬件矩阵）归 A 线自账。

## 坑清单（本线新增）

1. 演练编排器 EV 检测三坑连环（mtime 竞态→marker 锚定；pursuit 前提活性校验；D5 预建
   目录幻影→/tmp+回拷）——全部热修入 t1_drill_run.sh（cca3286 版）
2. `pgrep -f <含自身命令串>` 自匹配自杀三次（d1_takeover/start_sitl 教训重复）——已第三次
   入册，远程命令禁含目标串字面
3. ROS_MASTER_URI 跨命令泄漏（回放专用 11399 泄漏给演练链→ENV-FAIL）——环境隔离纪律
4. git add 含不存在路径=整体不 add（两次）——逐路径核实铁律
5. 烟测 config 目录缺 cam 标定文件=相对路径空指针崩（cam0_calib 相对引用——整目录复制）
6. 我方脚本复刻晨间坑（set -u 先于 source ROS 链）——四件套前置模板已入 drill_run

## 残场与谱系

- 残场：进程/锁零残留（批毕+演练毕+teardown 全清）；df 528G；
- commit 链（本线）：033ba71（M2）→ cca3286（M3+HAFIX+口径22+P3+X5 联表）全推；
- 关键 md5：X7 f4e96bbd（A 线域内未动）｜REGEN+M3 终账=regen_prereg_v1_frozen.md（v1.1+M3 节）｜
  HAFIX px4ctrl 0b581422｜VINS 栈 f622bae2/886b1e90｜SITL config 复验 054ddc8d。

## 下册移交（客观）

1. INPUTFACE-SCREEN 后续：场景分带标定设计+新参数集预注册→M3'（禁直接再试）；
2. P3 生产/消费侧落码；监控 v1（相位感知+重复告警+单发布器接管语义）——D5 必修③；
3. kill≠disarm 缺口闭合（HAFIX 梯②后 disarm 确认/重试）；
4. HAFIX 参数实机化复标（dead_s/kill_s 对实机 d435 时延域）+演练五案实机版（规划册 M1 门）；
5. E8P 族（E×plain）在腿 B 下仍 0/3——该族修复面=前端筛查深化或场景分门硬隔离。
