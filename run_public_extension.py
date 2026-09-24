"""Frozen four-orientation public-portfolio robustness extension."""
from __future__ import annotations
import argparse
import json
import math
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src")]
from instances import core_public_case
from milp_oracle import solve_milp
from producer import BudgetExceeded
from response_cover import MODES, solve
from response_checker import verify

CIRCUITS = ("hp", "n10", "apte", "xerox")
LAYOUTS = ("balanced", "netaware")
LIMITS = dict(max_joins=50000, max_states=10000, max_comparisons=500000, seconds=15)


def cases():
    upstream = ROOT / "data" / "upstream" / "core"
    return [core_public_case(upstream, circuit, layout, "orientation4")
            for circuit in CIRCUITS for layout in LAYOUTS]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="results/public-portfolio-extension")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error("output directory must be absent or empty")
    out.mkdir(parents=True, exist_ok=True)
    (out / "inputs").mkdir()
    (out / "certificates").mkdir()
    resource.setrlimit(resource.RLIMIT_AS, (3500 * 1024 * 1024, 3500 * 1024 * 1024))

    rows = []
    oracle_rows = []
    started = time.process_time()
    for case in cases():
        name = case["name"]
        (out / "inputs" / (name + ".json")).write_text(json.dumps(case, sort_keys=True) + "\n")
        oracle = solve_milp(case, time_limit=30)
        if oracle["status"] != "optimal":
            raise RuntimeError(name + ": MILP oracle not optimal")
        assignments = math.prod(len(region["candidates"]) for region in case["regions"])
        oracle["cartesian_assignments_not_enumerated"] = assignments
        oracle_rows.append(oracle)
        for mode in MODES:
            begin = time.process_time()
            record = {"case": name, "mode": mode, "truth_optimum": oracle["optimum"]}
            try:
                certificate, stats = solve(case, mode, **LIMITS)
                check = verify(case, certificate, max_joins=LIMITS["max_joins"], max_states=LIMITS["max_states"], seconds=30)
                if certificate["optimum"] != oracle["optimum"] or check["optimum"] != oracle["optimum"]:
                    raise AssertionError("certificate optimum differs from MILP oracle")
                encoded = json.dumps(certificate, sort_keys=True, separators=(",", ":")) + "\n"
                (out / "certificates" / (name + "_" + mode + ".json")).write_text(encoded)
                record.update(status="success", producer=stats, checker=check,
                              certificate_bytes=len(encoded.encode()))
            except BudgetExceeded as exc:
                record.update(status="limit", reason=str(exc))
            except Exception as exc:
                record.update(status="failure", reason=type(exc).__name__ + ": " + str(exc))
            record["total_cpu_seconds"] = time.process_time() - begin
            rows.append(record)
            (out / "records.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(name + ": " + ",".join(row["mode"] + "=" + row["status"] for row in rows[-4:]), flush=True)

    by = {(row["case"], row["mode"]): row for row in rows}
    completed_pairs = []
    for case in cases():
        name = case["name"]
        leaf, response = by[name, "leaf"], by[name, "response"]
        if leaf["status"] == response["status"] == "success":
            completed_pairs.append({
                "case": name,
                "leaf_transitions": leaf["producer"]["transitions"],
                "response_transitions": response["producer"]["transitions"],
                "delta": leaf["producer"]["transitions"] - response["producer"]["transitions"],
                "optimum": response["producer"]["optimum"],
            })
    summary = {
        "cases": 8,
        "jobs": len(rows),
        "success": sum(row["status"] == "success" for row in rows),
        "limit": sum(row["status"] == "limit" for row in rows),
        "failure": sum(row["status"] == "failure" for row in rows),
        "milp_optimal": len(oracle_rows),
        "cartesian_assignments_not_enumerated": sum(row["cartesian_assignments_not_enumerated"] for row in oracle_rows),
        "completed_leaf_response_pairs": len(completed_pairs),
        "response_fewer": sum(row["delta"] > 0 for row in completed_pairs),
        "ties": sum(row["delta"] == 0 for row in completed_pairs),
        "response_greater": sum(row["delta"] < 0 for row in completed_pairs),
        "limits": LIMITS,
        "cpu_seconds": time.process_time() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    (out / "milp-oracles.json").write_text(json.dumps(oracle_rows, indent=2, sort_keys=True) + "\n")
    (out / "leaf-response-pairs.json").write_text(json.dumps(completed_pairs, indent=2, sort_keys=True) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    assert summary["failure"] == 0


if __name__ == "__main__":
    main()
