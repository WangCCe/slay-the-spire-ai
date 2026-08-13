## Context

The frozen event ranker improved one-step counterfactual regret twice, but its
raw full-trajectory overlay failed: 74 of 331 overrides occurred on event
identities absent from the training dataset. The next policy configuration must
make the training support boundary part of the executable artifact identity,
not infer it from model confidence.

## Goals / Non-Goals

**Goals:**

- Bind and restore the exact training dataset alongside the frozen model.
- Allow model selection only for event candidate semantics observed in training.
- Measure supported exposure, Current fallbacks, overrides, and paired terminal
  value on a fresh fixed simulator cohort.
- Produce one terminal go/no-go result without changing the configuration after
  outcome access.

**Non-Goals:**

- New fitting, threshold calibration, seed replacement, or model selection.
- Causal attribution to individual events from full-trajectory associations.
- Gameplay, CommunicationMod, production checkpoint access, qualification, or
  promotion.

## Decisions

### Manifest-bound semantic support signatures

Verify `train_dataset.json` against the same training artifact manifest used to
load the model, restore it through the canonical event-partition codec, and
require an exact byte round trip. Build support from each row's legal candidate
set. A candidate semantic identity consists of `action_id`, `kind`, and the full
`raw` action mapping; candidate identities are sorted by `action_id` before the
set is hashed with an explicit signature schema. This is stricter than event ID
alone and prevents an observed event name from authorizing an unseen follow-up
phase or action set. The full normalized candidate mapping is bound; state
feature tensors are excluded because exact fresh states would never match.

Alternatives considered: event-ID support is broader but leaks across unseen
event phases; state-feature hashes are too narrow and would make nearly every
fresh state unsupported.

### Current fallback is an observed policy action

At every decision, evaluate persistent Current first. For a multi-option event,
compute its semantic support signature. A supported signature may invoke the
same frozen model and stored 0.50 threshold. An unsupported signature executes
Current unchanged and records the signature, event identity, and fallback
reason. Route, shop, card reward, and single-option events remain Current.

### Disjoint single-use paired cohort

Use seeds `94800..94927`, disjoint from all prior event cohorts. Run separate
pure-Current and supported-overlay environments for each seed. Require at least
112 complete pairs, 96 event-exposed pairs, 64 support-exposed pairs, and 64
actual override pairs, with at most 16 registered censors. No replacement seeds
or rerun follow terminal outcome access.

### Fixed terminal and support gates

Retain strict return `2*victory + floor/57` and the raw experiment's victory,
mean floor, mean return, paired victory-loss, and improved-versus-worsened gates.
Add support-exposure and fallback-accounting completeness gates. A pass permits
only a separate simulator policy-bundle proposal; a failure ends this frozen
event-ranker integration path.

## Risks / Trade-offs

- [Exact signatures reject benign variants] -> Report per-signature fallback
  counts and fail on insufficient supported exposure rather than broadening the
  gate after results.
- [Aliases could split one event] -> Use canonical executable `action_id` plus
  raw action semantics, not display labels.
- [Removing early extrapolation changes later state visitation] -> Run a fresh
  paired cohort; do not filter or reinterpret the prior trajectories.
- [Small terminal deltas remain noisy] -> Preserve paired seeds and all fixed
  noninferiority/regression gates.

## Migration Plan

Add a separate offline runner and focused tests, execute the fixed cohort once,
then archive the terminal evidence. No production migration occurs. Rollback
removes the new runner and artifacts; the raw-overlay no-go remains immutable.

## Open Questions

If this configuration passes, a later proposal must define a simulator policy
bundle and live shadow-only boundary before any gameplay effect is considered.
