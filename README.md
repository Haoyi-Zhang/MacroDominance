# Surrogate-Free Feasibility

This standalone artifact implements and checks the finite-portfolio results in
*Self-Context Dominance Certificates for Hierarchical Macro-Placement
Portfolios*. It is an exact-integer study of selecting one explicitly supplied,
locally legal placement per disjoint owner region to minimize weighted point-pin
HPWL. It is not a general macro placer, an OpenROAD plugin, a routed-quality
study, or an industrial-flow claim.

## What is certified

At each hierarchy node, a row retains an actual partial-placement witness, its
raw live-net boxes, a normalized response key, and a closed cost. The producer
supports four pruning policies:

- `equality`: merge only identical response keys;
- `containment`: a sufficient box-inclusion rule;
- `leaf`: exact response dominance at leaves and equality above them; and
- `response`: exact relaxed response dominance at every node.

Every retained row cites an actual leaf alternative or verified child pair.
Every generated transition has a coverage edge to a retained row. The replay
checker independently reconstructs geometry, node transitions, row costs, and
target self-context response differences; it imports neither the producer nor
its positive-part dominance routine. An accepted root row therefore certifies
the exact optimum **within the supplied finite portfolios**, subject to the
explicit resource bounds used for that run.

The written proofs establish exact exterior-extremum ranges, response-preserving
normalization, the common self-context maximum, compositional closure, the
minimal actual-response frontier, certificate soundness, a coNP-complete
actual-context boundary, and an explicit exponential response-frontier family.
They are mathematical arguments with finite executable checks, not a
proof-assistant formalization.

## Independent optimum routes

The artifact deliberately uses four distinct optimum routes where applicable:

1. a Cartesian oracle that evaluates complete assignments by pairwise pin
   diameters and imports no dynamic-program code;
2. closed-form lower/upper-bound arguments for the frozen `biased`, `masked`,
   and `exposed` controls;
3. the response-frontier producer plus independent coverage replay; and
4. a separately parsed one-hot MILP with net-extremum variables, solved through
   `scipy.optimize.milp` and HiGHS.

The MILP path re-evaluates the selected candidate vector with exact integer
arithmetic, requires optimal status, zero reported MIP gap, and agreement of the
reported primal and dual values with that exact witness. Because the solver
interface is floating point, this optional oracle rejects coefficients or a
worst-case objective bound outside an explicit `2**52` exact-in-double envelope.
The integer dynamic program has its own wider input contract. A solver status is
not a proof log, and all routes still share the declared mathematical model and
development authorship.

## Requirements and resource contract

The producer, replay checker, Cartesian oracle, closed-form checks, and all
original campaigns use Python 3 and the standard library only. The independent
MILP cross-check additionally requires NumPy and SciPy as listed in
`requirements-milp.txt`; SciPy and HiGHS license notices are retained under
`licenses/`. No source optimizer, GPU, model API, OpenROAD executable, or
network access is required.

Run one process at a time and constrain numerical-library threads:

```sh
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

The frozen response campaigns use 50,000 generated transitions, 10,000 retained
rows per node, 500,000 dominance comparisons, a 15-second producer deadline,
a 30-second replay deadline, and a 3,500 MiB process address-space cap. A cap is
an incomplete bounded computation, never evidence of layout infeasibility.

## Fast integrity and correctness checks

From the repository root:

```sh
python tests/pilot_algebra.py
python tests/test_suite.py
python tests/pilot_dominance.py
python tests/test_dominance.py
python tests/test_context_hardness.py
python tests/test_frontier.py
python tests/test_actual_context_gap.py
python tests/test_order_invariance.py
python tests/test_public_inputs.py
python tests/test_milp_oracle.py
python validate_dominance.py results/dominance-campaign
python validate_results.py results/campaign
python validate_results.py results/null-baseline --methods constant_raw
python validate_milp_oracle.py --report results/milp-oracle-validation.json
python validate_public_extension.py results/public-portfolio-extension \
  --report results/public-portfolio-extension-validation.json
python audit_artifact.py
```

A single certificate can be produced and replayed with:

```sh
python src/response_cover.py \
  data/cases/openroad_macro_only_balanced.json /tmp/response.json \
  --mode response
python src/response_checker.py \
  data/cases/openroad_macro_only_balanced.json /tmp/response.json
```

## Robustness audits outside the performance campaign

Two finite audits target common reviewer concerns without enlarging the frozen
performance sample. `tests/test_order_invariance.py` permutes region records and
every candidate list on 23 inputs. Across all four policies, 92 paired runs and
184 replayed certificates preserve the exact optimum, every retained
(key,cost) response function, and all per-node transition/state counts.

`tests/test_actual_context_gap.py` enumerates every realizable exterior
completion for 1,746 ordered pairs of actual partial rows over 33 small cases.
It checks that actual maximum excess never exceeds the relaxed self-context
excess. It also records 11 actual dominance relations missed by the relaxation,
including one mutual actual equivalence absent from the relaxed relation. These
are soundness and conservatism audits, not an unbounded actual-context solver or
additional practical benchmark evidence.

## Reproduce the 77-case response campaign

Use a new empty destination. Expected results are read only by the final
comparison, never by the producer.

```sh
python run_dominance.py --out results/dominance-reproduction
python validate_dominance.py results/dominance-reproduction
python compare_dominance.py \
  results/dominance-campaign results/dominance-reproduction
python analyze_dominance.py
```

The frozen campaign contains 77 case/hierarchy inputs and four policies: 308
jobs, 293 successful certificates, 15 structural caps, and no uncategorized
failures. Replay checks 114,482 transition-coverage obligations. Fifty-one cases
have Cartesian optima totaling 176,128 complete assignments. The remaining 26
synthetic controls have written closed-form optima and explicit attaining
witnesses.

On the forty prospectively selected coupled generated cases, transition totals
for Equality, Containment, Leaf-only Response, and All-level Response are
37,645, 13,940, 4,363, and 2,152. All-level Response uses fewer transitions than
Leaf-only in 32 cases and ties in eight. These are deterministic work counts,
not a universal runtime claim; dominance comparisons and transient storage also
consume work, and under equal caps two Response jobs versus one Leaf job are
limited.

## Reproduce the independent MILP cross-check

```sh
python run_milp_oracle.py --out results/milp-reproduction.json
python validate_milp_oracle.py results/milp-reproduction.json
python compare_milp_oracle.py \
  results/milp-oracle.json results/milp-reproduction.json
```

All 77 frozen inputs terminate with optimal status, zero reported gap, matching
primal/dual values, and an exact integer witness recheck. They agree with all 51
Cartesian and 26 closed-form optima. A separate test-only differential suite
uses 40 new quarter-turn instances, 38,737 complete assignments, the MILP, the
Cartesian oracle, the all-level producer, and replay; six malformed, oversized,
or numerically unsafe inputs are rejected. Solver witness tie choices, branch-and-bound paths,
timing, and RSS are intentionally excluded from deterministic equality.

## Reproduce the four-orientation public extension

The extension protocol was frozen in
`proofs/public-portfolio-extension-protocol.md` before its new producer, checker,
or MILP outcomes were inspected. It retains all four previously imported CORE
hypergraphs (`hp`, `n10`, `apte`, and `xerox`), both frozen hierarchy rules, and
supplies R0/R90/R180/R270 candidates in square disjoint owners.

```sh
python run_public_extension.py \
  --out results/public-portfolio-extension-reproduction
python validate_public_extension.py \
  results/public-portfolio-extension-reproduction
python compare_public_extension.py \
  results/public-portfolio-extension \
  results/public-portfolio-extension-reproduction
```

The eight inputs produce 32 policy runs: 26 successful replayed certificates,
six retained structural caps, and no other failures. Both Leaf and Response
complete on every input; Response uses fewer transitions in all eight. The eight
MILPs are optimal and exact-witness checked. Replay checks 66,570 coverage
obligations. The combined full products contain 13,107,200 assignments and are
not relabeled as Cartesian enumeration. This is a deterministic portfolio-size
sensitivity test on adapted public hypergraphs, not native benchmark placement.

## Reproduce the inherited equality/normalization controls

```sh
python run_experiments.py --out results/reproduction --start 0 --stop 30
python run_experiments.py --out results/reproduction --start 30 --stop 39
python run_experiments.py --out results/reproduction --start 39 --stop 48
python run_experiments.py --out results/reproduction --start 48 --stop 60
python run_experiments.py --out results/reproduction --start 60 --stop 72
python run_experiments.py --out results/reproduction --start 72 --stop 78
python run_experiments.py --out results/reproduction --start 78 --stop 87
python validate_results.py results/reproduction
python compare_results.py results/campaign results/reproduction

python run_experiments.py \
  --out results/null-reproduction --methods constant_raw
python validate_results.py \
  results/null-reproduction --methods constant_raw
python compare_results.py \
  results/null-baseline results/null-reproduction --expected-jobs 29
python summarize_results.py
```

These retained negative controls contain 116 runs, 86 accepted certificates,
and 30 structural caps. Constant-net preprocessing explains the earlier large
masked-family compression, and two-sided clipping alone does not reduce the
OpenROAD tables beyond a one-envelope representation. No later experiment erases
those outcomes.

## Final clean-reproduction receipt

`results/final-clean-reproduction.json` records a fresh-extraction execution of
all fast tests, the 308-job main campaign, the 87-job inherited campaign, the
29-job constant-net control, all 77 MILPs, and the 32-job four-orientation
extension. Comparisons require exact statuses, optima, structural-cap reasons,
deterministic work counts, input bytes, and successful certificate bytes where
applicable. Timing, RSS, solver-selected tied witnesses, and branch-and-bound
paths are excluded. The receipt also records outer execution interruptions and
their fail-closed handling; interrupted output is not treated as evidence.

## Public inputs and adaptation boundary

`data/upstream/` retains the exact public text inputs used by the adapters, and
`licenses/` retains their notices. The OpenROAD case converts one-pin rectangles
to centers at 2,000 database units per micrometre and constructs fixed disjoint
R0/R180 owners. The CORE adapter preserves block dimensions and macro-only
hypergraph incidence, removes fixed terminals, collapses repeated induced
hyperedges to integer weights, and assigns sorted incident nets cyclically to
four quarter-offset pin sites. The two- and four-orientation portfolios and all
owner boxes are newly constructed experiment inputs.

`hp` and `n10` were adapter-development sources; `apte` was inspected after the
orientation rule was frozen; `xerox` was selected in a written post-freeze
extension before algorithmic outcomes. These controls reduce outcome-guided
construction risk but do not create independent replication. No source
placement, native pin geometry, routing, timing, congestion, power, thermal, or
tapeout result is claimed.

## Evidence map and repository map

- `proofs/core.md`: exterior ranges, normalization, closure, complexity, and
  retained counterexamples.
- `proofs/response-dominance.md`: self-context, frontier, composition,
  certificate, and explicit lower-bound arguments.
- `proofs/context-hardness.md`: actual-context coNP-completeness reduction.
- `proofs/control-optima.md`: independent synthetic-control optima.
- `proofs/*protocol.md`: frozen comparisons and falsification rules.
- `src/producer.py`, `src/response_cover.py`: exact producers.
- `src/checker.py`, `src/response_checker.py`: separately implemented replay.
- `src/milp_oracle.py`: independent one-hot MILP parser and exact witness check.
- `tests/`: Cartesian, frontier, mutation, reduction, public-input, and
  differential MILP tests.
- `results/`: every retained success, cap, certificate, validation, and derived
  table input.
- `claim_evidence_ledger.csv`: claim-to-proof/test/result map.
- `reference-audit.csv`: 64 cited scholarly records and supported clauses.
- `reference-verification.csv`: one row per bibliography key with citation count,
  manuscript lines, identifier/metadata status, source, and context check.
- `literature-calibration.csv` / `.md`: non-overlapping 12 TCAD + 5
  influential/foundational + 5 adjacent full-paper calibration.
- `external_resources.csv`: provenance, access mode, license, and integration
  record for every external source.

The root `LICENSE` governs original code and proof text. Upstream terms remain
unchanged. The artifact contains no invented hosted repository, cached model
output, proof-assistant claim, or assertion of external blind review.

## Interpretation boundary

The exact result concerns only explicit finite portfolios in pairwise
disjoint owners. It does not construct those portfolios, negotiate owner
boundaries, legalize arbitrary macros, optimize standard cells, or evaluate
routing, timing, congestion, power, or thermal constraints. HPWL is evaluated
exactly for the declared point pins but remains a routing proxy. Agreement among
Cartesian, closed-form, replay, and MILP routes reduces selected implementation
risks; it does not establish venue acceptance, industrial value, or an
independent novelty judgment.
