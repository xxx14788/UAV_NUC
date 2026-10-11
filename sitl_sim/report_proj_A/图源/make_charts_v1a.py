# -*- coding: utf-8 -*-
"""项目总结报告 v1A 图源生成脚本(七图一次产出;数据=战役台账正源数字)
运行: python make_charts_v1a.py  (在 本目录下产出 fig1..fig7 png, 150dpi)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np, os

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
OUT = os.path.dirname(os.path.abspath(__file__))

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)

# ---------------- fig1 项目时间线 ----------------
fig, ax = plt.subplots(figsize=(13, 4.6))
days = ["09-26","09-27","09-28","09-29","09-30","10-01","10-02","10-03","10-04","10-05","10-06","10-07","10-08","10-09","10-10","10-11"]
events = [
 ("仓库版本化\ntag v0.2/v0.3", 1), ("四线制诞生\nT2根因链", 0),
 ("毒槽位根治\n纯视觉红线", 1), ("任务书守则\n无限深度", 0),
 ("EV考古\n从未启用", 1), ("磁盘危机\nroute定因", 0),
 ("A1死锁等\n五大机理", 1), ("三题收缩\n三段式判据", 0),
 ("3090迁移开工\n自主推进条款", 1), ("迁移完成\n敌对17%翻案", 0),
 ("CauchyLoss(0)\n定案", 1), ("tag sitl-v0.4\n实机启动", 0),
 ("D435定案\n三臂δ相变", 1), ("USB案侦破\nδc∈(3,4]", 0),
 ("HAFIX二次修复\nbias证伪", 1), ("C-1错号翻案\n软件清零态", 0)]
ypos = [0.55 if i%2==0 else -0.55 for i in range(len(days))]
colors = ["#4472C4"]*12 + ["#C00000"]*1 + ["#70AD47"]*3
for i,(t,_) in enumerate(events):
    ax.vlines(i, 0, ypos[i], color=colors[i], alpha=.6, lw=1.2)
    ax.text(i, ypos[i], t, ha="center", va="center" if ypos[i]>0 else "center",
            fontsize=8, bbox=dict(boxstyle="round,pad=0.32", fc="#F2F6FC" if ypos[i]>0 else "#FDF2F2", ec=colors[i], lw=.8))
ax.plot(range(len(days)), [0]*len(days), "-o", color="#333", ms=4, lw=1.6)
ax.set_xticks(range(len(days))); ax.set_xticklabels(days, fontsize=8)
ax.set_yticks([]); ax.set_ylim(-1.15, 1.15); ax.set_xlim(-.7, len(days)-.3)
ax.set_title("项目时间线:09-26 启动 → 10-11 软件清零态(红=磁盘/毒配置危机日,绿=收官三连)", fontsize=11)
for s in ["top","right","left"]: ax.spines[s].set_visible(False)
save(fig, "fig1_timeline.png")

# ---------------- fig2 绿率趋势 ----------------
fig, ax = plt.subplots(figsize=(9, 5.2))
stages = ["全库原始\n~30%","剔毒格\n42%","绿格重飞\n70.5%","X4 五连\n5/5(100%)","N8P冷期\n0/11"]
vals = [30, 42, 70.5, 100, 0]
bars = ax.bar(range(5), vals, color=["#8FAADC","#4472C4","#2E75B6","#70AD47","#C00000"], width=.62)
for b,v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+2.5, f"{v:g}%", ha="center", fontsize=11, fontweight="bold")
ax.set_xticks(range(5)); ax.set_xticklabels(stages, fontsize=9.5)
ax.set_ylabel("绿率(%)"); ax.set_ylim(0, 118)
ax.set_title("绿率演进:统计口径逐层净化后的真实带(选格收窄=唯一有效杠杆)", fontsize=11)
ax.annotate("tag sitl-v0.4\n(统计化验收兑现)", xy=(3,100), xytext=(2.1,88),
            arrowprops=dict(arrowstyle="->", color="#2E75B6"), fontsize=9, color="#2E75B6")
ax.annotate("彩票冷期=二项噪声\n(结构性不收敛注记)", xy=(4,4), xytext=(3.35,30),
            arrowprops=dict(arrowstyle="->", color="#C00000"), fontsize=8.5, color="#C00000")
ax.grid(axis="y", alpha=.3)
save(fig, "fig2_greenrate_trend.png")

# ---------------- fig3 X7 失分构成饼图 ----------------
fig, ax = plt.subplots(figsize=(7.2, 6.2))
labels = ["跳变族 37.4pp", "慢淋transit 24.0pp", "毒配置等已拔除 ~6.2pp", "真FAIL/环境等 32.4pp"]
sizes = [37.4, 24.0, 6.2, 32.4]
cs = ["#C00000","#ED7D31","#808080","#4472C4"]
w,_ = ax.pie(sizes, colors=cs, startangle=100, wedgeprops=dict(width=.46, edgecolor="white"))
ax.legend(w, labels, loc="center left", bbox_to_anchor=(.92,.5), fontsize=10)
ax.text(0,.06,"X7 §5 终版", ha="center", fontsize=12, fontweight="bold")
ax.text(0,-.13,"两主族 63.8pp\n= 失分 80.1%", ha="center", fontsize=10, color="#C00000")
ax.set_title("全库 ~30% 绿率的失分构成(61.4→63.8pp 两主族)", fontsize=11)
save(fig, "fig3_x7_pie.png")

# ---------------- fig4 δ 相变图 ----------------
fig, (a1,a2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
deltas = [0, 1, 2, 3, 4, 5, 10, 20]
maxjump_med = [69, 71, 66, 72, 0.21, 0.21, 0.21, 0.21]   # 瀑布带中位 vs 收敛带(E12P族标本口径)
errs_lo = [55, 60, 58, 61, 0.1, 0.1, 0.1, 0.1]; errs_hi = [18, 16, 15, 17, 0.15, 0.15, 0.15, 0.15]
a1.errorbar(deltas, maxjump_med, yerr=[errs_lo, errs_hi], fmt="-s", color="#C00000", capsize=4, ms=6)
a1.axvspan(2, 4, color="#FFF2CC", alpha=.8, zorder=0)
a1.annotate("δc∈(3,4]ms\n(H-pairing-threshold:\n双流配对窗3-4ms)", xy=(3.2,35), fontsize=9, color="#996600")
a1.set_yscale("log"); a1.set_xlabel("双目帧时戳偏移 δ (ms)"); a1.set_ylabel("maxjump 中位 (m, log)")
a1.set_title("臂A:δ 相变(跳变瀑布→逐位收敛)"); a1.grid(alpha=.3)
arms = ["臂A 时戳\n配对","臂B 节奏\n4操作","臂C 内容\n替换"]
eff = [1, 0, 0]
a2.bar(arms, [1,1,1], color=["#70AD47","#BFBFBF","#BFBFBF"], width=.5)
for i,e in enumerate(eff):
    a2.text(i, .5, {1:"唯一敏感因子\n(strong)",0:"NO-EFFECT\n(noop)"}[e], ha="center", fontsize=10,
            color={1:"white",0:"#555"}[e], fontweight="bold")
a2.set_ylabel("效应"); a2.set_yticks([]); a2.set_ylim(0,1.15)
a2.set_title("三臂终判:排除法收敛(C1=0/12, B/C=23 noop)")
save(fig, "fig4_delta_phase.png")

# ---------------- fig5 内存泄漏统一模型 ----------------
fig, ax = plt.subplots(figsize=(9.8, 5.4))
t = np.linspace(0, 5.5, 200)
healthy = 2.18 * t                      # 健康相线性 GB
patho_hi = 0.95 * t                     # 平台相(病理发作,泄漏暂停)
ax.plot(t, healthy, "-", color="#C00000", lw=2.2, label="健康相:2.18 GB/h 统一模型")
ax.fill_between(t, 1.85*t, 2.5*t, color="#C00000", alpha=.12, label="实测带(1.85-2.5 GB/h)")
ax.plot(t, patho_hi, "--", color="#ED7D31", lw=1.8, label="平台相:病理发作=泄漏暂停(~0 GB/h)")
pts = [(3.13, 6.56, "第四数据点\n2.09 GB/h(实机)", (2.6,8.2)),
       (3.5, 8.06, "watch2 截断值\n2.3 GB/h", (3.7,9.6)),
       (0.45, 0.71, "L2 回放域\n0.95 GB/h", (0.15,2.6))]
for x,y,lab,(tx,ty) in pts:
    ax.plot(x, y, "o", color="#333", ms=6, zorder=5)
    ax.annotate(lab, xy=(x,y), xytext=(tx,ty), fontsize=8.5, arrowprops=dict(arrowstyle="->", lw=.9))
ax.axvline(5, color="#70AD47", ls=":", lw=2)
ax.text(5.06, 1.5, "5h 运维窗红线\n(重启制)", color="#2E75B6", fontsize=9, rotation=90)
ax.axhline(1.1, color="#70AD47", ls="--", lw=1.2)
ax.text(0.1, 1.25, "半小时飞行 1.1GB 安全线", color="#2E75B6", fontsize=9)
ax.set_xlabel("VINS 实例运行时长 (h)"); ax.set_ylabel("RSS (GB)")
ax.set_title("内存泄漏统一模型:2.18GB/h × 健康帧占比(三家族归属 estimator.cpp:666/2188/1736+Ceres)", fontsize=10.5)
ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=.3); ax.set_xlim(0,5.7); ax.set_ylim(0,12.5)
save(fig, "fig5_memleak_model.png")

# ---------------- fig6 三大翻案链流程图 ----------------
fig, ax = plt.subplots(figsize=(12.6, 6.4))
ax.set_xlim(0,10); ax.set_ylim(0,8); ax.axis("off")
def box(x,y,w,h,text,fc,ec,fs=8.8,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.12",fc=fc,ec=ec,lw=1.4))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,
            fontweight="bold" if bold else "normal")
def arrow(x1,y1,x2,y2,c="#555"):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=14,color=c,lw=1.5))
# 案1 敌对态
box(.2,6.6,2.5,.95,"错误结论:\n疑 VINS 算法病(敌对 83%)","#FDF2F2","#C00000",8.6,True)
box(.2,5.15,2.5,1.15,"四面证据链:\n对审B+/时序稳定/8例进程内\n/3090对照 17%","#F2F6FC","#4472C4",8.0)
box(.2,3.7,2.5,1.15,"定案:\n机器层改形态不改发生率\n(大漂移 92% 跨机恒定)","#EAF3E6","#70AD47",8.2,True)
arrow(1.45,6.6,1.45,6.35); arrow(1.45,5.15,1.45,4.9)
# 案2 anchor
box(3.3,6.6,2.9,.95,"错误结论:\n\"22/22 动态窗 z 污染=VINS 物理瞬态\"","#FDF2F2","#C00000",8.4,True)
box(3.3,5.15,2.9,1.15,"翻案:\n锚=sum(前50)/len(全窗) 分母错\nX2g3 0.849→0.035 翻绿;99轮15翻转","#F2F6FC","#4472C4",7.9)
box(3.3,3.7,2.9,1.15,"教训:\n判读器自身算术审计\nselftest+历史零漂移验证","#EAF3E6","#70AD47",8.2,True)
arrow(4.75,6.6,4.75,6.35); arrow(4.75,5.15,4.75,4.9)
# 案3 C-1
box(6.8,6.6,3.0,.95,"错误结论(连环三版):\nfailsafe覆写→ACK假确认→固件不可依赖","#FDF2F2","#C00000",8.3,True)
box(6.8,4.95,3.0,1.35,"三段接力:\n复现分支确认→取证F1分离\n(候选①②双否证)→第三发现\n179=DO_SET_HOME,400=ARM_DISARM","#F2F6FC","#4472C4",7.9)
box(6.8,3.7,3.0,1.0,"终局:\npx4ctrl 错号=全案根因(fsm_decision.h)\n修复89dc2a1+双正控45/45+旧机部署","#EAF3E6","#70AD47",8.0,True)
arrow(8.3,6.6,8.3,6.35); arrow(8.3,4.95,8.3,4.75)
# 底部总教训带
box(.2,.35,9.6,2.6,"","#FFFFFF","#333")
ax.text(5,2.55,"三案共同的方法论(可复用)", ha="center", fontsize=11, fontweight="bold", color="#333")
ax.text(.5,1.9,"① \"观测与源码互斥\"时优先怀疑观测前提(注释自称的语义/判读器的算术)——三者全是'观测前提'先错", fontsize=9.2, color="#333")
ax.text(.5,1.4,"② 破局器=新证据面:双机对照(4.1)/双锚重算(4.2)/纯打印取证构建(4.3)——不动被测系统,加观测维度", fontsize=9.2, color="#333")
ax.text(.5,.9,"③ 翻案必须'不制造虚假绿':修正后逐轮对账+独立背书(X2g3 有 ARRIVE_WATCH 0.099 背书才翻绿)", fontsize=9.2, color="#333")
ax.text(.5,.5,"④ 翻案后全库重算:anchor 案 99 轮重算/C-1 案多份记忆表述修正——历史文书勘误是翻案的成本", fontsize=9.2, color="#333")
ax.set_title("三大翻案链:错误结论 → 证据链 → 终局(0.5=半透明占位去除)", fontsize=11.5)
save(fig, "fig6_reversal_flow.png")

# ---------------- fig7 HAFIX 50轮演进 ----------------
fig, ax = plt.subplots(figsize=(9.8, 5.2))
phases = ["修复前复验批\n(20轮)","正源重判\n(13有效)","增量批\n(10轮)","终验批 S1-S3\n(15轮)+S4(2)","50轮总表"]
passrate = [15, 23, 100, 87, 87]
bars = ax.barh(range(5), passrate, color=["#C00000","#ED7D31","#70AD47","#2E75B6","#4472C4"], height=.58)
for b,v in zip(bars, passrate):
    ax.text(v+1.5, b.get_y()+b.get_height()/2, f"{v}%", va="center", fontsize=11, fontweight="bold")
ax.set_yticks(range(5)); ax.set_yticklabels(phases, fontsize=9.5)
ax.invert_yaxis(); ax.set_xlim(0,112); ax.set_xlabel("PASS 率(%)")
ax.set_title("HAFIX 强制降落链:15% → 87%(物理链 0→26/30;S4 边界注记)", fontsize=11)
ax.axvline(87, color="#4472C4", ls=":", lw=1.5)
ax.annotate("三级失效实锤→梯①盲降二次修复\n(idle门+disarmed终态+双锚)", xy=(2,100), xytext=(30,3.1),
            arrowprops=dict(arrowstyle="->", color="#2E75B6"), fontsize=9, color="#2E75B6")
ax.grid(axis="x", alpha=.3)
save(fig, "fig7_hafix_ladder.png")

print("ALL 7 CHARTS DONE")
