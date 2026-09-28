# 实飞检查单（Pixhawk 6C mini + NUC 实机链路）

> 适用: 实机首飞及每次实飞前。链路 = FC(921600 串口) → mavros → VINS(/mavros/imu/data_raw)。
> 由来: 2026-09-28 IMU 250Hz 定案（SITL 探针实证 50/125Hz 两层根因后，两侧统一名义 250Hz）。

## A. 固件与参数台账（首次连接 / 每次刷固件后）

1. 固件版本确认（**2026-09-28 已知缺口: 实机固件版本无任何记录**，首连必补）：
   ```bash
   rosrun mavros mavsys info        # 记录 autopilot 类型 / 版本 / git hash
   ```
   填入文末台账。若与源码树 ~/PX4-Autopilot (v1.17.0-dirty, 仅 SITL 资产改动) 不一致，不阻塞飞行，
   但 IMU 相关参数行为以实机固件为准复核一遍本单。
2. IMU_INTEG_RATE 必须 = 250（一次性设置，BMI055 陀螺 2000Hz ODR，2000÷8 整数分频出精确 250Hz）：
   ```bash
   rosrun mavros mavparam get IMU_INTEG_RATE
   # 若非 250:
   rosrun mavros mavparam set IMU_INTEG_RATE 250
   rosrun mavros mavparam save          # 磁参数必须 save 才持久（T1 v4 教训）
   # 然后重启飞控
   ```

## B. IMU 250Hz 三步检查（每次起飞前）

1. 提频应用（mavros_with_imu_rate.launch / full_vins_px4.launch 已内置，无需手动）：
   ```bash
   rosrun mavros mavcmd long 511 105 4000 0 0 0 0 0
   ```
2. 频率验证（**红线: ≥200Hz 才飞；期望 250.0±0.5**）：
   ```bash
   rostopic hz /mavros/imu/data_raw
   ```
   - ~250Hz = 正常
   - ~125Hz = 提频命令误配回 5000（lockstep 网格量化仅 SITL 有，实机出现此值=命令没吃上，重发）
   - ~50Hz = 511 从未生效（检查 mavros connected 与命令出口）
3. SITL 参考值 ~223Hz（同架构 sim 上限，lockstep 传输批量化所致，非缺陷）。sim 数字不作为实机判据。

## C. 关联纪律

- SITL 动过的 PX4 参数（MAG_TYPE/SDLOG 等）一律不同步实机（README R5）。
- 磁参数写回必须 param save（否则重启丢失）。
- 纯视觉架构红线: 无 GPS，定位层走 VINS；GPS 链路仅流程验证用。

## D. 台账

| 日期 | 固件版本(mavsys info) | IMU_INTEG_RATE | 实测 /mavros/imu/data_raw | 备注 |
|------|----------------------|----------------|---------------------------|------|
| 待填 | 待首连确认（源码树=v1.17.0-dirty，实机固件来源未记录） | 待设 250 | — | 2026-09-28 建单 |
