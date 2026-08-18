## Context

The simulator training runner currently consumes the production RL v2
observation shape (`328` continuous features plus card, potion, and relic IDs).
Monster slots carry health, intent, damage, and generic powers, but no encounter
identity. The r4 parent must remain the control, so a feature experiment cannot
silently replace it with a randomly initialized wider network.

## Goals / Non-Goals

**Goals:**

- Add deterministic encounter information only when explicitly requested.
- Migrate the r4 simulator checkpoint into the wider input shape while keeping
  its pre-training policy numerically equivalent.
- Bind the feature encoding and migration evidence in the report/checkpoint.
- Test the new information on fresh LightSTS train and held-out cohorts.

**Non-Goals:**

- Change the production `StateEncoderV2`, CommunicationMod, or live checkpoint
  format.
- Claim that simulator encounter identity is already available in live form.
- Tune hash size, replay balance, anchor weight, or optimizer budget after
  outcome access.

## Decisions

1. The runner appends a `64`-bucket one-hot feature derived from the canonical
   snapshot encounter string with SHA-256. A fixed hash avoids a mutable
   vocabulary or native-module API change while remaining deterministic.
2. The feature is appended to the continuous observation. During warm start,
   the first hidden layer copies legacy continuous columns in place, inserts
   zero columns for encounter features, and shifts all existing embedding
   columns unchanged. Every other parameter is copied exactly.
3. Before trajectory collection, the runner compares masked Q values and greedy
   actions from the legacy parent and migrated control on deterministic probe
   observations. Failure is a pre-training blocker.
4. The default bucket count remains zero. Fresh initialization with positive
   buckets is rejected because the experiment requires a bound parent control.
5. Training keeps the established stratified replay and parent-anchor recipe.
   The only experimental variable is encounter information.

## Risks / Trade-offs

- Hash collisions can merge encounters. -> Bind the bucket count and algorithm,
  report observed bucket occupancy, and treat this as a screening experiment.
- Simulator encounter names may not map directly to live monster names. -> Keep
  checkpoints production-incompatible and require a separate transfer design.
- Wider-input migration can shift columns incorrectly. -> Add structural tests
  plus pre-collection Q-value and action equivalence checks.
- The feature may overfit encounter identity. -> Use disjoint fresh seeds and
  retain per-battle-index guardrails; a failure rolls back by setting buckets to
  zero and retaining r4.
