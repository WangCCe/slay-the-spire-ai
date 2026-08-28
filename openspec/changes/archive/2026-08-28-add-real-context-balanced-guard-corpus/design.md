## Context

The current 6,473-row training and 1,643-row fresh evaluation paired-return
corpora use battle indices `0,3,6,9`. They are useful for action-relative labels
but overrepresent early, high-HP, potion-rich simulator contexts. Exact-cell
post-stratification against complete production-r16 replay materially reduces
inventory mismatch, yet evaluation support remains sparse after floor 27.

A 32-seed native diagnostic over battle indices `10..24` showed that `10..14`
produce the desired floors 23..34. Later indices are mostly unreachable under
the native baseline or fall beyond the target stratum. The diagnostic completed
quickly enough that targeted collection is cheaper and narrower than adding an
arbitrary real-combat-state import surface.

## Goals / Non-Goals

**Goals:**

- Generate immutable train and fresh-evaluation late-floor supplements from
  disjoint seeds and battle indices `10..14`.
- Preserve the existing paired-return labels and tensor contract.
- Combine each supplement with its corresponding expanded corpus partition.
- Derive deterministic real-context density-ratio weights and publish support,
  ESS, SMD, floor, legality, and provenance evidence.
- Fail closed before fitting unless both partitions satisfy the registered
  support gates.

**Non-Goals:**

- Training, tuning, model selection, policy evaluation, OPE, qualification, or
  promotion.
- Game or CommunicationMod execution and production checkpoint mutation.
- Exact simulator equivalence, causal attribution, or arbitrary state import.
- Changing the native paired-return reward, continuation, guard, or branch
  semantics.

## Decisions

### Use a supplement instead of regenerating the early corpus

The existing corpus is immutable, validated, and provides useful early support.
The runner will bind and load its exact hashes, collect only the missing
late-progression profiles, filter supplement rows to floors 23..34, and
concatenate aligned tensors and metadata by partition. This keeps historical
evidence reproducible and limits native work.

Alternative: regenerate all battle indices in one new corpus. Rejected because
it repeats roughly 52 minutes of accepted work and increases the number of new
states without specifically addressing the observed support hole.

### Bind battle indices 10 through 14 and disjoint seed ranges

The fixed collection uses training seeds `268000..269023` and fresh evaluation
seeds `270000..270511`, battle indices `10..14`, at most two retained states per
profile, and the existing return recipe. These ranges are disjoint from the
expanded corpus, the 267000-series diagnostic, and each other.

Alternative: include indices 15 through 24. Rejected because the diagnostic
shows sharply lower reachability and increasing floors above 34, which spends
native time outside the identified gap.

### Publish weights separately from compatible corpus tensors

Combined `train_corpus.pt` and `evaluation_corpus.pt` retain the existing
`combat_guard_advantage_corpus` schema. A separate `context_weights.pt` binds a
non-negative normalized weight vector to each partition and records each row's
cell identity. This avoids breaking existing corpus loaders while making any
future weighted fit explicit.

### Use exact, interpretable post-stratification cells

Cells consist of canonical floor stratum, occupied potion slots, occupied relic
slots, and player-HP quartile. A simulator cell receives the real-to-simulator
density ratio; cells absent from real replay receive zero weight. The runner
reports real mass covered, simulator mass retained, ESS, maximum row weight,
and raw/weighted SMDs.

Alternative: propensity modeling or learned domain adaptation. Rejected for
this stage because it adds model-fit uncertainty before simple observed-context
support has been established.

### Gate corpus support before any training authority

Both partitions must be tensor-aligned, legal, finite, provenance-valid, and
class-complete. The combined corpus must satisfy all of these registered gates:

- at least 256 fresh-evaluation rows across floors 23..34;
- overall real context mass coverage at least 90% per partition;
- floors 23..27 coverage at least 80% and floors 28..34 coverage at least 60%
  per partition;
- weighted ESS at least 750 for train and 400 for fresh evaluation;
- maximum normalized row weight at most 1.5%;
- weighted absolute SMD at most 0.20 for player HP, potion occupancy, and relic
  occupancy, and at most 0.30 for floor ratio;
- zero illegal guard/target actions and zero train/evaluation seed overlap.

Passing publishes only `corpus_support_ready_for_separate_weighted_fit`.
Failing publishes `corpus_support_insufficient_close_without_fit` and grants no
retry with changed seeds, thresholds, battle indices, or bounds under this
change.

## Risks / Trade-offs

- [Late profiles remain unreachable] -> Preserve initialization failures and
  close without fitting; only then reconsider exact state import in a new
  proposal.
- [Exact cells create high-variance weights] -> Enforce ESS and maximum-weight
  gates and retain zero-weight rows in the immutable corpus for auditability.
- [Replay and paired-return rows represent different selection mechanisms] ->
  State that weights calibrate observed context support only and grant no
  unconditional distribution or policy-quality claim.
- [Supplement changes label proportions] -> Publish partition-local class,
  target-identity, floor, encounter, and source-component summaries; do not
  rebalance labels in this change.
- [Native collection is interrupted] -> Write only to a new output directory
  and publish success artifacts after validation; existing corpora remain the
  rollback boundary.

## Migration Plan

1. Add focused source-only tests for binding, filtering, concatenation,
   weighting, gates, and fail-closed publication.
2. Implement the registered runner and validate it against synthetic fixtures.
3. Commit the immutable registration and run one source-only preflight.
4. Execute the bounded native collection once and publish the combined corpus
   and support report.
5. If gates pass, create a separate OpenSpec change for one weighted fit. If
   they fail, close this line without training and retain the prior corpus.

Rollback requires no mutation: downstream consumers continue to use the
existing expanded corpus hashes unless a later change explicitly binds the new
artifacts.

## Open Questions

None. Any threshold, seed, profile, or weighting change after registration is a
new evidence question and requires a new change rather than an in-place retry.
