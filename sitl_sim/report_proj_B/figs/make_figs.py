# -*- coding: utf-8 -*-
"""项目总结报告 B 版 图源包——7 幅图可复现脚本
用法：python make_figs.py  （在本目录运行，输出 fig*.png）
数据：全部来自报告正文引用的战役台账数字（各图注释标注出处章节）。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = "."

# ---------------- 图 1 时间线与 commit 密度（章 2 / 9.2：git log 逐日实测） ----------------
def fig1():
    days = ["09-22","09-26","09-27","09-28","09-29","09-30","10-01","10-02","10-03","10-04",
            "10-05","10-06","10-07","10-08","10-09","10-10","10-11"]
    comm = [1,19,16,42,25,57,58,30,76,98,53,43,27,9,14,11,44]
    marks = {3:"纯视觉红线",6:"磁盘危机W-0",8:"route收缩",9:"3090迁移+自主推进",
             12:"tag v0.4+实机启动",13:"预热/三臂δ",14:"场景批+USB案",15:"终验批+50pp",16:"错号翻案收官"}
    fig, ax = plt.subplots(figsize=(11,4.2))
    ax.bar(days, comm, color="#4C78A8")
    for i,t in marks.items():
        ax.annotate(t,(i,comm[i]),textcoords="offset points",xytext=(0,6),
                    ha="center",fontsize=7.5,rotation=45,color="#B24A28")
    ax.set_ylabel("commits/日"); ax.set_title("图 1  16 天时间线与 commit 密度（623 笔@10-11 基线）")
    plt.xticks(rotation=60,fontsize=8); plt.tight_layout(); plt.savefig(f"{OUT}/fig1_timeline.png",dpi=150); plt.close()

# ---------------- 图 2 绿率四口径（章 3.2） ----------------
def fig2():
    labels=["全库粗绿率","剔毒格后","绿格重飞","X4 验证批","近期 N8P（冷期）"]
    vals=[30,42,70.5,100,0]
    fig,ax=plt.subplots(figsize=(8,4))
    bars=ax.barh(labels[::-1],vals[::-1],color=["#888","#5C9","#2A7","#1A5","#C55"])
    for b,v in zip(bars,vals[::-1]):
        ax.text(b.get_width()+1.5,b.get_y()+b.get_height()/2,f"{v}%",va="center",fontsize=9)
    ax.set_xlim(0,115); ax.set_xlabel("绿率 %")
    ax.set_title("图 2  绿率四口径对比（±25pp=8 轮批组间分辨极限）")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig2_greenrate.png",dpi=150); plt.close()

# ---------------- 图 3 X7 失分构成饼图（章 3.2：37.4+24.0=61.4→63.8pp 终版=80.1%） ----------------
def fig3():
    fig,ax=plt.subplots(figsize=(6.2,5))
    ax.pie([37.4,24.0,38.6],labels=["跳变族 jumpy\n37.4pp","慢淋 transit\n24.0pp","其他失分\n38.6pp"],
           colors=["#C55","#E9A319","#7A9"],autopct="%1.1f%%",startangle=90,
           wedgeprops=dict(width=0.42,edgecolor="w"))
    ax.set_title("图 3  失分构成（X7 终版口径：两主族=失分 80.1% 下界）")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig3_x7_pie.png",dpi=150); plt.close()

# ---------------- 图 4 δ 相变（章 3.7：δc∈(3,4]ms 门型签名 55.041） ----------------
def fig4():
    import numpy as np
    d=np.array([0,1,2,3,4,5,10,20])
    j=np.array([68,55,42,30,2,1.5,1.2,1.1])   # 跳变幅度 m：瀑布带→收敛带（示意带，锚=台账）
    fig,ax=plt.subplots(figsize=(8,4.2))
    ax.plot(d,j,"o-",color="#C55",lw=2)
    ax.axvspan(0,2,color="#C55",alpha=.12); ax.axvspan(4,20,color="#2A7",alpha=.10)
    ax.annotate("瀑布带 δ≤2ms",(1,60),fontsize=9,color="#C55")
    ax.annotate("δ≥4ms 收敛带（右目弃用=单目化）",(9,25),fontsize=9,color="#2A7")
    ax.axvline(3.5,ls="--",c="k",lw=1); ax.annotate("δc∈(3,4]ms\n=配对窗宽",(3.6,45),fontsize=9)
    ax.set_xlabel("δ（左右目时戳差 ms）"); ax.set_ylabel("跳变幅度（m）")
    ax.set_title("图 4  臂 A δ 相变曲线（跨 δ∈{4,5,10,20} 逐位相同=门型签名）")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig4_delta.png",dpi=150); plt.close()

# ---------------- 图 5 内存泄漏统一模型（章 5.7：2.18GB/h×健康占比） ----------------
def fig5():
    import numpy as np
    t=np.arange(0,6,0.05)
    rss=0.62+2.18*t/1.0  # GB
    rss=np.where((t>2.6)&(t<3.4), rss-(t-2.6)*0  , rss)  # 平台相示意：断开爬升
    plat=np.where((t>2.6)&(t<3.4), rss*0+0.62+2.18*2.6, rss)
    fig,ax=plt.subplots(figsize=(8.5,4.2))
    ax.plot(t,rss,color="#C55",lw=2,label="健康相：2.18GB/h 精确线性")
    ax.plot(t,plat,color="#888",lw=2,ls="--",label="平台相（病理发作=泄漏暂停）")
    ax.axvline(5,ls=":",c="k"); ax.annotate("5h 运维窗重启\n（watch2 RESTART）",(4.15,10.2),fontsize=9)
    ax.axhline(1.1+0.62,xmax=0.09,ls="-.",c="#2A7")
    ax.annotate("半小时飞行 ≈1.1GB 安全",(0.12,1.85),fontsize=9,color="#2A7")
    ax.set_xlabel("运行时长（h）"); ax.set_ylabel("VINS RSS（GB）")
    ax.set_title("图 5  内存泄漏统一模型（实机数据点 1.44/2.09·回放域 0.95GB/h 同带）")
    ax.legend(fontsize=8.5); plt.tight_layout(); plt.savefig(f"{OUT}/fig5_memleak.png",dpi=150); plt.close()

# ---------------- 图 6 三大翻案链流程图（章 4） ----------------
def fig6():
    fig,ax=plt.subplots(figsize=(10,6.4)); ax.axis("off")
    boxes=[
     (0.02,0.86,0.30,0.12,"案4.1 敌对态\n疑 VINS 算法病（83%）","#F6D"),
     (0.36,0.86,0.30,0.12,"案4.2 anchor 算术\n22/22=物理瞬态","#F6D"),
     (0.70,0.86,0.28,0.12,"案4.3 C-1 错号\nACK 假确认","#F6D"),
     (0.02,0.62,0.30,0.16,"图像对审不可分+R3x+8 例进程内铁证","#FFD"),
     (0.36,0.62,0.30,0.16,"判读器 v1.4 自审计\nsum(前50)/len(全窗) 分母错","#FFD"),
     (0.70,0.62,0.28,0.16,"重编译取证 8 打点\n候选①②双否证","#FFD"),
     (0.02,0.36,0.30,0.16,"3090 对照：83%→17%\n形态剧变/92% 恒定","#DFD"),
     (0.36,0.36,0.30,0.16,"X2g3 0.849→0.035 翻绿\n99 轮 15 翻转","#DFD"),
     (0.70,0.36,0.28,0.16,"第三发现：179=DO_SET_HOME\n固件全程正确","#DFD"),
     (0.02,0.12,0.96,0.16,"定案教训：①双机对照=分诊台 ②判读器=仪器要自校（锚点哨兵）③注释自称的命令语义不可信——命令号必查官方表/优先怀疑观测前提","#DED"),
    ]
    for x,y,w,h,c in [(b[0],b[1],b[2],b[3],b[4]) for b in boxes]:
        pass
    for x,y,w,h,txt,c in boxes:
        ax.add_patch(plt.Rectangle((x,y),w,h,fc=c,ec="k",lw=.8))
        ax.text(x+w/2,y+h/2,txt,ha="center",va="center",fontsize=8.6)
    for x0 in (0.17,0.51,0.84):
        ax.annotate("",xy=(x0,0.78),xytext=(x0,0.86),arrowprops=dict(arrowstyle="->",lw=1.2))
        ax.annotate("",xy=(x0,0.52),xytext=(x0,0.62),arrowprops=dict(arrowstyle="->",lw=1.2))
        ax.annotate("",xy=(x0,0.28),xytext=(x0,0.36),arrowprops=dict(arrowstyle="->",lw=1.2))
    ax.set_title("图 6  三大翻案链：错误结论 → 证据链 → 定案（粉=错误结论/黄=翻案证据/绿=定案）")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig6_reversals.png",dpi=150); plt.close()

# ---------------- 图 7 HAFIX 看门梯（章 6.1） ----------------
def fig7():
    fig,ax=plt.subplots(figsize=(9,5)); ax.axis("off")
    rows=[
     ("odom 死亡 → watch 5s",0.80,"#FDC"),
     ("梯① AUTO_LAND 盲降（odom 门旁路+时基开环+idle 门防伪落地）\n平均 15s 触地 z=0.10 · 增量批 10/10 · 终验 S1-S3 15/15",0.58,"#DFD"),
     ("触地 → cleared=disarmed 终态",0.42,"#DFD"),
     ("15s 死线未触地 → 梯② KILL=cmd185 TERM / 梯③ forced disarm=cmd400(0,21196)\n（修复前错号 179=SET_HOME 空转——4.3 翻案后双正控 PASS：45/45 翻转+nav14→13）",0.20,"#F6D"),
    ]
    for txt,y,c in rows:
        ax.add_patch(plt.Rectangle((0.03,y),0.94,0.14,fc=c,ec="k",lw=.8))
        ax.text(0.5,y+0.07,txt,ha="center",va="center",fontsize=8.8)
    for y0,y1 in ((0.80,0.72),(0.58,0.56),(0.42,0.34)):
        ax.annotate("",xy=(0.5,y1),xytext=(0.5,y0),arrowprops=dict(arrowstyle="->",lw=1.4))
    ax.text(0.86,0.27,"↓",fontsize=13)
    ax.set_title("图 7  HAFIX 看门梯（修复版）与验证账：50 轮总账 15%→87%、物理链 26/30")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig7_hafix.png",dpi=150); plt.close()

if __name__=="__main__":
    for f in (fig1,fig2,fig3,fig4,fig5,fig6,fig7): f()
    print("7 figures done")
