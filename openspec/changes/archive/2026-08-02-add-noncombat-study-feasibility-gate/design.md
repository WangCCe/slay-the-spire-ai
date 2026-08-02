## Context

The active v2 registration fixes 600 attempts and requires at least three deterministic-Current-supported victories. Its frozen historical reference contains 125 complete trajectories, one raw victory, and zero supported victories because the winning trajectory has exact target weight zero. A plug-in supported-victory rate must be about 0.7118% for 600 independent attempts to have an 80% probability of producing at least three successes. The repository has not recorded evidence that the current study meets that planning condition.

The launch process has also become the dominant cost. R1-r8 produced no registered trajectory, and a message-based Git audit finds 55 non-adaptive qualification, handshake, outcome-evidence, or pre-request commits among 146 commits since 2026-07-15. The current runner and verifier plus their two test files grew by roughly 29,865 added lines after the first v2 candidate. These counts are maintenance context, not quality metrics, but they make another launch-only iteration inappropriate before statistical feasibility is checked.

## Goals / Non-Goals

**Goals:**

- Derive the registered attempt budget and supported-victory threshold from the canonical registration rather than duplicating them in code.
- Derive raw and target-supported victory counts from one canonical readiness artifact by exact trajectory identity and rational target-weight numerator.
- Compute deterministic binomial planning probabilities and required-rate thresholds.
- Distinguish historical-reference evidence from source-comparable evidence.
- Produce a small, deterministic, offline report that decides only whether feasibility has been demonstrated.
- Keep replacement qualification and study launch blocked for the current evidence.

**Non-Goals:**

- No game, CommunicationMod, Java, qualification, study, or training process.
- No change to the 600-attempt registration, three-victory threshold, exploration rates, OPE estimator, reward contract, or gameplay policy.
- No confidence interval, causal claim, Bayesian posterior, power guarantee, or assertion that the plug-in rate is the true future rate.
- No independent verifier, self-hashed protocol, external root, run lock, or new launch identity.
- No use of floor reached as a substitute reward or supported victory.

## Decisions

### 1. Keep the analyzer small and read-only

Add one module, `analysis_scripts/noncombat_study_feasibility.py`, with pure arithmetic and parsing helpers plus a CLI. It reads a canonical input manifest, the tracked v2 registration, and one tracked OPE-readiness JSON artifact; it writes deterministic JSON and Markdown only to explicit output paths.

Bind the analyzer, its focused regression, and `reports/noncombat_study_feasibility_*` to `text eol=lf` in `.gitattributes` so canonical hashes and byte-replay checks survive Windows `core.autocrlf=true` checkouts.

The input manifest binds both source files by path, byte size, and SHA-256 and declares whether the evidence is source-comparable or historical-reference-only. The current manifest marks B3-B7 historical-only because its target policy commit predates the current candidate.

Alternative: extend the study runner or standalone verifier. Rejected because feasibility is planning evidence, not launch or terminal evidence, and coupling it to those large modules would increase the same operational surface being audited.

### 2. Derive supported victories rather than accepting a count

The analyzer joins `trajectory_audit.complete_trajectories` to `diagnostics.trajectory_weights` by exact `group_id`, requires one-to-one complete coverage, counts raw victories from the outcome object, and counts a supported victory only when `victory=true` and the exact rational weight numerator is positive. Float `value` fields are diagnostic and never determine support.

Alternative: accept `supported_victories=0` in the input manifest. Rejected because a manually copied count could drift from the frozen readiness artifact or confuse raw and supported outcomes.

### 3. Use transparent plug-in operating characteristics

For observed supported rate `p=x/n`, the analyzer computes
`P[X >= k] = 1 - sum(i=0..k-1, C(N,i) p^i (1-p)^(N-i))`, where `N` and `k` come from the registration. It also finds the rates yielding 50%, 80%, and 90% pass probability by fixed-iteration decimal bisection and renders a fixed sensitivity grid.

The current planning rule requires at least 100 source-comparable reference trajectories and plug-in pass probability at least 0.80. This is a resource-allocation gate, not a statistical confidence claim. Historical-only evidence remains informative but cannot return `demonstrated`.

Alternative: use the one raw B3-B7 win as `p=1/125`. Rejected because that trajectory has target weight zero and cannot satisfy the registered gate. Alternative: infer a posterior or confidence bound. Rejected because choosing a prior or interval rule is unnecessary for the narrow go/no-go and would create a stronger inferential claim than the data supports.

### 4. Keep every downstream authority false

The JSON and Markdown report state `demonstrated` or `not_demonstrated` plus blockers and limitations. Even `demonstrated` only permits a separate reviewed study amendment to consider launch preparation. It does not authorize r9, a run lock, gameplay, OPE interpretation, reward changes, training, or promotion.

## Risks / Trade-offs

- [The plug-in probability understates uncertainty] -> Label it planning-only, render observed counts beside every probability, and never call it power or confidence.
- [Historical B3-B7 source differs from the current candidate] -> Mark it historical-reference-only and fail the comparability prerequisite.
- [A later policy improvement changes the relevant rate] -> Generate a new source-bound reference audit; never relabel the old artifact.
- [The feasibility gate adds another process layer] -> Keep it to one pure offline module, one manifest, focused tests, and ordinary deterministic reports; do not add a verifier protocol.
- [Stopping the study delays outcome evidence] -> The current evidence already gives no basis to expect the expensive run to satisfy its primary gate; an explicit no-go is cheaper and more informative than another launch-only cycle.

## Migration Plan

1. Add red tests for exact supported-victory derivation, zero-support handling, binomial boundaries, provenance mismatch, LF checkout bindings, and all-false authority.
2. Implement the pure analyzer and deterministic renderers.
3. Generate the frozen current audit from B3-B7 and the v2 registration.
4. Update project direction and the active study to record `not_demonstrated` before any replacement qualification.
5. Run focused tests, the registered commit gate, strict OpenSpec validation, archive, commit, and push.

Rollback removes this unarchived change, module, tests, manifest, and reports. It does not alter any registration, historical evidence, live configuration, or process.

## Open Questions

After the current audit, a separate direction decision must choose between improving and re-baselining the gameplay policy, defining a different outcome/reward contract, or proposing a new study design. None is authorized by this change.
