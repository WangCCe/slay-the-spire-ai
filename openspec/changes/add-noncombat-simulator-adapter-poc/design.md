## Context

The live known-propensity path cannot currently supply enough target-supported victories to justify its registered 600-attempt study. The repository nevertheless needs more than Current/Bottled imitation labels before formal non-combat RL is sensible: it needs an environment that can cheaply produce legal counterfactual transitions and terminal outcomes.

The local `sts_lightspeed` checkout at commit `7476a81954020087da31d41d16fddf475746ec2d` implements full Ironclad runs and all out-of-combat acts. A production-Python probe built the module with one compatibility-only forced include, completed 100 deterministic-policy runs in 0.084 seconds, reproduced a repeated 20-seed outcome batch exactly, and matched six historical runs at both their Neow reward and first combat reward (12/12 candidate sets). Its upstream Python surface, however, exposes only card-reward choices: `GameAction::getAllActionsInState`, `GameAction::execute`, state cloning, map access, shops, and events remain C++-only.

The local checkout is not a pristine upstream identity: `CMakeLists.txt` and both dependency worktrees differ from the recorded parent commit. Every result therefore has to bind the physical source and dependency identities rather than citing only the parent commit.

## Goals / Non-Goals

**Goals:**

- Prove whether a thin offline adapter can expose deterministic non-combat transitions for route, shop, event, and card reward.
- Preserve exact simulator, adapter, build, and fixture provenance.
- Use a declared simulator policy only to resolve combat and unsupported intermediate screens.
- Map choices into a distinct, versioned simulator-transition schema compatible with later dataset analysis but not confused with live evidence.
- Produce a fail-closed report that supports a later go/no-go decision for one bounded simulator RL smoke.

**Non-Goals:**

- No formal RL, behavior cloning, reward tuning, policy promotion, or live gameplay.
- No replacement of CommunicationMod or the current live agent.
- No vendoring or source modification of `sts_lightspeed` or Bottled.
- No claim that simulator outcomes are interchangeable with real-game outcomes.
- No attempt to import arbitrary historical live states; upstream save loading is not complete outside combat.
- No use of Bottled choices as reward or ground truth.

## Decisions

### 1. Build an optional out-of-tree adapter module

Add a small C++ pybind module and CMake project under a development-only adapter directory. Configuration requires an explicit `STS_LIGHTSPEED_ROOT`; all generated files go to an ignored caller-selected build directory. The module compiles against the external checkout but does not patch, vendor, or write it.

Alternative: add bindings directly to the local `sts_lightspeed` checkout. Rejected because that would split the change across repositories and make this repository's evidence depend on uncommitted external edits. Alternative: use only the existing Python module. Rejected because it cannot enumerate or execute route, shop, or event actions and cannot clone states.

### 2. Own the simulator state behind one narrow environment API

The extension exposes an Ironclad-only environment with `reset`, `clone`, `snapshot`, `legal_actions`, `step`, and terminal outcome. Python does not receive mutable raw C++ state. `clone` uses the simulator's `GameContext` copy constructor; branch-isolation regressions verify that applying an action to one branch does not alter its sibling. The shared map is accepted only while it remains immutable during play.

Snapshots contain only deterministic JSON-compatible values: seed, act, floor, HP, gold, deck, relics, potions, current category, map context, and category-specific offers. Every candidate has a stable simulator action id, category, kind, label, source slot or node, and raw action encoding where applicable.

Alternative: reuse the upstream 412-element observation. Rejected because it omits screen type, current candidates, event identity, shop inventory, and map topology.

### 3. Pause only at the four target decision categories

The environment advances combat with `SimpleAgent::playoutBattle` and resolves non-target screens with an explicitly named simulator baseline. It pauses at map, shop, non-Neow event, and card-reward choices. Neow, boss relics, campfires, treasure, reward collection, and follow-up card-selection screens remain baseline-controlled in this POC and are reported as unsupported for learned control.

Card rewards use a dedicated adapter action rather than generic reward-screen `SKIP`, because the generic action can abandon unrelated rewards. Shop purchases are sequential decisions. Event actions include baseline-controlled follow-up selection in their transition semantics and are marked accordingly.

Alternative: expose every simulator screen immediately. Rejected because it expands the action contract before the four requested categories are proven.

### 4. Keep simulated transitions in a separate evidence class

Simulator rows use a new schema and `source_type=sts_lightspeed_simulation`. They record deterministic behavior only when the adapter can reproduce the exact action distribution; otherwise propensity remains unknown. They never enter the live known-propensity gate, never inherit `.run` outcomes, and never count toward live OPE overlap or supported victories.

The eventual training design may combine live and simulated data only through a separately approved contract that declares weighting, simulator-divergence controls, reward semantics, and real-game holdout evaluation.

### 5. Make the fit audit empirical and fail closed

The audit binds parent commit, source-tree diff digest, submodule identities, module hash, compiler/Python versions, adapter commit, and fixture hash. It checks:

- build and import under the production Python ABI;
- repeated-seed reset and clone determinism;
- legal execution of every candidate on a clone;
- at least one bounded transition for each target category;
- terminal outcome production and bounded throughput;
- exact historical prefix agreement against a frozen six-run, twelve-choice fixture;
- explicit unsupported screens and semantics.

The strongest result is `adapter_poc_ready`. It permits only a separate proposal for a bounded simulator-training smoke. All live-study, formal-training, OPE, and promotion authority remains false.

## Risks / Trade-offs

- [Simulator mechanics diverge after the validated prefixes] -> Preserve source-bound reports, add category-level differential fixtures before training, and require real-game holdout evaluation for every later model.
- [The external checkout is dirty or changes] -> Hash the physical source and dependencies; fail closed when identity differs from the registered fixture.
- [C++ state copy is not branch independent] -> Execute every candidate on sibling clones and compare the untouched branch snapshot before accepting the clone capability.
- [Baseline-controlled combat confounds non-combat rewards] -> Record the combat baseline identity and treat simulator returns as environment-specific training signals, never causal live outcomes.
- [Event follow-up choices hide additional decisions] -> Mark follow-up control in transition metadata and keep those subchoices out of the learned action space in this POC.
- [Optional C++ integration slows normal tests] -> Keep compilation and external-checkout tests opt-in; ordinary commit-gate tests cover schemas, provenance, reports, and a fake adapter.

## Migration Plan

1. Add pure regressions for transition schema, provenance, authority boundaries, deterministic report rendering, and missing-capability failures.
2. Add the optional out-of-tree extension and a Python adapter wrapper.
3. Build against the exact local checkout and run deterministic clone/action/category smoke checks.
4. Freeze the historical-prefix fixture and publish the fit report.
5. Run focused tests, the registered commit gate, strict OpenSpec validation, and scoped review.
6. If the POC passes, archive this change and propose a separately bounded simulator-training smoke. If it fails, retain the report and remove only the optional adapter implementation.

## Open Questions

- What simulator-to-live divergence threshold should gate a later training smoke after more than the current 12 prefix checks exist?
- Should a later learned policy control campfires and boss relics before or after the four current categories demonstrate real-game holdout value?
- Which training-only reward shaping, if any, is acceptable while victory remains the sole promotion outcome?
