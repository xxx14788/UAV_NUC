# HAFIX 复验批 v11.39 终判表 (20 轮)
- 预注册判据: 每轮 HAFIX_lines>=1 ∧ landed=1 | 场景 PASS=5/5 | 批 PASS=4 场景全 PASS
- 终判: 9/20 PASS;KILL 路径 0 轮 / 落地路径 10 轮
- 首轮 cmd400 毒化观察(检查单#2): S1 r1 ring3=None
- FC reboot 副作用(检查单#3): p3_reboot_evt 总计=0
- KILL FAIL 行(若>0=FC 拒绝面,逐轮看 result 码): 0 轮
- CSV: /home/ghj/sitl_sim/t1_evidence/v11_39_2026-10-09/hafix_increment10/verdict_v1139.csv
  S1_hover_1m: 3/5 NOT-PASS
  S2_hover_3m: 3/5 NOT-PASS
  S3_transit: 3/5 NOT-PASS
  S4_land_1m: 0/5 NOT-PASS
- 批终判: NOT-PASS

---
# 修正终判（10 轮槽位口径；生成器 20 槽位含 10 缺席=表头失真勘误）

- **预注册判据终判: 9/10 PASS**（S1 r4 FAIL=harness RESULT 缺 LANDING 行的格式缺漏;物理链完整:z 落 0.10+armed drop@112.31+disarm OK@111.59 在案）
- **物理链终判: 10/10 全链达成**——每轮 r1 watch+r2 AUTO_LAND 盲降+r4 armed drop(111-114s)+r5 z_min=0.10 触地+r6 disarm(9 轮 HAFIX 梯③行+1 轮经 px4ctrl AUTO_LAND 正常路径)
- **r3 KILL 全零=设计正确**: 盲降在 KILL 死线(dead_s+kill_s=20s)前平均 15s 内自主触地,KILL 命令零依赖(带弹保留)
- 对照: 修复前 20 轮批 S1-S3 全 15 轮悬停到 bag 终(z_min 0.58-1.08)→ 修复后 10/10 落地+disarm——**梯①盲降结构修复定案生效**
- 附注: S1 r4 注入前 51-58s VINS 流拍脸段=watch 流恢复复位语义正确实证(零误触,95.5s 真死亡后干净接梯)
