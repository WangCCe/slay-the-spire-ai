## Context

The full candidate card policy has 262,402 trainable values across its family
and conditional heads but only 542 merged informative states. Its selected
8-epoch model generalized poorly on rare development and changed many family
choices. The prior 128-value scorer-weight pilot had only 16 train seeds and
zero development action flips; the merged corpus now has 439 informative
take-ranking states, 960 unequal take pairs, and 306 supporting seeds.

The simulator executes greedy card actions in two stages: family argmax, then
conditional argmax within that family. The new runner must use that same rule
for action regret instead of global joint-probability argmax.

## Goals / Non-Goals

**Goals:**

- Test whether the frozen conditional hidden representation supports useful
  take-card ordering with only a 64-value linear scorer update.
- Preserve every entry family choice exactly by freezing the complete family
  head and excluding cross-family pairs from the loss.
- Select duration on train-only seed folds and evaluate development once using
  actual two-stage choices.

**Non-Goals:**

- Learning when to take versus skip, changing hidden features, or adding model
  architecture.
- Retrying the full-head model, tuning after development, or using reserved
  audit, native, simulator, CommunicationMod, gameplay, or production state.

## Decisions

### Optimize one conditional scorer tensor

The optimizer owns only
`candidate.card_policy.conditional_ranker.scorer.weight`, exactly 64 float32
values. The scorer bias is excluded because a shared scalar bias cancels in
within-family comparisons. Every other tensor, generator, optimizer input, and
family output remains byte-identical. This is the smallest state-conditioned
capacity above a per-card global residual and avoids another 131k/262k fit.

### Use take-only pairwise loss

Each optimization batch includes rows with at least one unequal return among
the three take candidates. The margin-weighted softplus loss compares only
take indices `0..2`; skip and all take-vs-skip pairs contribute no gradient.
Rows are ordered by `(seed, decision_index, source_sha256)` in deterministic
64-row mini-batches.

### Select fixed epochs with seed-level crossfit

Five seed-disjoint folds start from identical r7 entry bytes. Fixed checkpoints
are `{1, 2, 4, 8, 16, 32}` epochs. Selection uses only held-out train rows and
chooses the lowest-regret passing checkpoint, with earlier epoch as the final
tie breaker. No passing checkpoint stops before final fitting or development.

### Evaluate the real two-stage policy

Metrics choose the greedy family from family logits and the greedy action from
conditional logits inside that family, matching the runtime. Weighted pairwise
accuracy compares family logits across families and conditional logits within
a family. Reports separately expose take-only pairwise accuracy and require
zero family-choice flips from entry.

### Persist before one-shot development

After train-only selection, one final scorer is fit on all informative train
rows, encoded with the complete bootstrap, restored byte-exactly, and only then
used to load development. Overall and rare-only gates are evaluated once. A
pass authorizes only a separate untouched-audit proposal.

## Risks / Trade-offs

- [Frozen hidden features remain too weak] -> Train-only crossfit stops the
  experiment without development access when the 64-value scorer cannot move
  held-out actions safely.
- [Take-only learning cannot fix skip errors] -> This experiment deliberately
  tests conditional choice independently; acceptance needs separate evidence.
- [Development informed architecture choice] -> Development cannot select
  epochs or parameters; `92320..92383` remains the independent future gate.
- [Historical joint-argmax reports differ] -> Preserve them as historical
  evidence and clearly label this runner's policy-aligned metric schema.
