## Context

The v1 registration embeds the complete fixed-tree seed inventory. That was below the 64 MiB artifact ceiling for the consumed `20260806-r1` cohort, but the independently verified `20260808-r2` readiness candidate has 347,575,355 canonical bytes. Embedding it would exceed both the unchanged 64 MiB per-artifact ceiling and the 256 MiB uncompressed terminal-bundle ceiling. The candidate is already published as a 6,020,468-byte deterministic gzip with canonical/stored digests and an independently verified `go` report.

The registration is an all-false source-control document, not empirical execution. It must remain reviewable, pushed, request-bound, and independently verifiable without importing Torch, the native adapter, or gameplay code. Any producer or verifier change is part of the source identity and therefore requires a new readiness run before a new registration can be proposed.

## Goals / Non-Goals

**Goals:**

- Keep new registration and terminal-bundle files within the existing byte ceilings without discarding complete historical-exclusion evidence.
- Bind one compact canonical registration to exact pushed readiness JSON and deterministic-gzip candidate bytes.
- Reconstruct the full freshness and disjointness proof before dependency loading and again in the independent terminal verifier.
- Preserve historical v1 terminal verification against its registered Git source and all execution, retry, authority, and resource semantics.

**Non-Goals:**

- Recompute or change the candidate cohort, selection algorithm, training algorithm, budget, or artifact ceilings.
- Publish a registration, request, approval, authorization, or empirical output in this change.
- Load native/model dependencies, access an environment seed, train, evaluate, run gameplay, or use CommunicationMod.
- Treat the existing r2 readiness result as evidence for the modified control-plane source.

## Decisions

### Add a compact v2 registration, retain v1 for historical evidence

`noncombat-cross-fitted-hierarchical-learning-registration-v2` replaces the top-level `seed_inventory` field with `readiness_evidence`. All other registration fields and the complete eight-field 8x64 schedule remain unchanged. The producer and independent verifier continue to accept v1 only so already-published evidence remains verifiable; the builder for any new successor registration emits v2.

`readiness_evidence` has exact fields:

- `candidate_artifact`: canonical repository `path`, `encoding`, stored `sha256` and `size_bytes`, and decompressed `canonical_sha256` and `canonical_size_bytes`.
- `readiness_report`: canonical repository `path`, file `sha256` and `size_bytes`, and `readiness_identity_sha256`.
- `verification_receipt`: canonical repository `path`, file `sha256` and `size_bytes`, and self-authenticating `verification_receipt_sha256`.
- `publication_commit`: the immutable pushed commit that contains all three exact readiness artifacts.

The candidate and report paths must be sibling files named `candidate_seed_inventory.json.gz` and `readiness_report.json` under one canonical `reports/` directory. The receipt path must be the source-keyed canonical `attempt_verified.json` under the readiness attempt root. The publication commit must contain all three exact blobs, descend from the readiness source commit, and remain an ancestor of the current pushed head. The registration's repository commit must equal the receipt, report, and candidate source commit.

Alternative considered: store the complete registration as gzip. Rejected because the execution bundle currently publishes canonical `registration.json`; decoding it there would still violate the unchanged artifact ceilings and would duplicate the inventory.

Alternative considered: raise the artifact limits. Rejected because that changes the registered experiment contract and resource budget to solve a control-document representation problem.

### Keep registration identity compact and semantic

Request, approval, authorization, execution identity, and terminal documents continue to bind the SHA-256 of canonical compact registration JSON. Candidate/report digests are fields inside that canonical document, so changing either evidence binding changes the registration digest without making compression metadata part of an implicit side channel.

The registration written into the terminal bundle remains canonical JSON and contains no expanded inventory. The external readiness artifacts are immutable source inputs, like the registered source tree and native provenance; they are not copied into or charged against empirical output resources.

### Verify exact pushed evidence before dependency loading

For v2, producer preflight first proves that `publication_commit` is an ancestor of `origin/master`, then reads the report and candidate from exact `<publication_commit>:<path>` objects rather than accepting the same blob at an arbitrary or movable path. It then, in fixed order:

1. checks Git object size before reading each blob, then checks stored path, size, and SHA-256 bindings;
2. parses the canonical independent-verification receipt, verifies its self-digest, and requires its publication bindings and verified `go` summary to match the report and candidate;
3. parses canonical readiness JSON and requires the exact all-false authority map, `go`, proposal eligibility, source commit, readiness identity, and candidate binding, including exact JSON booleans for authority and eligibility and exact JSON integers for counts;
4. bounds candidate gzip to 64 MiB stored and 512 MiB canonical, rejects extra or nondeterministic members by byte-identical deterministic recompression, and parses strict canonical JSON;
5. validates the complete historical inventory, canonical 512-seed selection, consumed 512-seed cohort and its exact `consumed_registration` source role, zero collisions, source commit, and all-false authority;
6. reconstructs the registration's eight chunks and requires byte-identical schedule identity;
7. requires every registration source-inventory row to equal the blob at `<readiness-source-commit>:<path>` and requires readiness's bound control plane, terminal verifier, seed helper, and successor contract rows to match those exact source identities.

Only after these checks, the existing current-worktree/source-inventory equality, runtime/native/isolation checks, exact pushed registration/authorization checks, and clean-worktree checks pass may dependency loading begin. Consequently an r2 report bound to the pre-change control plane cannot validate a registration executed by the post-change control plane. `inspect-registration` and `render-request` perform the same readiness-evidence verification for v2, while pure structural validation remains side-effect free for internal identity checks.

Alternative considered: trust only the readiness report digest. Rejected because source preflight must detect missing, replaced, malformed, or schedule-inconsistent candidate bytes before seed access.

### Preserve independent verification

The terminal verifier implements its own standard-library v2 parsing and candidate checks and reads evidence from exact publication-commit Git paths using its existing repository-root boundary. It does not import the producer, readiness auditor, Torch, runtime, or native module. Its registration validation fails closed if the external evidence is unavailable or differs, even when the producer's persisted source-preflight report says it passed.

For both v1 and v2, the independent verifier compares the registered source inventory with blobs from the registration's `repository_commit`, not with mutable current-worktree bytes. Producer execution still separately requires the current tracked worktree to reproduce that inventory before dependency loading. This preserves historical v1 verification under its frozen source while preventing v1 from becoming a new-registration path.

The producer source inventory and independent verifier declarations are updated together. A subsequent readiness audit must bind both changed source files and any changed seed-inventory helper before registration eligibility can be regained.

## Risks / Trade-offs

- [Risk] v2 terminal verification depends on retained pushed readiness artifacts outside the terminal directory. -> Mitigation: bind an immutable publication commit, canonical paths, and stored/canonical digests; require the commit to remain reachable from the pushed head; and read exact commit-path blobs.
- [Risk] bounded decompression and full inventory validation remain CPU- and memory-heavy. -> Mitigation: perform them once per source-only boundary, keep the existing 64 MiB/512 MiB ceilings, avoid deep copies where practical, and prove actual scale again in readiness.
- [Risk] producer and verifier validation logic can drift. -> Mitigation: use independent implementations plus shared golden and adversarial fixtures that require identical accept/reject outcomes.
- [Risk] accepting v1 could accidentally permit a new embedded registration. -> Mitigation: retain v1 validation only for historical/existing evidence, replay its source from the registered commit, and expose a separate v2-only new-registration builder.
- [Risk] changing the control plane invalidates r2 as execution-source evidence. -> Mitigation: make a new pushed source identity and run a separately preregistered one-shot readiness audit before any registration proposal.

## Migration Plan

1. Add RED producer and independent-verifier tests for v2, exact-path Git binding, bounded deterministic gzip, schedule reconstruction, and v1 compatibility.
2. Implement compact v2 structural validation, source-only readiness-evidence verification, and a v2-only registration builder.
3. Run focused tests, source-preservation tests, strict OpenSpec validation, and the repository's bounded commit gate.
4. Commit and push the control-plane change without publishing a registration.
5. Create a separate exact readiness change for the new source, run it once, and stop on any no-go.
6. Only after a verified new `go`, publish a separate compact registration proposal. Execution request and explicit human approval remain later boundaries.

Rollback before readiness is a normal revert. Once a new readiness source is claimed, a defect consumes that identity and requires a new fix and source commit; it is never patched and retried under the same identity.

## Open Questions

None. Exact r3 paths, audit id, source commit, and candidate digests belong to the later readiness change and must not be guessed or hard-coded here.
