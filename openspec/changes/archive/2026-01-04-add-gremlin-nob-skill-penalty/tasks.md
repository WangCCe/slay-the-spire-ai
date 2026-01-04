# Implementation Tasks

## 1. Add SKILL card penalty to Ironclad combat scoring
- [x] Modify `_score_sequence()` in `ironclad_combat.py` (around line 375)
- [x] Add check: if `has_gremlin_nob` and action is PlayCardAction
- [x] Detect card type: `card.type == CardType.SKILL`
- [x] Exclude Powers: `card.type != CardType.POWER`
- [x] Apply penalty: `score -= 50` for each SKILL card
- [x] Add exception: skip penalty if `card_id == 'Demon Form' and turn <= 3`
- [x] Add logging: `logger.info("[SKILL_PENALTY] Applied -50 for SKILL card against Gremlin Nob")`

## 2. Test card type detection
- [x] Verify `card.type` enum values match `CardType.ATTACK/SKILL/POWER`
- [x] Test against known cards:
  - Defend_R: should be SKILL
  - Iron Wave: should be ATTACK (not penalized)
  - Demon Form: should be POWER (not penalized)
  - Battle Trance: should be SKILL (penalized)

## 3. Validate scoring impact
- [x] Run simulation: Gremlin Nob fight with current code
- [x] Run simulation: Gremlin Nob fight with SKILL penalty
- [x] Compare: SKILL cards should score 50+ points lower
- [x] Verify ATTACK cards unaffected

## 4. Monitor and log
- [x] Check `ai_debug.log` for SKILL_PENALTY messages
- [x] Verify penalty only applies to Gremlin Nob fights
- [x] Verify Powers not penalized
- [x] Track win rate in `ai_game_stats.csv`

## 5. Update AI version
- [x] Bump version in `spirecomm/ai/statistics.py`
- [x] Update comment: "v3.3.1-gremlin-skill-penalty"

## Dependencies
- Task 1 must complete before Task 2
- Task 2 must complete before Task 3
- Task 3 must complete before Task 4
- Task 5 can happen in parallel with Task 4
