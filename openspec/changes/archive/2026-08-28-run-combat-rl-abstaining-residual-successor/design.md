## Context

The fresh zero-update residual cohort is qualified and immutable. Its replay
contains `350` direct and `502` changed-proposal candidate-decision starts,
with complete callability, SMDP, trace, inventory, and runtime reconciliation.
The collection registration already freezes the residual architecture,
optimizer recipe, split and training seeds, and downstream technical gates.

The mechanism implementation proves exact parent equivalence at zero entry and
keeps every parent parameter frozen. This change must bind that mechanism to
the qualified replay without reopening the recipe or granting production
authority.

## Goals / Non-Goals

**Goals:**

- Validate the exact registered source, cohort, checkpoint, report, and recipe
  before any optimizer update.
- Fit only the residual correction head for exactly `128` CPU updates using
  balanced direct and changed-proposal SMDP spans.
- Publish partitioned gate, action, TD, End Turn, integrity, and serialization
  evidence against the frozen production-r16 parent.
- Make the result deterministic, restorable, non-production-compatible, and
  eligible only for a separately registered fresh holdout when every fixed
  technical gate passes.

**Non-Goals:**

- Tune the registered recipe, thresholds, seeds, cohort, or architecture after
  observing the result.
- Reuse the closed R1 replay, retry a failed fit, or fit a second candidate on
  this corpus.
- Launch gameplay, modify CommunicationMod, replace production r16, claim
  policy quality, or promote a candidate.

## Decisions

### Bind execution separately from the frozen collection registration

A runner-binding supplement records the runner source hash, input checkpoint
and report hashes, output identity, command, interpreter, and one-shot failure
policy. The supplement may not restate or change the recipe or gates. This
keeps the earlier registration immutable while still binding code that did not
exist when the cohort was collected.

### Reuse deployment-consistent SMDP construction

The runner uses the existing candidate-decision span builder, terminal-combat
split, balanced stratified schedule, frozen-parent masked-greedy bootstrap, and
variable discount targets. No-proposal rows can contribute only inside a span;
they are never sampled as independent decisions. Reusing these helpers avoids
creating a second interpretation of callability provenance.

### Optimize only the correction head

The adapter is constructed from the checkpoint's production-r16 online state.
Its parent is evaluated and detached, and the optimizer receives only
correction parameters. Direct rows supervise the gate closed. Changed rows
supervise the gate open, executed action, and registered SMDP target. The fixed
loss weights, hidden width, threshold, residual scale, learning rate, batch
composition, update count, and seeds come directly from the registration.

### Evaluate hard-gated behavior by partition and provenance

Training and validation reports compare parent and hard-gated adapter actions
and executed-action SMDP TD loss. They also report gate-open share overall and
for direct and changed strata, executed-label agreement, positive-energy End
Turn behavior, parent immutability, objective finiteness, and exact artifact
round trip. Eligibility is the conjunction of the preregistered checks; no
single improved metric can override a failed stability or integrity gate.

### Publish atomically and stop on any failure

The runner writes to a staging directory and renames it only after all expected
artifacts and checks are complete. A started attempt cannot be retried, tuned,
or redirected. A failed result leaves production r16 authoritative and closes
this corpus to further fitting.

## Risks / Trade-offs

- [Risk] The gate learns provenance labels but does not generalize. -> Require
  changed gate coverage and direct abstention on the held-out combat split,
  then require a separately registered fresh holdout before any live claim.
- [Risk] SMDP TD improvement is driven by changed rows while direct behavior
  drifts. -> Keep direct disagreement and direct gate-open ceilings as hard
  gates rather than aggregate diagnostics.
- [Risk] The fixed recipe is underpowered. -> Report failure and close the
  corpus; do not tune on the observed result.
- [Risk] A custom artifact is mistaken for a production checkpoint. -> Mark it
  non-production-compatible and leave production loaders unchanged.
- [Risk] Partial output is mistaken for a completed result. -> Use staging,
  explicit receipts, and atomic final publication.
