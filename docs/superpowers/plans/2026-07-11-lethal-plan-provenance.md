# Lethal Plan Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve a validated multi-card lethal plan through `OptimizedAgent` and `CombatRLAgent` so a safe HP-loss lethal prefix is executed instead of being replaced by an end-turn pressure guard.

**Architecture:** `IroncladCombatPlanner` records whether its returned sequence came from the validated lethal branch. `OptimizedAgent` caches that plan kind with the action sequence and exposes a narrow identity-based query for the action it just emitted. `CombatRLAgent` repairs and validates that action, rejects immediate HP-cost or Sharp Hide death, and otherwise passes it through before end-turn pressure heuristics.

**Tech Stack:** Python 3, pytest, OPSX/OpenSpec 1.6.0 workflow, CommunicationMod, Windows production Python at `D:\anaconda\envs\stsai\python.exe`.

## Global Constraints

- Use OPSX change `investigate-lethal-detection-failure`; `openspec instructions apply --change "investigate-lethal-detection-failure" --json` is the task source of truth.
- Keep live gameplay on `D:\anaconda\envs\stsai\python.exe`; do not use the WSL Python for CommunicationMod.
- Do not train, tune combat weights, copy additional Bottled policy, or refactor unrelated guards.
- Preserve ordinary HP-loss pressure guards and immediate self-death protection.
- Use red regression, minimal implementation, focused pytest, full pytest, then fresh live evaluation.
- Commit the code as one coherent lethal-plan behavior class; do not split planner metadata, cache metadata, and arbitration into call-site microcommits.
- Do not delete or stage the existing untracked historical report files.

---

## File Map

- Modify `spirecomm/ai/heuristics/ironclad_combat.py:125` to initialize and set `last_plan_kind`.
- Modify `spirecomm/ai/heuristics/ironclad_combat.py:220` to reset provenance at the start of every plan and mark only a non-empty validated lethal sequence.
- Modify `spirecomm/ai/agent.py:2823` to initialize `current_plan_kind` with the cached combat plan.
- Modify `spirecomm/ai/agent.py:2935` to clear, replace, and query plan metadata through one lifecycle.
- Modify `spirecomm/ai/agent.py:3161` to clear plan metadata on turn change and combat exit.
- Modify `spirecomm/ai/rl/agent.py:1266` to pass a safe active lethal prefix through before encounter-pressure guards.
- Modify `spirecomm/ai/rl/agent.py:2381` to reuse current card-object target repair and immediate-death checks.
- Modify `tests/test_ironclad_combat_guards.py:11937` for planner provenance coverage.
- Modify `tests/test_turn_plan_signature_guards.py:314` for cache, query, stale-plan, turn-reset, and combat-exit coverage.
- Modify `tests/test_combat_rl_guards.py:2500` for the exact Hemokinesis failure and hard-veto controls.
- Modify `openspec/changes/investigate-lethal-detection-failure/tasks.md` as OPSX tasks are completed.
- Create `reports/trainable_baseline_qualification_batch1.md` after the first fresh batch.
- Create `reports/trainable_baseline_qualification_batch2.md` only after the first batch is free of A-class failures.

---

### Task 1: Implement End-to-End Lethal Plan Provenance

**Files:**
- Modify: `spirecomm/ai/heuristics/ironclad_combat.py:125`
- Modify: `spirecomm/ai/heuristics/ironclad_combat.py:220`
- Modify: `spirecomm/ai/agent.py:2823`
- Modify: `spirecomm/ai/agent.py:2935`
- Modify: `spirecomm/ai/agent.py:3161`
- Modify: `spirecomm/ai/rl/agent.py:1266`
- Modify: `spirecomm/ai/rl/agent.py:2381`
- Test: `tests/test_ironclad_combat_guards.py:11937`
- Test: `tests/test_turn_plan_signature_guards.py:314`
- Test: `tests/test_combat_rl_guards.py:2500`
- Modify: `openspec/changes/investigate-lethal-detection-failure/tasks.md`

**Interfaces:**
- Produces: `IroncladCombatPlanner.last_plan_kind: Optional[str]`, with the only current non-null value equal to `"lethal"`.
- Produces: `OptimizedAgent.current_plan_kind: Optional[str]`.
- Produces: `OptimizedAgent.is_active_lethal_plan_action(action: Action) -> bool`.
- Produces: `OptimizedAgent._clear_current_combat_plan() -> None`.
- Consumes: `CombatRLAgent.fallback_agent.is_active_lethal_plan_action(action)` when present; absence or exception means normal guard behavior.
- Produces: `CombatRLAgent._active_validated_lethal_prefix_action(action: Action, game: Game) -> Optional[Action]`.

- [ ] **Step 1: Add the failing planner provenance test**

Append this test near the existing lethal planner tests in `tests/test_ironclad_combat_guards.py`:

```python
def test_ironclad_planner_marks_only_nonempty_validated_lethal_plan():
    strike = _card("Strike_R", "Strike", cost=1)
    monster = _louse(current_hp=6)
    context = _combat_context([strike], energy=1, monsters=[monster])
    lethal_action = PlayCardAction(card=strike, target_monster=monster)
    planner = IroncladCombatPlanner()
    planner.combat_ending_detector = SimpleNamespace(
        can_kill_all=lambda _context: True,
        find_lethal_sequence=lambda _context: [lethal_action],
    )

    assert planner.plan_turn(context) == [lethal_action]
    assert planner.last_plan_kind == "lethal"

    empty_context = _combat_context([], energy=0, monsters=[monster])
    assert planner.plan_turn(empty_context) == []
    assert planner.last_plan_kind is None
```

- [ ] **Step 2: Run the planner test and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_ironclad_combat_guards.py::test_ironclad_planner_marks_only_nonempty_validated_lethal_plan -q -p no:cacheprovider --basetemp .pytest_tmp_lethal_plan_planner_red
```

Expected: FAIL because `IroncladCombatPlanner` does not expose `last_plan_kind`.

- [ ] **Step 3: Add minimal planner provenance**

Initialize the field in `IroncladCombatPlanner.__init__`:

```python
self.combat_ending_detector = CombatEndingDetector()
self.combat_mode = combat_mode
self.last_plan_kind: Optional[str] = None
```

Reset it before every early return and set it only when the detector returns a non-empty sequence:

```python
def plan_turn(self, context: DecisionContext) -> List[Action]:
    self.last_plan_kind = None
    self.decision_start = time.time()
    playable_cards = context.playable_cards

    if not playable_cards:
        return []

    # existing logging remains unchanged
    if self.combat_ending_detector.can_kill_all(context):
        logger.info("[COMBAT] Lethal detected!")
        lethal_sequence = self.combat_ending_detector.find_lethal_sequence(context)
        if lethal_sequence:
            self.last_plan_kind = "lethal"
            logger.info("[COMBAT] Lethal sequence: %s cards", len(lethal_sequence))
            return lethal_sequence
```

Do not mark an empty detector result or ordinary beam/timing plan as lethal.

- [ ] **Step 4: Run the planner test and verify GREEN**

Run the Step 2 command with `--basetemp .pytest_tmp_lethal_plan_planner_green`.

Expected: PASS.

- [ ] **Step 5: Extend cached-sequence tests with provenance and lifecycle coverage**

Update imports in `tests/test_turn_plan_signature_guards.py`:

```python
from spirecomm.ai.agent import OptimizedAgent, SimpleAgent, TurnPlanSignature
from spirecomm.communication.action import EndTurnAction, PlayCardAction
```

In `test_optimized_agent_continues_cached_sequence_after_played_card_leaves_hand`, give `FixedPlanner` a lethal plan kind, initialize `agent.current_plan_kind`, and assert both emitted actions retain provenance:

```python
class FixedPlanner:
    last_plan_kind = "lethal"

    def __init__(self):
        self.calls = 0

    def plan_turn(self, _context):
        self.calls += 1
        return [first_action, second_action]

# existing agent setup
agent.current_plan_kind = None

first = agent._get_optimized_play_card_action()
assert first is first_action
assert agent.current_plan_kind == "lethal"
assert agent.is_active_lethal_plan_action(first) is True

agent.game = _game([second_card])
agent.game.play_available = True
second = agent._get_optimized_play_card_action()

assert second is second_action
assert agent.is_active_lethal_plan_action(second) is True
assert agent.combat_planner.calls == 1
```

Add direct lifecycle and state-transition tests:

```python
def test_optimized_agent_clear_current_combat_plan_clears_provenance():
    action = PlayCardAction(card=_card("Strike_R", "Strike", uuid="strike"))
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_action_sequence = [action]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"

    agent._clear_current_combat_plan()

    assert agent.current_action_sequence == []
    assert agent.current_action_index == 0
    assert agent.current_plan_signature is None
    assert agent.current_plan_kind is None
    assert agent.is_active_lethal_plan_action(action) is False


def test_optimized_agent_clears_lethal_provenance_before_stale_replan(monkeypatch):
    stale_card = _card("Strike_R", "Strike", uuid="stale-strike")
    live_card = _card("Defend_R", "Defend", uuid="live-defend")
    stale_action = PlayCardAction(card=stale_card)
    live_action = PlayCardAction(card=live_card)
    planned_context = SimpleNamespace(act=1, threat_category=None, turn=3, floor=14)

    class FixedPlanner:
        last_plan_kind = None

        def plan_turn(self, _context):
            return [live_action]

    monkeypatch.setattr("spirecomm.ai.agent.DecisionContext", lambda _game: planned_context)
    monkeypatch.setattr(
        "spirecomm.ai.heuristics.simulation.select_combat_mode_with_monster_data",
        lambda _context: "test-mode",
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = _game([live_card])
    agent.game.play_available = True
    agent.current_action_sequence = [stale_action]
    agent.current_action_index = 0
    agent.current_plan_signature = None
    agent.current_plan_kind = "lethal"
    agent.replan_count_this_turn = 0
    agent._current_combat_mode = "test-mode"
    agent.combat_planner = FixedPlanner()
    agent.game_tracker = None
    agent.decision_history = []
    agent.player_class = "IRONCLAD"

    action = agent._get_optimized_play_card_action()

    assert action is live_action
    assert agent.current_plan_kind is None
    assert agent.is_active_lethal_plan_action(stale_action) is False


def test_optimized_agent_clears_lethal_plan_on_turn_change(monkeypatch):
    monkeypatch.setattr(
        SimpleAgent,
        "get_next_action_in_game",
        lambda _self, _game: EndTurnAction(),
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = SimpleNamespace(turn=3, in_combat=True)
    agent.game_tracker = None
    agent.current_action_sequence = [PlayCardAction(card_index=0, target_index=0)]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"
    agent.replan_count_this_turn = 0

    agent.get_next_action_in_game(SimpleNamespace(turn=4, in_combat=True))

    assert agent.current_plan_kind is None
    assert agent.current_action_sequence == []


def test_optimized_agent_clears_lethal_plan_on_combat_exit(monkeypatch):
    monkeypatch.setattr(
        SimpleAgent,
        "get_next_action_in_game",
        lambda _self, _game: EndTurnAction(),
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = SimpleNamespace(turn=3, in_combat=True)
    agent.game_tracker = None
    agent.current_action_sequence = [PlayCardAction(card_index=0, target_index=0)]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"
    agent.replan_count_this_turn = 0

    agent.get_next_action_in_game(SimpleNamespace(turn=3, in_combat=False))

    assert agent.current_plan_kind is None
    assert agent.current_action_sequence == []
```

- [ ] **Step 6: Run cache tests and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_turn_plan_signature_guards.py::test_optimized_agent_continues_cached_sequence_after_played_card_leaves_hand tests\test_turn_plan_signature_guards.py::test_optimized_agent_clear_current_combat_plan_clears_provenance tests\test_turn_plan_signature_guards.py::test_optimized_agent_clears_lethal_provenance_before_stale_replan tests\test_turn_plan_signature_guards.py::test_optimized_agent_clears_lethal_plan_on_turn_change tests\test_turn_plan_signature_guards.py::test_optimized_agent_clears_lethal_plan_on_combat_exit -q -p no:cacheprovider --basetemp .pytest_tmp_lethal_plan_cache_red
```

Expected: FAIL because plan-kind state, clear lifecycle, and query do not exist.

- [ ] **Step 7: Implement the OptimizedAgent plan lifecycle**

Initialize `current_plan_kind` in both `OptimizedAgent.__init__` branches next to `current_plan_signature`:

```python
self.current_action_sequence = []
self.current_action_index = 0
self.current_plan_signature = None
self.current_plan_kind = None
```

Add these methods before `_get_optimized_play_card_action`:

```python
def _clear_current_combat_plan(self) -> None:
    self.current_action_sequence = []
    self.current_action_index = 0
    self.current_plan_signature = None
    self.current_plan_kind = None

def is_active_lethal_plan_action(self, action: Action) -> bool:
    if self.current_plan_kind != "lethal":
        return False
    emitted_index = self.current_action_index - 1
    return (
        0 <= emitted_index < len(self.current_action_sequence)
        and self.current_action_sequence[emitted_index] is action
    )
```

When a new non-empty sequence is cached, copy the planner's plan kind:

```python
self.current_action_sequence = action_sequence
self.current_action_index = 0
self.current_plan_signature = current_signature
self.current_plan_kind = getattr(self.combat_planner, "last_plan_kind", None)
```

Replace each existing sequence reset in `_get_optimized_play_card_action` with `_clear_current_combat_plan()`:

```python
if self.should_replan(current_signature):
    self.replan_count_this_turn += 1
    self._clear_current_combat_plan()
else:
    self._clear_current_combat_plan()
```

Use the same helper when planning returns no actions and in the exception path:

```python
if not action_sequence:
    self._clear_current_combat_plan()
    return EndTurnAction()

except Exception as e:
    # existing error reporting remains
    self._clear_current_combat_plan()
    return super().get_play_card_action()
```

At the start of `get_next_action_in_game`, clear on either turn change or combat exit:

```python
turn_changed = (
    hasattr(game_state, "turn")
    and hasattr(self.game, "turn")
    and game_state.turn != self.game.turn
)
combat_ended = (
    bool(getattr(self.game, "in_combat", False))
    and not bool(getattr(game_state, "in_combat", False))
)
if turn_changed or combat_ended:
    self._clear_current_combat_plan()
    self.replan_count_this_turn = 0
```

- [ ] **Step 8: Run cache tests and verify GREEN**

Run the Step 6 command with `--basetemp .pytest_tmp_lethal_plan_cache_green`.

Expected: all five selected tests PASS.

- [ ] **Step 9: Add the exact takeover regression and hard-veto controls**

Append these tests near the existing HP-loss takeover tests in `tests/test_combat_rl_guards.py`:

```python
def _configure_takeover_agent(agent, fallback_agent, floor=14, turn=4):
    agent._fallback_turn_key = (floor, turn)
    agent.fallback_agent = fallback_agent
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0


def test_energy_guard_takeover_preserves_safe_hemokinesis_lethal_prefix(caplog):
    caplog.set_level("INFO")
    hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    headbutt = SimpleNamespace(
        name="Headbutt",
        card_id="Headbutt",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=9,
    )
    attacking_slime = _monster(
        hp=3,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    attacking_slime.intent = Intent.ATTACK_DEBUFF
    debuffing_slime = _monster(
        hp=14,
        damage=0,
        index=1,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    debuffing_slime.intent = Intent.DEBUFF
    lethal_action = PlayCardAction(
        card=hemokinesis,
        target_monster=debuffing_slime,
    )
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: lethal_action,
        is_active_lethal_plan_action=lambda action: action is lethal_action,
    )
    game = _game(
        hand=[hemokinesis, headbutt],
        monsters=[attacking_slime, debuffing_slime],
        current_hp=3,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 1
    assert "plan_kind=lethal decision=pass_through" in caplog.text


def test_energy_guard_takeover_rejects_self_lethal_lethal_prefix(caplog):
    caplog.set_level("INFO")
    hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    first = _monster(hp=3, damage=8, index=0, name="Spike Slime (M)", monster_id="SpikeSlime_M")
    second = _monster(hp=14, damage=0, index=1, name="Spike Slime (M)", monster_id="SpikeSlime_M")
    first.intent = Intent.ATTACK
    second.intent = Intent.DEBUFF
    lethal_action = PlayCardAction(card=hemokinesis, target_monster=second)
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: lethal_action,
        is_active_lethal_plan_action=lambda action: action is lethal_action,
    )
    game = _game(
        hand=[hemokinesis],
        monsters=[first, second],
        current_hp=2,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=1, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert "plan_kind=lethal veto=immediate_self_lethal" in caplog.text


def test_energy_guard_takeover_rejects_sharp_hide_lethal_prefix(caplog):
    caplog.set_level("INFO")
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        cost_for_turn=2,
        has_target=True,
        damage=30,
    )
    guardian = _monster(
        hp=20,
        damage=0,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.DEFEND
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    lethal_action = PlayCardAction(card=carnage, target_monster=guardian)
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: lethal_action,
        is_active_lethal_plan_action=lambda action: action is lethal_action,
    )
    game = _game(
        hand=[carnage],
        monsters=[guardian],
        current_hp=3,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=11,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback, floor=16, turn=11)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert "plan_kind=lethal veto=immediate_self_lethal" in caplog.text
```

- [ ] **Step 10: Run takeover tests and verify the main regression is RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_combat_rl_guards.py::test_energy_guard_takeover_preserves_safe_hemokinesis_lethal_prefix tests\test_combat_rl_guards.py::test_energy_guard_takeover_rejects_self_lethal_lethal_prefix tests\test_combat_rl_guards.py::test_energy_guard_takeover_rejects_sharp_hide_lethal_prefix tests\test_combat_rl_guards.py::test_energy_guard_takeover_skips_bloodletting_when_hp_loss_makes_incoming_lethal -q -p no:cacheprovider --basetemp .pytest_tmp_lethal_plan_takeover_red
```

Expected: the safe Hemokinesis test FAILS because the old pressure guard returns `EndTurnAction`; existing safety behavior remains intact.

- [ ] **Step 11: Implement lethal-prefix arbitration before pressure guards**

Add this helper near `_repair_current_play_card_target` in `spirecomm/ai/rl/agent.py`:

```python
def _active_validated_lethal_prefix_action(
    self,
    action: Action,
    game: Game,
) -> Optional[Action]:
    checker = getattr(
        self.fallback_agent,
        "is_active_lethal_plan_action",
        None,
    )
    if not callable(checker):
        return None
    try:
        if not checker(action):
            return None
    except Exception as exc:
        logger.debug("[LETHAL_PLAN] provenance query failed: %s", exc)
        return None

    candidate = action
    if not self._is_current_combat_action_playable(candidate, game):
        candidate = self._repair_current_play_card_target(candidate, game)
    if candidate is None or not self._is_current_combat_action_playable(candidate, game):
        logger.info(
            "[LETHAL_PLAN] plan_kind=lethal veto=stale_or_unplayable action=%s",
            self._describe_combat_action(action, game),
        )
        return None

    card = self._card_for_action(candidate, game)
    immediate_self_lethal = self._would_play_self_lethal_card(card, game)
    if is_attack_card(card):
        immediate_self_lethal = (
            immediate_self_lethal
            or self._would_single_card_lethal_attack_self_kill(card, game)
        )
    if immediate_self_lethal:
        logger.info(
            "[LETHAL_PLAN] plan_kind=lethal veto=immediate_self_lethal action=%s",
            self._describe_combat_action(candidate, game),
        )
        return None

    logger.info(
        "[LETHAL_PLAN] plan_kind=lethal decision=pass_through action=%s",
        self._describe_combat_action(candidate, game),
    )
    return candidate
```

Immediately after the existing `PotionAction` branch and before `act1_boss_pressure_replacement`, add:

```python
lethal_prefix_action = self._active_validated_lethal_prefix_action(
    fallback_action,
    game,
)
if lethal_prefix_action is not None:
    return self._with_combat_action_context(lethal_prefix_action, game)
```

Do not remove the later self-lethal, Sharp Hide, pressure, or unplayable-action guards. They remain the fallback path when provenance is absent, stale, unsafe, or raises an exception.

- [ ] **Step 12: Run takeover tests and verify GREEN**

Run the Step 10 command with `--basetemp .pytest_tmp_lethal_plan_takeover_green`.

Expected: all four selected tests PASS; the safe prefix is repaired to `card_index=0,target_index=1`, while HP-cost and Sharp Hide death remain blocked.

- [ ] **Step 13: Run the complete focused regression set**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_ironclad_combat_guards.py tests\test_turn_plan_signature_guards.py tests\test_combat_rl_guards.py -q -p no:cacheprovider --basetemp .pytest_tmp_lethal_plan_focused
```

Expected: exit code 0 with no failures.

- [ ] **Step 14: Run full pytest**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_lethal_plan_full
```

Expected: exit code 0 with no failures.

- [ ] **Step 15: Review the implementation diff for scope**

Run:

```powershell
git diff --check
git diff --stat
git diff -- spirecomm/ai/heuristics/ironclad_combat.py spirecomm/ai/agent.py spirecomm/ai/rl/agent.py tests/test_ironclad_combat_guards.py tests/test_turn_plan_signature_guards.py tests/test_combat_rl_guards.py
```

Expected: only provenance, lifecycle, arbitration, logs, and their tests changed; no scoring constants, route policy, Bottled policy, training configuration, or generated reports changed.

- [ ] **Step 16: Mark OPSX implementation and verification tasks complete**

In `openspec/changes/investigate-lethal-detection-failure/tasks.md`, mark tasks 2.1 through 4.4 complete after the red/green evidence, focused tests, full tests, and diff review all succeeded. Then run:

```powershell
openspec status --change "investigate-lethal-detection-failure" --json
openspec validate investigate-lethal-detection-failure --strict
```

Expected: valid change with only live-validation tasks 5.1 through 5.5 remaining.

- [ ] **Step 17: Commit one cohesive behavior fix**

Run:

```powershell
git add -- spirecomm/ai/heuristics/ironclad_combat.py spirecomm/ai/agent.py spirecomm/ai/rl/agent.py tests/test_ironclad_combat_guards.py tests/test_turn_plan_signature_guards.py tests/test_combat_rl_guards.py openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit -m "fix: preserve validated lethal takeover plans"
```

Expected: one commit containing the complete lethal-plan behavior class and no historical untracked reports.

---

### Task 2: Run the First Fresh Qualification Batch

**Files:**
- Read: `C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties`
- Read: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt`
- Read: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\*.run`
- Read: `D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log`
- Read: `D:\SteamLibrary\steamapps\common\SlayTheSpire\communication_mod_errors.log`
- Read: `D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_clean.jsonl`
- Read: `D:\SteamLibrary\steamapps\common\SlayTheSpire\sim_divergence_trace_clean.jsonl`
- Create: `reports/trainable_baseline_qualification_batch1.md`
- Modify: `openspec/changes/investigate-lethal-detection-failure/tasks.md`

**Interfaces:**
- Consumes: the committed code from Task 1.
- Produces: one bounded, no-training, 25-game report with cutoff, commit, config, run metrics, command errors, death clusters, lethal arbitration evidence, and sim-divergence classification.
- Gate: a causally demonstrated A-class failure stops qualification and prevents Task 3.

- [ ] **Step 1: Invoke gameplay operations and verify launch configuration**

At execution time, read and follow `sts-gameplay-ops`. Run:

```powershell
Get-Content 'C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties'
```

Expected command: Windows Python, `scripts/run_training_batch.py`, `--eval`, `--max-games 25`, `--phase conservative`, decision trace enabled, sim-divergence trace enabled, and no `--train` flag.

- [ ] **Step 2: Record a fresh cutoff and start a clean batch**

In one PowerShell session, run:

```powershell
$cutoff = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$commit = git rev-parse HEAD
$cutoff
$commit
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\PycharmProjects\slay-the-spire-ai\scripts\restart_sts_modded.ps1' -FreshRun
```

Expected: a numeric cutoff, the Task 1 commit hash, and a controlled fresh Ironclad launch. Preserve both values for the report and later commands.

- [ ] **Step 3: Monitor until the bounded batch exits**

Check progress from current processes, `ai_debug.log`, and new `.run` files without waits longer than 60 seconds. Completion evidence is:

```text
Max games reached (25); exiting.
```

Do not treat a live process, a main-menu screen, or fewer than 25 new AI-marked runs as completion.

- [ ] **Step 4: Generate combat and sim-divergence diagnostics**

In the same PowerShell session that retains `$cutoff`, run:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\analyze_combat_failures.py --runs-dir 'D:\SteamLibrary\steamapps\common\SlayTheSpire\runs' --character IRONCLAD --count 25 --log-path 'D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log' --decision-trace 'D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_clean.jsonl' --json

D:\anaconda\envs\stsai\python.exe analysis_scripts\summarize_sim_divergence_trace.py --trace 'D:\SteamLibrary\steamapps\common\SlayTheSpire\sim_divergence_trace_clean.jsonl' --since-unix $cutoff --limit-examples 5

Select-String -Path 'D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log' -Pattern 'Invalid command','invalid command','plan_kind=lethal veto=immediate_self_lethal','plan_kind=lethal decision=pass_through','Max games reached'

Get-Content 'D:\SteamLibrary\steamapps\common\SlayTheSpire\communication_mod_errors.log' -Tail 300
```

Expected: diagnostics limited to the new batch, zero invalid commands, and no new traceback attributable to the candidate.

- [ ] **Step 5: Classify all high-impact evidence**

Inspect raw log and trace rows for every lethal-plan pass-through or veto and every high-impact sim-divergence cluster. Classify each as:

```text
A: trace-supported mechanics, legality, or arbitration error that can change the combat/run outcome
B: plausible policy concern without causal proof
C: expected boundary noise or harmless stale-state timing
```

If any A-class issue exists, stop qualification after writing the report. Add a red regression and a separate cohesive fix before restarting Task 2; do not run Task 3.

- [ ] **Step 6: Write the batch report**

Create `reports/trainable_baseline_qualification_batch1.md` with this exact structure and replace each value with observed evidence from Steps 2-5:

```markdown
# Trainable Baseline Qualification Batch 1

## Batch Identity
- Commit: recorded Task 1 commit hash
- Cutoff: recorded Unix timestamp
- Mode: conservative eval, 25 games, no training
- Completion: 25/25 with `Max games reached (25); exiting`

## Run Outcomes
- Victories: observed count
- Average floor: observed value
- Maximum floor: observed value
- Act 1 boss reach: observed value
- Act 2 reach: observed value
- Top death clusters: observed ordered counts

## Execution Correctness
- Invalid commands: observed count
- New uncaught gameplay exceptions: observed count
- Validated lethal prefix pass-throughs: observed count
- Immediate self-lethal prefix vetoes: observed count

## Sim Divergence
- Fresh events: observed count
- High-impact clusters: observed cluster list
- Unresolved A-class clusters: observed count

## Qualification Decision
- Batch status: clean or failed
- Reason: evidence-backed decision
- Next action: second qualification batch or named regression cluster
```

- [ ] **Step 7: Update OPSX tasks and validate**

Mark tasks 5.1 through 5.4 complete after the batch, error audit, evidence classification, and report exist. Leave 5.5 unchecked. Run:

```powershell
openspec status --change "investigate-lethal-detection-failure" --json
openspec validate investigate-lethal-detection-failure --strict
git diff --check
```

Expected: valid change with task 5.5 as the only remaining task when Batch 1 is clean. When Batch 1 fails, the report names the A-class blocker and qualification returns to Task 1 through a new red regression.

- [ ] **Step 8: Commit the first qualification report**

Run:

```powershell
git add -- reports/trainable_baseline_qualification_batch1.md openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit -m "docs: record lethal plan qualification batch 1"
```

Expected: report and task-state commit only; generated raw JSONL and historical untracked reports remain unstaged.

---

### Task 3: Run the Second Qualification Batch and Close the Change

**Files:**
- Read: the same live game records and logs as Task 2.
- Create: `reports/trainable_baseline_qualification_batch2.md`
- Modify: `openspec/changes/investigate-lethal-detection-failure/tasks.md`

**Interfaces:**
- Consumes: a clean Task 2 report with zero unresolved A-class failures.
- Produces: the second consecutive clean 25-game qualification report and an OPSX change with 24/24 tasks complete.
- Stop rule: any new A-class failure resets qualification and leaves task 5.5 unchecked.

- [ ] **Step 1: Confirm Batch 1 is eligible**

Read `reports/trainable_baseline_qualification_batch1.md` and run:

```powershell
openspec instructions apply --change "investigate-lethal-detection-failure" --json
```

Expected: Batch 1 status is `clean`, tasks 5.1 through 5.4 are complete, task 5.5 remains, and there is no unresolved A-class issue. Otherwise stop and return to the named regression cluster.

- [ ] **Step 2: Start a second independently cut fresh batch**

Repeat Task 2 Steps 1-3 with a newly calculated `$cutoff`, the current commit hash, and `restart_sts_modded.ps1 -FreshRun`. Do not reuse the first cutoff or include first-batch trace rows.

- [ ] **Step 3: Run the same diagnostics and classification**

Repeat Task 2 Steps 4-5 using the second cutoff. Expected: 25/25 completion, zero invalid commands, no new candidate-attributable exception, and no unresolved A-class mechanics or arbitration failure.

- [ ] **Step 4: Write the second report**

Create `reports/trainable_baseline_qualification_batch2.md` with the same sections as Batch 1 plus:

```markdown
## Two-Batch Promotion
- Batch 1 status: clean
- Batch 2 status: clean or failed
- Consecutive clean batches: observed count
- Trainable baseline promoted: yes only when the count is 2
- Frozen baseline commit: current commit hash when promoted
```

If Batch 2 has an A-class issue, set promotion to `no`, leave task 5.5 unchecked, and name the regression cluster.

- [ ] **Step 5: Complete OPSX task state only after two clean batches**

When both reports are clean, mark task 5.5 complete and run:

```powershell
openspec instructions apply --change "investigate-lethal-detection-failure" --json
openspec validate investigate-lethal-detection-failure --strict
git diff --check
```

Expected: `state: "all_done"`, progress `24/24`, strict validation success, and no diff errors.

- [ ] **Step 6: Commit the second report and completed task state**

Run:

```powershell
git add -- reports/trainable_baseline_qualification_batch2.md openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit -m "docs: qualify lethal plan trainable baseline"
```

Expected: the change is implementation-complete and ready for the separate OPSX archive workflow. Formal non-combat RL remains blocked, and bounded combat-RL experiment planning begins from the frozen baseline commit rather than from generated training output.
