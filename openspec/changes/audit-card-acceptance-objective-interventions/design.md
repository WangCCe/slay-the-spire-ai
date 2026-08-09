## Context

The sealed cross-fitted r2 run retains five named shared-parameter gradient
components and the independently retained full gradient for each of eight
chunks. The published card-acceptance audit exactly reconstructed those
vectors and found nonzero family-policy and conditional-policy components in
every chunk. Their cosine was negative in chunks 1 and 4 and positive in the
other six chunks. This is evidence of limited component conflict, not evidence
that changing the objective improves a policy.

The current ranker shares parameters across action-family and within-family
scores, and the family logit is the maximum candidate score. A score change can
therefore affect acceptance and conditional choice together. The next step
must establish whether parameter-free interventions can be represented and
audited before proposing another architecture or empirical successor.

## Goals / Non-Goals

**Goals:**

- Rebind the exact published audit and sealed r2 gradient evidence without
  loading model, runtime, native, simulator, seed, or gameplay state.
- Compare three fixed shared-gradient compositions with no fitted coefficient.
- Prove synthetic invariants for a genuinely independent acceptance coordinate.
- Report exact per-chunk and fixed-window geometry, degenerate cases, and a
  bounded feasibility verdict without ranking candidates by policy quality.
- Produce deterministic compact reports with no raw vector disclosure and no
  downstream authority.

**Non-Goals:**

- Select, implement in training, or recommend one intervention as a successor.
- Infer loss reduction, card value, return, policy quality, causality, or live
  impact from parameter-space dots or norms.
- Fit a coefficient, architecture, baseline, reward, model, or threshold.
- Load Torch, a checkpoint, native code, a simulator, seed data, game state, or
  CommunicationMod; train, replay, evaluate, run OPE, qualify, or promote.

## Decisions

### Use the published audit as the trust root and reopen only its bound evidence

The audit will require the canonical 20260809 JSON and Markdown digests,
schema, verdict, execution counts, exact all-false authority, source identity,
terminal-verifier result, and complete input bindings. It will then reopen only
the named terminal, manifest, checkpoints, and eight gzip chunk artifacts
under the inactive execution lease. It will independently reverify containment,
canonical encodings, digests, sizes, vector dtype/shape/order, chunk order, and
the full-gradient reconstruction while binding every reused source helper.
The audit is the single lease owner and invokes the source-bound independent
verifier lease guard once. That guard validates the bounded regular lease,
owner liveness, complete execution identity, and stable path before yielding
the parsed identity to the verifier contents and the remaining analysis; the
audit does not call the outer lease-acquiring wrapper and therefore cannot
attempt a second non-reentrant lock.

Alternative: consume only the compact gradient geometry already published.
Rejected because norms and dots cannot reconstruct transformed vectors or
independently prove the intervention algebra.

### Compare exactly three parameter-free gradient compositions

For each chunk let `F` be `card_reward_family_policy`, `C` be
`card_reward_conditional_policy`, and
`R = other_policy + family_entropy_regularizer +
conditional_entropy_regularizer`. The recorded full gradient is
`G = F + C + R` before the already registered clipping rule.

The fixed candidates are:

1. `recorded`: `G_recorded = F + C + R`.
2. `family_policy_ablated`: `G_ablated = C + R`.
3. `conditional_conflict_guarded`: when `dot(F, C) < 0` and `||C|| > 0`,
   `F_guarded = F - dot(F,C) / ||C||^2 * C`; otherwise
   `F_guarded = F`. Then `G_guarded = F_guarded + C + R`.

The ablation is a structural control, not a coefficient search. The guard is
the unique Euclidean projection that removes only the component of `F`
opposing `C`; its multiplier is derived from the vectors rather than tuned.
Every candidate reports raw and frozen-rule clipped norms, displacement from
the recorded gradient, retained family-policy norm, and dots/cosines against
`F`, `C`, and `G`. The guard must be byte-for-byte unchanged in non-conflict
chunks and must satisfy `dot(F_guarded, C) = 0` within fixed arithmetic
tolerance in conflict chunks. `dot(G_guarded, C)` remains descriptive because
`R` may itself conflict with `C`.

Alternative: search a family-loss weight or compare a coefficient grid.
Rejected because the same observed cohort would then select a hyperparameter.
Alternative: require the guarded full gradient to align with `C`. Rejected
because that would silently project unrelated policy and entropy components.

### Prove an independent acceptance coordinate only with synthetic fixtures

A pure-Python synthetic distribution will use one acceptance-family logit
separate from within-`take` conditional logits. In a registered smooth fixture
with at least two valid families, interior family mass, and a nonzero finite
translation that produces distinct representable masses, translating the
acceptance logit must change family mass while preserving every conditional
probability, ordering, entropy, and margin. In a registered smooth fixture, a
fixed nonzero zero-sum conditional perturbation that produces a representably
distinct conditional distribution must change that distribution while
preserving the acceptance logit and family mass. One-family fallback has family mass one and an inactive
acceptance coordinate; translating that inactive coordinate changes nothing.
Extreme finite values and ties test finiteness and identity preservation but
do not require a representably distinct mass or unique derivative. Invalid
candidates and finite-difference agreement at smooth nontied points are also
covered.

This establishes a representational invariant but does not claim that the
current shared ranker implements that coordinate. The report will contrast it
with a max-pooled synthetic control where perturbing the maximum take score can
change both family and conditional distributions.

Alternative: add a real acceptance head to the ranker. Rejected at this stage
because that is an architecture and training proposal, not a source-only audit.

### Use fixed feasibility predicates rather than outcome or magnitude ranking

Identity or reconstruction failure aborts publication. After all synthetic and
arithmetic gates pass:

1. If any chunk has zero conditional-policy norm, leave that chunk's guarded
   family component unchanged, mark it unsupported, continue deterministic
   summaries for valid chunks, and publish
   `insufficient_conditional_gradient_support`.
2. If every `dot(F,C)` is nonnegative, publish
   `no_recorded_family_conditional_conflict`.
3. If at least one chunk conflicts and every conflicting chunk is projected to
   zero while every non-conflicting chunk is unchanged, publish
   `bounded_conditional_conflict_guard_feasible`.

The verdict reports algebraic feasibility only. It selects no candidate and
grants no authority for an objective, architecture, coefficient, experiment,
or policy. Exact signs determine conflict; a fixed tolerance is used only to
verify reconstructed floating-point identities, never to reclassify a sign.

### Publish compact deterministic evidence after a pushed source boundary

The implementation will use standard-library JSON, gzip, hashing, base64, and
array operations. Two fresh isolated processes with separate staging roots
must produce byte-identical canonical JSON and Markdown. Canonical JSON must
not exceed 1,048,576 bytes and Markdown must not exceed 65,536 bytes. Reports
contain component summaries and transformed geometry, not raw vectors or
unrestricted decision rows. Every authority field remains false.

The focused tests run first. The requalified `commit` gate runs once at the
source boundary, and the unchanged `full` gate runs once at phase close; an
infrastructure failure is recorded separately from test evidence and is not
blindly retried. Source is committed and pushed before either isolated
publication reads sealed evidence.

## Risks / Trade-offs

- [Risk] Projection geometry is mistaken for policy improvement. -> Name the
  result a feasibility audit, report all residual components, and keep policy-
  quality, causal, evaluation, training, and promotion authority false.
- [Risk] Euclidean projection depends on parameterization. -> State that the
  guard is specific to the retained shared-parameter coordinates and compare
  no architectures or optimizers.
- [Risk] Removing family-policy pressure also changes useful acceptance
  learning. -> Treat ablation only as a structural control and publish no
  preferred intervention.
- [Risk] The same cohort influenced the fixed candidate set. -> Disclose the
  post-hoc design, prohibit magnitude thresholds and coefficient search, and
  require a separate preregistered successor before empirical use.
- [Risk] A max-pooled score boundary is nondifferentiable at ties. -> Preserve
  complete tie identities, test one-sided controls, and make no unique-gradient
  claim at a tied maximum.

## Migration Plan

1. Commit and push this complete planning boundary.
2. Add RED identity, vector, intervention, synthetic, verdict, determinism,
   malformed-input, import-isolation, and authority regressions.
3. Implement the source-only audit and pass focused tests.
4. Run the requalified commit gate once; commit and push source before opening
   sealed evidence for publication.
5. Run two isolated publications, compare bytes, and stage the canonical pair.
6. Run the unchanged full gate once, strict OpenSpec validation, diff checks,
   and independent review; update project direction, sync, archive, commit, and
   push.

Rollback removes only this audit's source, tests, reports, specification,
archive, and direction entry. It does not modify the sealed run, prior audits,
policy, checkpoints, test tiers, or live configuration.

## Open Questions

None.
