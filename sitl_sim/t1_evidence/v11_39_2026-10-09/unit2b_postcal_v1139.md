# 2b 校准后参数复测对照（T1 v11.39；2026-10-10 05:2x）

> 环境：旧机栈=2a 复苏版（realmachine_2a_reboot_stack.sh，IMU 默认 50Hz——203Hz 行 [10-10 停用] 注记在正源脚本，遵照）；
> FC=Auterion PX4 FMU v6C.x（lsusb 实证）；固件=**v1.17.0**（Flight software 011100ff，mavros VER banner 05:19 实测）。

## 复测对照表（自检脚本 v1 复跑=preflight_v1_postcal_20261010.txt 正源）

| 项 | 重校前基线（v11.34 件） | 重校后实测 | 判定 |
|---|---|---|---|
| CAL_GYRO0 X/Y/ZOFF | —（旧值未记录对照） | -0.00236/+0.00110/-0.00071 | **PASS**（|v|<0.005 带） |
| CAL_ACC0_XOFF | 0.0089 | **-0.2409** | 变化 0.2498（重校写入） |
| CAL_ACC0_YOFF | **-0.2583** | **+0.2808** | 变化 0.5391（**翻号级**=真重校非复写） |
| CAL_ACC0_ZOFF | -0.0925 | +0.2214 | 变化 0.3139 |
| CAL_MAG0_XOFF | 0（未校准态） | **0.4066** | 磁校写入实证（Y -0.0171/Z +0.1257） |
| battery_voltage | —（实弹 15.9V @v11.34） | **0.0V（未插电池，FC USB 供电态）** | 免测注记（用户裁定：插电池免测；首飞前插电池后复核） |
| mavros_link | True | connected=True | PASS |
| odom_stream | — | 15.0Hz 有限 | PASS（VINS 复苏健康：|Bas|0.124/track146） |
| 自检终判 | — | **NO-GO（唯一 FAIL=battery 0.0=免测项）** | 电池插上后复核即转净面 |

## 硬件矩阵台账行（入 M1 行 2/3 注记）

- FC=Auterion PX4 FMU v6C.x / 固件 v1.17.0（011100ff, d6f12ad1）/ MAVLink 集 2025.5.5
- 与 SITL PX4 版本差异如实注记不升级（SITL=PX4-Autopilot 本地 build，版本差异在册）
- ACC/Y 翻号级重校=QGC 全传感器校准真写入（非参数复写）；mag 首次非零=磁校完成

## 遗留

- G-1（低优先，任务书 M1 行 8 注记）：本轮未做 strace 侧参数写回链核查——2b 同窗注记维持
- 首飞前电池插上后 preflight v1 复跑一次（预期 NO-GO→GO）
