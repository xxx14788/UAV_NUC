# P-N1 已删锚袋判读面资产 md5 固化台账（run_WC2OBS1_030927 / run_WC2OBS1_032005）

- 池件：T4 视觉验收线 P-N1（2026-10-05 晨批，0 锁纯文本/固化件批）
- 红线声明：本台账只含清点/固化/核对陈述，零判读语义；未触碰 verdicts 正本。
- 背景事实：两源袋 ~/sitl_sim/vins_smoke_runs/run_WC2OBS1_030927/flight.bag 与 run_WC2OBS1_032005/flight.bag 已于 2026-10-04 腾位删除；本批实测 `test -e` 两路径均不存在（GONE/GONE）。三面判读资产保留在册，本台账对其逐件 md5 固化，防后续引用漂移。
- 固化件：同目录 `pn1_deleted_bag_asset_md5.csv`（表头 path,bytes,md5；数据行 289 行；33229 B；md5=9e5c68a9a18f64acb57d82eef5158b96）
- 固化执行：2026-10-05 晨（CSV 生成于远端 08:33，台账落盘 08:46 窗口；NUC uav4 远端时钟）
- 方法：python3 hashlib.md5 全量读算逐件计算（原样输出为准）；生成器为一次性工具未入册，复验可直接对 CSV 逐行重算比对。

## 面① 提帧目录（~/sitl_sim/vision_inputs/）

| 目录 | 文件数 | 构成 | manifest.json bytes | manifest.json md5 |
|---|---|---|---|---|
| WC2OBS1_030927_j3 | 140 | 139 帧 PNG + manifest.json（其他 0） | 26763 | 412d448e573640f28c103371b83b33f3 |
| WC2OBS1_032005_j3 | 139 | 138 帧 PNG + manifest.json（其他 0） | 26770 | dbba66998ef8aa6bc3718757d55759a7 |

逐帧文件数清点：139+138=277 帧 PNG，与两 manifest.json 全部逐件入 CSV face1 段。

## 面② metrics/fbres 同族 json（~/sitl_sim/vision_inputs/，8 件逐件）

| 文件 | bytes | md5 |
|---|---|---|
| metrics_WC2OBS1_030927.json | 69671 | ad1fb70b7e2bc124af574793f34468e9 |
| metrics_WC2OBS1_030927_density.json | 767 | 21e7055ac88edc6bcab28d80f368fce9 |
| metrics_WC2OBS1_030927_w3.json | 79974 | daa7154df6bb5f26f72eeb1968b545a7 |
| metrics_WC2OBS1_032005.json | 69253 | 467f8a13c1a614bf8e5f52d7e305701e |
| metrics_WC2OBS1_032005_density.json | 773 | c057d125cea93c9fab36b80a34adad02 |
| metrics_WC2OBS1_032005_w3.json | 79199 | bdd18d17a0594335a071763e9319818c |
| fbres_WC2OBS1_030927.json | 19369 | fe88115cadaa96d7919352062b064a1a |
| fbres_WC2OBS1_032005.json | 18962 | b8adf9ef4b6bc9749590b7d49dc0b168 |

## 面③ jr3_replay 特征包（2 件逐件，预期 bytes 核对）

| 文件 | bytes 实测 | bytes 预期 | 核对 | md5 |
|---|---|---|---|---|
| jr3_replay_WC2OBS1_030927/features.bag | 1164385 | 1164385 | PASS | 9c58292890a8db949e30939cf42e266a |
| jr3_replay_WC2OBS1_032005/features.bag | 2107784 | 2107784 | PASS | 19b4036548458d6447900806d9fd4e96 |

注：jr3_replay_WC2OBS1_0{30927,32005}/ 目录内伴随 play.log/record.log/roscore.log/vins.log 在盘，非本池件清单范围（清单范围=features.bag），未入 CSV。

## manifest 源袋字段引用面注记

- WC2OBS1_030927_j3/manifest.json 的 "bag" 字段 = /home/uav/sitl_sim/vins_smoke_runs/run_WC2OBS1_030927/flight.bag
- WC2OBS1_032005_j3/manifest.json 的 "bag" 字段 = /home/uav/sitl_sim/vins_smoke_runs/run_WC2OBS1_032005/flight.bag
- 实测（2026-10-05 晨）：上述两路径均不存在（已删源袋），与 10-04 腾位删除背景一致；manifest 为固化资产本体、纯文本引用面，字段原样保留不改；后续引用以本台账三面逐件 md5 为准。

## 核对声明

1. 固化计数：共 289 件 = 面① 279（140+139，含 2 manifest）+ 面② 8 + 面③ 2；MISSING=0。
2. 面③两件 bytes 与池件预期值（1164385B / 2107784B）逐件核对一致（PASS/PASS）。
3. CSV 与本台账同源（同一轮 python3 计算产出）；CSV md5 已登记于本文首部，可随时重算复验。
