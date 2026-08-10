## 1. Freeze R6 Planning

- [x] 1.1 Bind pushed r5 verification, incident, and archive commits, absent r5 registration, and unchanged parent 6.2/6.3; strict-validate and independently review the complete r6 proposal, design, delta specs, and task plan with a tool-prohibited static reviewer; resolve every actionable finding.
- [x] 1.2 Commit and push the planning boundary before changing producer, verifier, tests, parent tasks, or registration artifacts.

## 2. Implement Frozen Registration Validation

- [x] 2.1 Add RED producer tests for strict raw-byte parsing, duplicate/noncanonical input rejection, the exact 16-field schema, r5 evidence bindings, canonical self-digest, exact cohorts/role digests, closed all-false maps, and rejection of drift without filesystem discovery.
- [x] 2.2 Add RED standalone tests for duplicate/unknown fields, non-boolean or true authority, cohort/role drift, evidence mismatch, and independent standard-library acceptance.
- [x] 2.3 Add RED driver tests for canonical request/CLI identity, separately trusted request digest, pre-request receipt on malformed request/missing request/wrong root/nonisolated failures, independent-stage API absence, exact six-JSON allowlist enforcement, symlink/alias/additional-path rejection, prohibition of preflight/directory/glob enumeration, one-open accounting, real composed-validator success, exclusive output creation, short writes, and flush/fsync failures.
- [x] 2.4 Implement the minimal pure producer registration builder and validator, expose their stable public API, and keep every path/discovery/native/runtime operation outside the functions.
- [x] 2.5 Implement the independent standard-library registration validator without importing producer, seed-inventory, runtime, native, or model modules.
- [x] 2.6 Implement the dedicated one-shot registration driver and exact CLI with a separately trusted request digest, immutable pre-request receipt and transitive bindings, strict six-canonical-JSON allowlist and raw-byte validation, exact request/evidence one-open accounting, fresh standalone reconstruction, in-memory dual validation, and exclusive publication without preflight or directory enumeration.
- [x] 2.7 Run focused producer/standalone/driver tests, compile checks, strict change validation, and the owning card-acceptance test set under the Windows temp convention.
- [x] 2.8 Run the registered full pytest gate once after focused GREEN; treat pytest temp setup/cleanup permission failures as infrastructure, do not repeat successful tests for cleanup, and record gameplay validation as not applicable.
- [x] 2.9 Give a tool-prohibited reviewer only exact source/diff and test-evidence text, with no path or report-root access; resolve findings, then commit and push the source boundary. Any out-of-scope review access closes r6.

## 3. Register From Allowlisted R5 Evidence

- [x] 3.1 From pushed tracked-clean HEAD, publish one exact r6 preflight binding only the six allowlisted r5 inputs, their canonical hashes/sizes, pushed r5 verification/incident/archive commits, absent r5 registration, unchanged parent 6.2/6.3, absent r6 receipt/output/review paths, and explicit denial of directory enumeration, globbing, report-root search, protected predecessor access, and downstream authority.
- [x] 3.2 Independently review and commit/push the preflight before any registration input is opened by the rendering step.
- [ ] 3.3 Render, independently text-review, commit, and push one canonical driver request binding the pushed preflight, exact six input content kinds/hashes/sizes, receipt/output paths, registration id/schema, both source commits, all-false downstream map, and exact sole CLI identity including the separately reviewed expected request digest and receipt path.
- [ ] 3.4 Recheck pushed cleanliness and exact request/allowlist identity, then invoke the driver once. It must claim its immutable invocation receipt before reading or resolving the request, require the request bytes/self-digest to equal the separately reviewed expected digest, open each allowlisted raw input exactly once, strict-parse and canonical-byte-compare all six JSON inputs, rerun standalone inventory reconstruction, and render plus dual-validate one registration entirely in memory without substitution, discovery, preflight access, or additional path access. Any process or pre-publication failure is terminal without reinvocation.
- [ ] 3.5 After in-memory GREEN, let the same invocation publish once through exclusive create/write/flush/fsync; preserve receipt plus any complete or partial output and close r6 without deletion, retry, repair, or replacement on publication failure. Record exact validator agreement and require the driver output set to equal receipt plus registration, with the later review accounted separately.
- [ ] 3.6 Give a tool-prohibited reviewer only exact canonical preflight, request, receipt, registration, validator-result, and access-accounting text; on no findings, complete parent task 6.2, leave 6.3 unchanged, and commit/push without creating a training request or granting downstream authority. Any out-of-bounded-text review access closes r6.

## 4. Closeout

- [ ] 4.1 Publish a bounded closeout, sync applicable main specs, archive r6, strict-validate globally, verify tracked path hygiene, and commit/push the archive without training, evaluation, gameplay, OPE, qualification, or promotion.
