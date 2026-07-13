## Context

The frozen non-combat policy pilot proved that canonical samples, grouped splits, candidate-masked training, and isolated artifacts work. Its evidence remains too weak for outcome learning: only 14 trajectories join uniquely to run outcomes, no joined run is a victory, and all 1,453 behavior probabilities are unknown. More deterministic Current or Bottled imitation would add labels but would not create the action overlap required for policy evaluation.

This change introduces the first live-facing data collection experiment. It must remain visibly separate from normal gameplay, preserve CommunicationMod compatibility, use the Windows production Python path, and fail back to the existing Current action whenever configuration, proposal construction, persistence, or execution confirmation is uncertain.

## Goals / Non-Goals

**Goals:**

- Represent a non-combat decision as a baseline action plus normalized, guard-approved alternatives without changing the baseline result.
- Sample an eligible alternative with an exact, reproducible behavior probability and retain enough provenance to replay the decision byte-for-byte.
- Confirm that the selected high-level action caused the expected game transition before exporting it as known-propensity evidence.
- Collect a bounded fresh batch with more independent trajectories and real action overlap than the frozen pilot.
- Report data readiness separately from OPE, reward readiness, formal RL, or live-policy promotion.

**Non-Goals:**

- No reward optimization, IPS/SNIPS/DR estimate, causal uplift claim, policy gradient, Q-learning, or formal non-combat RL.
- No automatic loading of the Current-imitation or Bottled-auxiliary pilot models.
- No runtime dependency on the Bottled checkout and no use of Bottled labels as live actions.
- No arbitrary alternative purchase, event, route, or card choice in the first executable experiment.
- No change to the default `optimized` or `combat_rl` behavior, CommunicationMod configuration, combat checkpoints, or checkpoint discovery.

## Decisions

### Add a proposal envelope beside the existing Current decision

`spirecomm/ai/noncombat_exploration.py` will own immutable proposal, candidate, configuration, distribution, and selection records. Existing decision surfaces continue to compute the Current action first. Because the legacy card-reward and shop callbacks also update tracker, decision-history, and shop-transition fields, an active executable category evaluates Current inside an action-scoped preview transaction. The wrapper captures the resulting Current state, restores the pre-callback state before sampling, and commits only the selected arm. CombatRL decision trace and expected-action recording are likewise deferred until that commit. A transaction failure fails closed to the Current action.

Category adapters map the previewed Current result and any permitted alternative into stable high-level candidate IDs without mutating agent state.

The first adapters cover `card_reward` and `shop`. Card rewards can propose `card_reward:skip` only when skipping is immediately legal. Shops can propose `shop:leave` only when an immediate leave, cancel, or proceed command can materialize the high-level action; post-purchase waits and transitional screens are ineligible. If the Current action is already the abstention action, cannot map uniquely, or has side effects during proposal construction, the controller records an ineligibility reason and returns it unchanged.

Event and route adapters may emit shadow proposals for coverage diagnostics, but the controller cannot execute their alternatives under this change. Enabling those categories or richer shop/card alternatives requires a later spec change with category-specific safety evidence.

Alternative: use Bottled or the frozen learned ranker as the second live policy. Rejected because that adds an external/runtime policy dependency or promotes an artifact whose manifest explicitly forbids live use.

Alternative: sample uniformly from all normalized candidates. Rejected because legality alone does not establish gameplay safety and would make early evidence needlessly destructive.

### Require an explicit immutable experiment configuration

Exploration is off when `STS_NONCOMBAT_EXPLORATION_CONFIG` is absent. The referenced JSON configuration contains a schema version, session ID, integer seed, enabled categories, category rates in basis points, per-run attempt budget, trace path, and manifest path. Code-level validation rejects rates above 1,000 basis points, budgets above two attempts per run, executable categories other than `shop` and `card_reward`, reused output paths, or missing provenance fields. Invalid configuration fails startup rather than silently clamping values.

`scripts/run_training_batch.py` may pass the configuration path through the child environment for an explicit bounded eval. It must not rewrite CommunicationMod `config.properties`. The effective configuration, source commit, tracked-clean state, command, Python executable, and hashes are frozen in a session manifest before the first run. A non-clean tracked worktree cannot start a qualification batch.

CommunicationMod isolation also records a semantic hash of the effective Java Properties mapping. Parsing follows Java's CR, LF, and CRLF natural-line rules, continuation and escape handling, and last-value-wins duplicate-key behavior. Comment, order, or timestamp-only rewrites may therefore compare equal, while any effective command or setting change remains detectable.

Alternative: add several independent command-line flags. Rejected because a single versioned configuration is easier to hash, review, replay, and associate with the resulting data.

### Use exact deterministic sampling

For an eligible binary proposal, the alternative receives `epsilon_bps / 10000` probability and the Current action receives the remainder. The sampler derives a 64-bit draw from SHA-256 over canonical `(schema, session_id, seed, trajectory_session_id, decision_index, state_hash)` input. Distribution records store exact integer numerators and denominators, the draw, input hash, selected action ID, and selected-action probability; floats are derived only for compatibility with the existing v2 sample field.

The state hash covers the normalized state and ordered candidate payload used to make the decision. Replaying the same proposal and configuration must reproduce the same distribution and selection. Replay-critical draw, probability, decision-index, and budget fields must be actual non-boolean JSON integers; numeric strings and floats are not coercible evidence. Duplicate candidate IDs, an invalid exact field, a distribution that does not sum exactly to one, or a selected action outside the candidate set makes the proposal ineligible.

Alternative: use process-global `random`. Rejected because retries and unrelated calls would change the sequence and prevent independent replay.

### Persist every sampled mixture action and confirm afterward

Every eligible mixture decision writes a `proposed` JSONL record before returning the sampled action, whether the draw selects Current or the alternative. This is required to measure both arms from the actual behavior policy. If the write fails, the controller returns the unmodified Current action and does not claim a known propensity. The per-run budget is consumed only when the alternative is selected, and is reserved before return so a rejected action cannot trigger repeated resampling.

On the next game-state callback, the controller resolves the pending record with a category-specific transition check and appends `confirmed`, `rejected`, `superseded`, or `terminal_unresolved`. Card selection requires the expected card/deck or reward-screen transition; skip requires leaving the reward screen without the card; shop purchase/removal requires the expected gold, inventory, or purge transition; shop leave requires leaving the shop screen. These checks apply to both sampled Current and alternative actions. Only a unique confirmed transition is exported as an executed known-propensity sample.

The proposal record embeds the existing compact decision snapshot and a stable decision ID. Resolution records reference that ID rather than copying mutable state. Append failures are visible in `ai_debug.log` and the session report. They never cause the alternative to be retried or a probability to be invented.

Alternative: treat the returned Python action as executed. Rejected because CommunicationMod may reject an action or expose an intermediate state, which would mislabel the actual behavior data.

### Keep exploration evidence and policy evidence separate

The canonical exporter adds an additive v3 exploration block while retaining v1/v2 readers. Confirmed records provide a session-scoped `behavior_policy_id=known-propensity-epsilon-v1:<session_id>`, exact candidate probabilities, selected probability, session/decision IDs, replay status, and source hashes. Shadow, rejected, unresolved, or unmatched rows remain diagnostic and cannot satisfy known-propensity support.

The offline validator recomputes state hashes, candidate uniqueness, distributions, draws, selections, confirmation joins, and `.run` joins. Its report includes unique trajectories, eligible and confirmed decisions, baseline/alternative support by category, propensity coverage, replay failures, outcome coverage, floor/killed-by distributions, and victories. Bottled and pilot predictions may be joined afterward as labels, but they do not alter behavior provenance.

### Qualify the data loop without authorizing OPE or RL

The first evidence gate requires at least 25 uniquely joined trajectories; 100 percent replay-valid distributions, selected-action probabilities, candidate legality, and confirmation joins for eligible executed decisions; and at least five confirmed baseline plus five confirmed alternative selections in every executable category. It also verifies that CommunicationMod configuration and combat checkpoints match the pre-session isolation snapshot.

Passing sets only `known_propensity_exploration_data_ready=true`. `ope_ready`, `causal_uplift_ready`, `formal_noncombat_rl_training_ready`, and `live_policy_promotion_ready` remain false. Reward design and any estimator-specific overlap/variance threshold belong to a later change.

## Risks / Trade-offs

- **Abstention-only support is narrow** -> Treat it as instrumentation evidence, not a generally improved policy; richer alternatives require a later gated change.
- **Low epsilon may require many runs to reach five alternative selections** -> Use a bounded batch and report the shortfall rather than raising the hard 10 percent ceiling.
- **Action confirmation can be ambiguous across transitional screens** -> Exclude ambiguous records and add category fixtures from fresh traces before broadening eligibility.
- **Previewing Current can leak baseline bookkeeping into the alternative arm** -> Snapshot only action-scoped card/shop policy state, roll it back before sampling, commit the selected arm once, and regression-test both SimpleAgent and CombatRL trace behavior.
- **Trace persistence can fail while gameplay continues** -> Fail closed to Current before any alternative is returned and expose persistence failures in logs and reports.
- **A qualified batch could be mistaken for OPE readiness** -> Emit separate readiness fields with permanent false values for OPE, causal claims, formal RL, and promotion.

## Migration Plan

1. Add proposal, configuration, exact sampler, and replay tests without wiring live actions.
2. Add shadow adapters and prove that exploration-off and shadow-only outputs equal the existing Current actions on focused fixtures.
3. Add append-only proposal/resolution records and synthetic confirmation/replay tests.
4. Wire the explicit environment/config path and run dry-run plus focused smoke checks with zero exploration probability.
5. Enable a small shop/card-reward smoke batch inside the hard safety envelope, inspect fresh logs and transitions, then run the bounded evidence batch.
6. Export and freeze only confirmed records, produce the qualification report, run focused and full pytest plus strict OpenSpec validation, and preserve an isolation hash snapshot.

Rollback removes the explicit environment setting and exploration-only records. Because the default path does not wrap or replace Current decisions, no checkpoint, policy artifact, or CommunicationMod migration is required.

## Open Questions

- Whether to expand beyond abstention actions, enable event/route execution, or implement an OPE estimator is intentionally deferred until this batch quantifies real overlap, rejection rate, trajectory count, outcome diversity, and variance risk.
