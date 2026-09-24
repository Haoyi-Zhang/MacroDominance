# Prospective response-coverage comparison

This protocol was written after the eight development seeds (0--7) and the
three public hierarchy pilot runs, but before running seeds 100--139 or the
scaling controls listed below. The public topology and its hierarchies are
already inspected development evidence, never held-out designs.

The question is whether cross-key cost-response dominance reduces transitions
beyond equality, box containment, and response pruning restricted to leaves.
The primary outcome is exact transition count; secondary outcomes are retained
rows, comparisons, certificate bytes, producer CPU and replay CPU. CPU ratios
are descriptive single runs, not statistically controlled performance claims.

The fixed cases are 40 independent generated seeds 100--139 with six owners
and four alternatives; the three inherited public hierarchies; biased, masked,
and exposed controls for k in {2,4,6,8} and q in {2,4}; and exposed paired
hierarchies at k=8 with q in {2,4}. This original campaign is 69 cases and 276 method cases. The frozen public-topology
first extension below adds six case/hierarchy inputs. A second, prospectively frozen
extension adds two `xerox` hierarchy inputs, yielding 77 cases and 308 method
cases in the combined retained result. All four methods use the original unmodified
marginal support ranges.
One worker; each method gets 50,000 transitions, 10,000 active rows,
500,000 dominance comparisons and a 15-second producer wall limit. The
separate checker gets the same transition/row limits and 30 seconds. These
limits are identical across methods; reaching a cap is not infeasibility.
The campaign is not an attempt to reproduce modern placement engines.

Constant-net preprocessing is already an inherited strong null baseline.
The biased control makes every net nonconstant, but is deliberately also
solvable by the leaf-only comparator. It cannot establish a multilevel-only
advantage. Generated inputs assess a declared mechanism, not workload breadth.
No thresholds, case inclusion or seeds are changed after looking at outcomes.

All successful outputs must replay. For the 40 generated cases and the three
public hierarchies, an independent full Cartesian oracle must match the root
optimum. Every structural cap and checker failure is retained. Retained rows
and transition counts are compared on common successful cases, never by
silently deleting failures. A fresh extraction reruns the complete campaign.

## Public-topology extension frozen before `apte`

The first response-coverage campaign used one OpenROAD regression topology. To
separate topology breadth from repeated hierarchy variants, a later extension
uses normalized text copies of the public MCNC `hp` and `apte` circuits and the
GSRC `n10` circuit distributed by the CORE repository under its non-commercial
license. The source optimizer is not executed. The adapter parses block sizes and
net membership, removes fixed terminals, collapses repeated macro-only hyperedges
into positive integer weights, and retains every placeable block.

Two adapter variants were evaluated in a development pilot on `hp` and `n10`.
The first put every incident pin at the block center and translated the block
between two diagonal positions. It produced monotone leaf eliminations and no
added all-level reduction. This null is retained in
`results/public-adapter-pilot.json`. Before inspecting `apte`, the portfolio
contract was frozen as follows: sort each block's incident induced hyperedges;
cycle their point pins through the lower-left, lower-right, upper-left, and
upper-right quarter-offset sites; place the block in a fixed disjoint owner box;
and use only R0 and R180 candidates. Duplicate source nets remain represented by
weights, not duplicate pins. Coordinates and alternatives are therefore newly
constructed experiment inputs, not source placements or routed pin geometries.

For every CORE circuit, one balanced lexical hierarchy and one deterministic topology-
only hierarchy are used. The latter recursively chooses a floor(n/2) subset
containing the lexicographically first remaining block that minimizes weighted
cut hyperedges; ties are lexicographic. Candidate coordinates, costs, and method
outcomes do not enter the hierarchy. `hp` and `n10` are development cases;
`apte` is the topology held out until this rule was frozen. All four coverage
policies receive the original equal resource limits, every successful result is
replayed, and the full 2^n Cartesian optimum is checked. Both `apte` hierarchy
outcomes are retained regardless of direction. This held-out status concerns only
the adapter decision sequence, not independent authorship or external review.

## Second public extension frozen before `xerox` outcomes

On 2026-09-16, before running any producer, checker, or Cartesian oracle on
`xerox`, the campaign was extended by the public MCNC `xerox` block/net pair.
It was selected because its ten movable blocks make both balanced and frozen
topology-only hierarchy views exactly enumerable ($2^{10}$ assignments each)
within the existing CPU envelope. The already frozen orientation adapter, all
four policies, identical work limits, exact oracle, and replay checker are
unchanged. Both hierarchy outcomes, including limits or regressions, are retained.
The input topology was inspected to verify parseability and licensing before this
amendment; no algorithmic outcome was inspected. This extension tests transfer to
a fifth source topology, not native benchmark placement quality.
