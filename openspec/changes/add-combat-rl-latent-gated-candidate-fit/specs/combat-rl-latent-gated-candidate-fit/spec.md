## ADDED Requirements

### Requirement: Exact source and input binding
The candidate fit runner SHALL validate a committed registration containing the exact source commit, runner identity, native module, item data, parent checkpoint, development replay, evaluation replay checkpoints, fixed recipe, fixed technical gates, and output path before fitting begins.

#### Scenario: Bound input differs
- **WHEN** any registered source or input SHA-256, transition count, parent state identity, recipe, gate set, or output path differs
- **THEN** the runner raises a validation error before fitting and produces no completed output

#### Scenario: Registration or source inventory is not committed
- **WHEN** the registration differs from committed HEAD content or the exact behavior-affecting source inventory differs from its registered ancestor commit or current worktree
- **THEN** the runner raises a validation error before native or checkpoint loading

#### Scenario: Development and evaluation replay overlap
- **WHEN** the development replay and any evaluation replay, or two evaluation replays, share a path or SHA-256 identity
- **THEN** registration validation rejects the cohort as data leakage

#### Scenario: Unbound native dependency is supplied
- **WHEN** a registration supplies a DLL search directory for the self-contained registered native module
- **THEN** registration validation rejects the unbound dependency surface

### Requirement: Deterministic two-stage fitting
The runner SHALL use the registered seeds and budgets to pretrain the gate from fixed LightSTS guard labels, refine the gate on balanced direct and changed development rows, and fit the legal action head only on changed development rows.

#### Scenario: Fixed fit completes
- **WHEN** all registered inputs validate and the fit runs to completion
- **THEN** optimizer update counts, finite loss summaries, fitted head hashes, frozen parent hash, and calibrated threshold are recorded and exactly match the registered recipe

#### Scenario: Parent receives no update
- **WHEN** gate or action optimizer steps execute
- **THEN** no parent parameter receives a gradient and the parent state hash remains unchanged

### Requirement: Development-only threshold calibration
The gate threshold SHALL be calibrated only from development replay scores by maximizing changed-row recall subject to the registered direct-row open cap.

#### Scenario: Evaluation replay is scored
- **WHEN** one or more bound evaluation replays are loaded
- **THEN** no evaluation row changes model parameters or the calibrated threshold

### Requirement: Independent replay eligibility
The runner SHALL evaluate every bound replay independently against the registered direct-open, changed-open, direct-agreement, changed-correction, changed-candidate, overall-uplift, and positive-energy EndTurn gates.

#### Scenario: All evaluation replays pass
- **WHEN** every bound evaluation replay satisfies every registered technical gate
- **THEN** the report marks the artifact eligible only for a separately registered gameplay evaluation

#### Scenario: One evaluation replay fails
- **WHEN** any bound evaluation replay fails any technical gate
- **THEN** the report closes the scientific cohort as ineligible without tuning or promotion authority

### Requirement: Strict non-production artifact
The runner SHALL serialize the fitted heads and calibrated configuration with `build_development_artifact`, bind the artifact to the exact parent identities, and require exact restore parity before publication.

#### Scenario: Artifact round trip differs
- **WHEN** restored actions, correction actions, gate probabilities, telemetry, or fitted head hashes differ on the bound rows
- **THEN** the runner fails without publishing a completed output directory

### Requirement: Atomic reporting and practical retry boundary
The runner SHALL write through a run-scoped staging directory, SHALL refuse to overwrite a completed output, and SHALL distinguish infrastructure failure from a completed scientific decision.

#### Scenario: Infrastructure failure occurs before publication
- **WHEN** execution fails without a completed report
- **THEN** the unchanged registered recipe may be rerun after removing only its partial staging directory

#### Scenario: Output escapes development reports
- **WHEN** the registered output is not a new child of the repository `reports/` directory
- **THEN** the runner rejects the path before creating files

#### Scenario: Scientific report is published
- **WHEN** the output directory is atomically published with a passing or failing decision
- **THEN** changing seeds, budgets, thresholds, inputs, or gates requires a new registration and output identity

### Requirement: Development-only authority
The result SHALL NOT modify CommunicationMod, agent routing, production checkpoints, or gameplay state and SHALL NOT itself authorize qualification or promotion.

#### Scenario: Candidate is eligible offline
- **WHEN** every technical and integrity condition passes
- **THEN** the result authorizes only a separate gameplay-evaluation proposal or registration
