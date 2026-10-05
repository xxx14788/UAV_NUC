# gates 臂验证轮预注册 v1（T1 v11.9 单元 1.2；冻结先于飞行；判据未预注册不出 PASS-FAIL）

> 背景：用户 2026-10-06 晨处置②——现场重启 3090 后验证机器态；恢复→原口径 gates+guard 飞 X4；
> 仍风暴→嫌疑收敛 gates 键本身，STATUS 待用户重裁禁私飞。
> 对照基线：晨间（10-05 13:xx，重启前）RA13/14 同臂（gates+guard+cauchy4.0）干净
> （T2fail=0）；当晚（22:00 重启后）同臂 4/4 风暴（T2fail 52-216，cost 门全打地面 init 段）。
> 验证轮构型=X2③ 型（goal 8,-1,1/budget 180/world obstacles）；栈=b7de133d+59548c6a；
> 臂=arm_xline.sh 装载（10 键 cauchy=0.0，banner [T2SGCFG] guard=1 sane_p=50 sane_v=15）。

## 判据（冻结）

- **V-J1 起飞建立**：轮次非 never-flew（truth z 离地门通过，轮完成至降落段）。
- **V-J2 地面段零误触发**：起飞建立前（arm→truth z>0.3m 窗）simvins.log 零 "cost gate: streak" 行。
- **V-J3 VINS 域健康**：全轮 T2fail=0（wa_gate vins=✓；对照 RA13/14 态）。
- **判定**：
  - **干净轮** = V-J1 ∧ V-J2 ∧ V-J3。
  - **风暴轮** = never-flew ∨ T2fail≥3（对照当晚风暴带 52-216，中间值 1-2=边缘如实注记单判）。
  - **机器态恢复** = 两轮均"干净"→按处置①②走单元 3 原口径冲刺。
  - **仍风暴** = 任一轮"风暴"（或两轮合计含 1 个风暴+1 个非干净）→嫌疑收敛 gates 键×机器态
    耦合→STATUS 待用户重裁行（附证据包：当晚四轮+验证轮对照表），X4 冻结禁私飞。
- 附带消费：VRFY2 挂 P2-A（p2_cmdresp/enabled=true）——若 VRFY2 干净且 j0<0.5∧njf=0，
  即顺带满足 P2-A 严格净轮版（零 latch 断言同判）；P2 零行为面（净轮无 divergence 事件）。
