# E-4 栈号跟随机制预设计（T1 v11.0 深挖池⑥；2026-10-04 03:0x）

## 问题

判读凭据栈号（vins_node/libvins_lib 双 md5）随 T2 fixface 换代滚动（fixface-2 d43504d9→fixface-3 e7044319/08a46d0a）；E-4 型判读的"栈号登记"当前为**判读文手工补记**（e4r2_verdict 头部"栈=lib d43504d9+node 4701bd3a"）——判读与实际飞行栈的对齐依赖人工，跨栈代对比（如 F3B vs R8）需要回溯推断。已知坑：R4 judge JSON ulg 字段错记=同类"凭据错记"族。

## 机制设计（预注册，harness 改动挂协调窗）

1. **自动落盘**：sitl_smoke（或 01/03 启动脚本）在 SITL/mavros 就绪后、起飞前，dump 双 md5 到 run 目录 `stack_md5.txt`：
   ```
   date=<UTC>; vins_node=<md5>; libvins_lib=<md5>; px4ctrl_node=<md5>; vins_to_mavros=<md5>
   ```
   （px4ctrl/vins_to_mavros 一并登记——F3/P1/U2.7 后 px4ctrl 二进制也成判读变量）
2. **判读强制读取**：e4_judge/round_result 判读器开头读 stack_md5.txt；缺文件=判读降级（WARN+判读文标注"栈号缺失"）——红线"每轮重放登记双 md5"的机器化。
3. **换代对账**：T2 fixface 换代通告后，首轮跑完自动比对 stack_md5.txt vs 通告值——不一致=STATUS 告警（防"源码改了没 build"型栈错位，本会话 R3x/w2b A 路的 unbuilt 状态即此类面）。
4. **跨栈代对比规范**：判读文头部栈号段自动生成（替代手工），A/B 对比跨栈时强制注记（F3B 案例的做法固化为机制）。

## 实施挂点与协调

- 改动面=sitl_smoke.sh（共享 harness）+判读器（T1 域 e4_judge/round_result=T3 权域）——**双副本同步纪律+@T3 @T4 通告后进窗**；本稿先入池为预设计（不动码）。
- 收益账：判读凭据错记族（ulg 字段/栈号手工）两类坑一次收口；F3/P1 验收轮的 px4ctrl md5 登记同步解决。
