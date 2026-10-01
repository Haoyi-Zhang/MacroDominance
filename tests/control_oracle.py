"""Closed-form optima for the exact frozen synthetic control inputs.

The written lower-bound arguments live in ``proofs/control-optima.md``.  This
module applies those formulas only after reconstructing the named control with
the deterministic constructor and requiring full JSON equality.  Candidate
counts and one attaining assignment alone are not a family-membership test.
The exact parser/evaluator is standard-library only and is shared with the MILP
wrapper; neither the producer nor either replay checker imports it.
"""
from __future__ import annotations

import re

from dominance_instances import biased
from instances import exposed, masked
from portfolio_exact import exact_objective, parse_instance

_FROZEN_K = (2, 4, 6, 8)
_FROZEN_Q = (2, 4)


def _expected_control(family: str, k: int, q: int, paired: bool):
    if k not in _FROZEN_K or q not in _FROZEN_Q:
        raise ValueError("not a frozen control size")
    if family == "biased":
        if paired:
            raise ValueError("biased controls have no paired variant")
        return biased(k, q)
    if family == "masked":
        if paired:
            raise ValueError("masked controls have no paired variant")
        return masked(k, q)
    if family == "exposed":
        if paired and k != 8:
            raise ValueError("only the frozen k=8 exposed controls are paired")
        return exposed(k, q, paired)
    raise ValueError("unknown control family")


def closed_form_optimum(instance):
    name = instance.get("name", "") if type(instance) is dict else ""
    match = re.fullmatch(r"(biased|masked|exposed)_(\d+)_(\d+)(_paired)?", name)
    if not match:
        raise ValueError("not a recognized frozen control")
    family, k_text, q_text, paired_text = match.groups()
    k, q, paired = int(k_text), int(q_text), bool(paired_text)
    expected = _expected_control(family, k, q, paired)
    if instance != expected:
        raise ValueError("frozen control geometry, weights, connectivity, tree, or candidate order mismatch")

    model = parse_instance(instance)
    if family == "biased":
        value = 29 * k
    elif family == "masked":
        value = k * (q + 20)
    else:
        value = 23 * k
    witness = tuple([0] * len(model.candidate_counts))
    attained = exact_objective(model, witness)
    if attained != value:
        raise AssertionError((name, value, attained))
    return {
        "case": name,
        "family": family,
        "optimum": value,
        "attaining_choices": list(witness),
        "family_guard": "full deterministic input match",
    }
