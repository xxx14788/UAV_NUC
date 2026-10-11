# HAFIX 终验批 v11.40 终判表 (20 轮, B-7 参数化: 场景/轮数自日志推导)
- 预注册判据: 每轮 HAFIX_lines>=1 ∧ landed=1 | S4 边界解读(v11.40 预注册): hafix=0 ∧ landed=1 → SILENT-OK(正确静默)
- 场景 PASS=实际轮数全 {PASS,SILENT-OK} ∧ ≥1 机制轮 | 批 PASS=全部场景 PASS
- 终判: 17/20 PASS; SILENT-OK 2; KILL 路径 0 轮 / 落地路径 16 轮
- 首轮 cmd400 毒化观察(检查单#2): S1 r1 ring3=None
- FC reboot 副作用(检查单#3): p3_reboot_evt 总计=0
- KILL FAIL 行(若>0=FC 拒绝面,逐轮看 result 码): 0 轮
- CSV: /home/ghj/sitl_sim/t1_evidence/v11_40_2026-10-10/hafix_finalverify/verdict_v1140.csv
  S1_hover_1m: PASS 5 / SILENT-OK 0 / 其他 0 (共 5) -> PASS
  S2_hover_3m: PASS 5 / SILENT-OK 0 / 其他 0 (共 5) -> PASS
  S3_transit: PASS 5 / SILENT-OK 0 / 其他 0 (共 5) -> PASS
  S4_land_1m: PASS 2 / SILENT-OK 2 / 其他 1 (共 5) -> NOT-PASS
- 批终判: NOT-PASS
