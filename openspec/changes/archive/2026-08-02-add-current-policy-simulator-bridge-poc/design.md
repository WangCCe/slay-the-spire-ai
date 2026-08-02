## Context

The simulator adapter exposes rich JSON snapshots and stable legal candidate IDs for route, shop, event, and card-reward decisions, but it currently exposes only the native C++ SimpleAgent as an executable policy. The repository's Current policy is `OptimizedAgent`; its non-combat logic expects Communication Mod model objects, reads static card/relic/potion metadata, and retains route and shop state across decisions. The prior warm-start and structured-ranker studies validly showed that another SimpleAgent imitation pass is not a credible path to the required baseline floor.

This change is analysis-only. It uses frozen simulator demonstrations first and does not alter production gameplay, the native adapter, reward, training, or promotion code.

## Goals / Non-Goals

**Goals:**

- Reuse the exact Current non-combat decision implementation rather than porting its heuristics.
- Hydrate simulator snapshots into the minimum Communication Mod object graph with explicit source and metadata provenance.
- Map a Current action to exactly one legal adapter candidate or fail closed with a classified reason.
- Demonstrate deterministic, non-mutating structural behavior on frozen rows across all four target categories.
- Preserve one Current agent per episode and gate any own-trajectory compatibility check behind the frozen-row result.
- Publish a hash-closed verdict whose authority is limited to bridge compatibility.

**Non-Goals:**

- Training, imitation, reward optimization, hyperparameter tuning, or policy promotion.
- Treating Current, Bottled, SimpleAgent, agreement, or HP/floor heuristics as reward truth.
- Claiming a credible baseline floor, policy improvement, outcome support, or formal-RL readiness.
- Consuming untouched seeds, launching live gameplay, or changing Communication Mod configuration.
- Rewriting Current policy logic inside the bridge.

## Decisions

### Invoke the exact screen-specific Current path

The bridge will instantiate `OptimizedAgent(PlayerClass.IRONCLAD, elite_mode=<bound mode>)`, immediately disable `game_tracker`, bind a hydrated `Game`, and invoke `handle_screen()` only for a declared target category. It will reject any optimized-component downgrade or call path that resolves to `SimpleAgent` fallback. Calling the screen-specific entry point avoids gameplay callbacks and tracker lifecycle side effects while retaining the production non-combat implementation.

Alternative considered: copy Current scoring rules into an independent simulator policy. Rejected because two implementations would drift and any agreement result would not validate the production policy.

### Hydrate a minimum, validated object graph

The bridge will convert the adapter's cards, relics, potions, map nodes, screen context, run resources, and legal choices into existing `spirecomm.spire` model objects or narrow compatible screen objects. Static fields absent from the adapter snapshot will come only from a registered and SHA-256-bound `items.json`; no heuristic default may influence a decision unless the field is proven irrelevant by tests. Input snapshots and candidate arrays will be deep-copied and canonical-hashed before and after invocation.

Event rows require event identity, legal option count, and the semantic labels read by Current. Because the current adapter records only generic option labels, those rows will fail with `missing_event_option_semantics` unless an exact source-bound label mapping exists. They will not be converted to index-only decisions.

Alternative considered: fill missing event text with `option 0`, `option 1`, and so on. Rejected because Current deliberately searches semantic keywords for several events.

### Map by category-specific stable identity

Route actions map by node coordinates. Card rewards map by source card slot/object identity, with distinct bowl and skip handling. Shop actions map by kind and slot/object identity; name-only matches are invalid when duplicate names are possible. Event actions map by enabled option index only after semantic hydration succeeds. Leave, purge, bowl, and skip are explicit candidate kinds. Zero or multiple matches are hard failures.

Alternative considered: map by display name first. Rejected because duplicate shop/card names make that non-identifying.

### Maintain episode-local Current state

The bridge exposes a session keyed by registered episode identity. It creates exactly one agent for that episode and applies snapshots in decision order, preserving adaptive route history, card-reward skip state, and multi-step shop flags. Stateless frozen-row probes may use fresh agents only when the report labels them as hydration/mapping checks rather than own-trajectory compatibility.

### Use a two-stage gate

Stage 1 evaluates a preregistered bounded selection of already-frozen rows. Every selected row must pass schema/provenance checks, hydration, exact mapping, deterministic replay, non-mutation, fallback exclusion, and category coverage. Unsupported rows remain explicit failures; aggregate success cannot hide them.

Stage 2 is permitted only after Stage 1 passes. It may run one fixed subset of previously consumed seeds solely to check that an episode-local bridge can drive legal deterministic trajectories. It must reuse existing simulator source identity and must not compare terminal quality or update the formal readiness verdict. A fresh baseline-floor study requires a separate OpenSpec change and untouched preregistered seeds.

### Bind evidence and authority explicitly

The registration binds the implementation commit, Current/bridge/dependency files, adapter source/provenance, frozen dataset, metadata, runtime, category quotas, deterministic replay count, optional reused seeds, and expected output directory. The report emits per-row results, reason counts, hashes, a stage verdict, and authority booleans. `baseline_floor_authorized`, `training_authorized`, `reward_authorized`, `promotion_authorized`, and `fresh_evidence_authorized` remain false in every outcome.

## Risks / Trade-offs

- [Adapter snapshots omit decision-relevant fields] -> Fail closed per row, report the exact missing field, and require a separate adapter-contract change before adding it.
- [Current constructor or helper imports mutate global state] -> Disable tracking, isolate sessions, hash inputs, and add repeat-in-process tests.
- [External metadata drifts] -> Resolve one explicit file, bind its canonical path and SHA-256, and reject fallback loading.
- [Stateful Current behavior cannot be reconstructed from independent frozen rows] -> Keep Stage 1 structural and require Stage 2 before claiming own-trajectory compatibility.
- [A passing bridge is mistaken for policy quality] -> Keep all downstream authority false and require a separate baseline-floor study.
- [Bridge maintenance follows Current code churn] -> Bind source files and fail identity validation when they change.

## Migration Plan

1. Add the offline bridge and focused synthetic regressions.
2. Register a frozen-row Stage 1 POC and publish its hash-closed report.
3. Run Stage 2 only if the report explicitly authorizes it and the reused seed registration validates.
4. Sync and archive the capability after all authorized tasks complete.

Rollback removes the analysis module, tests, registration, reports, and this capability spec. No persisted gameplay or model state requires migration.

## Open Questions

- Whether frozen event evidence contains an exact event-option semantic source; until proven, event support remains fail-closed.
- Whether Stage 1 provides four-category executable coverage. If not, the POC stops without running Stage 2 or expanding the evidence cohort.
