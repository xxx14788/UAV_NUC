import csv, os, glob, re
home=os.path.expanduser("~")
outdir=home+"/catkin_ws/sitl_sim/t2_results/gate_science_v1"
os.makedirs(outdir,exist_ok=True)
# passmap 权威
pm={}
with open(home+"/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f):
        pm[row["run_dir"]]=row
rows=[]
for R in sorted(glob.glob(home+"/sitl_sim/vins_smoke_runs/run_X5_*")):
    n=os.path.basename(R)
    def sz(p):
        try: return os.path.getsize(os.path.join(R,p))/(1024*1024)
        except: return 0.0
    px=glob.glob(os.path.join(R,"px4_params_*.txt"))
    px4="OK" if px else "MISS"
    cfg="OK" if os.path.getsize(os.path.join(R,"vins_config.md5"))>0 else "MISS"
    hw_p=os.path.join(R,"hwmon.tsv")
    hw="OK" if os.path.exists(hw_p) and os.path.getsize(hw_p)>0 else "MISS"
    hwr=sum(1 for _ in open(hw_p)) if hw=="OK" else 0
    gt="OK" if os.path.exists(os.path.join(R,"goal_trace.tsv")) and os.path.getsize(os.path.join(R,"goal_trace.tsv"))>0 else "MISS"
    sv=sz("simvins.log"); bag=sz("flight.bag")
    verdict="NOFILE"
    try:
        for line in open(os.path.join(R,"RESULT.txt")):
            if line.startswith("RESULT="): verdict=line.split()[0].split("=")[1]
    except: pass
    p=pm.get(n,{})
    rows.append(dict(round=n.replace("run_",""),green=p.get("result","NOTINMAP"),
        gyr_peak=p.get("gyr_peak",""),profile=p.get("profile",""),
        bag_mb=round(bag,1),px4_params=px4,cfg_md5=cfg,hwmon=hw,hwmon_rows=hwr,
        goal_trace=gt,simvins_mb=round(sv,1),RESULT=verdict))
keys=list(rows[0].keys())
with open(outdir+"/x5_integrity.tsv","w") as f:
    w=csv.DictWriter(f,fieldnames=keys,delimiter="\t"); w.writeheader()
    for r in rows: w.writerow(r)
greens=[r for r in rows if r["green"]=="PASS"]
print("total",len(rows),"| greens_in_passmap",len(greens))
for r in greens: print("  GREEN",r["round"],"gyr="+r["gyr_peak"],"prof="+r["profile"])
miss=[r["round"] for r in rows if r["px4_params"]=="MISS" or r["goal_trace"]=="MISS"]
print("four_artifact_miss(",len(miss),"):",miss)
notin=[r["round"] for r in rows if r["green"]=="NOTINMAP"]
print("not_in_passmap(",len(notin),"):",notin)
# green 轮四件质量
gm=[r["round"] for r in greens if r["px4_params"]=="MISS" or r["goal_trace"]=="MISS"]
print("green_rounds_with_gap:",gm if gm else "NONE")
