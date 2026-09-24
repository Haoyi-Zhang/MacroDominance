"""Frozen response-coverage campaign inventory.

This module contains only deterministic case construction.  It lets the
producer, validators, and artifact audit reconstruct the same inventory without
reading expected outcomes.
"""
from __future__ import annotations
from pathlib import Path
from instances import random_small, public_case, core_public_case, exposed, masked
from dominance_instances import biased

GENERATED_SEEDS = tuple(range(100, 140))
OPENROAD_LAYOUTS = ('balanced', 'columns', 'chain')
CORE_CIRCUITS = ('hp', 'n10', 'apte', 'xerox')
CORE_LAYOUTS = ('balanced', 'netaware')
CONTROL_SIZES = (2, 4, 6, 8)
CONTROL_ALTERNATIVES = (2, 4)


def dominance_cases(root: Path):
    """Return ``(all_cases, oracle_names)`` in the frozen execution order."""
    oracle_group = [random_small(seed, 6, 4) for seed in GENERATED_SEEDS]
    oracle_group += [public_case(root / 'data/upstream', layout)
                     for layout in OPENROAD_LAYOUTS]
    oracle_group += [core_public_case(root / 'data/upstream/core', circuit, layout)
                     for circuit in CORE_CIRCUITS for layout in CORE_LAYOUTS]
    controls = [family(k, q)
                for family in (biased, masked, exposed)
                for k in CONTROL_SIZES for q in CONTROL_ALTERNATIVES]
    controls += [exposed(8, q, True) for q in CONTROL_ALTERNATIVES]
    cases = oracle_group + controls
    names = [case['name'] for case in cases]
    if len(names) != len(set(names)):
        raise ValueError('duplicate campaign case name')
    oracle_names = {case['name'] for case in oracle_group}
    if len(cases) != 77 or len(oracle_names) != 51:
        raise AssertionError('frozen campaign inventory changed')
    return cases, oracle_names
