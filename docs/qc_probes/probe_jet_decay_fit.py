import math, sys
sys.path.insert(0, sys.argv[1]+"/legacy"); sys.path.insert(0, sys.argv[1])
import hec14_outlet_protection as h
from methods_apron import apron_d50
from dataclasses import asdict
pts=[]
for n in ("culv1","culv2","culv4"):
    e=h.EXAMPLES[n]; r=h.analyze(h.Inputs(**asdict(e))); De=math.sqrt(4*e.yo*e.Wo/math.pi)
    pts+= [(r.LB*i/De, v/e.Vo) for i,v in enumerate(e.V_LB,1)]
pts.sort(); hi=[p for p in pts if p[0]>=10]
xs=[math.log(x) for x,_ in hi]; ys=[math.log(y) for _,y in hi]
n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); a=math.exp(my-b*mx)
print("fit a=%.3f b=%.4f n=%d maxerr=%.3f%%"%(a,b,n,max(abs(a*x**b/y-1) for x,y in hi)*100))
def interp(L):
    for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
        if x0<=L<=x1:
            t=(math.log(L)-math.log(x0))/(math.log(x1)-math.log(x0)); return math.exp(math.log(y0)+t*(math.log(y1)-math.log(y0)))
print([round(interp(L),3) for L in (10,15,20,21)])
try: apron_d50(85,5,4.5,supercritical=True,normal_depth=3)
except ValueError as e: print("M15:",e)
