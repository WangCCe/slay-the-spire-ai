## Context

Combat LightSTS training produced three structurally compatible simulator-only checkpoints: r4 trained on first combats, and r5/r6 trained on battle indices `0,3,6,9`. Their existing reports compare each fitted candidate only with its own randomly initialized network, so uplift magnitudes cannot be used to rank candidates across runs. The comparison must remain source-only and use the current immutable r3 native module that includes later-battle initialization fixes.

## Goals / Non-Goals

**Goals:**

- Validate immutable checkpoint identity, simulator-only metadata, and network structure before evaluation.
- Evaluate all candidates on identical fresh profiles and report absolute, pairwise, and per-index metrics over reachable profiles.
- Preserve deterministic reachability accounting and fail on candidate-specific initialization differences.
- Produce one bounded report that decides whether any candidate merits a separately reviewed real-game gate.

**Non-Goals:**

- Fitting, fine-tuning, ensembling, or selecting actions from a production checkpoint.
- Starting Slay the Spire or CommunicationMod.
- Claiming simulator mechanics equivalence or production policy quality.
- Automatically promoting the best simulator candidate.

## Decisions

### Reuse the existing frozen evaluator

The comparator will instantiate the existing RL v2 trainer architecture, load one frozen `online_network_state_dict` at a time, and call `evaluate_policy` with the same module, item mapper, profile config, and decision bounds. This keeps action selection and reward semantics identical to the training reports.

Alternative: implement a separate inference loop. Rejected because it would duplicate action masking, card-selection settlement, reward, and reachability behavior.

### Bind candidates and evaluation inputs before execution

The registration will bind candidate labels, checkpoint paths and hashes, runner sources, native module, simulator sources, item export, seeds, battle indices, and limits. Checkpoints must be `simulator_training_smoke`, `production_compatible=false`, and have identical keys and tensor shapes.

Alternative: discover all checkpoints under `reports/`. Rejected because directory discovery makes the candidate set mutable and risks including unrelated artifacts.

### Rank only reachable matched profiles

Absolute and per-index policy metrics will exclude classified baseline-loss or run-terminal profiles. Every candidate must report the same reachability and initialization reason for each profile. Pairwise metrics will use the existing matched evaluator; any asymmetric initialization, unsupported state, or truncation is a blocker.

Alternative: assign zero reward and HP to unreachable profiles. Rejected because reachability is determined before the frozen policy acts and is not a policy outcome.

### Publish evidence, not promotion authority

The report will identify the ranking by reachable-profile mean reward, with victories and player HP as guardrails. A ready verdict only supports choosing a candidate for a separate real-game evaluation proposal.

## Risks / Trade-offs

- [All candidates share LightSTS bias] -> Keep mechanics-equivalence and live policy-quality authority false and require a later real-game gate.
- [One random evaluation cohort can overstate ranking] -> Use a fixed multi-index cohort and report every pairwise and per-index result; do not train or retune from the outcome.
- [Older candidates were trained against older adapter bytes] -> Evaluate all frozen weights on one current immutable module and preserve both training checkpoint bindings and evaluation source identity.
- [Later indices have fewer reachable profiles] -> Report counts per index and never hide missing coverage in aggregate zeros.

## Migration Plan

1. Add unit regressions for checkpoint compatibility, reachable aggregation, pairwise reachability, and report publication.
2. Implement the source-only comparator without changing the existing trainer or production agent.
3. Register one fresh cohort and run the comparison once.
4. Archive the change after focused tests and strict OpenSpec validation.

Rollback removes the comparator runner and reports; no checkpoint or production state is modified.

## Open Questions

None. A later real-game gate remains a separate decision based on the frozen comparison result.
