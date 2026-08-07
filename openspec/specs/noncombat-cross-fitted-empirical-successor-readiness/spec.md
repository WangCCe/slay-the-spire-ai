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
decision. It SHALL reject missing, mutable, rehashed, or source-inconsistent
inputs before any rehearsal or candidate publication.

#### Scenario: The pushed source and evidence are exact
- **WHEN** every required Git blob and immutable artifact matches its registered path, size, and SHA-256 under one pushed commit
- **THEN** the audit may continue source-only and grants no registration, native, seed, fitting, training, or evaluation authority

#### Scenario: One bound input drifts
- **WHEN** `HEAD`, `origin/master`, tracked status, a source blob, consumed terminal artifact, closeout, contract, or historical throughput input differs
- **THEN** the claimed attempt emits typed `no_go_source_binding` before rehearsal, installs no final publication, and does not substitute a nearby file or commit

### Requirement: The candidate cohort is canonical and fully fresh
The audit SHALL reconstruct the complete historical seed inventory from the
bound Git tree and publish that canonical inventory. It SHALL derive exactly
the first 512 ascending nonnegative seeds absent from that inventory and all
reserved ranges. It SHALL extract the complete 512-seed schedule from the
consumed cross-fitted registration and require an empty intersection, including
the 500 scheduled positions that were never debited. Producer validation and
independent reconstruction SHALL use shallow or streamed representations for
the actual-scale inventory and SHALL NOT deep-copy or concurrently materialize
multiple complete canonical inventories.

#### Scenario: A fully disjoint candidate schedule exists
- **WHEN** the rebuilt inventory is canonical, its independent replay is byte-identical, the candidate contains 512 ordered unique seeds, and its intersection with the consumed 512-seed schedule is empty
- **THEN** the audit records the candidate inventory/schedule digests and continues without treating any seed integer as an environment access

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
