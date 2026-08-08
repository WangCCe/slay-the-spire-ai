## Context

The sealed r2 bundle contains eight independently verified checkpoint/evidence
pairs and exposes every cross-fitted prediction, advantage, policy term, fold
binding, gradient component, and candidate diagnostic needed for a source-only
audit. The terminal verifier proves structural and arithmetic integrity, but it
does not answer whether lower-bound clipping is related to the remaining
card-reward `take` pressure or whether that pressure persists on supported
unclipped rows.

The output tree also contains an inactive `.execution.lease` that is not part
of the manifest. An audit must prevent a concurrent writer, retain the exact
tracked terminal identity, avoid importing Torch/native/runtime modules, and
stream the roughly 244 MiB canonical evidence within a bounded memory surface.

## Goals / Non-Goals

**Goals:**

- Reuse the independent terminal verifier rather than creating a weaker
  parallel definition of valid r2 evidence.
- Hold the inactive execution lease while rechecking immutable identities and
  reading every chunk.
- Reconstruct baseline support, residual, advantage, direct take-logit
  pressure, gradient-component, and final-window saturation diagnostics under
  fixed strata.
- Publish compact deterministic JSON and Markdown from a pushed source commit.
- Produce one bounded descriptive verdict that selects the next source-only
  question without authorizing another empirical run.

**Non-Goals:**

- Refit the baseline, replay trajectories, load Torch/native/model code, access
  a seed, evaluate a policy, run OPE, or launch the game.
- Change clipping bounds, support thresholds, saturation rules, rewards,
  coefficients, architecture, or historical evidence.
- Interpret direct logit pressure as a full shared-parameter gradient, causal
  card value, or policy improvement.

## Decisions

### Add a separate cross-fitted audit module

Create `analysis_scripts/audit_cross_fitted_baseline_support.py` and a focused
test module. The existing hierarchical credit-assignment audit remains bound to
the older single `training_rows.json.gz` schema and normalized-return objective;
retrofitting it would mix two immutable evidence contracts and weaken both.

Alternative: extend the old audit with mode flags. Rejected because its
constants, manifest schema, lease identity, row format, and pressure semantics
are intentionally experiment-specific.

### Verify first, then lock and bind the exact snapshot

Run the existing standard-library `verify_terminal_bundle` before analysis.
Then acquire a non-blocking exclusive lock on the inactive lease, require the
exact r2 identity, and while holding it revalidate the terminal and manifest
self-digests, exact tracked file inventory, per-artifact sizes/digests, and the
verifier result. Stream and analyze evidence only under that lock.

The expected terminal, manifest, registration, authorization, and r2 closeout
hashes are constants derived from commit `7f2f08878e08d9276425f2fb99a97cf095361c9e`.
The audit source and tests are separately bound to a pushed `--source-commit`;
HEAD, origin/master, and worktree source bytes must match before publication.

Alternative: trust the postmortem summary. Rejected because it is descriptive
and cannot replace the manifest, checkpoint, and independent-verifier chains.

### Stream one deterministic-gzip chunk at a time

Read each registered evidence gzip in checkpoint order, enforce stored and
uncompressed bounds and digests, analyze it, and discard row payloads before
the next chunk. Retain only bounded aggregate accumulators and the exact row
coordinate of any non-`take` final-window greedy-family exception.

Alternative: concatenate all decisions in memory. Rejected because the report
needs no cross-chunk row joins beyond fixed accumulators and seed/fold counts.

### Use fixed support and attribution strata

Report chunk, fold, category, clipping status, selected family, advantage sign,
pre-decision effective-floor bands `<17`, `17..33`, `>=34`, and card-reward
ordinal `first`, `second`, `later`. A binary clipping contrast is supported only
with at least 64 rows and at least 16 rows on each side; selected `take`/`skip`
comparisons additionally require at least 16 of each. Sparse rows remain
visible and are never merged or used to change thresholds.

For each multi-family card reward, compute direct take-logit update pressure
from the recorded cross-fitted advantage and registered family/conditional
entropy terms. Reconcile policy-loss scalar components and preserve the stored
full-gradient comparison separately; never equate row-local pressure with the
shared network gradient.

### Bound the verdict to baseline support

Use only these terminal verdicts:

- `take_pressure_persists_on_supported_unclipped_rows`;
- `take_pressure_concentrated_in_clipped_rows`;
- `take_pressure_not_consistently_aligned`; or
- `insufficient_support_or_evidence`.

The report separately records exact saturation-predicate behavior. No verdict
authorizes an algorithm change or another experiment.

### Publish from a pushed source identity

First commit and push the proposal, source, and tests. Run focused tests,
source/import isolation, and the applicable tiered commit gate. Then invoke the
audit twice in fresh isolated processes with the exact pushed source commit and
separate staging paths. Publish only if both JSON and Markdown bytes match.

## Risks / Trade-offs

- **Private verifier behavior drifts** -> Depend only on its public terminal
  entry point and independently recheck fixed hashes under the audit lease.
- **A writer appears between verification and lock acquisition** -> Fail closed
  if the lease is active or any fixed identity differs after lock acquisition.
- **Clipping is correlated with state but not causal** -> Label every
  comparison descriptive and expose support counts without confidence claims.
- **One rare `bowl` row dominates exact saturation classification** -> Preserve
  its exact coordinate and report both the registered Boolean predicate and the
  1,773/1 descriptive concentration.
- **Large evidence slows iteration** -> Stream per chunk, keep focused unit
  fixtures small, and reserve full real-bundle analysis for the final two-run
  deterministic publication gate.

## Migration Plan

1. Validate and push this OpenSpec plan before implementation.
2. Add RED fixtures for identity/lease failure, clipping strata, pressure
   arithmetic, support verdicts, final-window exception, determinism, and
   forbidden imports.
3. Implement the source-only streaming audit and pass focused plus applicable
   tiered gates.
4. Commit and push the audit source identity with no analytical report.
5. Run two fresh source-only audits against the sealed r2 bundle; require exact
   output equality, then publish the report in a separate closeout commit.
6. Sync the new capability, update project direction, archive, and push.

Rollback before report publication removes only additive uncommitted audit
files. After publication, rollback preserves the report as evidence and uses a
new change for any correction; the r2 bundle is never modified.

## Open Questions

None.
