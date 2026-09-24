# Actual-context dominance and its complexity boundary

## Statement
For the unbounded finite-portfolio model with explicit legal owner alternatives,
deciding whether one partial placement has cost response no greater than a
second for **every actual exterior completion** is coNP-complete. This holds
with pairwise interior-disjoint rectangles, unit-square macros, unit net
weights, two alternatives per owner, and clause nets of at most five pins.
Only one inside owner is needed. All coordinates are nonnegative integers
of magnitude linear in the number of exterior owners. This is an asymptotic
statement about the mathematical model, not the prototype's fixed 48-owner
admission bound.

## Membership
Non-dominance has a polynomial witness: choose one explicitly listed candidate
for each exterior owner, reconstruct all pin coordinates and compute both
exact integer HPWL totals. A strictly positive difference is checkable in
polynomial time in the input bit length. Hence dominance is in coNP.

## Reduction
Start from an arbitrary 3-CNF formula F. Conjoin a fresh clause
(y OR y OR y); this preserves satisfiability because the fresh variable can be
set true, and it guarantees that the cleaned formula below is nonempty. Delete
tautological clauses, duplicate literals within a clause, and variables unused
by the remaining clauses. These polynomial transformations preserve
satisfiability and produce a nonempty formula whose clauses contain at most
three distinct variables and no tautology. Let m be the number of clauses and
n the number of variables.
An owner I at [0,4] x [0,2] contains three nonoverlapping unit squares. Their
lower-left coordinates are (0,0), (x,0), (3,0), with x=1 in partial placement P
and x=2 in partial placement Q. Boundaries may touch. Each clause has one pin
at (0,0) and one at (x,0). A separate local net joins (x,0) to (3,0), so its
HPWL in P minus that in Q equals +1. All pin offsets used here are (0,0).

Variable i owns [0,4] x [10i,10i+2], disjoint from every other owner. Its one
unit-square macro has lower-left coordinate (1,10i), with alternatives R0 and
R180. For each positive occurrence of i put a pin with local offset (1,0);
for a negative occurrence use (0,0). The occurrence pin belongs to its clause
net. Interpret R0 as true and R180 as false. The pin's global x coordinate
is exactly 2 when that literal is true, and 1 otherwise. Rotation may change
the y coordinate; this is harmless because P and Q have identical inside y
coordinates. Their vertical HPWL responses therefore cancel for every exterior
completion. Unused variables can simply be removed.

For a clause j, let b_j be the largest x coordinate of its exterior pins.
Then b_j is 2 if the clause is satisfied and 1 if it is not. The inside minimum
is 0 in both P and Q. The horizontal span under P is b_j, while under Q it is
2. Consequently

    F_P(z) - F_Q(z) = 1 + sum_j (b_j(z)-2)
                    = 1 - number_of_unsatisfied_clauses(z).

Wholly exterior nets are absent. All geometric alternatives are individually
legal and all combinations are legal by disjoint ownership. Therefore P fails
to dominate Q exactly when some assignment satisfies all clauses: a satisfying
assignment gives difference +1; every nonsatisfying assignment gives difference
at most 0. This is a polynomial reduction from UNSAT to dominance and proves
coNP-hardness. Together with membership it proves the statement.

## Consequence for the relaxation
Marginally legal exterior boxes can select the best endpoint for every clause
even when no single assignment realizes those choices together. Thus an
exact necessary-and-sufficient actual-context pruning test cannot in general
be obtained by simply renaming the independent relaxed-context test. The
self-context formula in response-dominance.md is linear in the live interface
and exactly characterizes the declared product relaxation; it is deliberately
only sufficient over physically realizable completions.

The executable `tests/test_actual_context_gap.py` also enumerates every
realizable exterior completion for 1,746 ordered row pairs in 33 small cases.
It checks that actual excess never exceeds relaxed excess and records strict
conservatism rather than treating it as a correctness failure. This is again a
finite audit, not an unbounded actual-context algorithm.

The reduction does not prove that all special graphs, bounded-width fragments,
or practical instances are hard. It does not establish a lower bound for
approximate dominance or for the independent marginal relaxation. The hardness
of general constraint reasoning is established background; the contribution
of this construction is its explicit embedding into the narrow point-pin,
unit-weight, disjoint-owner HPWL model.

## Finite implementation check
`tests/test_context_hardness.py` independently reconstructs actual placements
through the checker model and compares the cost difference to the literal
formula on every assignment of a declared finite formula corpus. This tests
the construction and both directions on that corpus; it is not a machine-checked
proof of coNP-completeness.
