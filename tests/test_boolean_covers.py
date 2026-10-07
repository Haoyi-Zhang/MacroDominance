"""Finite Boolean-predicate regression; no performance campaign or timing.

The test-local reference evaluates interval union spans at the target context,
not the producer's positive-part expression. All fixtures are constructed here.
Clocks are fixed only inside tests; production deadlines remain unchanged.
"""
from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import response_cover as rc
from response_checker import verify
from producer import BudgetExceeded, InvalidInstance, Model
from oracle import optimum


def span_excess(left, right, weights):
    value = left.cost - right.cost
    for a, context in zip(left.key, right.key):
        assert a[0] == context[0]
        for lo, hi in ((1, 2), (3, 4)):
            lower = min((a[lo], context[lo]))
            upper = max((a[hi], context[hi]))
            target_span = context[hi] - context[lo]
            value += weights[context[0]] * (upper - lower - target_span)
    return value


def reference_covers(left, right, weights, mode):
    if mode == "equality":
        return left.key == right.key and left.cost <= right.cost
    if mode == "containment":
        return left.cost <= right.cost and all(
            a[1] >= b[1] and a[2] <= b[2] and a[3] >= b[3] and a[4] <= b[4]
            for a, b in zip(left.key, right.key))
    return span_excess(left, right, weights) <= 0


def predicate_cases():
    # Canonical lower/upper endpoints can cross; they are not raw geometry.
    boxes = list(itertools.product((-1, 2), repeat=4))
    for a, b, delta, weight in itertools.product(
            boxes, boxes, (-6, -1, 0, 1, 6), (1, 3, 2**59)):
        yield (SimpleNamespace(key=(("e", *a),), cost=delta),
               SimpleNamespace(key=(("e", *b),), cost=0), {"e": weight})
    rng = random.Random(801)
    for _ in range(2048):
        keys = [tuple((net, *(rng.randrange(-4, 5) for _ in range(4)))
                      for net in ("a", "b", "c")) for _ in range(2)]
        yield (SimpleNamespace(key=keys[0], cost=rng.randrange(-40, 41)),
               SimpleNamespace(key=keys[1], cost=rng.randrange(-40, 41)),
               {"a": 1, "b": 3, "c": 7})
    for delta in (-1, 0, 1):
        yield SimpleNamespace(key=(), cost=delta), SimpleNamespace(key=(), cost=0), {}


def region(name, y, pins=True, fixed=False):
    macro = "m_" + name
    return {"id": name, "box": [0, y, 12, y + 6],
            "macros": [{"id": macro, "size": [2, 3],
                        "pins": ([{"id": "p", "net": "a", "offset": [0, 1]},
                                  {"id": "q", "net": "b", "offset": [2, 2]}]
                                 if pins else [])}],
            "candidates": [[{"macro": macro, "xy": [x, y + 1], "rotation": r}]
                           for x, r in ([(1, 0)] if fixed else
                                        [(1, 0), (6, 90), (3, 180), (8, 270)])]}


def fixtures():
    coupled = {"name": "boolean_coupled", "regions": [region("r0", 0), region("r1", 10),
                                                         region("r2", 20)],
               "weights": {"a": 1, "b": 3}, "tree": [["r0", "r1"], "r2"]}
    fixed = copy.deepcopy(coupled)
    fixed["name"] = "boolean_fixed_exterior"
    fixed["regions"][2] = region("r2", 20, fixed=True)
    wide = copy.deepcopy(fixed)
    wide["name"] = "boolean_wide_weights"
    wide["weights"] = {"a": 2**59, "b": 2**59}
    pinless = {"name": "boolean_pinless", "regions": [region("r0", 0, pins=False)],
               "weights": {}, "tree": "r0"}
    singleton = copy.deepcopy(pinless)
    singleton["name"] = "boolean_singleton"
    singleton["regions"][0]["macros"][0]["pins"] = [
        {"id": "p", "net": "a", "offset": [0, 1]}]
    singleton["weights"] = {"a": 1}
    return [coupled, fixed, wide, pinless, singleton]


def run_case(data, mode, **limits):
    # Patching the shared time module also fixes independent replay's clocks.
    with patch.object(rc.time, "perf_counter", return_value=0), \
            patch.object(rc.time, "process_time", return_value=0):
        try:
            cert, stats = rc.solve(data, mode, **limits)
        except BudgetExceeded as exc:
            return {"capped": str(exc)}
        replay = verify(data, cert, max_joins=1000, max_states=1000, seconds=1)
        return {"certificate": cert, "stats": stats, "replay": replay}


def snapshot():
    """Actual-code outputs for an external, private before/current comparison."""
    outcomes = []
    for data in fixtures():
        truth = optimum(data, limit=64)
        for mode in rc.MODES:
            complete = run_case(data, mode, max_joins=1000, max_states=1000,
                                max_comparisons=10000, seconds=1)
            assert complete["certificate"]["optimum"] == truth["optimum"]
            outcomes.append([data["name"], mode, complete, truth])
            for cap, stat in (("max_joins", "transitions"), ("max_states", "max_states"),
                              ("max_comparisons", "comparisons")):
                boundary = (max(n["peak_online_states"] for n in complete["stats"]["per_node"])
                            if cap == "max_states" else complete["stats"][stat])
                for value in sorted({1, max(1, boundary - 1), max(1, boundary)}):
                    limits = dict(max_joins=1000, max_states=1000, max_comparisons=10000, seconds=1)
                    limits[cap] = value
                    outcomes.append([data["name"], mode, cap, value, run_case(data, mode, **limits)])
    with patch.object(rc.time, "perf_counter", side_effect=[0, 2]), \
            patch.object(rc.time, "process_time", return_value=0):
        try:
            rc.solve(fixtures()[0], seconds=1)
        except BudgetExceeded as exc:
            deadline = str(exc)
        else:
            raise AssertionError("deadline must fail closed")
    return {"predicates": [[rc.covers(a, b, w, mode) for mode in rc.MODES] + [rc.excess(a, b, w)]
                           for a, b, w in predicate_cases()],
            "outcomes": outcomes, "deadline": deadline}


class BooleanCoversTests(unittest.TestCase):
    def test_independent_span_reference_and_numeric_excess(self):
        for a, b, weights in predicate_cases():
            self.assertEqual(rc.excess(a, b, weights), span_excess(a, b, weights))
            for mode in rc.MODES:
                self.assertEqual(rc.covers(a, b, weights, mode), reference_covers(a, b, weights, mode))

    def test_valid_positive_prefix_stops_without_changing_numeric_excess(self):
        class TrackedKey(tuple):
            def __iter__(self):
                for row in super().__iter__():
                    visited.append(row[0])
                    yield row
        visited = []
        a = SimpleNamespace(key=TrackedKey((("a", 0, 0, 0, 0), ("b", 0, 0, 0, 0))), cost=0)
        b = SimpleNamespace(key=(("a", 1, 1, 0, 0), ("b", 2, 2, 0, 0)), cost=0)
        self.assertFalse(rc.covers(a, b, {"a": 1, "b": 3}, "response"))
        self.assertEqual(visited, ["a"])
        visited.clear()
        self.assertEqual(rc.excess(a, b, {"a": 1, "b": 3}), 7)
        self.assertEqual(visited, ["a", "b"])
        visited.clear()
        a.cost = 1
        self.assertFalse(rc.covers(a, b, {"a": 1, "b": 3}, "response"))
        self.assertEqual(visited, [])

    def test_certificates_counters_caps_and_oracle(self):
        actual = snapshot()
        with patch.object(rc, "covers", reference_covers):
            self.assertEqual(actual, snapshot())

    def test_invalid_weights_remain_model_rejections(self):
        for weight in (0, -1, True, 1.5):
            data = fixtures()[0]
            data["weights"]["a"] = weight
            with self.assertRaises(InvalidInstance):
                Model(data)


if __name__ == "__main__":
    unittest.main()
