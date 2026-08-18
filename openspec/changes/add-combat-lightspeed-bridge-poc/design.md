## Context

The repository already compiles `sts_lightspeed` into an offline non-combat adapter, but that adapter runs every battle to completion with native SimpleAgent and exposes only route, shop, event, and reward decisions. The production combat policy consumes CommunicationMod-shaped RL v2 observations and masks, so simulator combat cannot currently enter its replay or fitting pipeline.

The local simulator checkout is external and dirty by design. Historical adapter registrations therefore bind both Git identities and physical source/module hashes. Production remains r16, and the interrupted r19 cohort supplies no authority for this change.

## Goals / Non-Goals

**Goals:**

- Expose deterministic, cloneable `sts_lightspeed` player-normal combat states through a separate offline native module.
- Represent legal play-card, use-potion, and end-turn actions with stable action identifiers that map to RL v2 indices `0..90`.
- Produce the exact RL v2 observation components and 133-wide action mask expected by existing checkpoints for supported states.
- Measure deterministic replay, clone isolation, mapping coverage, and unsupported-state concentration in a bounded source-only calibration.

**Non-Goals:**

- Import arbitrary live mid-combat states or claim mechanics equivalence with the game.
- Support combat card-selection substates in this first POC.
- Load a checkpoint, fit a model, generate production replay, start CommunicationMod, run gameplay, qualify a policy, or promote r19.
- Modify the external `sts_lightspeed` checkout or the production runtime.

## Decisions

1. **Use a separate native module and build directory.** Add `sts_lightspeed_combat_adapter` beside the existing non-combat module and compile the same bound simulator sources. This avoids changing historical module bytes and keeps live imports impossible by default. Extending the existing module was rejected because it would couple unrelated evidence lineages and invalidate old hashes.

2. **Start with simulator-generated first combats.** Reset constructs an Ironclad run from a seed and uses native SimpleAgent only until the first battle reaches player-normal input. This gives deterministic POC states without claiming that SimpleAgent deck or route distributions match Current. Save-file and arbitrary-state import remain a later capability.

3. **Expose normalized JSON, then map in Python.** C++ owns simulator legality and state extraction; Python owns schema validation, ID normalization, RL v2 tensor construction, and coverage reporting. Directly constructing CommunicationMod `Game` objects was rejected because it would hide unsupported simulator fields behind permissive defaults.

4. **Support only player-normal input in v1.** Legal actions include playable hand cards, usable potions, and End Turn. When an action opens a card-selection substate, the environment reports an explicit unsupported boundary instead of fabricating an RL action. This makes coverage measurable and prevents silent training contamination.

5. **Keep simulator evidence outside production replay.** Calibration artifacts carry `source_type=sts_lightspeed_combat_simulation` and all training, gameplay, qualification, and promotion authority flags remain false. A later change must explicitly authorize transition generation or model fitting after divergence calibration.

6. **Use bounded deterministic calibration before real-game collection.** The first runner uses fixed registered seeds and action selection, clones each supported state, applies the same action to both branches, and compares canonical successors. It reports shapes, mask agreement, action coverage, terminal outcomes, unsupported reasons, and source identities. It does not consume fresh live seeds.

## Risks / Trade-offs

- **Simulator structs do not expose every CommunicationMod concept** -> Reject any field that cannot be mapped explicitly and report the unsupported reason; do not substitute zero silently except for RL v2 padding slots.
- **Card, relic, potion, power, or intent names differ** -> Reuse existing metadata/alias infrastructure where possible and make unknown identifiers terminal mapping errors in the POC.
- **BattleContext copies may retain unsafe internal references** -> Add clone-isolation tests that mutate one branch and compare the untouched branch before relying on native clones.
- **Normal-state-only coverage may be low for selection-heavy decks** -> Report concentration by reason and defer replay generation until a later bridge version covers material substates.
- **Determinism does not prove live fidelity** -> Keep mechanics-equivalence and policy-quality authority false; later calibration must replay matched real battle starts and action sequences.
- **Native builds can mutate historical evidence** -> Use a new run-scoped build directory and bind physical source and module hashes in every report.

## Migration Plan

There is no production migration. The module is opt-in and absent from CommunicationMod imports. Rollback removes the new target, Python adapter, calibration tooling, and its reports without touching r16, configuration, or existing non-combat artifacts.

## Open Questions

- Which first-combat states and action sequences provide enough coverage to justify a save-file-based real-game calibration?
- How should combat card-selection actions extend the fixed RL v2 action space without breaking checkpoint compatibility?
- What divergence thresholds are strong enough to authorize simulator replay generation in a later change?
