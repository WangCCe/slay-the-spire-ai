## 1. Evidence And Design

- [x] 1.1 Capture the fresh 2026-07-10 lethal-prefix failure from `ai_debug.log` and its `.run` record.
- [x] 1.2 Trace the failure through `IroncladCombatPlanner`, `OptimizedAgent`, and `CombatRLAgent`.
- [x] 1.3 Identify commit `139ddb4b` as the source of the generic end-turn pressure veto and confirm the later single-card lethal guard does not cover multi-card plans.
- [x] 1.4 Replace the stale low-HP and multi-character design with the scoped guard-provenance design.
- [x] 1.5 Validate this OpenSpec change in strict mode.

## 2. Regression Tests

- [ ] 2.1 Add a failing regression for the 3 HP, two-slime, Hemokinesis-plus-Headbutt lethal prefix.
- [ ] 2.2 Add a control proving an immediately self-lethal HP-cost action remains blocked.
- [ ] 2.3 Add a control proving lethal reactive damage such as Sharp Hide remains blocked.
- [ ] 2.4 Add plan metadata lifecycle tests for replan, stale action, turn reset, and combat end.

## 3. Minimal Implementation

- [ ] 3.1 Expose validated lethal plan kind from `IroncladCombatPlanner`.
- [ ] 3.2 Cache and clear plan kind with `OptimizedAgent.current_action_sequence`.
- [ ] 3.3 Add a narrow fallback-agent query for whether the returned action is an active lethal prefix.
- [ ] 3.4 Apply legality and immediate-death vetoes before allowing the lethal prefix through takeover arbitration.
- [ ] 3.5 Keep normal pressure guards for actions without validated lethal provenance.
- [ ] 3.6 Add concise arbitration logs for pass-through and veto cases.

## 4. Verification

- [ ] 4.1 Run focused combat guard and planner tests with the Windows production Python.
- [ ] 4.2 Run full pytest with cache disabled and a writable repository-local base temp.
- [ ] 4.3 Review the implementation diff for unrelated policy or tuning changes.
- [ ] 4.4 Commit the regression-backed behavior fix.

## 5. Live Validation

- [ ] 5.1 Run a fresh conservative 25-game evaluation without training.
- [ ] 5.2 Confirm zero invalid commands and no new uncaught gameplay exceptions.
- [ ] 5.3 Inspect fresh lethal, death-cluster, and sim-divergence evidence for A-class failures.
- [ ] 5.4 Record the batch in a committed summary report.
- [ ] 5.5 If the batch is clean, run and report the second consecutive fresh 25-game qualification batch.
