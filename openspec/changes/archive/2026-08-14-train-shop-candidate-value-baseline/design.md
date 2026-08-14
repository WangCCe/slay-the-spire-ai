## Context

The committed shop corpus has complete legal candidate sets, Current actions,
and branch returns for 43 sources. It intentionally omitted projected game-state
features, so this experiment must measure only candidate-level value signal and
must not claim state-conditioned policy quality.

## Goals / Non-Goals

**Goals:**
- Fit a deterministic CPU ranker from the existing corpus.
- Prevent source leakage across fit, tune, and holdout partitions.
- Compare one frozen selection with Current and deterministic initialization.
- Publish enough identity and per-source evidence to reproduce the result.

**Non-Goals:**
- Recollect native outcomes or inspect protected seed inventories.
- Claim formal RL, causal value, state-conditioned behavior, or live readiness.
- Load production checkpoints or alter gameplay policy.

## Decisions

1. Use a deterministic hash ordering to allocate 32 sources to training and 11
   to one-shot holdout, then split training into 24 fit and 8 tune sources. This
   gives exact, source-isolated sizes without depending on seed arithmetic.
2. Encode only candidate-observable fields: five action-kind indicators,
   normalized price and slot, upgrade fields, and 128 stable SHA-256 identity
   buckets. A zero state vector makes the candidate-only limitation explicit
   while reusing the versioned ranker and pairwise loss.
3. Select from fixed epochs `1, 2, 4, 8, 16, 32` on tune mean regret, then
   weighted pairwise accuracy, then the smaller epoch. Refit once on all 32
   training sources before accessing holdout metrics.
4. Pass only when holdout mean regret strictly improves Current, maximum regret
   is non-inferior, pairwise accuracy improves deterministic initialization,
   and corrected Current decisions are nonzero and not outnumbered by worsened
   decisions. A pass authorizes only a fresh shadow-evaluation proposal.

## Risks / Trade-offs

- [Candidate-only features cannot adapt to deck, gold, relic, or potion state]
  -> Name and report the limitation explicitly and retain state-conditioned
  collection as the next capability if the baseline is promising.
- [Small holdout has high variance] -> Use it once, publish every prediction,
  and forbid same-cohort tuning or reruns.
- [Hash collisions merge identities] -> Bind the bucket count and encoder in
  source identity; collisions are deterministic and do not cross partitions.
