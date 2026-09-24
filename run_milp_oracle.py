"""Run the independent SciPy/HiGHS MILP oracle on frozen campaign inputs."""
from __future__ import annotations
import argparse
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from milp_oracle import read_json, solve_milp
from control_oracle import closed_form_optimum
from oracle import optimum as cartesian_optimum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", default="results/dominance-campaign/inputs")
    parser.add_argument("--out", default="results/milp-oracle.json")
    parser.add_argument("--seconds", type=float, default=30.0)
    args = parser.parse_args()
    inputs = Path(args.inputs)
    files = sorted(inputs.glob("*.json"))
    if not files:
        parser.error("no input JSON files")
    resource.setrlimit(resource.RLIMIT_AS, (3500 * 1024 * 1024, 3500 * 1024 * 1024))
    started = time.process_time()
    records = []
    categories = {"cartesian": 0, "closed_form": 0}
    assignments = 0
    for path in files:
        data = read_json(path)
        evidence = solve_milp(data, time_limit=args.seconds)
        if evidence["status"] != "optimal":
            raise RuntimeError(path.name + ": " + evidence["message"])
        truth = None
        try:
            truth = closed_form_optimum(data)
            category = "closed_form"
        except ValueError:
            truth = cartesian_optimum(data, limit=200000)
            category = "cartesian"
            assignments += truth["assignments"]
        if evidence["optimum"] != truth["optimum"]:
            raise AssertionError((path.name, evidence["optimum"], truth["optimum"]))
        categories[category] += 1
        evidence["independent_truth"] = category
        evidence["truth_optimum"] = truth["optimum"]
        if category == "cartesian":
            evidence["cartesian_assignments"] = truth["assignments"]
        records.append(evidence)
        print(f"{path.stem}: {evidence['optimum']} ({category})", flush=True)
    payload = {
        "scope": "independent MILP cross-check of every frozen 77-case campaign input",
        "records": records,
        "summary": {
            "cases": len(records),
            "optimal": sum(r["status"] == "optimal" for r in records),
            "zero_gap": sum(r.get("mip_gap") is not None and r["mip_gap"] <= 1e-10 for r in records),
            "exact_witness_rechecks": sum(bool(r.get("exact_witness_recheck")) for r in records),
            "primal_dual_agreements": sum(bool(r.get("primal_dual_agree")) for r in records),
            "truth_categories": categories,
            "cartesian_assignments": assignments,
            "cpu_seconds": time.process_time() - started,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "boundary": "SciPy/HiGHS optimal status is an independent numerical solver result, not a proof-logged certificate.",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
