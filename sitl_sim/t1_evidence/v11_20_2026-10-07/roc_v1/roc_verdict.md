# ROC v1 判决(T1 v11.20 单元2;引擎同核重放)

```
{
 "question": "绿格11零误拦 ∧ 巨跳6全触发 — 工作点存在?",
 "grid_points": 64,
 "operating_points": 0,
 "max_jumps_at_zero_false": 2,
 "min_greens_false_at_6catch": 6,
 "corner_note": "零误拦域内最大捕获=2/6;捕获6/6所需最小绿误拦=6/11 → 两端互斥,无工作点",
 "verdict": "门不可靠(零工作点;预注册分支:禁上真轮作绿率提升器→无门基线支)",
 "engine": "t1_gate_watch.run_eval 同核(replay 模式);与T2 gate_science_report §1.2/1.3(自适应lift面+surge面)结论一致=双线独立互证",
 "grid": "adapt cost_ratio×bas_ratio {1.5..50}, sustain=5s, OR组合"
}
```

灵敏度全表=sensitivity.tsv;pregate 面=pregate_roc.tsv(绿格 init_final_cost 跨 366-10999=绝对阈值不可行;E8P_224044 反例与 T2 §2 一致:起飞前门不成立)。
双线互证:T2 六面检验(科学包)+T1 同核 ROC(本件)=门对巨跳族无判别力,预注册无门基线分支生效。
