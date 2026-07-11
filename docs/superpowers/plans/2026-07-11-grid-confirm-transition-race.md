# GRID Confirm Transition Race Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serialize GRID card selection and confirmation across stale CommunicationMod frames so one selection sequence emits exactly one selector and one legal confirm.

**Architecture:** Keep coordinator callback behavior unchanged. Add backward-compatible wait controls to existing action classes, then make only the GRID branch of `CardSelectAction` queue response-waiting selector commands and FIFO `wait 1` barriers before confirmation and after a sent confirm.

**Tech Stack:** Python 3, `pytest`, `collections.deque`, existing spirecomm `Action`/`Coordinator` APIs, CommunicationMod FIFO command protocol, OpenSpec 1.6.0.

## Global Constraints

- Production gameplay SHALL use `D:\anaconda\envs\stsai\python.exe`; never place a WSL Python path in CommunicationMod configuration.
- Do not train, tune, create checkpoints, change RL spaces/rewards, or modify CommunicationMod Java.
- Preserve default readiness and response-wait behavior for non-GRID callers.
- Preserve the qualified HAND_SELECT key and terminal-confirm ordering.
- Use red regression, minimal implementation, focused pytest, full pytest, strict OpenSpec validation, independent review, then fresh live evidence.
- Do not stage unrelated historical untracked reports.

---

### Task 1: Preserve The Stale GRID Frames As Red Regressions

**Files:**
- Modify: `tests/test_card_select_confirm_guard.py`
- Modify: `tests/test_deferred_state_callback.py`

**Interfaces:**
- Consumes: existing `CardSelectAction`, `ChooseAction`, `ClickAction`, `KeyAction`, `WaitAction`, `OptionalCardSelectConfirmAction`, and `Coordinator.receive_game_state_update()` behavior.
- Produces: queue-contract tests for all GRID selector transports and `test_grid_selection_and_confirm_ignore_stale_frames_until_fifo_barriers()` as the end-to-end regression.

- [ ] **Step 1: Replace the old GRID non-blocking assertion with a serialized choose contract**

Update imports in `tests/test_card_select_confirm_guard.py` to include
`ClickAction` and `WaitAction`, then replace
`test_card_select_does_not_confirm_grid_selection_before_confirm_is_available`
with:

```python
def test_grid_choose_selection_queues_response_barriers_before_confirm():
    card = SimpleNamespace(name="Defend_R")
    coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.GRID,
            available_commands=["choose", "cancel", "key", "click", "wait", "state"],
            screen=SimpleNamespace(
                cards=[card],
                selected_cards=[],
                num_cards=1,
                any_number=False,
                confirm_up=False,
                card_positions=[],
            ),
        )
    )

    CardSelectAction([card]).execute(coordinator)
    selector, settle, confirm = list(coordinator.action_queue)

    assert isinstance(selector, ChooseAction)
    assert selector.requires_game_ready is True
    assert selector.wait_for_response is True
    assert isinstance(settle, WaitAction)
    assert settle.requires_game_ready is True
    assert settle.wait_for_response is True
    assert settle.timeout == 1
    assert isinstance(confirm, OptionalCardSelectConfirmAction)
    assert confirm.requires_game_ready is True
    assert confirm.wait_for_response is True
    assert confirm.settle_after_confirm is True
```

- [ ] **Step 2: Add click, key fallback, and unchanged-default contracts**

Append these tests to `tests/test_card_select_confirm_guard.py`:

```python
def test_grid_click_and_key_selectors_use_response_barriers():
    card = SimpleNamespace(name="Defend_R")

    click_coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.GRID,
            available_commands=["click", "key", "wait", "state"],
            screen=SimpleNamespace(
                cards=[card],
                selected_cards=[],
                num_cards=1,
                any_number=False,
                confirm_up=False,
                card_positions=[{"x": 100, "y": 200}],
            ),
        )
    )
    CardSelectAction([card]).execute(click_coordinator)
    click_selector, click_settle, _ = list(click_coordinator.action_queue)
    assert isinstance(click_selector, ClickAction)
    assert click_selector.requires_game_ready is True
    assert click_selector.wait_for_response is True
    assert isinstance(click_settle, WaitAction)
    assert click_settle.wait_for_response is True

    key_coordinator = FakeCoordinator(
        SimpleNamespace(
            screen_type=ScreenType.GRID,
            available_commands=["key", "wait", "state"],
            screen=SimpleNamespace(
                cards=[card],
                selected_cards=[],
                num_cards=1,
                any_number=False,
                confirm_up=False,
                card_positions=[],
            ),
        )
    )
    CardSelectAction([card]).execute(key_coordinator)
    key_selector, key_settle, _ = list(key_coordinator.action_queue)
    assert isinstance(key_selector, KeyAction)
    assert key_selector.requires_game_ready is True
    assert key_selector.wait_for_response is True
    assert isinstance(key_settle, WaitAction)
    assert key_settle.wait_for_response is True


def test_shared_action_serialization_defaults_remain_unchanged():
    click = ClickAction("proceed")
    choose = ChooseAction(0)
    wait = WaitAction(timeout=1)
    confirm = OptionalCardSelectConfirmAction()

    assert click.requires_game_ready is False
    assert click.wait_for_response is False
    assert choose.requires_game_ready is True
    assert choose.wait_for_response is False
    assert wait.requires_game_ready is False
    assert wait.wait_for_response is False
    assert confirm.requires_game_ready is False
    assert confirm.wait_for_response is False
    assert confirm.settle_after_confirm is False
```

- [ ] **Step 3: Add parsed GRID state helpers**

Add after `_hand_select_state_message()` in
`tests/test_deferred_state_callback.py`:

```python
def _grid_state_message(cards, selected, confirm_up, available_commands, choice_list=False):
    game_state = {
        "screen_type": "GRID",
        "room_phase": "COMPLETE",
        "class": "IRONCLAD",
        "screen_state": {
            "cards": cards,
            "selected_cards": selected,
            "num_cards": 1,
            "any_number": False,
            "confirm_up": confirm_up,
            "for_upgrade": False,
            "for_transform": False,
            "for_purge": True,
            "card_positions": [],
        },
    }
    if choice_list:
        game_state["choice_list"] = [card["name"] for card in cards]
    return json.dumps(
        {
            "ready_for_command": True,
            "in_game": True,
            "available_commands": available_commands,
            "game_state": game_state,
        }
    )
```

- [ ] **Step 4: Add the exact two-window stale-frame regression**

Append to `tests/test_deferred_state_callback.py`:

```python
def test_grid_selection_and_confirm_ignore_stale_frames_until_fifo_barriers():
    coordinator = _coordinator_without_threads()
    card = SimpleNamespace(name="Strike_R")
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.GRID,
        available_commands=["choose", "potion", "cancel", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=[card],
            selected_cards=[],
            num_cards=1,
            any_number=False,
            confirm_up=False,
            card_positions=[],
        ),
    )
    callbacks = []
    coordinator.state_change_callback = (
        lambda game: callbacks.append(game.screen_type) or None
    )

    coordinator.action_queue.append(CardSelectAction([card]))
    coordinator.execute_next_action_if_ready()
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "choose 0"
    assert coordinator.game_is_ready is False

    strike = _card_json("Strike_R", "strike-1")
    coordinator.input_queue.put(
        _grid_state_message(
            [strike],
            [],
            False,
            ["choose", "potion", "cancel", "key", "click", "wait", "state"],
            choice_list=True,
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike],
            [strike],
            True,
            ["potion", "confirm", "cancel", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator.game_is_ready is False
    assert callbacks == []

    coordinator.input_queue.put(
        _grid_state_message(
            [strike],
            [strike],
            True,
            ["potion", "confirm", "cancel", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "wait 1"
    assert coordinator.game_is_ready is False
    assert not coordinator._run_deferred_state_callback_if_idle()
    assert callbacks == []

    coordinator.input_queue.put(_event_state_message())
    assert coordinator.receive_game_state_update(block=False, perform_callbacks=True)
    assert callbacks == [ScreenType.EVENT]
    assert coordinator.output_queue.empty()
```

- [ ] **Step 5: Run the red tests and preserve the expected failures**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_card_select_confirm_guard.py tests/test_deferred_state_callback.py -p no:cacheprovider --basetemp .pytest_tmp_grid_confirm_transition_red -q
```

Expected: failures show that `ClickAction`, `ChooseAction`, `WaitAction`, and
`OptionalCardSelectConfirmAction` lack the new wait attributes/options, the
GRID queue lacks settle actions, and the stale-frame regression invokes a GRID
callback or emits commands out of order. Existing unrelated tests remain
green.

---

### Task 2: Implement GRID-Only Protocol Serialization

**Files:**
- Modify: `spirecomm/communication/action.py`
- Test: `tests/test_card_select_confirm_guard.py`
- Test: `tests/test_deferred_state_callback.py`

**Interfaces:**
- Consumes: Task 1 red tests and existing `Coordinator.send_message(message, wait_for_response=True)`.
- Produces: `WaitAction(timeout=1, requires_game_ready=False, wait_for_response=False)`, `ClickAction(target, requires_game_ready=False, wait_for_response=False)`, `ChooseAction(choice_index=0, name=None, wait_for_response=False)`, and `OptionalCardSelectConfirmAction(..., wait_for_response=False, settle_after_confirm=False)`.

- [ ] **Step 1: Extend the ready-wait helper and WaitAction without changing defaults**

Change `_queue_ready_wait()` and `WaitAction` in
`spirecomm/communication/action.py` to:

```python
def _queue_ready_wait(coordinator, timeout=1, wait_for_response=False):
    add_action_to_queue = getattr(coordinator, "add_action_to_queue", None)
    if callable(add_action_to_queue):
        add_action_to_queue(
            WaitAction(
                timeout=timeout,
                requires_game_ready=True,
                wait_for_response=wait_for_response,
            )
        )


class WaitAction(Action):
    """An action to use the CommunicationMod 'Wait' command to trigger a state update"""

    def __init__(
        self,
        timeout=1,
        requires_game_ready=False,
        wait_for_response=False,
    ):
        super().__init__("wait", requires_game_ready=requires_game_ready)
        self.timeout = timeout
        self.wait_for_response = wait_for_response

    def execute(self, coordinator):
        coordinator.send_message(
            f"{self.command} {self.timeout}",
            wait_for_response=self.wait_for_response,
        )
```

- [ ] **Step 2: Add opt-in waiting to ClickAction and ChooseAction**

Change their constructors and sends to:

```python
class ClickAction(Action):
    """An action to use the CommunicationMod 'Click' command"""

    def __init__(
        self,
        target,
        requires_game_ready=False,
        wait_for_response=False,
    ):
        super().__init__("click", requires_game_ready=requires_game_ready)
        self.target = target
        self.wait_for_response = wait_for_response

    def execute(self, coordinator):
        payload = self._resolve_payload(coordinator)
        coordinator.send_message(
            f"{self.command} {payload}",
            wait_for_response=self.wait_for_response,
        )
```

```python
class ChooseAction(Action):
    """An action to use the CommunicationMod 'Choose' command"""

    def __init__(self, choice_index=0, name=None, wait_for_response=False):
        super().__init__("choose", requires_game_ready=True)
        self.choice_index = choice_index
        self.name = name
        self.wait_for_response = wait_for_response
```

In both branches of `ChooseAction.execute()`, replace the hard-coded
`wait_for_response=False` with `wait_for_response=self.wait_for_response`.
Do not change its stale-command or event-ready special cases.

- [ ] **Step 3: Serialize optional GRID confirm and its transition barrier**

Change `OptionalCardSelectConfirmAction` to accept and use:

```python
def __init__(
    self,
    allow_stale_selection=False,
    requires_game_ready=False,
    wait_for_response=False,
    settle_after_confirm=False,
):
    super().__init__("confirm", requires_game_ready=requires_game_ready)
    self.allow_stale_selection = allow_stale_selection
    self.wait_for_response = wait_for_response
    self.settle_after_confirm = settle_after_confirm
```

Replace its confirm send with:

```python
coordinator.send_message(
    self.command,
    wait_for_response=self.wait_for_response,
)
if self.settle_after_confirm:
    _queue_ready_wait(coordinator, wait_for_response=True)
return
```

- [ ] **Step 4: Queue GRID selectors and one-frame barriers**

Replace the GRID selector branch in `CardSelectAction.execute()` with:

```python
if screen_type == ScreenType.GRID:
    available = getattr(coordinator.last_game_state, "available_commands", [])
    positions = getattr(screen, "card_positions", [])
    if "click" in available and positions:
        selector = ClickAction(
            ("card", index, 0),
            requires_game_ready=True,
            wait_for_response=True,
        )
    elif "choose" in available:
        selector = ChooseAction(
            choice_index=index,
            wait_for_response=True,
        )
    else:
        selector = KeyAction(
            f"CARD_{index + 1}",
            requires_game_ready=True,
            wait_for_response=True,
        )
    coordinator.add_action_to_queue(selector)
    coordinator.add_action_to_queue(
        WaitAction(
            timeout=1,
            requires_game_ready=True,
            wait_for_response=True,
        )
    )
else:
    coordinator.add_action_to_queue(
        KeyAction(
            f"CARD_{index + 1}",
            requires_game_ready=True,
            wait_for_response=True,
        )
    )
```

Then replace the terminal optional-confirm construction with:

```python
is_grid = screen_type == ScreenType.GRID
coordinator.add_action_to_queue(
    OptionalCardSelectConfirmAction(
        allow_stale_selection=True,
        requires_game_ready=(screen_type in [ScreenType.HAND_SELECT, ScreenType.GRID]),
        wait_for_response=is_grid,
        settle_after_confirm=is_grid,
    )
)
```

- [ ] **Step 5: Run the focused tests to green**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_card_select_confirm_guard.py tests/test_deferred_state_callback.py tests/test_agent_basic_card_name_guards.py -p no:cacheprovider --basetemp .pytest_tmp_grid_confirm_transition_focused -q
```

Expected: all tests pass. The parsed-state regression's output queue contains
only `choose 0`, `wait 1`, `confirm`, and `wait 1` in that order, with no GRID
callback from either stale frame.

- [ ] **Step 6: Run the full suite**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp .pytest_tmp_grid_confirm_transition_full -q
```

Expected: the full suite passes with no new failure.

- [ ] **Step 7: Validate the OpenSpec change and diff**

Run:

```powershell
openspec validate fix-grid-confirm-transition-race --strict
git diff --check
```

Expected: strict validation succeeds and `git diff --check` reports no error.

- [ ] **Step 8: Obtain independent review and resolve findings**

Give the reviewer the design, proposal, delta spec, task list, implementation
plan, live failure excerpt, and behavior diff. Require separate checks for:

```text
spec compliance
default compatibility
one-selector/one-confirm ordering
stale-frame callback suppression
test sufficiency
unrelated scope
```

Apply only verified findings. Rerun Steps 5 through 7 after any edit.

- [ ] **Step 9: Commit the reviewed behavior**

Run:

```powershell
git add -- spirecomm/communication/action.py tests/test_card_select_confirm_guard.py tests/test_deferred_state_callback.py openspec/changes/fix-grid-confirm-transition-race/tasks.md
git commit -m "fix: serialize grid selection transitions"
```

Expected: one cohesive behavior commit; historical untracked reports remain
unstaged.

---

### Task 3: Run And Review The Fresh Batch 2 Retry

**Files:**
- Create: `reports/trainable_baseline_qualification_batch2_retry1.md`
- Modify conditionally: `openspec/changes/investigate-lethal-detection-failure/tasks.md`
- Modify: `openspec/changes/fix-grid-confirm-transition-race/tasks.md`
- Modify: `.superpowers/sdd/progress.md` (operational ledger; stage only if tracked by repository policy)

**Interfaces:**
- Consumes: reviewed behavior commit from Task 2, eligible `reports/trainable_baseline_qualification_batch1_retry2.md`, live CommunicationMod config, run markers, `.run` files, debug/error logs, decision trace, and sim-divergence trace.
- Produces: one complete independently reviewed 25-game Batch 2 retry or one preserved failed attempt with promotion still blocked.

- [ ] **Step 1: Record immutable launch eligibility and baselines**

Run and preserve outputs for:

```powershell
git rev-parse HEAD
Get-Content C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties
openspec instructions apply --change investigate-lethal-detection-failure --json
Get-FileHash reports\trainable_baseline_qualification_batch1.md -Algorithm SHA256
Get-FileHash reports\trainable_baseline_qualification_batch1_retry1.md -Algorithm SHA256
Get-FileHash reports\trainable_baseline_qualification_batch1_retry2.md -Algorithm SHA256
```

Record a fresh Unix cutoff, AI marker count and last marker, completion-marker
count, active/rotated debug sizes, error-log size, and both trace sizes. Confirm
the command uses Windows Python, `--eval --max-games 25 --phase conservative`,
and no `--train`.

- [ ] **Step 2: Launch exactly one fresh batch**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_sts_modded.ps1 -FreshRun
```

Expected: one ModTheSpire launch, no stale Ironclad autosave, one batch wrapper,
and one gameplay Python process.

- [ ] **Step 3: Monitor bounded live evidence**

At approximately 50-second intervals, record marker growth and scan only the
post-cutoff debug/error/decision/sim evidence for:

```text
Invalid command
Traceback
Wrong number of cards selected
HAND_SELECT key/confirm ordering
GRID selector/barrier/confirm ordering
lethal pass_through acknowledgement
```

Stop immediately on an A-class command rejection, uncaught gameplay exception,
cardinality failure, or repeated demonstrated mechanics cluster. Otherwise
allow exactly 25 completed games and one new completion marker.

- [ ] **Step 4: Build the durable retry report**

Create `reports/trainable_baseline_qualification_batch2_retry1.md` with exact:

```text
candidate/cutoff/config/launch identity
pre/post hashes and log/trace baselines
25 unique marker-to-run pairs
floor, victory, and killed_by outcomes
invalid-command and exception counts
HAND_SELECT and GRID ordering counts
lethal acknowledgement counts
fresh sim-divergence A/B/C classification
two-batch promotion decision
first-victory status
OPSX task state
```

Do not call an incomplete or failed attempt a qualification result.

- [ ] **Step 5: Obtain independent raw-evidence review**

Require the reviewer to recompute marker/run uniqueness, completion count,
debug/error deltas, selector/confirm legality, lethal counts, sim classes,
report hashes, and task state from raw files rather than trusting the report.
Correct every factual discrepancy and re-review the corrections.

- [ ] **Step 6: Update task state only if evidence qualifies**

If and only if all 25 games are complete and the independent review finds no
A-class failure, mark task 5.5 in
`openspec/changes/investigate-lethal-detection-failure/tasks.md` complete and
record two consecutive eligible batches. Otherwise leave it unchecked and
preserve the failure report.

- [ ] **Step 7: Commit only reviewed evidence**

Stage the retry report and only task files whose state genuinely changed, then
run:

```powershell
git diff --cached --check
git commit -m "docs: record grid serialization qualification retry"
```

Do not train, tune, create checkpoints, freeze a baseline after a failed batch,
or archive changes as part of this task.
