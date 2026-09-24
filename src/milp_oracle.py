"""Independent mixed-integer oracle for finite placement portfolios.

This module deliberately imports neither the dynamic-program producer nor either
certificate checker.  It translates the original placement JSON directly into a
one-hot mixed-integer linear program and re-evaluates the returned witness using
integer arithmetic.  SciPy's ``optimize.milp`` provides the numerical optimizer;
its reported optimality status is treated as an independent cross-check, not as a
proof log.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


class InvalidMilpInstance(ValueError):
    """Raised when an input violates the independently checked JSON contract."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidMilpInstance(message)


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidMilpInstance("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path: str | Path) -> Any:
    path = Path(path)
    _need(path.is_file(), "input is not a file")
    _need(path.stat().st_size <= 64 * 1024 * 1024, "input exceeds 64 MiB")
    return json.loads(
        path.read_text(),
        object_pairs_hook=_strict_object,
        parse_constant=lambda token: (_ for _ in ()).throw(InvalidMilpInstance(token)),
    )


def _integer(value: Any) -> bool:
    return type(value) is int and abs(value) < 2**60


def _overlap(a, b) -> bool:
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _transform(width: int, height: int, x: int, y: int, rotation: int) -> tuple[int, int]:
    if rotation == 0:
        return x, y
    if rotation == 90:
        return height - y, x
    if rotation == 180:
        return width - x, height - y
    if rotation == 270:
        return y, width - x
    raise InvalidMilpInstance("rotation must be 0, 90, 180, or 270")


@dataclass(frozen=True)
class ParsedPortfolio:
    name: str
    weights: dict[str, int]
    # region_alternatives[region][candidate] = tuple(net, x, y) per pin occurrence
    region_alternatives: tuple[tuple[tuple[tuple[str, int, int], ...], ...], ...]
    candidate_counts: tuple[int, ...]
    pin_count: int


def parse_instance(data: Any) -> ParsedPortfolio:
    """Validate geometry and derive every candidate pin coordinate independently."""
    _need(type(data) is dict, "top-level JSON object required")
    _need(set(data) <= {"name", "regions", "weights", "tree", "provenance"}, "unknown instance field")
    _need({"name", "regions", "weights", "tree"} <= set(data), "missing instance field")
    _need(type(data["name"]) is str and data["name"], "nonempty text name required")
    regions = data["regions"]
    _need(type(regions) is list and 1 <= len(regions) <= 48, "1..48 regions required")

    owner_boxes = []
    region_ids = []
    macro_ids = set()
    seen_nets = set()
    alternatives = []
    counts = []
    pin_count = 0

    for region in regions:
        _need(type(region) is dict and set(region) == {"id", "box", "macros", "candidates"}, "region fields")
        rid = region["id"]
        _need(type(rid) is str and rid and rid not in region_ids, "unique nonempty region id")
        region_ids.append(rid)
        box = region["box"]
        _need(type(box) is list and len(box) == 4 and all(_integer(v) for v in box), "integer owner box")
        _need(box[0] < box[2] and box[1] < box[3], "positive owner box")
        _need(not any(_overlap(box, old) for old in owner_boxes), "owner regions overlap")
        owner_boxes.append(tuple(box))

        macros = region["macros"]
        _need(type(macros) is list and macros, "nonempty macro list")
        definitions = {}
        occurrence_order = []
        for macro in macros:
            _need(type(macro) is dict and set(macro) == {"id", "size", "pins"}, "macro fields")
            mid = macro["id"]
            _need(type(mid) is str and mid and mid not in macro_ids and mid not in definitions, "globally unique macro id")
            macro_ids.add(mid)
            size = macro["size"]
            _need(type(size) is list and len(size) == 2 and all(_integer(v) and v > 0 for v in size), "positive integer macro size")
            pins = macro["pins"]
            _need(type(pins) is list, "pin list")
            local_ids = set()
            parsed_pins = []
            for pin in pins:
                _need(type(pin) is dict and set(pin) == {"id", "net", "offset"}, "pin fields")
                pid, net, offset = pin["id"], pin["net"], pin["offset"]
                _need(type(pid) is str and pid and pid not in local_ids, "unique pin id within macro")
                local_ids.add(pid)
                _need(type(net) is str and net, "nonempty net id")
                _need(type(offset) is list and len(offset) == 2 and all(_integer(v) for v in offset), "integer pin offset")
                _need(0 <= offset[0] <= size[0] and 0 <= offset[1] <= size[1], "pin offset outside macro")
                parsed_pins.append((pid, net, tuple(offset)))
                occurrence_order.append((mid, len(parsed_pins) - 1, net, tuple(offset)))
                seen_nets.add(net)
                pin_count += 1
            definitions[mid] = (tuple(size), tuple(parsed_pins))

        candidates = region["candidates"]
        _need(type(candidates) is list and 1 <= len(candidates) <= 32, "1..32 candidates per region required")
        region_alts = []
        for candidate in candidates:
            _need(type(candidate) is list and len(candidate) == len(definitions), "candidate macro coverage")
            placements = {}
            occupied = []
            for placement in candidate:
                _need(type(placement) is dict and set(placement) == {"macro", "xy", "rotation"}, "placement fields")
                mid = placement["macro"]
                _need(type(mid) is str and mid in definitions and mid not in placements, "candidate macro identity")
                xy, rotation = placement["xy"], placement["rotation"]
                _need(type(xy) is list and len(xy) == 2 and all(_integer(v) for v in xy), "integer placement coordinate")
                _need(type(rotation) is int and rotation in (0, 90, 180, 270), "quarter-turn rotation")
                width, height = definitions[mid][0]
                placed_width, placed_height = (height, width) if rotation in (90, 270) else (width, height)
                rect = (xy[0], xy[1], xy[0] + placed_width, xy[1] + placed_height)
                _need(box[0] <= rect[0] < rect[2] <= box[2] and box[1] <= rect[1] < rect[3] <= box[3], "macro outside owner")
                _need(not any(_overlap(rect, old) for old in occupied), "local macro overlap")
                occupied.append(rect)
                placements[mid] = (tuple(xy), rotation)
            _need(set(placements) == set(definitions), "candidate misses macro")

            coordinates = []
            for mid, pin_index, net, offset in occurrence_order:
                size, pins = definitions[mid]
                _need(pins[pin_index][1] == net and pins[pin_index][2] == offset, "internal occurrence mismatch")
                xy, rotation = placements[mid]
                dx, dy = _transform(size[0], size[1], offset[0], offset[1], rotation)
                px, py = xy[0] + dx, xy[1] + dy
                _need(abs(px) < 2**52 and abs(py) < 2**52,
                      "MILP coordinate exceeds exact-in-double envelope")
                coordinates.append((net, px, py))
            region_alts.append(tuple(coordinates))
        alternatives.append(tuple(region_alts))
        counts.append(len(region_alts))

    weights = data["weights"]
    _need(type(weights) is dict and set(weights) == seen_nets, "weights must cover exactly all nets")
    _need(all(type(net) is str and net and _integer(weight) and weight > 0 for net, weight in weights.items()), "positive integer net weights")

    # The MILP optimum does not depend on the hierarchy, but independently check
    # that the supplied tree is a binary tree containing each region exactly once.
    leaves = []
    def walk(tree, depth=0):
        _need(depth <= 48, "tree depth")
        if type(tree) is str:
            _need(tree in region_ids, "unknown tree leaf")
            leaves.append(tree)
            return
        _need(type(tree) is list and len(tree) == 2, "binary tree required")
        walk(tree[0], depth + 1)
        walk(tree[1], depth + 1)
    walk(data["tree"])
    _need(len(leaves) == len(region_ids) and len(set(leaves)) == len(leaves) and set(leaves) == set(region_ids), "tree must cover every region once")

    return ParsedPortfolio(
        name=data["name"],
        weights=dict(weights),
        region_alternatives=tuple(alternatives),
        candidate_counts=tuple(counts),
        pin_count=pin_count,
    )


def exact_objective(model: ParsedPortfolio, choices: tuple[int, ...] | list[int]) -> int:
    """Evaluate one selected candidate vector using only exact integer arithmetic."""
    _need(len(choices) == len(model.region_alternatives), "choice-vector length")
    by_net = {net: [] for net in model.weights}
    for region_index, candidate_index in enumerate(choices):
        _need(type(candidate_index) is int and 0 <= candidate_index < model.candidate_counts[region_index], "candidate index")
        for net, x, y in model.region_alternatives[region_index][candidate_index]:
            by_net[net].append((x, y))
    total = 0
    for net, weight in model.weights.items():
        points = by_net[net]
        _need(points, "net without pins")
        total += weight * (
            max(x for x, _ in points) - min(x for x, _ in points)
            + max(y for _, y in points) - min(y for _, y in points)
        )
    return total


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
