# Adaptive Elite Routing Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in Ironclad adaptive elite route mode that chooses the existing aggressive route only for a safe `0`-elite conservative versus `1`-elite aggressive candidate pair, then qualify it without training.

**Architecture:** Preserve the current dynamic-programming route behavior as the only candidate generator. First characterize and benchmark that generator, then add pure immutable adaptive assessment data in `map_routing.py`, refactor route generation to return mode-specific candidates, and let `SimpleAgent` choose between exactly two candidates while tracking visited nodes. All malformed, unsupported, forced-elite, and non-qualifying cases select conservative with stable reasons.

**Tech Stack:** Python 3, pytest, argparse, dataclasses, `time.perf_counter_ns`, Communication Mod, repository-local OpenSpec, Windows production interpreter `D:\anaconda\envs\stsai\python.exe`.

## Global Constraints

- Adaptive is opt-in and Ironclad-only; the CLI default remains `aggressive` and non-Ironclad adaptive requests execute conservative routing with `unsupported_character`.
- The first baseline permits an optional elite only for `conservative elite count == 0` and `aggressive elite count == 1`; it never compares legacy route scores.
- Optional Act 2 and Act 3 elites remain denied.
- Do not change combat, campfire, shop, event, card-reward, checkpoint, training, or Communication Mod protocol behavior.
- Use the production Windows interpreter for POC, focused tests, qualification gates, and live gameplay.
- Use `-p no:cacheprovider` and a writable unique repository-local `--basetemp` for direct pytest commands.
- Do not proceed past Task 1 when any POC candidate is incomplete, aggregate median exceeds 25 ms, or any measured pair exceeds 100 ms.
- Preserve the first `105.1622 ms` failed attempt. After freezing the review-complete qualification harness, permit exactly one clean-source requalification under the same thresholds; a second miss ends this plan without another POC retry.
- Do not train or tune from the ten-game cohort; restore conservative Communication Mod configuration after completion or failure.
- Preserve exact failures without overwrite. A permitted diagnosis or source-revision requalification never rewrites a failed full result.

---

### Task 1: Legacy Characterization And Paired-Route Feasibility

**Files:**
- Modify: `tests/test_map_routing_safety.py`
- Create: `tests/fixtures/adaptive_route_maps/full_height_sparse.json`
- Create: `tests/fixtures/adaptive_route_maps/full_height_typical.json`
- Create: `tests/fixtures/adaptive_route_maps/full_height_dense.json`
- Create: `analysis_scripts/benchmark_adaptive_route_candidates.py`
- Create: `tests/test_adaptive_route_candidate_benchmark.py`
- Create: `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json`
- Create: `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.md`
- Modify: `openspec/changes/add-adaptive-elite-routing-baseline/tasks.md`

**Interfaces:**
- Consumes: existing `SimpleAgent.generate_map_route()`, `AdaptiveMapRouter.calculate_node_priority()`, `Map.from_json()`, and `Node` graph semantics.
- Produces: `load_route_fixture(path: Path) -> dict`, `build_fixture_agent(fixture: dict, elite_mode: str) -> SimpleAgent`, `benchmark_fixture(path: Path, warmups: int, samples: int) -> FixtureBenchmark`, four shared legacy-characterization cases, three versioned full-height fixture JSON files, and the seven-case clean-source evidence artifacts at `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json` and `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.md`.

- [ ] **Step 1: Add characterization helpers and legacy tests**

Append small graph builders to `tests/test_map_routing_safety.py` and lock the pre-refactor behavior:

```python
def _route_agent(elite_mode, game_map, *, hp=80, max_hp=80, floor=0, deck=None):
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode=elite_mode)
    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = floor
    agent.game.current_hp = hp
    agent.game.max_hp = max_hp
    agent.game.deck = list(deck or [])
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = ["Burning Blood"]
    return agent


def test_legacy_modes_lock_optional_elite_choice_on_identical_map():
    game_map, safe_start, elite_start = _optional_elite_route_map()
    conservative = _route_agent("conservative", game_map)
    aggressive = _route_agent("aggressive", game_map, deck=_prepared_act1_deck())
    _set_start_screen(conservative, safe_start, elite_start)
    _set_start_screen(aggressive, safe_start, elite_start)

    assert conservative.make_map_choice().node == safe_start
    assert aggressive.make_map_choice().node == elite_start
```

Add separate concrete fixtures and assertions named `test_legacy_node_priorities_remain_mode_specific`, `test_legacy_conservative_tie_delays_first_forced_elite`, `test_legacy_modes_preserve_forced_single_elite_path`, `test_legacy_modes_preserve_forced_two_elite_path`, and `test_legacy_modes_only_replan_after_configured_hp_drop`. Each test constructs the full graph and asserts the exact selected `Node` or whether `generate_map_route` was called.

- [ ] **Step 2: Run legacy characterization tests before refactoring**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_adaptive_route_characterization tests/test_map_routing_safety.py
```

Expected: all existing and new characterization tests pass on the unmodified planner. If a proposed fixture does not expose the intended legacy difference, fix the fixture rather than gameplay code.

- [ ] **Step 3: Add benchmark schema tests first**

Create `tests/test_adaptive_route_candidate_benchmark.py` with fixture and timing-protocol tests:

```python
@pytest.mark.parametrize("name", ("sparse", "typical", "dense"))
def test_full_height_fixture_shape(name):
    fixture = load_route_fixture(FIXTURE_ROOT / f"full_height_{name}.json")
    nodes = fixture["nodes"]
    assert sorted({node["y"] for node in nodes}) == list(range(15))
    assert {node["x"] for node in nodes} <= set(range(7))
    assert len(_reachable_nodes(nodes)) >= 35
    assert all(1 <= len(node["children"]) <= 2 for node in nodes if node["y"] < 14)


def test_benchmark_fixture_uses_excluded_warmups_and_exact_samples(monkeypatch, fixture_path):
    calls = []
    monkeypatch.setattr(
        benchmark,
        "timed_route_pair",
        lambda fixture: (calls.append(fixture) or 1_000, (0,) * 15, (1,) * 15),
    )
    result = benchmark.benchmark_fixture(fixture_path, warmups=10, samples=100)
    assert len(calls) == 110
    assert result.sample_count == 100
    assert result.durations_ns == (1_000,) * 100
```

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_route_poc_red tests/test_adaptive_route_candidate_benchmark.py
```

Expected: fail because the benchmark module and fixture files do not exist.

- [ ] **Step 4: Add versioned fixture JSON and benchmark implementation**

Each JSON file has this stable top-level shape:

```json
{
  "schema_version": "adaptive-route-map-fixture-v1",
  "fixture_id": "full-height-sparse-v1",
  "game": {
    "act": 1,
    "floor": 0,
    "current_hp": 80,
    "max_hp": 80,
    "gold": 99,
    "deck": ["Bash+", "Pommel Strike", "Headbutt", "Anger", "Shrug It Off", "Iron Wave"],
    "potions": ["Fire Potion"],
    "relics": ["Burning Blood"]
  },
  "nodes": []
}
```

Populate 15 layers, x coordinates in `0..6`, at least 35 reachable nodes, and one or two child coordinates for each reachable nonterminal node. Vary elite/rest placement across sparse, typical, and dense while keeping the graph acyclic.

Implement `analysis_scripts/benchmark_adaptive_route_candidates.py` with immutable results:

```python
@dataclass(frozen=True)
class FixtureBenchmark:
    fixture_id: str
    fixture_sha256: str
    warmup_count: int
    sample_count: int
    durations_ns: tuple[int, ...]
    conservative_path: tuple[int, ...]
    aggressive_path: tuple[int, ...]


def timed_route_pair(fixture: dict) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    conservative = build_fixture_agent(fixture, "conservative")
    aggressive = build_fixture_agent(fixture, "aggressive")
    started = time.perf_counter_ns()
    conservative.generate_map_route()
    aggressive.generate_map_route()
    elapsed = time.perf_counter_ns() - started
    return elapsed, tuple(conservative.map_route), tuple(aggressive.map_route)
```

Configure a DEBUG file handler before timing so existing route INFO/DEBUG work is included. Hash the exact fixture bytes with SHA-256. Reject path-generation exceptions, empty routes, route lengths other than 15, and inconsistent paths across samples. Emit deterministic JSON with per-fixture and aggregate median, p95 nearest-rank, and maximum milliseconds.

- [ ] **Step 5: Run benchmark unit tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_route_poc_green tests/test_adaptive_route_candidate_benchmark.py tests/test_map_routing_safety.py
```

Expected: all tests pass.

- [ ] **Step 6: Run the production-interpreter POC**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\benchmark_adaptive_route_candidates.py --fixture-root tests\fixtures\adaptive_route_maps --warmups 10 --samples 100 --output reports\adaptive_route_candidate_poc_20260721_attempt-2_clean.json --log .adaptive_route_poc\route.log
```

Expected: seven qualification cases and 700 measured pairs, every candidate complete, aggregate median `<= 25.0 ms`, and maximum `<= 100.0 ms`.

- [ ] **Step 7: Write the POC decision report and update OpenSpec tasks**

The benchmark writes `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json`. After that command completes, generate `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.md` from that exact JSON result with command, interpreter, Git commit, fixture ids/SHA-256, graph dimensions, warm-up/measured counts, per-fixture median/p95/max, aggregate values, selected paths, raw-duration auditability, and explicit `PASS` or `FAIL`. Neither the canonical first FAIL artifacts nor `attempt-1-fail` artifacts may be overwritten.

If PASS, mark OpenSpec task 1.5 complete. If FAIL, stop without editing gameplay code; the sole clean-source requalification has then been consumed.

- [ ] **Step 8: Commit Task 1**

```powershell
git add tests/test_map_routing_safety.py tests/test_adaptive_route_candidate_benchmark.py tests/fixtures/adaptive_route_maps analysis_scripts/benchmark_adaptive_route_candidates.py reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.md reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
git commit -m "test: qualify adaptive route candidate generation"
```

---

### Task 2: Pure Adaptive Risk Policy

**Files:**
- Modify: `spirecomm/ai/heuristics/map_routing.py`
- Modify: `tests/test_map_routing_safety.py`
- Modify: `openspec/changes/add-adaptive-elite-routing-baseline/tasks.md`

**Interfaces:**
- Consumes: canonical card, potion, and relic identifiers already used by `AdaptiveMapRouter`.
- Produces: `AdaptiveRouteState`, `RouteCandidateFeatures`, `AdaptiveEliteAssessment`, `AdaptiveMapRouter.build_adaptive_state()`, `AdaptiveMapRouter.describe_candidate()`, and `AdaptiveMapRouter.assess_optional_elite()`.

- [ ] **Step 1: Add failing policy tests**

Add tests covering exact independent dimensions:

```python
def test_adaptive_deck_readiness_excludes_hp_potions_relics_and_floor():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    context = _context(deck=_prepared_act1_deck(), floor=12, hp_pct=0.95)
    context.game.potions = [_potion("Fire Potion")]
    context.game.relics = ["Burning Blood", "Preserved Insect"]
    assert router.adaptive_deck_readiness(context) == 7


def test_adaptive_relic_support_is_allowlisted_and_capped():
    assert router.adaptive_relic_support(["Burning Blood", "Preserved Insect", "Vajra"]) == 2
    assert router.adaptive_relic_support(["Burning Blood", "Question Card"]) == 0


def test_adaptive_assessment_allows_only_prepared_zero_vs_one_candidate():
    assessment = router.assess_optional_elite(prepared_state, safe_candidate, one_elite_candidate)
    assert assessment.optional_elite_budget == 1
    assert assessment.allowed is True
    assert assessment.reasons == ("optional_elite_allowed",)
```

Also add named tests for low absolute HP, low relative HP, insufficient deck, potion usability, exceptional deck, two-point relic support, local `node.y + 1`, Act 2 denial, malformed state, prior exposure, missing recovery, and the 90-percent/readiness-7/potion recovery exception.

- [ ] **Step 2: Run policy tests to verify RED**

Run the new node ids only with a unique basetemp. Expected: fail on missing adaptive types and methods while all legacy characterization tests remain green.

- [ ] **Step 3: Implement immutable inputs and named thresholds**

Add to `map_routing.py`:

```python
@dataclass(frozen=True)
class AdaptiveRouteState:
    player_class: str
    act: int
    current_hp: int
    max_hp: int
    hp_pct: float
    deck_readiness: int
    potion_support: int
    relic_support: int
    elite_seen: bool
    last_rest_floor: int | None


@dataclass(frozen=True)
class RouteCandidateFeatures:
    mode: str
    path: tuple[int, ...]
    symbols: tuple[str, ...]
    elite_floors: tuple[int, ...]
    first_elite_index: int | None
    rest_before_distance: int | None
    rest_after_distance: int | None


@dataclass(frozen=True)
class AdaptiveEliteAssessment:
    allowed: bool
    optional_elite_budget: int
    reasons: tuple[str, ...]
```

Use `Optional[int]` instead of `int | None` if the repository's supported Python floor requires it. Define constants for `48`, `0.75`, `0.90`, local floor `6`, readiness `5/7`, recovery distance `2`, potion ids, and relic weights.

- [ ] **Step 4: Implement pure scoring and hard gates**

Keep `_act_1_elite_readiness_score()` byte-for-byte behaviorally unchanged. Add independent methods whose output does not depend on HP/floor/resources, then evaluate gates in stable order and return one or more reason codes such as:

```python
("unsupported_character",)
("later_act_optional_elite",)
("hp_below_absolute_floor",)
("hp_below_relative_floor",)
("deck_not_ready",)
("resource_support_missing",)
("elite_already_seen",)
("candidate_counts_not_zero_vs_one",)
("recovery_window_missing",)
("optional_elite_allowed",)
```

- [ ] **Step 5: Run focused policy and legacy tests**

Run `tests/test_map_routing_safety.py`. Expected: policy tests and every Task 1 characterization pass.

- [ ] **Step 6: Mark OpenSpec tasks 2.2, 3.1, and 3.2 complete and commit**

```powershell
git add spirecomm/ai/heuristics/map_routing.py tests/test_map_routing_safety.py openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
git commit -m "feat: add adaptive elite risk policy"
```

---

### Task 3: Mode-Specific Candidates And Adaptive Selection

**Files:**
- Modify: `spirecomm/ai/agent.py`
- Modify: `spirecomm/ai/heuristics/map_routing.py`
- Modify: `tests/test_map_routing_safety.py`
- Modify: `openspec/changes/add-adaptive-elite-routing-baseline/tasks.md`

**Interfaces:**
- Consumes: Task 2 assessment types and the existing map dynamic program.
- Produces: `SimpleAgent._build_map_route(elite_mode: str) -> list[int]`, `SimpleAgent._adaptive_route_candidates() -> tuple[RouteCandidateFeatures, RouteCandidateFeatures]`, and `SimpleAgent._select_adaptive_route(conservative: RouteCandidateFeatures, aggressive: RouteCandidateFeatures, context: DecisionContext) -> tuple[list[int], AdaptiveEliteAssessment]`.

- [ ] **Step 1: Add failing candidate and selector tests**

Use the committed fixture maps and small targeted graphs to assert:

```python
def test_build_map_route_returns_legacy_candidates_without_committing_state():
    agent = _prepared_route_agent("adaptive", optional_elite_map)
    conservative = agent._build_map_route("conservative")
    aggressive = agent._build_map_route("aggressive")
    assert _elite_count(conservative, agent.game.map) == 0
    assert _elite_count(aggressive, agent.game.map) == 1
    assert agent.map_route == []
```

Add complete graph assertions named `test_adaptive_selector_chooses_aggressive_only_for_allowed_zero_vs_one`, `test_adaptive_selector_chooses_conservative_for_zero_vs_two`, `test_adaptive_selector_keeps_conservative_for_forced_one_elite`, `test_adaptive_selector_preserves_forced_two_elite_tie_break`, and `test_adaptive_selector_falls_back_when_candidate_generation_fails`.

- [ ] **Step 2: Run selector tests to verify RED**

Expected: missing `_build_map_route` and adaptive selector methods; legacy tests stay green.

- [ ] **Step 3: Refactor route generation without behavior changes**

Extract the body of `generate_map_route()` into a mode-parameterized builder. Pass `elite_mode_override` explicitly into elite minimization and node-priority calculation rather than mutating `self.elite_mode` or `self.map_router.elite_mode`:

```python
def _build_map_route(self, elite_mode):
    context = DecisionContext(self.game) if DecisionContext is not None else None
    # Existing DP body uses elite_mode for minimize-elites and node priority.
    return best_path


def generate_map_route(self):
    route = self._build_map_route(self.elite_mode)
    self.map_route = route
    self._last_route_hp_pct = self._current_route_hp_pct()
    self._last_route_floor = self.game.floor
    return route
```

Update `AdaptiveMapRouter.calculate_node_priority()` and internal Act 1/Act 2 helpers to accept an optional mode override while preserving no-override behavior. Do not temporarily mutate shared mode fields.

- [ ] **Step 4: Verify characterization immediately after refactor**

Run Task 1 characterization node ids before adding selection. Expected: every selected node/path and tie break is unchanged.

- [ ] **Step 5: Implement candidate description and selection**

Build fresh `DecisionContext` instances for each route pass, describe complete paths from the current local start row, and call the pure assessment. Catch only candidate-generation/data-shape exceptions at the adaptive boundary, log `candidate_generation_failed`, and run conservative once. Do not catch unrelated process or programming errors.

When assessment allows, commit aggressive; otherwise commit conservative. Return the chosen route and assessment so logging and tests inspect the exact decision.

- [ ] **Step 6: Run focused selector and legacy tests**

Expected: all map-routing tests pass, including forced paths and malformed fallback.

- [ ] **Step 7: Mark OpenSpec tasks 2.3, 3.3, and 3.4 complete and commit**

```powershell
git add spirecomm/ai/agent.py spirecomm/ai/heuristics/map_routing.py tests/test_map_routing_safety.py openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
git commit -m "feat: select bounded adaptive elite routes"
```

---

### Task 4: CLI, Visited-State Tracking, And Observability

**Files:**
- Modify: `main.py`
- Modify: `spirecomm/ai/agent.py`
- Modify: `tests/test_map_routing_safety.py`
- Modify: `tests/test_main_runtime_errors.py`
- Modify: `openspec/changes/add-adaptive-elite-routing-baseline/tasks.md`

**Interfaces:**
- Consumes: Task 3 selector.
- Produces: CLI acceptance for `adaptive`, `_adaptive_route_act`, `_adaptive_visited_nodes`, `_adaptive_elite_seen`, `_adaptive_last_rest_floor`, and one `[ADAPTIVE_ROUTE]` structured log record per map decision.

- [ ] **Step 1: Add failing CLI and tracking tests**

Add a subprocess help test that asserts `{conservative,aggressive,adaptive}` appears while the documented default remains aggressive. Add direct constructor tests for Ironclad and non-Ironclad adaptive modes.

Add complete agent fixtures named `test_adaptive_replans_on_every_map_choice`, `test_legacy_mode_keeps_hp_drop_replan_trigger`, `test_adaptive_history_is_idempotent_for_repeated_coordinate`, `test_adaptive_history_resets_on_act_change`, `test_adaptive_history_records_latest_rest_and_elite`, and `test_adaptive_decision_emits_one_structured_summary`. The first two monkeypatch `_build_map_route` and assert exact call sequences; the history tests assert the concrete set/act/floor values; the log test asserts exactly one record whose message starts with `[ADAPTIVE_ROUTE]`.

- [ ] **Step 2: Run new tests to verify RED**

Expected: argparse rejects adaptive or help lacks it; tracking attributes and log record are absent.

- [ ] **Step 3: Add CLI mode without changing defaults**

Change only the route option and examples/help:

```python
parser.add_argument(
    "--elite-route",
    choices=["conservative", "aggressive", "adaptive"],
    default="aggressive",
    help="Map routing strategy for elites: conservative, aggressive, or adaptive (default: aggressive)",
)
```

Update constructor docstrings that enumerate supported modes.

- [ ] **Step 4: Add idempotent adaptive history and per-choice replanning**

Initialize empty history in `SimpleAgent.__init__`. On each map choice, normalize act/current node, reset on act change, insert `(x, y)` into a set once, and record `R`/`E` effects only on first insertion. In adaptive mode always build both candidates. In legacy modes preserve the existing act-start/HP-drop logic exactly.

- [ ] **Step 5: Emit one stable summary record**

Use parameterized logging, not f-string multi-line output:

```python
logging.info(
    "[ADAPTIVE_ROUTE] act=%s floor=%s hp=%s/%s deck=%s potion=%s relic=%s "
    "conservative=%s aggressive=%s elite_counts=%s/%s recovery=%s/%s "
    "budget=%s selected=%s reasons=%s",
    state.act,
    self.game.floor,
    state.current_hp,
    state.max_hp,
    state.deck_readiness,
    state.potion_support,
    state.relic_support,
    conservative.symbols,
    aggressive.symbols,
    len(conservative.elite_floors),
    len(aggressive.elite_floors),
    aggressive.rest_before_distance,
    aggressive.rest_after_distance,
    assessment.optional_elite_budget,
    selected.mode,
    assessment.reasons,
)
```

Unsupported characters select conservative and include exactly `unsupported_character` in reasons.

- [ ] **Step 6: Run focused tests**

Run map-routing and main-runtime tests. Expected: all pass; CLI default assertions stay aggressive.

- [ ] **Step 7: Mark OpenSpec tasks 2.1, 2.4, 3.5, and 3.6 complete and commit**

```powershell
git add main.py spirecomm/ai/agent.py tests/test_map_routing_safety.py tests/test_main_runtime_errors.py openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
git commit -m "feat: expose observable adaptive route mode"
```

---

### Task 5: Automated Qualification And Final Review

**Files:**
- Create: `reports/adaptive_elite_routing_automated_qualification_20260721.md`
- Create: `reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md`
- Modify: `openspec/changes/add-adaptive-elite-routing-baseline/tasks.md`

**Interfaces:**
- Consumes: committed implementation from Tasks 1-4 and tiered pytest gates.
- Produces: exact automated qualification evidence and reviewed implementation ready for bounded live use.

- [x] **Step 1: Preserve immutable attempt-1 sandbox evidence**

Keep `reports/adaptive_elite_routing_automated_qualification_20260721.md` as attempt-1 sandbox FAIL. It retains focused `183 passed in 14.09s`, plus gameplay (`16.07s`, exit `1`), commit (`707.37s`, gate exit `1`, harness exit `124`), and full (`1237.76s`, exit `1`) results with their exact generated basetemps. Do not rerun focused verification and do not rewrite any attempt-1 result.

- [x] **Step 2: Record the managed-sandbox ACL root cause**

Record that pytest `9.0.2` cleanup calls `cleanup_dead_symlinks(basetemp) -> root.iterdir()`; the direct single `tmp_path` node passed; the same node under parent-Python to pytest-child failed; nested Python `mkdir(mode=0o700)` followed by immediate `iterdir()` failed in the managed sandbox; and the same minimal operation passed under host permission. Treat this as execution-environment ACL evidence, not a product or assertion failure.

- [ ] **Step 3: Run the sole corrected host-permission gate attempt**

Under host permission, run these unchanged commands once each and allow each gate to generate its unique basetemp:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

Keep the existing manifest and all thresholds unchanged. Do not rerun focused verification. Run `gameplay`, then `commit`, then `full` only while the preceding gate exited `0`; stop immediately at the first nonzero result. Preserve attempt 1 as failed. Only the already-known stream-silence node may receive its existing one diagnostic run when `full` is reached and it is the sole full-gate failure. Any other failure stops qualification without retry, code/test change, training change, or live-config change.

- [ ] **Step 4: Write the separate corrected qualification report**

Write exact printed profiles, resolved commands, unique basetemps, counts, durations, exit codes, stop point, and any permitted stream-silence diagnosis only to `reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md`. Never overwrite attempt 1. Mark OpenSpec task `4.3b` when the sequence has executed according to the stop rule and its evidence is preserved. Qualification success requires all three gates to exit `0` subject only to the existing full-node handling; otherwise do not start final review or live qualification.

- [ ] **Step 5: Validate artifacts and scope**

Run:

```powershell
openspec validate add-adaptive-elite-routing-baseline
git diff --check e1a559f37..HEAD
git diff --stat e1a559f37..HEAD
```

Confirm implementation touches only route/CLI/tests/POC/report/OpenSpec files and no prohibited policy or training files.

- [ ] **Step 6: Obtain read-only final review only after corrected-gate success**

Begin only after all three corrected `4.3b` gates succeeded. Review the complete diff from `e1a559f37` to HEAD against proposal/design/spec/tasks. Mark task 4.4 only after OpenSpec validation, diff check, and review are clean. A Critical or Important finding blocks this qualification and requires a follow-up change and new evidence; do not apply a same-attempt code fix or rerun focused tests.

- [ ] **Step 7: Commit qualification evidence**

```powershell
git add reports/adaptive_elite_routing_automated_qualification_20260721.md reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
git commit -m "docs: qualify adaptive elite routing implementation"
```

---

### Task 6: Bounded Live Ironclad Qualification

**Files:**
- Read/temporarily update: `C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties`
- Create: `reports/gameplay_adaptive_route_live_qualification_20260721.md`
- Modify: `openspec/changes/add-adaptive-elite-routing-baseline/tasks.md`

**Interfaces:**
- Consumes: reviewed adaptive implementation, production Windows Python, Communication Mod, fresh `.run` files and logs.
- Produces: one immutable ten-game no-training cohort decision and attested conservative rollback.

- [ ] **Step 1: Capture live baseline and rollback evidence**

Record raw and semantic hashes of `config.properties`, current command, AI marker line count, latest Ironclad run timestamp, `ai_debug.log`/`communication_mod_errors.log` sizes, decision/sim trace sizes and timestamps, and checkpoint inventory hash. Verify the command contains `--eval`, does not contain `--train`, and uses `--elite-route conservative` before modification.

- [ ] **Step 2: Configure exactly one ten-game adaptive cohort**

Use the production interpreter and existing controlled restart path. The child command must include:

```text
D:\anaconda\envs\stsai\python.exe D:\PycharmProjects\slay-the-spire-ai\main.py --agent combat_rl --eval --max-games 10 --ascension 0 --rl-version v2 --elite-route adaptive
```

Preserve all existing trace paths and operational safeguards. Capture the exact launch cutoff before starting.

- [ ] **Step 3: Monitor and stop on operational gates**

At bounded intervals inspect the visible game first if progress stalls, then fresh debug/error logs, process state, AI markers, and run files. Stop on uncaught runtime error, repeated stall, evidence-integrity loss, or causally demonstrated A-class command/mechanics failure. Do not train or alter policy during the cohort.

- [ ] **Step 4: Restore conservative configuration and attest it**

On completion or failure, restore the exact baseline bytes and verify raw byte equality, semantic command equality, production interpreter, conservative mode, no `--train`, and unchanged checkpoint inventory.

- [ ] **Step 5: Compute the qualification metrics**

For the ten fresh AI-marked `.run` files compute run ids, victory, floor, max floor, Act 2 boss reach, count of path `E` nodes, final `killed_by`, normalized elite-death attribution, `elite_death_runs`, and `elite_fatality_ratio`. Classify fresh sim-divergence rows by normalized cluster key and causal A/B/C class.

- [ ] **Step 6: Write report and apply the fixed gate**

The report declares eligible for a larger cohort only when all are true: at least three elite encounters; at most two elite-death runs; fatality ratio `<= 0.25`; average floor `>= 24.2`; Act 2 boss reaches `>= 3`; no runtime error; no repeated causal A-class cluster. Report any `victory=true` separately as progress on the outer objective. Do not change defaults or authorize training.

- [ ] **Step 7: Mark live tasks and commit**

Mark OpenSpec tasks 5.1-5.5 according to observed evidence, then commit:

```powershell
git add reports/gameplay_adaptive_route_live_qualification_20260721.md openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
git commit -m "docs: record adaptive route live qualification"
```

- [ ] **Step 8: Push the reviewed branch**

```powershell
git push
```

Do not archive the OpenSpec change without explicit confirmation.
