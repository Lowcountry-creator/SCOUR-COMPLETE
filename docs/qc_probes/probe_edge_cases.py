import math, sys, json
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[1]+"/legacy")
import hec14_outlet_protection as h
from methods_apron import apron_d50
from scour_complete import run_case, run_batch
from dataclasses import asdict
# apron benchmark Eq 10.4: D50 = 0.2 D (Q/(sqrt(g) D^2.5))^(4/3) (D/TW)
Q,D,TW=85,5,2.0
print("apron hand", 0.2*D*(Q/(math.sqrt(32.2)*D**2.5))**(4/3)*(D/TW), apron_d50(85,5,1.6))
print("apron TW=0", apron_d50(85,5,0)); print("apron TW None", apron_d50(85,5,None))
print("apron TW=D", apron_d50(85,5,5))
for kw in [dict(supercritical=True, normal_depth=2)]:
    print("supercrit", apron_d50(85,5,1.6,**kw))
# Eq 10.6 hand
print("eq10.6 V=16.32", 0.692*16.32**2/(2*32.2*1.65))
# culv1 hand: Fr, hs
yo,Vo,TW=2.8,16.32,5.14; Fr=Vo/math.sqrt(32.2*yo); hs=(0.86*(0.75/yo)**-0.55*Fr-2.4)*yo
print("c1 Fr",Fr,"hs",hs,"Ls",max(10*hs,42),"La",max(5*hs,14))
# silent defaults: omit TW, V_channel, V_LB
base=asdict(h.EXAMPLES["culv1"])
for k in ("TW","V_channel","V_LB","V_perm","tau_perm"):
    d=dict(base); d.pop(k)
    r=run_case(d)["legacy"]
    print("omit",k,"->",r["tailwater_case"],"L_adopted",r["L_adopted"],"opt1",r["option_1"][:60])
# Fr >= 3 still gives basin
d=dict(base, Vo=30.0, Q=30*14*2.8)
r=run_case(d)["legacy"]; print("Fr",round(r["Fr"],2), r["basin_applicable"], "| basin_applies", r["basin_applies"], "| opt2", r["option_2"][:50])
# NaN / inf
for bad in (float("nan"), float("inf")):
    d=dict(base, Q=bad)
    try:
        out=run_batch([d, base]); json.dumps(out, allow_nan=False); print("bad",bad,"ok")
    except Exception as e: print("bad",bad,"->",type(e).__name__, e)
# V_LB increasing / zero
d=dict(base, V_LB=[0,0,0,0]); r=run_case(d)["legacy"]; print("VLB zero L_target", r["L_target"], [x["scdot_class"] for x in r["reaches"]])
d=dict(base, V_LB=[-5,2,3,4]); 
try: r=run_case(d)["legacy"]; print("VLB negative accepted", r["L_target"])
except Exception as e: print("neg rejected", e)
# box yo > D
d=dict(base, yo=7.0, Vo=639.56/(14*6)); r=run_case(d)["legacy"]; print("yo>D ye",r["ye"],"A",r["A"],"Vo_check",r["Vo_check_result"])
# supercritical text with low TW
d=dict(base, TW=0.5); r=run_case(d)["legacy"]; print("lowTW regime:", r["regime"], "|", r["tailwater_case"], "| L", r["L_adopted"], "| opt1", r["option_1"])
# yo string type
try: run_case(dict(base, yo="2.8"))
except Exception as e: print("string yo ->", type(e).__name__, e)
# multiple barrels box: barrels ignored?
d=dict(base, barrels=2); r=run_case(d)["legacy"]; print("box barrels=2 A", r["A"], "Wo", r["inputs"] if False else "", r["Ls"])
