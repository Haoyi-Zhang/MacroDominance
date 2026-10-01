"""Measure transient online-frontier growth versus final table size."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from dominance_instances import online_frontier_stress
from oracle import optimum as cartesian_optimum
from response_checker import verify
from response_cover import solve


def main():
    rows = []
    for k in (3, 7, 15, 31):
        for reverse in (False, True):
            case = online_frontier_stress(k, reverse)
            truth = cartesian_optimum(case, limit=1000)
            certificate, stats = solve(
                case,
                "response",
                max_joins=1000,
                max_states=1000,
                max_comparisons=100000,
                seconds=30,
            )
            replay = verify(case, certificate, max_joins=1000, max_states=1000, seconds=30)
            assert truth["optimum"] == certificate["optimum"] == replay["optimum"] == 11
            measured_peak = max(node["peak_online_states"] for node in stats["per_node"])
            inside = next(node for node in stats["per_node"] if node["transitions"] == k + 1)
            expected = {
                "transitions": k + 5,
                "final_s_max": 2,
                "inside_final_rows": 1,
                "inside_peak": 1 if reverse else k,
                "global_peak": 2 if reverse else k,
                "comparisons": (k + 3) if reverse else (k * (k + 1) + 3),
            }
            actual = {
                "transitions": stats["transitions"],
                "final_s_max": stats["max_states"],
                "inside_final_rows": inside["states"],
                "inside_peak": inside["peak_online_states"],
                "global_peak": measured_peak,
                "comparisons": stats["comparisons"],
            }
            assert actual == expected, (case["name"], actual, expected)
            rows.append({
                "case": case["name"],
                "k": k,
                "candidate_order": "reverse" if reverse else "forward",
                "assignments_enumerated": truth["assignments"],
                "optimum": truth["optimum"],
                "predicted": expected,
                "measured": actual,
                "prediction_matched": True,
                "per_node": stats["per_node"],
                "replayed_transitions": replay["replayed_transitions"],
            })
    payload = {
        "construction": "legal two-owner unit-square width-one online-frontier stress case",
        "rows": rows,
        "forward_formula": {
            "M": "k+5",
            "final_S_max": 2,
            "inside_P": "k",
            "comparisons": "k(k+1)+3",
        },
        "reverse_formula": {
            "M": "k+5",
            "final_S_max": 2,
            "inside_P": 1,
            "global_P": 2,
            "comparisons": "k+3",
        },
        "scope": "measured finite executions for k in {3,7,15,31}; not an unbounded test",
    }
    path = ROOT / "results" / "online-frontier-peak.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
