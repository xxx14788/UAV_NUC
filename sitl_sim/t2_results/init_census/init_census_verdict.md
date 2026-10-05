# 单元 3 定案文书 — init 分布审计（A1 疑点）

**T2 v9.8 单元 3 | 2026-10-06 | 数据: init_census_3090.tsv + init_census_nuc.tsv（双机全库 220 行,去重 144 轮）**
口径: init 时间=首次 "Initialization finish!" 的 sim 时钟; multi-init=init finish 计数; banner 键=T2 knobs/T2RFIXCFG/T2SGCFG 实际生效值。

## 1. init 时间全谱（A1 主问）

**去重 144 轮,init-ok 137 轮: p50=10.6s, 带宽 9.4-12.2s, 无任何轮 >30s。**

- 任务书引例口径勘定: "3s[T2M0]/53s[手工]/102s[VRFY1]" 三数**均非 init finish 时间**——T2M0 实测 init 1 次正常（全谱带内）; VRFY1 首次 init@10.16s（其"102s"疑为 odom 判读面或其他事件口径）。**init 在输入正常时是确定性事件: 11 帧窗口×~0.1s 帧距+首帧等待 ≈10.6s,离散度 σ<0.5s**。
- 结构含义: stereo+IMU init 无"慢收敛"形态——要么 ~10.6s 完成,要么环境级根本不发生（见 §2）。

## 2. never-init 逐例解剖（3/3 环境级,零估计器失败）

| 轮 | 死因 | 层级 |
|---|---|---|
| T2ZETACTRL_133959 | config_file 路径不存在 → FATAL BREAKPOINT（parameters.cpp） | 启动失败 |
| WD1_024016 | "waiting for image and imu..." 永久等待——无图像/IMU 输入流 | 数据面断流 |
| X1_223836 | "cannot launch node of type [vins/vins_node]"——节点未起 | 启动失败 |

**全库不存在"估计器 init 逻辑失败"案例**——init 逻辑在输入正常时 100% 完成。A1 疑点的"init 失败"疑点画像=环境级三件套（config 路径/输入流/节点启动）,与估计器质量无关。

## 3. multi-init 59 轮二分（init 质量真面）

| 族 | 轮数 | 形态 | 定案 |
|---|---|---|---|
| 毒配置风暴 | 6（ARMCHK/SUPHV2a/SUPHV2b/SUPX2a/SUPX2b/VRFY1,init_n=35-216） | INITIAL NaN→cost gate 假触发 reboot 循环 | **C.1 已定案（CauchyLoss(0)）**,本审计提供全库印证: 风暴轮=毒配置轮 6/6 一一对应,无散例 |
| 环境型 | 53（BL 系 never-flew 2-15 次 / F3 系瞬态发散 2-19 次 / MACH·RA 系 route 空中 2-3 次） | 空中瞬态发散→failureDetection/insane 重 init | route/flight 轮 init_n p50=2 vs ground/hover 全 1——**飞行剖面重 init=常态,非病**（与 C-域"route 急冻/瞬态发散"既有定案同源） |

## 4. cauchy/gates 键×init 关联检验（"cauchy 拖慢收敛"假说）

单次 init 轮按臂键分组:

| 组 | n | init p50 | init p90 | max |
|---|---|---|---|---|
| loss=0,cauchy=4.00 | 63 | 10.7s | 11.2s | 11.5s |
| loss=1,cauchy=4.00 | 29 | 10.6s | 11.1s | 11.6s |
| loss=0,cauchy=0.00* | 6 | 10.5s | — | 10.5s |

*loss=0 下 cauchy 值无效应（HuberLoss 路径）。

**假说否证**: cauchy loss 对 init 时间零效应（组间差 0.1s ≪ 带内离散）。机理同源: stereo+IMU init 的首轮求解中残差尚未积累厚尾,CauchyLoss(4) 与 Huber 在此尺度不可分——与 §1 的确定性 ~10.6s 互证。

## 5. 场景关联（地面视差/IMU 激励）

| 场景 | n | init p50 | init_n p50/max | never-flew |
|---|---|---|---|---|
| ground | 3 | 10.5s | 1 / 1 | 0 |
| hover | 4 | 10.6s | 1 / 1 | 0 |
| route/flight | 63 | 10.5s | 2 / 216 | 11 |

**地面视差不足不构成 init 障碍**（gnd/hov 全一次过——stereo 深度独立于平台运动视差,运动模型深度（motion2）虽病态（init_neg 28-36%）但不阻塞 stereo+IMU init 路径）。IMU 激励在 gnd/hov≈0 同样不阻塞（solGyroscopeBias 用近零激励仍收敛到 sane Bgs）。

## 6. 勘误件（@T1）

**DIAGCAUCHY_231757 非 never-init**: 实测 init@9.55s 成功、INITIAL cost 2906→622 健康、NON_LINEAR 全程稳定收敛（cost 1161→70,0 NaN/0 reboot/0 insane）、T2fail=0。死因=**中途 34.289m VINS 帧跳变（anchor 判读"T2 瞬态发散类"）→到位 FAIL**。boot_diff_report §6 表该行判读应更正为"瞬态发散型 FAIL"——其"v4 栈 cauchy=4.00 never-init"的栈代×cauchy4×boot confound（§7 残留）随之**不存在**,never-init 残线整体销案（§2: 3/3 环境级）。

## 7. 数据包

init_census_3090.tsv/init_census_nuc.tsv + 本文书; 普查脚本 init_census.sh。双机重复轮（~77 个 rsync 副本）已去重处理,去重口径=轮名（NUC 副本与 3090 正本逐字节同源,history 在案）。
