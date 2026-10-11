# HAFIX 终验批 v11.40 批前环境检查单（工程合并册单元 2）
- 时间: 2026-10-11T00:35:15+08:00
- 1. P-3 强清生效验证: 批首强制清场一次(结果见 summary 首行);轮间 force_clean 逐轮断言
- 2. PID 文件单例守卫在役: /tmp/t1_reverify_batch.pid (v2=PID 文件方案,D-1010-T1-01 教训)
- 3. FC reboot 副作用清除: 代码无 246 路径(grep 见下)+运行面 p3_reboot_evt 判读器逐批计数(修复前复验批=3/修复后增量批=0)
- 4. 注入时序语义(v4 flying 门双门): S1-S3 稳定窗 15s / S4=40s;
   S4 边界解读预注册(v11.40 任务书原文): 落地后注入轮 hafix=0∧landed=1 → SILENT-OK(正确静默)禁误判 FAIL
   (修复前复验批 S4 r1/r3 形态;中段下降注入精度未达成=已知边界,预承 T1 B-1/C-6)
- 5. 栈二进制指纹(T2 C-7 跨批栈指纹不可追溯 补记):
   px4ctrl_node: 3af9de74e3d6c8a0be1c89da7a0ae25b
   vins_node:    cac140b0a17aa31d6199fd4f3fe24721
   libvins_lib:  80be3cf2f28ea97b37fd7769a208fb1d  /home/ghj/catkin_ws/devel/.private/vins/lib/libvins_lib.so
- 6. git HEAD: e0640e3
- 7. 对照基线: 修复前复验批 3/20(S1-S3 0/15 悬停不落+S4 3/5,r1/r3=落地后注入静默形态)
   / 增量批(梯①盲降二次修复) 10/10 物理链;本批=终验批(M1 行 5 终闭环)
390:		if (fd_o.reject) // LAND in CMD_CTRL — source :239-246, message kept verbatim
927:	// https://mavlink.io/en/messages/common.html, MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN(#246)
930:	reboot_srv.request.command = 246; // MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN
