# Non-Combat State-Conditioned Collapse Audit Specification

## Purpose

Define a deterministic, read-only audit of retained state-conditioned simulator
artifacts that locates card-reward action-family collapse without accessing a
holdout cohort, replaying seeds, fitting a model, or granting downstream
authority.

## Requirements

### Requirement: Frozen terminal evidence is identity-bound and read-only
The audit SHALL accept one consumed state-conditioned terminal bundle and SHALL
read only the explicit analysis allowlist of terminal manifest, training rows,
terminal diagnostics, terminal metrics, final model, paired evaluation
container, and contiguous checkpoint files. It SHALL validate source bytes
against manifest identities, require exact all-false source authority, bind
checkpoint execution and registration identities to the terminal manifest,
reject symlinks and structural drift, and never modify a source artifact.

#### Scenario: Valid consumed canary-stop evidence is loaded
- **WHEN** every allowed artifact is canonical, manifest-bound, schema-valid,
  terminal, contiguous, and consistent with an unaccessed holdout
- **THEN** the audit SHALL retain each consumed source path, byte count, and
  SHA-256 and proceed with analysis
- **AND** it SHALL consume only initial and trained canary rows from the paired
  evaluation container and SHALL NOT open registration cohorts, seed
  inventories, native bindings, or any file outside the allowlist

#### Scenario: Holdout or terminal integrity is inconsistent
- **WHEN** diagnostics indicate holdout access, holdout diagnostics are present,
  the evaluation holdout wrapper indicates access or contains an evaluation
  object, a source identity differs, a checkpoint is missing or extra, or a
  required terminal coordinate is inconsistent
- **THEN** the audit SHALL fail before publication
- **AND** it SHALL NOT infer, repair, substitute, replay, or discover evidence

#### Scenario: Source authority or execution identity drifts
- **WHEN** a retained authority map is not the exact registered all-false map,
  a checkpoint identity is malformed or mixed, or its logical execution or
  registration hash differs from the terminal manifest
- **THEN** the audit SHALL fail before publishing an all-false authority claim
- **AND** it SHALL NOT normalize or inherit authority from its own output

### Requirement: Candidate and action-family dynamics are reconstructed exactly
For each retained decision, the audit SHALL validate candidate identity, order,
kind, selected action, and finite score alignment. It SHALL recompute every
episode action-sequence hash, align ordered diagnostic IDs and selected actions
to their exact episode and seed, require frozen canary selections to be greedy,
and recompute the terminal card-reward blocker from those rows. For every
card-reward decision exposing both `take` and `skip`, it SHALL report candidate
multiplicity, selected and greedy kinds, best-take minus best-skip score margin,
stable softmax probability mass by kind, candidate entropy, kind entropy, and
take-family probability excess over candidate-count share.

#### Scenario: A card reward exposes take and skip
- **WHEN** one or more `take` candidates and exactly one `skip` candidate have
  finite recorded scores
- **THEN** the audit SHALL include the decision in chunk-level opportunity,
  selection, greedy, margin, probability, multiplicity, and entropy summaries
- **AND** it SHALL preserve whether any additional registered kind was present

#### Scenario: Diagnostic and episode evidence align
- **WHEN** retained training or canary decisions are audited
- **THEN** every decision ID, category, selected action, action count, and
  action-sequence SHA-256 SHALL match its ordered episode evidence
- **AND** canary selections and the stored saturation blocker SHALL recompute
  from the same validated rows

#### Scenario: Candidate evidence is malformed
- **WHEN** action IDs are duplicated, selected action is unavailable, scores do
  not exactly cover candidates, kinds are invalid, values are nonfinite, or a
  card-reward skip/take contract is incomplete
- **THEN** the audit SHALL reject the evidence rather than drop or normalize the
  decision

#### Scenario: Another target category is observed
- **WHEN** route, event, or shop diagnostic rows are retained
- **THEN** the audit SHALL report generic opportunity, selected-kind, greedy-kind,
  probability, margin, and entropy summaries as descriptive controls
- **AND** it SHALL NOT claim that unlike candidate schemas are causally
  interchangeable

### Requirement: Training chunks and checkpoints form one explicit trajectory
The audit SHALL preserve training chunk order, pre-update decision semantics,
episode outcomes, optimizer-update coordinates, and one aligned post-update
checkpoint per chunk. It SHALL decode finite float32 model tensors, verify
their embedded hashes and architecture-derived shapes, strictly type every
coordinate, report model norms and consecutive post-update delta norms, and
require the final model to equal the last checkpoint model.

#### Scenario: A complete 64-chunk trajectory is audited
- **WHEN** chunk `n` contains its registered episode interval and optimizer
  update and checkpoint `n + 1` contains the resulting runtime state
- **THEN** the audit SHALL align the pre-update decision summary with that
  post-update checkpoint and retain pass, reward, floor, victory, support,
  entropy, loss, and gradient summaries

#### Scenario: Initial tensors are unavailable
- **WHEN** the terminal bundle contains only the initial-model SHA-256
- **THEN** checkpoint 1 parameter delta SHALL be null with an explicit evidence
  gap
- **AND** the audit SHALL NOT regenerate, estimate, or substitute initial
  tensors

#### Scenario: Tensor or coordinate continuity fails
- **WHEN** a tensor hash, dtype, byte order, shape, parameter key, checkpoint
  link, chunk interval, optimizer update, or final-model equality check fails
- **THEN** the audit SHALL fail closed without publishing a trajectory claim

### Requirement: Collapse boundaries do not tune thresholds
The audit SHALL publish the complete chunk series and SHALL locate exact
first-observed and earliest-persistent boundaries for selected-kind saturation
and greedy score saturation. An observed-selection saturation chunk SHALL have
eligible card-reward decisions and no selected non-`take` kind. A greedy
saturation chunk SHALL have eligible card-reward decisions and a strictly
positive best-take/skip margin for every eligible decision.

#### Scenario: Saturation occurs transiently
- **WHEN** an exact saturation predicate is true for one chunk and false in a
  later chunk
- **THEN** the audit SHALL report its first occurrence but SHALL NOT classify it
  as the persistent boundary

#### Scenario: Saturation persists to the final chunk
- **WHEN** the same exact predicate is true for every chunk from one boundary
  through the final chunk
- **THEN** the audit SHALL report the earliest such persistent boundary and all
  supporting chunk indices

#### Scenario: No persistent training saturation exists
- **WHEN** stochastic exploration continues to select a non-`take` kind or a
  later greedy margin is nonpositive
- **THEN** the corresponding persistent boundary SHALL be null
- **AND** terminal greedy canary saturation SHALL remain a separate observation

### Requirement: Conclusions preserve evidence limits and no authority
The audit SHALL separate direct observations, bounded interpretations,
unresolved hypotheses, and prohibited claims. It SHALL classify candidate
multiplicity, scores, reconstructed probabilities, selections, entropies,
outcomes, and parameter movement as descriptive evidence only and SHALL retain
all downstream authority as false.

#### Scenario: Recorded dynamics narrow a mechanism
- **WHEN** the trajectory shows action-family probability or score concentration
  alongside candidate multiplicity or candidate-versus-kind entropy divergence
- **THEN** the audit MAY report that the observations are consistent with a
  bounded mechanism
- **AND** it SHALL NOT claim reward, optimizer, architecture, or intervention
  causality

#### Scenario: A future action is considered
- **WHEN** the report identifies a candidate ablation, representation change,
  objective change, or successor experiment
- **THEN** it SHALL list that action only as separately reviewable follow-up
- **AND** it SHALL NOT authorize training, replay, seed access, threshold
  changes, model selection, formal RL, gameplay, CommunicationMod, policy
  loading, qualification, or promotion

### Requirement: Publication and verification are deterministic and bounded
The audit SHALL serialize canonical JSON, derive Markdown only from the
normalized JSON result, refuse output paths inside the consumed source bundle,
and atomically write only the two explicit output paths. Identical source bytes
and arguments SHALL produce byte-identical outputs.

#### Scenario: The frozen audit is published
- **WHEN** source validation and every analysis invariant pass
- **THEN** JSON and Markdown SHALL retain source identities, audit parameters,
  complete trajectory summaries, boundary evidence, limitations, and the exact
  invocation without a wall-clock timestamp

#### Scenario: Verification fails
- **WHEN** focused regressions, strict OpenSpec validation, deterministic
  reproduction, source immutability checks, or the repository commit gate fails
- **THEN** the change SHALL remain incomplete
- **AND** no successor algorithm or experiment SHALL be proposed as established
  by the failed audit
