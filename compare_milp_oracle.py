"""Compare deterministic scientific fields of two independent MILP runs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

RECORD_FIELDS = (
    "case", "status", "solver_status", "variables", "binary_variables",
    "constraints", "regions", "candidates", "nets", "pins",
    "objective_upper_bound", "optimum", "exact_witness_recheck",
    "primal_dual_agree", "independent_truth", "truth_optimum",
    "cartesian_assignments",
)
SUMMARY_FIELDS = (
    "cases", "optimal", "zero_gap", "exact_witness_rechecks",
    "primal_dual_agreements", "truth_categories", "cartesian_assignments",
)

def load(path: Path):
    return json.loads(path.read_text())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("expected"); p.add_argument("fresh")
    a=p.parse_args(); left=load(Path(a.expected)); right=load(Path(a.fresh))
    assert left["scope"] == right["scope"] and left["boundary"] == right["boundary"]
    for field in SUMMARY_FIELDS:
        assert left["summary"][field] == right["summary"][field], field
    lrows={row["case"]:row for row in left["records"]}
    rrows={row["case"]:row for row in right["records"]}
    assert set(lrows)==set(rrows) and len(lrows)==77
    for case in sorted(lrows):
        for field in RECORD_FIELDS:
            assert lrows[case].get(field) == rrows[case].get(field), (case,field)
        for field in ("solver_objective","mip_dual_bound"):
            assert abs(lrows[case][field]-rrows[case][field]) <= 1e-5, (case,field)
        assert lrows[case]["mip_gap"] <= 1e-10 and rrows[case]["mip_gap"] <= 1e-10
    print(json.dumps({"compared_cases":77,"timing_compared":False,
                      "solver_witness_choice_compared":False,
                      "branch_and_bound_path_compared":False},sort_keys=True))

if __name__=="__main__": main()
