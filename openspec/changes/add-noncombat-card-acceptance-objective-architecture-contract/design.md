## Context

The current non-combat hierarchy uses one
`StateConditionedCandidateRanker`. Candidate scores are both conditional logits
and inputs to max-pooled family logits. The runtime records separate family and
conditional loss components, but both update the same ordered parameter set.
The item 58 audit found persistent acceptance pressure with mixed direct
conditional pressure; item 59 found recorded family/conditional gradient
conflicts only in chunks 1 and 4 and proved a separate acceptance coordinate in
synthetic score space. Neither audit selected an architecture or authorized a
run.

Card rewards are not always a binary `take/skip` surface. Existing fixtures
include explicit `bowl`, `skip`, and `take` families. Any architecture that
collapses every non-`take` family into one label would lose legal-action
identity and invalidate existing candidate semantics.

This change is additive and source-only. Its public API accepts already
projected tensors; it must not import the state-conditioned policy-input
projector because that projector transitively imports the simulator adapter and
simulator RL experiment. It also must not import or modify the consumed
cross-fitted experiment/runtime/verifier, load model/native state, or enter
production imports.

## Goals / Non-Goals

**Goals:**

- Define a concrete card-reward architecture with disjoint family and
  conditional trainable parameter sets.
- Make family logits independent of conditional candidate logits while keeping
  every observed `kind` explicit.
- Expose complete hierarchical probability, entropy, greedy-set, and selected
  objective terms without defining a loss or coefficient.
- Prove score-coordinate invariants and parameter-gradient ownership with
  deterministic synthetic fixtures.
- Bind architecture/checkpoint metadata tightly enough that a later successor
  cannot reuse a consumed checkpoint or verifier identity.
- State the minimum structural, empirical, rollback, and authority boundaries
  that any later successor proposal must preregister.

**Non-Goals:**

- Modify the v1 max-pooled distribution, v1 hierarchical objective, existing
  candidate ranker, policy input, formal reward, advantage contract, consumed
  runtime, experiment, verifier, checkpoint, or production agent.
- Select a family or conditional policy-loss coefficient, entropy objective,
  optimizer, initialization, baseline, reward, cohort, or promotion threshold.
- Fit, train, replay, evaluate, run OPE, access seeds, load native/model state,
  launch gameplay or CommunicationMod, qualify, or promote.
- Claim that score-space or parameter isolation improves policy value.

## Decisions

### Add a parallel card-reward contract instead of changing v1 APIs

The new modules will not extend the positional signatures or metadata of
`build_action_family_distribution`, `build_hierarchical_policy_terms`, or
`StateConditionedCandidateRanker`. They form a parallel v1 card-acceptance
contract that binds those public dependencies by exact metadata.

Alternative: add optional explicit family logits to the existing distribution.
Rejected because optional modes would change a completed public contract and
make consumed-runtime preservation harder to prove.

### Use two separate ranker instances with canonical family-mean features

`CardAcceptancePolicy` will own:

- `conditional_ranker`: an unchanged `StateConditionedCandidateRanker` scoring
  each candidate feature row.
- `family_head`: a second independent `StateConditionedCandidateRanker` scoring
  one feature row per exact candidate `kind`.

For each family, candidates are first sorted by `action_id`; their finite CPU
float32 feature rows are cast to float64, averaged in that canonical order, and
converted back to float32 only after the result is checked finite and within
the float32 range. Families are sorted lexicographically by `kind`. The supplied
preprojected state feature vector and the family mean are passed to
`family_head`. Float64 accumulation prevents repeated finite float32 extremes
from overflowing during aggregation; mean aggregation avoids cardinality
scaling, and canonical ordering makes input permutation reproducible.

The two modules may use the same class and receive the same immutable state
tensor, but no `Parameter` object, storage, optimizer slot, gradient ledger
entry, or checkpoint key may be shared. State dict namespaces are fixed as
`family_head.*` and `conditional_ranker.*`.

Alternative: share a trainable trunk and split only the final layers. Rejected
because score outputs would be separate but parameter updates could still
interfere through the trunk.

Alternative: add one uniform `take` offset to max-pooled candidate scores.
Rejected because the family logit would still depend on the maximum conditional
score and family-policy gradients would still update the winning candidate.

### Treat every candidate kind as an explicit family

The family head scores all observed kinds, including `take`, `skip`, and
`bowl`. A valid multi-family card reward must contain `take`; non-`take`
families are not merged. The acceptance coordinate is

`z_take - logsumexp(z_f for f != take)`, computed after casting every finite
family logit to float64. The registered `take/skip/bowl` fixture therefore uses
exactly `z_take - logsumexp(z_skip, z_bowl)`.

For a single `take` family, family mass is one and the acceptance coordinate is
inactive while conditional choice remains live. A card-reward surface without
`take`, duplicate action IDs, empty kinds, or misaligned features fails closed.

Alternative: binary `take` versus `not_take`. Rejected because it erases legal
family identity and cannot represent `bowl` independently.

### Build probabilities from explicit family and conditional logits

The objective module consumes family logits aligned to sorted family IDs and
conditional logits aligned to candidates. It computes family softmax, a
separate conditional softmax within each family, and joint candidate
probabilities as their product. It exposes:

- selected family, conditional, and joint log probabilities;
- family entropy;
- each family's unweighted conditional entropy;
- expected conditional entropy weighted by family probability;
- joint entropy and its exact decomposition;
- complete maximum-family and within-family maximum-action sets.

Deterministic greedy metadata follows max family logit, then max conditional
logit within that family. Any family or conditional tie leaves the unique
action absent. It does not reuse the old raw-candidate-score equivalence.

### Keep gradient ownership claims narrower than entropy decomposition

The selected family log probability depends only on `family_head` parameters;
the selected conditional log probability and every unweighted per-family
conditional entropy depend only on `conditional_ranker` parameters. Synthetic
backward checks require absent or exact-zero cross-head gradients and exact
reconstruction of the summed named unit policy components.

Expected conditional entropy equals
`sum_f p(family=f) * H(candidate|f)` and therefore depends on both heads. Joint
entropy also depends on both. The contract exposes these mathematically useful
quantities but grants them no owner-specific objective status and selects no
entropy regularizer.

Alternative: claim expected conditional entropy is a conditional-only term.
Rejected because changing acceptance mass changes its family weights.

### Publish deterministic synthetic evidence with no empirical authority

The source-only report will bind dependency metadata, architecture and
checkpoint namespaces, family aggregation, acceptance definition, probability
identities, gradient ownership, edge-case fixtures, prohibited imports, future
successor entry conditions, and an exact all-false authority map. Repeated
rendering must be byte-identical. Canonical JSON is limited to 131,072 bytes
and Markdown to 32,768 bytes.

The public surface is fixed before RED tests:

- policy schema `noncombat-card-acceptance-policy-v1` with
  `CardAcceptancePolicy`, `policy_metadata()`, and `build_family_features()`;
- objective schema `noncombat-card-acceptance-objective-v1` with
  `build_card_acceptance_policy_terms()` and `objective_metadata()`;
- report schema
  `noncombat-card-acceptance-objective-architecture-contract-report-v1` with
  `build_contract_report()`, `canonical_json_bytes()`, and
  `render_contract_markdown()`.

The exact Python signatures are:

- `CardAcceptancePolicy(input_dim: int, hidden_dim: int = DEFAULT_HIDDEN_DIM)`;
- `CardAcceptancePolicy.forward(state_features: torch.Tensor,
  candidate_features: torch.Tensor, candidates:
  Sequence[Mapping[str, Any]], *, category: str) ->
  CardAcceptancePolicyOutput`;
- `build_family_features(candidate_features: torch.Tensor, candidates:
  Sequence[Mapping[str, Any]], *, category: str) -> FamilyFeatureBatch`;
- `policy_metadata() -> dict[str, Any]`;
- `build_card_acceptance_policy_terms(family_logits: torch.Tensor,
  conditional_logits: torch.Tensor, candidates:
  Sequence[Mapping[str, Any]], selected_action_id: str, *, category: str) ->
  CardAcceptancePolicyTerms`;
- `objective_metadata() -> dict[str, Any]`;
- `build_contract_report() -> dict[str, Any]`;
- `canonical_json_bytes(report: Mapping[str, Any]) -> bytes`; and
- `render_contract_markdown(report: Mapping[str, Any]) -> str`.

`FamilyFeatureBatch` contains, in order, `action_ids`,
`candidate_families`, `family_order`, `family_candidate_indices`, and
`family_features`. Identity fields are tuples of strings,
`family_candidate_indices` is a tuple of tuples of input-row indices aligned to
`family_order`, and `family_features` is finite CPU float32 shape `[F, D]`.
`CardAcceptancePolicyOutput` contains, in order, `family_batch`,
`conditional_logits`, `family_logits`, `acceptance_active`, and
`acceptance_coordinate`; logits are finite CPU float32 shapes `[N]` and `[F]`,
and acceptance is a scalar CPU float64 tensor when active and `None` otherwise.

`CardAcceptancePolicyTerms` contains, in order: `action_ids`,
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
`unique_two_stage_greedy_action_id`. All probability, log-probability,
acceptance, and entropy tensors are CPU float64; family vectors have shape
`[F]`, candidate vectors `[N]`, per-family entropy `[F]`, and selected or total
terms are scalar. Greedy collections are lexicographically ordered tuples;
`greedy_action_ids_by_family` is a tuple of `(family, action_ids)` pairs aligned
to `family_order`; unique fields are strings only for singleton maxima and
otherwise `None`.

`policy_metadata()` has exactly `acceptance_dtype`, `aggregation_dtype`,
`architecture_id`, `candidate_identity_field`, `checkpoint_namespaces`,
`device`, `family_aggregation`, `family_identity_field`, `input_projection`,
`model_dtype`, `output_type`, `ranker_architecture_id`, and `schema_version`.
The instance `architecture_metadata()` adds exactly `input_dim` and
`hidden_dim`. `objective_metadata()` has exactly `candidate_identity_field`,
`coefficient_api`, `device`, `entropy_terms`, `family_identity_field`,
`input_logit_dtype`, `loss_api`, `optimizer_api`, `output_type`,
`schema_version`, `selected_terms`, `term_dtype`, `tie_policy`, and
`update_api`.

The policy metadata values are fixed as: `acceptance_dtype="float64"`,
`aggregation_dtype="float64"`,
`architecture_id="disjoint-card-acceptance-heads-v1"`,
`candidate_identity_field="action_id"`,
`checkpoint_namespaces={"conditional_ranker": "conditional_ranker.*",
"family_head": "family_head.*"}`, `device="cpu"`,
`family_aggregation="canonical-mean-projected-candidate-features-v1"`,
`family_identity_field="kind"`,
`input_projection="caller-supplied-preprojected-float32-v1"`,
`model_dtype="float32"`, `output_type="CardAcceptancePolicyOutput"`,
`ranker_architecture_id="state-conditioned-candidate-ranker-mlp-v1"`, and
`schema_version="noncombat-card-acceptance-policy-v1"`. The objective values
are fixed as: `candidate_identity_field="action_id"`,
`coefficient_api=false`, `device="cpu"`, `entropy_terms=("family",
"per_family_conditional", "expected_conditional", "joint")`,
`family_identity_field="kind"`, `input_logit_dtype="float32"`,
`loss_api=false`, `optimizer_api=false`,
`output_type="CardAcceptancePolicyTerms"`,
`schema_version="noncombat-card-acceptance-objective-v1"`,
`selected_terms=("family_log_probability", "conditional_log_probability",
"joint_log_probability")`, `term_dtype="float64"`,
`tie_policy="lexicographic-all-maxima-no-unique-on-tie-v1"`, and
`update_api=false`.

The report top-level fields are exactly `authority`, `contracts`,
`dependencies`, `future_empirical_entry`, `limitations`, and `schemas`.
Authority contains the fixed all-false inventory from the capability spec.
`schemas` has exactly `objective`, `policy`, and `report` string fields.
`dependencies` has exactly `prohibited_modules` and `required`; `required` has
one `ranker` mapping with exactly `architecture_id`, `class`, and `module`.
`contracts` has exactly `architecture`, `objective`, and
`synthetic_evidence`. `architecture` has exactly `checkpoint_namespaces`,
`family_aggregation`, `family_order`, `input_projection`, and
`parameter_sharing`; `objective` has exactly `acceptance_coordinate`,
`entropy_decomposition`, `gradient_ownership`, `probability_factorization`,
and `tie_policy`; `synthetic_evidence` has exactly `fixture_ids` and
`invariants`, with a fixed boolean inventory for parameter identity/storage
isolation, permutation, coordinate isolation, normalization, entropy identity,
family/conditional gradient isolation, gradient reconstruction,
expected-conditional cross-head dependence, and finite extremes.
The architecture values are the policy checkpoint/aggregation/projection
values above plus `family_order="lexicographic-kind"` and
`parameter_sharing="none"`. The objective values are
`acceptance_coordinate="z_take-logsumexp-all-explicit-non-take-families-float64-v1"`,
`entropy_decomposition="joint=family+expected_conditional"`,
`gradient_ownership="selected-family:family-head;selected-conditional:conditional-ranker;expected-conditional:cross-head-v1"`,
`probability_factorization="p(family)*p(candidate|family)"`, and the metadata
tie policy above. Dependency `ranker` is exactly module
`analysis_scripts.noncombat_state_conditioned_ranker`, class
`StateConditionedCandidateRanker`, and architecture ID
`state-conditioned-candidate-ranker-mlp-v1`; `prohibited_modules` is the sorted
tuple from the fresh-process requirement. Fixture IDs are exactly the sorted
tuple `float32-extremes`, `permutation`, `take-only`, `take-skip-bowl`,
`take-skip-smooth`, and `ties`; invariant keys are exactly the twelve keys in
the capability spec and every value is boolean.
`future_empirical_entry` has exactly `authorization`, `canary`, `holdout`,
`prohibitions`, `required_bindings`, and `rollback`; canary has exactly
`at_most_once`, `family_only_shadow_step_required`,
`max_candidate_family_rate`, `paired_episodes`,
`selected_family_denominator_min`, `unique_greedy_denominator_min`,
`candidate_disabled_before_authorization`, `control_reproduction_required`,
and `minimum_family_identities_per_set`;
holdout has exactly `at_most_once`, `frozen_arms`, `paired_seeds`, and
`requires_canary_pass`; rollback has exactly `authority_required`,
`candidate_disabled`, `promotion_authority`, `target_binding_required`, and
`trigger_classes`. `limitations` is the fixed sorted tuple of
`mean-family-features-lose-within-family-detail`,
`source-only-no-empirical-policy-quality`,
`two-head-checkpoints-require-new-identity`, and
`variable-family-sets-require-validation`.
Authorization is the exact string `not-authorized-source-only-contract`.
`required_bindings` is the sorted tuple `candidate_checkpoint_sha256`,
`candidate_config_sha256`, `candidate_source_sha256`,
`control_checkpoint_sha256`, `control_config_sha256`,
`control_source_sha256`, `seed_inventory_sha256`, and `source_commit`.
`prohibitions` is the sorted tuple `candidate-enable-before-authorization`,
`post-canary-replacement`, `post-canary-resume`, `post-canary-retry`,
`post-canary-tuning`, `post-canary-update`, and `seed-inventory-reuse`.
Canary values are `at_most_once=true`,
`family_only_shadow_step_required=true`, `max_candidate_family_rate=0.95`,
`paired_episodes=128`, `selected_family_denominator_min=64`,
`unique_greedy_denominator_min=64`,
`candidate_disabled_before_authorization=true`,
`control_reproduction_required=true`, and
`minimum_family_identities_per_set=2`. Holdout values are true, true, `512`,
and true in field order. Rollback values are true, true, false, true, and the
sorted tuple `authority`, `canary`, `holdout`, `identity`, `legality`,
`preflight`, and `publication` for `trigger_classes`.
Canonical repository names are
`reports/noncombat_card_acceptance_objective_architecture_contract_20260809.json`
and the matching `.md`.

Synthetic fixtures cover `take/skip`, `take/skip/bowl`, one-family `take`,
candidate permutations, tied family and conditional maxima, opposite finite
float32 limits, acceptance-only and conditional-only perturbations, and
non-aliased backward passes.

### Defer empirical ownership to a separate successor change

This contract registers no seeds or execution. A later successor proposal must
use a new architecture/schema/checkpoint/output identity and fresh paired
control/candidate cohorts disjoint from r2 and every historical holdout. Its
minimum plan is:

1. Before canary access, bind source, candidate/control checkpoint, config, and
   seed-inventory hashes; keep the candidate disabled by default; name the
   rollback authority, triggers, and exact control/production target; and forbid
   post-canary tuning, replacement, resume, or retry.
2. Run one at-most-once 128-paired-episode structural canary. Exact control
   reproduction is evaluated only against its registered hashes and outputs.
   Candidate concentration uses candidate-arm valid multi-family card-reward
   decisions as the selected-family denominator and candidate-arm decisions
   with a unique greedy family as the greedy denominator. Each denominator must
   be at least 64; each observed family set must contain at least two identities;
   and each maximum family rate must be no greater than `0.95`. A registered
   family-only shadow step must preserve conditional quantities.
3. Only after every canary gate passes, run one untouched 512-seed paired
   holdout with both hashes frozen and no update, replacement, tuning, resume,
   or retry.
4. Any identity, legality, preflight, canary, holdout, publication, or authority
   failure triggers rollback: leave the candidate disabled, restore and verify
   the exact registered control/production configuration and checkpoint
   inventories, and grant no promotion. Report structural, mechanism, floor,
   and victory classifications separately. Victory remains primary; mechanism
   completion is not policy quality.

Those numbers and predicates are planning requirements for a future proposal,
not execution authorization from this change.

## Risks / Trade-offs

- [Risk] Mean family features lose within-family detail. -> Keep the limitation
  explicit; this contract proves separation, not optimal representation, and a
  later architecture change requires a new proposal.
- [Risk] Two heads increase parameter and checkpoint size. -> Use the existing
  small ranker class and exact disjoint namespaces; do not migrate or overwrite
  old checkpoints.
- [Risk] Dynamic family sets create inconsistent identities. -> Derive exact
  sorted kinds from validated candidates and fail on missing `take`, duplicates,
  empty kinds, or alignment drift.
- [Risk] Float32 aggregation or acceptance arithmetic overflows on finite
  extremes. -> Accumulate family means and compute log-sum-exp acceptance in
  float64, range-check conversion, and fail closed on nonfinite head outputs.
- [Risk] Expected conditional entropy is mistaken for conditional-only
  ownership. -> Expose per-family and expected forms separately and test the
  expected form's cross-head dependence.
- [Risk] Synthetic isolation is treated as expected performance. -> Keep all
  fitting, execution, evaluation, policy-quality, and causal authority false;
  require a separate empirical successor.
- [Risk] New tests worsen commit-gate latency. -> Run focused ownership tests
  first and change tier inventory only through a separate measured gate change
  if the repository profile requires it.

## Migration Plan

1. Commit and push the complete reviewed planning boundary.
2. Add RED architecture, explicit-logit, gradient-ownership, edge-case,
   deterministic-report, import-isolation, and preservation tests.
3. Implement the two source-only modules over preprojected tensors without
   changing existing APIs or importing policy-input/runtime surfaces.
4. Run focused tests, direct preservation coverage, the configured repository
   gates once per phase, strict OpenSpec validation, and independent review.
5. Publish the compact design report, update project direction, sync and
   archive the change, then stop before empirical registration.

Rollback removes only this capability's source, tests, report, spec, archived
change, and direction entry. There is no production rollout or checkpoint
migration to reverse.

## Open Questions

There are no implementation-blocking questions for the source-only contract.
A future successor must separately choose initialization, objective
coefficients, optimizer ownership, paired seed inventory, statistical
noninferiority thresholds, runtime budgets, and execution authorization.
