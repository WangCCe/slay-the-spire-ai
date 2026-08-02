## ADDED Requirements

### Requirement: Bind read-only source and train evidence
The audit SHALL bind the exact preserved train-only corpus, its manifest, the
implementation commit and runtime, lineage artifacts, and every audited C++ and
Python source file by physical identity. It MUST NOT build, load, execute, or
modify the external simulator checkout, and it MUST reject validation/final
cohorts, new seeds, outcomes, rewards, prior predictions, and prior metrics as
audit inputs.

#### Scenario: Registered inputs are valid
- **WHEN** the runner receives the exact registered corpus, source files,
  runtime, implementation, and lineage identities
- **THEN** it SHALL retain only route/card rows from seeds `4000..4031`
- **AND** it SHALL record the external commit, checkout status, and audited-file
  hashes without requiring unrelated checkout files to be clean

#### Scenario: Input identity or scope differs
- **WHEN** any required identity differs or unregistered evidence reaches the
  audit boundary
- **THEN** the audit SHALL fail closed before source interpretation or metrics

### Requirement: Reconstruct source-policy dependencies and actions
The audit SHALL extract the registered SimpleAgent route/card decision blocks
and policy constants, publish a dependency matrix, and deterministically
reproduce every recorded route/card teacher action from the source semantics
and recorded row. Ordering, strict comparisons, hidden cached map-path state,
candidate mapping, upgrade adjustment, copy-limit behavior, and skip/bowl
mapping MUST be explicit.

#### Scenario: A preserved teacher row is audited
- **WHEN** the row and bound source satisfy their contracts
- **THEN** the reference evaluator SHALL select exactly the recorded teacher
  action
- **AND** every input it reads SHALL map to a published dependency entry

#### Scenario: Source closure is incomplete
- **WHEN** an anchor cannot be extracted, a policy constant is ambiguous, a
  teacher action cannot be expressed exactly once, or reproduction differs
- **THEN** the audit SHALL classify the execution `blocked`

### Requirement: Quantify representation and action aliases
The audit SHALL compute the preregistered teacher-source, adapter-observable,
legacy-hash-1024, and structured-hash-2048 ordered decision signatures for every
multi-candidate route/card row. It SHALL report repeated/conflicting decision
groups, exact candidate-vector equivalence, indistinguishable targets, directed
pairwise preference contradictions, and raw-versus-semantic action agreement
without tolerance or result-dependent coarsening.

#### Scenario: Representation metrics are generated
- **WHEN** all eligible rows have valid candidates and exact teacher labels
- **THEN** the report SHALL materialize every required count and affected row
  identity separately by category and representation
- **AND** semantic duplicate-card actions SHALL be distinguished from
  non-equivalent action conflicts

#### Scenario: A required signature or metric is missing
- **WHEN** any row cannot be represented, a float is non-finite, a required
  metric cannot be recomputed, or a signature definition changes after result
  observation
- **THEN** the audit SHALL fail closed

### Requirement: Separate adapter gaps from teacher suitability
The audit SHALL classify required source dependencies as directly represented,
deterministically derivable, policy constant, intentionally irrelevant, or
missing for raw adapter, legacy, and structured layers. It SHALL evaluate fixed
teacher-suitability checks for adaptive route state, current deck/run context,
copy-limit semantics, and skip/bowl utility independently from imitation
fidelity.

#### Scenario: Only a learned projection loses information
- **WHEN** raw adapter rows reproduce the teacher without non-equivalent target
  conflicts but a hashed projection contains aliases or preference
  contradictions
- **THEN** the audit SHALL attribute the finding to that projection/model layer
- **AND** it SHALL NOT call it an adapter representation gap

#### Scenario: The teacher is deterministic but policy-narrow
- **WHEN** adapter reproduction is complete and any critical source-backed
  teacher-suitability check fails
- **THEN** the audit SHALL state that deterministic imitation is not evidence of
  policy quality

### Requirement: Publish one terminal no-authority verdict
The audit SHALL apply the fixed ordered classifier and publish exactly one of
`blocked`, `adapter_representation_repair_required`,
`simpleagent_unsuitable_as_policy_quality_gate`, or `audit_inconclusive`. The
canonical artifact set SHALL be hash-closed, strictly recomputable, bounded to
the registered resources, and contain only false downstream authority flags.

#### Scenario: An actionable adapter gap is demonstrated
- **WHEN** source dependencies are missing/non-derivable or raw adapter
  signatures contain conflicting non-equivalent targets after source closure
  and exact candidate mapping have passed
- **THEN** the verdict SHALL be `adapter_representation_repair_required`
- **AND** it SHALL authorize only a separate adapter-repair proposal

#### Scenario: Teacher limitations dominate
- **WHEN** no actionable adapter gap exists and any critical teacher-suitability
  check fails
- **THEN** the verdict SHALL be
  `simpleagent_unsuitable_as_policy_quality_gate`
- **AND** SimpleAgent SHALL remain only an auxiliary regression oracle pending a
  separate outcome-backed RL-readiness proposal

#### Scenario: A consumer inspects the result
- **WHEN** the manifest and report are loaded or recomputed
- **THEN** simulator build/load/rollout, model fitting, new evidence collection,
  live gameplay/loading, DAgger, formal RL, qualification, OPE reinterpretation,
  and policy promotion authority SHALL all be false
