# noncombat-large-corpus-card-uplift-residual-audit Specification

## Purpose
TBD - created by archiving change add-large-corpus-card-uplift-residual-audit. Update Purpose after archive.
## Requirements
### Requirement: Frozen audit lineage
The runner SHALL bind the exact residual model, selected configuration, r7
entry checkpoint, corpus train/development evidence, native identity, source,
and reserved audit schedule. It MUST reject any drift before audit access.

#### Scenario: Audit preflight passes
- **WHEN** every bound byte, schedule, process, and production-isolation check passes
- **THEN** the exact frozen model may be evaluated on the reserved audit cohort

#### Scenario: Bound evidence differs
- **WHEN** any source, model, input, schedule, native, process, or isolation binding differs
- **THEN** the runner stops before constructing an audit environment

### Requirement: Bounded complete audit collection
The runner SHALL consume only seeds `80320..80383`, collect at most two complete
card states per seed and 512 branches, permit at most four registered Courier
censors, and require at least 110 complete states. Censored seeds MUST NOT be
replaced.

#### Scenario: Audit collection succeeds
- **WHEN** complete states meet the floor within all fixed limits
- **THEN** the canonical audit dataset is persisted with exact source identities and returns

#### Scenario: Collection boundary fails
- **WHEN** a nonregistered blocker, censor overflow, branch overflow, deadline, or support failure occurs
- **THEN** no usable audit verdict is published and no seed or limit changes

### Requirement: No-refit independent evaluation
The runner SHALL restore the frozen model before native environment
construction and MUST NOT fit, tune, or replace it before or after audit access.

#### Scenario: Fixed gate passes
- **WHEN** all registered regret, ranking, correction, and safety checks pass
- **THEN** the verdict authorizes only a separate fresh gameplay/evaluation proposal

#### Scenario: Fixed gate fails
- **WHEN** any registered check fails
- **THEN** the residual is not ready and no retry, tuning, promotion, or production loading is authorized

### Requirement: No downstream authority
The audit report SHALL keep gameplay, policy-quality, promotion, qualification,
production loading, OPE, and causal authority false.

#### Scenario: Audit report is published
- **WHEN** fixed evaluation completes
- **THEN** exact metrics, flips, censors, unseen cards, and isolation evidence are published without modifying production state
