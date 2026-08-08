## ADDED Requirements

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
