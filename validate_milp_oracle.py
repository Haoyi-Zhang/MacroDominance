"""Recompute and validate every deterministic field of the independent MILP run."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from milp_oracle import read_json, solve_milp
from control_oracle import closed_form_optimum
from oracle import optimum as cartesian_optimum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", nargs="?", default="results/milp-oracle.json")
    parser.add_argument("--inputs", default="results/dominance-campaign/inputs")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--report")
    args = parser.parse_args()
    payload = json.loads(Path(args.result).read_text())
    records = payload["records"]
    assert len(records) == 77
    by_case = {record["case"]: record for record in records}
    assert len(by_case) == 77
    cartesian = closed_form = assignments = 0
    for path in sorted(Path(args.inputs).glob("*.json")):
        data = read_json(path)
        expected = by_case[data["name"]]
        fresh = solve_milp(data, time_limit=args.seconds)
        assert fresh["status"] == "optimal"
        for field in ("case", "status", "solver_status", "variables", "binary_variables", "constraints", "regions", "candidates", "nets", "pins", "objective_upper_bound", "optimum", "exact_witness_recheck", "primal_dual_agree"):
            assert fresh[field] == expected[field], (data["name"], field)
        assert fresh["mip_gap"] <= 1e-10
        assert abs(fresh["solver_objective"] - expected["optimum"]) <= 1e-6 * max(1, expected["optimum"])
        assert abs(fresh["mip_dual_bound"] - expected["optimum"]) <= 1e-6 * max(1, expected["optimum"])
        try:
            truth = closed_form_optimum(data)
            closed_form += 1
        except ValueError:
            truth = cartesian_optimum(data, limit=200000)
            cartesian += 1
            assignments += truth["assignments"]
        assert truth["optimum"] == fresh["optimum"] == expected["truth_optimum"]
    assert cartesian == 51 and closed_form == 26 and assignments == 176128
    assert payload["summary"]["cases"] == payload["summary"]["optimal"] == 77
    assert payload["summary"]["zero_gap"] == payload["summary"]["exact_witness_rechecks"] == payload["summary"]["primal_dual_agreements"] == 77
    result={"validated_cases":77,"cartesian_cases":cartesian,"closed_form_cases":closed_form,
            "cartesian_assignments":assignments,"timing_compared":False,
            "solver_choices_compared":False}
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.report: Path(args.report).write_text(text)
    print(json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
