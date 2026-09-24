"""Differential tests for the independent MILP formulation."""
from __future__ import annotations
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from campaign import dominance_cases
from control_oracle import closed_form_optimum
from instances import random_small
from milp_oracle import InvalidMilpInstance, parse_instance, solve_milp
from oracle import optimum as cartesian_optimum
from response_cover import solve as response_solve
from response_checker import verify as response_verify


def main():
    started = time.process_time()
    campaign, oracle_names = dominance_cases(ROOT)
    campaign_checks = cartesian_checks = analytic_checks = 0
    for case in campaign:
        answer = solve_milp(case, time_limit=30)
        assert answer["status"] == "optimal" and answer["mip_gap"] <= 1e-10
        if case["name"] in oracle_names:
            truth = cartesian_optimum(case, limit=200000)
            cartesian_checks += 1
        else:
            truth = closed_form_optimum(case)
            analytic_checks += 1
        assert answer["optimum"] == truth["optimum"]
        campaign_checks += 1

    # New seeds are test-only differential instances and never enter the paper's
    # frozen performance campaign.  They exercise all quarter-turn rotations.
    fuzz_cases = 0
    fuzz_assignments = 0
    for seed in range(1000, 1040):
        rng = random.Random(seed)
        n = rng.choice((3, 4, 5, 6))
        q = rng.choice((2, 3, 4))
        case = random_small(seed, n, q)
        truth = cartesian_optimum(case, limit=200000)
        answer = solve_milp(case, time_limit=30)
        assert answer["status"] == "optimal" and answer["optimum"] == truth["optimum"]
        # Check the all-level certificate on the same independently solved input.
        certificate, _ = response_solve(case, "response", max_joins=200000, max_states=20000, max_comparisons=2000000, seconds=30)
        replay = response_verify(case, certificate, max_joins=200000, max_states=20000, seconds=30)
        assert replay["optimum"] == answer["optimum"]
        fuzz_cases += 1
        fuzz_assignments += truth["assignments"]

    # Reject an independent set of malformed inputs, including a broken tree and
    # nonintegral candidate schema.  Existing producer/checker mutation suites are
    # separate and do not satisfy this oracle-specific obligation.
    malformed = []
    base = random_small(4242, 3, 2)
    bad = json.loads(json.dumps(base)); bad["weights"][next(iter(bad["weights"]))] = 0; malformed.append(bad)
    bad = json.loads(json.dumps(base)); bad["tree"] = [bad["regions"][0]["id"], bad["regions"][0]["id"]]; malformed.append(bad)
    bad = json.loads(json.dumps(base)); bad["regions"][0]["candidates"][0][0]["rotation"] = 45; malformed.append(bad)
    bad = json.loads(json.dumps(base)); bad["regions"][0]["box"][2] = bad["regions"][0]["box"][0]; malformed.append(bad)
    # The optional numerical oracle deliberately rejects coefficients outside the
    # exact-in-double envelope, even though the integer DP has a wider contract.
    bad = json.loads(json.dumps(base))
    shift = 2**53
    region = bad["regions"][0]
    region["box"] = [value + shift if index in (0, 2) else value for index, value in enumerate(region["box"])]
    for candidate in region["candidates"]:
        for placement in candidate:
            placement["xy"][0] += shift
    malformed.append(bad)
    bad = json.loads(json.dumps(base))
    bad["regions"][0]["candidates"] = bad["regions"][0]["candidates"] * 17
    malformed.append(bad)
    rejected = 0
    for case in malformed:
        try:
            parse_instance(case)
        except InvalidMilpInstance:
            rejected += 1
        else:
            raise AssertionError("malformed MILP input accepted")

    payload = {
        "campaign_cases": campaign_checks,
        "campaign_cartesian_checks": cartesian_checks,
        "campaign_closed_form_checks": analytic_checks,
        "differential_fuzz_cases": fuzz_cases,
        "differential_fuzz_assignments": fuzz_assignments,
        "rejected_malformed": rejected,
        "cpu_seconds": time.process_time() - started,
        "scope": "finite differential testing; SciPy/HiGHS optimal status is not a proof log",
    }
    (ROOT / "results" / "milp-oracle-tests.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
