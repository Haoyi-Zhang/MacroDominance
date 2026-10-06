"""Finite boundary regressions for the exact integer portfolio contract.

These owned inputs are not additions to a frozen performance campaign. No
NumPy/SciPy, source optimizer, network, or Unix resource module is required.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from checker import verify as equality_verify
from instances import pin, single_region
from oracle import optimum
from portfolio_exact import exact_objective, parse_instance
from producer import solve as equality_solve
from response_checker import verify
from response_cover import MODES, solve


def cases():
    pinless = {
        "name": "boundary_pinless", "tree": "r", "weights": {},
        "regions": [single_region("r", [0, 0, 10, 10], [2, 3], [],
                                  [([1, 1], 0), ([4, 4], 90)])],
    }
    singleton = copy.deepcopy(pinless)
    singleton["name"] = "boundary_singleton"
    singleton["regions"][0]["macros"][0]["pins"] = [pin("p", "e", 2, 1)]
    singleton["weights"] = {"e": 1}
    fixed = {
        "name": "boundary_fixed_exterior", "tree": ["inside", "outside"],
        "weights": {"e": 1},
        "regions": [
            single_region("inside", [0, 0, 12, 6], [2, 3], [pin("p", "e", 2, 1)],
                          [([1, 1], 90), ([5, 1], 270)]),
            single_region("outside", [20, 0, 24, 6], [1, 1], [pin("p", "e", 0, 0)],
                          [([20, 3], 0)]),
        ],
    }
    contact = {
        "name": "boundary_contact", "tree": "r", "weights": {"e": 1},
        "regions": [{"id": "r", "box": [0, 0, 3, 2],
                     "macros": [{"id": name, "size": [1, 1],
                                 "pins": [pin("p", "e", 0, 0)]} for name in ("a", "b")],
                     "candidates": [[{"macro": "a", "xy": [x, 0], "rotation": 0},
                                     {"macro": "b", "xy": [x + 1, 0], "rotation": 0}]
                                    for x in (0, 1)]}],
    }
    wide = copy.deepcopy(fixed)
    wide["name"] = "boundary_wide_integer"
    wide["weights"] = {"e": 2**59}
    for region in wide["regions"]:
        region["box"] = [value - 2**59 for value in region["box"]]
        for candidate in region["candidates"]:
            for placement in candidate:
                placement["xy"] = [value - 2**59 for value in placement["xy"]]
    return [(pinless, 0), (singleton, 0), (fixed, 16), (contact, 1), (wide, 16 * 2**59)]


def main():
    started = time.perf_counter()
    assignments = certificates = obligations = 0
    records = []
    for data, expected in cases():
        truth = optimum(data, limit=16)
        assert truth["optimum"] == expected
        assignments += truth["assignments"]
        exact = parse_instance(data)
        assert exact_objective(exact, truth["choices"]) == expected
        for method in ("raw", "envelope", "support"):
            packet, _ = equality_solve(data, method, max_joins=100, max_states=100, seconds=5)
            replay = equality_verify(data, packet, max_joins=100, max_states=100, seconds=5)
            assert packet["optimum"] == replay["optimum"] == expected
            certificates += 1
        for mode in MODES:
            packet, stats = solve(data, mode, max_joins=100, max_states=100,
                                  max_comparisons=1000, seconds=5)
            replay = verify(data, packet, max_joins=100, max_states=100, seconds=5)
            assert packet["optimum"] == replay["optimum"] == expected
            assert stats["transitions"] == replay["dominance_obligations"]
            certificates += 1
            obligations += replay["dominance_obligations"]
        records.append({"case": data["name"], "optimum": expected,
                        "cartesian_assignments": truth["assignments"]})
    print(json.dumps({"cases": len(records), "cartesian_assignments": assignments,
                      "certificates_replayed": certificates,
                      "response_coverage_obligations": obligations,
                      "records": records, "wall_seconds": time.perf_counter() - started,
                      "scope": "finite boundary regressions; not a general proof or performance campaign"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
