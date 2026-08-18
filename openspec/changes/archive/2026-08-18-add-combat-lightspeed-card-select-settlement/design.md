## Context

The v1 combat adapter exposes only `PLAYER_NORMAL` as supported. A legal card or potion action can enter native `CARD_SELECT`, after which the training runner excludes the pending transition. In r3 this censored 27 training trajectories and exactly the two held-out candidate trajectories that failed the victory and unsupported guardrails. LightSTS already has native card-selection enumeration, legality, execution, and a deterministic `SimpleAgent` selection policy, but several task variants remain unimplemented.

## Goals / Non-Goals

**Goals:**

- Resolve natively enumerable, implemented combat card-selection tasks before returning the successor of an RL-visible action.
- Preserve deterministic clone behavior and make every auxiliary settlement auditable.
- Keep unsafe or unimplemented task variants explicit and bounded.
- Preserve immutable historical modules, reports, and the RL v2 observation/action dimensions.

**Non-Goals:**

- Learning a card-selection policy or adding card-selection indices to RL v2.
- Claiming that the native auxiliary policy matches the production agent.
- Supporting every LightSTS `CardSelectTask` in this change.
- Starting the game, loading a production checkpoint, or granting transfer or promotion authority.

## Decisions

### Settle inside one environment step

After the selected card, potion, or End Turn action executes, the adapter will loop while the input state is `CARD_SELECT`. Each iteration is an auxiliary native action and does not increment the RL-visible decision count. This keeps the replay transition aligned with the production contract, where combat RL chooses ordinary combat actions and card-selection screens are handled outside the RL v2 action encoder.

Alternative: expose card selection through unused non-combat RL indices. Rejected because it changes the learned action semantics and would not match production decoding.

### Preflight native enumeration, then use the deterministic native subpolicy

The adapter will call `search::Action::enumerateCardSelectActions` before invoking `SimpleAgent::stepBattleCardSelect`. Settlement is allowed only for an explicit task allowlist whose native enumeration and execution are implemented. An empty enumeration, unknown task, exception, or unchanged card-selection state remains unsupported. A hard maximum of eight auxiliary selections prevents loops.

Alternative: always choose the first native action. Rejected because source ordering is not a policy and is weaker than the existing deterministic card-priority behavior.

### Publish settlement evidence in adapter v2

The adapter API and state schema will advance to v2. Status and snapshots will always include a `card_select_settlement` object with the count and ordered task names from the most recent RL-visible step. The Python bridge will validate this object but will keep the encoded RL v2 tensor and 133-element mask unchanged.

Alternative: add fields without a schema change. Rejected because the successor semantics change even when the tensor shape does not.

### Preserve immutable native builds

The v1 build directory and module remain untouched. Validation will create a new run-scoped build directory, bind its module hash in reports, and allow rollback by selecting the prior module path.

## Risks / Trade-offs

- [Native SimpleAgent differs from production card-selection heuristics] -> Keep transfer authority false and require later matched real-game divergence evidence.
- [A task has incomplete native enumeration or execution] -> Use an explicit allowlist plus non-empty enumeration preflight; preserve unsupported status otherwise.
- [Auxiliary settlement hides a policy decision from replay] -> Record task order and settlement count on every successor and document the fixed subpolicy.
- [Repeated card-selection screens loop] -> Enforce an eight-selection bound and report a stable classified reason.
- [New behavior invalidates historical evidence] -> Bump adapter/state schema versions and build in a new immutable directory.

## Migration Plan

1. Add red source-level and native regressions for r3 blocker seeds, clone isolation, evidence fields, and an unimplemented task boundary.
2. Implement v2 settlement and Python validation without changing RL v2 dimensions.
3. Build a new module in a new ignored directory and run focused bridge, calibration, and training tests.
4. Run one fixed new-cohort simulator replication only if the focused gate passes.
5. Roll back by restoring the v1 module path; no checkpoint or production state migration is required.

## Open Questions

None. Broader encounter and production-policy parity are intentionally deferred to later evidence gates.
