# Change: Stabilize lethal execution across combat guards

## Why

The lethal detector can produce a valid multi-card kill sequence, but the takeover layer does not retain that plan's provenance. In the fresh 25-game evaluation completed on 2026-07-10, the fallback planner selected Hemokinesis as the first action of a validated two-card lethal at 3 HP. The pressure HP-loss guard treated it as an ordinary filler action, ended the turn with 2 energy, and the player died.

The current change description is also stale: it proposes a generic low-HP threshold and broad multi-character work, while current code and live evidence show a narrower Ironclad action-arbitration defect.

## What Changes

- Preserve validated lethal-plan provenance from `IroncladCombatPlanner` through `OptimizedAgent` plan caching.
- Let `CombatRLAgent` distinguish a safe lethal prefix from ordinary pressure-unsafe HP-loss filler.
- Keep hard vetoes for illegal, stale, immediately self-lethal, and reactive-damage-lethal actions.
- Define and log the combat guard precedence contract.
- Add an exact regression from the fresh live failure plus negative safety controls.
- Validate with focused tests, full pytest, and bounded fresh evaluation.

## Non-Goals

- No general combat-policy retuning.
- No formal RL training.
- No SimpleAgent, Silent, Defect, or Watcher expansion.
- No broad replacement of the combat planner or lethal sequence builder.

## Impact

- Affected spec: `ai-combat`
- Expected code surfaces:
  - `spirecomm/ai/heuristics/ironclad_combat.py`
  - `spirecomm/ai/agent.py`
  - `spirecomm/ai/rl/agent.py`
  - focused combat guard and planner tests
- Live validation surfaces:
  - `ai_debug.log`
  - `communication_mod_errors.log`
  - `.run` records
  - decision and sim-divergence traces
