## Context

The callability-complete R1 fit trained all dueling-DQN parameters. It improved
validation SMDP TD from `7.601144` to `7.584513` and changed-proposal executed
label agreement from `0%` to `33.33%`, but direct parent disagreement reached
`21.67%`. The failed recipe is closed on that corpus and production r16 remains
authoritative.

Callability provenance is observed only after `CombatRLAgent` receives an RL
proposal and applies its guards. It therefore cannot be used as an inference
input without changing the deployed decision boundary. The new adapter must
learn an abstention function from information available before the proposal.

## Goals / Non-Goals

**Goals:**

- Preserve frozen-r16 behavior exactly at adapter initialization.
- Train a small correction mechanism without changing any parent parameter.
- Make correction eligibility explicit and measurable through an abstention
  gate rather than relying only on a full-network anchor loss.
- Produce a deterministic, restorable, non-production artifact and a cheap
  synthetic training smoke before spending live-game budget.
- Retain the existing fresh-cohort technical gates for any later successor.

**Non-Goals:**

- Refit or tune on the closed R1 corpus.
- Change guards, rewards, state/action spaces, CommunicationMod, r16, or online
  training defaults.
- Add production checkpoint loading, launch gameplay, collect a fresh cohort,
  or claim policy quality in the first implementation boundary.
- Search hidden width, gate threshold, residual scale, losses, or optimizer
  settings after observing a result.

## Decisions

### Compose a frozen parent with one abstaining correction head

The experiment adapter owns a frozen copy of the existing DQN and one MLP. The
MLP reads the continuous state, finite unmasked parent Q values, and the legal
action mask. It emits one gate logit and one residual per action. The parent is
always evaluated with dropout disabled and detached from autograd.

The final correction projection starts at exact zero. The gate opens only when
its sigmoid probability reaches the fixed `0.90` threshold. A closed gate
returns parent Q values exactly; an open gate adds residuals bounded by
`4 * tanh(raw_residual)` before applying the action mask. This is preferred over
a second full network because parent identity becomes a construction invariant
and trainable capacity remains small. It is preferred over using the stored
direct/changed bit at inference because that bit is not available until after
the wrapper has processed a proposal.

The initial hidden width is fixed at `32`. These constants are mechanism
settings, not a search grid.

### Train gate and correction roles separately

Direct rows train the gate to abstain. Changed-proposal rows train the gate to
open and train corrected Q values toward the executed action and SMDP target.
No-proposal rows remain attached only through their SMDP spans. The frozen
parent provides bootstrap actions and target values exactly as in the previous
callability runner.

The mechanism smoke uses deterministic synthetic candidate-decision spans with
separable direct and changed states. It proves gradient flow, exact frozen
parent bytes, restorable adapter state, nonempty gate behavior, and bounded
residuals. It is not policy evidence and does not authorize a live run.

### Keep a separate experiment artifact

The checkpoint stores the parent checkpoint hash and parameter hash, adapter
configuration, correction state, optimizer state, seed, update count, and
mechanism telemetry. It is marked `production_compatible=false`; existing
`RLAgentV2` loaders continue accepting only ordinary DQN state dictionaries.

A later fresh training registration must bind a new callability-complete cohort
and fixed recipe before data access. It must retain at least the existing direct
disagreement, changed-label uplift, validation TD, positive-energy End Turn,
serialization, and integrity gates. The closed R1 corpus may be referenced only
as read-only motivation and input-identity evidence.

## Risks / Trade-offs

- [Risk] The gate overfits changed provenance and opens on direct states. ->
  Keep the parent frozen, report gate confusion and direct action drift, and
  reject any future fit above the existing `10%` direct ceiling.
- [Risk] A hard gate is not differentiable. -> Train its logit with supervised
  binary loss and use the hard threshold only for evaluation and inference.
- [Risk] Bounded residuals cannot overcome a large parent margin. -> Report
  eligible-open rows that remain unchanged; do not increase scale after seeing
  a result.
- [Risk] The synthetic smoke is too easy. -> Treat it only as a mechanism gate
  and require a separately registered fresh real-game development cohort.
- [Risk] A custom artifact reaches production accidentally. -> Mark it
  non-production-compatible and leave production loader code unchanged.

## Migration Plan

1. Add failing focused tests for zero-entry equivalence, frozen parameters,
   abstention, bounded correction, and checkpoint round trip.
2. Implement the experiment-only adapter and deterministic synthetic smoke.
3. Run focused pytest and the smoke; publish only mechanism evidence.
4. If the mechanism passes, commit and separately preregister a fresh cohort
   before any real fitting or gameplay.

Rollback removes the experiment module, tests, and non-production artifacts.
No production state needs restoration because r16 and its loader are unchanged.

## Open Questions

None for the mechanism boundary. Fresh-cohort size and optimizer budget must be
fixed in a later registration before collection.
