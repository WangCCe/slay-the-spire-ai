## ADDED Requirements

### Requirement: Hybrid rollout roles are exact
The pilot SHALL use native SimpleAgent for every non-card candidate action, use
the hierarchical card policy only for candidate card rewards, and use native
SimpleAgent for every control action. Candidate and control SHALL run in
separate environments constructed from the same ordered seed.

#### Scenario: Candidate reaches a non-card decision
- **WHEN** a candidate trajectory reaches route, shop, or event candidates
- **THEN** the runner queries the source-preserving native baseline action and applies the exactly mapped legal action
- **AND** no learned non-card ranker or fallback selects the action

#### Scenario: Control reaches any decision
- **WHEN** a control trajectory reports any supported target category
- **THEN** the runner queries and applies the exactly mapped native baseline action
- **AND** no control optimizer, model update, or candidate output influences the choice

#### Scenario: Native baseline mapping is invalid
- **WHEN** a native query mutates its source, returns an absent action, maps ambiguously, or fails during application
- **THEN** the pilot blocks the current run without synthesizing a fallback action

### Requirement: Bottled card warm start is isolated and gated
The pilot SHALL derive card-only train and validation rows from the existing
archived SimpleAgent demonstration corpus, relabel them with one bound clean
Bottled `REQUESTED_STRIKE` checkout, and SHALL NOT read the prior warm-start
final-test rows. Bottled labels SHALL be auxiliary supervised initialization,
not reward or permanent policy truth.

#### Scenario: Archived card rows are relabeled
- **WHEN** the pilot reads the 302 train and 175 validation card rows
- **THEN** every row maps one Bottled result to exactly one reported action id with complete source state, deck, offered-card, candidate, and provenance identity
- **AND** the report records take, skip, bowl, confidence, mapping, and SimpleAgent-disagreement counts

#### Scenario: Hierarchical warm start trains
- **WHEN** all train rows and source bindings validate
- **THEN** one fixed deterministic schedule trains family cross entropy and selected-family conditional cross entropy on the current hierarchical card heads
- **AND** no simulator reward, outcome, validation label, SimpleAgent card label, or protected seed changes an optimizer step

#### Scenario: Warm-start validation passes
- **WHEN** the frozen model is evaluated once on all 175 validation card rows
- **THEN** family agreement is at least 0.70 and at least 0.10 above zero-step, exact action agreement is at least 0.50, all rows map legally, and greedy take and non-take rates are each between 0.05 and 0.95 inclusive

#### Scenario: Warm-start validation fails
- **WHEN** any mapping, identity, determinism, support, agreement, or coverage gate fails
- **THEN** the pilot publishes the failure and performs no policy-gradient rollout or update
- **AND** it does not change the model, schedule, threshold, corpus, or label source under this change

### Requirement: Residual training is candidate-card-only and bounded
After the warm-start gate passes, the pilot SHALL run at most four complete
64-pair attempted cohorts on exactly the already-consumed seeds `1000..1031`
and `2000..2031`. It MAY censor at most eight pairs that hit only the declared
Courier-restock simulator blocker and SHALL update on 56 to 64 supported pairs.
Only candidate card parameters and optimizer moments SHALL change.

#### Scenario: One residual chunk completes
- **WHEN** one 64-seed attempt yields at least 56 complete supported candidate/native-control pairs within the fixed deadline and four-fold candidate baseline contract
- **THEN** the runner applies exactly one candidate Adam step from card-reward advantages, writes a restorable complete-boundary checkpoint, and records zero control optimizer steps

#### Scenario: Declared Courier blocker is censored
- **WHEN** either arm of a pair reaches `unsupported_shop_courier_restock_semantics`
- **THEN** the whole pair is excluded from the update and its seed, arm, category, decision id, and reason are reported
- **AND** the runner does not retry the seed, replace it, or consume a new seed

#### Scenario: Fixed probe detects boundary concentration
- **WHEN** a completed chunk makes frozen greedy take or non-take coverage on the pre-RL source-state probe fall below 0.05 or exceed 0.95
- **THEN** training stops before another environment access and preserves the last complete checkpoint

#### Scenario: Residual execution becomes invalid
- **WHEN** a chunk has more than eight censored pairs, an unknown support blocker, fewer than 56 supported pairs, an invalid gradient or reward, an exceeded deadline or resource bound, or checkpoint restore differs
- **THEN** the pilot stops without retrying, changing seeds, tuning, or loading a partial checkpoint

### Requirement: Development comparison has a strict no-go boundary
The pilot SHALL compare one frozen final candidate against native SimpleAgent on
the same consumed development cohort. This comparison SHALL determine only
whether a separate fresh-evaluation proposal is justified.

#### Scenario: Development proposal gate passes
- **WHEN** all 64 frozen pairs complete with zero unsupported episodes, candidate victories are at least control victories, candidate mean floor progress is at least control mean floor progress, and candidate greedy take coverage is between 0.05 and 0.95 inclusive
- **THEN** the verdict is `ready_to_propose_fresh_card_only_evaluation`
- **AND** no fresh evaluation, qualification, promotion, or live loading starts under this change

#### Scenario: Development proposal gate fails
- **WHEN** any frozen comparison or coverage condition fails
- **THEN** the verdict is `card_only_native_baseline_pilot_not_ready`
- **AND** native SimpleAgent remains the rollback baseline without another pilot run

### Requirement: Artifacts remain exploratory and non-production
The pilot SHALL publish a compact source-bound registration, warm-start report,
complete chunk summaries, final checkpoint, frozen comparison, and terminal
verdict outside production checkpoint discovery. Every artifact SHALL keep all
formal, live, holdout, qualification, promotion, and policy-quality authority
false.

#### Scenario: Pilot publishes successfully
- **WHEN** the warm-start and optional residual stages reach a terminal boundary
- **THEN** canonical artifacts bind source, native module, Bottled checkout, corpus, cohorts, configuration, checkpoints, resources, and stop reason
- **AND** CommunicationMod configuration, game processes, live logs, and production checkpoints remain unchanged

#### Scenario: Exploratory candidate is rolled back
- **WHEN** the pilot fails or is not promoted by a later separately approved change
- **THEN** no loader discovers the exploratory checkpoint and native SimpleAgent behavior remains available without migration
