## 1. Schema and Trace Export
- [x] 1.1 Define the canonical non-combat decision sample schema and version field.
- [x] 1.2 Normalize category-specific candidate actions for shop, event, route, and card reward.
- [x] 1.3 Export current-policy choice, Bottled-style reference label, confidence, reason, and evidence limitations.
- [x] 1.4 Add fixture tests that cover complete and partial samples for all four categories.

## 2. Outcome Join
- [x] 2.1 Define the conservative live outcome fields and join status values.
- [x] 2.2 Join samples to `.run` summaries when exactly one reliable run match exists.
- [x] 2.3 Mark missing or ambiguous joins explicitly and exclude them from promotion metrics.
- [x] 2.4 Add tests for matched, missing, and ambiguous outcome joins.

## 3. Offline Evaluation Gate
- [x] 3.1 Add a report that summarizes sample counts, evidence quality, candidate coverage, Bottled agreement, repeated high-confidence gaps, and live outcomes.
- [x] 3.2 Add a fixed fresh-eval promotion gate with explicit `allowed`/`blocked` status and blocking reasons.
- [x] 3.3 Define the non-combat reward-readiness contract in reportable, test-covered terms without training on it yet.
- [x] 3.4 Keep formal non-combat RL training blocked until state, action, reward, and evaluation definitions are all present and tested.
- [x] 3.5 Add tests for gate pass/fail behavior using deterministic fixtures.

## 4. Training Pipeline Smoke
- [x] 4.1 Define a bounded combat RL smoke command or dry-run path that validates training wiring without starting formal non-combat RL training.
- [x] 4.2 Ensure reports distinguish combat RL smoke health from non-combat RL readiness.

## 5. Verification
- [x] 5.1 Run focused pytest for new sample/export/gate tests.
- [x] 5.2 Run existing comparator and training-batch tests touched by the change.
- [x] 5.3 Run `openspec validate add-noncombat-rl-decision-loop --strict`.
- [x] 5.4 Run full pytest before using the gate as a promotion decision or committing shared live-path changes.
