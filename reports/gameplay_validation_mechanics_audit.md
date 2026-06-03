# Gameplay Validation Mechanics Audit

## Round 1 - 2026-06-03

- Preflight: git clean at `d306cd8 Unify combat ending player HP reads`.
- Baseline: `D:\anaconda\envs\stsai\python.exe -m pytest -q --basetemp C:\Users\20571\Documents\Codex\2026-06-03\d-pycharmprojects-slay-the-spire-ai\.pytest-basetemp` -> 1453 passed before changes.
- Validation: CommunicationMod ran `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance` with Windows Python.
- Outcome: no Ironclad `victory=true`; AI markers `1780450800` through `1780452924`; latest visible run `1780452921.run` died at floor 16 to Hexaghost.
- Failure type: lethal-sequence execution drift during RL energy-guard fallback takeover. A proven sequence could be planned, but `OptimizedAgent` invalidated the cached sequence after the first card left hand, replanned mid-turn, and could abandon the remaining lethal line.
- Fix: keep executing cached combat sequences when the next planned action is still available, and advance `current_action_index` after returning a newly planned first action.
- Regression: `test_optimized_agent_continues_cached_sequence_after_played_card_leaves_hand`.
- Verification after fix: focused related tests `56 passed`; full pytest `1454 passed`.
- Next candidate: inspect post-fix bounded validation for remaining Act 1 boss deaths and late Act 2 boss deaths, especially low-HP turns where fallback selects zero-damage setup cards or Havoc before lethal/defense.
