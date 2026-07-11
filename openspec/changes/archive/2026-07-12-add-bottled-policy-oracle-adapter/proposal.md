# Change: Add Bottled policy oracle adapter

## Why
The current offline comparator encodes a Bottled-style Ironclad reference locally. That is useful, but it can drift from the checked-out `xaved88/bottled_ai` implementation and cannot prove that disagreements reflect the real RequestedStrike handlers.

We need a read-only oracle adapter that evaluates current non-combat samples against the local Bottled checkout while preserving the existing live gameplay and non-combat RL training guards.

## What Changes
- Add an offline-only Bottled policy oracle adapter for Ironclad `REQUESTED_STRIKE`.
- Support shop, card-reward, event, and route decisions first.
- Record oracle source metadata, including Bottled repo path, git commit when available, strategy name, confidence, reason, limitations, and mapped candidate action id.
- Extend current-vs-Bottled disagreement reports to distinguish native Bottled oracle evidence from the older locally encoded Bottled-style fallback.
- Keep combat limited to adapter feasibility reporting; do not replace combat policy.
- Preserve live gameplay behavior, CommunicationMod config, and formal non-combat RL training guard.

## Impact
- Affected specs: `noncombat-rl-decision-loop`
- Affected code:
  - `analysis_scripts/offline_decision_comparator.py`
  - `analysis_scripts/noncombat_rl_decision_loop.py`
  - new offline adapter module under `analysis_scripts/`
  - focused tests under `tests/`
- External read-only input: `C:\Users\20571\Documents\bottled_ai` (`xaved88/bottled_ai.git`)
- No live agent, CommunicationMod, checkpoint, or training behavior changes.
