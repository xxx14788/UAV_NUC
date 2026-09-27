# W4 验证(2026-09-27)
- relay(depth_caminfo_relay)已挂 run_planner_sitl.launch;与 gazebo 静默发布者并存
  (rostopic info 显示两 publisher,gazebo 侧零消息不冲突)。
- 实测:depth/camera_info ~10Hz(min 0/max 105ms,window 60)≥9Hz ✓
- K 与 rgb 逐位一致:fx=fy=454.6857718666893, cx=424.5, cy=240.5 ✓
- grid_map 不订阅 camera_info(内参来自 advanced_param_sitl.xml),relay 对其透明;
  回归判据=带 relay 的全链冒烟(等锁执行,结果补记)。

## v2(2026-09-27 晚,最终方案)

- v1(订阅 rgb camera_info 合成)实测引发灾难:v1 的 rgb_info 订阅会激活 openni 的 RGB
  相机渲染,Xvfb llvmpipe 软件渲染下双流饱和 → 深度流饿死 → grid_map 空图 →
  直线穿箱(=smoke5/6 FAIL 根因,T3 18:29 独立确证)。**教训:headless SITL 里任何
  "订阅即激活渲染"的相机话题都是全局负载开关。**
- v2 设计:只订阅 depth/image_raw,内参全部来自参数(launch 同源 fx/fy/cx/cy),
  零额外渲染激活。K 与 rgb 逐位一致(同源数值)。
- 回归:relay v2 挂载冒烟(等 T3 V2d 完成后执行,结果补记)。

## 回归认证结论(2026-09-27 深夜)

傍晚(18:00 后)所有飞行轮(含 T3 无 relay 的 V2 系列、我 HEAD 栈 relay v2 轮)均出现
grid_map 间歇致盲(出图风险/穿箱签名),与 relay 无关(T3 的 relay-off 轮同样致盲);
Xvfb 重启未治愈。当日 50+ 次 gazebo/渲染重启后的环境退化,根因未定(候选:llvmpipe/
gazebo 相机插件状态累积污染),移交次日清洁会话(NUC 重启后)做 relay v2 挂载回归认证。
relay v2 本身功能验证已完成(10Hz/K 逐位一致/零 rgb 订阅零渲染激活),launch 挂载保持启用。

## U5 全飞认证(2026-09-28 02:1x-02:3x,磁根治后干净环境)

轮A(relay off):run_021048(T1)+run_021257(T3 并行轮)双 PASS 六指标全绿。
轮B(relay on v3 独立话题):run_023213 + run_023658 双 PASS(arrival 0.225/0.231,
min_dist 0.525/0.358,poscmd 99.8-100.2Hz,yaw -0.45/-0.57°,depth 13.2Hz)。
B1(021506)/B2(021949)的 arrival FAIL(stable_n=0 末端震荡)归因=多 agent 争抢污染
(与 T3 P0/T2b chain 时窗重叠;同代码排他窗 B4/B5 对照 PASS)。
B3(022428)环境事故(px4ctrl 被同名节点顶掉)无效。
smoke 六指标固化:smoke_probe.py(--yaw/--depthhz),RELAY_ON=1 透传。
W4 认证完成;按任务书不打 tag。
