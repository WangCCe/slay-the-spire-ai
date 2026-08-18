## Context

The combat bridge currently initializes `GameContext` and stops at the first `BATTLE`. That gives deterministic, cheap episodes but only starter-era states. LightSTS already exposes the pieces required to reach later real run states: `SimpleAgent::stepOutOfCombat`, `BattleContext::init`, deterministic battle actions, and `BattleContext::exitBattle` state writeback.

## Goals / Non-Goals

**Goals:**

- Reach a requested zero-based battle index through native run progression rather than synthetic state mutation.
- Preserve deterministic clone and reset behavior for a `(seed, ascension, battle_index, source)` identity.
- Characterize encounter, floor, act, deck, relic, and HP coverage before training on the expanded surface.
- Keep the existing RL v2 observation/action dimensions and simulator-only authority.

**Non-Goals:**

- Replacing the production route, reward, shop, event, or combat policy with `SimpleAgent`.
- Learning from the baseline actions used before the target battle.
- Directly constructing elite or boss states by mutating LightSTS internals.
- Starting the game, loading production checkpoints, or treating simulator outcomes as promotion evidence.

## Decisions

### Use baseline-forward run progression

`Environment(seed, ascension, battle_index)` will resolve out-of-combat screens and every combat before `battle_index` with the existing native `SimpleAgent`. After each prior victory, `BattleContext::exitBattle` writes HP, cards, relic counters, potions, gold, and RNG state back to `GameContext`; progression then continues until the requested battle begins.

Alternative: inject a chosen encounter, deck, relic set, and HP directly. Rejected because it bypasses run invariants, requires a large state-construction API, and makes provenance harder to interpret.

### Keep earlier battles outside the RL episode

The RL-visible decision count starts at zero when the target battle is reached. Baseline-forward actions are initialization provenance, not replay transitions. Snapshot and status evidence will include requested/reached battle index plus the target act and floor.

Alternative: train continuously from battle zero through the whole run. Deferred because the current environment terminates at one battle and would mix non-combat policy and credit assignment into this narrow expansion.

### Bound and classify initialization

Negative battle indices and indices above a conservative fixed maximum are rejected. Out-of-combat and prior-combat actions have independent hard bounds. A baseline loss, terminal run, unsupported input, no progress, or exhausted bound raises a classified initialization error; the adapter never falls back to an earlier combat.

### Calibrate profiles before optimizer work

Calibration accepts registered `(seed, battle_index)` profiles and aggregates reached encounters, acts, floors, deck sizes, relic counts, HP, initialization failures, and ordinary bridge determinism evidence. The first expanded training run is allowed only if the report contains later floors and more encounter/progression diversity than the existing first-combat cohort.

The expanded training runner keeps classified baseline losses and run termination as profile-coverage evidence. It does not turn them into replay rows or zero-valued policy outcomes. Held-out control and candidate evaluations must agree on each unreachable profile and exclude those profiles from uplift aggregates; any other initialization error remains an integrity blocker.

### Preserve immutable native artifacts

The adapter and state schema advance to v3 and are built into a new run-scoped directory. Historical v1/v2 modules and reports remain unchanged, and rollback selects the v2 module.

## Risks / Trade-offs

- [Native baseline choices bias target-state distribution] -> Treat the surface as candidate-generation evidence, report its policy identity, and retain real-game replay/live gates for promotion.
- [Later requested battles are unreachable after a baseline loss] -> Record classified initialization failures, exclude matching natural unreachability from paired policy metrics, and never silently resample.
- [Baseline-forward initialization is slower] -> Characterize cost and use a small stratified index set before increasing episode counts.
- [LightSTS progression contains simulator divergence] -> Bind source bytes and make no mechanics-equivalence or production-policy claim.
- [Long prior combats can hang] -> Use explicit action bounds and fail the profile without retry or fallback.

## Migration Plan

1. Add red source and native regressions for indexed reset, deterministic clones, metadata, and unreachable-index errors.
2. Implement bounded baseline-forward initialization and Python validation without changing RL v2 dimensions.
3. Build a new immutable v3 module and run focused tests.
4. Publish one bounded profile calibration; only then register and run one expanded-surface training replication if coverage passes.
5. Roll back by selecting the prior v2 module; no production state or checkpoint migration is required.

## Open Questions

None. The profile distribution will be chosen from calibration evidence rather than assumed mappings between battle indices and encounter classes.
