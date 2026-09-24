# Exact HPWL composition over regional portfolios

## Model and quantifiers

There are finitely many regions. Region r owns a fixed finite set of positive-area
axis-aligned macro rectangles and a nonempty finite set C_r of complete local
placements. Rectangular owner regions have disjoint interiors. Every listed
placement fits its owner and has no interior overlap. Boundary contact is legal.
A pin belongs to one immutable macro and one net; its local offset is transformed
by the selected legal orientation. All net weights are positive. Coordinates and
weights may be rational; the executable representation uses bounded integer
inputs and arbitrary-precision integer intermediates.

A global placement is an element of the Cartesian product of the C_r. There are
no cross-region choice constraints other than a subsequently queried objective
threshold. This independence is essential. A binary hierarchy has the regions as
its leaves exactly once. For a node v, U_v is its set of descendant regions. A net
is live at v if it has pins both in U_v and outside U_v. A net is closed at v if
all its pins lie in U_v. Nets with no inside pins are omitted. For a partial
placement p, C_v(p) is the total weighted HPWL of its closed nets.

Legality follows directly: two macros with the same owner are disjoint by the
local check; macros with different owners lie in sets with disjoint interiors.
No separator signature is needed for legality in this restricted model. This is
not a theorem about arbitrary floorplanning or cross-boundary movable macros.

For one live net and one axis, let [l,u] be the actual inside pin interval. For
an outside placement let [a,b] be its actual outside pin interval. Its full span
is h(l,u;a,b)=max(u,b)-min(l,a). The two axes add, and net weights multiply spans.
Closed-net cost plus these live-net responses describes all dependence on p;
wholly outside net costs are irrelevant to comparisons of partial placements.

## Lemma 1: exact marginal ranges of outside extrema

For each outside region r that touches this net, define m_r(c) and M_r(c) as the
smallest and largest pin coordinates in candidate c. Then the outside minimum a
and maximum b have the following exact marginal ranges:

    a_- = min_r min_c m_r(c)       a_+ = min_r max_c m_r(c)
    b_- = max_r min_c M_r(c)       b_+ = max_r max_c M_r(c).

Proof. The smallest possible minimum is attained by selecting a region/candidate
that contains the smallest possible coordinate. To maximize the minimum, each
outside region may independently select a candidate maximizing its own minimum;
the minimum over these region maxima is both an upper bound and attainable.
The two statements for maxima are the order-dual arguments. Finiteness and
nonempty portfolios ensure that the extrema are attained. There is no assertion
that all four extreme values, different nets, or different axes can be realized
simultaneously. In particular a_- <= b_- and a_+ <= b_+, since every actual
minimum is at most its corresponding actual maximum. QED.

For this axis define the relaxed exterior domain

    D = {(a,b): a in [a_-,a_+], b in [b_-,b_+], a <= b}.

Intervals here are real intervals, even for integer input. The full relaxed
context domain at a node is the product of D over all live nets and axes. It
contains every actual outside context but generally many unrealizable ones.
Empty live-net sets have a single empty context. All support ranges are computed
from the original portfolios, not from a circularly pruned approximation.

## Lemma 2: normalization identity

Define clip(x;A,B)=min(B,max(A,x)) and

    l* = clip(l;a_-,a_+),       u* = clip(u;b_-,b_+),
    delta = max(a_- - l,0) + max(u - b_+,0).

For every (a,b) in D,

    h(l,u;a,b) = delta + h(l*,u*;a,b).

Proof. If l<a_-, then min(l,a)=l=min(l*,a)-(a_- - l). If l is in the
minimum's range, clipping does nothing. If l>a_+, both min(l,a) and min(l*,a)
equal a. These exhaustive cases establish the lower-endpoint term. Dually,
max(u,b)=max(u*,b)+max(u-b_+,0). Subtract the former identity from the latter.
Also l*<=u*: the lower and upper clipping intervals have coordinatewise ordered
ends, and clipping is monotone in its argument and both interval ends. QED.

This identity is about cost responses. It does not say that [l*,u*] contains
actual pins, is a feasible macro placement, or can replace real geometry at a
later join.

## Theorem 3: canonical responses on the relaxed context domain

Let K_v(p) be the joint, net-labelled tuple of all (l*,u*) pairs for both axes.
Define tau_v(p)=C_v(p)+sum_(live e,axis d) weight(e)*delta_(e,d)(p).
For two partial placements p and p', their responses to every relaxed context
are identical if and only if (K_v(p),tau_v(p))=(K_v(p'),tau_v(p')). Their
responses differ by a context-independent constant if and only if their keys
are equal; that constant is the difference of their tau values.

Proof. Lemma 2 expresses the response as tau plus the sum of canonical span
functions, so equal keys immediately imply the asserted constant difference.
For the converse suppose the responses differ by a constant. Hold every net and
axis except one fixed. Fix b=b_+ and vary a over [a_-,a_+]. This is legal because
a_+<=b_+. Apart from constants, the response is -w*min(l*,a). On any nondegenerate
range its slope switches from -w to 0 exactly at the clipped threshold l*; two
different thresholds cannot have a constant difference. When the range is a
singleton, clipping already forces l* to that singleton. Therefore the two
lower thresholds agree. Similarly, fixing a=a_- permits every b in [b_-,b_+]
and identifies u* from the slope of w*max(u*,b). Positive weights are needed.
Repeat independently over the product domain to identify the full joint key.
The remaining constant is the difference of tau values. Equality of complete
responses thus additionally requires equal tau. At a closed root the domain is
a singleton, the key empty, and the same statement reduces to equality of cost.
QED.

The theorem describes the coarsest equivalence under *all relaxed contexts*,
not a minimal encoding for the finitely many actual joint contexts. It also
allows comparisons up to a constant, which is the property needed for dominance
by the least tau in a key class. It does not license independent per-net minima.

## Lemma 4: closure under an actual sibling witness

Let v have children s and t. Fix an actual partial placement of t and any relaxed
context at v. For a net live at s, combine the actual pins of t on the net, when
present, with the parent's context on that net, when present. Their union is a
valid relaxed exterior context for s. A net closing at v uses just the actual
sibling pins. A net without sibling pins uses just the parent context.

Proof. The outside regions of s are the disjoint union of the sibling's regions
and the outside regions of v. When both groups touch the net, Lemma 1 yields

    a_-(s)=min(a_-(t group),a_-(outside v)),
    a_+(s)=min(a_+(t group),a_+(outside v)),
    b_-(s)=max(b_-(t group),b_-(outside v)),
    b_+(s)=max(b_+(t group),b_+(outside v)).

The sibling's actual minimum lies between its two marginal minimum bounds and
its actual maximum between its maximum bounds. The parent-context endpoints
obey their respective ranges by definition. Monotonicity of min and max puts
the union endpoints in the displayed child ranges. Both component intervals
have minimum<=maximum, so their union does too. The argument is axiswise and
netwise. Omitting an absent group leaves its other component unchanged. QED.

This lemma deliberately quantifies over every *relaxed* parent context, not
only realizable global completions. The weaker quantifier would not prove that
the entire parent table, rather than only its final optimum, survives pruning.

## Lemma 5: witness-preserving substitution

At child s replace actual witness p_s by actual witness p'_s with equal key.
For a fixed actual sibling witness, the parent key does not change and its tau
changes by exactly tau_s(p'_s)-tau_s(p_s). In particular a child with smaller
tau safely dominates the other at every ancestor.

Proof. For every relaxed parent context, Lemma 4 provides a valid child context.
Theorem 3 makes the child's response difference the same constant in all these
contexts. Every cost term not touching s is unchanged. Hence the two parent
responses differ by that constant over the full relaxed parent domain. Apply
the converse in Theorem 3 at v to conclude equal parent keys and the asserted
tau difference. If there are no parent live nets, the conclusion is just the
same equality of closed total costs. QED.

## Algorithm and Theorem 6: exact hierarchical optimization

At a leaf, enumerate every local candidate. At an internal node, enumerate every
pair of retained child witnesses. For each generated witness, compute actual
live-net boxes and closed-net cost, normalize with Lemma 2, and retain the least
tau for each joint key. For equal scores retain the lexicographically first
candidate-index vector in the fixed input-region order. Store the chosen real
witness and its raw geometry, not only its canonical key.

For every node and key, the resulting table contains precisely the minimum tau
among all actual partial portfolio choices with that key, with the specified
tie-breaking witness. Therefore the root gives the minimum weighted HPWL over
the complete Cartesian product.

Proof by induction on the hierarchy. At leaves the result is exhaustive. Take
any partial choice at an internal node. For either child its restriction has a
key present in that child's table by induction. Replace that restriction by the
retained child witness. Lemma 5 preserves the parent key and cannot increase
parent tau. Do the same for the second child; the first replacement still leaves
an actual sibling witness, so the lemma remains applicable. The resulting pair
is enumerated at the parent. Conversely every enumerated pair is an actual
partial choice because the leaf sets are disjoint and the region choices are
independent. Thus no parent key disappears or is invented and its minimum score
is exact. With equal scores, replacing a child by its input-order lexicographically
smaller witness also makes the full sorted witness lexicographically no larger,
so the induction preserves the specified tie rule. At the root every net is
closed and the unique key is empty. QED.

Implementation detail: a join unions the actual child boxes, sums *raw* child
closed costs, charges each newly closed net once, then normalizes anew. It does
not add the children's adjusted tau values. The actual witness determines the
raw geometry independently of what endpoints were hidden by the key.

## Theorem 7: full-table certificate soundness and bounded completeness

A certificate lists, in postorder, every retained node row (key, tau, actual
candidate indices), and the root optimum and witness. An independent checker
validates the complete input; builds all leaf candidates from immutable macro
and pin definitions; directly evaluates all combinations of the preceding
verified child witnesses; computes their per-key minima; and requires exact
agreement with the supplied rows, including tie-breaking and node coverage.

If this checker accepts, the reported root placement is legal and achieves the
portfolio optimum. If a well-formed input's full recurrence fits the checker
and producer work limits, the producer's complete certificate is accepted.

Proof. At each node the checker computes exactly the recurrence of Theorem 6
using only independently reconstructed candidate geometry and previously
verified child witness lists. Induction identifies every accepted table with
that recurrence. The root is therefore an attaining legal optimum. Completeness
follows from computing the identical mathematical recurrence and deterministic
tie rule, provided neither bounded execution is interrupted. Nothing about a
rejected, incomplete or resource-capped packet proves geometric infeasibility.
The argument assumes the mathematical checker operations are implemented as
specified; finite tests are evidence for that correspondence, not a mechanized
proof of the Python interpreter or program. QED.

For an integer budget B, an accepted optimum W proves that an allowed portfolio
combination meets HPWL<=B exactly when W<=B. When W>B, the infeasibility statement
is confined to these supplied portfolios. An omitted legal alternative can change
that answer. No certificate seals an externally selected file cryptographically.

## State and bit-complexity bounds

For node v, live net e and axis d, let q^-_(ved) and q^+_(ved) be the counts of
possible clipped lower and upper endpoints across actual partial choices. Then

    S_v <= product_(e,d) q^-_(ved)*q^+_(ved).

For a nonempty pin set, if q is the number of distinct coordinate values over every listed candidate pin
and w the maximum number of live nets, S_v<=q^(4w). A pinless instance has one state at each node. The support bounds and every
clipped endpoint are drawn from that coordinate alphabet. The number of generated
transitions is T=sum_r |C_r| + sum_(internal v) S_left(v)*S_right(v).
With M the total candidate-pin occurrence count, a direct support precomputation
costs O(nM); combining raw boxes and actual witness vectors gives total work
O(nM+T*poly(n,w,L)), for integer bit-length parameter L. In particular this gives
2^O(w log(q))*poly(input length) work, including the squared state bound at joins.
It is an FPT bound for the combined exposure/alphabet parameter, not an FPT
result parameterized only by live-net width. No hardness result ruling out a
better width-only algorithm is asserted.

The certificate stores full selected candidate vectors, costing up to
O(sum_v S_v*(wL+n log(max_r |C_r|+1)+identifier length)) bits. The replay may
perform T direct pin evaluations and is not promised to take time linear in
certificate size. Input legality also includes ordinary pairwise macro/region
checks. The abstract theorem has finite nonempty portfolios of arbitrary size;
source limits of 48 regions, 32 candidates and magnitude <2^60 are documented
resource restrictions, not an unrestricted physical-design claim.

## Counterexamples and separations

1. Canonical boxes are not geometric children. Two fixed points at 0 and 10
   produce canonical endpoints 10 and 0, each with offset 10. Unioning those
   endpoints and adding both offsets gives 30, although actual span is 10.
   Each local response normalization is correct; this invented join is not.

2. Marginal per-net minima need not be compatible. A region has two rigid choices
   whose two net-pin coordinates are (0,2) and (2,0). Both corresponding outside
   points are at 0. Each net individually can have span 0, but every actual choice
   has total span 2. Separate minima erase the shared candidate selection.

3. Two-sided supports can hide all inner choices. For k nets, put q independent
   inside pin positions between fixed outside left and right anchors of the same
   net. Keep macro/anchor regions disjoint using separate rows. At the node
   containing all inside variables, raw and one-envelope keys distinguish q^k
   choices. Both exterior extrema ranges are singleton anchors, so the two-sided
   key is constant and all offsets are zero. Every choice has the same HPWL.

4. Exposed endpoints retain q^k responses. Give each net one inside pin with q
   distinct positions x_i in a row and one outside pin that can lie at L_i or R_i,
   with L_i<x_i<R_i. Put the two macros in disjoint horizontal owner bands so all
   choices are legal and the vertical span is constant. Independent outside
   choices distinguish every inside vector even up to an additive constant: a
   difference Delta in coordinate i contributes Delta for the left choice and
   -Delta for the right choice. Thus any exact explicit response-equivalence
   table at this chosen separator needs at least q^k rows. This is a lower bound
   on that representation at that separator, not computational hardness. Joining
   each inside/outside pair first removes the wide interface.

5. Marginal-range minimality is not actual-context minimality. In one dimension,
   let a=b be either 0 or 2 (one outside pin with two choices). Inside intervals
   [0,2] and [1,1] respond respectively (2,2) and (1,1): they differ by a constant
   on the two actual contexts. Their canonical keys differ. In the relaxed domain
   a=0,b=2 is also allowed; both spans there equal 2, so the constant difference
   disappears. Theorem 3 intentionally distinguishes them. A physical realization
   uses an owner [0,4]x[0,4] containing two unit macros with one lower-left pin
   each. Their lower-left positions are (0,0)/(2,2) in the first candidate and
   (1,0)/(1,2) in the second. They never overlap. A separate owner [0,4]x[5,7]
   has a unit outside macro with lower-left pin at (0,5) or (2,5). All three pins
   share one net of weight one. Both inside candidates have the same vertical
   response 5, so the displayed horizontal argument applies unchanged. This
   preserves macro sizes, pin offsets and net identities in every candidate.

## Constant-net baseline and the significance limitation

Apply Lemma 1 to *all* regions touching a net rather than to an outside subset.
If the two bounds of each minimum range coincide and the two bounds of each
maximum range coincide on both axes, that net's HPWL is a fixed constant across
all portfolio combinations. Remove its pins from the optimization netlist and
add its constant cost to the final answer. Geometry and the set of candidate
choices remain unchanged, so the reduced optimum plus this constant equals the
original optimum. This is a sufficient test for constant HPWL, not a necessary
one: a single moving pin has zero span even when its extremum ranges move.

Every net in the masked family satisfies this sufficient test. Consequently,
constant-net removal followed by the raw DP also has one row at every node.
The q^k-versus-one key separation remains mathematically true for the named
unpreprocessed representations; it does **not** demonstrate a new computational
advantage over this elementary preprocessing baseline. This check was added
as an exploratory adversarial repair after the initial three-method campaign.
An independently computed deletion/offset check precedes replay of the reduced
certificate, and the selected full witness is checked against original pins.
The approach is conventional exact simplification, not a claimed contribution.


## Explicit physical lower-bound construction

For arbitrary k>=1 and q>=2, place an inside unit macro for net i in the owner
[0,q+2] x [4i,4i+1], and an outside unit macro in
[0,q+2] x [4i+2,4i+3]. Both pins are their macro's lower-left corner. The inside
pin's x coordinate is one of 1,...,q; the outside pin chooses 0 or q+1. All owner
interiors are disjoint and every local placement fits. At the node containing
all inside owners, two distinct inside vectors differ at coordinate j. Holding
all other outside choices fixed, the response difference on net j is Delta
when the outside pin is 0 and -Delta when it is q+1. It is not constant. Thus
q^k explicit response-equivalence rows are necessary at that chosen separator,
even before relaxing the exterior contexts.

A different hierarchy pairs the two owners of each net first. It has width one,
q rows at an inside leaf, at most two at an outside leaf, and one after closing
each net. At most k(q+2)+2kq+(k-1)=3kq+3k-1 transitions suffice. Its optimum is
3k (vertical span two, minimum horizontal span one per net). This proves a
representation/hierarchy contrast, not optimization hardness. The executable
exposed family uses wider coordinate bands and has optimum 23k instead; these
constants refer to different geometries.

## Evidence boundary

These are elementary explicit mathematical proofs, not externally peer-reviewed
or machine-checked results. The relationship to terminal propagation, standard
elimination/state minimization and exact floorplanning must still establish a
worthwhile distinct EDA contribution. The public regression experiment supports
format adaptation and exact finite orientation selection only; it does not
establish production-scale benefit or general benchmark coverage.

## Objective ownership and key-count monotonicity

For nonempty net owner set O(e), the first closing node is its least common
ancestor lambda(e). At an internal node v with children s,t, the newly closed
nets are exactly those with O(e) contained in U_v but contained in neither U_s
nor U_t. Accordingly C_v=C_s+C_t+sum(newly closed weighted actual HPWL). The
first-closure sets partition the netlist; a net cannot be wholly inside both
disjoint children. Adjusted child scores contain live-net offsets, which are
not raw closed costs.

For a fixed node let E=[a_-,b_+]. Raw key maps to the one-envelope key by clipping
both endpoints to E. That key maps to the two-sided key by clipping the lower
endpoint to A and upper endpoint to B, since A,B are subsets of E and nested
clipping is idempotent. The two clipped modes have the same offset formula.
Raw equality is sufficient for response equality up to closed cost; the envelope
mode uses the same proof with A=B=E, whose context-closure property follows by
union of an actual sibling and any interval within the parent envelope. Thus
each complete table contains every attainable key of its respective mode.
The functional mappings imply S_two <= S_envelope <= S_raw at each node. The
transition formula implies the same ordering of total generated transitions for
complete computations. This does not order runtime or serialized bytes and does
not compare against preprocessing that changes the netlist.
