# Offline Decision Comparator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first read-only POC that compares local operating-decision samples against Bottled-style Ironclad reference choices and emits a readable difference report.

**Architecture:** Add one focused analysis script with plain dataclasses for samples, comparisons, adapters, fixture loading, `.run` loading, bounded JSONL loading, and Markdown rendering. Keep gameplay code untouched and keep Bottled behavior encoded as a small read-only reference adapter rather than importing `bottled_ai`.

**Tech Stack:** Python standard library, existing pytest setup, JSON fixtures, Markdown report output.

---

## File Structure

- Create `analysis_scripts/offline_decision_comparator.py`: CLI plus reusable functions for normalizing samples, Bottled-style reference decisions, comparison rows, ranking, and report rendering.
- Create `tests/test_offline_decision_comparator.py`: focused TDD coverage for loaders, adapters, confidence, report ranking, and CLI-style report generation.
- Create `tests/fixtures/offline_decision_samples.json`: deterministic samples that cover shop, event, route, and card reward.
- Create `reports/offline_decision_comparator_poc.md`: generated POC report from local fixture and `.run` sample inputs.
- Modify `openspec/changes/add-offline-decision-comparator/tasks.md`: mark implementation and verification tasks complete only after tests/report succeed.

### Task 1: Failing Tests And Fixtures

**Files:**
- Create: `tests/test_offline_decision_comparator.py`
- Create: `tests/fixtures/offline_decision_samples.json`

- [ ] **Step 1: Write fixture samples**

Create JSON samples for:
- shop: our choice buys `Anger`; reference should prefer purge because a removable starter card exists.
- event: our choice enters `Shining Light` at low post-event HP; reference should leave.
- route: our choice takes an elite-heavy path; reference should prefer safer reward-to-survivability path.
- card reward: our choice skips `Offering`; reference should take it under `REQUESTED_STRIKE`.

- [ ] **Step 2: Write failing tests**

Tests must import:

```python
from analysis_scripts.offline_decision_comparator import (
    compare_samples,
    load_fixture_samples,
    load_run_samples,
    render_markdown_report,
    rank_issues,
)
```

Assert:
- fixture loading returns all four categories.
- comparisons produce reference choices and high-confidence disagreements for all four fixture rows.
- `.run` loading marks shop purchase rows as partial evidence.
- the report contains "Current Choice", "Bottled Reference", "Most Worth Fixing", and "No gameplay-code fix is applied".
- ranking returns at most five issues and prioritizes high-confidence disagreements.

- [ ] **Step 3: Run tests to verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_offline_decision_comparator.py -q -p no:cacheprovider --basetemp .pytest-tmp-offline-red
```

Expected: fail because `analysis_scripts.offline_decision_comparator` does not exist.

### Task 2: Minimal Comparator Implementation

**Files:**
- Create: `analysis_scripts/offline_decision_comparator.py`

- [ ] **Step 1: Implement sample and comparison dataclasses**

Define `DecisionSample`, `ReferenceDecision`, and `ComparisonRow` with fields used by tests and report output.

- [ ] **Step 2: Implement loaders**

Implement:
- `load_fixture_samples(path)`
- `load_run_samples(path, limit=None)`
- bounded `load_jsonl_samples(path, tail=2000)` for future trace use.

`.run` samples should extract card choices, event choices, item purchases, and a coarse route summary while marking partial evidence where context is incomplete.

- [ ] **Step 3: Implement Bottled-style adapters**

Implement minimal adapters:
- shop priority: purge curses, Perfected Strike, Membership Card, purge starter cards, listed relics, listed cards, leave.
- event thresholds for Shining Light, Golden Idol, World of Goop, Wing Statue, Dead Adventurer, The Mausoleum, Golden Shrine, Nest, Lab, Drug Dealer, and fallback.
- route reward-to-survivability score over provided candidate paths.
- card reward desired counts based on `REQUESTED_STRIKE`.

- [ ] **Step 4: Implement comparison, ranking, report, and CLI**

Implement:
- `compare_samples(samples)`
- `rank_issues(rows, max_issues=5)`
- `render_markdown_report(rows, issues)`
- CLI args for `--fixture`, `--run`, `--trace`, `--output`.

- [ ] **Step 5: Run tests to verify GREEN**

Run the same pytest command with `--basetemp .pytest-tmp-offline-green`.

### Task 3: Local POC Report

**Files:**
- Create: `reports/offline_decision_comparator_poc.md`
- Modify: `openspec/changes/add-offline-decision-comparator/tasks.md`

- [ ] **Step 1: Run comparator on fixture plus one local run**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts/offline_decision_comparator.py --fixture tests/fixtures/offline_decision_samples.json --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1781445184.run --output reports/offline_decision_comparator_poc.md
```

Expected: report is written and includes rows from all four categories.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_offline_decision_comparator.py -q -p no:cacheprovider --basetemp .pytest-tmp-offline-focused
```

Expected: all tests pass.

- [ ] **Step 3: Validate OpenSpec**

Run:

```powershell
openspec validate add-offline-decision-comparator --strict
```

Expected: valid.

- [ ] **Step 4: Update OpenSpec tasks**

Mark completed POC and verification tasks in `openspec/changes/add-offline-decision-comparator/tasks.md`. Leave repair-gate code-fix tasks truthful: no gameplay-code fix is applied.

## Self-Review

- Spec coverage: The plan covers read-only normalization, reference adapters, report/ranking, and the no-repair gate.
- Placeholder scan: No TBD/TODO placeholders are present.
- Scope: The plan is a single POC and does not touch live gameplay decision code.
