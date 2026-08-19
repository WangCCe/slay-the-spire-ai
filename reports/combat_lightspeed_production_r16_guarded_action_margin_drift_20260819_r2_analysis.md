# Guarded successor action-margin drift analysis

## Decision

Stop adding end-turn-specific objective patches. The guarded candidate is not eligible, and this audit does not authorize training, packaging, or gameplay.

## Technical result

- Verdict: `action_margin_drift_ready`; blockers: none
- Registered/initialized complete profiles: `1,024` / `846`
- Accepted transitions: `16,315`
- Battle transition counts: `3,772`, `4,421`, `4,909`, `3,213`
- Initialization failures: `178`, all expected baseline losses before the requested battle
- Unsupported states: `0`

## Drift result

The guarded candidate disagrees with production r16 on `1,224 / 16,315` transitions (`7.50%`). Disagreement increases with requested battle:

| Battle | Disagreements | Rate |
|---:|---:|---:|
| 0 | 178 | 4.72% |
| 3 | 310 | 7.01% |
| 6 | 436 | 8.88% |
| 9 | 300 | 9.34% |

Battle 9's rate is `1.98x` battle 0's. Parent play-card states are most sensitive (`15.04%`), followed by potion (`7.90%`) and end-turn (`4.44%`) states.

The dominant flips are `play_card -> play_card` (`497`) and `end_turn -> play_card` (`424`). Only `164` flips (`13.4%`) move a parent non-end-turn action to end turn, while `493` (`40.3%`) move parent end turn to a card or potion and `514` (`42.0%`) stay within the same action family.

## Interpretation

The first guard did its intended job: non-end-turn to end-turn displacement is no longer the dominant policy drift. Residual changes are broader card ranking and increased action-taking, and they grow in later battle strata. Adding the mirror-image end-turn special case would be another narrow patch without outcome attribution.

The next decision should be made from existing encounter-identity and target-mode evidence. If later-battle drift reflects missing context, a battle/encounter-conditioned representation is the next candidate; if the state is adequate but credit is wrong, the return target should change. The completed guard's weight and cap should not be tuned on these results.

The current audit does not provide a battle-by-flip-family cross-tabulation, so it cannot claim that a specific flip family causes battle-9 outcome harm.
