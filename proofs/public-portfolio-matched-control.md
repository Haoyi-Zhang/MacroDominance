# Corrective square-geometry R0/R180 matched control

This control was requested before its execution in the repair round, after the
frozen four-way outcomes were already known. It is a corrective matched comparison,
not an independent preregistration, and it does not replace or rewrite the
original 32 four-way records.

For each of `hp`, `n10`, `apte`, and `xerox`, under balanced and net-aware trees,
regenerate the frozen square-owner four-way input. Construct a second input with
identical owner boxes, macro definitions, point-pin offsets, weights, and tree, but
retain only candidate indices 0 and 2 (R0 and R180) from each four-way owner.
Before running any policy, assert exact equality of those structural fields and
exact list containment of every retained candidate.

Use the original extension limits: 50,000 generated transitions, 10,000 temporary
states, 500,000 dominance comparisons, 15 seconds for production, and 30 seconds
for replay. Run Leaf-only and All-level Response on the matched subset and replay
every success. Independently solve both the subset and full four-way case with the
MILP wrapper, exactly re-evaluate each selected witness, and require
`W*_four <= W*_R0/R180`; this inequality follows from candidate inclusion but is
also checked on all eight pairs. Preserve the original 26 successes and six caps
unchanged.

The actual run produced sixteen successful subset certificates, no subset cap or
failure, eight verified structural matches, eight verified optimum inequalities,
and 876 replayed dominance obligations. These are finite results for the named
constructed portfolios, not native benchmark placement evidence.
