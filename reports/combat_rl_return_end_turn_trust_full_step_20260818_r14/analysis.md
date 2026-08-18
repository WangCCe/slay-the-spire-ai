# Full-step End Turn trust candidate r14

## Decision

Do not freeze a candidate. Interpolation `alpha=1.0` improved both registered
losses on all four consumed replay cohorts, but no trust weight passed every
action guard. No checkpoint was written.

## Result

Weight zero retained the original r12 failure mode: off-target disagreement
exceeded `1%` on every replay and positive-energy End Turn increased on r8,
r9, and r10. Positive trust weights removed the End Turn increase, but the
full step changed too many other greedy decisions. At weight `0.25`, parent
agreement fell to `98.9708%` on r6 and `98.8312%` on r9; r6, r9, and r10 also
slightly exceeded the off-target ceiling.

The failure is therefore overall step size, not insufficient End Turn
protection. Do not increase the trust weight further or relax agreement and
off-target thresholds to admit this candidate.

## Next step

Keep the optimizer, return target, trust objective, and thresholds fixed. Test
one intermediate interpolation, `alpha=0.75`, on r6/r8/r9/r10 before deciding
whether another fresh replay is justified.
