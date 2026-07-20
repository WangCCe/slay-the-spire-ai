## ADDED Requirements

### Requirement: R7 Qualification Handoff Boundary
The outcome-evidence study SHALL treat the independently attested r7 result only as input to a later study-launch review and SHALL remain blocked throughout this amendment.

#### Scenario: R7 is independently qualified
- **WHEN** the complete request-v3/bootstrap-v1 lifecycle, terminal anchors, restored request-bound isolation, protected inventory comparison, and independent attestation all pass for r7
- **THEN** the study SHALL record r7 as the sole current qualification candidate eligible for a later review of whether to invoke `start`
- **AND** this amendment SHALL NOT create the run lock, ledger, registered slot configuration, collection artifact, OPE artifact, model, checkpoint, policy change, causal claim, training run, or promotion authority
- **AND** the repository SHALL remain tracked-clean at the exact qualified R with no intervening write or commit; the r7 handoff, attestation, and provisional closeout SHALL remain externally anchored until the later `start` decision or run-lock no-write window releases that freeze

#### Scenario: R7 is retired
- **WHEN** r7 is obsolete before publication, retired after publication without an issued invocation, consumed without a complete valid attestation, or retired for any observed, uncertain, partial, invalid, failed, abrupt, or cleanup-uncertain live boundary
- **THEN** the registered study root SHALL remain absent and every remaining `run-v2-known-propensity-outcome-evidence-study` live task SHALL remain blocked
- **AND** a published r7 root SHALL remain immutable even when no invocation occurred, and no r7 byte MAY be retried, repaired, deleted, upgraded in place, or used to justify `start`

#### Scenario: R7 amendment closes deterministically
- **WHEN** offline review rejects r7, live qualification retires r7, or independent replay qualifies r7
- **THEN** the amendment closeout SHALL bind the exact source range, request/review/root/result/attestation hashes or declared absences, CommunicationMod before/after bytes, protected inventory comparison, process observations, disposition, limitations, and all-false authority
- **AND** an obsolete or retired branch MAY commit, sync, and archive that closeout immediately because no qualified `start` handoff exists
- **AND** a qualified branch SHALL keep the closeout external and the amendment active until a later reviewed decision declines `start` or the complete frozen-study tracked-write prohibition has ended, after which the exact externally anchored closeout MAY be imported without changing historical r7 evidence
- **AND** preparing r8, invoking study `start`, collecting trajectories, interpreting OPE, changing rewards or gameplay policy, training, and promotion SHALL each require separately reviewed authority outside this amendment
