"""Validate the square-grid R0/R180 matched public control."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src")]

from instances import core_public_case
from milp_oracle import solve_milp
from response_checker import verify

CIRCUITS = ("hp", "n10", "apte", "xerox")
LAYOUTS = ("balanced", "netaware")
LIMITS = dict(max_joins=50000, max_states=10000, max_comparisons=500000, seconds=15)


def read(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="results/public-portfolio-matched-control")
    parser.add_argument("--report")
    args = parser.parse_args()
    root = Path(args.directory)
    summary = read(root / "summary.json")
    rows = read(root / "records.json")
    pairs = read(root / "matched-pairs.json")
    geometry = read(root / "geometry-audit.json")
    oracles = read(root / "milp-oracles.json")
    assert len(rows) == summary["subset_policy_jobs"] == 16
    assert len(pairs) == len(oracles) == summary["case_pairs"] == 8
    assert geometry["hp_cmp3"] == {
        "region": "cmp3",
        "two_orientation_rectangular_grid_origin": [0, 800],
        "four_way_square_grid_origin": [0, 3404],
    }

    upstream = ROOT / "data" / "upstream" / "core"
    frozen = ROOT / "results" / "public-portfolio-extension"
    by_record = {(row["case"], row["mode"]): row for row in rows}
    accepted = caps = obligations = 0
    for circuit in CIRCUITS:
        for layout in LAYOUTS:
            full = core_public_case(upstream, circuit, layout, "orientation4")
            subset = core_public_case(upstream, circuit, layout, "orientation4_r0180")
            assert read(frozen / "inputs" / (full["name"] + ".json")) == full
            assert read(root / "inputs" / (subset["name"] + ".json")) == subset
            assert full["weights"] == subset["weights"] and full["tree"] == subset["tree"]
            for fregion, sregion in zip(full["regions"], subset["regions"]):
                assert fregion["id"] == sregion["id"]
                assert fregion["box"] == sregion["box"]
                assert fregion["macros"] == sregion["macros"]
                assert sregion["candidates"] == [fregion["candidates"][0], fregion["candidates"][2]]
            full_milp = solve_milp(full, time_limit=30)
            subset_milp = solve_milp(subset, time_limit=30)
            assert full_milp["status"] == subset_milp["status"] == "optimal"
            assert full_milp["optimum"] <= subset_milp["optimum"]
            for mode in ("leaf", "response"):
                row = by_record[subset["name"], mode]
                if row["status"] == "limit":
                    assert row["reason"].startswith(("coverage transition limit", "coverage comparison limit", "coverage state limit", "coverage wall-time limit"))
                    caps += 1
                    continue
                assert row["status"] == "success"
                packet = read(root / "certificates" / (subset["name"] + "_" + mode + ".json"))
                check = verify(subset, packet, max_joins=LIMITS["max_joins"], max_states=LIMITS["max_states"], seconds=30)
                assert check["optimum"] == row["truth_optimum"] == subset_milp["optimum"]
                assert check["replayed_transitions"] == row["producer"]["transitions"]
                obligations += check["dominance_obligations"]
                accepted += 1
    assert accepted == summary["subset_success"]
    assert caps == summary["subset_limit"]
    assert summary["subset_failure"] == 0
    result = {
        "accepted_subset_certificates": accepted,
        "subset_structural_caps": caps,
        "matched_case_pairs": 8,
        "four_le_two_checks": 8,
        "dominance_obligations": obligations,
        "original_four_way_records_unchanged": True,
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        Path(args.report).write_text(text)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
