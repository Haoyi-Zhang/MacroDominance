"""Replay and validate the frozen four-orientation public extension."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src")]
from milp_oracle import read_json, solve_milp
from response_checker import verify
from checker import read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="results/public-portfolio-extension")
    parser.add_argument("--report")
    args = parser.parse_args()
    root = Path(args.directory)
    rows = read(root / "records.json")
    summary = read(root / "summary.json")
    oracles = {row["case"]: row for row in read(root / "milp-oracles.json")}
    assert len(rows) == summary["jobs"] == 32
    assert len({(row["case"], row["mode"]) for row in rows}) == 32
    assert len({row["case"] for row in rows}) == summary["cases"] == len(oracles) == 8
    expected_certificates = set()
    accepted = caps = obligations = 0
    for case_name, oracle in oracles.items():
        data = read_json(root / "inputs" / (case_name + ".json"))
        fresh = solve_milp(data, time_limit=30)
        assert fresh["status"] == "optimal" and fresh["optimum"] == oracle["optimum"]
        assert fresh["mip_gap"] <= 1e-10 and fresh["primal_dual_agree"]
    for row in rows:
        if row["status"] == "limit":
            assert row["reason"].startswith(("coverage transition limit", "coverage comparison limit", "coverage state limit", "coverage wall-time limit"))
            caps += 1
            continue
        assert row["status"] == "success", row
        name = row["case"] + "_" + row["mode"] + ".json"
        expected_certificates.add(name)
        packet = read(root / "certificates" / name)
        checked = verify(read(root / "inputs" / (row["case"] + ".json")), packet,
                         max_joins=50000, max_states=10000, seconds=30)
        assert checked["optimum"] == row["truth_optimum"] == oracles[row["case"]]["optimum"]
        assert checked["replayed_transitions"] == row["producer"]["transitions"]
        assert (root / "certificates" / name).stat().st_size == row["certificate_bytes"]
        accepted += 1
        obligations += checked["dominance_obligations"]
    assert {path.name for path in (root / "certificates").iterdir()} == expected_certificates
    assert accepted == summary["success"] and caps == summary["limit"] and summary["failure"] == 0
    pairs = read(root / "leaf-response-pairs.json")
    assert summary["completed_leaf_response_pairs"] == len(pairs)
    assert summary["response_fewer"] == sum(row["delta"] > 0 for row in pairs)
    assert summary["ties"] == sum(row["delta"] == 0 for row in pairs)
    assert summary["response_greater"] == sum(row["delta"] < 0 for row in pairs)
    result={"accepted":accepted,"structural_caps":caps,"milp_oracles":8,
            "dominance_obligations":obligations,
            "completed_leaf_response_pairs":len(pairs)}
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.report: Path(args.report).write_text(text)
    print(json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
