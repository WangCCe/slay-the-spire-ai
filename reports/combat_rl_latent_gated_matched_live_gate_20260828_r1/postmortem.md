# Latent-Gated Candidate Postmortem

## Conclusion

Do not tune or retrain this latent-gated candidate recipe. The candidate was a
technically valid but lossy approximation of the deployed energy-guard policy,
then it was inserted before that policy. Its legal card proposals frequently
prevented the stronger deterministic guard takeover from running.

This is a high-confidence interaction mechanism, not a complete causal estimate
of the 16-floor matched outcome gap. The gate contained only ten seed pairs.

## Evidence

The candidate lost the preregistered gate with zero paired floor wins against
two parent wins, 168 total floors against 184, and one Act 2 boss reach against
two. Runtime health was not the issue: all 601 takeovers were legal and the
adapter stayed within its latency limit.

Of the 601 takeovers, 570 (94.84%) replaced a raw parent `EndTurn` proposal.
Only 35 takeover proposals were subsequently changed by an outer guard. The
candidate therefore bypassed the production `ENERGY_GUARD` on most states where
that guard would otherwise have selected and continued a card sequence.

The offline qualification thresholds admitted weak correction accuracy:

| Replay | Correction agreement on changed states | Final candidate agreement on changed states |
|---|---:|---:|
| Independent replay | 40.13% | 30.94% |
| Fresh confirmation | 39.89% | 30.51% |

The registered floors were 35% and 25%, respectively. Positive-energy
`EndTurn` reduction was treated as favorable, but the evaluation did not test
whether the replacement beat or even preserved the deployed guard action.

## Losing-Seed Attribution

Exact-state matching joins the candidate live trace to both arms' decision
traces using act, floor, turn, player resources, hand identity and costs, and
monster state. It exposes two material early divergences:

- Pair 3, seed `EAE490C1DD9B1`, floor 1 turn 1: the raw parent proposed
  `EndTurn` with three energy against Jaw Worm. The candidate played `Strike`.
  On the same state the parent arm's `ENERGY_GUARD` selected a sequence starting
  with `Corruption`, followed by three `Defend` cards. The branches diverged on
  the first combat decision; the candidate reached floor 22 and the parent
  reached floor 33.
- Pair 9, seed `EC0E64A30F720`, floor 2 turn 1: the raw parent proposed
  `EndTurn` with two energy against a buffing Cultist. The candidate played
  `Strike`; on the same state the parent arm's `ENERGY_GUARD` selected
  `Clothesline`. The candidate reached floor 11 and the parent reached floor 16.

An earlier pair-9 difference selected two behavior-equivalent copies of
`Strike`, so it is not treated as explanatory evidence.

## Design Correction

The development action head was behavior-cloned from executed guarded actions.
That can learn to imitate the guard, but it does not provide evidence that a
different action improves on the guard. Deploying an imperfect imitation before
the original guard is therefore structurally unfavorable.

The next candidate must use the deployed guarded action as its baseline. A
correction should be eligible only when fresh offline or simulator evidence
estimates positive advantage over that baseline. Exact imitation of the guard
is not a policy improvement and should remain with the existing deterministic
implementation.

## Next Experiment

Run a bounded, offline guard-aware counterfactual audit before another training
or live gate:

1. Reconstruct raw-parent `EndTurn` states and their actual guarded final action
   from the existing development and fresh replay corpora.
2. Evaluate the current candidate relative to that guarded baseline, with exact
   and behavior-equivalent action agreement reported separately.
3. Use LightSTS only on states with supported mechanics to estimate paired
   downstream return for candidate action versus guarded baseline action.
4. Start a new training recipe only if a repeatable positive-advantage stratum
   exists. Train a residual over the guarded baseline, then require substantially
   higher changed-state precision before any fresh live gate.

No same-cohort threshold adjustment, retry, or promotion is justified.
