## ADDED Requirements

### Requirement: Repaired-source readiness r4 is one exact source-only attempt
The readiness runner SHALL use audit id
`noncombat-cross-fitted-empirical-successor-readiness-20260808-r4`, output path
`reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r4`, and
scratch path `.source_only_readiness_scratch_20260808_r4`. Its source commit
SHALL be the pushed, tracked-clean final planning commit that descends from and
preserves repair commit
`479f5536ca21e2abd543f33f970bef93103ba0d8`, contains the complete synced r4
contract, and has not been claimed by any readiness attempt. Immediately before
authorization and invocation, the source-keyed attempt directory, output path,
scratch path, exact derived staging sibling
`reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r4.<source-commit>.staging`,
and every matching sealed sibling SHALL be absent. All canonical bound inputs
SHALL exist at that commit; r1 and r2 evidence plus the consumed r3 attempt,
closeout, and residue SHALL remain unchanged. The repaired existing auditor
SHALL be invoked at most once with those exact values, its absolute script path,
the repository-root cwd, and unchanged internal ceilings, and only after an
exact human authorization names the final source and complete execution
boundary. Every empirical and downstream authority SHALL remain false for
every outcome.

The final preclaim source preflight SHALL require
`git diff --name-status --no-renames 479f5536ca21e2abd543f33f970bef93103ba0d8 <source-commit>`
to contain exactly these status/path rows and no others:

- `A openspec/changes/run-cross-fitted-readiness-20260808-r4/.openspec.yaml`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r4/design.md`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r4/proposal.md`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r4/specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md`
- `A openspec/changes/run-cross-fitted-readiness-20260808-r4/tasks.md`
- `M openspec/specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md`

The same preflight SHALL preserve all eight exact r1/r2 bindings in the
canonical r3 readiness requirement and require the r3 attempt directory to
contain exactly its two listed regular files, the r3 staging directory exactly
its one listed regular file, and the r3 closeout to remain a regular file, with
these exact decimal byte sizes and SHA-256 digests:

- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/5777eef4a43065e6246481926f95d6cfcba04c88/attempt_started.json`: `1386`, `89f65dccc117bf73c68c19c0e71b2bb1d9dca66b0c39a9f9402eafdd2f415fed`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/5777eef4a43065e6246481926f95d6cfcba04c88/attempt_terminal.json`: `1277`, `32ab883b9b5f3ecbefe937dc309adcceb577c421e2874e8b28ac1fbf4dc93dc7`
- `reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r3.5777eef4a43065e6246481926f95d6cfcba04c88.staging/candidate_seed_inventory.json.gz`: `6763664`, `6e7a0ab7da295e310b0da01757ab33883c61c6e11aa30d43fc1e529e4988bdc3`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r3_closeout.json`: `5011`, `d4fade45af25d26a319fc4ac44b2cd416af1083bbb19d4f841e609c6306a0c26`

Exact human authorization SHALL name the final 40-character source commit;
interpreter `D:\anaconda\envs\stsai\python.exe`; isolated `-I` mode; absolute
auditor script, repository root, and cwd
`D:\PycharmProjects\slay-the-spire-ai`; complete command; audit id; output,
scratch, source-keyed attempt, and derived staging paths; sealed sibling pattern
`.noncombat_cross_fitted_empirical_successor_readiness_20260808_r4.<64-lowercase-hex>.sealed`;
outer wait `7200` seconds; stage ceiling `300.000` seconds; independent verifier
ceiling `900` seconds; empirical ceiling `14400.000` seconds; control
reservation `3600.000` seconds; candidate stored/canonical ceilings `67108864`
and `536870912` bytes; report ceiling `4194304` bytes; schedule/chunk sizes
`512` and `64`; consumed registration size `63171200` bytes; exact all-false
authority and empirical-operation maps; at-most-once claim; and no-retry rule.

When no canonical publication exists after true process exit, an independent
Python `-I` standard-library review SHALL apply the canonical r3 receipt field,
schema, canonical-encoding, digest, false-map, bound, and path-absence algorithm
with only the registered r4 identifiers and source substituted. It SHALL accept
only an attempt directory containing exactly canonical `attempt_started.json`
and `attempt_terminal.json`, reject a verified receipt or additional entry,
require output, scratch, exact staging, and every matching sealed sibling
absent, and import no auditor, publication verifier, project, native, runtime,
Torch, or model module. No review result authorizes retry.

#### Scenario: Final preflight passes
- **WHEN** local `HEAD` and `origin/master` equal the final plan commit, tracked status is clean, repair ancestry and the exact six-row diff hold, all bound inputs and old evidence match, and every registered r4 attempt, output, scratch, staging, and sealed path is absent
- **THEN** the exact source-keyed authorization may be presented while the auditor remains uninvoked

#### Scenario: Any pre-start identity, evidence, or path check fails
- **WHEN** source identity, ancestry, diff, tracked status, a bound path, old evidence byte, attempt path, output path, scratch path, staging path, sealed sibling, script path, cwd, command argument, or ceiling differs from the registered value
- **THEN** execution stops before invoking the auditor and does not choose another commit, id, path, digest, limit, or command

#### Scenario: The attempt is claimed
- **WHEN** the source-keyed `attempt_started.json` is atomically installed
- **THEN** that source identity is permanently consumed regardless of exit, timeout, exception, no-go, verifier failure, cleanup failure, or publication result and SHALL NOT be retried or resumed

#### Scenario: The auditor process exits
- **WHEN** a source-specific Windows process query proves the exact auditor and every observed descendant absent
- **THEN** the standalone publication verifier checks an installed publication, or the preregistered independent standard-library review checks canonical terminal closure, identity linkage, receipt hashes, all-false maps, bounds, and path absence before any readiness claim is made

#### Scenario: Readiness returns go
- **WHEN** an independently verified canonical r4 report has decision `go`
- **THEN** only a later successor-registration proposal becomes eligible while registration, native, seed, model, fitting, training, evaluation, OPE, gameplay, CommunicationMod, formal-RL, qualification, and promotion authorities remain false

#### Scenario: Readiness returns no-go or fails publication
- **WHEN** r4 closes with typed no-go, exception, timeout, cleanup failure, or absent canonical publication
- **THEN** terminal evidence and all-false authority are preserved, no downstream proposal is eligible, and no same-source repair or retry is permitted

#### Scenario: Consumed r3 is substituted or modified
- **WHEN** a caller deletes, rewrites, reparses as historical seed evidence, verifies in place, or retries the r3 attempt, closeout, or staging residue, or substitutes r3 identity or paths for r4
- **THEN** preflight and independent verification fail closed and r4 grants no readiness or downstream authority

#### Scenario: An empirical operation is requested
- **WHEN** any code path attempts native or model loading, environment construction, empirical outcome access, fitting, training, evaluation, OPE, gameplay, CommunicationMod, qualification, or promotion
- **THEN** the operation is forbidden and the attempt cannot yield readiness or downstream authority
