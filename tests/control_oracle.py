"""Closed-form optima for the frozen synthetic control families.

The formulas are independent of both dynamic-program implementations.  Each
recognized case is also evaluated at an explicit attaining assignment so that an
incorrect name/geometry pairing cannot silently enter the evidence table.
"""
from __future__ import annotations

import re
from milp_oracle import parse_instance, exact_objective


def closed_form_optimum(instance):
    name = instance.get("name", "") if type(instance) is dict else ""
    match = re.fullmatch(r"(biased|masked|exposed)_(\d+)_(\d+)(?:_paired)?", name)
    if not match:
        raise ValueError("not a recognized frozen control")
    family, k_text, q_text = match.groups()
    k, q = int(k_text), int(q_text)
    model = parse_instance(instance)
    counts = model.candidate_counts
    if family == "biased":
        if len(counts) != 2 * k or counts != tuple([q, 2] * k):
            # The construction orders all variable owners, then all anchors.
            if counts != tuple([q] * k + [2] * k):
                raise ValueError("biased family inventory mismatch")
        value = 29 * k
        witness = tuple([0] * len(counts))
    elif family == "masked":
        if len(counts) != k + 2 or counts != tuple([q] * k + [1, 1]):
            raise ValueError("masked family inventory mismatch")
        value = k * (q + 20)
        witness = tuple([0] * len(counts))
    else:
        if len(counts) != 2 * k or counts != tuple([q] * k + [2] * k):
            raise ValueError("exposed family inventory mismatch")
        value = 23 * k
        witness = tuple([0] * len(counts))
    attained = exact_objective(model, witness)
    if attained != value:
        raise AssertionError((name, value, attained))
    return {"case": name, "family": family, "optimum": value, "attaining_choices": list(witness)}
