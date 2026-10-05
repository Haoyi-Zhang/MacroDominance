# Self-context dominance and transition-coverage certificates

This argument extends the finite portfolio model and normalization in `core.md`.
It is a mathematical proof, not a mechanized proof of this text or the software.
All ownership, independence, positive-weight and relaxed-context assumptions are
unchanged. The original equality-key dynamic program and its results remain valid.

## 1. A maximal-difference context

For one axis let A=[a-,a+] and B=[b-,b+] be the exact exterior minimum and maximum
ranges, with a- <= b- and a+ <= b+. The relaxed exterior domain is
D={(a,b): a in A, b in B, a<=b}. Normalize inside intervals to (l_p,u_p) and
(l_q,u_q), so both canonical intervals belong to D. Include their normalization
corrections in their scalar scores tau_p and tau_q.

**Self-context lemma.** For canonical intervals,

    max_(a,b in D) [h(l_p,u_p;a,b)-h(l_q,u_q;a,b)]
       = (l_q-l_p)_+ + (u_p-u_q)_+.

The maximum is attained at (a,b)=(l_q,u_q), the canonical interval of the target q.

Proof. Split the difference as

    [min(l_q,a)-min(l_p,a)] + [max(u_p,b)-max(u_q,b)].

For every real a the first bracket is at most (l_q-l_p)_+: if l_q>=l_p this follows
from monotonicity and the unit Lipschitz bound of min in its first argument; if
l_q<l_p the bracket is nonpositive. At a=l_q equality holds in either case.
The second bracket is similarly at most (u_p-u_q)_+ and attains it at b=u_q.
The two maximizing endpoints are simultaneously feasible: normalization gives
l_q in A, u_q in B and l_q<=u_q. Thus their sum is both a universal upper bound
and an attained value on D. This proves the maximum, including degenerate
ranges. QED.

For the product domain of all live nets and axes, define

    E_v(p,q) = tau_p-tau_q
               + sum_(live e,axis d) w_e [ (l_q,e,d-l_p,e,d)_+
                                          +(u_p,e,d-u_q,e,d)_+ ].

**Theorem (exact relaxed-context dominance).** E_v(p,q) is the maximum of
R_v(p;c)-R_v(q;c) over all relaxed contexts c. Therefore p can replace q without
increasing any relaxed-context response if and only if E_v(p,q)<=0.
If E_v(p,q)>0, the product of q's canonical intervals is a separating relaxed
context. Testing dominance and constructing this witness require O(|L_v|)
exact arithmetic operations (two axes per net); no exterior-portfolio product
is enumerated.

Proof. The domain is a product. The self-context lemma bounds each summand, and
the product of its individual maximizers belongs to that product. All weights
are positive, so summing yields the stated attained maximum. QED.

This is not a necessity theorem for dominance under actual joint exterior
placements. The product self-context may be unrealizable because extrema of
one macro, several nets or the two axes can be correlated. E<=0 remains safe
for actual contexts; E>0 alone does not establish an actual counterexample.

The relation is transitive because it is pointwise comparison of response
functions. Mutual dominance implies equality of responses and hence equality
of canonical key and adjusted score by the canonical-characterization theorem.
Within a key, retaining the least score is the original equality pruning.
Componentwise canonical-box inclusion plus a no-larger scalar score is sufficient
but not necessary: the scalar saving can pay for a bounded expansion of a box.

## 2. Lower-envelope-preserving substitution

A retained table T_v covers every actual partial portfolio p if, for every
relaxed context c at v,

    min_(t in T_v) R_v(t;c) <= R_v(p;c).

The construction establishes the single-cover property that for every p there is
one t in T_v dominating p throughout the domain. Section 5 proves that, for this
function class, it is equivalent to the displayed lower-envelope property. It does not preserve the
minimum row of every equality key, and it need not preserve the globally
lexicographically smallest optimum. It preserves the minimum objective and
returns a deterministic actual attaining witness.

At leaves, enumerate all alternatives. At an internal node enumerate every pair
of retained child witnesses and join their actual geometry, never their
canonical endpoints. Discard an enumerated row only when another actual row
dominates it under the node's declared relation. Equality-only, box-inclusion,
leaf-only response dominance and all-level response dominance are supported.
All four relations imply pointwise domination. For deterministic results the
producer resolves equal-key/equal-score cases by witness order; cross-key weak
dominance is not a lexicographic-optimality rule.

**Theorem (exact root optimum).** A nonempty covering table at every node gives
an optimal root placement in the supplied finite portfolios.

Proof. Induct on nodes. The leaf case follows from exhaustive enumeration and
coverage. Given any actual parent placement, replace its left restriction by
its covering retained child witness. For every relaxed parent context, union
with the actual sibling pins produces a relaxed child context by the closure
lemma in `core.md`. The replacement cannot increase the parent response.
Repeat for the right restriction, using the now-actual replacement on the left.
The resulting retained-child pair is enumerated. A retained parent row covers
that generated pair, so by transitivity it covers the original parent placement.
Every retained row is itself an actual parent placement because owner choices
are independent. At the root no net is live: responses are constant costs and
one least-cost actual row covers all complete placements. QED.

Unlike equality-key substitution, the parent key may change. Reusing the original
per-key induction after cross-key pruning would be incorrect; the stronger
pointwise covering relation is the invariant used here.

## 3. Coverage certificate and separate replay

Each node supplies a nonempty list of actual retained rows. A row includes its
canonical key, scalar score and choices. A `source` integer identifies a leaf
alternative or an ordered retained-child pair from which that row was obtained.
A `cover` array contains one retained-row index for every generated transition,
in the completely specified enumeration order. The root includes the optimum
and the attaining placement. The certificate contains no learned score or
uncertified inferred geometry.

The replay validates the input geometry and recomputes all ranges. It reconstructs
each retained row from its cited transition and compares the whole row. It then
enumerates every leaf/child-pair transition, reconstructs its actual response and
checks the indicated coverage edge. For full response coverage it evaluates the
response difference at the target's self-context via max/min span arithmetic,
not by importing the producer's positive-part formula. These are separately implemented, replay checks, not machine verification.

**Theorem (coverage-replay soundness).** Acceptance establishes both attainability
and exact objective optimality in the finite input model.

Proof. Source reconstruction establishes that all retained rows are actual
alternatives or joins of already validated child rows. The complete cover array
and the exact dominance theorem establish coverage of every enumerated candidate.
The preceding induction then establishes coverage of all partial and complete
choices. Recomputed closed-root cost and witness attain the optimum. QED.

The checker need not verify that no retained row dominates another; that property
only affects size, not soundness. Nor must its accepted packet equal the
producer's particular pruning order. Soundness is a property of the supplied
covering packet, not of trusting the search implementation.

For each node v, let S_v be its **final** retained-row count. Let M_v be the
number of generated candidates: the local portfolio size at a leaf, or
S_left*S_right at an internal node. Let P_v be the largest size reached by the
online ``kept`` dictionary while node v is processed, and let w_v be the live-net
count. These quantities are different: a row that arrives late can remove many
currently kept rows, so P_v need not be bounded by final S_v or by
S_max=max_v S_v.

For one candidate, the producer scans at most P_v current rows. It evaluates at
most two dominance directions per scanned row, and each direction takes
O(w_v+1) exact arithmetic operations. Therefore

    dominance-scan arithmetic = O(sum_v M_v P_v (w_v+1))
                  <= O((w+1) sum_v M_v P_v),

where w=max_v w_v. For nontrivial w>=1 this is conventionally written
O(w sum_v M_v P_v). This is a direct summation proof, not a claim that every scan
reaches the bound. This counts scan arithmetic after candidate construction,
not total production work. Equal-key dictionary handling uses O(sum_v M_v)
expected lookups; variable-length key hashing/comparison costs extra. Model and
original-portfolio support preparation, raw joins, actual witness copying and
sorting, final table ordering, and certificate construction are separate costs.
During node production the implementation stores up to P_v actual rows
and M_v redirection entries, besides completed child/final tables.

The distinction is witnessed by the executable legal two-owner family in
``tests/test_online_frontier_peak.py``. The inside owner is
[0,3k+5] x [0,3] and contains unit squares A and B. Its first k candidates put
A=(i,0), B=(i+k,1) for i=1,...,k, followed by A=(0,0), B=(0,1). A unit local net
joins the lower-left pins of A and B. A unit live net joins A to unit square C in
the disjoint owner [0,3k+5] x [10,12], where C has candidates (0,10) and
(k+1,10). The first k inside rows are pairwise incomparable, while the last row
dominates all of them. Thus forward order has total M=k+5, final S_max=2,
inside P=k, and k(k+1)+3 producer comparisons. Reversing the inside candidate
list presents the dominator first, giving inside P=1, global P=2, and k+3
comparisons. Exact Cartesian, producer, and replay executions for k=3,7,15,31
match these formulas. Those eight runs are finite checks; the general work bound
comes from the scan argument above.

Let M=sum_v M_v and S=sum_v S_v. Coverage uses M integer indices plus S source
indices, excluding row/witness representations. After geometric reconstruction,
replay has exactly M dominance obligations and O(M(w+1)) arithmetic for those
obligations, including scalar comparison at w=0. This is not a bound on the entire checker: direct witness
reconstruction additionally reads the relevant pins. The producer has explicit
comparison, transition, temporary-state, time and memory caps. Exhausting a cap
proves neither portfolio nor unrestricted infeasibility.

## 4. Nonconstant separation from equality and box inclusion

For k independent owner regions, give each variable pin q positions x=4+c,
c=0,...,q-1. Its live net goes to an exterior pin with choices on both sides of
all q positions, so every position has a distinct canonical point interval.
Inside its owner, connect the variable macro to a fixed macro to its left by a
closed net of weight 2; let the live net have weight 1. Use separate horizontal
strips for different owners and a disjoint exterior strip, so all macros and
all alternatives are legal. Constant vertical offsets do not affect the argument.

Moving a variable pin right by c increases the closed-net contribution by 2c,
while its worst live-net improvement is at most c. Thus the leftmost choice
dominates every other choice with margin at least c. Every net is nonconstant
on the full portfolio product; removing globally constant nets does not change
this example. Point intervals at distinct x do not contain each other, so the
box-inclusion baseline cannot perform this pruning.

Under a hierarchy collecting the k variable owners before the exterior owners,
equality keys have q^k combinations at that cut, whereas response pruning keeps
one. Leaf-only response pruning already obtains this saving. Therefore the
construction separates response comparison from equality and inclusion, not
multilevel response pruning from the stronger leaf-only baseline. The latter
comparison requires and is reported on separate coupled/generated cases.

## 5. Collective coverage, irredundancy, and the minimal frontier

The self-context is common to **all** competitors of one target Q. This yields
an additional exact result, not just a sufficient one-row pruning test. Let T be
any finite nonempty set of actual rows at a fixed node, and let c_Q be Q's
canonical context. Then

    max_c min_(P in T) [R(P;c)-R(Q;c)] = min_(P in T) E(P,Q).

Proof. Every individual difference is bounded above by E(P,Q), so the left side
is at most the right side. At c_Q all individual upper bounds are attained
simultaneously, so their minimum attains that upper bound as well. QED.

Consequently T covers Q's response at every relaxed context if and only if one
member P of T individually dominates Q. In this canonical HPWL model the
context-dependent lower-envelope definition and the single-cover definition in
Section 2 are therefore equivalent, although they differ for general function
classes. This result does not apply after replacing the relaxed domain by the
actual exterior choice set.

Define functions equal when they agree everywhere on the relaxed domain. A
function in the finite actual partial-placement family is undominated if there
is no unequal function pointwise no larger. Take one representative of each
undominated function. Finiteness and transitivity show that every function is
dominated by one of these representatives. Conversely, if a covering subset
omits an undominated function Q, the collective-coverage result demands some
retained P dominating Q. Undominatedness then makes P equal to Q, contradicting
the omission of the function class. Thus this frontier is the unique minimal
set of actual response functions preserving the relaxed lower envelope.

Each member is exposed by its self-context: all other frontier functions have
strictly larger value there. Otherwise one of them would dominate it. The
minimum number of actual rows needed equals the number of undominated functions.
This is a cardinality lower bound for **actual-row subsets over the specified
relaxed domain**, not for arbitrary symbolic representations or actual-context
optimization.

The all-level producer maintains a pairwise antichain, with one representative
per equal function, and Section 2 proves coverage of all actual partial choices.
Therefore its table is this minimal frontier at every node. To see that no
retained P is globally dominated by a missing Q, coverage would supply a retained
T dominating Q; hence T dominates P, contradicting antichainness unless all
three responses are equal. The same argument makes every undominated function
represented. Equality of functions is equivalently equality of canonical key
and adjusted score, as proved in core.md; choice vectors can differ.

Every complete equality, inclusion, or leaf-only table is a covering actual-row
subset. Therefore the complete all-level response table has no more rows at
any node than these alternatives. Summing child-table products proves that it
also generates no more transitions. This monotonicity does not bound producer
comparisons, transient active states, wall time, or completion under fixed caps.
Different retained actual witnesses can remain possible within a function class.

## 6. An unavoidable frontier with exposed pins

For k variable owners in disjoint horizontal strips, supply q>=2 positions of
one unit-square macro's lower-left point at x=1,...,q. Its sole unit-weight net
connects to a dedicated exterior owner, in another disjoint strip, whose unit
macro has pin-position alternatives x=0 and x=q+4. All y coordinates are fixed
within each owner. Use owner width q+5 so every alternative is legal.

At the hierarchy cut collecting the k variable owners but none of their k
exterior owners, A=B=[0,q+4] for the x coordinates, all vertical response terms
are constant, and no horizontal normalization correction occurs. Every vector
p in {1,...,q}^k gives a different canonical point key. For any two such vectors,
E(p,q)=sum_i |p_i-q_i|, strictly positive unless they coincide. All q^k responses
are undominated and are exposed at their own relaxed singleton contexts.
Therefore any subset of actual rows preserving the relaxed lower envelope needs
q^k rows; response pruning cannot eliminate this exponential interface frontier.
A hierarchy pairing each variable with its own exterior owner first closes each
net locally and has live-net width one instead of k.

The self-contexts at intermediate integer x positions need not be actual
exterior choices, since the latter offer only the two endpoints. For q=2 the
actual extreme completions already expose all 2^k choices; for q>2 actual-context
coverage can omit intermediate positions that the relaxed frontier retains.
This is another concrete cost of forgetting correlations/domain sparsity, not
a lower bound on every algorithm for the original portfolio problem.
