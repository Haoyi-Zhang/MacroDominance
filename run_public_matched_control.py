"""Matched R0/R180 control on the square-grid four-way public geometry.

This does not replace the frozen four-way records.  It constructs a separate
R0/R180 subset on exactly the same owner boxes, macro definitions, point pins,
weights, tree, and candidate coordinates as the four-way instance, then runs
Leaf and Response under the original extension limits.
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src")]

from instances import core_public_case
from milp_oracle import solve_milp
from producer import BudgetExceeded
from response_checker import verify
from response_cover import solve

CIRCUITS = ("hp", "n10", "apte", "xerox")
LAYOUTS = ("balanced", "netaware")
MODES = ("leaf", "response")
LIMITS = dict(max_joins=50000, max_states=10000, max_comparisons=500000, seconds=15)


def _matched(full, subset):
    assert full["weights"] == subset["weights"]
    assert full["tree"] == subset["tree"]
    assert len(full["regions"]) == len(subset["regions"])
    for four_region, two_region in zip(full["regions"], subset["regions"]):
        assert four_region["id"] == two_region["id"]
        assert four_region["box"] == two_region["box"]
        assert four_region["macros"] == two_region["macros"]
        assert len(four_region["candidates"]) == 4
        assert len(two_region["candidates"]) == 2
        assert two_region["candidates"] == [four_region["candidates"][0], four_region["candidates"][2]]
    return True


def _origin(case, region_id):
    region = next(region for region in case["regions"] if region["id"] == region_id)
    placement = region["candidates"][0][0]
    return list(placement["xy"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="results/public-portfolio-matched-control")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error("output directory must be absent or empty")
    out.mkdir(parents=True, exist_ok=True)
    (out / "inputs").mkdir()
    (out / "certificates").mkdir()
    resource.setrlimit(resource.RLIMIT_AS, (3500 * 1024 * 1024, 3500 * 1024 * 1024))

    upstream = ROOT / "data" / "upstream" / "core"
    frozen_dir = ROOT / "results" / "public-portfolio-extension"
    frozen_records = json.loads((frozen_dir / "records.json").read_text())
    frozen_by = {(row["case"], row["mode"]): row for row in frozen_records}

    records = []
    pairs = []
    oracles = []
    geometry = []
    started = time.process_time()
    for circuit in CIRCUITS:
        for layout in LAYOUTS:
            full = core_public_case(upstream, circuit, layout, "orientation4")
            subset = core_public_case(upstream, circuit, layout, "orientation4_r0180")
            assert _matched(full, subset)
            frozen_input = json.loads((frozen_dir / "inputs" / (full["name"] + ".json")).read_text())
            assert frozen_input == full, "regenerated four-way input differs from frozen record"
            (out / "inputs" / (subset["name"] + ".json")).write_text(json.dumps(subset, sort_keys=True) + "\n")

            four_oracle = solve_milp(full, time_limit=30)
            two_oracle = solve_milp(subset, time_limit=30)
            assert four_oracle["status"] == two_oracle["status"] == "optimal"
            assert four_oracle["optimum"] <= two_oracle["optimum"]
            oracles.append({
                "circuit": circuit,
                "layout": layout,
                "four_way": four_oracle,
                "matched_r0180": two_oracle,
                "four_le_two": four_oracle["optimum"] <= two_oracle["optimum"],
            })

            local = {}
            for mode in MODES:
                begin = time.process_time()
                record = {
                    "case": subset["name"],
                    "circuit": circuit,
                    "layout": layout,
                    "mode": mode,
                    "truth_optimum": two_oracle["optimum"],
                }
                try:
                    certificate, stats = solve(subset, mode, **LIMITS)
                    check = verify(subset, certificate, max_joins=LIMITS["max_joins"], max_states=LIMITS["max_states"], seconds=30)
                    assert certificate["optimum"] == check["optimum"] == two_oracle["optimum"]
                    encoded = json.dumps(certificate, sort_keys=True, separators=(",", ":")) + "\n"
                    (out / "certificates" / (subset["name"] + "_" + mode + ".json")).write_text(encoded)
                    record.update(status="success", producer=stats, checker=check, certificate_bytes=len(encoded.encode()))
                except BudgetExceeded as exc:
                    record.update(status="limit", reason=str(exc))
                except Exception as exc:
                    record.update(status="failure", reason=type(exc).__name__ + ": " + str(exc))
                record["total_cpu_seconds"] = time.process_time() - begin
                records.append(record)
                local[mode] = record
                (out / "records.json").write_text(json.dumps(records, indent=2) + "\n")

            full_leaf = frozen_by[full["name"], "leaf"]
            full_response = frozen_by[full["name"], "response"]
            assert full_leaf["status"] == full_response["status"] == "success"
            assert full_leaf["truth_optimum"] == full_response["truth_optimum"] == four_oracle["optimum"]
            pairs.append({
                "circuit": circuit,
                "layout": layout,
                "matched_r0180_case": subset["name"],
                "four_way_case": full["name"],
                "matched_geometry_verified": True,
                "matched_r0180_optimum": two_oracle["optimum"],
                "four_way_optimum": four_oracle["optimum"],
                "four_le_two": four_oracle["optimum"] <= two_oracle["optimum"],
                "matched_r0180_leaf": None if local["leaf"]["status"] != "success" else local["leaf"]["producer"]["transitions"],
                "matched_r0180_response": None if local["response"]["status"] != "success" else local["response"]["producer"]["transitions"],
                "four_way_leaf": full_leaf["producer"]["transitions"],
                "four_way_response": full_response["producer"]["transitions"],
            })
            geometry.append({
                "circuit": circuit,
                "layout": layout,
                "regions": len(full["regions"]),
                "weights_equal": full["weights"] == subset["weights"],
                "tree_equal": full["tree"] == subset["tree"],
                "boxes_macros_pins_equal": True,
                "candidate_subset_indices": [0, 2],
            })
            print(subset["name"] + ": " + ",".join(mode + "=" + local[mode]["status"] for mode in MODES), flush=True)

    original_hp = core_public_case(upstream, "hp", "balanced", "orientation")
    square_hp = core_public_case(upstream, "hp", "balanced", "orientation4")
    origin_audit = {
        "region": "cmp3",
        "two_orientation_rectangular_grid_origin": _origin(original_hp, "cmp3"),
        "four_way_square_grid_origin": _origin(square_hp, "cmp3"),
    }
    (out / "matched-pairs.json").write_text(json.dumps(pairs, indent=2, sort_keys=True) + "\n")
    (out / "milp-oracles.json").write_text(json.dumps(oracles, indent=2, sort_keys=True) + "\n")
    (out / "geometry-audit.json").write_text(json.dumps({"cases": geometry, "hp_cmp3": origin_audit}, indent=2, sort_keys=True) + "\n")
    summary = {
        "case_pairs": len(pairs),
        "subset_policy_jobs": len(records),
        "subset_success": sum(row["status"] == "success" for row in records),
        "subset_limit": sum(row["status"] == "limit" for row in records),
        "subset_failure": sum(row["status"] == "failure" for row in records),
        "matched_geometry_verified": sum(row["matched_geometry_verified"] for row in pairs),
        "four_le_two_verified": sum(row["four_le_two"] for row in pairs),
        "limits": LIMITS,
        "cpu_seconds": time.process_time() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "original_four_way_records_unchanged": True,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    assert summary["subset_failure"] == 0
    assert summary["matched_geometry_verified"] == summary["four_le_two_verified"] == 8


if __name__ == "__main__":
    main()
