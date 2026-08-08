# Noncombat Cross-Fitted Empirical Successor Readiness Specification

## Purpose

Define the source-only, one-shot readiness decision that must close before any
new cross-fitted empirical successor registration can be proposed.

## Requirements

### Requirement: Readiness binds exact pushed source and immutable evidence
The readiness audit SHALL bind one pushed implementation commit, require local
`HEAD` and `origin/master` to equal that commit, require a clean tracked
worktree, and hash every auditor, verifier, consumed-terminal, bottleneck,
repair-closeout, historical-throughput, and contract input used by the
decision. The readiness contract SHALL be bound through the canonical main spec
at
`openspec/specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md`
and SHALL NOT depend on an active or archived change path. The audit SHALL
reject missing, mutable, rehashed, or source-inconsistent inputs before any
rehearsal or candidate publication.

#### Scenario: All source and evidence bindings match
- **WHEN** every required Git blob and immutable artifact matches its registered path, size, and SHA-256 under one pushed commit, including the canonical readiness main spec
- **THEN** the audit may continue source-only and grants no registration, native, seed, fitting, training, or evaluation authority

#### Scenario: A lifecycle-dependent readiness spec path is used
- **WHEN** source binding names the retired active-change path, an archive path, or any readiness contract path other than the canonical main spec
- **THEN** the audit emits typed `no_go_source_binding` before rehearsal and does not substitute a nearby spec

#### Scenario: One bound input drifts
- **WHEN** `HEAD`, `origin/master`, tracked status, a source blob, consumed terminal artifact, closeout, contract, or historical throughput input differs
- **THEN** the claimed attempt emits typed `no_go_source_binding` before rehearsal, installs no final publication, and does not substitute a nearby file or commit

### Requirement: The candidate cohort is canonical and fully fresh
The audit SHALL reconstruct the complete historical seed inventory from the
bound Git tree and publish that canonical inventory. It SHALL derive exactly
the first 512 ascending nonnegative seeds absent from that inventory and all
reserved ranges. It SHALL extract the complete 512-seed schedule from the
consumed cross-fitted registration and require an empty intersection, including
the 500 scheduled positions that were never debited. The consumed schedule
SHALL contain exactly `canonical_search_start`, `chunk_count`, `chunks`,
`episodes_per_chunk`, `inventory_sha256`, `seeds`, `seeds_sha256`, and
`selection_schema_version`. Its canonical search start SHALL be `0`, its
inventory SHA-256 SHALL be
`435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174`, and its
selection schema SHALL be
`noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1`. Producer
validation and independent reconstruction SHALL use shallow or streamed
representations for the actual-scale inventory and SHALL NOT deep-copy or
concurrently materialize multiple complete canonical inventories.

#### Scenario: A fully disjoint candidate schedule exists
- **WHEN** the rebuilt inventory is canonical, its independent replay is byte-identical, the consumed schedule has the exact eight fields, canonical search start `0`, inventory SHA-256 `435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174`, and selection schema `noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1`, the candidate contains 512 ordered unique seeds, and its intersection with the consumed 512-seed schedule is empty
- **THEN** the audit records the candidate inventory/schedule digests and continues without treating any seed integer as an environment access

#### Scenario: Consumed schedule provenance drifts
- **WHEN** the consumed schedule omits or adds a field, changes canonical search start, changes inventory SHA-256, changes selection schema version, or supplies malformed provenance
- **THEN** readiness is `no_go_source_binding` before candidate inventory construction or rehearsal

#### Scenario: Only debited seeds are excluded
- **WHEN** any candidate seed belongs to the consumed registration even if that position has no access-journal debit
- **THEN** readiness is `no_go_cohort_not_fresh` and the schedule cannot be repaired by dropping individual collisions in place

#### Scenario: Candidate seed data is used empirically
- **WHEN** the change attempts to construct an environment, append an empirical access journal, fit, train, evaluate, or inspect an outcome for a candidate seed
- **THEN** the operation is forbidden and no readiness report is publishable

### Requirement: Actual-scale rehearsal remains source-only and bounded
The audit SHALL create an ephemeral actual-registration-scale context in a
caller-supplied isolated scratch root, validate the complete registration once,
record one exact 64-position synthetic control chunk, and close and independently
verify one typed synthetic terminal bundle. Torch and native adapter imports,
dependency loading, environment construction, runtime fitting, checkpoint
loading, and CommunicationMod SHALL remain blocked. Context/setup, chunk
control, and terminal closeout SHALL each have an immutable 300-second ceiling.
The rehearsal child SHALL run in a separately terminable process tree; every
timeout or malformed event path SHALL terminate descendants and confirm child
exit before returning a typed result.

#### Scenario: The actual-scale control path passes
- **WHEN** one context validation owns immutable values, 64 synthetic debit/terminal coordinates preserve all journal and resource checks without increasing the validation count, terminal closeout verifies, and all three stages finish within their ceilings
- **THEN** the audit records stage pass witnesses and excludes the scratch tree from published candidate and readiness inventories

#### Scenario: Registration-size work recurs per position
- **WHEN** complete registration validation, digesting, or source-inventory copying grows with the 64-position count or a nested terminal helper
- **THEN** readiness is `no_go_control_plane_scaling` even if the rehearsal finishes before the watchdog

#### Scenario: A blocked import or stage ceiling fires
- **WHEN** Torch, native, runtime fitting, environment construction, or a stage beyond 300 seconds is observed
- **THEN** the child stops, readiness is typed `no_go_rehearsal_boundary`, and the audit is not retried with a wider ceiling

### Requirement: Readiness uses one fixed conservative budget equation
The decision SHALL reserve exactly 3,600 seconds of the unchanged
14,400-second ceiling for source-control overhead and contingency. It SHALL
bind the comparable historical workload at exactly 2,165.452 charged seconds,
require its bound source field to equal the exact raw decimal
`2165.4520000000193` by parsing it as an exact decimal before any binary-float
conversion and rejecting a JSON string representation, apply an immutable
multiplier of 3.0, and compute the projected total as 10,096.356 seconds with
4,303.644 seconds of margin. It SHALL NOT infer or tune the budget from observed
rehearsal timings.

#### Scenario: The fixed budget inputs and arithmetic pass
- **WHEN** the bound historical artifact proves 512 episodes, eight updates, eight checkpoints, no evaluation, the exact raw charge `2165.4520000000193`, and exact arithmetic from the pre-registered `2165.452` term reproduces the fixed projection and positive margin
- **THEN** the budget gate passes without changing episode count, wall-time ceiling, estimator, objective, or training contract

#### Scenario: A budget term changes
- **WHEN** the historical binding or raw charge, 3.0 multiplier, 3,600-second reservation, 14,400-second ceiling, decimal projection, or margin differs
- **THEN** readiness is `no_go_budget_binding` rather than recalculating a more favorable threshold

### Requirement: Independent verification publishes one typed decision
The auditor SHALL publish the canonical full inventory as deterministic gzip
with a 64 MiB stored ceiling and 512 MiB bounded canonical ceiling, plus JSON
and Markdown artifacts. It SHALL first write the three artifacts to a hidden
staging sibling and SHALL atomically install the final directory only after a
separate standard-library verifier succeeds. The verifier imports neither the
auditor nor Torch/native/runtime modules and SHALL stream Git blobs, expected
deterministic gzip, and staged-file comparison while reconstructing
source/evidence bindings, inventory/schedule arithmetic, full consumed-cohort
disjointness, rehearsal witnesses, budget arithmetic, decision precedence,
and JSON/Markdown agreement. It SHALL run in a separately terminable process
tree with an immutable 900-second ceiling. The decision SHALL be `go` only when
every gate passes; otherwise the first fixed-precedence failure SHALL be one
typed `no_go` reason in the durable attempt journal. No alternate callable API
SHALL write validated artifacts directly to a final publication directory.
After verification, the runner SHALL stream-copy the staged files into a
cryptographically random hidden sealed sibling, require every copied and sealed
SHA-256 and size to match the pre-verifier bindings recorded in the verified
receipt, retire the predictable staging tree, and atomically install only that
sealed snapshot.

#### Scenario: Every readiness gate passes
- **WHEN** exact source/evidence, full-cohort freshness, deterministic gzip and bounded decompression, bounded actual-scale rehearsal, fixed budget, artifact limits, and independent verification all pass
- **THEN** the verified staging directory is atomically installed, its report sets only `empirical_successor_registration_proposal_eligible=true`, and every empirical or downstream authority remains false

#### Scenario: Independent verification fails or times out
- **WHEN** the verifier returns nonzero, exceeds 900 seconds, or emits a summary that differs from the staged artifacts
- **THEN** the complete process tree is terminated, no final publication directory is installed, and the attempt closes as typed `no_go_artifact_binding` even when verifier diagnostics quote an earlier gate token

#### Scenario: A readiness gate fails before publication
- **WHEN** the audit safely observes a failure while traversing fixed order `source_binding`, `cohort_not_fresh`, `rehearsal_boundary`, `control_plane_scaling`, `budget_binding`, `artifact_binding`
- **THEN** it stops at that first observed gate, honors only a literal leading structured `no_go_<gate>` marker in the raw exception or canonical scratch-verifier `error` field and otherwise uses the currently executing gate, writes exactly one typed terminal reason, installs no final publication, and does not inspect or claim downstream gates whose inputs are no longer trustworthy

#### Scenario: Scratch verifier emits a non-scaling gate marker
- **WHEN** canonical scratch-verifier stderr has a literal source, cohort, budget, or artifact gate marker rather than `no_go_control_plane_scaling`
- **THEN** the audit retains `no_go_rehearsal_boundary` because scratch verification may override that stage only with the scaling marker

#### Scenario: Bound evidence is malformed
- **WHEN** a bound registration, terminal, manifest, historical throughput, or contract input cannot be parsed or fails its required shape
- **THEN** readiness closes as `no_go_source_binding` before candidate inventory construction begins, including when the consumed schedule lacks exact fields, integer seeds in either the flat list or any chunk, eight exact chunks, or its required digest

#### Scenario: Staging changes after independent verification
- **WHEN** any staged file's SHA-256 or size differs while the verified snapshot is being sealed
- **THEN** the exact runner-owned random sealed path is removed, including across the sealing helper-return boundary, no final publication is installed, and the attempt closes as `no_go_artifact_binding`

#### Scenario: A readiness report claims execution authority
- **WHEN** JSON or Markdown grants registration, native loading, seed access, model loading, fitting, training, evaluation, OPE, gameplay, CommunicationMod, formal RL, qualification, or promotion
- **THEN** independent verification rejects the report regardless of a `go` label

### Requirement: Readiness is single-publication and non-retryable
Before running any gate, the audit SHALL atomically claim one durable attempt
directory keyed only by the pushed source commit and write a canonical started
receipt without exposing an empty canonical directory. The runner SHALL recover
an interruption across the claim helper boundary only when the installed
started receipt exactly matches its own source, audit id, and paths. One pushed
source identity SHALL produce at most one canonical readiness attempt regardless
of changed paths or audit id. A failure after the claim and before completed
installation SHALL write a typed all-false terminal receipt; independently
verified staging SHALL write a verified receipt before atomic installation. A
typed `no_go`, child timeout, corrupt inventory, or failed independent
verification SHALL NOT be rerun with changed paths, thresholds, inputs, cohort,
or source under the same identity. A verified `go` SHALL make only a separate
empirical registration proposal eligible for review.

#### Scenario: Readiness returns go
- **WHEN** the canonical report is independently verified as `go`
- **THEN** a later OpenSpec change may propose the exact fresh registration while this change still grants no execution request or approval

#### Scenario: Readiness returns no-go or fails publication
- **WHEN** the claimed attempt emits typed `no_go` or cannot install an independently verified final publication
- **THEN** the attempt journal preserves the terminal all-false receipt, the identity is consumed for readiness, and any changed attempt requires a new proposal and pushed source commit

#### Scenario: The same source commit is invoked with different paths
- **WHEN** any started, terminal, or verified attempt directory already exists for the requested source commit
- **THEN** the new invocation is rejected before source validation, rehearsal, staging, or publication

#### Scenario: Interruption follows the atomic final installation
- **WHEN** interruption is observed after the verified staging rename completed, the exact verified receipt matches the installed final artifacts, and the staging directory is absent
- **THEN** the installed `go` remains the sole durable outcome, no terminal `no_go` receipt is written, and non-interruption exceptions may return the recovered verified result

#### Scenario: Final installation or installed recovery fails
- **WHEN** the final rename fails before installation, or an appearing output entry cannot be validated against the exact verified receipt
- **THEN** the exact sealed snapshot is removed when still present and the attempt writes terminal `no_go_artifact_binding` rather than remaining started/verified without a terminal outcome

### Requirement: Corrected-source readiness r2 is one exact source-only attempt
The readiness runner SHALL use audit id
`noncombat-cross-fitted-empirical-successor-readiness-20260808-r2`, output path
`reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2`, and
scratch path `.source_only_readiness_scratch_20260808_r2`. Its source commit
SHALL be the pushed, tracked-clean commit containing the final strictly
validated execution contract and synced main spec. Immediately before
invocation, the source-keyed attempt directory, output path, scratch path, and
the exact derived staging sibling
`reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r2.<source-commit>.staging`
SHALL all be absent, every canonical bound path SHALL exist at that commit, and
the terminal `r1` identity and receipts SHALL remain unchanged. The existing
auditor SHALL be invoked at most once with those exact values, the absolute
auditor script path, the repository-root cwd, and unchanged internal ceilings.
When no canonical publication exists after true process exit, the exact
standard-library canonical receipt-review algorithm in the execution design
SHALL independently verify the terminal outcome without importing project
modules. Every empirical and downstream authority SHALL remain false for every
outcome.

#### Scenario: Final preflight passes
- **WHEN** local `HEAD` and `origin/master` equal the final plan commit, the tracked worktree is clean, all bound paths match, the new source has no attempt directory, output, scratch, or exact derived staging sibling, and the consumed `r1` evidence remains intact
- **THEN** the runner may invoke the exact `r2` source-only auditor command once and only once

#### Scenario: Any pre-start identity or path check fails
- **WHEN** source identity, tracked status, a bound path, old receipt, attempt path, output path, scratch path, derived staging path, absolute script path, cwd, command argument, or ceiling differs from the registered value
- **THEN** the runner stops before invoking the auditor and does not choose another commit, id, path, limit, or command

#### Scenario: The attempt is claimed
- **WHEN** the source-keyed `attempt_started.json` is atomically installed
- **THEN** that source identity is permanently consumed regardless of exit, timeout, exception, no-go, verifier failure, or publication result and SHALL NOT be retried or resumed

#### Scenario: The auditor process exits
- **WHEN** the true auditor process tree has exited and its lease is no longer held
- **THEN** the standalone publication verifier checks an installed publication, or the preregistered exact standard-library receipt-review algorithm checks canonical started/terminal closure, identity linkage, receipt hashes, all-false maps, and output/scratch/staging absence, before any project-direction claim is made

#### Scenario: Readiness returns go
- **WHEN** an independently verified canonical report has decision `go`
- **THEN** only a later empirical-successor registration proposal becomes eligible while registration, native, seed, model, fitting, training, evaluation, OPE, gameplay, CommunicationMod, formal-RL, qualification, and promotion authorities remain false

#### Scenario: Readiness returns no-go or fails publication
- **WHEN** the attempt closes with a typed no-go, exception, timeout, or absent canonical publication
- **THEN** terminal receipts and all-false authority are preserved, no downstream proposal is eligible, and no same-source repair or retry is permitted

#### Scenario: An empirical operation is requested
- **WHEN** any code path attempts native or model loading, environment construction, empirical outcome access, fitting, training, evaluation, OPE, gameplay, CommunicationMod, qualification, or promotion
- **THEN** the operation is forbidden and the attempt cannot yield readiness or downstream authority

### Requirement: Readiness-derived artifacts are not historical seed evidence
The readiness producer and standalone verifier SHALL reconstruct historical seed evidence from eligible structured artifacts in the exact bound Git tree while excluding every canonical path that begins with `reports/noncombat_cross_fitted_empirical_successor_readiness_` or `reports/.noncombat_cross_fitted_empirical_successor_readiness_`. Exclusion SHALL occur before format selection, Git blob loading, decompression, JSON parsing, or recursive seed extraction. The two implementations SHALL independently reproduce the same included source bindings without importing one another. Existing handling for every other report path, supported format, malformed artifact, reserved range, and unsupported seed-like format SHALL remain unchanged.

#### Scenario: Prior readiness evidence is tracked
- **WHEN** the bound Git tree contains readiness attempt receipts, final publications, closeouts, predictable staging, or random sealed siblings under either excluded namespace
- **THEN** neither producer nor verifier loads those blobs or treats their candidate schedules, historical rows, or metadata as seed evidence

#### Scenario: Legitimate empirical evidence is tracked
- **WHEN** a supported structured report outside both excluded namespaces contains seed-valued fields
- **THEN** producer and verifier retain the report in the historical inventory under the existing canonical parsing and source-binding rules

#### Scenario: A lookalike path is tracked
- **WHEN** a report path contains readiness words or a candidate inventory basename but does not begin with either exact excluded namespace
- **THEN** the path is not excluded and existing supported-format or fail-closed unsupported-format handling applies

#### Scenario: Producer and verifier selection differs
- **WHEN** either implementation includes a path the other excludes or produces different included source bindings for the same bound Git tree
- **THEN** independent verification fails closed before publication and grants no proposal or downstream authority

### Requirement: Runner-owned staging is retired before terminal closure
The readiness runner SHALL record ownership only after it exclusively creates the exact source/output-derived staging directory. On every pre-install failure after ownership is established, including candidate canonical or stored ceiling failure, report construction failure, and independent-verifier failure or timeout, it SHALL remove only that exact runner-owned staging tree and prove absence before writing the terminal receipt. A pre-existing, replaced, mismatched, or otherwise unowned path SHALL NOT be deleted. Existing final-output, sealed-snapshot, process-tree, typed-decision, all-false-authority, and no-retry rules SHALL remain unchanged.

#### Scenario: Candidate serialization exceeds a ceiling
- **WHEN** streaming candidate publication crosses the unchanged stored or canonical byte ceiling after the runner created staging
- **THEN** the exact owned staging tree is absent before one typed `no_go_artifact_binding` terminal receipt is written, so no-publication receipt review can verify closure

#### Scenario: Independent verification fails
- **WHEN** the standalone verifier returns nonzero, times out, or rejects staged publication bytes
- **THEN** its process tree is confirmed absent, the exact owned staging tree is removed, no final output is installed, and the attempt terminalizes once as `no_go_artifact_binding`

#### Scenario: Staging existed before runner ownership
- **WHEN** the exact derived staging path exists before the invocation successfully creates it
- **THEN** readiness fails source binding without deleting or modifying that path and does not claim staging ownership

#### Scenario: Owned staging cleanup fails
- **WHEN** bounded removal of exact owned staging raises or absence cannot be proven
- **THEN** the runner writes one durable typed `no_go_artifact_binding` terminal receipt with cleanup diagnostics, leaves terminal verification and every downstream authority false, preserves any residue for review, and does not retry or delete through another path

#### Scenario: Publication succeeds
- **WHEN** all gates and independent verification pass and the verified staging snapshot is sealed and installed
- **THEN** existing verified-receipt, staging-retirement, sealed-copy, and atomic-output semantics remain unchanged

### Requirement: Compact-source readiness r3 is one exact source-only attempt
The readiness runner SHALL use audit id
`noncombat-cross-fitted-empirical-successor-readiness-20260808-r3`, output path
`reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r3`, and
scratch path `.source_only_readiness_scratch_20260808_r3`. Its source commit
SHALL be the pushed, tracked-clean final planning commit that descends from and
preserves compact implementation commit
`08d2c74e6e923380f32bc8aa5aa75c8c337f27d7`, contains the complete synced r3
contract, and has not been claimed by any readiness attempt. Immediately before
authorization and invocation, the source-keyed attempt directory, output path,
scratch path, and exact derived staging sibling
`reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r3.<source-commit>.staging`
SHALL be absent, all canonical bound paths SHALL exist at that commit, and r1
and r2 evidence SHALL remain unchanged. The existing auditor SHALL be invoked
at most once with those exact values, its absolute script path, the repository-
root cwd, and unchanged internal ceilings, and only after an exact human
authorization names the final source and complete execution boundary. When no
canonical publication exists after true process exit, the canonical receipt-
review algorithm below SHALL independently verify the terminal outcome without
importing project modules. Every empirical and downstream authority SHALL
remain false for every outcome.

The final preclaim source preflight SHALL require
`git diff --name-status --no-renames 08d2c74e6e923380f32bc8aa5aa75c8c337f27d7 <source-commit>`
to contain exactly these status/path rows and no others:

- `D openspec/changes/support-compressed-cross-fitted-registration/.openspec.yaml`
- `D openspec/changes/support-compressed-cross-fitted-registration/design.md`
- `D openspec/changes/support-compressed-cross-fitted-registration/proposal.md`
- `D openspec/changes/support-compressed-cross-fitted-registration/specs/noncombat-cross-fitted-hierarchical-learning-successor/spec.md`
- `D openspec/changes/support-compressed-cross-fitted-registration/tasks.md`
- `A openspec/changes/archive/2026-08-08-support-compressed-cross-fitted-registration/.openspec.yaml`
- `A openspec/changes/archive/2026-08-08-support-compressed-cross-fitted-registration/design.md`
- `A openspec/changes/archive/2026-08-08-support-compressed-cross-fitted-registration/proposal.md`
- `A openspec/changes/archive/2026-08-08-support-compressed-cross-fitted-registration/specs/noncombat-cross-fitted-hierarchical-learning-successor/spec.md`
- `A openspec/changes/archive/2026-08-08-support-compressed-cross-fitted-registration/tasks.md`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r3/.openspec.yaml`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r3/design.md`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r3/proposal.md`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r3/specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r3/tasks.md`
- `M openspec/specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md`

The same preflight SHALL require the r1 attempt directory to contain exactly
its two listed files, the r2 attempt directory exactly its two listed files,
the r2 publication exactly its three listed files, and the closeout to remain a
regular file, with these exact decimal byte sizes and SHA-256 digests:

- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/863ae5a4046df110e4f9028bb3c56d556a7c6a43/attempt_started.json`: `1386`, `5af300236aa7c903e928a973e21b964419af20fc74a142a3b250f9905177fb7c`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/863ae5a4046df110e4f9028bb3c56d556a7c6a43/attempt_terminal.json`: `1279`, `8d5650b24ec6c808ef068dfb0c5dff3166a3c6d4f5c793e00cc26ddbf9bd805b`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/522185d06ddf48cb1be095c16efacaad299a0197/attempt_started.json`: `1386`, `93416149a7d65248d75b0437ab6e4dfb2ad13ebdef51356b2b4585ada3126d7e`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/522185d06ddf48cb1be095c16efacaad299a0197/attempt_verified.json`: `1517`, `82056cbd26eba2e66afa7dabdfe57b7c1b89fff55ebe67168ebd094143d151f0`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2/candidate_seed_inventory.json.gz`: `6020468`, `7b5b2d9da9fe0b0cdb2dc9a298b395783171dbf9ecf46b941af92ba809e3695d`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2/readiness_report.json`: `6816`, `103521948dfa4e67b1fb8d40ca8e3f17ee80921745f905225c1a7169756d0eed`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2/readiness_report.md`: `1621`, `3f16062f5800eff186f82b1cbb6eefd8618c689a935a1db4cd0cfa2c08463688`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2_closeout.json`: `3967`, `3ec9bd64f97c825d1e30a44e236563814b099d266eeea9d11f55dc2eed2153d8`

Exact human authorization SHALL name the final 40-character source commit;
interpreter `D:\anaconda\envs\stsai\python.exe`; isolated `-I` mode; absolute
auditor script, repository root, and cwd
`D:\PycharmProjects\slay-the-spire-ai`; the complete command; audit id; output,
scratch, source-keyed attempt, and derived staging paths; sealed sibling pattern
`.noncombat_cross_fitted_empirical_successor_readiness_20260808_r3.<64-lowercase-hex>.sealed`;
outer wait `7200` seconds; stage ceiling `300.000` seconds; independent verifier
ceiling `900` seconds; empirical ceiling `14400.000` seconds; control
reservation `3600.000` seconds; candidate stored/canonical ceilings `67108864`
and `536870912` bytes; report ceiling `4194304` bytes; schedule/chunk sizes
`512` and `64`; consumed registration size `63171200` bytes; all-false
authority and empirical-operation maps; at-most-once claim; and no-retry rule.

The canonical no-publication receipt review SHALL:

1. Accept only final source commit `S`; derive the fixed r3 attempt, output,
   scratch, staging, and sealed-name pattern above; and accept no path, audit-id,
   source, or limit overrides.
2. Require the source-keyed attempt directory to contain exactly two regular
   files, `attempt_started.json` and `attempt_terminal.json`, each at most
   `1048576` bytes; reject `attempt_verified.json` and every additional entry.
3. Decode both as strict UTF-8 JSON with duplicate object keys rejected and
   require byte equality with `json.dumps(value, allow_nan=False,
   ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8") +
   b"\\n"`.
4. Require the started receipt to have exactly `attempt_sha256`, `audit_id`,
   `authority`, `empirical_operations`, `output_dir`, `schema_version`,
   `scratch_root`, `source_commit`, `staging_dir`, and `status`; require the
   fixed r3 identity and absolute paths, schema
   `noncombat-cross-fitted-empirical-successor-readiness-attempt-v1`, status
   `started`, and exact false Boolean values for authority keys `causal_claim`,
   `communication_mod`, `empirical_registration`, `evaluation`,
   `execution_authorization`, `execution_request`, `external_approval`,
   `formal_rl`, `gameplay`, `model_fitting`, `model_loading`, `native_loading`,
   `ope`, `policy_quality`, `promotion`, `qualification`, `seed_access`, and
   `training`, plus empirical-operation keys `communication_mod`,
   `environment_construction`, `evaluation`, `model_fitting`, `model_loading`,
   `native_loading`, `ope`, `runtime_fitting`, `seed_access`, and `training`;
   recompute `attempt_sha256` as SHA-256 of the canonical started body after
   removing only `attempt_sha256`.
5. Require the terminal receipt to have exactly `attempt_sha256`, `audit_id`,
   `authority`, `decision`, `empirical_operations`, `failure`, `schema_version`,
   `source_commit`, `status`, and `terminal_sha256`; require exact linkage to
   the started receipt, schema
   `noncombat-cross-fitted-empirical-successor-readiness-attempt-terminal-v1`,
   status `terminal_no_go`, the same exact false Boolean maps, decision fields
   exactly `failed_gates`, `reason`, and `status`, one failed gate from
   `source_binding`, `cohort_not_fresh`, `rehearsal_boundary`,
   `control_plane_scaling`, `budget_binding`, or `artifact_binding`, status
   `no_go`, matching reason `no_go_<gate>`, and failure fields exactly nonempty
   string `message` and `type` with message length at most `2000`; recompute
   `terminal_sha256` from the canonical terminal body after removing only
   `terminal_sha256`.
6. Require output, scratch, and exact staging to be absent and require zero
   sealed siblings matching the registered pattern; recompute and report raw
   SHA-256 and byte size for both receipts.
7. Emit one canonical JSON summary containing `audit_id`, `source_commit`,
   `attempt_sha256`, `terminal_sha256`, raw receipt bindings, decision,
   `all_authority_false=true`, `all_empirical_operations_false=true`, and
   `status=terminal_receipts_independently_verified`. Any failed check SHALL
   exit nonzero, verify nothing, and authorize no retry.

#### Scenario: Final preflight passes
- **WHEN** local `HEAD` and `origin/master` equal the final plan commit, that commit descends from the compact baseline with exactly the registered 16-row no-renames diff, the tracked worktree is clean, all bound paths match, r3 has no attempt, output, scratch, staging, or sealed path, and every registered r1/r2 size and digest remains exact
- **THEN** the exact source-keyed execution request may be presented without invoking the auditor

#### Scenario: Exact human authorization is absent
- **WHEN** the final source commit is known but the user has not explicitly approved its audit id, output, scratch, staging derivation, outer wait, all-false authority, at-most-once claim, and no-retry boundary
- **THEN** the runner remains blocked even if earlier standing repository or experiment authorization exists

#### Scenario: Any pre-start identity or path check fails
- **WHEN** source identity, ancestry, allowed path diff, tracked status, a bound path, old evidence, attempt path, output path, scratch path, staging path, script path, cwd, command argument, or ceiling differs from the registered value
- **THEN** the runner stops before invoking the auditor and does not choose another commit, id, path, limit, command, or authorization interpretation

#### Scenario: The attempt is claimed
- **WHEN** the source-keyed `attempt_started.json` is atomically installed
- **THEN** that source identity is permanently consumed regardless of exit, timeout, exception, no-go, verifier failure, or publication result and SHALL NOT be retried or resumed

#### Scenario: The auditor process exits
- **WHEN** a Windows process query finds no Python process whose command line binds the exact auditor script, source commit, audit id, output, and scratch paths, and no source-specific descendant remains; the readiness runner has no top-level output lease, so synthetic-child lease state is not used as an exit signal
- **THEN** the standalone publication verifier checks an installed publication, or the preregistered exact standard-library receipt-review algorithm checks canonical terminal closure, identity linkage, receipt hashes, all-false maps, and output/scratch/staging absence, before any project-direction claim is made

#### Scenario: Readiness returns go
- **WHEN** an independently verified canonical r3 report has decision `go`
- **THEN** only a later compact empirical-successor registration proposal becomes eligible while registration, native, seed, model, fitting, training, evaluation, OPE, gameplay, CommunicationMod, formal-RL, qualification, and promotion authorities remain false

#### Scenario: Readiness returns no-go or fails publication
- **WHEN** the r3 attempt closes with a typed no-go, exception, timeout, or absent canonical publication
- **THEN** terminal receipts and all-false authority are preserved, no downstream proposal is eligible, and no same-source repair or retry is permitted

#### Scenario: R2 eligibility is offered to the changed source
- **WHEN** a caller cites the verified r2 `go` instead of completing r3 against the final compact-source identity
- **THEN** registration eligibility remains false for the changed source and no r2 artifact, path, receipt, or cohort is substituted

#### Scenario: An empirical operation is requested
- **WHEN** any code path attempts native or model loading, environment construction, empirical outcome access, fitting, training, evaluation, OPE, gameplay, CommunicationMod, qualification, or promotion
- **THEN** the operation is forbidden and the attempt cannot yield readiness or downstream authority
