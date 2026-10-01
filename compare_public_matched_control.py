"""Compare deterministic outputs and exact assets for the square-grid R0/R180 control."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SUMMARY_FIELDS = (
    "case_pairs",
    "subset_policy_jobs",
    "subset_success",
    "subset_limit",
    "subset_failure",
    "matched_geometry_verified",
    "four_le_two_verified",
    "original_four_way_records_unchanged",
    "limits",
)
PRODUCER_FIELDS = (
    "mode",
    "optimum",
    "transitions",
    "comparisons",
    "total_states",
    "max_states",
    "per_node",
)
CHECKER_FIELDS = (
    "accepted",
    "optimum",
    "replayed_transitions",
    "retained_row_evaluations",
    "dominance_obligations",
)
ORACLE_FIELDS = (
    "case",
    "status",
    "solver_status",
    "variables",
    "binary_variables",
    "constraints",
    "regions",
    "candidates",
    "nets",
    "pins",
    "objective_upper_bound",
    "optimum",
    "exact_witness_recheck",
    "primal_dual_agree",
)


def read(path: Path):
    return json.loads(path.read_text())


def files(path: Path):
    return {item.name: item.read_bytes() for item in path.glob("*.json")}


def compare(expected: Path, fresh: Path) -> dict:
    left_summary = read(expected / "summary.json")
    right_summary = read(fresh / "summary.json")
    for field in SUMMARY_FIELDS:
        if left_summary[field] != right_summary[field]:
            raise ValueError(f"summary field differs: {field}")

    left_rows = {(row["case"], row["mode"]): row for row in read(expected / "records.json")}
    right_rows = {(row["case"], row["mode"]): row for row in read(fresh / "records.json")}
    if set(left_rows) != set(right_rows) or len(left_rows) != 16:
        raise ValueError("record inventory differs")
    for key in sorted(left_rows):
        left, right = left_rows[key], right_rows[key]
        for field in ("case", "circuit", "layout", "mode", "truth_optimum", "status", "reason", "certificate_bytes"):
            if left.get(field) != right.get(field):
                raise ValueError(f"{key}: record field differs: {field}")
        if left["status"] == "success":
            for field in PRODUCER_FIELDS:
                if left["producer"][field] != right["producer"][field]:
                    raise ValueError(f"{key}: producer field differs: {field}")
            for field in CHECKER_FIELDS:
                if left["checker"][field] != right["checker"][field]:
                    raise ValueError(f"{key}: checker field differs: {field}")

    if read(expected / "matched-pairs.json") != read(fresh / "matched-pairs.json"):
        raise ValueError("matched-pair results differ")
    if read(expected / "geometry-audit.json") != read(fresh / "geometry-audit.json"):
        raise ValueError("geometry audit differs")

    left_oracles = {(row["circuit"], row["layout"]): row for row in read(expected / "milp-oracles.json")}
    right_oracles = {(row["circuit"], row["layout"]): row for row in read(fresh / "milp-oracles.json")}
    if set(left_oracles) != set(right_oracles) or len(left_oracles) != 8:
        raise ValueError("MILP-pair inventory differs")
    for key in sorted(left_oracles):
        left, right = left_oracles[key], right_oracles[key]
        if left["four_le_two"] != right["four_le_two"]:
            raise ValueError(f"{key}: four_le_two differs")
        for route in ("four_way", "matched_r0180"):
            for field in ORACLE_FIELDS:
                if left[route].get(field) != right[route].get(field):
                    raise ValueError(f"{key}: {route} field differs: {field}")
            for field in ("solver_objective", "mip_dual_bound"):
                if abs(left[route][field] - right[route][field]) > 1e-5:
                    raise ValueError(f"{key}: {route} field differs: {field}")
            if left[route]["mip_gap"] > 1e-10 or right[route]["mip_gap"] > 1e-10:
                raise ValueError(f"{key}: nonzero MILP gap")

    if files(expected / "inputs") != files(fresh / "inputs"):
        raise ValueError("input bytes differ")
    if files(expected / "certificates") != files(fresh / "certificates"):
        raise ValueError("certificate bytes differ")

    return {
        "compared_subset_jobs": 16,
        "exact_subset_inputs": 8,
        "exact_subset_certificates": 16,
        "exact_geometry_audit": True,
        "exact_matched_pairs": 8,
        "milp_pairs": 8,
        "four_le_two_checks": 8,
        "timing_and_rss_compared": False,
        "solver_witness_choice_compared": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("fresh", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = compare(args.expected, args.fresh)
        text = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.report:
            args.report.write_text(text)
        print(text, end="")
    except (AssertionError, KeyError, OSError, TypeError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
