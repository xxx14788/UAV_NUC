#!/usr/bin/env python3
# t1_c1_179_fields.py — C-1 分离轮 ulog 179 命令/ACK 全字段提取(工程合并 v1.6 单元1)
import sys
import numpy as np
from pyulog import ULog

u = ULog(sys.argv[1], None)
for name in ["vehicle_command", "vehicle_command_ack"]:
    for d in u.data_list:
        if d.name == name:
            t = d.data["timestamp"] / 1e6
            sel = d.data["command"] == 179
            print(f"== {name} (179 rows: {int(sel.sum())})")
            for i in np.where(sel)[0]:
                if name == "vehicle_command":
                    print(f" t={t[i]:.3f} cmd={d.data['command'][i]} p1={d.data['param1'][i]:.3f} "
                          f"p2={d.data['param2'][i]:.1f} p3={d.data['param3'][i]:.3f} "
                          f"tgt={d.data['target_system'][i]}/{d.data['target_component'][i]} "
                          f"src={d.data['source_system'][i]}/{d.data['source_component'][i]} "
                          f"ext={d.data['from_external'][i]}")
                else:
                    print(f" t={t[i]:.3f} cmd={d.data['command'][i]} result={d.data['result'][i]} "
                          f"tgt={d.data['target_system'][i]}/{d.data['target_component'][i]} "
                          f"ext={d.data['from_external'][i]}")
# 全部 vehicle_command 行(含非179, 看改写链上游)
for d in u.data_list:
    if d.name == "vehicle_command":
        t = d.data["timestamp"] / 1e6
        print("== all vehicle_command rows (t, cmd, src, tgt, ext):")
        for i in range(len(t)):
            print(f" t={t[i]:.3f} cmd={d.data['command'][i]} src={d.data['source_system'][i]}/{d.data['source_component'][i]} "
                  f"tgt={d.data['target_system'][i]}/{d.data['target_component'][i]} ext={d.data['from_external'][i]}")
