# Non-Combat RL Decision Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pre-training loop for shop, event, route, and card-reward RL decisions by exporting trainable samples, joining conservative live outcomes, and reporting a fixed fresh-eval promotion gate while keeping formal non-combat RL training disabled.

**Architecture:** Add one focused analysis module on top of the existing decision trace and offline comparator. The module exports canonical sample dictionaries, normalizes candidate actions, attaches conservative `.run` outcomes, renders readiness reports, and reports a training guard; it does not mutate live gameplay decisions or import Bottled at runtime.

**Tech Stack:** Python standard library dataclasses/JSON/argparse, existing pytest setup, existing `analysis_scripts/offline_decision_comparator.py`, existing `analysis_scripts/diagnose_live_batch.py`, existing Windows Python test command.

---

## File Structure

- Create `analysis_scripts/noncombat_rl_decision_loop.py`: canonical schema, trace export, candidate normalization, Bottled/current labels via comparator reuse, outcome join, reward-readiness contract, promotion gate, Markdown/JSONL report CLI, combat RL smoke command text.
- Create `tests/test_noncombat_rl_decision_loop.py`: focused TDD tests for export, candidate IDs, partial evidence, outcome joins, reward-readiness gate, report sections, and smoke-command separation.
- Modify `openspec/changes/add-noncombat-rl-decision-loop/tasks.md`: mark tasks complete only after each matching test and report step succeeds.
- Modify `analysis_scripts/offline_decision_comparator.py`: add a tiny public `sample_from_trace_event(event, index=0)` wrapper around the existing trace normalizer; keep existing comparator behavior unchanged.
- Optional create `reports/noncombat_rl_decision_loop_fresh_eval.md`: generated report from local trace/run inputs after implementation.

## Public API Target

`analysis_scripts/noncombat_rl_decision_loop.py` should expose these stable functions:

```python
SCHEMA_VERSION = "noncombat-rl-decision-v1"

def export_samples_from_trace(path, tail=2000, since_unix=None):
    """Return list[dict] canonical samples from decision-trace JSONL rows."""

def build_trainable_sample(decision_sample, comparison_row, trace_event=None):
    """Return one canonical sample dict from a comparator sample and comparison."""

def normalize_candidates(decision_sample):
    """Return list[dict] candidate actions for shop/event/route/card_reward."""

def load_run_outcomes(runs_dir, character="IRONCLAD", limit=20, ai_markers_path=None):
    """Return list[dict] conservative run outcomes parsed from .run files."""

def attach_live_outcomes(samples, outcomes, tolerance_seconds=30):
    """Return samples with outcome_join status matched/missing/ambiguous."""

def default_reward_contract():
    """Return reportable reward-readiness contract without training weights."""

def evaluate_promotion(samples, reward_contract=None, min_complete_per_category=1, min_matched_outcomes=1):
    """Return dict with status allowed/blocked, metrics, and blocking_reasons."""

def render_readiness_report(samples, gate_result):
    """Return Markdown report for fresh-eval readiness."""

def combat_rl_smoke_command(python, game_dir, max_games=1):
    """Return a bounded combat_rl smoke command for training-pipeline health."""
```

## Canonical Sample Shape

Every exported sample dictionary must include:

```python
{
    "schema_version": "noncombat-rl-decision-v1",
    "sample_id": "trace:0",
    "category": "shop",
    "source": "decision_trace",
    "floor": 3,
    "act": 1,
    "unix_time": 1780000000.0,
    "state": {
        "player": {"current_hp": 68, "max_hp": 80},
        "gold": 99,
        "deck": ["Strike", "Defend", "Bash"],
        "relics": ["Burning Blood"],
        "potions": [],
        "screen": {"type": "SHOP_SCREEN"},
    },
    "candidate_actions": [
        {"action_id": "shop:buy_card:perfected_strike", "kind": "buy_card", "label": "Perfected Strike", "available": True, "raw": {"price": 72}},
        {"action_id": "shop:purge:strike", "kind": "purge", "label": "purge Strike", "available": True, "raw": {"cost": 75}},
        {"action_id": "shop:leave", "kind": "leave", "label": "leave", "available": True, "raw": {}},
    ],
    "selected_action_id": "shop:purge:strike",
    "current_policy_label": {"label": "purge Strike", "action_id": "shop:purge:strike"},
    "bottled_label": {"label": "Perfected Strike", "action_id": "shop:buy_card:perfected_strike", "confidence": "high", "reason": "Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge."},
    "evidence_quality": "complete",
    "limitations": [],
    "outcome": {"join_status": "missing", "included_in_gate": False},
}
```

## Task 1: RED Tests For Canonical Trace Export

**Files:**
- Create: `tests/test_noncombat_rl_decision_loop.py`
- Create later through implementation: `analysis_scripts/noncombat_rl_decision_loop.py`

- [ ] **Step 1: Add deterministic trace-row helpers to the test file**

Add helpers that write one JSONL row per supported category. Use compact rows that match `decision_trace.py` output:

```python
import json


def _write_trace(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def _base_trace_row(screen_type, action, screen):
    return {
        "timestamp": "2026-06-18T00:00:00.000Z",
        "unix_time": 1780000000.0,
        "source": "combat_rl",
        "decision_path": "fallback_noncombat",
        "floor": 3,
        "act": 1,
        "room_type": "",
        "screen_type": screen_type,
        "in_combat": False,
        "gold": 99,
        "player": {"current_hp": 68, "max_hp": 80, "block": 0, "energy": 0},
        "deck": [{"name": "Strike"}, {"name": "Defend"}, {"name": "Bash"}],
        "relics": [{"name": "Burning Blood"}],
        "potions": [],
        "screen": screen,
        "action": action,
    }
```

- [ ] **Step 2: Write the failing complete-export test**

Add a test that expects all four categories, stable candidate IDs, current label, Bottled label, and complete evidence:

```python
def test_exports_complete_noncombat_samples_from_trace(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import SCHEMA_VERSION, export_samples_from_trace

    rows = [
        _base_trace_row(
            "CARD_REWARD",
            {"type": "ChooseAction", "name": "Clothesline", "choice_index": 0},
            {"type": "CARD_REWARD", "cards": [{"name": "Clothesline"}, {"name": "Perfected Strike"}], "can_skip": True, "can_bowl": False},
        ),
        _base_trace_row(
            "SHOP_SCREEN",
            {"type": "BuyPurgeAction", "name": "purge", "card_to_purge": {"name": "Strike"}},
            {"type": "SHOP_SCREEN", "cards": [{"name": "Perfected Strike", "price": 72}], "relics": [], "potions": [], "purge_available": True, "purge_cost": 75},
        ),
        _base_trace_row(
            "EVENT",
            {"type": "ChooseAction", "choice_index": 1},
            {"type": "EVENT", "event_name": "Golden Shrine", "event_id": "Golden Shrine", "options": [{"label": "Pray"}, {"label": "Leave"}]},
        ),
        _base_trace_row(
            "MAP",
            {"type": "ChooseMapNodeAction", "choice_index": 0, "node": {"x": 0, "y": 1, "symbol": "M"}},
            {"type": "MAP", "next_nodes": [{"x": 0, "y": 1, "symbol": "M"}], "paths": [{"choice": 0, "label": "M@0,1 -> ?@0,2", "nodes": ["M", "?"]}]},
        ),
    ]
    trace_path = tmp_path / "trace.jsonl"
    _write_trace(trace_path, rows)

    samples = export_samples_from_trace(trace_path)

    assert [sample["schema_version"] for sample in samples] == [SCHEMA_VERSION] * 4
    assert {sample["category"] for sample in samples} == {"card_reward", "shop", "event", "route"}
    shop = next(sample for sample in samples if sample["category"] == "shop")
    assert {candidate["action_id"] for candidate in shop["candidate_actions"]} >= {
        "shop:buy_card:perfected_strike",
        "shop:purge:strike",
        "shop:leave",
    }
    assert shop["selected_action_id"] == "shop:purge:strike"
    assert shop["current_policy_label"]["label"] == "purge Strike"
    assert shop["bottled_label"]["label"] == "Perfected Strike"
    assert shop["evidence_quality"] == "complete"
    assert shop["outcome"]["join_status"] == "missing"
```

- [ ] **Step 3: Write the failing partial-export test**

```python
def test_partial_trace_sample_preserves_limitations(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            {
                "unix_time": 1780000001.0,
                "screen_type": "SHOP_SCREEN",
                "floor": 3,
                "act": 1,
                "screen": {"type": "SHOP_SCREEN", "cards": []},
                "action": {"type": "LeaveAction", "name": "leave"},
            }
        ],
    )

    [sample] = export_samples_from_trace(trace_path)

    assert sample["category"] == "shop"
    assert sample["evidence_quality"] == "partial"
    assert sample["limitations"]
    assert sample["candidate_actions"][-1]["action_id"] == "shop:leave"
```

- [ ] **Step 4: Run RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_rl_decision_loop.py::test_exports_complete_noncombat_samples_from_trace tests/test_noncombat_rl_decision_loop.py::test_partial_trace_sample_preserves_limitations -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_red_1
```

Expected: fail with `ModuleNotFoundError: No module named 'analysis_scripts.noncombat_rl_decision_loop'`.

## Task 2: GREEN Implementation For Export And Candidate Normalization

**Files:**
- Create: `analysis_scripts/noncombat_rl_decision_loop.py`
- Optional modify: `analysis_scripts/offline_decision_comparator.py`

- [ ] **Step 1: Create the module with dataclasses and serialization helpers**

Implement concrete data helpers in the new module:

```python
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from analysis_scripts.offline_decision_comparator import compare_samples, sample_from_trace_event


SCHEMA_VERSION = "noncombat-rl-decision-v1"


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _name(item: Any) -> str:
    return str((item or {}).get("name") or (item or {}).get("id") or "").strip()
```

If `sample_from_trace_event` does not exist yet, add this compatibility wrapper to `analysis_scripts/offline_decision_comparator.py` before importing it from the new module:

```python
def sample_from_trace_event(event: Dict[str, Any], index: int = 0) -> Optional[DecisionSample]:
    return _sample_from_trace_event(event, index)
```

- [ ] **Step 2: Implement `export_samples_from_trace`**

Decode bounded JSONL rows, reuse comparator normalization and comparison, then build canonical samples:

```python
def export_samples_from_trace(path, tail=2000, since_unix=None):
    rows = deque(maxlen=max(1, tail))
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            rows.append(line)

    exported = []
    for index, line in enumerate(rows):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_time = _to_float(event.get("unix_time"))
        if since_unix is not None and (event_time is None or event_time < since_unix):
            continue
        decision_sample = sample_from_trace_event(event, index)
        if decision_sample is None:
            continue
        comparison_row = compare_samples([decision_sample])[0]
        exported.append(build_trainable_sample(decision_sample, comparison_row, trace_event=event))
    return exported
```

- [ ] **Step 3: Implement candidate normalization**

Candidate IDs must be deterministic:

```python
def normalize_candidates(decision_sample):
    category = decision_sample.category
    ctx = decision_sample.context
    if category == "card_reward":
        candidates = [
            _candidate(f"card_reward:take:{_slug(card)}", "take", str(card), True, {"name": card})
            for card in ctx.get("offered", [])
        ]
        if ctx.get("can_bowl"):
            candidates.append(_candidate("card_reward:bowl", "bowl", "bowl", True, {}))
        if ctx.get("can_skip", True):
            candidates.append(_candidate("card_reward:skip", "skip", "skip", True, {}))
        return candidates
    if category == "shop":
        candidates = []
        for card in ctx.get("cards", []):
            candidates.append(_candidate(f"shop:buy_card:{_slug(card.get('name'))}", "buy_card", card.get("name", ""), True, dict(card)))
        for relic in ctx.get("relics", []):
            candidates.append(_candidate(f"shop:buy_relic:{_slug(relic.get('name'))}", "buy_relic", relic.get("name", ""), True, dict(relic)))
        for potion in ctx.get("potions", []):
            candidates.append(_candidate(f"shop:buy_potion:{_slug(potion.get('name'))}", "buy_potion", potion.get("name", ""), True, dict(potion)))
        if ctx.get("purge_available"):
            purge_target = _first_removable_card(ctx.get("deck", []))
            candidates.append(_candidate(f"shop:purge:{_slug(purge_target)}", "purge", f"purge {purge_target}", True, {"cost": ctx.get("purge_cost")}))
        candidates.append(_candidate("shop:leave", "leave", "leave", True, {}))
        return candidates
    if category == "event":
        return [
            _candidate(f"event:choice:{index}", "choose", f"choose {index}: {label}", True, {"index": index, "label": label})
            for index, label in enumerate(ctx.get("choices", []))
        ]
    if category == "route":
        seen = set()
        candidates = []
        for path in ctx.get("paths", []):
            choice = int(path.get("choice", len(candidates)))
            if choice in seen:
                continue
            seen.add(choice)
            candidates.append(_candidate(f"route:choice:{choice}", "map_node", f"route {choice}: {path.get('label', '')}", True, dict(path)))
        return candidates
    return []
```

- [ ] **Step 4: Implement selected/current/Bottled mapping**

Map labels to candidate IDs by action kind first and normalized labels second. Keep unmapped labels explicit:

```python
def build_trainable_sample(decision_sample, comparison_row, trace_event=None):
    candidates = normalize_candidates(decision_sample)
    selected_id = _selected_action_id(decision_sample, candidates)
    bottled_id = _label_to_candidate_id(comparison_row.reference_choice, candidates)
    state = _state_snapshot(decision_sample, trace_event or {})
    return {
        "schema_version": SCHEMA_VERSION,
        "sample_id": decision_sample.sample_id,
        "category": decision_sample.category,
        "source": decision_sample.source,
        "floor": decision_sample.floor,
        "act": decision_sample.act,
        "unix_time": _to_float((trace_event or {}).get("unix_time")),
        "state": state,
        "candidate_actions": candidates,
        "selected_action_id": selected_id,
        "current_policy_label": {"label": comparison_row.current_choice, "action_id": selected_id},
        "bottled_label": {
            "label": comparison_row.reference_choice,
            "action_id": bottled_id,
            "confidence": comparison_row.confidence,
            "reason": comparison_row.reason,
        },
        "evidence_quality": decision_sample.evidence_quality,
        "limitations": list(decision_sample.limitations),
        "outcome": {"join_status": "missing", "included_in_gate": False},
    }
```

- [ ] **Step 5: Run GREEN**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_rl_decision_loop.py::test_exports_complete_noncombat_samples_from_trace tests/test_noncombat_rl_decision_loop.py::test_partial_trace_sample_preserves_limitations -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_green_1
```

Expected: both tests pass.

## Task 3: RED/GREEN For Conservative Outcome Join

**Files:**
- Modify: `tests/test_noncombat_rl_decision_loop.py`
- Modify: `analysis_scripts/noncombat_rl_decision_loop.py`

- [ ] **Step 1: Write failing tests for matched, missing, and ambiguous joins**

```python
def test_attach_live_outcomes_matches_exactly_one_run():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    samples = [{"sample_id": "trace:0", "unix_time": 1780000010.0, "outcome": {"join_status": "missing"}}]
    outcomes = [
        {"run_file": "1780000000.run", "start_unix": 1780000000, "end_unix": 1780000200, "victory": False, "floor_reached": 12, "killed_by": "Gremlin Nob", "playtime": 200, "ai_marked": True}
    ]

    [joined] = attach_live_outcomes(samples, outcomes)

    assert joined["outcome"]["join_status"] == "matched"
    assert joined["outcome"]["included_in_gate"] is True
    assert joined["outcome"]["floor_reached"] == 12


def test_attach_live_outcomes_excludes_missing_and_ambiguous_matches():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    missing = [{"sample_id": "trace:missing", "unix_time": 1780000500.0, "outcome": {"join_status": "missing"}}]
    ambiguous = [{"sample_id": "trace:ambiguous", "unix_time": 1780000010.0, "outcome": {"join_status": "missing"}}]
    outcomes = [
        {"run_file": "a.run", "start_unix": 1780000000, "end_unix": 1780000200, "victory": False, "floor_reached": 10, "killed_by": "A", "playtime": 200, "ai_marked": True},
        {"run_file": "b.run", "start_unix": 1780000005, "end_unix": 1780000300, "victory": False, "floor_reached": 11, "killed_by": "B", "playtime": 295, "ai_marked": True},
    ]

    assert attach_live_outcomes(missing, outcomes)[0]["outcome"]["join_status"] == "missing"
    joined = attach_live_outcomes(ambiguous, outcomes)[0]
    assert joined["outcome"]["join_status"] == "ambiguous"
    assert joined["outcome"]["included_in_gate"] is False
```

- [ ] **Step 2: Run RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_rl_decision_loop.py::test_attach_live_outcomes_matches_exactly_one_run tests/test_noncombat_rl_decision_loop.py::test_attach_live_outcomes_excludes_missing_and_ambiguous_matches -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_red_2
```

Expected: fail because `attach_live_outcomes` is missing or incomplete.

- [ ] **Step 3: Implement outcome join**

Use timestamp windows only for AI-marked runs:

```python
def attach_live_outcomes(samples, outcomes, tolerance_seconds=30):
    joined = []
    for sample in samples:
        sample_copy = dict(sample)
        sample_time = _to_float(sample_copy.get("unix_time"))
        matches = [
            outcome for outcome in outcomes
            if outcome.get("ai_marked", True)
            and sample_time is not None
            and outcome.get("start_unix") is not None
            and outcome.get("end_unix") is not None
            and outcome["start_unix"] - tolerance_seconds <= sample_time <= outcome["end_unix"] + tolerance_seconds
        ]
        if len(matches) == 1:
            outcome = dict(matches[0])
            sample_copy["outcome"] = {
                "join_status": "matched",
                "included_in_gate": True,
                "run_file": outcome.get("run_file"),
                "victory": bool(outcome.get("victory")),
                "floor_reached": outcome.get("floor_reached"),
                "killed_by": outcome.get("killed_by") or "",
                "playtime": outcome.get("playtime"),
            }
        elif len(matches) > 1:
            sample_copy["outcome"] = {"join_status": "ambiguous", "included_in_gate": False}
        else:
            sample_copy["outcome"] = {"join_status": "missing", "included_in_gate": False}
        joined.append(sample_copy)
    return joined
```

- [ ] **Step 4: Add `load_run_outcomes` after the pure join passes**

Parse `.run` records from `runs_dir/IRONCLAD/*.run`, derive `start_unix` from file stem, `end_unix = start_unix + playtime`, and read `victory`, `floor_reached`, `killed_by`, `playtime`. Use `runs/ai_games.txt` when available to set `ai_marked`.

- [ ] **Step 5: Run GREEN**

Run the same outcome tests with `--basetemp .pytest_tmp_noncombat_green_2`.

Expected: both tests pass.

## Task 4: RED/GREEN For Reward Contract And Promotion Gate

**Files:**
- Modify: `tests/test_noncombat_rl_decision_loop.py`
- Modify: `analysis_scripts/noncombat_rl_decision_loop.py`

- [ ] **Step 1: Write failing reward and gate tests**

```python
def _complete_sample(category, matched=True):
    return {
        "schema_version": "noncombat-rl-decision-v1",
        "sample_id": f"{category}:1",
        "category": category,
        "evidence_quality": "complete",
        "candidate_actions": [{"action_id": f"{category}:a", "kind": "test", "label": "A", "available": True, "raw": {}}],
        "selected_action_id": f"{category}:a",
        "current_policy_label": {"label": "A", "action_id": f"{category}:a"},
        "bottled_label": {"label": "A", "action_id": f"{category}:a", "confidence": "high", "reason": "same"},
        "outcome": {"join_status": "matched" if matched else "missing", "included_in_gate": matched, "victory": False, "floor_reached": 20},
    }


def test_gate_blocks_when_reward_contract_is_missing():
    from analysis_scripts.noncombat_rl_decision_loop import evaluate_promotion

    samples = [_complete_sample(category) for category in ["shop", "event", "route", "card_reward"]]

    result = evaluate_promotion(samples, reward_contract=None)

    assert result["status"] == "blocked"
    assert "reward_contract_missing" in result["blocking_reasons"]
    assert result["formal_noncombat_rl_training_ready"] is False


def test_gate_allows_data_loop_when_state_action_reward_eval_are_present():
    from analysis_scripts.noncombat_rl_decision_loop import default_reward_contract, evaluate_promotion

    samples = [_complete_sample(category) for category in ["shop", "event", "route", "card_reward"]]

    result = evaluate_promotion(samples, reward_contract=default_reward_contract())

    assert result["status"] == "allowed"
    assert result["readiness"]["state"] == "present"
    assert result["readiness"]["action"] == "present"
    assert result["readiness"]["reward"] == "present"
    assert result["readiness"]["evaluation"] == "present"
    assert result["formal_noncombat_rl_training_ready"] is False
```

- [ ] **Step 2: Run RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_rl_decision_loop.py::test_gate_blocks_when_reward_contract_is_missing tests/test_noncombat_rl_decision_loop.py::test_gate_allows_data_loop_when_state_action_reward_eval_are_present -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_red_3
```

Expected: fail because gate functions are missing.

- [ ] **Step 3: Implement reward contract**

Use a reportable contract without tuned training weights:

```python
def default_reward_contract():
    return {
        "version": "noncombat-reward-readiness-v1",
        "components": [
            {"name": "run_victory", "required_outcome_field": "victory", "direction": "positive"},
            {"name": "floor_reached", "required_outcome_field": "floor_reached", "direction": "positive"},
            {"name": "decision_survival", "required_outcome_field": "killed_by", "direction": "diagnostic"},
        ],
        "exclusions": ["combat card play reward shaping", "Bottled label as direct reward"],
        "unresolved_gaps": ["No learned non-combat policy is trained by this change."],
    }
```

- [ ] **Step 4: Implement promotion evaluation**

Gate data-loop readiness separately from formal training readiness:

```python
SUPPORTED_CATEGORIES = ("shop", "event", "route", "card_reward")


def evaluate_promotion(samples, reward_contract=None, min_complete_per_category=1, min_matched_outcomes=1):
    counts = Counter(sample.get("category") for sample in samples)
    complete_counts = Counter(sample.get("category") for sample in samples if sample.get("evidence_quality") == "complete")
    matched = [sample for sample in samples if sample.get("outcome", {}).get("included_in_gate")]
    blocking = []
    for category in SUPPORTED_CATEGORIES:
        if complete_counts.get(category, 0) < min_complete_per_category:
            blocking.append(f"missing_complete_{category}_samples")
    if sum(1 for sample in samples if sample.get("candidate_actions")) < len(SUPPORTED_CATEGORIES):
        blocking.append("candidate_actions_missing")
    if len(matched) < min_matched_outcomes:
        blocking.append("matched_live_outcomes_missing")
    if not reward_contract:
        blocking.append("reward_contract_missing")
    status = "allowed" if not blocking else "blocked"
    return {
        "status": status,
        "blocking_reasons": blocking,
        "readiness": {
            "state": "present" if samples else "missing",
            "action": "present" if all(sample.get("candidate_actions") for sample in samples) else "missing",
            "reward": "present" if reward_contract else "missing",
            "evaluation": "present" if matched else "missing",
        },
        "metrics": {
            "sample_count": len(samples),
            "category_counts": dict(counts),
            "complete_category_counts": dict(complete_counts),
            "matched_outcomes": len(matched),
        },
        "formal_noncombat_rl_training_ready": False,
        "formal_noncombat_rl_training_guard": "not_started_by_this_change",
    }
```

- [ ] **Step 5: Run GREEN**

Run the same gate tests with `--basetemp .pytest_tmp_noncombat_green_3`.

Expected: both tests pass.

## Task 5: Report Rendering, CLI, And Combat RL Smoke Separation

**Files:**
- Modify: `tests/test_noncombat_rl_decision_loop.py`
- Modify: `analysis_scripts/noncombat_rl_decision_loop.py`
- Optional create after local run: `reports/noncombat_rl_decision_loop_fresh_eval.md`

- [ ] **Step 1: Write failing report and smoke tests**

```python
def test_report_names_gate_reward_and_training_guard():
    from analysis_scripts.noncombat_rl_decision_loop import default_reward_contract, evaluate_promotion, render_readiness_report

    samples = [_complete_sample(category) for category in ["shop", "event", "route", "card_reward"]]
    gate = evaluate_promotion(samples, reward_contract=default_reward_contract())

    report = render_readiness_report(samples, gate)

    assert "# Non-Combat RL Decision Loop Readiness" in report
    assert "Promotion status: allowed" in report
    assert "Reward readiness" in report
    assert "Formal non-combat RL training: blocked" in report


def test_combat_rl_smoke_command_is_bounded_and_not_noncombat_training():
    from analysis_scripts.noncombat_rl_decision_loop import combat_rl_smoke_command

    command = combat_rl_smoke_command(r"D:\anaconda\envs\stsai\python.exe", r"D:\SteamLibrary\steamapps\common\SlayTheSpire")

    assert "--agent combat_rl" in command
    assert "--max-games 1" in command
    assert "--dry-run" in command
    assert "noncombat" not in command.lower()
```

- [ ] **Step 2: Run RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_rl_decision_loop.py::test_report_names_gate_reward_and_training_guard tests/test_noncombat_rl_decision_loop.py::test_combat_rl_smoke_command_is_bounded_and_not_noncombat_training -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_red_4
```

Expected: fail because report/smoke functions are missing.

- [ ] **Step 3: Implement Markdown report**

The report must include these sections:
- `# Non-Combat RL Decision Loop Readiness`
- `## Summary`
- `## Sample Coverage`
- `## Bottled Agreement`
- `## Live Outcomes`
- `## Reward readiness`
- `## Promotion Gate`
- `## Training Guard`
- `## Combat RL Smoke`

- [ ] **Step 4: Implement CLI**

CLI shape:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts/noncombat_rl_decision_loop.py --trace D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace.jsonl --runs-dir D:\SteamLibrary\steamapps\common\SlayTheSpire\runs --character IRONCLAD --output reports\noncombat_rl_decision_loop_fresh_eval.md --json-output reports\noncombat_rl_decision_samples.jsonl
```

Required behavior:
- Read trace samples.
- Load recent run outcomes.
- Attach outcomes.
- Evaluate gate with `default_reward_contract()`.
- Write Markdown report if `--output` is provided.
- Write JSONL samples if `--json-output` is provided.
- Print the promotion status and blocking reasons to stdout.

- [ ] **Step 5: Implement bounded combat RL smoke command text**

Return this exact shape, with caller-provided `python` and `game_dir`:

```powershell
<python> scripts\run_training_batch.py --python <python> --game-dir <game_dir> --agent combat_rl --eval --max-games 1 --dry-run
```

This command is a smoke/dry-run health check only and must not be presented as non-combat RL training.

- [ ] **Step 6: Run GREEN**

Run report/smoke tests with `--basetemp .pytest_tmp_noncombat_green_4`.

Expected: tests pass and report contains the training guard.

## Task 6: Integration Verification And OpenSpec Task Updates

**Files:**
- Modify: `openspec/changes/add-noncombat-rl-decision-loop/tasks.md`
- Create if local inputs exist: `reports/noncombat_rl_decision_loop_fresh_eval.md`
- Create if local inputs exist: `reports/noncombat_rl_decision_samples.jsonl`

- [ ] **Step 1: Run all new tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_rl_decision_loop.py -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_focused
```

Expected: all new tests pass.

- [ ] **Step 2: Run comparator regression tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_offline_decision_comparator.py -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_comparator
```

Expected: all comparator tests pass unchanged.

- [ ] **Step 3: Run training batch runner tests if smoke command or runner integration changed**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_training_batch_runner.py -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_training_batch
```

Expected: all training-batch tests pass. If `scripts/run_training_batch.py` was not modified, this step still gives useful guard coverage.

- [ ] **Step 4: Generate a local readiness report when trace data exists**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts/noncombat_rl_decision_loop.py --trace D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace.jsonl --runs-dir D:\SteamLibrary\steamapps\common\SlayTheSpire\runs --character IRONCLAD --output reports\noncombat_rl_decision_loop_fresh_eval.md --json-output reports\noncombat_rl_decision_samples.jsonl
```

Expected:
- The report is written.
- The report states `Formal non-combat RL training: blocked`.
- The report includes sample counts for shop, event, route, and card reward when trace rows exist.
- The JSONL file contains canonical samples with `schema_version`.

- [ ] **Step 5: Validate OpenSpec**

Run:

```powershell
openspec validate add-noncombat-rl-decision-loop --strict
```

Expected: valid.

- [ ] **Step 6: Run full pytest before commit or promotion use**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_noncombat_full
```

Expected: full suite passes. If the full suite is too slow for the current iteration, do not mark the promotion gate as reliable yet; report the focused-test state and leave the OpenSpec task unchecked.

- [ ] **Step 7: Update OpenSpec task checkboxes truthfully**

Only mark a task complete when the matching implementation, focused test, and report/validation evidence exists. Leave formal non-combat RL training tasks blocked by design unless a later approved change explicitly starts training.

## Self-Review

- Spec coverage: Canonical samples are covered by Tasks 1-2; candidate normalization by Task 2; conservative outcome join by Task 3; reward readiness and promotion gate by Task 4; formal training guard and combat RL smoke separation by Task 5; verification by Task 6.
- Placeholder scan: No unresolved placeholder markers are present. Optional files are explicitly bounded by whether local trace data exists.
- Type consistency: Public API names match across tests, implementation snippets, CLI, and report steps.
- Scope: The plan does not alter live shop/event/route/card-reward decision logic, does not import Bottled at runtime, and does not start formal non-combat RL training.
