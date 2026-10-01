"""Standard-library parser and exact integer HPWL evaluator for portfolio inputs.

This module has no NumPy/SciPy dependency.  It is shared by the closed-form
control guard and the optional MILP wrapper, but it is not imported by the
producer or either replay checker.  Sharing this parser means the closed-form
and MILP routes are not independent parsing implementations from each other;
they remain separate from the dynamic-program/replay implementation paths.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class InvalidPortfolioInstance(ValueError):
    """Raised when an input violates the exact finite-portfolio JSON contract."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidPortfolioInstance(message)


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidPortfolioInstance("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path: str | Path) -> Any:
    path = Path(path)
    _need(path.is_file(), "input is not a file")
    _need(path.stat().st_size <= 64 * 1024 * 1024, "input exceeds 64 MiB")
    return json.loads(
        path.read_text(),
        object_pairs_hook=_strict_object,
        parse_constant=lambda token: (_ for _ in ()).throw(InvalidPortfolioInstance(token)),
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
    raise InvalidPortfolioInstance("rotation must be 0, 90, 180, or 270")


@dataclass(frozen=True)
class ParsedPortfolio:
    name: str
    weights: dict[str, int]
    # region_alternatives[region][candidate] = tuple(net, x, y) per pin occurrence
    region_alternatives: tuple[tuple[tuple[tuple[str, int, int], ...], ...], ...]
    candidate_counts: tuple[int, ...]
    pin_count: int


def parse_instance(data: Any) -> ParsedPortfolio:
    """Validate geometry and derive every candidate pin coordinate exactly."""
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
                coordinates.append((net, xy[0] + dx, xy[1] + dy))
            region_alts.append(tuple(coordinates))
        alternatives.append(tuple(region_alts))
        counts.append(len(region_alts))

    weights = data["weights"]
    _need(type(weights) is dict and set(weights) == seen_nets, "weights must cover exactly all nets")
    _need(all(type(net) is str and net and _integer(weight) and weight > 0 for net, weight in weights.items()), "positive integer net weights")

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
