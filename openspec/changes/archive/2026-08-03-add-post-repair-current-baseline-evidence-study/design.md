## Context

Formal non-combat RL readiness passes state/action, reference isolation, reward,
and evaluation, but remains blocked on a credible non-teacher baseline floor
and source-comparable target-supported outcomes. Current is the only eligible
non-teacher baseline candidate. Its frozen-row bridge checks pass, but the v1
and r2 own-trajectory diagnostics each retained zero rows: v1 failed on an
invalid candidate field and r2 failed on the native `Elixir Potion` display
name. Both identities are consumed and immutable.

The candidate-schema defect and all statically known base-game item-name gaps
are independently fixed. A no-native planning-HEAD recomputation over 83
tracked sources and 8,315 seed rows found 348 excluded values; neither
`11000..11015` nor `12000..12063` overlaps them. The older persisted inventory
is historical, so preregistration must publish and bind a new current snapshot.
There is still no empirical proof that Current completes an own trajectory
after the repairs.
Another diagnostic would answer the same structural question for a third time
without producing a policy-quality contract. This design instead makes one
formal baseline study bear that risk under conservative, no-retry rules.

## Goals / Non-Goals

**Goals:**

- Produce one immutable, deterministic Current baseline-floor result with an
  absolute gate and a paired weak-control gate.
- Protect the untouched holdout through a fixed canary stop gate.
- Include every selected episode in the denominator and make exact declared
  support blockers conservative non-victories at their last supported floor.
- Preserve v1 and r2 byte-for-byte and prohibit r3 or any replacement cohort.
- Separate source implementation, preregistration, and explicit execution
  approval so offline work cannot silently access native environments.

**Non-Goals:**

- No policy change, training, model fitting, hyperparameter selection, reward
  selection, gameplay, Communication Mod work, OPE, qualification, loading, or
  promotion.
- No claim that simulator victories satisfy the live target-supported-outcome
  domain.
- No SimpleAgent or Bottled action, label, score, agreement, or outcome in a
  pass gate.
- No generic experiment framework, diagnostic runner copy, simulator rebuild,
  new support approximation, or post-result repair inside this change.

## Decisions

### Use an integrated study instead of a third diagnostic

The study is a new capability and publication identity, not a v3 diagnostic
profile. It evaluates policy quality directly and treats structural risk as a
terminal study risk. Unexpected structural failures block publication; exact
predeclared support blockers remain retained conservative rows. Neither case
can be retried or converted into a new cohort.

Alternative: prepare r3 on the same four reused seeds. Rejected because r2
explicitly forbids r3 and a third structural-only result would still leave all
floor-contract checks unresolved.

Alternative: declare the bridge ready from static coverage. Rejected because
static names do not prove reachable snapshot hydration or episode completion.

### Use a fixed canary and untouched holdout

The canary is exactly seeds `11000..11015`; the holdout is exactly
`12000..12063`. Registration validation binds the current tracked exclusion
inventory and rejects any overlap, duplicate, omission, reorder, replacement,
or runtime override. The canary is a stop gate only. No action, floor, blocker,
or outcome can change code, thresholds, policies, or holdout membership.

Each episode has at most 500 target decisions. The canary permits exactly 64
policy episodes across two policies and two executions and at most 600 seconds.
The holdout permits exactly 256 policy episodes and the entire durable attempt
at most 1,800 seconds. Exceeding either bound is an unexpected structural
failure, not a conservative support row.

Canary passes only with all 16 paired rows retained, exact replay identity,
zero unexpected failures, at most one declared-support row per policy, all four
target categories for Current, Current mean floor at least 15, and mean
Current-minus-control floor at least zero. Failure publishes a terminal
negative or blocked result and proves the holdout remained untouched.

Alternative: one 80-seed cohort. Rejected because an early implementation
boundary would spend every untouched seed before proving basic viability.

Alternative: reused development seeds for canary. Rejected because that is r3
in substance and carries selection history.

### Compare Current with a deterministic first-candidate weak control

Each seed runs Current and the existing ordered first-candidate policy in
independent environments under identical simulator and baseline-controlled
non-target behavior. The control is intentionally weak and reference-free. It
supports a paired improvement gate but cannot define the absolute floor.

SimpleAgent and Bottled remain excluded because the readiness audit classifies
them as auxiliary references rather than policy-quality truth. Existing
SimpleAgent and first-candidate reports may justify preregistered thresholds but
their actions and outcomes do not enter this study.

Alternative: use SimpleAgent as the primary comparison. Rejected because its
teacher suitability failed and would reintroduce the reference-policy conflict
the readiness audit already closed.

### Require independent absolute and paired holdout gates

All 64 holdout pairs remain in both aggregate and paired metrics. A passing
floor requires:

- zero unexpected structural failures;
- at most three exact
  `unsupported_shop_courier_restock_semantics` rows per policy;
- aggregate Current coverage of route, shop, event, and card reward;
- Current mean terminal/conservative floor at least 18;
- a 95% percentile-bootstrap lower bound on Current mean floor at least 15;
- mean paired Current-minus-control floor at least 3; and
- a 95% paired percentile-bootstrap lower bound greater than zero.

The bootstrap uses exactly 10,000 resamples and integer seed `20260803`.
Absolute and paired draws are canonical artifacts. Victories, supported-only
summaries, and SimpleAgent historical context are report-only diagnostics and
cannot override a failed gate.

The absolute gate is above the observed 13.2 mean of the 20-seed first-candidate
adapter POC and the 14.5625 mean of the failed smoke-trained policy, while
remaining below the historical 19.96875 SimpleAgent mean. These historical
values select a fixed competence band without using unobserved Current results.

### Implement a focused runner from existing public boundaries

Add a new runner that composes `NativeSimulatorEnvironment`,
`CurrentPolicyBridgeSession`, registered metadata/event semantics, canonical
JSON/hash helpers, and the deterministic bootstrap helper. Implement only the
small policy-neutral episode orchestration and first-candidate selection needed
for this study. Do not copy the diagnostic registration/publication framework
or modify its v1/r2 profiles.

The runner validates all tracked and external identities before loading the
native module, writes a durable started journal before native loading or the
first environment, and writes canonical rows, metrics, report, configuration,
and manifest atomically. Only
`unsupported_shop_courier_restock_semantics` may become a conservative support
row; every other runtime or bridge failure is unexpected. A no-native verifier
reconstructs every deterministic artifact from registration, journal, and rows.

Verdict precedence is invalid/unverifiable, interrupted, unexpected structural
failure (`study_blocked`), structurally valid canary gate failure
(`study_stopped_at_canary`), structurally valid holdout without every quality
gate (`study_valid_without_baseline_floor`), then
`study_valid_with_baseline_floor`.

### Separate implementation, preregistration, and execution authority

Planning is committed first. Source and tests are then implemented and pass
focused tests, `py_compile`, exact historical v1/r2 verification, the repository
commit gate, and strict OpenSpec validation before a registration exists. A
later registration commit binds the clean pushed implementation, exact cohorts,
seed inventory, thresholds, module, simulator, metadata, runtime, and all-false
authority.

Even a valid pushed registration cannot execute until the user explicitly
approves the exact registered command. That approval covers one canary and, only
if its fixed gate passes, one conditional holdout within the same durable
attempt. It never authorizes training or another study identity.

## Risks / Trade-offs

- [Risk] A new bridge defect consumes the canary and yields no floor result.
  -> Mitigation: known static item gaps are closed, production-shaped source
  regressions run first, and the failed canary remains terminal rather than
  triggering another repair/retry loop.
- [Risk] A weak control makes relative improvement easy. -> Mitigation: the
  independent absolute mean and bootstrap-lower-bound gates are mandatory.
- [Risk] Sixteen canary seeds give noisy quality estimates. -> Mitigation: the
  canary uses means only as a coarse stop gate; all inferential gates use the
  untouched 64-seed holdout.
- [Risk] Exact Courier support blocks distort results. -> Mitigation: retain
  them as non-victories at last supported floor, cap them per policy, and
  publish supported-only values only as diagnostics.
- [Risk] Proposal and execution authority blur under standing authorization.
  -> Mitigation: registration validation requires a separate tracked execution
  authorization artifact created only after explicit user approval.
- [Trade-off] Two policies, two stages, and exact replay require up to 320
  policy episodes. This is more expensive than a diagnostic but directly
  resolves the floor question if successful.

## Migration Plan

1. Commit and push this planning change with no runner or registration.
2. Add red registration, cohort, episode, gate, publication, and no-authority
   tests; implement the source-only runner and no-native verifier.
3. Pass focused verification, exact v1/r2 artifact checks, the repository
   commit gate, and strict OpenSpec validation; commit and push implementation.
4. Build a canonical seed-exclusion audit and registration from that pushed
   source, validate external identities without constructing an environment,
   then commit and push preregistration.
5. Stop for explicit execution approval. If approved, write the journal and run
   canary once; run holdout automatically only when the fixed canary gate passes.
6. Verify and close out the terminal result, then perform a separate read-only
   baseline/readiness refresh. Sync and archive this change.

Before step 5, rollback may remove the unconsumed source and registration. From
the first started journal onward, rollback preserves all evidence and never
creates a replacement identity.

## Open Questions

None. Any request to change policy code, seed membership, thresholds, support
semantics, bootstrap, replay, or authority stops this change and requires a new
proposal before empirical execution.
