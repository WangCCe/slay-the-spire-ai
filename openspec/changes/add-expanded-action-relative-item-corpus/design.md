## Context

The original corpus contains 1,633 training states from 256 seeds. The
selective base head reaches `0.857` fit accuracy but only `0.449` calibration
accuracy. Direct item semantics increase fit accuracy to `0.981` while
calibration remains `0.472`. This is a shared generalization failure, not
evidence for another feature or threshold adjustment.

The original native adapter and corpus runner remain byte-identical to their
successful registration. Corpus generation is simulator-only and does not
start Slay the Spire or CommunicationMod.

## Goals / Non-Goals

**Goals:**

- Increase independent paired-return training support by four times while
  preserving the same parent, simulator, encounter profiles, horizons,
  canonicalization, reward, and return calculation.
- Reserve a larger seed-disjoint calibration partition and one untouched fresh
  evaluation partition.
- Run one item-semantic fit with the already tested recipe and decide against
  the original production-oriented offline gates.

**Non-Goals:**

- Changing LightSTS mechanics, branch horizon, reward, action families, labels,
  model architecture, optimizer, update count, calibration quantile, or gates.
- Starting CommunicationMod or gameplay, writing production checkpoints, or
  promoting a candidate in this change.
- Reusing the consumed `263xxx` comparison as fresh evidence.

## Decisions

### Fixed expanded cohort

Generate training seeds `264000..265023` and fresh evaluation seeds
`266000..266255`, with battle indices `0,3,6,9` and two retained states per
profile. Within training, fit uses `264000..264767` and calibration uses
`264768..265023`. These ranges are disjoint from all earlier `262xxx` and
`263xxx` model-selection evidence.

The cohort is approximately four times the original training support. A
smaller increase was rejected because both models show a large fit-to-
calibration collapse. A much larger cohort was rejected until this scale shows
whether the learning curve moves.

### Reuse immutable generator bytes

Bind and reuse:

- native module SHA-256
  `195678b7fc6bf69815f3d2971404afb8ce72fb666700edf4203383429caf1009`;
- corpus runner SHA-256
  `bf8392f2dc61b02ecd5507e0fe589750a5a859cf2f5c5ccf24d9c15840ffb772`;
- simulator-only r16 shadow SHA-256
  `ce2ae34f82b3f457fb35e87d429c397204c42d0f742d3ac8952d91b69119b83b`;
  and
- items.json SHA-256
  `e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc`.

Do not rebuild or mutate the native build directory. The corpus registration
contains the exact command and output path. A pre-start or infrastructure
failure may be retried only when no output directory exists and the fixed
bindings remain unchanged; this avoids the earlier impractical blanket retry
ban without permitting a changed experiment.

### One post-corpus item-semantic fit

After generation succeeds, bind the new corpus file hashes into a compact
source-committed runner. Reuse the item-semantic feature path, 4,096 updates,
128 samples per class, 128 ranking pairs, Adam `0.001`, ranking weight `0.5`,
and finite-sample 95th-percentile negative calibration threshold.

Evaluation loads only after fit and calibration. Pass requires at least 30
interventions, precision at least `0.65`, mean selected true advantage above
`0.18881003558635712`, mean policy regret below `3.1811342239379883`, and zero
severe, illegal, or forbidden selections. A pass may justify a later fresh
matched LightSTS policy gate but grants no authority by itself.

### Verification budget

The existing generator has focused tests and unchanged bytes. Validate the
registration and output hashes without rerunning its full suite. New training
code receives focused tests, strict OpenSpec validation, and exactly one timed
commit gate at the completed source boundary.

## Risks / Trade-offs

- [More samples can preserve the same bias] -> The untouched fresh gate closes
  the recipe if precision or severe risk does not improve.
- [Native generation is the expensive stage] -> Use the existing fast module,
  fixed bounded profiles, and a single cohort; do not start gameplay.
- [Large in-memory corpus collection can fail] -> Permit an identical retry
  only when no output exists; never change seeds or bounds under the same id.
- [Fresh evaluation is consumed by a failed fit] -> Treat failure as final for
  this recipe and require new seeds for any later architecture.

## Migration Plan

1. Commit OpenSpec artifacts and the exact corpus registration.
2. Run the fixed native corpus generation and verify sufficiency and hashes.
3. Implement and commit the compact expanded-corpus training runner.
4. Execute one item-semantic fit and untouched fresh evaluation.
5. Run one final gate, sync specs, archive, commit evidence, and push.

Rollback is non-use of the generated corpus and development artifact. No
production state is modified.

## Open Questions

None. Any seed, horizon, profile, feature, optimizer, threshold, or gate change
requires a new change rather than mutation of this cohort.
