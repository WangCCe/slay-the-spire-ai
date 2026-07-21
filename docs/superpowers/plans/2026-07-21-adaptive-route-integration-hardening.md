# Adaptive Route Integration Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three Important adaptive-routing integration findings with one-shot conservative recovery, explicit full-RL compatibility rejection, and a complete parseable decision record, then obtain fresh no-retry qualification evidence.

**Architecture:** Keep the normal strict two-candidate path unchanged. Add a narrower recovery context that validates only the active origin, committed history, and returned conservative route; centralize the `rl + adaptive` compatibility rule before any RL side effect; and preformat one fixed-order adaptive log payload before atomically committing route metadata. No policy threshold, route score, learned MAP behavior, training path, or default changes.

**Tech Stack:** Python 3, pytest, argparse, dataclasses, repository-local OpenSpec, Windows production interpreter `D:\anaconda\envs\stsai\python.exe`.

## Global Constraints

- The CLI default remains `aggressive`; adaptive remains opt-in.
- `simple`, `optimized`, Ironclad `auto`, and `combat_rl` retain heuristic adaptive MAP ownership; full `rl` rejects adaptive with the exact specified message.
- Keep normal adaptive whole-map and two-candidate validation strict.
- Recovery invokes the existing conservative builder exactly once and never retries.
- Do not change adaptive thresholds, route rewards, legacy conservative/aggressive behavior, RL action ownership, checkpoint/training behavior, Communication Mod protocol, or persistent live configuration.
- Use regression-first red/green cycles and `D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider` with a new repository-local basetemp for each direct run.
- Do not start live gameplay or training in Tasks 1-4.
- Once fresh qualification starts, any nonzero gate or blocking whole-range review ends this follow-up. Do not repair or rerun within this change.

---

### Task 1: One-Shot Conservative Recovery

**Files:**
- Modify: `tests/test_map_routing_safety.py`
- Modify: `spirecomm/ai/agent.py`
- Modify: `openspec/changes/harden-adaptive-route-integration-contracts/tasks.md`

**Interfaces:**
- Consumes: `_adaptive_candidate_origin()`, `_validated_route_history_prefix()`, `_describe_adaptive_route_candidate()`, `_build_map_route("conservative")`, and `_route_from_adaptive_candidate()`.
- Produces: `_adaptive_fallback_context() -> tuple[int, object | None, tuple, tuple[int, ...]]` and `_adaptive_conservative_fallback_candidate() -> _AdaptiveRouteCandidate`.

- [ ] **Step 1: Change the irrelevant-node characterization into a red recovery regression**

Replace `test_adaptive_malformed_unreachable_child_propagates_without_route_mutation` with a test that preserves the same malformed orphan, tracks `_build_map_route`, and asserts:

```python
route = agent.generate_map_route()

assert calls == ["conservative"]
assert route[:current.y + 1] == original_route[:current.y + 1]
assert route == agent.map_route
assert (agent._last_route_hp_pct, agent._last_route_floor) != original_metadata
assert "candidate_generation_failed" in caplog.text
```

Add the same malformed earlier-node condition to `_late_adaptive_route_agent(13)` and assert the floor-14 decision retains its complete absolute prefix and invokes one conservative builder. Extend `test_adaptive_act_start_fallback_uses_one_full_conservative_builder` with both a naturally empty route and a stale previous-act full route; in both cases assert a valid empty current-act `start_y=0` prefix, one builder call, and no previous-act prefix copied into the new route.

- [ ] **Step 2: Add red integrity regressions for invalid initial origin and fallback output**

Add an invalid-origin test where the screen has no usable current node but advertises only nonzero-row next nodes. Inject candidate failure and assert `_AdaptiveRouteCandidateGenerationError`, zero builder calls, unchanged route/metadata, and no `[ADAPTIVE_ROUTE]` record. Retain existing invalid mid-act history, truncated fallback, builder exception, and selector programming-error tests as the no-retry matrix.

- [ ] **Step 3: Run only the new recovery nodes and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_fallback_red tests/test_map_routing_safety.py -k "malformed_unreachable or late_fallback or act_start_fallback or invalid_initial"
```

Expected: the irrelevant-node cases fail because `_adaptive_conservative_fallback_route()` repeats `_validate_adaptive_candidate_map()`; integrity characterizations remain green.

- [ ] **Step 4: Implement the narrow recovery context**

In `spirecomm/ai/agent.py`, add a helper with this shape:

```python
def _adaptive_fallback_context(self):
    start_y, current_map_node, next_nodes = self._adaptive_candidate_origin()
    rows = getattr(getattr(self.game, "map", None), "nodes", None)
    if not isinstance(rows, dict) or not rows:
        raise _AdaptiveRouteCandidateGenerationError("candidate map has no rows")
    try:
        map_height = max(rows)
    except (TypeError, ValueError) as error:
        raise _AdaptiveRouteCandidateGenerationError(
            "candidate map height is invalid"
        ) from error
    if not isinstance(map_height, int) or map_height < start_y:
        raise _AdaptiveRouteCandidateGenerationError("candidate map is too short")

    if current_map_node is None:
        if start_y != 0 or any(
            getattr(node, "y", None) != 0 for node in next_nodes
        ):
            raise _AdaptiveRouteCandidateGenerationError(
                "initial candidate origin is invalid"
            )
        history_prefix = ()
    else:
        history_prefix = self._validated_route_history_prefix(
            map_height, current_map_node, start_y
        )
    return start_y, current_map_node, next_nodes, history_prefix
```

Do not call `_validate_adaptive_candidate_map()` here. `_adaptive_candidate_origin()` validates the active current-node lookup; `_validated_route_history_prefix()` validates committed coordinates/edges; `_describe_adaptive_route_candidate()` validates the returned full route, next-node start, active edge, bounds, coordinates, symbols, completion, and future edges.

- [ ] **Step 5: Return the validated fallback candidate and commit its route**

Replace `_adaptive_conservative_fallback_route()` with:

```python
def _adaptive_conservative_fallback_candidate(self):
    if self.map_router is None:
        raise _AdaptiveRouteCandidateGenerationError(
            "adaptive map router is unavailable"
        )
    start_y, current_map_node, next_nodes, history_prefix = (
        self._adaptive_fallback_context()
    )
    return self._describe_adaptive_route_candidate(
        "conservative",
        self._build_map_route("conservative"),
        start_y,
        current_map_node,
        next_nodes,
        history_prefix,
    )
```

In `generate_map_route()`, retain that object and derive the route only after it validates:

```python
fallback_candidate = self._adaptive_conservative_fallback_candidate()
route = self._route_from_adaptive_candidate(fallback_candidate)
```

For this task, pass the retained candidate through the existing summary slot so all old log tests stay green; Task 3 will apply the final availability matrix.

- [ ] **Step 6: Run recovery and complete routing suites**

Run the new nodes, then:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_fallback_green tests/test_map_routing_safety.py
```

Expected: all routing tests pass, one conservative call is observed for recovery, and every integrity/programming failure remains non-mutating and non-recursive.

- [ ] **Step 7: Mark tasks 1.1, 1.2, and 2.1 and commit**

```powershell
git add spirecomm/ai/agent.py tests/test_map_routing_safety.py openspec/changes/harden-adaptive-route-integration-contracts/tasks.md
git commit -m "fix: recover adaptive routes conservatively"
```

---

### Task 2: Full-RL Adaptive Compatibility Rejection

**Files:**
- Modify: `tests/test_main_runtime_errors.py`
- Modify: `main.py`
- Modify: `openspec/changes/harden-adaptive-route-integration-contracts/tasks.md`

**Interfaces:**
- Produces: `RL_ADAPTIVE_ROUTE_ERROR: str` and `validate_agent_route_compatibility(agent_type: str, elite_mode: str | None) -> None`.
- Direct construction raises `ValueError`; parsed CLI translates the same error through `parser.error()` to status `2`.

- [ ] **Step 1: Add direct-construction RED tests**

Add a test that monkeypatches `_load_rl_components`, `find_latest_checkpoint`, `create_rl_agent`, and `SimpleAgent` to fail if called, then asserts:

```python
with pytest.raises(ValueError) as error:
    main.create_agent(agent_type="rl", elite_mode="adaptive")

assert str(error.value) == main.RL_ADAPTIVE_ROUTE_ERROR
```

Add supported-path characterizations for `simple`, `optimized`, Ironclad `auto`, and `combat_rl` proving `elite_mode="adaptive"` reaches the heuristic owner. Add an `rl + conservative` characterization proving the existing learned RL factory path remains available and receives no new MAP-policy delegation.

- [ ] **Step 2: Add parsed-entrypoint RED test**

Launch the actual file with a fresh `STS_AI_LOG_FILE`:

```python
completed = subprocess.run(
    [
        sys.executable,
        "-I",
        str(Path(main.__file__).resolve()),
        "--agent", "rl",
        "--elite-route", "adaptive",
        "--eval",
    ],
    cwd=tmp_path,
    env=environment,
    capture_output=True,
    text=True,
    timeout=30,
    check=False,
)

assert completed.returncode == 2
assert main.RL_ADAPTIVE_ROUTE_ERROR in completed.stderr
assert "Creating CommunicationMod coordinator" not in log
assert "Creating RL Agent" not in log
assert "Auto-loading" not in log
assert "Falling back" not in log
```

This invocation includes `--eval` so rejection must precede checkpoint discovery as well as coordinator and agent startup.

- [ ] **Step 3: Run the new main tests and verify RED**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_rl_guard_red tests/test_main_runtime_errors.py -k "adaptive and (rl or heuristic)"
```

Expected: direct construction reaches `_load_rl_components` and the CLI does not yet emit the stable parser error.

- [ ] **Step 4: Add the shared validator before every side effect**

Near `create_agent()` in `main.py`, add:

```python
RL_ADAPTIVE_ROUTE_ERROR = (
    "--elite-route adaptive is unsupported for --agent rl; "
    "adaptive routing requires a heuristic map owner"
)


def validate_agent_route_compatibility(agent_type, elite_mode):
    if str(agent_type).lower() == "rl" and str(elite_mode).lower() == "adaptive":
        raise ValueError(RL_ADAPTIVE_ROUTE_ERROR)
```

Call it in `create_agent()` after resolving the deprecated `use_optimized` argument but before auto selection, `_load_rl_components()`, checkpoint lookup, or fallback branches. In the CLI block, call it immediately after resolving effective `agent_type` and before all RL-specific option processing:

```python
try:
    validate_agent_route_compatibility(agent_type, args.elite_route)
except ValueError as error:
    parser.error(str(error))
```

- [ ] **Step 5: Clarify help/docstring without changing defaults**

Update the `elite_mode` docstring and `--elite-route` help to state that adaptive requires a heuristic map owner and full `rl` rejects it. Keep choices and default unchanged.

- [ ] **Step 6: Run main-runtime and supported routing tests**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_rl_guard_green tests/test_main_runtime_errors.py tests/test_map_routing_safety.py -k "adaptive or create_agent or main_help"
```

Expected: exact `ValueError`, CLI status `2`, no RL/checkpoint/coordinator/fallback evidence, and supported heuristic paths remain green.

- [ ] **Step 7: Mark tasks 1.3, 2.2, and 2.4 and commit**

```powershell
git add main.py tests/test_main_runtime_errors.py openspec/changes/harden-adaptive-route-integration-contracts/tasks.md
git commit -m "fix: reject adaptive full rl startup"
```

---

### Task 3: Complete Outcome-Aware Adaptive Record

**Files:**
- Modify: `tests/test_map_routing_safety.py`
- Modify: `spirecomm/ai/agent.py`
- Modify: `openspec/changes/harden-adaptive-route-integration-contracts/tasks.md`

**Interfaces:**
- Produces: `_adaptive_candidate_summary(candidate) -> str` and `_adaptive_route_summary_payload(...) -> str`.
- The payload starts with `[ADAPTIVE_ROUTE]` and contains exactly the 21 ordered keys in the delta spec.

- [ ] **Step 1: Add a full-line parser and RED outcome fixtures**

In `tests/test_map_routing_safety.py`, define an expected key tuple and parser independent of implementation constants:

```python
ADAPTIVE_ROUTE_KEYS = (
    "outcome", "character", "act", "floor", "state_valid", "hp",
    "hp_pct", "deck", "potion", "relic", "elite_seen",
    "last_rest_floor", "candidate_pair", "conservative_candidate",
    "aggressive_candidate", "minimum_elites", "added_elites",
    "fallback_candidate", "budget", "selected", "reasons",
)


def _parse_adaptive_route_record(message):
    prefix, *tokens = message.split()
    assert prefix == "[ADAPTIVE_ROUTE]"
    pairs = [token.split("=", 1) for token in tokens]
    assert tuple(key for key, _ in pairs) == ADAPTIVE_ROUTE_KEYS
    assert all(value and not any(char.isspace() for char in value)
               for _, value in pairs)
    return dict(pairs)
```

Replace the current substring-only parameterization with exact assertions for `success`, `forced`, `unsupported`, `candidate_generation_failed`, and an invalid-state fixture. Assert six-decimal `hp_pct`, lowercase booleans, `none`, pair/count/fallback availability, candidate grammar, selected mode, and joined reasons. Keep the exactly-one and pre-commit-no-record tests.

- [ ] **Step 2: Run the log nodes and verify RED**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_log_red tests/test_map_routing_safety.py -k "structured_summary or route_summary_requires or invalid_state"
```

Expected: old `character=... hp=... conservative=...` output fails the ordered-key parser and lacks fallback/state evidence.

- [ ] **Step 3: Serialize validated candidates deterministically**

Make `_adaptive_candidate_summary()` return `unavailable` for absent data and otherwise format only validated `RouteCandidateFeatures`:

```python
return (
    f"mode:{features.mode},start_y:{features.start_y},"
    f"symbols:{symbols},elite_count:{len(features.elite_floors)},"
    f"elite_floors:{elite_floors},"
    f"recovery_before:{before},recovery_after:{after}"
)
```

Use `/` for symbols, `|` for elite floors, and `none` for empty/optional values.

- [ ] **Step 4: Build the exact outcome/availability payload before commit**

Add `_adaptive_route_summary_payload()` that:

1. Calls `self.map_router._valid_adaptive_state(state)`.
2. Emits `hp=current/max`, `hp_pct` with `:.6f`, readiness/support, elite history, and last rest only for valid state.
3. Uses `complete`, `not_attempted`, or `generation_failed` pair state from explicit `outcome`.
4. Computes `minimum_elites` and `added_elites` only for a complete pair.
5. Serializes the retained fallback candidate only for `candidate_generation_failed`.
6. Joins assessment reasons with `|` or emits `none`.
7. Rejects whitespace or `=` inside values before returning one preformatted string.

Determine `forced` only when `forced_elite_route` is in assessment reasons; otherwise a complete-pair decision is `success`.

- [ ] **Step 5: Preserve pre-commit preparation and post-commit emission**

In `generate_map_route()`, carry explicit `outcome` and `fallback_candidate`, prepare `adaptive_log_payload` before `_log_chosen_map_route(route)`, then retain the current commit order:

```python
self._log_chosen_map_route(route)
self.map_route = route
self._last_route_hp_pct = route_hp_pct
self._last_route_floor = route_floor
if adaptive_log_payload is not None:
    logging.info("%s", adaptive_log_payload)
```

Any candidate, fallback, state serialization, or chosen-path failure therefore occurs before route metadata mutation and emits no adaptive record.

- [ ] **Step 6: Run all routing tests**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_log_green tests/test_map_routing_safety.py
```

Expected: all outcome fixtures parse to the exact key set and all legacy/fallback integrity tests pass.

- [ ] **Step 7: Mark tasks 1.4 and 2.3 and commit**

```powershell
git add spirecomm/ai/agent.py tests/test_map_routing_safety.py openspec/changes/harden-adaptive-route-integration-contracts/tasks.md
git commit -m "feat: complete adaptive route decision records"
```

---

### Task 4: Focused Verification And Task Reviews

**Files:**
- Modify: `openspec/changes/harden-adaptive-route-integration-contracts/tasks.md`

**Interfaces:**
- Consumes: committed Tasks 1-3.
- Produces: focused test evidence, strict artifact validation, clean range checks, and no unresolved Critical/Important task review finding.

- [ ] **Step 1: Run both complete focused suites once**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest_followup_focused_final tests/test_map_routing_safety.py tests/test_main_runtime_errors.py
```

Preserve exact count and duration in the task ledger or later qualification report.

- [ ] **Step 2: Validate both changes and the whole range**

```powershell
openspec validate add-adaptive-elite-routing-baseline --strict
openspec validate harden-adaptive-route-integration-contracts --strict
git diff --check e1a559f37..HEAD
git diff --stat e1a559f37..HEAD
```

Confirm no threshold, learned MAP behavior, training, checkpoint, protocol, default, or live-config file changed.

- [ ] **Step 3: Obtain read-only task reviews**

Review each commit against its regressions and the follow-up delta, then review the combined implementation range. Resolve only findings discovered before fresh qualification begins. Require no unresolved Critical or Important finding.

- [ ] **Step 4: Mark tasks 3.1 and 3.2 and commit the truthful checklist**

```powershell
git add openspec/changes/harden-adaptive-route-integration-contracts/tasks.md
git commit -m "docs: verify adaptive route integration fixes"
```

---

### Task 5: One-Shot Host Qualification And Whole-Range Review

**Files:**
- Create: `reports/adaptive_route_integration_followup_gameplay_20260721.txt`
- Create: `reports/adaptive_route_integration_followup_commit_20260721.txt`
- Create: `reports/adaptive_route_integration_followup_full_20260721.txt`
- Create: `reports/adaptive_route_integration_followup_qualification_20260721.md`
- Create: `reports/adaptive_route_integration_followup_final_review_20260721.md`
- Modify: `openspec/changes/harden-adaptive-route-integration-contracts/tasks.md`
- Modify only after PASS: `openspec/changes/add-adaptive-elite-routing-baseline/tasks.md`

**Interfaces:**
- Consumes: frozen reviewed Task 4 HEAD.
- Produces: immutable one-attempt gate transcripts/report and a clean highest-capability review, or a terminal FAIL for this follow-up.

- [ ] **Step 1: Freeze source identity and run one host sequence**

Record `git rev-parse HEAD` and a clean tracked status. Under host permission, run exactly once in order, stopping on the first nonzero exit:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

Capture each reached command's complete terminal stream in its named raw `.txt` file. Do not retry. A nonzero result freezes code/tests/commands/gate policy and ends this follow-up.

- [ ] **Step 2: Write and verify the qualification report**

Record source SHA, exact printed commands, generated basetemps, counts, pytest and gate durations, exit codes, transcript SHA-256 hashes, stop point, and the fact that no training/live configuration was used. Mark tasks 4.1 and 4.2 according to actual evidence.

- [ ] **Step 3: Re-run final static checks only after all three gates pass**

```powershell
openspec validate add-adaptive-elite-routing-baseline --strict
openspec validate harden-adaptive-route-integration-contracts --strict
git diff --check e1a559f37..HEAD
```

- [ ] **Step 4: Obtain the final highest-capability whole-range review**

Review `e1a559f37..HEAD`, both active changes, all preserved qualification reports, and log-consumer compatibility. Write the verbatim verdict and evidence references to `reports/adaptive_route_integration_followup_final_review_20260721.md`. Any Critical or Important finding ends the follow-up with no same-change repair or qualification rerun.

- [ ] **Step 5: On PASS only, satisfy task 4.4 and commit evidence**

Mark follow-up tasks 4.3/4.4 and original task 4.4 only when every gate and final review passes:

```powershell
git add reports/adaptive_route_integration_followup_*_20260721.txt reports/adaptive_route_integration_followup_qualification_20260721.md reports/adaptive_route_integration_followup_final_review_20260721.md openspec/changes/harden-adaptive-route-integration-contracts/tasks.md openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
git commit -m "docs: qualify adaptive route integration fixes"
git push
```

Do not archive either change. The original ten-game no-training live cohort remains the next phase, and its conservative rollback requirements remain unchanged.
