import math, sys, json
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[1]+"/legacy")
import hec14_outlet_protection as h
from methods_apron import apron_d50
from scour_complete import run_case, run_batch
from dataclasses import asdict
# apron benchmark Eq 10.4: D50 = 0.2 D (Q/(sqrt(g) D^2.5))^(4/3) (D/TW)
Q,D,TW=85,5,2.0
print("apron hand", 0.2*D*(Q/(math.sqrt(32.2)*D**2.5))**(4/3)*(D/TW), apron_d50(85,5,1.6))
def rejects(call, field):
    try:
        call()
    except ValueError as exc:
        assert field in str(exc), str(exc)
        print("Rejected:", exc)
    else:
        raise AssertionError(f"Expected rejection for {field}")


print("apron TW=0", apron_d50(85, 5, 0))
rejects(lambda: apron_d50(85, 5, None), "tailwater")
print("apron TW=D", apron_d50(85, 5, 5))
rejects(lambda: apron_d50(85, 5, 1.6, supercritical=True, normal_depth=2), "D versus")
# Eq 10.6 hand
print("eq10.6 V=16.32", 0.692*16.32**2/(2*32.2*1.65))
# culv1 hand: Fr, hs
yo,Vo,TW=2.8,16.32,5.14; Fr=Vo/math.sqrt(32.2*yo); hs=(0.86*(0.75/yo)**-0.55*Fr-2.4)*yo
print("c1 Fr",Fr,"hs",hs,"Ls",max(10*hs,42),"La",max(5*hs,14))
base = asdict(h.EXAMPLES["culv1"])
for field in ("TW", "V_channel", "V_LB", "V_perm", "tau_perm"):
    data = dict(base)
    del data[field]
    rejects(lambda: run_case(data), field)

rejects(lambda: run_case(dict(base, Vo=30, Q=30*14*2.8)), "Fr >= 3")
for bad in (float("nan"), float("inf")):
    pair = json.loads(json.dumps(run_batch([dict(base, Q=bad), base]), allow_nan=False))
    assert "Q" in pair[0]["error"] and pair[1]["legacy"]["L_adopted"] == 108

for stations in ([0, 0, 0, 0], [-5, 2, 3, 4], [10, 11, 4, 1]):
    rejects(lambda: run_case(dict(base, V_LB=stations)), "V_LB")
rejects(lambda: run_case(dict(base, yo=7.0, Vo=639.56/(14*6))), "yo")
rejects(lambda: run_case(dict(base, yo="2.8")), "yo")
rejects(lambda: run_case(dict(base, barrels=2)), "barrels")
rejects(lambda: run_case(dict(base, TW=0.5)), "HS_hy8")
low = run_case(dict(base, TW=0.5, HS_hy8=None))["legacy"]
assert low["regime"] == "Supercritical at brink" and not low["reaches"]
