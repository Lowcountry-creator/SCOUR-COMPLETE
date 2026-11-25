import math, sys
sys.path.insert(0, sys.argv[1]+"/legacy"); sys.path.insert(0, sys.argv[1])
import hec14_outlet_protection as h
from scour_complete import run_case
from dataclasses import asdict
def run(**k):
    k.setdefault("V_LB",[1,1,1,1]); k.setdefault("V_channel",1)
    return h.analyze(h.Inputs(**k))
# 5.2 steep slope 8x6 box
r=run(Q=800,Wo=8,rise=6,yo=4,Vo=25,TW=2.8,D50_trial=1.83)
print("steep Fr %.3f hs %.3f hs/D50 %.2f Ls %.2f LB %.2f WB %.2f"%(r.Fr,r.trial.hs_envelope,r.trial.hs_D50,r.Ls,r.Lb,r.Wb), r.trial.result)
A=32; print("De", math.sqrt(4*A/math.pi), "TW4.2/ye", 4.2/4)
print("eq10.6", [round(h.riprap_d50_velocity(v,32.2,2.65),3) for v in (14.75,10.5,7.5,7.0)])
r=run(shape="circular",Q=135,rise=6,yo=2.7,Vo=10.9,TW=2.0,D50_trial=0.5)
print("mild A %.2f ye %.2f Fr %.2f C0 %.2f hs %.2f hs/D50 %.2f Ls %.1f LB %.1f WB %.1f"%(r.A,r.ye,r.Fr,r.C0_envelope,r.trial.hs_envelope,r.trial.hs_D50,r.Ls,r.Lb,r.Wb))
for d in (0.65,0.83):
    r=run(shape="circular",Q=135,rise=6,yo=2.7,Vo=10.9,TW=2.0,D50_trial=d)
    print(" D50",d,"hs %.2f hs/D50 %.2f LB %.1f"%(r.trial.hs_envelope,r.trial.hs_D50,r.LB))
for vo in (200/(5*2.15),19):
    r=run(Q=200,Wo=5,rise=5,yo=2.15,Vo=vo,TW=0,D50_trial=1.2)
    print("ch1 Vo %.2f hs %.2f Ls %.1f La %.1f t %.2f %.2f %s"%(vo,r.trial.hs_envelope,r.Ls or 0,r.La or 0,r.t_approach or 0,r.t_pool or 0,r.Vo_check_result))
# H-03
for n,Q in ((1,60),(3,180)):
    r=run(shape="circular",barrels=n,Q=Q,rise=4,yo=2,Vo=60/(2*math.pi),TW=1)
    print("H03 n",n,"ye %.3f Fr %.3f TWye %.2f"%(r.ye,r.Fr,r.TW_ye))
# H-04
b=asdict(h.EXAMPLES["culv1"])
r=h.analyze(h.Inputs(**{**b,"Vo":8.0})); print("H04 Vo8", r.Vo_check_result, round(r.Fr,2), r.trial.result, r.option_1)
# M-02 HEC-15 numbers
tau=62.4*5.14*0.0211; d=tau/(0.047*1.65*62.4); us=math.sqrt(32.2*5.14*0.0211)
print("M02 tau %.3f D50 %.3f u* %.3f Re %.3g D50_hec15 %.3f"%(tau,d,us,us*d/1.217e-5,1.5*5.14*0.0211/(0.15*1.65)))
# M-03
for c in h.SCDOT_CLASSES: print("M03",c["name"],"2D50",2*c["d50"],"1.5Dmax",1.5*c["dmax"],"3D50",3*c["d50"],"2Dmax",2*c["dmax"])
# M-07
r=run_case({**b,"Vo":20.0,"Q":20*14*2.8})["legacy"]; print("M07", r["reaches"][0]["D50_required"], r["reaches"][0]["scdot_class"])
# C-02 probe as written
r=run_case({**b,"Vo":30.0,"Q":30*14*2.8,"D50_trial":1.3})["legacy"]; print("C02", round(r["Fr"],2), r["basin_applicable"], r["trial_gives"], r["option_2"][:70])
# Sec 7: L/De, VL/Vo
for name in ("culv1","culv2","culv4"):
    e=h.EXAMPLES[name]; rr=h.analyze(h.Inputs(**asdict(e)))
    De=math.sqrt(4*min(e.yo,e.rise-e.embedment)*e.Wo/math.pi)
    print(name,"De %.3f LB %.0f"%(De,rr.LB), [("%.2f"%(rr.LB*i/De),"%.4f"%(v/e.Vo)) for i,v in enumerate(e.V_LB,1)])
