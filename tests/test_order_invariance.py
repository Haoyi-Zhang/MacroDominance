"""Candidate/owner serialization-order invariance for all four policies.

The geometry is unchanged while region records and each candidate list are
permuted.  Optima, retained response functions, and per-node work counts must
remain invariant.  Witness indices and coverage edges may change.
"""
from __future__ import annotations
import copy
import json
import random
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from checker import enc
from instances import public_case, random_small
from response_checker import verify
from response_cover import MODES, solve


def permute_serialization(data, seed):
    transformed = copy.deepcopy(data)
    rng = random.Random(seed)
    rng.shuffle(transformed["regions"])
    for region in transformed["regions"]:
        rng.shuffle(region["candidates"])
    transformed["name"] += "_serialization_permuted"
    return transformed


def table_signature(certificate):
    return {
        table["node"]: sorted(
            (enc(row["key"]), row["cost"]) for row in table["rows"]
        )
        for table in certificate["tables"]
    }


def structural_stats(stats):
    return [
        (row["node"], row["transitions"], row["states"])
        for row in stats["per_node"]
    ]


def main():
    started = time.process_time()
    cases = [random_small(2000 + index, 4, 3) for index in range(20)]
    cases.extend(
        public_case(ROOT / "data" / "upstream", layout)
        for layout in ("balanced", "columns", "chain")
    )
    comparisons = certificates = replayed = 0
    records = []
    for index, case in enumerate(cases):
        transformed = permute_serialization(case, 9000 + index)
        for mode in MODES:
            original_certificate, original_stats = solve(case, mode)
            transformed_certificate, transformed_stats = solve(transformed, mode)
            original_replay = verify(case, original_certificate)
            transformed_replay = verify(transformed, transformed_certificate)
            assert original_certificate["optimum"] == transformed_certificate["optimum"]
            assert table_signature(original_certificate) == table_signature(transformed_certificate)
            assert structural_stats(original_stats) == structural_stats(transformed_stats)
            assert original_stats["transitions"] == transformed_stats["transitions"]
            assert original_stats["total_states"] == transformed_stats["total_states"]
            assert original_replay["optimum"] == transformed_replay["optimum"]
            comparisons += 1
            certificates += 2
            replayed += (
                original_replay["replayed_transitions"]
                + transformed_replay["replayed_transitions"]
            )
            records.append(
                {
                    "case": case["name"],
                    "mode": mode,
                    "optimum": original_certificate["optimum"],
                    "transitions": original_stats["transitions"],
                    "states": original_stats["total_states"],
                }
            )
    payload = {
        "cases": len(cases),
        "modes": list(MODES),
        "paired_comparisons": comparisons,
        "certificates_verified": certificates,
        "replayed_transitions": replayed,
        "invariance_failures": 0,
        "cpu_seconds": time.process_time() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "scope": "serialization-order metamorphic test; geometry and hierarchy unchanged",
        "records": records,
    }
    (ROOT / "results" / "order-invariance.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({k: v for k, v in payload.items() if k != "records"}, sort_keys=True))


if __name__ == "__main__":
    main()
