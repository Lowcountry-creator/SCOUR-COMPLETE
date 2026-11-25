import sys
sys.path.insert(0, sys.argv[1]+"/legacy")
import hec14_outlet_protection as h
from dataclasses import asdict
inp=h.Inputs(**{**asdict(h.EXAMPLES["culv1"]), "D50_trial":0.5})
r=h.analyze(inp)
print(r.trial.result, r.largest_valid_class, round(r.hs,3), r.Ls, r.La, r.t_pool)
print(r.option_2)
print([ (c.label, round(c.hs_envelope,2), c.result) for c in r.classes])

assert r.option_2.startswith("Class A basin: pool 4.0 ft deep")
assert r.t_pool == 1 and r.t_approach == 1.5 and r.largest_valid_class == "B"
