## Context

The current reusable card corpus has 46 train/development states from 23 seeds;
the independent audit added only 15 states. The full ranker overfit, a
scorer-only update could not flip actions, and a card-uplift residual failed
audit. All three outcomes are consistent with insufficient state/action
coverage. The native collector already produces canonical feature tensors and
formal branch returns, so corpus expansion can reuse that proven boundary.

## Goals / Non-Goals

**Goals:**

- Materialize roughly an order of magnitude more train/development card states.
- Keep complete legal action sets, features, returns, source identities, and
  censors in reusable canonical artifacts.
- Reserve a clearly separate untouched audit cohort before model development.

**Non-Goals:**

- Select an architecture, train or evaluate a policy, or claim improvement.
- Access reserved audit seeds, start gameplay/CommunicationMod, or modify
  production checkpoints.
- Replace unsupported seeds or loosen limits after execution starts.

## Decisions

### Reserve one new high seed block

The block `80000..80383` is absent from current registered source schedules.
Train uses `80000..80255`, development uses `80256..80319`, and audit reserves
`80320..80383`. The three sets are immutable and disjoint. Merely recording the
audit schedule does not authorize constructing its environments.

### Collect train and development only

Each seed may contribute at most two complete card-reward states, each requiring
four action continuations. Train permits at most 2,048 branches and 16
registered Courier censors; development permits at most 512 branches and four
censors. No censored seed is replaced. Minimum support is 440 train states and
110 development states.

### Publish full datasets plus diagnostics

The runner uses the existing canonical full-partition codec. It also reports
state/action counts, informative-return counts, unique card ids, unseen
development cards relative to train, return-spread summaries, branch counts,
and censors. It does not fit a model.

## Risks / Trade-offs

- [Collection is long] -> Bound total charged time to four hours and publish
  only after both partitions pass support and identity checks.
- [Courier failures reduce coverage] -> Permit bounded registered censors,
  retain exact censor evidence, and require conservative support floors.
- [Some cards remain rare] -> Report train/development card coverage so the
  next architecture can handle unseen identities explicitly.
- [Audit leakage] -> Keep the audit range only in registration metadata; the
  execution path has no audit collection call.

## Migration Plan

No production migration occurs. Failure leaves no model and retains all current
policy behavior. A successful corpus enables a separate source-only training
proposal.

## Open Questions

None.
