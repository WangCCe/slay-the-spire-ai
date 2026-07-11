# Partial GRID Card Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make partially completed GRID screens select exactly the remaining unselected cards so fresh qualification cannot loop on local cardinality errors.

**Architecture:** `SimpleAgent` computes remaining cardinality from total required minus already selected, removes reconstructed selected-card occurrences through a UUID-first multiset key, and applies existing ranking only to unselected candidates. `CardSelectAction` and coordinator behavior remain strict and unchanged.

**Tech Stack:** Python 3, pytest, OPSX/OpenSpec 1.6.0, CommunicationMod, Windows production Python at `D:\anaconda\envs\stsai\python.exe`.

## Global Constraints

- Use OPSX change `fix-partial-grid-card-selection` as the source of truth.
- Preserve the failed Batch 1 report at `reports/trainable_baseline_qualification_batch1.md`.
- Do not change `CardSelectAction`, coordinator callback timing, HAND_SELECT, ranking policy, RL, route, reward, or training behavior.
- Match selected cards by UUID when present, otherwise canonical identity and upgrade count, consuming duplicates by multiplicity.
- Return exactly `max(0, total_required - selected_count)` new cards for exact-count GRID screens.
- If too few unselected candidates exist, request state refresh instead of constructing an invalid action.
- Run RED regression, minimal fix, focused tests, full pytest, independent review, then a new no-training Batch 1 retry.
- Do not stage historical untracked reports or raw trace files.

---

### Task 1: Fix Partial GRID Selection

**Files:**
- Modify: `spirecomm/ai/agent.py:212`
- Modify: `spirecomm/ai/agent.py:1873`
- Test: `tests/test_agent_basic_card_name_guards.py:225`
- Test: `tests/test_card_select_confirm_guard.py`
- Modify: `openspec/changes/fix-partial-grid-card-selection/tasks.md`

**Interfaces:**
- Produces: `SimpleAgent._grid_card_multiset_key(card) -> tuple`.
- Produces: `SimpleAgent._grid_unselected_cards(cards, selected_cards) -> list`.
- Keeps: `SimpleAgent.handle_screen() -> Action` public behavior.

- [ ] **Step 1: Add the exact partial-Astrolabe regression**

Add to `tests/test_agent_basic_card_name_guards.py`:

```python
def test_grid_partial_selection_only_selects_remaining_unselected_card():
    shockwave = _card("Shockwave")
    shockwave.uuid = "shockwave"
    fiend_fire = _card("Fiend Fire")
    fiend_fire.uuid = "fiend-fire"
    shrug = _card("Shrug It Off")
    shrug.uuid = "shrug"

    selected_shockwave = _card("Shockwave")
    selected_shockwave.uuid = "shockwave"
    selected_fiend_fire = _card("Fiend Fire")
    selected_fiend_fire.uuid = "fiend-fire"

    agent = _agent(
        screen_type=ScreenType.GRID,
        choice_available=True,
        available_commands=["choose", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=[shockwave, fiend_fire, shrug],
            selected_cards=[selected_shockwave, selected_fiend_fire],
            num_cards=3,
            any_number=False,
            confirm_up=False,
            for_upgrade=False,
            for_purge=False,
            for_transform=False,
        ),
    )

    action = agent.handle_screen()

    assert isinstance(action, CardSelectAction)
    assert action.cards == [shrug]
```

- [ ] **Step 2: Add reconstructed duplicate and inconsistent-state controls**

Add `StateAction` to the action imports and add:

```python
def test_grid_unselected_cards_consumes_duplicate_by_multiplicity():
    first_defend = _card("Defend_R")
    second_defend = _card("Defend_R")
    strike = _card("Strike_R")
    selected_defend = _card("Defend_R")
    agent = _agent()

    remaining = agent._grid_unselected_cards(
        [first_defend, second_defend, strike],
        [selected_defend],
    )

    assert remaining == [second_defend, strike]


def test_grid_inconsistent_remaining_count_requests_state_refresh():
    strike = _card("Strike_R")
    selected_strike = _card("Strike_R")
    agent = _agent(
        screen_type=ScreenType.GRID,
        choice_available=True,
        available_commands=["choose", "key", "click", "wait", "state"],
        screen=SimpleNamespace(
            cards=[strike],
            selected_cards=[selected_strike],
            num_cards=2,
            any_number=False,
            confirm_up=False,
            for_upgrade=False,
            for_purge=False,
            for_transform=False,
        ),
    )

    action = agent.handle_screen()

    assert isinstance(action, StateAction)
```

- [ ] **Step 3: Run the new tests and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_agent_basic_card_name_guards.py::test_grid_partial_selection_only_selects_remaining_unselected_card tests\test_agent_basic_card_name_guards.py::test_grid_unselected_cards_consumes_duplicate_by_multiplicity tests\test_agent_basic_card_name_guards.py::test_grid_inconsistent_remaining_count_requests_state_refresh -q -p no:cacheprovider --basetemp .pytest_tmp_partial_grid_red
```

Expected: three failures because the partial screen returns total-card output,
the multiset helper does not exist, and the inconsistent state returns an
invalid `CardSelectAction`.

- [ ] **Step 4: Add stable multiset helpers**

Add beside `_card_ids_for_tracking()` in `SimpleAgent`:

```python
@staticmethod
def _grid_card_multiset_key(card):
    card_uuid = getattr(card, "uuid", None)
    if card_uuid:
        return ("uuid", str(card_uuid))
    return (
        "card",
        canonical_card_name(card),
        card_upgrade_count(card),
    )

@classmethod
def _grid_unselected_cards(cls, cards, selected_cards):
    selected_keys = [
        cls._grid_card_multiset_key(card)
        for card in selected_cards or []
    ]
    unselected = []
    for card in cards or []:
        card_key = cls._grid_card_multiset_key(card)
        try:
            selected_index = selected_keys.index(card_key)
        except ValueError:
            unselected.append(card)
        else:
            selected_keys.pop(selected_index)
    return unselected
```

- [ ] **Step 5: Apply remaining count before existing ranking**

At the start of the GRID selection branch after `screen = self.game.screen`,
compute:

```python
num_required = max(
    0,
    self._safe_int(getattr(screen, "num_cards", 0), 0),
)
already_selected = list(getattr(screen, "selected_cards", []) or [])
num_remaining = max(0, num_required - len(already_selected))
grid_candidates = self._grid_unselected_cards(
    getattr(screen, "cards", []) or [],
    already_selected,
)
if num_remaining > len(grid_candidates):
    logger.warning(
        "[GRID_SCREEN] inconsistent remaining selection: required=%s selected=%s remaining=%s available=%s",
        num_required,
        len(already_selected),
        num_remaining,
        len(grid_candidates),
    )
    return StateAction()
```

Replace each GRID ranking input `self.game.screen.cards` with
`grid_candidates`; do not change sorting keys or branch order. Replace the
final total-count slice:

```python
selected_cards = available_cards[:num_remaining]
logger.debug(
    "[GRID_SCREEN] Returning CardSelectAction with %s/%s remaining cards: %s",
    len(selected_cards),
    num_remaining,
    self._card_ids_for_tracking(selected_cards),
)
return CardSelectAction(selected_cards)
```

Keep strict cardinality validation in `CardSelectAction.execute()` unchanged.

- [ ] **Step 6: Run the RED selection and verify GREEN**

Run Step 3 with `--basetemp .pytest_tmp_partial_grid_green`.

Expected: all three selected tests pass.

- [ ] **Step 7: Run focused GRID, HAND_SELECT, and action tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_agent_basic_card_name_guards.py tests\test_card_select_confirm_guard.py tests\test_deferred_state_callback.py -q -p no:cacheprovider --basetemp .pytest_tmp_partial_grid_focused
```

Expected: exit code 0; existing initial neutral, removal, upgrade, and
HAND_SELECT behavior remains green.

- [ ] **Step 8: Run full pytest**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_partial_grid_full
```

Expected: exit code 0 with no failures.

- [ ] **Step 9: Update OPSX and review scope**

After RED/GREEN and tests succeed, mark tasks 2.1 through 4.4 complete. Leave
4.5 and live tasks pending. Run:

```powershell
openspec validate fix-partial-grid-card-selection --strict
git diff --check
git diff --stat
git diff -- spirecomm/ai/agent.py tests/test_agent_basic_card_name_guards.py
```

Expected: only the OPSX artifacts, one implementation file, and one focused
test file changed; no action, coordinator, HAND_SELECT, ranking, or policy
change.

- [ ] **Step 10: Commit the behavior fix**

Run:

```powershell
git add -- openspec/changes/fix-partial-grid-card-selection spirecomm/ai/agent.py tests/test_agent_basic_card_name_guards.py
git commit -m "fix: honor partial grid selection count"
```

Expected: one cohesive behavior commit. Independent review later marks task
4.5 complete and amends only its task checkbox.

---

### Task 2: Rerun Batch 1 Qualification

**Files:**
- Read: `C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties`
- Read: live `.run`, marker, debug, error, decision, and sim-divergence files.
- Create: `reports/trainable_baseline_qualification_batch1_retry1.md`
- Modify: `openspec/changes/fix-partial-grid-card-selection/tasks.md`
- Modify: `openspec/changes/investigate-lethal-detection-failure/tasks.md`

**Interfaces:**
- Consumes: independently approved partial-GRID behavior commit.
- Produces: a new 25-game retry report while preserving the failed attempt.
- Gate: any A-class cluster stops before the second consecutive qualification batch.

- [ ] **Step 1: Verify configuration and record a new cutoff**

Follow `sts-gameplay-ops`. Confirm production Python, `--eval --max-games 25
--phase conservative`, both trace paths, and no `--train`. Record:

```powershell
$cutoff = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$commit = git rev-parse HEAD
```

- [ ] **Step 2: Start and monitor a fresh retry**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\PycharmProjects\slay-the-spire-ai\scripts\restart_sts_modded.ps1' -FreshRun
```

Require 25 new AI-marked runs and `Max games reached (25); exiting.`. Poll at
intervals no longer than 60 seconds and use screenshot-first diagnosis if
stuck.

- [ ] **Step 3: Audit fresh correctness evidence**

Run the same combat-failure and cutoff-bounded sim-divergence commands used in
the failed Batch 1 attempt. Additionally search:

```powershell
Select-String -Path 'D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log' -Pattern 'Wrong number of cards selected','GRID_SCREEN','Invalid command','Max games reached','PLAN_ACK','plan_kind=lethal'
```

Require zero fresh GRID cardinality exceptions, zero invalid commands, no new
candidate-attributable uncaught exception, and no unresolved A-class cluster.

- [ ] **Step 4: Write the retry report**

Create `reports/trainable_baseline_qualification_batch1_retry1.md` with:

```markdown
# Trainable Baseline Qualification Batch 1 Retry 1

## Batch Identity
- Commit: exact retry HEAD
- Cutoff: exact Unix timestamp
- Mode: conservative eval, 25 games, no training
- Completion: exact fresh run count and completion-marker evidence

## GRID Regression
- Partial GRID callbacks: fresh count
- GRID cardinality exceptions: fresh count
- Evidence: selected/required/remaining examples or `none observed`

## Run Outcomes
- Victories: integer from 25 fresh AI-marked runs
- Average floor: arithmetic mean of `floor_reached`
- Maximum floor: maximum `floor_reached`
- Act 1 boss reach: count with `floor_reached >= 16`
- Act 2 reach: count with `floor_reached >= 18`
- Top death clusters: descending `killed_by` counts

## Execution Correctness
- Invalid commands: fresh count
- New uncaught gameplay exceptions: fresh attributable count
- Lethal pass-throughs: fresh count
- Plan rejections: fresh count
- Lethal quarantines: fresh count

## Sim Divergence
- Fresh events: cutoff-bounded count
- High-impact clusters: named raw-row clusters
- Unresolved A-class clusters: classified count

## Qualification Decision
- Retry status: clean or failed
- Reason: evidence-backed decision
- Next action: second consecutive batch or named regression cluster
```

- [ ] **Step 5: Update OPSX and commit**

When the retry is clean, mark the new change's tasks 5.1 through 5.4 complete
and the original change's tasks 5.1 and 5.2 complete. Leave the original 5.5
pending. Run strict validation for both changes, scope-check, and commit:

```powershell
git add -- reports/trainable_baseline_qualification_batch1_retry1.md openspec/changes/fix-partial-grid-card-selection/tasks.md openspec/changes/investigate-lethal-detection-failure/tasks.md
git commit -m "docs: record partial grid qualification retry"
```

If the retry fails, commit the evidence-backed failed retry report, leave task
states truthful, and stop before the second consecutive batch.
