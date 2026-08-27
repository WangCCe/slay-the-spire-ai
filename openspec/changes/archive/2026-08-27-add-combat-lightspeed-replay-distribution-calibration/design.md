## Context

The combat LightSTS runner can collect RL-v2 replay with a frozen simulator
shadow of production r16, but its reports summarize simulator outcomes rather
than compare the collected transition distribution with real gameplay. The r14
and r15 parent-on-policy collections contain complete, untruncated schema-v1
replay snapshots from zero-epsilon r16 gameplay. The current loader also supports
schema-v2; its additional executed-action anchor flag is irrelevant to this
descriptive audit. Both schemas expose the same continuous,
card, potion, relic, action, reward, terminal, and action-mask tensors used by
LightSTS collection.

The sources are not matched environments: they have different run seeds,
progression policies, and trajectory boundaries. The POC must therefore remain
descriptive and stratified, not turn marginal similarity into a mechanics or
policy-quality claim.

## Goals / Non-Goals

**Goals:**

- Validate and bind complete real replay snapshots and a fresh zero-epsilon
  frozen-r16 LightSTS collection.
- Summarize comparable RL-v2 fields within explicit floor strata and rank the
  largest descriptive mismatches.
- Distinguish technical comparability from low divergence so a large mismatch
  remains a useful successful result.
- Produce compact deterministic JSON, Markdown, and manifest artifacts without
  serializing another raw replay copy.

**Non-Goals:**

- Arbitrary real combat-state import into `sts_lightspeed` or step-for-step
  mechanics equivalence.
- Gameplay, CommunicationMod control, training, optimizer updates, OPE, policy
  evaluation, candidate selection, packaging, qualification, or promotion.
- A scalar promotion threshold or tuning simulator seeds to resemble the real
  replay.

## Decisions

### Reuse canonical RL-v2 tensors

The audit reads real replay through `load_torch_checkpoint(...,
weights_only=True)` and validates complete schema-v1 or schema-v2 snapshots with
`ReplayBufferV2.load_state_dict`.
LightSTS transitions come from the existing `collect_transitions` path using the
bound simulator shadow parent with epsilon zero. This avoids a second encoder
and compares the exact representation consumed by combat RL.

Parsing the verbose decision-trace JSON directly was rejected for the first POC:
it would duplicate game-object reconstruction and mix logging coverage with
checkpoint coverage. The trace archives remain follow-up evidence for concrete
mismatches.

### Compare within canonical floor strata

Floor is recovered from continuous feature index 3 using the encoder's
`min(floor, 50) / 50` contract. The fixed strata are `0..5`, `6..10`, `11..17`,
`18..22`, `23..27`, `28..34`, `35..39`, `40..44`, and `45..50`. Reports include
all source strata, but rank comparisons only where both sources have at least
the registered minimum transition count.

Matching global row counts was rejected because it would still confound
progression mix. Stratum-local summaries preserve all rows and make coverage
gaps explicit.

### Use interpretable descriptive metrics

Per source and stratum, summarize player HP, energy, block, floor, alive-monster
count, occupied hand/potion/relic slots, legal-action count, reward, and terminal
rate. Report executed combat-action family counts, action-index support, and
card/potion/relic ID support. Numeric comparisons include mean deltas and
absolute standardized mean differences; categorical comparisons use total
variation distance and support overlap.

These metrics are ranked separately rather than combined into one score.
Degenerate variance is reported explicitly. No threshold is interpreted as
mechanics equivalence.

### Bind operations and keep authority false

The report binds repository source hashes, native/simulator provenance, item
metadata, every real checkpoint, parent checkpoint, exact collection config,
and canonical report identity. It records native and checkpoint loading plus
simulator collection as performed operations. All gameplay, training,
evaluation, OPE, policy-quality, mechanics-equivalence, qualification, and
promotion authority remains false.

Registered runner, item metadata, and native module hashes are checked before
native loading. Adapter and simulator source identities are checked after the
module provenance handshake but before any environment construction.

## Risks / Trade-offs

- [Marginal differences conflate mechanics, policy, and progression] -> Compare
  only within floor strata and label every result descriptive; use decision
  traces only after a mismatch suggests a concrete hypothesis.
- [Real replay does not retain seed or encounter identity per transition] -> Do
  not claim matched trajectories; report this attribution limit prominently.
- [Serial correlation makes row counts look more independent than they are] ->
  Avoid confidence intervals and causal tests in the POC; publish counts and
  descriptive effect sizes only.
- [Importing the training module could accidentally fit] -> Call only explicit
  initialization and collection functions, assert optimizer step remains zero,
  and keep training/evaluation functions outside the audit path.
- [Native collection can be slow] -> Bound fresh seeds, battle indices,
  decisions, wall time, and output size in a separate immutable registration.

## Migration Plan

Add the standalone runner and focused tests, validate the OpenSpec change, and
commit the capability before creating an execution registration. Execute one
fresh bounded POC and publish its report separately. Rollback deletes this
offline capability and its reports; no production migration is required.

## Open Questions

After the POC, decide from the ranked mismatches whether the next evidence step
is decision-trace reconstruction, richer simulator state identity, or a small
fresh real-game collection. The current change does not preselect one.
