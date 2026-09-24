"""Compare deterministic outputs and exact input/certificate bytes for the public extension."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

SUMMARY_FIELDS=("cases","jobs","success","limit","failure","milp_optimal",
                "cartesian_assignments_not_enumerated","completed_leaf_response_pairs",
                "response_fewer","ties","response_greater","limits")
PRODUCER_FIELDS=("mode","optimum","transitions","comparisons","total_states","max_states","per_node")
CHECKER_FIELDS=("accepted","optimum","replayed_transitions","retained_row_evaluations","dominance_obligations")
ORACLE_FIELDS=("case","status","solver_status","variables","binary_variables","constraints",
               "regions","candidates","nets","pins","objective_upper_bound","optimum",
               "exact_witness_recheck","primal_dual_agree","cartesian_assignments_not_enumerated")

def read(path): return json.loads(path.read_text())
def files(path): return {p.name:p.read_bytes() for p in path.glob("*.json")}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("expected");p.add_argument("fresh");a=p.parse_args()
    left,right=Path(a.expected),Path(a.fresh)
    ls,rs=read(left/"summary.json"),read(right/"summary.json")
    for field in SUMMARY_FIELDS: assert ls[field]==rs[field],field
    lr={(x["case"],x["mode"]):x for x in read(left/"records.json")}
    rr={(x["case"],x["mode"]):x for x in read(right/"records.json")}
    assert set(lr)==set(rr) and len(lr)==32
    for key in sorted(lr):
        x,y=lr[key],rr[key]
        for field in ("case","mode","truth_optimum","status","reason","certificate_bytes"):
            assert x.get(field)==y.get(field),(key,field)
        if x["status"]=="success":
            for field in PRODUCER_FIELDS: assert x["producer"][field]==y["producer"][field],(key,"producer",field)
            for field in CHECKER_FIELDS: assert x["checker"][field]==y["checker"][field],(key,"checker",field)
    lo={x["case"]:x for x in read(left/"milp-oracles.json")};ro={x["case"]:x for x in read(right/"milp-oracles.json")}
    assert set(lo)==set(ro) and len(lo)==8
    for case in sorted(lo):
        for field in ORACLE_FIELDS: assert lo[case].get(field)==ro[case].get(field),(case,"oracle",field)
        for field in ("solver_objective","mip_dual_bound"):
            assert abs(lo[case][field]-ro[case][field])<=1e-5,(case,field)
        assert lo[case]["mip_gap"]<=1e-10 and ro[case]["mip_gap"]<=1e-10
    assert read(left/"leaf-response-pairs.json")==read(right/"leaf-response-pairs.json")
    assert files(left/"inputs")==files(right/"inputs")
    assert files(left/"certificates")==files(right/"certificates")
    print(json.dumps({"compared_jobs":32,"exact_inputs":8,"exact_certificates":ls["success"],
                      "milp_cases":8,"timing_compared":False,
                      "solver_witness_choice_compared":False},sort_keys=True))

if __name__=="__main__": main()
