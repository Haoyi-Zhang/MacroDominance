"""Exact finite audit of relaxed versus realizable exterior contexts.

For small instances, enumerate every exterior portfolio completion for every
ordered pair of actual partial rows.  The relaxed self-context excess must be
an upper bound on the largest difference over realizable completions.  This
checks soundness and measures conservatism; it is not an algorithm for the
unbounded actual-context problem.
"""
from __future__ import annotations
import itertools
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from checker import Replay, enc
from instances import random_small, pin, single_region


def relaxed_excess(left, right, weights):
    """Independent direct evaluation at the target row's self-context."""
    value = left["cost"] - right["cost"]
    for a, b in zip(left["key"], right["key"]):
        assert a[0] == b[0]
        for lo, hi in ((1, 2), (3, 4)):
            value += weights[b[0]] * (
                max(a[hi], b[hi]) - min(a[lo], b[lo]) - (b[hi] - b[lo])
            )
    return value


def exact_objective(model, witness):
    """Full HPWL from reconstructed integer pin coordinates, without DP code."""
    points = {net: [] for net in model.weights}
    for region, choice in witness:
        for net, coordinates in model.points[region][choice].items():
            points[net].extend(coordinates)
    total = 0
    for net, coordinates in points.items():
        assert coordinates
        total += model.weights[net] * sum(
            max(point[axis] for point in coordinates)
            - min(point[axis] for point in coordinates)
            for axis in (0, 1)
        )
    return total


def conflict_instance():
    """The legal (x) AND (not x) correlation example from the paper."""
    bottom_pins = [pin("p0", "e0", 0, 0), pin("p1", "e1", 0, 0)]
    upper_pins = bottom_pins + [pin("local", "local", 0, 0)]
    macros = [
        {"id": "bottom", "size": [1, 1], "pins": bottom_pins},
        {"id": "upper", "size": [1, 1], "pins": upper_pins},
        {"id": "anchor", "size": [1, 1], "pins": [pin("local", "local", 0, 0)]},
    ]
    candidates = [
        [
            {"macro": "bottom", "xy": [0, 0], "rotation": 0},
            {"macro": "upper", "xy": [x, 0], "rotation": 0},
            {"macro": "anchor", "xy": [3, 0], "rotation": 0},
        ]
        for x in (1, 2)
    ]
    inside = {
        "id": "inside",
        "box": [0, 0, 4, 2],
        "macros": macros,
        "candidates": candidates,
    }
    variable = single_region(
        "x1",
        [0, 10, 4, 12],
        [1, 1],
        [pin("positive", "e0", 1, 0), pin("negative", "e1", 0, 0)],
        [([1, 10], 0), ([1, 10], 180)],
    )
    return {
        "name": "actual_context_conflict",
        "regions": [inside, variable],
        "weights": {"e0": 1, "e1": 1, "local": 1},
        "tree": ["inside", "x1"],
    }


def unique_partial_rows(model, path):
    inside = sorted(model.groups[path])
    rows = {}
    for choices in itertools.product(*(range(len(model.points[r])) for r in inside)):
        witness = tuple(zip(inside, choices))
        row = model.evaluate(path, witness, "support")
        key = enc(row["key"])
        previous = rows.get(key)
        if previous is None or (row["cost"], witness) < (previous[0]["cost"], previous[1]):
            rows[key] = (row, witness)
    return list(rows.values())


def audit_case(data):
    model = Replay(data)
    counters = {
        "nodes": 0,
        "ordered_pairs": 0,
        "relaxed_dominance_pairs": 0,
        "actual_dominance_pairs": 0,
        "actual_not_relaxed_pairs": 0,
        "strict_gap_pairs": 0,
        "nodes_with_conservative_miss": 0,
        "max_relaxation_slack": 0,
    }
    mutual_actual_not_relaxed = 0
    for path in model.order:
        rows = unique_partial_rows(model, path)
        if len(rows) < 2:
            continue
        outside = sorted(set(range(len(model.names))) - model.groups[path])
        exterior_choices = list(
            itertools.product(*(range(len(model.points[r])) for r in outside))
        ) if outside else [()]
        responses = []
        for _, witness in rows:
            responses.append([
                exact_objective(
                    model,
                    tuple(sorted(witness + tuple(zip(outside, choices)))),
                )
                for choices in exterior_choices
            ])
        node_miss = False
        actual_matrix = [[None] * len(rows) for _ in rows]
        relaxed_matrix = [[None] * len(rows) for _ in rows]
        for p_index, (p, _) in enumerate(rows):
            for q_index, (q, _) in enumerate(rows):
                if p_index == q_index:
                    continue
                relaxed = relaxed_excess(p, q, model.weights)
                actual = max(
                    p_value - q_value
                    for p_value, q_value in zip(responses[p_index], responses[q_index])
                )
                # Every realizable context lies in the marginal product domain.
                assert actual <= relaxed
                relaxed_matrix[p_index][q_index] = relaxed
                actual_matrix[p_index][q_index] = actual
                counters["ordered_pairs"] += 1
                counters["relaxed_dominance_pairs"] += relaxed <= 0
                counters["actual_dominance_pairs"] += actual <= 0
                counters["strict_gap_pairs"] += actual < relaxed
                counters["max_relaxation_slack"] = max(
                    counters["max_relaxation_slack"], relaxed - actual
                )
                if actual <= 0 < relaxed:
                    counters["actual_not_relaxed_pairs"] += 1
                    node_miss = True
        for p_index in range(len(rows)):
            for q_index in range(p_index + 1, len(rows)):
                if (
                    actual_matrix[p_index][q_index] <= 0
                    and actual_matrix[q_index][p_index] <= 0
                    and (
                        relaxed_matrix[p_index][q_index] > 0
                        or relaxed_matrix[q_index][p_index] > 0
                    )
                ):
                    mutual_actual_not_relaxed += 1
        counters["nodes"] += 1
        counters["nodes_with_conservative_miss"] += node_miss
    counters["mutual_actual_equivalences_not_relaxed"] = mutual_actual_not_relaxed
    return counters


def main():
    started = time.process_time()
    cases = [conflict_instance()] + [random_small(seed, 4, 3) for seed in range(1000, 1032)]
    total = {
        "cases": len(cases),
        "cases_with_conservative_miss": 0,
        "nodes": 0,
        "ordered_pairs": 0,
        "relaxed_dominance_pairs": 0,
        "actual_dominance_pairs": 0,
        "actual_not_relaxed_pairs": 0,
        "strict_gap_pairs": 0,
        "nodes_with_conservative_miss": 0,
        "mutual_actual_equivalences_not_relaxed": 0,
        "max_relaxation_slack": 0,
    }
    records = []
    for case in cases:
        record = audit_case(case)
        record["name"] = case["name"]
        records.append(record)
        total["cases_with_conservative_miss"] += record["actual_not_relaxed_pairs"] > 0
        for key in (
            "nodes",
            "ordered_pairs",
            "relaxed_dominance_pairs",
            "actual_dominance_pairs",
            "actual_not_relaxed_pairs",
            "strict_gap_pairs",
            "nodes_with_conservative_miss",
            "mutual_actual_equivalences_not_relaxed",
        ):
            total[key] += record[key]
        total["max_relaxation_slack"] = max(
            total["max_relaxation_slack"], record["max_relaxation_slack"]
        )

    # The explicit correlation example must exhibit the paper's claimed strict gap.
    conflict = records[0]
    assert conflict["actual_not_relaxed_pairs"] >= 2
    assert conflict["mutual_actual_equivalences_not_relaxed"] >= 1
    assert total["actual_dominance_pairs"] >= total["relaxed_dominance_pairs"]
    assert total["actual_not_relaxed_pairs"] > 0
    total.update(
        cpu_seconds=time.process_time() - started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope=(
            "finite exact enumeration of actual exterior portfolio products; "
            "not an unbounded actual-context dominance algorithm"
        ),
        records=records,
    )
    (ROOT / "results" / "actual-context-gap.json").write_text(
        json.dumps(total, indent=2, sort_keys=True) + "\n"
    )
    summary = {key: value for key, value in total.items() if key != "records"}
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
