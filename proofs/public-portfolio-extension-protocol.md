# Frozen four-orientation public-portfolio extension protocol

## Decision point and purpose

This protocol was written before running any four-orientation producer, checker,
or MILP result. The existing two-candidate R0/R180 public cases had already been
inspected. The extension therefore is not a pristine preregistration and is not
presented as an independent replication. Its purpose is narrower: test whether
the reported pruning relation survives a deterministic increase in each public
owner's local portfolio size, and obtain an exact cross-check on public cases too
large for the existing Cartesian oracle limit.

## Included sources

Use exactly the four already retained CORE-distributed macro hypergraphs: MCNC
`hp`, MCNC `apte`, MCNC `xerox`, and GSRC `n10`. Use both already specified
hierarchies for every topology: lexical balanced and deterministic topology-only
net-aware. No topology or hierarchy may be removed after outcomes are observed.
This yields eight case/hierarchy inputs.

## Adapter frozen before outcomes

Preserve the same block dimensions, terminal removal, macro-only hypergraph,
duplicate-edge weights, sorted incident-net order, and quarter-offset pin sites as
the two-candidate adapter. For a block of width `w` and height `h`, place it at the
lower-left corner of a square owner of side `max(w,h)`. Supply exactly four
candidates at that same origin with rotations R0, R90, R180, and R270. Place
owners on a nonoverlapping deterministic grid. These are newly constructed finite
portfolios, not native benchmark placements or CORE optimizer outputs.

## Comparisons and fixed limits

Run Equality, Box Inclusion, Leaf-only Response, and All-level Response under the
same per-job structural limits used by the frozen campaign: 50,000 generated
transitions, 10,000 retained states, 500,000 dominance comparisons, and 15 wall
seconds. Replay every successful certificate with the independent checker.
Run the separately implemented MILP oracle on every input with a 30-second limit,
require solver status optimal, reported zero MIP gap, equal primal and dual bounds
within tolerance, and exact integer re-evaluation of its selected candidate vector.

The complete products contain 4^9 through 4^11 assignments, all above the
200,000-assignment test limit used here; therefore no case is to be relabeled as
Cartesian-enumerated.

## Outcomes and falsification

Record every success, structural cap, and uncategorized failure. Compare
All-level Response primarily with Leaf-only Response using generated transitions
for pairs where both complete. Report separately the number of cases in which
Response uses fewer, equal, or more transitions, and the number of method-specific
caps. A tie, regression, or additional Response cap is retained and weakens the
empirical claim. No timing speedup, native benchmark quality, routing, timing,
congestion, or industrial-scale claim follows from this extension.
