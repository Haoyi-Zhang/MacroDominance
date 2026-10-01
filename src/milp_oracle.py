"""Independent mixed-integer oracle for finite placement portfolios.

This module imports neither the dynamic-program producer nor either certificate
checker.  It shares the standard-library exact parser in ``portfolio_exact``
with the closed-form control guard, then translates the parsed portfolio into a
one-hot mixed-integer linear program.  SciPy's ``optimize.milp`` provides the
numerical optimizer; its optimality status is an independent cross-check, not a
proof log.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from portfolio_exact import (
    InvalidPortfolioInstance,
    ParsedPortfolio,
    exact_objective,
    parse_instance,
    read_json,
)

# Backward-compatible public name used by the existing oracle tests and runner.
InvalidMilpInstance = InvalidPortfolioInstance


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidMilpInstance(message)


def solve_milp(data: Any, *, time_limit: float = 30.0) -> dict[str, Any]:
    """Solve the portfolio HPWL problem and return independently checked evidence."""
    _need(type(time_limit) in (int, float) and math.isfinite(time_limit) and time_limit > 0, "positive finite time limit")
    model = parse_instance(data)
    nets = tuple(sorted(model.weights))

    region_offsets = []
    variable_count = 0
    for count in model.candidate_counts:
        region_offsets.append(variable_count)
        variable_count += count

    extrema = {}
    for net in nets:
        for axis in (0, 1):
            extrema[net, axis, "lower"] = variable_count
            variable_count += 1
            extrema[net, axis, "upper"] = variable_count
            variable_count += 1

    objective = np.zeros(variable_count, dtype=float)
    lower = np.full(variable_count, -np.inf, dtype=float)
    upper = np.full(variable_count, np.inf, dtype=float)
    integrality = np.zeros(variable_count, dtype=np.int32)

    for region_index, count in enumerate(model.candidate_counts):
        start = region_offsets[region_index]
        lower[start:start + count] = 0.0
        upper[start:start + count] = 1.0
        integrality[start:start + count] = 1

    coordinate_inventory = {net: {0: [], 1: []} for net in nets}
    for alternatives in model.region_alternatives:
        for candidate in alternatives:
            for net, x, y in candidate:
                coordinate_inventory[net][0].append(x)
                coordinate_inventory[net][1].append(y)
    # The optimization interface is floating-point even though every source value
    # is integral.  Keep this optional cross-check inside an explicit exact-in-double
    # envelope and bound the largest possible integer objective.  The production DP
    # remains exact over its wider integer contract.
    float_exact_limit = 2**52
    _need(all(weight < float_exact_limit for weight in model.weights.values()),
          "MILP weight exceeds exact-in-double envelope")
    objective_upper_bound = 0
    for net in nets:
        for axis in (0, 1):
            coordinates = coordinate_inventory[net][axis]
            _need(coordinates, "empty coordinate inventory")
            _need(all(abs(value) < float_exact_limit for value in coordinates),
                  "MILP coordinate exceeds exact-in-double envelope")
            objective_upper_bound += model.weights[net] * (max(coordinates) - min(coordinates))
    _need(objective_upper_bound < float_exact_limit,
          "MILP objective bound exceeds exact-in-double envelope")

    for net in nets:
        for axis in (0, 1):
            coordinates = coordinate_inventory[net][axis]
            lo, hi = min(coordinates), max(coordinates)
            low_index = extrema[net, axis, "lower"]
            high_index = extrema[net, axis, "upper"]
            lower[low_index] = lower[high_index] = float(lo)
            upper[low_index] = upper[high_index] = float(hi)
            objective[low_index] = -float(model.weights[net])
            objective[high_index] = float(model.weights[net])

    row_indices = []
    column_indices = []
    coefficients = []
    constraint_lower = []
    constraint_upper = []
    row = 0

    # Select exactly one complete local candidate in each owner region.
    for region_index, count in enumerate(model.candidate_counts):
        start = region_offsets[region_index]
        for candidate_index in range(count):
            row_indices.append(row)
            column_indices.append(start + candidate_index)
            coefficients.append(1.0)
        constraint_lower.append(1.0)
        constraint_upper.append(1.0)
        row += 1

    # For each physical pin occurrence, bound the net extremum against the
    # coordinate induced by the selected candidate of that occurrence's owner.
    for region_index, alternatives in enumerate(model.region_alternatives):
        count = model.candidate_counts[region_index]
        start = region_offsets[region_index]
        occurrence_count = len(alternatives[0])
        _need(all(len(candidate) == occurrence_count for candidate in alternatives), "candidate pin occurrence mismatch")
        for occurrence in range(occurrence_count):
            net = alternatives[0][occurrence][0]
            _need(all(candidate[occurrence][0] == net for candidate in alternatives), "pin net changes across candidates")
            for axis in (0, 1):
                coordinate_offset = 1 + axis
                # upper(net,axis) >= selected pin coordinate
                row_indices.append(row)
                column_indices.append(extrema[net, axis, "upper"])
                coefficients.append(1.0)
                for candidate_index in range(count):
                    row_indices.append(row)
                    column_indices.append(start + candidate_index)
                    coefficients.append(-float(alternatives[candidate_index][occurrence][coordinate_offset]))
                constraint_lower.append(0.0)
                constraint_upper.append(np.inf)
                row += 1
                # lower(net,axis) <= selected pin coordinate
                row_indices.append(row)
                column_indices.append(extrema[net, axis, "lower"])
                coefficients.append(1.0)
                for candidate_index in range(count):
                    row_indices.append(row)
                    column_indices.append(start + candidate_index)
                    coefficients.append(-float(alternatives[candidate_index][occurrence][coordinate_offset]))
                constraint_lower.append(-np.inf)
                constraint_upper.append(0.0)
                row += 1

    matrix = coo_matrix(
        (coefficients, (row_indices, column_indices)),
        shape=(row, variable_count),
        dtype=float,
    ).tocsr()

    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(matrix, np.asarray(constraint_lower), np.asarray(constraint_upper)),
        options={"time_limit": float(time_limit), "mip_rel_gap": 0.0, "presolve": True},
    )
    wall_seconds = time.perf_counter() - start_wall
    cpu_seconds = time.process_time() - start_cpu

    evidence = {
        "case": model.name,
        "status": "optimal" if bool(result.success) and int(result.status) == 0 else "not_optimal",
        "solver_status": int(result.status),
        "message": str(result.message),
        "variables": int(variable_count),
        "binary_variables": int(sum(model.candidate_counts)),
        "constraints": int(row),
        "regions": len(model.candidate_counts),
        "candidates": int(sum(model.candidate_counts)),
        "nets": len(nets),
        "pins": model.pin_count,
        "objective_upper_bound": int(objective_upper_bound),
        "mip_node_count": None if getattr(result, "mip_node_count", None) is None else int(result.mip_node_count),
        "mip_gap": None if getattr(result, "mip_gap", None) is None else float(result.mip_gap),
        "mip_dual_bound": None if getattr(result, "mip_dual_bound", None) is None else float(result.mip_dual_bound),
        "solver_objective": None if result.fun is None else float(result.fun),
        "cpu_seconds": cpu_seconds,
        "wall_seconds": wall_seconds,
    }
    if evidence["status"] != "optimal" or result.x is None or result.fun is None:
        return evidence

    choices = []
    for region_index, count in enumerate(model.candidate_counts):
        start = region_offsets[region_index]
        values = np.asarray(result.x[start:start + count], dtype=float)
        selected = int(np.argmax(values))
        _need(abs(values[selected] - 1.0) <= 1e-7, "nonintegral selected candidate")
        _need(all(abs(value) <= 1e-7 for index, value in enumerate(values) if index != selected), "nonintegral unselected candidate")
        choices.append(selected)

    exact = exact_objective(model, choices)
    tolerance = 1e-5
    _need(abs(float(result.fun) - exact) <= tolerance, "solver objective disagrees with exact witness")
    _need(evidence["mip_gap"] is not None and evidence["mip_gap"] <= 1e-10, "nonzero reported MIP gap")
    _need(evidence["mip_dual_bound"] is not None, "missing dual bound")
    _need(abs(evidence["mip_dual_bound"] - exact) <= tolerance, "dual bound disagrees with exact witness")

    evidence.update(
        optimum=exact,
        choices=choices,
        exact_witness_recheck=True,
        primal_dual_agree=True,
    )
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance")
    parser.add_argument("--out")
    parser.add_argument("--seconds", type=float, default=30.0)
    args = parser.parse_args()
    try:
        result = solve_milp(read_json(args.instance), time_limit=args.seconds)
        text = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        if args.out:
            Path(args.out).write_text(text)
        print(text, end="")
        if result["status"] != "optimal":
            raise SystemExit(2)
    except (InvalidMilpInstance, KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(2, "MILP ORACLE ERROR: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
