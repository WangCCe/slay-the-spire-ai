# HAND_SELECT Confirm Race Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serialize HAND_SELECT confirmation after the final card-key response so stale acknowledgements cannot trigger duplicate decisions or illegal `confirm` commands.

**Architecture:** `CardSelectAction` keeps its existing key-command sequence but makes the terminal optional confirm ready-gated for HAND_SELECT only. A real `Coordinator` regression drives two key commands and two parsed HAND_SELECT state messages to prove the final-key acknowledgement is consumed by the queued confirmation rather than a new agent callback.

**Tech Stack:** Python 3, pytest, OPSX/OpenSpec 1.6.0, CommunicationMod, Windows production Python at `D:\anaconda\envs\stsai\python.exe`.

## Global Constraints

- Use OPSX change `fix-hand-select-confirm-race` as the source of truth.
- Preserve `reports/trainable_baseline_qualification_batch1.md` and `reports/trainable_baseline_qualification_batch1_retry1.md` as audit evidence.
- Change only HAND_SELECT terminal-confirm readiness; do not change GRID, selection policy, `ProceedAction`, generic coordinator callback behavior, RL, route, shop, event, reward, or training behavior.
- Run RED before changing production code, then focused pytest, full pytest, strict OPSX validation, and independent review.
- Use `D:\anaconda\envs\stsai\python.exe` and `-p no:cacheprovider --basetemp <repo-local-path>` for tests.
- Do not stage historical untracked reports or raw trace files.
- Do not start formal training; the live gate is conservative evaluation only.

---

### Task 1: Serialize HAND_SELECT Terminal Confirmation

**Files:**
- Modify: `tests/test_card_select_confirm_guard.py:46`
- Modify: `tests/test_deferred_state_callback.py:1`
- Modify: `spirecomm/communication/action.py:716`
- Modify: `openspec/changes/fix-hand-select-confirm-race/tasks.md`

**Interfaces:**
- Consumes: `CardSelectAction.execute(coordinator) -> None` and `Coordinator.receive_game_state_update(block=False, perform_callbacks=True) -> bool`.
- Preserves: `OptionalCardSelectConfirmAction(allow_stale_selection=False, requires_game_ready=False)` constructor.
- Produces: HAND_SELECT queues terminal `OptionalCardSelectConfirmAction(requires_game_ready=True)`; GRID retains `requires_game_ready=False`.

- [ ] **Step 1: Tighten the action queue contract**

In `tests/test_card_select_confirm_guard.py`, replace the terminal readiness assertion in `test_hand_select_card_select_waits_between_keys_and_confirm`:

```python
    assert all(action.requires_game_ready for action in queued_actions)
    assert all(action.wait_for_response for action in queued_actions[:2])
```

Extend `test_card_select_does_not_confirm_grid_selection_before_confirm_is_available` before draining the queue:

```python
    queued_actions = list(coordinator.action_queue)
    assert isinstance(queued_actions[-1], OptionalCardSelectConfirmAction)
    assert queued_actions[-1].requires_game_ready is False
```

- [ ] **Step 2: Add parsed HAND_SELECT state helpers**

Add `CardSelectAction` to the action imports in `tests/test_deferred_state_callback.py`, then add these helpers below `_stale_none_combat_message()`:

```python
def _card_json(name, uuid):
    return {
        "id": name,
        "name": name,
        "type": "SKILL",
        "rarity": "COMMON",
        "upgrades": 0,
        "has_target": False,
        "cost": 1,
        "uuid": uuid,
    }


def _hand_select_state_message(hand, selected, available_commands):
    return json.dumps(
        {
            "ready_for_command": True,
            "in_game": True,
            "available_commands": available_commands,
            "game_state": {
                "screen_type": "HAND_SELECT",
                "room_phase": "COMBAT",
                "class": "IRONCLAD",
                "current_action": "discard",
                "screen_state": {
                    "hand": hand,
                    "selected": selected,
                    "max_cards": 2,
                    "can_pick_zero": False,
                },
            },
        }
    )
```

- [ ] **Step 3: Add the live interleaving regression**

Add to `tests/test_deferred_state_callback.py`:

```python
def test_hand_select_confirm_waits_for_final_key_response_without_stale_callback():
    coordinator = _coordinator_without_threads()
    cards = [
        SimpleNamespace(name="Card 1"),
        SimpleNamespace(name="Card 2"),
    ]
    coordinator.last_game_state = SimpleNamespace(
        screen_type=ScreenType.HAND_SELECT,
        available_commands=["choose", "confirm", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=cards,
            selected_cards=[],
            num_cards=2,
            can_pick_zero=False,
        ),
    )
    callbacks = []
    coordinator.state_change_callback = (
        lambda game: callbacks.append(game.screen_type) or ChooseAction(0)
    )

    coordinator.action_queue.append(CardSelectAction(cards))
    coordinator.execute_next_action_if_ready()
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "key CARD_2"

    first = _card_json("Card 1", "card-1")
    second = _card_json("Card 2", "card-2")
    coordinator.input_queue.put(
        _hand_select_state_message(
            [first, second],
            [second],
            ["choose", "confirm", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(
        block=False,
        perform_callbacks=True,
    )
    assert callbacks == []

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "key CARD_1"
    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.empty()

    coordinator.input_queue.put(
        _hand_select_state_message(
            [first, second],
            [first, second],
            ["confirm", "key", "click", "wait", "state"],
        )
    )
    assert coordinator.receive_game_state_update(
        block=False,
        perform_callbacks=True,
    )
    assert callbacks == []

    coordinator.execute_next_action_if_ready()
    assert coordinator.output_queue.get_nowait() == "confirm"
    assert coordinator.output_queue.empty()
    assert not coordinator._run_deferred_state_callback_if_idle()
    assert callbacks == []
```

- [ ] **Step 4: Run the regressions and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_card_select_confirm_guard.py::test_hand_select_card_select_waits_between_keys_and_confirm tests\test_card_select_confirm_guard.py::test_card_select_does_not_confirm_grid_selection_before_confirm_is_available tests\test_deferred_state_callback.py::test_hand_select_confirm_waits_for_final_key_response_without_stale_callback -q -p no:cacheprovider --basetemp .pytest_tmp_hand_select_confirm_red
```

Expected: the GRID control passes; the queue-contract test fails because the terminal HAND_SELECT optional confirm is not ready-gated; the interleaving regression fails because old code emits `confirm` immediately after `key CARD_1`.

- [ ] **Step 5: Restore HAND_SELECT-only ready serialization**

In `CardSelectAction.execute()` in `spirecomm/communication/action.py`, construct the terminal action as:

```python
        coordinator.add_action_to_queue(
            OptionalCardSelectConfirmAction(
                allow_stale_selection=True,
                requires_game_ready=(screen_type == ScreenType.HAND_SELECT),
            )
        )
```

Do not modify `OptionalCardSelectConfirmAction.execute()`, `Coordinator`, or the agent screen handler.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_card_select_confirm_guard.py tests\test_deferred_state_callback.py tests\test_agent_basic_card_name_guards.py -q -p no:cacheprovider --basetemp .pytest_tmp_hand_select_confirm_focused
```

Expected: all focused tests pass, including the new interleaving regression and unchanged GRID controls.

- [ ] **Step 7: Run full pytest**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_hand_select_confirm_full
```

Expected: the full suite passes with no failures or errors.

- [ ] **Step 8: Update OPSX tasks and validate**

In `openspec/changes/fix-hand-select-confirm-race/tasks.md`, mark tasks 2.1-2.4, 3.1-3.3, and 4.1-4.3 complete. Then run:

```powershell
openspec validate fix-hand-select-confirm-race --strict
git diff --check
```

Expected: the change is valid and `git diff --check` emits no errors.

- [ ] **Step 9: Commit the behavior fix**

```powershell
git add -- spirecomm/communication/action.py tests/test_card_select_confirm_guard.py tests/test_deferred_state_callback.py openspec/changes/fix-hand-select-confirm-race/tasks.md
git commit -m "fix: serialize hand select confirmation"
```

- [ ] **Step 10: Obtain independent review**

Review the behavior commit against the OPSX proposal, design, spec, and this plan. Require explicit approval for root-cause coverage, HAND_SELECT ordering, GRID non-regression, test quality, focused/full test evidence, and scope. Address all important findings, rerun focused/full tests after code changes, then mark OPSX tasks 4.4 and 4.5 complete.

---

### Task 2: Re-run Batch 1 Qualification

**Files:**
- Create: `reports/trainable_baseline_qualification_batch1_retry2.md`
- Modify: `openspec/changes/fix-hand-select-confirm-race/tasks.md`
- Modify: `openspec/changes/fix-partial-grid-card-selection/tasks.md`
- Modify: `openspec/changes/investigate-lethal-detection-failure/tasks.md`

**Interfaces:**
- Consumes: the reviewed behavior-fix commit from Task 1 and the real CommunicationMod config at `C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties`.
- Produces: one cutoff-bounded 25-game conservative no-training report with fresh run, active/rotated log, decision trace, and sim-divergence evidence.

- [ ] **Step 1: Establish the candidate and fresh cutoff**

Record `git rev-parse HEAD`, re-read the real CommunicationMod config, confirm it uses Windows production Python, `--eval --max-games 25 --phase conservative`, both clean trace paths, and no `--train`. Record the current Unix cutoff and AI marker count in the task report.

- [ ] **Step 2: Launch one fresh run batch**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restart_sts_modded.ps1 -FreshRun
```

Monitor at intervals no longer than 60 seconds. Stop immediately on a causally demonstrated A-class command-legality failure, uncaught gameplay exception, or repeatable high-impact sim-divergence cluster. Do not start Batch 2 from this task.

- [ ] **Step 3: Audit cutoff-bounded evidence**

Require exactly 25 new AI markers and 25 matching `.run` files plus the `Max games reached (25); exiting.` marker. Inspect both active and rotated fresh `ai_debug` segments, `communication_mod_errors.log`, decision trace rows, and sim-divergence rows. Count HAND_SELECT confirmations, invalid commands, GRID cardinality exceptions, uncaught exceptions, plan acknowledgements/rejections/quarantines, run outcomes, and A/B/C clusters.

- [ ] **Step 4: Write the retry report**

Create `reports/trainable_baseline_qualification_batch1_retry2.md` with candidate/cutoff/config identity, completion evidence, per-run table, execution correctness, HAND_SELECT and GRID regressions, lethal acknowledgement evidence, sim-divergence classification, and qualification decision. Preserve the two earlier reports unchanged.

- [ ] **Step 5: Update task state and commit the report**

If all 25 runs complete with zero gated failures, mark tasks 5.1-5.4 in `fix-hand-select-confirm-race`, tasks 5.1-5.4 in `fix-partial-grid-card-selection`, and tasks 5.1-5.4 in `investigate-lethal-detection-failure` complete. If the batch fails, leave completion/zero-error tasks pending and mark only evidence/report tasks complete.

Run strict validation for every changed OPSX change, then commit only the new report and task files:

```powershell
git add -- reports/trainable_baseline_qualification_batch1_retry2.md openspec/changes/fix-hand-select-confirm-race/tasks.md openspec/changes/fix-partial-grid-card-selection/tasks.md openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit -m "docs: record hand select qualification retry"
```

- [ ] **Step 6: Obtain independent evidence review**

Require the reviewer to reconcile marker/run counts, active and rotated log counts, completion marker, invalid-command grouping, HAND_SELECT/GRID regressions, exceptions, sim-divergence classifications, preserved reports, and OPSX task state. Correct factual findings before treating Batch 1 as qualified.
