## Why

The first real-context-balanced corpus run improved fresh-evaluation support but
correctly closed without fitting: overall real context coverage was 80.79%, and
55% of the remaining missing mass was concentrated at floors 11..17. The
independent 1,024-seed training partition reached 93.83% coverage and passed all
registered support gates, so the smallest evidence-backed next step is an
early/mid fresh-evaluation supplement rather than a new weighting method,
threshold change, or state-import bridge.

## What Changes

- Collect one immutable fresh-evaluation-only supplement from new seeds
  `271000..272023`, battle indices `0,3,6,9`, and the unchanged paired-return
  recipe.
- Retain supplement rows at floors 0..22 and append them to the failed gate's
  exact combined evaluation corpus; preserve its combined training partition
  byte-for-byte.
- Recompute the same exact-cell context weights and apply the unchanged support
  gates from the archived balanced-corpus change.
- Publish source-bound corpus, weight, missing-cell, support, and artifact
  evidence; permit a separate weighted-fit proposal only if every existing gate
  passes.
- Close without retry, fitting, tuning, gameplay, or threshold changes if the
  fresh evaluation support remains insufficient.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-real-context-balanced-corpus`: Add a separately bound
  fresh-evaluation support supplement and immutable re-evaluation path after a
  late-floor supplement passes training support but fresh evaluation remains
  context-incomplete.

## Impact

The change adds a thin offline/native runner, focused tests, one immutable
registration, and report artifacts. It reuses the registered native module,
production-r16 simulator shadow, r14/r15 replay target, the archived balanced
train/evaluation corpora, exact context-cell definition, and all existing gate
thresholds.

Success means the augmented fresh evaluation partition passes every unchanged
context-mass, floor, ESS, maximum-weight, weighted-SMD, legality, provenance,
and seed-isolation gate. Non-goals are training, model or threshold selection,
gameplay, CommunicationMod, production checkpoint access, policy evaluation,
qualification, promotion, exact simulator equivalence, and arbitrary state
import.

The rollback boundary is the immutable
`combat_rl_real_context_balanced_corpus_20260829_r1` output. A failed or
interrupted supplement does not modify it and grants no downstream authority.
