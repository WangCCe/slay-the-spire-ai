# noncombat-card-acceptance-objective-architecture-contract Specification

## Purpose
Define the source-only card-reward policy architecture that separates explicit
family acceptance from conditional candidate choice, fixes their public APIs
and gradient ownership, publishes deterministic design evidence, and leaves
all empirical execution and policy-quality authority to a separate successor.

## Requirements

### Requirement: The card-reward policy has disjoint family and conditional heads
The system SHALL provide a source-only card-reward policy architecture with an
independent `family_head` and `conditional_ranker`, each an exact public
`StateConditionedCandidateRanker` instance. The two heads SHALL share no
trainable parameter object or storage and SHALL use exact checkpoint namespaces
`family_head.*` and `conditional_ranker.*`. Existing ranker, distribution,
objective, runtime, experiment, verifier, checkpoint, and production APIs SHALL
remain unchanged and SHALL NOT import this capability implicitly.

#### Scenario: A policy is constructed
- **WHEN** a valid input width and hidden width are supplied
- **THEN** both heads expose the bound public ranker metadata on CPU float32
- **AND** their parameter identities, storage, gradients, state-dict keys, and metadata namespaces are completely disjoint

#### Scenario: Existing modules are imported
- **WHEN** the current ranker, distribution, objective, consumed runtime, experiment, verifier, or production agent is imported without explicitly importing this capability
- **THEN** neither card-acceptance module is loaded or changes an existing API, checkpoint identity, or default behavior

#### Scenario: The new modules are imported in a fresh process
- **WHEN** only the card-acceptance policy and objective modules are imported
- **THEN** `analysis_scripts.noncombat_state_conditioned_policy_input`, `analysis_scripts.noncombat_simulator_adapter`, `analysis_scripts.noncombat_simulator_rl_experiment`, `analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime`, `analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment`, `analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment`, `spirecomm`, and `sts_lightspeed_noncombat_adapter` remain absent from loaded modules
- **AND** the public policy API accepts already projected state and candidate tensors rather than importing a projector

### Requirement: Family features and identities are canonical
The system SHALL validate one `card_reward` decision with unique nonempty
`action_id` and `kind` fields, finite aligned CPU float32 state and candidate
features, and at least one `take` candidate. It SHALL sort candidates within
each family by `action_id`, cast their candidate feature rows to float64, mean
them in that canonical order, verify the mean is finite and float32-representable,
convert it to float32, sort families lexicographically by exact `kind`, and
score every family without merging non-`take` identities.

#### Scenario: Take, skip, and bowl are offered
- **WHEN** a valid decision contains candidates from `take`, `skip`, and `bowl` families
- **THEN** the family head receives exactly three canonically ordered family-mean rows
- **AND** `skip` and `bowl` remain distinct non-`take` families

#### Scenario: Candidate input order changes
- **WHEN** candidates and aligned feature rows are permuted together
- **THEN** family identities, family-mean features, family logits, and action-aligned conditional logits are identical by action identity

#### Scenario: Finite float32 family rows have extreme magnitude
- **WHEN** one family contains repeated aligned feature rows at either finite float32 extreme
- **THEN** float64 accumulation produces a finite mean within the float32 range and checked conversion remains finite
- **AND** aggregation never performs an overflowing float32 sum

#### Scenario: The card-reward boundary is invalid
- **WHEN** the category differs, `take` is absent, an action ID is duplicated, a kind is empty, a tensor is nonfinite or has the wrong device or dtype, or rows are misaligned
- **THEN** construction fails before returning partial policy output

### Requirement: Acceptance is independent of conditional candidate logits
The system SHALL compute explicit family logits only with `family_head` and
conditional candidate logits only with `conditional_ranker`. For a multi-family
decision, the acceptance coordinate SHALL equal the `take` family logit minus
the log-sum-exp of every explicit non-`take` family logit, with both operands
cast to float64 before subtraction. For a single `take` family, family mass
SHALL be one and acceptance SHALL be marked inactive while conditional choice
remains live.

#### Scenario: Take, skip, and bowl logits define acceptance
- **WHEN** the sorted families are `bowl`, `skip`, and `take` with finite logits
- **THEN** acceptance equals `z_take - logsumexp(z_bowl, z_skip)` in float64
- **AND** family and joint probabilities retain all three identities through permutations and ties

#### Scenario: Only the take family logit changes
- **WHEN** a finite nonzero translation is applied to the `take` family logit while conditional logits remain fixed
- **THEN** take family mass and the acceptance coordinate change
- **AND** every within-family probability, order, margin, and unweighted per-family conditional entropy remains unchanged

#### Scenario: Only conditional logits change
- **WHEN** a finite within-`take` perturbation changes its conditional distribution while every family logit remains fixed
- **THEN** the acceptance coordinate and every family probability remain unchanged

#### Scenario: Only take candidates are legal
- **WHEN** every validated candidate belongs to `take`
- **THEN** take family mass is one, acceptance is inactive, and conditional probabilities equal an ordinary softmax over conditional logits

### Requirement: Explicit hierarchical policy terms are complete and finite
The system SHALL build family softmax over explicit sorted family logits,
separate conditional softmaxes over candidate logits within each family, and
joint candidate probabilities as their product. It SHALL expose selected
family, conditional, and joint log probabilities; family entropy; every
unweighted per-family conditional entropy; expected conditional entropy;
joint entropy; complete family and conditional greedy sets; and stable
action-identity alignment. Distribution computations SHALL be finite CPU
float64 over finite CPU float32 logits and preserve autograd.

#### Scenario: A selected action is resolved
- **WHEN** an exact selected action ID belongs to a valid multi-family decision
- **THEN** selected joint log probability equals selected family plus selected conditional log probability
- **AND** family and joint probabilities each sum to one and joint entropy equals family entropy plus expected conditional entropy within fixed tolerance

#### Scenario: A greedy maximum is tied
- **WHEN** multiple family logits tie or multiple conditional logits tie within a maximum family
- **THEN** every tied family and action ID is returned in lexicographic order
- **AND** the unique deterministic action is absent without using candidate input order as a tie-breaker

#### Scenario: Opposite finite float32 limits are supplied
- **WHEN** valid family and conditional logits include both finite float32 extremes
- **THEN** float64 acceptance, every exposed probability, log probability, entropy, and defined gradient remains finite

### Requirement: Policy-gradient ownership is exact
The system SHALL prove on the complete named parameter inventory that selected
family policy terms depend on no conditional parameter and selected conditional
policy terms and unweighted per-family conditional entropies depend on no
family parameter. Missing cross-head gradients and exact-zero cross-head
gradients SHALL both count as no dependency. Named unit family and conditional
component gradients SHALL reconstruct their summed gradient exactly in the
same ordered parameter space. Expected conditional and joint entropy SHALL be
reported as cross-head quantities and SHALL NOT be labeled owner-specific.

#### Scenario: Family policy is differentiated
- **WHEN** the negative selected family log probability is differentiated through the policy
- **THEN** at least one family-head gradient is finite and nonzero at a registered smooth fixture
- **AND** every conditional-ranker gradient is absent or exactly zero

#### Scenario: Conditional policy is differentiated
- **WHEN** the negative selected conditional log probability is differentiated through the policy
- **THEN** at least one conditional-ranker gradient is finite and nonzero at a registered smooth fixture
- **AND** every family-head gradient is absent or exactly zero

#### Scenario: Named policy components are combined
- **WHEN** unit family and conditional policy terms are differentiated separately and together at the same fixture
- **THEN** their ordered component gradients sum exactly to the combined gradient
- **AND** no loss coefficient, reward, return, advantage, optimizer, clipping rule, or update is selected by the contract

#### Scenario: Expected conditional entropy is inspected
- **WHEN** family probabilities are nondegenerate and conditional entropies differ by family
- **THEN** expected conditional entropy retains its mathematically required family-head dependence
- **AND** the report distinguishes it from unweighted per-family conditional entropy

### Requirement: Public APIs, schemas, reports, and authority are fixed
The policy module SHALL export `CardAcceptancePolicy`, `policy_metadata()`, and
`build_family_features()` under schema
`noncombat-card-acceptance-policy-v1`. The objective module SHALL export
`build_card_acceptance_policy_terms()`, `objective_metadata()`,
`build_contract_report()`, `canonical_json_bytes()`, and
`render_contract_markdown()` under objective schema
`noncombat-card-acceptance-objective-v1` and report schema
`noncombat-card-acceptance-objective-architecture-contract-report-v1`.
Neither module SHALL expose a loss, coefficient, reward, return, advantage,
optimizer, sampling, clipping, update, fitting, or execution API.

The policy constructor SHALL be `CardAcceptancePolicy(input_dim: int,
hidden_dim: int = DEFAULT_HIDDEN_DIM)`. Its forward signature SHALL be
`forward(state_features, candidate_features, candidates, *, category)` and
`build_family_features` SHALL accept `(candidate_features, candidates, *,
category)`. The category SHALL equal `card_reward`. `policy_metadata()` SHALL
take no arguments. The objective builder SHALL accept `(family_logits,
conditional_logits, candidates, selected_action_id, *, category)`;
`objective_metadata()` and `build_contract_report()` SHALL take no arguments;
and the two renderers SHALL each accept exactly one report mapping.

`FamilyFeatureBatch` SHALL have the exact ordered fields `action_ids`,
`candidate_families`, `family_order`, `family_candidate_indices`, and
`family_features`; the final tensor SHALL be CPU float32 shape `[F, D]` and the
index tuples SHALL align input rows to sorted families. `CardAcceptancePolicyOutput`
SHALL have the exact ordered fields `family_batch`, `conditional_logits`,
`family_logits`, `acceptance_active`, and `acceptance_coordinate`; logits SHALL
be CPU float32 shapes `[N]` and `[F]`, and active acceptance SHALL be a scalar
CPU float64 tensor, otherwise `None`.

`CardAcceptancePolicyTerms` SHALL have the exact ordered fields `action_ids`,
`candidate_families`, `family_order`, `selected_action_id`, `selected_index`,
`selected_family`, `selected_family_index`, `acceptance_active`,
`acceptance_coordinate`, `family_log_probabilities`, `family_probabilities`,
`conditional_log_probabilities`, `conditional_probabilities`,
`joint_log_probabilities`, `joint_probabilities`,
`selected_family_log_probability`, `selected_conditional_log_probability`,
`selected_joint_log_probability`, `family_entropy`,
`per_family_conditional_entropies`, `expected_conditional_entropy`,
`joint_entropy`, `greedy_family_ids`, `unique_greedy_family_id`,
`greedy_action_ids_by_family`, `two_stage_greedy_action_ids`, and
`unique_two_stage_greedy_action_id`. Probability, log-probability, acceptance,
and entropy tensors SHALL be CPU float64; family vectors SHALL have shape
`[F]`, candidate vectors `[N]`, per-family entropy `[F]`, and selected or total
terms SHALL be scalar. Greedy tuples SHALL be lexicographically ordered and
unique fields SHALL be nonempty strings only for singleton maxima, otherwise
`None`.

`policy_metadata()` SHALL contain exactly `acceptance_dtype`,
`aggregation_dtype`, `architecture_id`, `candidate_identity_field`,
`checkpoint_namespaces`, `device`, `family_aggregation`,
`family_identity_field`, `input_projection`, `model_dtype`, `output_type`,
`ranker_architecture_id`, and `schema_version`; instance architecture metadata
SHALL add exactly `input_dim` and `hidden_dim`. `objective_metadata()` SHALL
contain exactly `candidate_identity_field`, `coefficient_api`, `device`,
`entropy_terms`, `family_identity_field`, `input_logit_dtype`, `loss_api`,
`optimizer_api`, `output_type`, `schema_version`, `selected_terms`,
`term_dtype`, `tie_policy`, and `update_api`.

Policy metadata SHALL equal `acceptance_dtype="float64"`,
`aggregation_dtype="float64"`,
`architecture_id="disjoint-card-acceptance-heads-v1"`,
`candidate_identity_field="action_id"`, checkpoint namespaces
`{"conditional_ranker": "conditional_ranker.*", "family_head":
"family_head.*"}`, `device="cpu"`,
`family_aggregation="canonical-mean-projected-candidate-features-v1"`,
`family_identity_field="kind"`,
`input_projection="caller-supplied-preprojected-float32-v1"`,
`model_dtype="float32"`, `output_type="CardAcceptancePolicyOutput"`,
`ranker_architecture_id="state-conditioned-candidate-ranker-mlp-v1"`, and the
policy schema above. Objective metadata SHALL equal
`candidate_identity_field="action_id"`, `coefficient_api=false`,
`device="cpu"`, `entropy_terms=("family", "per_family_conditional",
"expected_conditional", "joint")`, `family_identity_field="kind"`,
`input_logit_dtype="float32"`, `loss_api=false`, `optimizer_api=false`,
`output_type="CardAcceptancePolicyTerms"`, the objective schema above,
`selected_terms=("family_log_probability", "conditional_log_probability",
"joint_log_probability")`, `term_dtype="float64"`,
`tie_policy="lexicographic-all-maxima-no-unique-on-tie-v1"`, and
`update_api=false`.

The canonical report SHALL have exactly `authority`, `contracts`,
`dependencies`, `future_empirical_entry`, `limitations`, and `schemas` as
top-level fields. The authority field SHALL contain exactly the following false
keys: `architecture_selection`, `causal_claim`, `coefficient_selection`, `cohort_materialization`,
`communication_mod`, `environment_construction`, `evaluation`, `execution`,
`fitting`, `formal_rl`, `gameplay`, `loss_construction`, `model_loading`,
`native_loading`, `objective_selection`, `ope`, `optimizer_selection`,
`policy_promotion`, `policy_quality`, `qualification`, `replay`,
`reward_selection`, `seed_access`, and `training`. Canonical JSON SHALL be no
larger than 131,072 bytes and Markdown no larger than 32,768 bytes. Repository
publication paths SHALL be exactly
`reports/noncombat_card_acceptance_objective_architecture_contract_20260809.json`
and the matching `.md`.

`schemas` SHALL contain exactly the string fields `objective`, `policy`, and
`report`. `dependencies` SHALL contain exactly `prohibited_modules` and
`required`; `required` SHALL contain only `ranker`, whose mapping has exactly
`architecture_id`, `class`, and `module`. `contracts` SHALL contain exactly
`architecture`, `objective`, and `synthetic_evidence`. Architecture SHALL
contain exactly `checkpoint_namespaces`, `family_aggregation`, `family_order`,
`input_projection`, and `parameter_sharing`; objective SHALL contain exactly
`acceptance_coordinate`, `entropy_decomposition`, `gradient_ownership`,
`probability_factorization`, and `tie_policy`; and synthetic evidence SHALL
contain exactly `fixture_ids` plus `invariants`, with boolean keys for
`acceptance_independent_of_conditional`, `conditional_independent_of_acceptance`,
`entropy_identity`, `expected_conditional_entropy_cross_head`,
`extremes_finite`, `family_gradient_isolated`, `family_permutation_invariant`,
`gradient_reconstruction_exact`, `parameter_identity_disjoint`,
`parameter_storage_disjoint`, `probability_normalized`, and
`conditional_gradient_isolated`.

Architecture contract values SHALL be the exact policy checkpoint,
aggregation, and projection values above plus
`family_order="lexicographic-kind"` and `parameter_sharing="none"`. Objective
contract values SHALL be
`acceptance_coordinate="z_take-logsumexp-all-explicit-non-take-families-float64-v1"`,
`entropy_decomposition="joint=family+expected_conditional"`,
`gradient_ownership="selected-family:family-head;selected-conditional:conditional-ranker;expected-conditional:cross-head-v1"`,
`probability_factorization="p(family)*p(candidate|family)"`, and the exact tie
policy above. Required ranker values SHALL be module
`analysis_scripts.noncombat_state_conditioned_ranker`, class
`StateConditionedCandidateRanker`, and architecture ID
`state-conditioned-candidate-ranker-mlp-v1`. Fixture IDs SHALL be the sorted
tuple `float32-extremes`, `permutation`, `take-only`, `take-skip-bowl`,
`take-skip-smooth`, and `ties`; every listed invariant SHALL be boolean.

`future_empirical_entry` SHALL contain exactly `authorization`, `canary`,
`holdout`, `prohibitions`, `required_bindings`, and `rollback`. Canary SHALL
contain exactly `at_most_once`, `family_only_shadow_step_required`,
`max_candidate_family_rate`, `paired_episodes`,
`selected_family_denominator_min`, `unique_greedy_denominator_min`,
`candidate_disabled_before_authorization`, `control_reproduction_required`,
and `minimum_family_identities_per_set`.
Holdout SHALL contain exactly `at_most_once`, `frozen_arms`, `paired_seeds`, and
`requires_canary_pass`. Rollback SHALL contain exactly `authority_required`,
`candidate_disabled`, `promotion_authority`, `target_binding_required`, and
`trigger_classes`. `limitations` SHALL equal the sorted tuple
`mean-family-features-lose-within-family-detail`,
`source-only-no-empirical-policy-quality`,
`two-head-checkpoints-require-new-identity`, and
`variable-family-sets-require-validation`.

Authorization SHALL equal `not-authorized-source-only-contract`.
`required_bindings` SHALL equal the sorted tuple
`candidate_checkpoint_sha256`, `candidate_config_sha256`,
`candidate_source_sha256`, `control_checkpoint_sha256`,
`control_config_sha256`, `control_source_sha256`, `seed_inventory_sha256`, and
`source_commit`. `prohibitions` SHALL equal the sorted tuple
`candidate-enable-before-authorization`, `post-canary-replacement`,
`post-canary-resume`, `post-canary-retry`, `post-canary-tuning`,
`post-canary-update`, and `seed-inventory-reuse`. Canary values SHALL be
`at_most_once=true`, `family_only_shadow_step_required=true`,
`max_candidate_family_rate=0.95`, `paired_episodes=128`,
`selected_family_denominator_min=64`, `unique_greedy_denominator_min=64`,
`candidate_disabled_before_authorization=true`,
`control_reproduction_required=true`, and
`minimum_family_identities_per_set=2`. Holdout values SHALL be
`at_most_once=true`, `frozen_arms=true`, `paired_seeds=512`, and
`requires_canary_pass=true`. Rollback values SHALL be
`authority_required=true`, `candidate_disabled=true`,
`promotion_authority=false`, `target_binding_required=true`, and the sorted
trigger tuple `authority`, `canary`, `holdout`, `identity`, `legality`,
`preflight`, and `publication`.

#### Scenario: Public surface and metadata are inspected
- **WHEN** callers inspect signatures, schema metadata, checkpoint namespaces, report fields, and authority
- **THEN** every exact parameter kind and order, return dataclass field, tensor shape/dtype, metadata key, and nested report field is present and no prohibited API or extra authority field exists
- **AND** dependency metadata binds only the public ranker identity plus this policy and objective contract

#### Scenario: Canonical reports are rendered
- **WHEN** one valid contract report is rendered as canonical JSON and Markdown
- **THEN** both outputs use the exact dated identities, stay within their fixed byte bounds, and contain no unrestricted tensors, parameter values, checkpoint bytes, or decision rows

### Requirement: Future empirical entry is preregistered without execution authority
The report SHALL require any future empirical successor to bind before canary
access: source commit; candidate and control source, checkpoint, and config
SHA-256 identities; seed-inventory SHA-256; candidate-disabled default; named
rollback authority; rollback triggers and exact control/production target;
paired canary count `128`; paired holdout seed count `512`; at-most-once canary
and holdout; and explicit no-tuning, no-replacement, no-resume, and no-retry
rules. These fields SHALL NOT materialize a cohort or authorize execution.

#### Scenario: A future candidate reaches canary planning
- **WHEN** a separate successor proposes a 128-paired-episode canary
- **THEN** candidate/control identities and seed inventory are frozen before access and exact control reproduction is judged only against registered control hashes and outputs
- **AND** candidate concentration uses candidate-arm valid multi-family card rewards as the selected-family denominator and candidate-arm unique-greedy-family decisions as the greedy denominator
- **AND** each denominator is at least 64, each family set contains at least two identities, and each maximum candidate family rate is no greater than `0.95`

#### Scenario: Canary passes every registered gate
- **WHEN** exact replay, legality, control reproduction, both candidate concentration gates, and a family-only shadow-step conditional-invariance gate all pass
- **THEN** one untouched 512-seed paired holdout may be requested under a separate authorization with both arms frozen and no update, tuning, replacement, resume, or retry
- **AND** this source-only contract still grants no seed access or execution

#### Scenario: A future gate fails
- **WHEN** any identity, legality, preflight, canary, holdout, publication, or authority gate fails
- **THEN** the registered rollback authority keeps the candidate disabled, restores and verifies the exact registered control/production configuration and checkpoint inventories, and grants no promotion

### Requirement: Synthetic evidence is deterministic and authority-free
The system SHALL publish compact deterministic metadata and design evidence
binding dependency identities, architecture, family aggregation, acceptance
definition, parameter and checkpoint namespaces, explicit-logit terms,
gradient ownership, registered edge cases, future successor entry conditions,
limitations, and the fixed all-false authority map. It SHALL satisfy the exact
prohibited-module set and report bounds defined above.

#### Scenario: Design evidence is reproduced
- **WHEN** the same checked-in source and registered synthetic fixtures are rendered twice in fresh processes
- **THEN** the canonical JSON and Markdown bytes are identical and within 131,072 and 32,768 bytes respectively
- **AND** all architecture/objective selection beyond this contract, fitting, training, replay, evaluation, OPE, model/native loading, seed access, gameplay, CommunicationMod, formal-RL, qualification, promotion, policy-quality, and causal authority remains false

#### Scenario: A future empirical successor is requested
- **WHEN** this contract is cited to request cohort materialization or execution
- **THEN** the request remains blocked pending a separate OpenSpec successor satisfying every fixed future-entry field with a new schema, checkpoint, output, control, seed inventory, canary, untouched paired holdout, rollback, publication, and explicit execution authorization
- **AND** the consumed r2 cohort, checkpoints, runtime, experiment, and verifier cannot be reused as fresh or blind evidence

#### Scenario: Source-only verification passes
- **WHEN** focused ownership and preservation tests, configured repository gates, strict OpenSpec validation, deterministic publication, and independent review pass
- **THEN** only the additive source-only architecture and objective contract is established
- **AND** fresh gameplay validation is not applicable because production and empirical imports remain unchanged
