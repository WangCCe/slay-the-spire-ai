## Why

The registered live 600-attempt study is statistically infeasible under the frozen evidence, while the current non-combat policy dataset has only 125 complete trajectories and no target-supported victory. A local `sts_lightspeed` checkout can produce deterministic full-run outcomes in milliseconds and matched 12/12 historical Neow and first-combat reward candidate sets across six real runs, but its current Python binding does not expose cloning, legal non-combat actions, or complete decision snapshots.

## What Changes

- Add an optional, offline-only `sts_lightspeed` adapter POC that is built against an explicitly supplied external checkout and never imported by the CommunicationMod runtime.
- Expose deterministic Ironclad reset and clone operations, canonical snapshots, legal candidate enumeration, action execution, and terminal outcome for route, shop, event, and card-reward decisions.
- Delegate combat and unsupported intermediate screens to a declared simulator baseline so the POC can produce non-combat transitions without training a policy or changing live gameplay.
- Map simulator choices into a separate versioned transition schema with simulator provenance; do not relabel simulated rows as live decisions or known-propensity evidence.
- Add a deterministic fit audit covering exact source identity, build/import compatibility, repeated-seed determinism, bounded throughput, historical RNG-prefix agreement, category coverage, and unsupported semantics.
- Keep Bottled labels auxiliary and excluded from rewards. Keep live study launch, formal RL training, OPE reinterpretation, and policy promotion unauthorized.
- Success means the adapter can replay deterministic bounded smoke trajectories across all four target categories, clone before a choice, apply every reported candidate legally, and publish a source-bound report with explicit blockers. Rollback removes only the optional adapter, tests, fixture, report, and this change.

## Capabilities

### New Capabilities

- `noncombat-simulator-adapter`: Offline, provenance-bound simulator transitions and a fail-closed fit gate for a future bounded non-combat RL smoke experiment.

### Modified Capabilities

- `noncombat-rl-decision-loop`: Keep simulator-generated transitions separate from live known-propensity samples and require an explicit later approval before they can support training or promotion.

## Impact

- Affected code: a small optional adapter/build surface outside the live agent plus one offline audit CLI.
- Affected tests: pure schema/provenance tests and opt-in integration smoke checks against the local external checkout.
- Affected artifacts: one frozen historical-prefix fixture and deterministic JSON/Markdown fit reports.
- External dependency: local `D:\CLionProjects\sts_lightspeed`, bound by exact source and submodule identities; it is not vendored and is not a production dependency.
- Unchanged systems: CommunicationMod configuration, gameplay policy, checkpoints, live sample collection, OPE estimators, Bottled oracle behavior, reward definitions, and formal training authority.
