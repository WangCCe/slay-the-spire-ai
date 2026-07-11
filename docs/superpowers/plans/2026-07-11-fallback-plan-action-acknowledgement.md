# Fallback Plan Action Acknowledgement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace scattered lethal-only cache invalidation with one generic fallback-plan accept/reject boundary so takeover guards cannot execute a stale continuation after replacing an emitted action.

**Architecture:** `OptimizedAgent` exposes identity-based membership, plan-kind, and rejection methods for the action it most recently emitted from a cached sequence. `CombatRLAgent` acquires fallback exactly once, classifies that action, and routes every takeover result through one finalizer that either accepts the planned action or rejects the cached continuation. Lethal rejection failure is quarantined by `(in_combat, floor, turn)`, independent of transient screen type.

**Tech Stack:** Python 3, pytest, OPSX/OpenSpec 1.6.0 workflow, CommunicationMod, Windows production Python at `D:\anaconda\envs\stsai\python.exe`.

## Global Constraints

- Use OPSX change `investigate-lethal-detection-failure`; its spec and design are the behavior source of truth.
- Keep gameplay on `D:\anaconda\envs\stsai\python.exe`; never use WSL Python for CommunicationMod.
- Do not train, tune combat weights, copy Bottled policy, change route/reward policy, or refactor unrelated guards.
- Preserve immediate HP-cost and reactive-damage death vetoes plus ordinary HP-loss pressure guards.
- A takeover decision obtains fallback at most once and finalizes every emitted active-plan action exactly once.
- Plan kind controls lethal precedence only; active-plan membership controls lifecycle for both lethal and ordinary plans.
- Do not delete, modify, or stage historical untracked report files.
- Use RED regression, minimal implementation, focused pytest, full pytest, independent task review, then fresh live evaluation.

---

## File Map

- Modify `openspec/changes/investigate-lethal-detection-failure/design.md` to replace lethal-only invalidation with generic plan acknowledgement.
- Modify `openspec/changes/investigate-lethal-detection-failure/specs/ai-combat/spec.md` to require rejection of cached continuation after takeover replacement.
- Modify `openspec/changes/investigate-lethal-detection-failure/tasks.md` to track acknowledgement and transient-screen regressions.
- Modify `spirecomm/ai/agent.py` to expose generic active-plan membership, kind, and rejection.
- Modify `spirecomm/ai/rl/agent.py` to centralize takeover finalization and use a screen-independent combat epoch.
- Modify `tests/test_turn_plan_signature_guards.py` for generic plan membership/rejection lifecycle.
- Modify `tests/test_combat_rl_guards.py` for ordinary cached replacement, finalizer, and transient-screen quarantine regressions.
- Preserve existing planner provenance tests in `tests/test_ironclad_combat_guards.py`.
- Create `reports/trainable_baseline_qualification_batch1.md` only after Task 1 review is approved.
- Create `reports/trainable_baseline_qualification_batch2.md` only after Batch 1 is clean.

---

### Task 1: Implement Generic Fallback Plan Acknowledgement

**Files:**
- Modify: `openspec/changes/investigate-lethal-detection-failure/design.md`
- Modify: `openspec/changes/investigate-lethal-detection-failure/specs/ai-combat/spec.md`
- Modify: `openspec/changes/investigate-lethal-detection-failure/tasks.md`
- Modify: `spirecomm/ai/agent.py:2919`
- Modify: `spirecomm/ai/rl/agent.py:1225`
- Modify: `spirecomm/ai/rl/agent.py:2403`
- Test: `tests/test_turn_plan_signature_guards.py:350`
- Test: `tests/test_combat_rl_guards.py:2700`

**Interfaces:**
- Produces: `OptimizedAgent.is_active_plan_action(action: Action) -> bool`.
- Produces: `OptimizedAgent.active_plan_kind_for_action(action: Action) -> Optional[str]`.
- Produces: `OptimizedAgent.reject_active_plan_action(action: Action) -> bool`.
- Keeps: `is_active_lethal_plan_action()` and `invalidate_active_lethal_plan_action()` as compatibility wrappers.
- Produces: `CombatRLAgent._fallback_plan_metadata(action: Action) -> tuple[bool, Optional[str]]`.
- Produces: `CombatRLAgent._finalize_takeover_action(...) -> Optional[Action]`.
- Produces: `CombatRLAgent._combat_epoch(game: Game) -> tuple[bool, object, object]`.

- [ ] **Step 1: Update OPSX artifacts before implementation**

Replace the lethal-only lifecycle decision in `design.md` with this contract:

```markdown
### Acknowledge every consumed cached-plan action

`OptimizedAgent` SHALL expose identity-based membership, plan-kind, and
rejection for the action most recently emitted from its cached sequence.
`CombatRLAgent` SHALL acquire fallback once and finalize the emitted action
exactly once. Returning the same validated planned action accepts it; returning
any wait, end turn, potion suppression, repaired target, survival action,
pressure action, or other replacement rejects and clears the entire cached
continuation.

Plan kind affects lethal guard precedence only. Plan rejection applies to both
ordinary and lethal cached sequences. A normalized lethal action counts as the
same action only when it preserves the planned card and still-live target.
```

Add this scenario to `specs/ai-combat/spec.md`:

```markdown
#### Scenario: Takeover replacement rejects cached continuation
- **GIVEN** the fallback agent emits the first action of a cached two-action plan
- **AND** takeover arbitration selects a different action
- **WHEN** the next game state is evaluated
- **THEN** the previous cached continuation SHALL have been cleared
- **AND** its second action SHALL NOT be emitted as though the first action executed
```

Append these tasks to the appropriate sections of `tasks.md`:

```markdown
- [ ] 2.5 Add an ordinary cached-plan replacement regression.
- [ ] 2.6 Add a same-turn transient-screen quarantine regression.
- [ ] 3.7 Replace lethal-only invalidation with generic plan acknowledgement.
- [ ] 3.8 Route takeover results through one accept/reject finalizer.
- [ ] 4.5 Re-run independent task review against the acknowledgement contract.
```

Run:

```powershell
openspec validate investigate-lethal-detection-failure --strict
```

Expected: `Change 'investigate-lethal-detection-failure' is valid`.

- [ ] **Step 2: Add generic OptimizedAgent lifecycle regressions**

Add to `tests/test_turn_plan_signature_guards.py`:

```python
def test_optimized_agent_generic_active_plan_action_rejection():
    emitted = PlayCardAction(card=_card("Strike_R", "Strike", uuid="emitted"))
    followup = PlayCardAction(card=_card("Defend_R", "Defend", uuid="followup"))
    unrelated = PlayCardAction(card=_card("Bash", "Bash", uuid="unrelated"))
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_action_sequence = [emitted, followup]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = None

    assert agent.is_active_plan_action(emitted) is True
    assert agent.active_plan_kind_for_action(emitted) is None
    assert agent.reject_active_plan_action(unrelated) is False
    assert agent.current_action_sequence == [emitted, followup]

    assert agent.reject_active_plan_action(emitted) is True
    assert agent.current_action_sequence == []
    assert agent.current_action_index == 0
    assert agent.current_plan_signature is None
    assert agent.current_plan_kind is None


def test_optimized_agent_lethal_compatibility_wraps_generic_plan_contract():
    emitted = PlayCardAction(card=_card("Strike_R", "Strike", uuid="lethal"))
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_action_sequence = [emitted]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"

    assert agent.active_plan_kind_for_action(emitted) == "lethal"
    assert agent.is_active_lethal_plan_action(emitted) is True
    assert agent.invalidate_active_lethal_plan_action(emitted) is True
    assert agent.current_action_sequence == []
```

- [ ] **Step 3: Add ordinary takeover replacement and finalizer regressions**

Add this helper and tests to `tests/test_combat_rl_guards.py` near the existing lethal-plan takeover tests:

```python
class _CachedPlanFallback:
    def __init__(self, actions, plan_kind=None):
        self.actions = list(actions)
        self.index = 0
        self.plan_kind = plan_kind
        self.last_emitted = None
        self.reject_calls = []
        self.calls = 0

    def get_next_action_in_game(self, _game):
        self.calls += 1
        if self.index >= len(self.actions):
            self.last_emitted = EndTurnAction()
            return self.last_emitted
        self.last_emitted = self.actions[self.index]
        self.index += 1
        return self.last_emitted

    def is_active_plan_action(self, action):
        return action is self.last_emitted and self.index > 0

    def active_plan_kind_for_action(self, action):
        return self.plan_kind if self.is_active_plan_action(action) else None

    def reject_active_plan_action(self, action):
        if not self.is_active_plan_action(action):
            return False
        self.reject_calls.append(action)
        self.actions = []
        self.index = 0
        self.last_emitted = None
        self.plan_kind = None
        return True


def test_takeover_replacement_rejects_ordinary_cached_continuation(monkeypatch):
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=6,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        cost_for_turn=2,
        has_target=True,
        damage=8,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=False,
        block=5,
    )
    first = PlayCardAction(card_index=0, target_index=0)
    stale_followup = PlayCardAction(card_index=1, target_index=0)
    replacement = PlayCardAction(card_index=2)
    fallback = _CachedPlanFallback([first, stale_followup])
    game = _game(
        hand=[strike, bash, defend],
        monsters=[_monster(hp=30, damage=8, index=0)],
        floor=14,
        turn=4,
        player=SimpleNamespace(energy=3, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)
    replacements = iter([replacement, None])
    monkeypatch.setattr(
        agent,
        "_get_slime_split_aoe_survival_replacement",
        lambda _game: next(replacements),
    )

    selected = agent.get_next_action_in_game(game)

    assert selected.card_index == 2
    assert fallback.reject_calls == [first]
    assert fallback.actions == []

    second = agent.get_next_action_in_game(game)
    assert second is not stale_followup
    assert fallback.calls == 2


@pytest.mark.parametrize(
    ("active_plan", "accepted", "expect_reject"),
    [(False, False, False), (True, True, False), (True, False, True)],
)
def test_takeover_finalizer_accepts_or_rejects_once(
    active_plan,
    accepted,
    expect_reject,
):
    emitted = PlayCardAction(card_index=0, target_index=0)
    selected = emitted if accepted else EndTurnAction()
    fallback = _CachedPlanFallback([emitted])
    fallback.last_emitted = emitted if active_plan else None
    fallback.index = 1 if active_plan else 0
    game = _game()
    agent = _agent()
    agent.fallback_agent = fallback

    result = agent._finalize_takeover_action(
        emitted,
        selected,
        game,
        active_plan=active_plan,
        plan_kind=None,
        accepted_plan_action=accepted,
    )

    assert result is selected
    assert len(fallback.reject_calls) == int(expect_reject)
```

- [ ] **Step 4: Add the same-turn transient-screen quarantine regression**

Add to `tests/test_combat_rl_guards.py`:

```python
def test_failed_lethal_rejection_quarantine_survives_transient_screen():
    action = PlayCardAction(card_index=0, target_index=0)
    fallback = SimpleNamespace(
        is_active_plan_action=lambda candidate: candidate is action,
        active_plan_kind_for_action=lambda candidate: (
            "lethal" if candidate is action else None
        ),
        reject_active_plan_action=lambda _candidate: False,
    )
    agent = _agent()
    agent.fallback_agent = fallback
    none_screen = _game(floor=14, turn=4, in_combat=True)
    hand_select = _game(floor=14, turn=4, in_combat=True)
    hand_select.screen_type = ScreenType.HAND_SELECT
    next_turn = _game(floor=14, turn=5, in_combat=True)

    assert agent._reject_confirmed_active_plan_action(
        action,
        none_screen,
        plan_kind="lethal",
    ) is False
    assert agent._lethal_plan_precedence_is_quarantined(none_screen) is True
    assert agent._lethal_plan_precedence_is_quarantined(hand_select) is True
    assert agent._lethal_plan_precedence_is_quarantined(none_screen) is True
    assert agent._lethal_plan_precedence_is_quarantined(next_turn) is False
```

- [ ] **Step 5: Run the new regressions and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_turn_plan_signature_guards.py::test_optimized_agent_generic_active_plan_action_rejection tests\test_turn_plan_signature_guards.py::test_optimized_agent_lethal_compatibility_wraps_generic_plan_contract tests\test_combat_rl_guards.py::test_takeover_replacement_rejects_ordinary_cached_continuation tests\test_combat_rl_guards.py::test_takeover_finalizer_accepts_or_rejects_once tests\test_combat_rl_guards.py::test_failed_lethal_rejection_quarantine_survives_transient_screen -q -p no:cacheprovider --basetemp .pytest_tmp_plan_ack_red
```

Expected: failures because generic plan APIs, finalizer, and screen-independent epoch do not exist; the ordinary cached continuation is not rejected.

- [ ] **Step 6: Implement generic OptimizedAgent plan acknowledgement**

Replace the lethal-only methods beside `_clear_current_combat_plan()` with:

```python
def is_active_plan_action(self, action: Action) -> bool:
    emitted_index = self.current_action_index - 1
    return (
        0 <= emitted_index < len(self.current_action_sequence)
        and self.current_action_sequence[emitted_index] is action
    )

def active_plan_kind_for_action(self, action: Action) -> Optional[str]:
    if not self.is_active_plan_action(action):
        return None
    return self.current_plan_kind

def reject_active_plan_action(self, action: Action) -> bool:
    if not self.is_active_plan_action(action):
        return False
    self._clear_current_combat_plan()
    return True

def is_active_lethal_plan_action(self, action: Action) -> bool:
    return self.active_plan_kind_for_action(action) == "lethal"

def invalidate_active_lethal_plan_action(self, action: Action) -> bool:
    if not self.is_active_lethal_plan_action(action):
        return False
    return self.reject_active_plan_action(action)
```

- [ ] **Step 7: Implement metadata classification and screen-independent epoch**

In `CombatRLAgent`, replace lethal-only classification helpers with:

```python
def _fallback_plan_metadata(
    self,
    action: Action,
) -> tuple[bool, Optional[str]]:
    membership = getattr(self.fallback_agent, "is_active_plan_action", None)
    if not callable(membership):
        return False, None
    try:
        active_plan = bool(membership(action))
    except Exception as exc:
        logger.debug("[PLAN_ACK] membership query failed: %s", exc)
        return False, None
    if not active_plan:
        return False, None

    kind_query = getattr(
        self.fallback_agent,
        "active_plan_kind_for_action",
        None,
    )
    if not callable(kind_query):
        return True, None
    try:
        return True, kind_query(action)
    except Exception as exc:
        logger.debug("[PLAN_ACK] kind query failed: %s", exc)
        return True, None

@staticmethod
def _combat_epoch(game: Game):
    return (
        bool(getattr(game, "in_combat", False)),
        getattr(game, "floor", None),
        getattr(game, "turn", None),
    )
```

Use `_combat_epoch()` instead of `_combat_turn_key()` only for lethal-plan quarantine storage and refresh. Keep `_combat_turn_key()` unchanged for takeover activation because it intentionally excludes transient screens.

- [ ] **Step 8: Implement generic rejection and one finalizer**

Add:

```python
def _reject_confirmed_active_plan_action(
    self,
    action: Action,
    game: Game,
    *,
    plan_kind: Optional[str],
) -> bool:
    reject = getattr(self.fallback_agent, "reject_active_plan_action", None)
    rejected = False
    if callable(reject):
        try:
            rejected = bool(reject(action))
        except Exception as exc:
            logger.debug("[PLAN_ACK] rejection failed: %s", exc)
    if rejected:
        return True
    if plan_kind == "lethal":
        self._lethal_plan_quarantine_epoch = self._combat_epoch(game)
        logger.info(
            "[LETHAL_PLAN] precedence=quarantined floor=%s turn=%s",
            getattr(game, "floor", None),
            getattr(game, "turn", None),
        )
    return False

def _finalize_takeover_action(
    self,
    emitted_action: Action,
    selected_action: Optional[Action],
    game: Game,
    *,
    active_plan: bool,
    plan_kind: Optional[str],
    accepted_plan_action: bool,
) -> Optional[Action]:
    if active_plan and not accepted_plan_action:
        self._reject_confirmed_active_plan_action(
            emitted_action,
            game,
            plan_kind=plan_kind,
        )
    return self._with_combat_action_context(selected_action, game)
```

Refresh quarantine with:

```python
def _refresh_lethal_plan_quarantine(self, game: Game) -> None:
    epoch = getattr(self, "_lethal_plan_quarantine_epoch", None)
    if epoch is not None and self._combat_epoch(game) != epoch:
        self._lethal_plan_quarantine_epoch = None
```

- [ ] **Step 9: Route every takeover result through the finalizer**

Immediately after the single fallback call:

```python
fallback_action = self.fallback_agent.get_next_action_in_game(game)
active_plan, plan_kind = self._fallback_plan_metadata(fallback_action)

def finalize(selected_action, *, accepted_plan_action=False):
    return self._finalize_takeover_action(
        fallback_action,
        selected_action,
        game,
        active_plan=active_plan,
        plan_kind=plan_kind,
        accepted_plan_action=accepted_plan_action,
    )
```

Within the takeover branch, replace direct returns as follows:

```python
return finalize(wait_action)                    # wait replaced the emitted plan
return finalize(replacement)                    # any guard replacement
return finalize(EndTurnAction())                # suppression/end-turn replacement
return finalize(fallback_action, accepted_plan_action=True)
return finalize(lethal_prefix_action, accepted_plan_action=True)
```

The lethal helper receives the already classified `active_plan` and
`plan_kind`; it must not query fallback membership again. It may pass through
only when `active_plan is True`, `plan_kind == "lethal"`, quarantine is absent,
the card is legal, the original target is still live, and immediate-death
checks pass.

Use this signature and gate at the start of the existing helper, preserving
its current normalization, legality, HP-cost, Sharp Hide, and logging body:

```python
def _active_validated_lethal_prefix_action(
    self,
    action: Action,
    game: Game,
    *,
    active_plan: bool,
    plan_kind: Optional[str],
) -> Optional[Action]:
    if self._lethal_plan_precedence_is_quarantined(game):
        return None
    if not active_plan or plan_kind != "lethal":
        return None

    candidate = self._normalize_active_lethal_play_card_action(action, game)
    if candidate is None or not self._is_current_combat_action_playable(
        candidate,
        game,
    ):
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

Rejection is intentionally absent from this helper. The single finalizer owns
all acceptance/rejection after the selected action is known.

Every return after fallback acquisition must use `finalize()`. Returns before
fallback acquisition remain unchanged. Generic target repair uses
`accepted_plan_action=False` even when it keeps the same card, because the
cached continuation was planned against a different action state.

- [ ] **Step 10: Run the new regressions and verify GREEN**

Run the Step 5 command with `--basetemp .pytest_tmp_plan_ack_green`.

Expected: all selected cases pass.

- [ ] **Step 11: Run prior lifecycle and guard coverage**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_turn_plan_signature_guards.py::test_optimized_agent_continues_cached_sequence_after_played_card_leaves_hand tests\test_turn_plan_signature_guards.py::test_optimized_agent_replans_when_cached_lethal_target_is_gone tests\test_turn_plan_signature_guards.py::test_optimized_agent_invalidates_only_emitted_active_lethal_action tests\test_combat_rl_guards.py::test_energy_guard_takeover_preserves_safe_hemokinesis_lethal_prefix tests\test_combat_rl_guards.py::test_energy_guard_takeover_lethal_prefix_precedes_early_survival_replacements tests\test_combat_rl_guards.py::test_rejected_lethal_prefix_invalidates_cached_plan_across_takeover_calls tests\test_combat_rl_guards.py::test_energy_guard_takeover_end_turn_queries_fallback_once tests\test_combat_rl_guards.py::test_ordinary_takeover_replacement_does_not_call_lethal_invalidator tests\test_combat_rl_guards.py::test_failed_lethal_invalidation_quarantines_precedence_until_next_turn tests\test_combat_rl_guards.py::test_energy_guard_takeover_rejects_self_lethal_lethal_prefix tests\test_combat_rl_guards.py::test_energy_guard_takeover_rejects_sharp_hide_lethal_prefix tests\test_combat_rl_guards.py::test_energy_guard_takeover_stale_lethal_target_uses_normal_guard_repair tests\test_combat_rl_guards.py::test_energy_guard_takeover_skips_bloodletting_when_hp_loss_makes_incoming_lethal -q -p no:cacheprovider --basetemp .pytest_tmp_plan_ack_covering
```

Expected: exit code 0. Compatibility test names may be updated only when the old helper no longer exists; preserve their behavioral assertions.

- [ ] **Step 12: Run focused and full pytest**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_ironclad_combat_guards.py tests\test_turn_plan_signature_guards.py tests\test_combat_rl_guards.py -q -p no:cacheprovider --basetemp .pytest_tmp_plan_ack_focused

D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_plan_ack_full
```

Expected: both commands exit 0 with no warnings or failures.

- [ ] **Step 13: Validate scope and pre-review OPSX state**

Mark tasks 2.5, 2.6, 3.7, and 3.8 complete after tests succeed. Leave 4.5 unchecked until the independent task review is approved. Run:

```powershell
openspec status --change investigate-lethal-detection-failure --json
openspec validate investigate-lethal-detection-failure --strict
git diff --check
git diff --stat
```

Expected: strict validation succeeds; only OPSX artifacts, two implementation files, and focused tests changed. Live tasks 5.1 through 5.5 remain pending.

- [ ] **Step 14: Commit the acknowledgement behavior**

Stage only:

```powershell
git add -- openspec/changes/investigate-lethal-detection-failure/design.md openspec/changes/investigate-lethal-detection-failure/specs/ai-combat/spec.md openspec/changes/investigate-lethal-detection-failure/tasks.md spirecomm/ai/agent.py spirecomm/ai/rl/agent.py tests/test_turn_plan_signature_guards.py tests/test_combat_rl_guards.py
git commit -m "fix: acknowledge fallback plan actions"
```

Expected: one cohesive architecture-correction commit and no generated reports.

- [ ] **Step 15: Close the independent review task**

After the Subagent-Driven task reviewer reports both spec compliance and task
quality approved, mark only task 4.5 complete. Re-run:

```powershell
openspec status --change investigate-lethal-detection-failure --json
openspec validate investigate-lethal-detection-failure --strict
git diff --check
git add -- openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit --amend --no-edit
```

Expected: strict validation succeeds, the acknowledgement commit includes the
review-complete task state, and only live-validation tasks 5.1 through 5.5
remain pending.

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
- Consumes: an independently approved Task 1 commit.
- Produces: a bounded conservative 25-game no-training report.
- Gate: any causally demonstrated A-class mechanics, legality, or arbitration failure stops qualification.

- [ ] **Step 1: Verify the real launch configuration**

Read and follow `sts-gameplay-ops`, then run:

```powershell
Get-Content 'C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties'
```

Expected: Windows production Python, `scripts/run_training_batch.py`, `--eval`, `--max-games 25`, `--phase conservative`, both trace paths, and no `--train`.

- [ ] **Step 2: Record identity and start a fresh batch**

In one PowerShell session:

```powershell
$cutoff = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$commit = git rev-parse HEAD
$cutoff
$commit
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\PycharmProjects\slay-the-spire-ai\scripts\restart_sts_modded.ps1' -FreshRun
```

Preserve cutoff and commit for all diagnostics and the report.

- [ ] **Step 3: Monitor bounded completion**

Poll current processes, new AI-marked `.run` files, and `ai_debug.log` at intervals no longer than 60 seconds. Completion requires:

```text
Max games reached (25); exiting.
```

Do not treat a running process, menu screen, or fewer than 25 new AI-marked runs as completion.

- [ ] **Step 4: Generate diagnostics**

Run with the recorded cutoff:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\analyze_combat_failures.py --runs-dir 'D:\SteamLibrary\steamapps\common\SlayTheSpire\runs' --character IRONCLAD --count 25 --log-path 'D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log' --decision-trace 'D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_clean.jsonl' --json

D:\anaconda\envs\stsai\python.exe analysis_scripts\summarize_sim_divergence_trace.py --trace 'D:\SteamLibrary\steamapps\common\SlayTheSpire\sim_divergence_trace_clean.jsonl' --since-unix $cutoff --limit-examples 5

Select-String -Path 'D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log' -Pattern 'Invalid command','invalid command','plan_kind=lethal','PLAN_ACK','Max games reached'

Get-Content 'D:\SteamLibrary\steamapps\common\SlayTheSpire\communication_mod_errors.log' -Tail 300
```

- [ ] **Step 5: Classify and report the batch**

Classify every high-impact row as A, B, or C. A means trace-supported mechanics, legality, or arbitration error that can change outcome; B is plausible policy concern without causal proof; C is expected boundary noise.

Create `reports/trainable_baseline_qualification_batch1.md`:

```markdown
# Trainable Baseline Qualification Batch 1

## Batch Identity
- Commit: recorded Task 1 commit hash
- Cutoff: recorded Unix timestamp
- Mode: conservative eval, 25 games, no training
- Completion: 25/25 with `Max games reached (25); exiting`

## Run Outcomes
- Victories: integer from the 25 fresh AI-marked `.run` files
- Average floor: arithmetic mean of `floor_reached` across those 25 runs
- Maximum floor: maximum `floor_reached` across those 25 runs
- Act 1 boss reach: count with `floor_reached >= 16`
- Act 2 reach: count with `floor_reached >= 18`
- Top death clusters: descending `killed_by` counts from those 25 runs

## Execution Correctness
- Invalid commands: fresh-cutoff matching log count
- New uncaught gameplay exceptions: fresh-cutoff attributable traceback count
- Validated lethal prefix pass-throughs: fresh-cutoff log count
- Plan rejections: fresh-cutoff `[PLAN_ACK]` rejection count
- Lethal rejection quarantines: fresh-cutoff quarantine log count

## Sim Divergence
- Fresh events: count returned by the cutoff-bounded divergence summary
- High-impact clusters: named clusters from raw-row inspection
- Unresolved A-class clusters: count after A/B/C classification

## Qualification Decision
- Batch status: clean or failed
- Reason: evidence-backed decision
- Next action: second qualification batch or named regression cluster
```

If an A-class issue exists, write the failed report and stop before Task 3.

- [ ] **Step 6: Update OPSX and commit Batch 1**

When clean, mark tasks 5.1 through 5.4 complete and leave 5.5 unchecked. Run:

```powershell
openspec validate investigate-lethal-detection-failure --strict
git diff --check
git add -- reports/trainable_baseline_qualification_batch1.md openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit -m "docs: record plan acknowledgement qualification batch 1"
```

Expected: report and task state only; raw JSONL remains unstaged.

---

### Task 3: Run the Second Qualification Batch and Close the Change

**Files:**
- Read: the live records and logs listed in Task 2.
- Create: `reports/trainable_baseline_qualification_batch2.md`
- Modify: `openspec/changes/investigate-lethal-detection-failure/tasks.md`

**Interfaces:**
- Consumes: a clean Batch 1 report with zero unresolved A-class failures.
- Produces: a second independently cut 25-game report and completed OPSX change.

- [ ] **Step 1: Confirm Batch 1 eligibility**

Run:

```powershell
openspec instructions apply --change investigate-lethal-detection-failure --json
Get-Content reports\trainable_baseline_qualification_batch1.md
```

Expected: Batch 1 is clean, tasks 5.1 through 5.4 are complete, task 5.5 remains, and no A-class issue is unresolved.

- [ ] **Step 2: Run a second independently cut batch**

Repeat Task 2 Steps 1 through 4 with a new Unix cutoff and current commit. Do not reuse Batch 1 trace rows. Require 25 new AI-marked runs and `Max games reached (25); exiting`.

- [ ] **Step 3: Classify and write Batch 2**

Create `reports/trainable_baseline_qualification_batch2.md` with the same sections as Batch 1 plus:

```markdown
## Two-Batch Promotion
- Batch 1 status: clean
- Batch 2 status: clean or failed
- Consecutive clean batches: `2` only when both reports are clean, otherwise the actual prefix count
- Trainable baseline promoted: yes only when the count is 2
- Frozen baseline commit: current commit hash when promoted
```

If Batch 2 contains an A-class issue, set promotion to `no`, leave task 5.5 unchecked, and name the regression cluster.

- [ ] **Step 4: Complete OPSX and commit**

Only after two clean batches, mark task 5.5 complete and run:

```powershell
openspec instructions apply --change investigate-lethal-detection-failure --json
openspec validate investigate-lethal-detection-failure --strict
git diff --check
git add -- reports/trainable_baseline_qualification_batch2.md openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit -m "docs: qualify fallback plan acknowledgement baseline"
```

Expected: OPSX state `all_done`, all tasks complete, strict validation succeeds, and the change is ready for a separate archive workflow.
