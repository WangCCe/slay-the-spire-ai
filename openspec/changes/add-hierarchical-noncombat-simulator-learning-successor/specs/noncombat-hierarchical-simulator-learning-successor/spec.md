## ADDED Requirements

### Requirement: Isolated successor identity
The system SHALL implement the hierarchical simulator-learning successor as a
new additive identity with its own schemas, source allowlist, registration,
authorization, checkpoints, artifacts, and verifier. It SHALL NOT modify the
consumed state-conditioned runner, verifier, tests, registration, checkpoints,
terminal artifacts, or prior holdout identity, and it SHALL NOT import private
logic from the consumed runner.

#### Scenario: Source-only successor implementation is prepared
- **WHEN** the successor source and focused fixtures are created before any registration
- **THEN** every consumed experiment byte remains unchanged and the successor binds only its new files plus explicitly reused low-level public APIs

#### Scenario: Control-only command is imported
- **WHEN** a registration, inventory, preflight, or verification command is imported or run
- **THEN** the system does not import Torch, load a native module, construct an environment, materialize a cohort, or access an empirical seed

### Requirement: Hierarchical family-first training policy
The runtime SHALL treat each validated candidate `kind` as its action family,
use max-pooled family logits, sample the sorted family distribution first, and
then sample original-order candidates within the selected family. It SHALL use
one checkpointed CPU Torch generator and SHALL perform the family draw before
the conditional draw at every training decision, including one-family and
one-candidate decisions.

#### Scenario: Multi-family training decision is sampled
- **WHEN** a legal decision contains candidates from at least two kinds
- **THEN** the runtime samples one family and one member of that family in the registered order and applies only the aligned selected `action_id`

#### Scenario: One-family event or route is sampled
- **WHEN** every legal candidate has the same kind
- **THEN** the family log probability and family entropy are exactly zero while the conditional distribution, RNG step, objective term, and legal action selection remain active

#### Scenario: Checkpointed sampling is resumed
- **WHEN** an infrastructure interruption resumes from the last complete checkpoint with unchanged controls
- **THEN** the restored model, optimizer, Python RNG, Torch generator, and coordinates reproduce the registered two-stage action sequence exactly

### Requirement: Split hierarchical objective
The system SHALL train with selected joint log probability equal to selected
family plus selected conditional log probability. It SHALL set
`family_entropy_coefficient` to `0.01` and
`conditional_entropy_coefficient` to `0.01`, apply each coefficient exactly
once to its corresponding mean entropy, and reject any runtime override or
metadata drift.

#### Scenario: One training chunk computes its loss
- **WHEN** aligned hierarchical terms and normalized returns are available for a complete chunk
- **THEN** policy loss uses the selected joint log probabilities and total loss subtracts `0.01` times mean family entropy plus `0.01` times mean expected-conditional entropy without an additional joint-entropy term or any claim that old and new entropy magnitudes are equal

#### Scenario: Coefficients affect independent gradients
- **WHEN** a synthetic multi-family batch compares the runtime loss and gradients with the manually reconstructed fixed-coefficient formula and with each entropy contribution differentiated separately
- **THEN** the family and conditional contributions are independently present at coefficient `0.01` while no runtime coefficient override is exposed

#### Scenario: Numeric boundary is extreme but finite
- **WHEN** CPU float32 ranker scores contain opposite finite float32 limits
- **THEN** all exposed CPU float64 hierarchical probabilities, log probabilities, entropies, losses, and gradients remain finite or the chunk fails closed before an update

### Requirement: Fixed non-policy controls
The successor SHALL preserve model seed `0`, the checked-in state-conditioned
ranker architecture and policy-input projection, Adam learning rate `0.001`,
betas `(0.9, 0.999)`, epsilon `1e-8`, zero weight decay, no AMSGrad, discount
`1.0`, normalized returns, gradient ceiling `1.0`, exact API v3 candidate order,
and formal scalar reward `2.0 * terminal_victory + bounded_floor_progress`.

#### Scenario: Successor contract is registered
- **WHEN** the clean pushed implementation is converted into a registration
- **THEN** every fixed control and imported source identity is present with no caller-supplied algorithm, reward, model, optimizer, coefficient, threshold, or runtime override

#### Scenario: A selected branch is applied
- **WHEN** the runtime selects one validated candidate on a cloned API v3 environment
- **THEN** only that legal `action_id` is applied, the unselected source environment remains byte-equivalent, and reward uses only the two formal channels

### Requirement: Raw-score deterministic evaluation
Frozen evaluation SHALL select only a unique maximum raw candidate score. It
SHALL NOT use family probability, conditional probability, joint probability,
candidate order, or lexical order as an argmax or tie-break rule.

#### Scenario: Unique raw-score maximum exists
- **WHEN** one candidate has the unique maximum raw score
- **THEN** evaluation selects that candidate and independently confirms the same result through maximum-family then maximum-within-family score semantics

#### Scenario: Raw-score maximum is tied
- **WHEN** two or more action IDs share the maximum raw score
- **THEN** evaluation fails closed before applying an action and records the complete tied action-ID set

#### Scenario: Joint-probability argmax differs
- **WHEN** hierarchical joint candidate probabilities rank a different action above the raw-score maximum
- **THEN** evaluation still selects the unique raw-score maximum and records the probability difference only as diagnostic evidence

### Requirement: Family-aware trajectory stop
After every complete training chunk, the system SHALL evaluate the trailing four
complete chunks for `card_reward` and `shop`. If the raw-score maximum-family
set equals the same singleton family for exactly `100%` of at least `64`
multi-family decisions in either category, the system SHALL stop before the
next chunk with verdict
`experiment_stopped_during_training_for_family_saturation` and SHALL NOT access
canary or holdout.

#### Scenario: Persistent card-reward family saturation is observed
- **WHEN** four consecutive durable chunks contain at least 64 multi-family card-reward decisions and every raw-score maximum action belongs to the same one family
- **THEN** the terminal training-collapse verdict is published before another update or any canary environment is constructed

#### Scenario: Window is insufficient
- **WHEN** a four-chunk window has fewer than 64 eligible decisions or contains at least two raw-score greedy families
- **THEN** the exact training-collapse predicate does not fire and training may continue within all other registered limits

### Requirement: Canary protects holdout
After complete training, the system SHALL evaluate frozen initialization and
trained policies on the same fresh canary seeds with exact replay. The trained
policy SHALL have at least `32` multi-family decisions, at least two selected
raw-score greedy families, and maximum selected-family rate at most `0.95`
independently in `card_reward` and `shop`. Canary SHALL also require exact
replay, legal candidates, all four target categories, unsupported rate at most
`0.10`, absolute relative-score change at least `1e-8` on at least `4`
multi-candidate decisions with nonzero-effect rate at least `0.25` and at least
one relative-order change, trained victory noninferiority, and a positive
paired floor lower confidence bound from `10,000` bootstrap resamples at `95%`
confidence with seed `0`.

#### Scenario: Canary passes all gates
- **WHEN** both frozen policies complete the registered canary and every structural, support, state-effect, family, victory-noninferiority, and paired-floor gate passes
- **THEN** and only then may the system construct an environment for the registered holdout

#### Scenario: Card reward or shop remains saturated
- **WHEN** either trained canary category has too few opportunities, fewer than two selected families, or a largest selected-family rate above `0.95`
- **THEN** the system publishes `experiment_stopped_at_canary` and records zero holdout episode and seed access

#### Scenario: Event and route expose one family
- **WHEN** canary event or route decisions contain only their current single candidate kind
- **THEN** the system reports their conditional behavior without applying the multi-family cardinality or selected-family-rate gates to those categories

### Requirement: Fresh deterministic cohort isolation
After source-only implementation is clean, reviewed, committed, and pushed,
the system SHALL build one tracked seed-exclusion inventory from a fixed Git
tree and SHALL select fresh cohorts by one fixed ascending algorithm. It SHALL
select `1,024` train, `128` canary, and `512` holdout seeds; repeat train seeds
for four fixed passes; and exclude every historical, consumed, selected,
reserved, diagnostic, training, canary, evaluation, and holdout identity,
including prior untouched seeds `71152..71663`.

#### Scenario: Registration materializes cohorts
- **WHEN** the fixed inventory and ascending selection algorithm run against the clean pushed implementation
- **THEN** the three cohorts are unique, mutually disjoint, absent from every exclusion, and exactly bound into an all-false-authority registration

#### Scenario: Caller proposes alternate seeds
- **WHEN** a caller supplies a seed, search start, replacement cohort, or reordered training pass
- **THEN** source-only validation rejects the registration before native loading or environment construction

### Requirement: Bounded CPU execution
The registration SHALL cap execution at `64` episodes per optimizer update,
`64` updates, `4,096` training episodes, `2,560` evaluation/replay episodes,
`6,656` total episodes, `500` decisions per episode, CPU only, and `28,800`
charged seconds. Runtime inputs SHALL NOT raise any bound.

#### Scenario: Resource limit is reached
- **WHEN** the next decision, episode, update, evaluation, or elapsed interval would exceed a registered ceiling
- **THEN** the system stops at the last durable coordinate, preserves a bounded terminal result, and does not skip work or substitute another limit

#### Scenario: Source benchmark supports a lower ceiling
- **WHEN** source-only benchmarks justify a lower episode or wall-time bound before registration
- **THEN** the registration may lower that bound but cannot raise any proposal ceiling without renewed proposal review

### Requirement: Evidence-bearing lifecycle and resume
Source-only preparation and pre-start validation SHALL be repeatable without
empirical seed access. A setup or native-load failure before first seed access
MAY retry under the same immutable registration and authorization with a new
pre-start attempt record. The evidence-bearing logical identity SHALL begin
with a durable flushed write-ahead marker immediately before the first
registered seed reaches an environment factory. Absence of that marker SHALL
be required before any pre-seed retry.

#### Scenario: Failure occurs before first seed access
- **WHEN** exact source, runtime, isolation, process, or native pre-start work fails without constructing an empirical environment
- **THEN** the system records a pre-start failure and may retry the unchanged registration without consuming an empirical identity

#### Scenario: Infrastructure interruption occurs after seed access
- **WHEN** the process stops for an infrastructure reason after evidence-bearing start and a complete checkpoint exists
- **THEN** only the same logical identity may resume from that checkpoint with unchanged bytes, controls, cohorts, generator state, and coordinates, including deterministic replay of an incomplete chunk

#### Scenario: Algorithm or evidence gate fails after seed access
- **WHEN** legality, schema, numeric, support, collapse, canary, or terminal verification fails after evidence-bearing start
- **THEN** the identity is terminal and no retry, replacement seed, selected checkpoint, threshold change, coefficient change, or source repair is allowed

#### Scenario: Execution is active on Windows
- **WHEN** the authorized process is alive and owns its output lease
- **THEN** monitoring reads process liveness only and does not read files under the active output root until process exit

### Requirement: Independent publication and bounded verdicts
The system SHALL publish canonical journals, checkpoints, training diagnostics,
evaluations, model bytes, metrics, report, and manifest under the new identity.
A separate standard-library verifier SHALL validate canonical bytes, hashes,
source and cohort identity, coordinates, declared two-stage sampling metadata,
generator-state hash chains, coefficients, gates, resource accounting, holdout
access, verdict, and isolation without
importing the runner/runtime, Torch, native code, or an environment.

#### Scenario: Training stops before canary
- **WHEN** the registered training-family saturation gate fires
- **THEN** the verifier accepts only the matching negative verdict, complete durable prefix, zero canary/holdout access, and all-false downstream authority

#### Scenario: Canary stops before holdout
- **WHEN** any registered canary gate fails
- **THEN** the verifier accepts only `experiment_stopped_at_canary` with complete canary evidence and zero holdout access

#### Scenario: Holdout completes
- **WHEN** the registered holdout is structurally complete
- **THEN** the system reapplies the trained card-reward/shop family gates and independently classifies a victory signal, floor-only signal, or no-learning signal without granting policy quality, formal RL, target-supported outcomes, model loading, gameplay, qualification, or promotion

#### Scenario: Production isolation is checked
- **WHEN** terminal verification compares pre-start and post-exit isolation snapshots
- **THEN** CommunicationMod configuration and the complete production-checkpoint inventory are unchanged or the experiment is invalid
