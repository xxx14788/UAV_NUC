# T3 v9.9 单元 6 池件笔记（2026-10-06 04:3x）

## P14 核销：X4 录制模式（带图）
- 证据：批轮实读 run_X2g4_030233/flight.bag=10.3G、run_X3l2a_031040=14.5G（带图量级；
  对照紧凑轮 VRG1=52M/VRFY1=86M）——批已按带图录制。**核销**（X4 五轮袋保全至 X7 出稿后
  按口径 22 处置 @T4 维持）。
- 注：磁盘影响=5 轮×10-15G≈50-75G（df 593G 余量足）。

## P16 初判：静默大发散 cf 层归类（@T2 单元 2 交叉件）
- 标本 j0d（bee17577 全库批跑）：BL7 j0_total=64.1（jump 21.4+transit 46.1，njf=178，
  transit 主导）/BL9=7.75（jump 4.0+transit 5.9，njf=163，mixed）/对照 BL5=0.664
  （jump 0.018+transit 0.65，njf=6，transit 98%——干净标本）。
- cf 层证据：BL7 simvins **0 FAILURE 帧/0 failure detection**；init 期 t=11s |Bas|=0.0416/
  |Bgs|=0.0086（健康量级）→ **非 R13 CauchyLoss-NaN 链**（NaN 链实证=1051 FAILURE 帧+
  INITIAL 111/111 NaN cost，BL7 无此面）。
- **归类初判**：静默大发散=「亚阈值跳变 churn+transit 慢淋」复合形态（njf 163-178 次小跳
  无一过 0.5 门，累计 21m jump+46m transit），cf 层性质=后置门状态有限性盲区的**非 NaN
  显型**（cost 全程有限，ratio 门永不含 10x streak）——与 R13 同盲区家族、不同显型。
- @T2 单元 2 交叉面：T2 C.1 定案的"门只查状态有限性"盲区表述可扩写为"有限性盲区两显型
  （NaN 型=R13/churn-慢淋型=P16）"；判读面 j0d 三列已可分离两型（njf+jump/transit 分量）。
- 状态：初判在册，终判归 @T2 单元 2（本件为判读域供材）。

## P19 初查：BL 系 goal UTM 溯源
- 实读：BL 系 goal.txt=「7 -4 1」（X 线①位形，prereg §X2 表正源）；sim 链=纯 ENU 局部系
  （VINS 路径无 GPS/UTM 变换任何环节，纯视觉无 GPS 红线一致）。
- 若池件原意=goal 数值来源：溯源到 prereg X2g1 位形定义；若原意涉实机 UTM 坐标域：
  本仓 sim 域无此链，需池件发起方澄清。**初查在册，挂澄清**。

## hover j0 带宽
- @T2 单元 6 素材未到（RA12hov/RA5hover/RA17hov/RA23hov j0d 已在 §6 统计表：0.085/0.232，
  hover 带宽=供 T2 并表）——等待登记 W-T2u6。
