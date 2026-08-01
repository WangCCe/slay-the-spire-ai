## Context

The registered v2 outcome-evidence study remains stopped before `start`. R7
consumed its identity after `launcher_verified` and `runner_entered`, then
failed source validation. The immutable closeout correctly forbids r7 retry or
automatic r8 preparation. A separate source change subsequently reproduced
the mixed-line-ending and built-in `binary` attribute failures, implemented a
raw-first validator, passed focused checks plus the registered commit gate,
and was archived.

R8 is therefore a new evidence identity, not a repair of r7. It must reuse the
existing trusted launcher, bootstrap-v1/request-v3 protocol, no-action child,
standalone verifier, and request-bound restoration boundary. The operational
work crosses the repository, an external guarded root in the Slay the Spire
directory, the real CommunicationMod configuration, and Windows production
Python, so exact source and rollback anchors remain necessary even though no
runtime implementation change is planned.

## Goals / Non-Goals

**Goals:**

- Prepare one previously absent r8 candidate from a clean source snapshot and
  an exact live-state baseline.
- Prove offline that the archived source fix and every candidate/request byte
  are the reviewed inputs before publishing the external root.
- Permit at most one no-action CommunicationMod invocation and independently
  replay its exact complete or fail-closed boundary.
- Restore the request-bound configuration, compare protected inventories, and
  prove zero surviving target processes.
- Produce either a qualified handoff for a separate `start` review or a final
  retired disposition with no retry.

**Non-Goals:**

- Editing qualification, verifier, CommunicationMod, gameplay, policy,
  estimator, reward, or training source in this change.
- Retrying or changing r1-r7, preparing r9, tuning timeouts, or weakening
  source and isolation checks.
- Starting the registered study, creating its run lock, acting in game,
  collecting or inspecting outcomes, computing OPE, training, or promoting.

## Decisions

### 1. Use a new immutable identity after the archived source fix

R8 receives a previously absent root, request, launch token, and review
binding. R7 remains byte-for-byte historical evidence and its closeout remains
accurate for the knowledge and authority available when it was written.

Reopening r7 was rejected because the claim and failure chain consumed that
identity. Editing the historical closeout was rejected because later diagnosis
does not change the earlier disposition.

### 2. Keep the qualification amendment source-neutral

The frozen runtime implementation is an input. A source or protocol defect
found during r8 preparation or invocation ends this amendment's live path and
must be handled by a separate regression-backed OpenSpec change. No fix may be
folded into the candidate and no replacement identity may be generated here.

This preserves a stable S/R review relationship and prevents preparation from
turning into an unbounded implementation loop.

### 3. Reuse expensive test evidence only by exact input identity

The completed source-fix evidence may satisfy the registered commit-gate
requirement only when the frozen executable/importable source and relevant
test input hashes are identical. Candidate-specific focused tests, canonical
render replay, source-only validation, strict OpenSpec validation, and diff
checks always run. If the bound inputs differ, rerun the registered gate.

An unregistered raw full pytest invocation is excluded because the repository
commit gate is the maintained release contract and the raw suite has become a
known iteration bottleneck. Reuse is based on hashes and recorded outputs, not
on elapsed time or an assumption that docs-only changes are harmless.

### 4. Separate offline publication authority from the one live invocation

Candidate request bytes, proposed static root, launcher vector, source
inventory, baseline, and rollback package remain repository-local until one
externally anchored offline go/no-go record passes. A go permits exactly one
publication transition and, only after an exact post-publication comparison,
one ModTheSpire invocation through CommunicationMod and
`D:\anaconda\envs\stsai\python.exe`.

If publication occurs but invocation cannot be proven unissued, classify the
branch as a live-boundary retirement. Never delete or rewrite a published
root.

### 5. Require independent replay and branch-specific closeout

The standalone verifier must classify the immutable root when its required
anchors exist. Separate external evidence binds configuration restoration,
protected inventory equality, invocation observations, and process death.
The allowed dispositions remain `obsolete_before_publication`,
`retired_after_publication_without_invocation`,
`retired_after_live_boundary`, and `qualified_for_start_review`.

A qualified terminal still grants no study authority. It freezes the reviewed
R and externally anchors its handoff until a separate `start` decision either
declines or enters the study's existing tracked-write prohibition. Retired
branches may import and archive their closeout immediately.

## Risks / Trade-offs

- [Another one-shot identity is consumed by an unexpected defect] -> Preserve
  the exact partial evidence, restore live state, retire r8, and forbid r9 in
  this amendment.
- [Reused test evidence no longer represents the candidate] -> Compare exact
  executable and relevant test input hashes; rerun the registered gate on any
  mismatch.
- [A producer terminal overstates broad isolation] -> Require independent
  verifier output plus separate configuration, inventory, and process
  attestation before qualification.
- [Publication succeeds before the final invocation check] -> Preserve the
  root, restore the baseline, and use only the evidence-supported no-invocation
  or live-boundary retirement.
- [The qualified branch leaves the change active] -> Keep all closeout bytes
  externally hash-anchored and preserve tracked-clean R until the downstream
  study contract releases writes.

## Migration Plan

1. Commit this amendment without creating r8 or changing live configuration.
2. Prove r8 and its paths absent, freeze source S and live baselines, and render
   the repository-local candidate twice.
3. Run candidate-specific checks, exact source replay, applicable registered
   gate evidence, and independent review; create one inert direct-child R and
   record the external go/no-go decision.
4. On no-go, leave the external root absent, import the obsolete closeout, and
   stop. On go, publish the exact root/configuration, compare again, and issue
   at most one CommunicationMod invocation.
5. Preserve the observed root, independently replay it, restore and attest the
   baseline, and select exactly one disposition.
6. For a retired branch, commit/sync/archive. For a qualified branch, keep R
   frozen and hand the external package to a separate study `start` review.

Before publication, rollback leaves live state untouched. After publication,
rollback never removes evidence: it restores exact CommunicationMod bytes,
stops controlled target processes, proves protected-state equality, and
retires r8 on any uncertainty.

## Open Questions

None. Exact S/R commits, candidate hashes, live paths, inventories, and the
branch disposition are generated during implementation rather than guessed in
planning.
