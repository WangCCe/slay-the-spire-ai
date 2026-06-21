# 2026-06-21 Act 1 Boss Failure Audit

## Scope

- Source batch: 50-run no-training eval launched 2026-06-21 21:29 CST.
- Relevant losses: 24/50 runs died to Act 1 bosses.
- Boss split: Slime Boss=9, The Guardian=8, Hexaghost=7.

## Findings

### Boss losses are not mainly low-HP entry losses

- Average HP after floor 15 rest/smith path point: 67.0.
- Average pre-boss damage among Act 1 boss deaths: 86.9.
- Every Act 1 boss death had a floor 15 rest node in the path.
- The fatal signal is the boss combat itself: average boss damage was 65-77 and average boss length was about 10-11 turns.

### Decks look underpowered for Act 1 boss kills

Average boss-death deck profile:

- Hexaghost: frontload=3.7, block=3.3, premium_frontload=0.3, boss_turns=10.9.
- Slime Boss: frontload=4.2, block=1.8, premium_frontload=0.1, boss_turns=11.3.
- Guardian: frontload=4.2, block=2.6, premium_frontload=0.4, boss_turns=9.9.

The Act 1 boss-death decks usually had only 0-1 premium frontload cards. Slime Boss losses in particular often had low block and still took too long to split/kill.

### Reward choices may be too conservative around Strike-synergy frontload

Among Act 1 boss deaths, frequently missed frontload/block offers before floor 16 included:

- Wild Strike: 15
- Perfected Strike: 15
- Twin Strike: 12
- Pommel Strike: 9
- Headbutt: 9
- Anger: 9

Current strategy detail:

- `IroncladCardEvaluator` scores `Perfected Strike` highly, but `IroncladDeckStrategy.should_pick_card()` hard-rejects it unless `_should_take_early_perfected_strike()` passes a narrow Act 1 exception.
- `_should_take_early_perfected_strike()` requires Act 1, deck size <= 14, no existing Perfected Strike, and narrow floor/Strike-source/frontload cases.
- `Twin Strike` is in Act 1 damage priority but does not appear to receive the same baseline priority as stronger frontload cards.

## Hypothesis

The most likely root cause is not a single non-combat Bottled mismatch. The stronger current hypothesis is:

> The conservative route avoids elites but still reaches Act 1 bosses with decks that lack enough reliable frontload or boss-specific damage density, because reward/shop policy sometimes rejects or underranks rough Strike-synergy attacks that are bad long-term but necessary for immediate Act 1 boss survival.

## Fix Gate

The first patch should stay narrow. A broad reward retune is not justified by this batch alone.

Implemented candidate:

- Allow the first Act 1 `Perfected Strike` when Strike-source density is still high, the deck has vulnerable coverage from `Thunderclap` or `Shockwave`, and reliable frontload is still below the Act 1 boss-readiness threshold.

Regression traces:

- Floor 3 `Perfected Strike / Rage / Intimidate` with four starter Strikes and `Thunderclap` now takes `Perfected Strike`.
- Floor 11 `Perfected Strike / Rage / Sentinel` with three starter Strikes, `Pommel Strike+`, `Thunderclap`, and duplicate `Rage` now takes `Perfected Strike`.

Guardrails retained:

- Low Strike-density Perfected Strike is still rejected.
- Duplicate Perfected Strike is still rejected.
- Existing Slime Boss `Headbutt` over `Perfected Strike` protection remains covered.
