## ADDED Requirements

### Requirement: R8 Qualification Handoff Boundary
The outcome-evidence study SHALL treat an independently attested r8 result only as input to a separate study `start` review and SHALL remain blocked throughout this amendment.

#### Scenario: R8 is independently qualified
- **WHEN** the complete bootstrap-v1/request-v3 lifecycle, terminal anchors, request-bound restoration, protected inventory comparison, process-death evidence, and standalone verifier all pass for r8
- **THEN** the study SHALL record r8 as the sole current qualification candidate eligible for a separate review of whether to invoke `start`
- **AND** this amendment SHALL NOT create a run lock, ledger, slot configuration, gameplay or collection artifact, OPE artifact, checkpoint, model, reward, policy change, causal claim, training run, or promotion authority
- **AND** the repository SHALL remain tracked-clean at exact reviewed R while the r8 handoff and provisional closeout remain externally anchored until the later `start` decision or existing run-lock no-write window releases that freeze

#### Scenario: R8 is obsolete or retired
- **WHEN** offline review rejects r8 or any publication, invocation, qualification, verification, restoration, inventory, cleanup, or process boundary fails to produce a complete independently attested terminal
- **THEN** the registered study root SHALL remain absent and every remaining live task in `run-v2-known-propensity-outcome-evidence-study` SHALL remain blocked
- **AND** every published r8 byte SHALL remain immutable and no r8 retry, repair, deletion, reuse, or r9 preparation SHALL be authorized

#### Scenario: R8 amendment closes by disposition
- **WHEN** r8 becomes obsolete, retires, or qualifies for a later `start` review
- **THEN** its closeout SHALL bind exact source, request, review, root, result, verifier, attestation, configuration, inventory, process, disposition, limitation, and authority evidence
- **AND** an obsolete or retired branch MAY commit, sync, and archive immediately
- **AND** a qualified branch SHALL preserve tracked-clean R and external closeout anchors until a separate `start` decision declines launch or the study's tracked-write prohibition ends
