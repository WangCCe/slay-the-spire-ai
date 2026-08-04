## ADDED Requirements

### Requirement: Successor Cohort Reuse Preregistration
The experiment process SHALL require canonical predecessor and overlap evidence
before preregistering a new logical execution over a cohort named by a prior
terminal execution.

#### Scenario: Terminal predecessor qualifies for cohort reuse
- **WHEN** an independently verified predecessor consumed its logical execution
  identity but constructed no environment, accessed no registered seed, retained
  no episode, performed no optimizer update, and observed neither canary nor
  holdout outcome
- **THEN** a successor preregistration MAY retain the exact predecessor cohort
- **AND** a canonical reuse inventory SHALL bind the immutable predecessor
  controls and terminal artifacts and classify the overlap as
  `registered_but_unconsumed`

#### Scenario: Prior empirical use or unclassified overlap is found
- **WHEN** any predecessor evidence is nonterminal, unverifiable, contradictory,
  seed-dependent, or any additional tracked registration-shaped artifact
  intersects the candidate cohort without an explicit qualifying disposition
- **THEN** successor preregistration SHALL stop before publication
- **AND** it SHALL NOT substitute another seed, range, threshold, source, module,
  or logical execution identity inside the same change

#### Scenario: Successor preregistration is published
- **WHEN** the cohort-reuse inventory qualifies, the repaired implementation is
  pushed, and all source, runtime, native, evidence, and inventory bindings match
- **THEN** the successor registration SHALL use canonical bytes, the unchanged
  fixed experiment contract, and all-false authority
- **AND** its authorization and output SHALL remain absent

#### Scenario: Preregistration is reproduced independently
- **WHEN** two fresh source-only processes generate and validate the successor
  inventory and registration from the same pushed inputs
- **THEN** both processes SHALL produce byte-identical artifacts and digests
- **AND** neither process SHALL import native code or Torch, construct an
  environment, access a registered seed, train, launch gameplay, contact
  CommunicationMod, or mutate production checkpoints

#### Scenario: Later execution is considered
- **WHEN** the successor preregistration has been committed and pushed
- **THEN** execution SHALL still require a separate exact authorization binding
  the pushed registration commit, new logical execution identity, output path,
  cohort, module, resource limit, and no-retry rules
- **AND** preregistration alone SHALL grant no execution, formal-RL, live,
  qualification, loading, OPE, causal, or promotion authority
