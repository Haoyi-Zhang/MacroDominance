"""Fail-closed tests for closed-form control-family recognition."""
from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from control_oracle import closed_form_optimum
from dominance_instances import biased
from instances import exposed, masked
from oracle import optimum as cartesian_optimum
from portfolio_exact import exact_objective, parse_instance

def imported_roots(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


assert not ({"numpy", "scipy", "milp_oracle"} & imported_roots(ROOT / "tests" / "control_oracle.py"))
assert not ({"numpy", "scipy"} & imported_roots(ROOT / "src" / "portfolio_exact.py"))


def main():
    controls = [
        family(k, q)
        for family in (biased, masked, exposed)
        for k in (2, 4, 6, 8)
        for q in (2, 4)
    ]
    controls += [exposed(8, q, True) for q in (2, 4)]
    assert len(controls) == 26
    matched = 0
    for case in controls:
        answer = closed_form_optimum(case)
        assert answer["family_guard"] == "full deterministic input match"
        matched += 1

    # Legal adversarial mutation requested by the review: retain the name,
    # inventory, weights, connectivity, tree, and all-zero witness value, but
    # change one candidate so the exposed-family lower bound is no longer valid.
    mutant = copy.deepcopy(exposed(2, 2))
    v0 = next(region for region in mutant["regions"] if region["id"] == "v0")
    placement = v0["candidates"][1][0]
    assert placement["xy"] == [5, 5]
    placement["xy"] = [1, 5]
    model = parse_instance(mutant)
    zero_witness_value = exact_objective(model, [0] * len(model.candidate_counts))
    exact = cartesian_optimum(mutant, limit=16)
    assert zero_witness_value == 46
    assert exact["assignments"] == 16 and exact["optimum"] == 43
    rejected = False
    try:
        closed_form_optimum(mutant)
    except ValueError as exc:
        rejected = "frozen control geometry" in str(exc)
    assert rejected, "mutated control was incorrectly accepted by the closed form"

    result = {
        "frozen_controls_matched": matched,
        "mutant_case": mutant["name"],
        "mutant_change": "v0 candidate 1 xy [5,5] -> [1,5]",
        "mutant_assignments_enumerated": exact["assignments"],
        "mutant_zero_witness_value": zero_witness_value,
        "mutant_true_optimum": exact["optimum"],
        "mutant_closed_form_rejected": rejected,
        "dependencies": "closed-form modules import only Python standard-library paths; no NumPy/SciPy or milp_oracle import",
    }
    path = ROOT / "results" / "control-oracle-guard.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
