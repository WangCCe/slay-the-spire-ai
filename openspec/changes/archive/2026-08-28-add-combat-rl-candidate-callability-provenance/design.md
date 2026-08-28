## Context

The production combat wrapper may replace an RL proposal and then keep control
for the rest of that turn. While takeover is active, it emits legal actions
before the RL call site. `RLAgentV2.commit_executed_action()` still records those
actions, but replay schema v2 stores only the merged
`anchor_to_executed_action` boolean.

The R2 corpus contains 391 direct proposals, 537 changed proposals, and 1,163
no-proposal takeover rows. No-proposal rows are 55.6% of the corpus and 68.4%
of the override stratum. The completed balanced-objective ablation reduced
direct drift but could not pass the 10% ceiling. A residual architecture on the
same merged labels would retain the larger callability confound.

## Goals / Non-Goals

**Goals:**

- Persist exact proposal identity without changing emitted actions.
- Separate direct proposals, changed proposals, no-proposal takeover, and
  legacy-unknown rows deterministically.
- Convert fresh sequential replay into candidate-decision SMDP spans without
  dropping takeover rewards or bootstrapping through candidate-unreachable
  states.
- Execute one preregistered 64-update candidate-callable development fit and
  make a holdout go/no-go decision.

**Non-Goals:**

- Change combat guards, fallback takeover, rewards, r16, network architecture,
  production inference, or online training defaults.
- Reconstruct per-row callability for the consumed schema-v2 R2 checkpoint.
- Add a residual/head, sweep recipes, or reuse the fresh development corpus
  after a failed fit.
- Authorize gameplay, qualification, promotion, policy quality, or production
  checkpoint replacement.

## Decisions

### Persist the proposed action index with explicit sentinels

Replay schema v3 adds an `int64 proposed_action_indices` tensor. Values in
`[0, action_dim)` are exact RL proposals, `-1` means no proposal existed, and
`-2` means legacy or caller-unknown provenance. A pending RL transition starts
with its proposed action index and never overwrites that field when an outer
guard changes the executed action. A legal emitted action with no pending
transition records `-1`.

For known rows, proposal identity and the existing override flag must agree:

- proposal equals executed action: direct unchanged, override false;
- proposal differs from executed action: changed proposal, override true;
- no proposal: takeover, override true.

Every nonnegative proposal must be legal under the stored action mask. Existing
callers that omit proposal identity store `-2`; this avoids falsely treating
legacy override rows as no-proposal or changed-proposal evidence.

This is preferred over another boolean because the exact proposal enables
action-family audit, legal validation, and future parent-versus-proposal
analysis. It is preferred over guard-name strings because tensor checkpoints
remain weights-only loadable and the first required boundary is callability,
not intervention taxonomy.

### Preserve replay compatibility without changing default sampling

Schema-v1 and schema-v2 states remain loadable. Their restored proposal indices
are all `-2`, while their existing executed-action override semantics remain
unchanged. Schema-v3 round trips both fields and rejects inconsistent known
rows. `ReplayBufferV2.sample()` keeps its existing return shape by default; an
explicit opt-in exposes proposal identity to new tooling.

This keeps current online trainer callers and historical checkpoints compatible
while making legacy uncertainty explicit. Any callability-filtered runner must
reject unknown rows rather than infer them from the merged boolean.

### Build candidate-decision SMDP spans

Filtering no-proposal rows as independent samples is insufficient because a
proposal-bearing action may enter wrapper takeover. The next candidate decision
then occurs several source transitions later. The offline builder therefore:

1. splits source replay into terminal-delimited combat groups;
2. starts one span at each row with a nonnegative proposal index;
3. accumulates discounted rewards through following `-1` rows;
4. bootstraps from the next proposal-bearing state, or terminalizes when the
   source combat ends;
5. records source-span length and a per-row bootstrap multiplier
   `gamma ** span_length`.

The next proposal-bearing row's current state and action mask are the
nonterminal bootstrap tensors. CommunicationMod may persist an immediate
post-action `next_*` snapshot before card effects, enemy turns, or draws
settle; that snapshot can legitimately differ from the next candidate-decision
state. The builder reports such settled boundaries but does not bootstrap from
the pre-settlement snapshot.

No-proposal prefixes before the first candidate decision remain diagnostic and
are not attached to a later action. Unknown rows fail construction. The builder
must reconcile every source row as proposal-bearing, attached takeover,
uncontrolled prefix, or terminal boundary and report all counts.

This is preferred over treating takeover entry as terminal because terminalizing
would discard the eventual consequences and bias actions that hand control to
the wrapper. It is preferred over one-step filtering because fixed-gamma
bootstrapping into a candidate-unreachable state is deployment-inconsistent.

### Freeze one callability-filtered development recipe before collection

The implementation commit will be followed by an immutable registration that
binds production r16, source hashes, ten unused game seeds, zero optimizer
updates, epsilon zero, exact trace/provenance checks, and the following CPU fit:

- terminal-combat validation fraction `0.2`;
- split seed `2026082807`, training seed `2026082808`;
- learning rate `1e-4`, batch size `128`, gamma `0.99`;
- exactly `64` optimizer updates;
- each optimizer batch contains exactly `64` direct and `64` changed-proposal
  spans, sampled without replacement within each stratum;
- parent anchor weight `1.0` with equal direct/changed aggregate anchor loss;
- direct-only top-action margin guard weight `1.0`, cap `0.1`;
- frozen production-r16 target and parent networks.

Only candidate-decision spans enter optimizer batches or development policy
metrics. Every batch must contain direct and changed-proposal rows. The runner
reports span-length and bootstrap-discount telemetry in addition to existing
TD, action, anchor, End Turn, parameter, integrity, and serialization evidence.

### Keep the existing technical decision boundary

Fresh-holdout eligibility requires improved validation SMDP TD, at least 5%
overall parent disagreement, at most 10% direct parent disagreement, at least
0.10 absolute changed-proposal executed-label agreement uplift, at most two
additional positive-energy End Turn selections, both validation strata,
complete callability provenance, exact round trip, and finite objectives.

Failure stops the corpus and points to a separately proposed residual/head.
Passing produces only a frozen candidate eligible for a separately registered
fresh holdout. The production r16 remains authoritative in both cases.

## Risks / Trade-offs

- [Risk] Schema-v3 can break code that assumes exact replay keys. -> Preserve
  default sampling, update strict loaders deliberately, and retain v1/v2 loads.
- [Risk] SMDP spans may cross a malformed combat boundary. -> Split on terminal
  markers first and fail on unknown, unreconciled, or cross-group successors.
- [Risk] Uncontrolled prefixes lose outcome information. -> Report them
  separately; they cannot be attributed to a candidate decision.
- [Risk] Ten games may have an empty validation stratum. -> Require both strata
  and stop without fitting if the registered corpus cannot support the gate.
- [Risk] The best prior scalar objective may still drift. -> Run it once under
  the corrected callability boundary, then move to residual/head without tuning.

## Migration Plan

1. Add RED coverage for pending proposal identity, schema-v3 round trip,
   v1/v2 unknown restoration, consistency validation, and default sampling.
2. Implement proposal attribution and replay persistence without action changes.
3. Add RED coverage and implementation for SMDP span construction and the
   fixed callability-filtered runner.
4. Run focused tests and one optimized commit gate, then commit and push the
   implementation boundary.
5. Register and collect the bounded zero-update fresh replay; restore the
   CommunicationMod config and stop game processes after the cohort.
6. Audit provenance and spans. If every pre-fit gate passes, execute the fixed
   CPU fit once and publish the decision.
7. Sync and archive the change. Rollback disables consumption of schema-v3
   fields; no production weights or action-selection code need restoration.

## Open Questions

None. The fixed recipe and residual/head fallback are decided before fresh data
collection.
