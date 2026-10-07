# T1 v11.23 夜报（2026-10-07 11:38-14:1x；单线承接·SITL 收官整合版）

## 双必达：✓✓ 全达成（硬底线 04:15 前完成，余量 ~14h）

1. **X7 终稿出稿**：同名去 _DRAFT（md5 a025d5e3 三处一致）+git 提交 247dc7f 推送。
   七槽销号（§2 续飞如实注记/§3 九轮逐轮表/§4-bis 无门批 5/5+tag 双链/§5 引尾节/
   §6 CI+j0d v2 扩切口 185/§7.10 综合陈述/§9 figs1-5 终版+fig6 正源注记）；
   R12 终措辞=输入面分支；R2/A2 状态刷新；R10 回挖位填行（E5P gyro，追加 commit e6e5544 后 X7=f4e96bbd）。
2. **1e 裁决有果=输入面实锤**（2/2×双标本，判据=设计件 §3 冻结逐字）：
   E8P=在线全部 11 个 >5m 巨跳同刻（±2s）同幅值带（多重逐位 55.0↔55.0）+重 init 后段
   逐位一致；HVNET1=悬停慢漂 2/2 确定性复现（终态差 1-2.4%，轨迹 p50 9mm）；
   j0d 前置：E8P=mixed(njf409)/HVNET1=transit 90%（判别价值降级如实注记）。
   机理两面=输入扣扳机+估计器定弹道（r1↔r2 分支 10/28 bin 差）。
   verdict_v1.md（c2d75688）+预授权首件=INPUTFACE-SCREEN 立项书（58a4a027）。

## 保底清单九件对账

| # | 件 | 状态 |
|---|---|---|
| ① | 1e 裁决文书 | ✓ verdict_v1（输入面实锤） |
| ② | X4 九轮 j0d+分型扩表 | ✓ 五绿全 njf=0；S12P"B 型跳"=transit 主导勘误；X7 §3 表 |
| ③ | X7 终稿 | ✓ 247dc7f+R10 追加 e6e5544（f4e96bbd） |
| ④ | 止损件代码+验证 | ✓ t1_stoploss_watch v1.0（selftest 6/6+7 例 replay 定位复现：5 触发含 E8P 逐位+2 慢漂不触发=设计边界）+vins_smoke --stoploss 挂点（5cd4bd0） |
| ⑤ | wl-bug 排查清单 | ✓ 615 文件扫描零真命中（唯一命中=修复注释误报；x4/x5 双确认 wl 文件化在位）wlbug_skeleton_audit_v1（34c40a82） |
| ⑥ | 悬停 8.5m 最后通牒 | ✓ 指针在案=NUC bags/t2v3_hover_130226.bag（68M/md5 7e3d56f1）+判读文 v10 目录（t4_proxy_hover85_ultimatum_answer 06c69fc9） |
| ⑦ | 预授权行动链首件 | ✓ 立项文书+设计件+预注册初稿（e1_inputface_project_v1）+DECISION_LOG 里程碑开行 |
| ⑧ | 实机安全盘点件 | ✓ realmachine_safety_audit_v1（1a475cf4）：6a H-A 升格=实机前阻塞项+6b G1-G3×P1-P3 对账+6c 注入演练四案+6d 原则登记 |
| ⑨ | STATUS 诚实夜报 | ✓ 本件+STATUS 行 |

## 阶段 4 工程件

- 4a 止损 ✓（上）；4b ✓；4c rtf 探针常态化 ✓（移出 GATE 块，--no-gate 亦挂载）；
- 4d starve 评估 ✓（a1ce23df）：execFSM timer 本体无缺陷；冻结载体=waypointCallback
  spinOnce 循环 sim 时钟永眠主嫌（H-s1）；**高风险分支=维持重启绕行**，修复案文本化
  （WallDuration+循环上界+重入门），落码窗=INPUTFACE M2 合并+注入验证。
- 4e E5P gyro ✓（bfed27bf）：CAL_GYRO0_ZOFF=-0.0403rad/s（2.3°/s 假偏航率，40×）入
  EKF2 链=实机 preflight 检查项；VINS data_raw 阻断非该轮因果（380× 分离）。X7 R10 已注记。
- 4f 栈资产清点 ✓（6f351d2a）：vins 721cad40/5bacc2e9+config 双态（arm 054ddc8d vs
  canonical 5c98dc0d=git HEAD，工作树 M 未提交=设计态）+工具链 11 件 md5 谱系。

## 阶段 5 T4 代持收货

- 两档收清单 ✓（30a4debd）；两 1e 标本袋保全标记 ✓（PRESERVE_DO_NOT_DELETE.md）；
- **处置未执行**（代持裁定如实）：口径 22 原文 3090 未定位+df 527G 零腾位压力+锚表 v3
  删除纪律→移交 @T4 自裁；verdicts 三节+E4 帧级复核=在途移交注记（IO 错峰，X7 不受阻）。

## 科学增量（本夜三件）

1. **1e 输入面实锤**（跳变触发层=输入内容锚定；重 init 段逐位一致=确定性复现最强形态）
2. **S12P"B 型跳"微观形态勘误**（j0d=transit 慢淋主导 4.42m，非帧跳）+悬停谱系定案
   （hover 自跳 5/8-6/9 与导航同族，"悬停=安全格"直觉数据否证 d07fcd60）
3. **统计扩切口 113→185**（X4 9+X5 59 并表+CAMPAIGN_ARM 映射；净轮 48/中漂移 72/风暴 65）

## 坑清单（本夜新增，全在 DECISION_LOG/文书注记）

1. t3_replay.sh set -u 撞 ROS 链（调用侧预置 ROS_DISTRO/MASTER_URI/ROS_VERSION/ROS_PACKAGE_PATH 四件套）
2. 判读器 vins.log 尾行截断浮点崩（bee17577 零触碰；CSV 走 wa_gate_online.json 正源收集器）
3. 中文 sed 经 ssh 偶发乱码（一律走 python UTF-8 或 scp 通道）
4. python 补丁字符串前缀替换吞行（pursuit 前缀吞 pursuit-start——行锚定 re.M 修复，从 catkin 正源恢复重打）
5. git add 含不存在路径=整体不 add（逐路径核实后重提）

## 残场

- 进程零残留/锁零残留；df 527G→~440G（1e 回放产物 4×~100M+figs+统计，两 13G 标本袋保全未动）；
- git：三笔全推（247dc7f→5cd4bd0→e6e5544）+收工笔随发；config 臂态 M=设计态（4f 在册）。

## 明日交接（总设计师域）

- 实机迁移规划首件输入=安全盘点件（6a 阻塞项+6c 注入演练+6d 原则）+栈资产清点（4f）；
- INPUTFACE-SCREEN 修复链跨夜里程碑（M2 写码+M3 绿率复测≥10 轮）；
- X4 袋处置待口径 22 原文（@T4）；悬停 8.5m 证据包单副本注记（NUC 68M，@T4 自裁镜像）。
