## Why

The adaptive elite-routing implementation passed its host `gameplay`, `commit`, and `full` gates (`371`, `2917`, and `3627` tests), but the required whole-change review still blocked live qualification. The review found three integration gaps that can stall on irrelevant malformed map data, silently ignore `adaptive` under the full-RL agent, and leave fallback decisions under-specified in live logs.

## What Changes

- Make `candidate_generation_failed` a real conservative recovery path: after adaptive candidate generation or validation fails, preserve a valid committed history, invoke the existing conservative builder exactly once, validate its returned full route, and commit only that validated result. Continue to propagate invalid active origins, invalid committed history, invalid fallback output, and unexpected programming errors without partial state.
- Reject the unsupported `--agent rl --elite-route adaptive` combination before agent startup. Keep adaptive routing supported for heuristic map owners (`simple`, `optimized`, Ironclad `auto`, and `combat_rl`) and do not add full-RL map-policy delegation or training behavior.
- Complete the single-line `[ADAPTIVE_ROUTE]` contract with honest availability states, normalized state validity and history, complete candidate summaries, minimum and added elite counts, and a validated conservative fallback summary. Preserve exactly one record after route commit and no record on an uncommitted error.
- Add regression-first coverage for each final-review finding, retain all existing legacy and integrity characterizations, and obtain fresh focused plus host `gameplay`/`commit`/`full` evidence followed by a clean whole-change review before reopening live qualification.
- Preserve the original automated-qualification PASS and final-review FAIL reports without reinterpretation or overwrite. The follow-up writes separately named evidence and may satisfy the original change's task `4.4` only after every new gate and review passes.
- Do not change adaptive risk thresholds, route rewards, combat/shop/event/card-reward/campfire policy, checkpoint or training behavior, Communication Mod protocol, CLI defaults, or persistent live configuration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `adaptive-elite-routing`: Narrows adaptive startup to agents whose MAP choices are owned by the heuristic router, defines one-shot conservative recovery at both first-map and mid-act origins, makes the adaptive decision record availability-aware and mechanically parseable, and requires fresh evidence after the blocked whole-change review. The original delta was synchronized into the main specification at commit `55b660b70` so this follow-up can modify the existing capability without duplicating it.

## Impact

- `spirecomm/ai/agent.py` will narrow fallback validation to active history/origin plus the returned conservative candidate and will retain that candidate for logging.
- `main.py` will fail fast with a stable error for the unsupported full-RL/adaptive combination in both direct construction and parsed CLI startup, before any RL factory, checkpoint load, or fallback agent path.
- `tests/test_map_routing_safety.py` and `tests/test_main_runtime_errors.py` will add exact regressions for fallback, compatibility, and outcome-specific log fields.
- Follow-up reports will preserve exact commands, raw or directly captured gate results, counts, durations, exit codes, final static validation, and independent review outcome.
- Success requires focused regressions, host `gameplay`, `commit`, and `full` gates to exit `0`, followed by no unresolved Critical or Important whole-change finding. Until then, conservative remains the rollback mode, adaptive remains opt-in, training remains disabled for qualification, and the first Ironclad `victory=true` run remains the outer objective.
