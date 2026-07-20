# Gameplay Route Mode Live A/B - 2026-07-20

## Scope

- Ironclad A0, combat RL evaluation mode, no training.
- Five games per launch with the same checkpoint and gameplay code.
- Current live batches were run after comparator commit `df92ca2ba`.
- The comparison is unpaired and bounded; it selects the next engineering direction rather than proving a final policy winner.

## Cohorts

Conservative run files:

- `1784544154.run`, `1784544360.run`, `1784544543.run`, `1784544642.run`, `1784544779.run`
- `1784557400.run`, `1784557460.run`, `1784557672.run`, `1784557805.run`, `1784557883.run`

Aggressive run files:

- `1784555553.run`, `1784555697.run`, `1784555813.run`, `1784555963.run`, `1784556067.run`
- `1784556705.run`, `1784556742.run`, `1784556805.run`, `1784556858.run`, `1784556932.run`

## Results

| Mode | Runs | Wins | Avg floor | Max floor | Act 2 boss reaches | Avg elites | Avg relics | Elite deaths |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| conservative | 10 | 0 | 24.2 | 33 | 3 | 0.0 | 4.7 | 0 |
| aggressive | 10 | 0 | 18.9 | 31 | 0 | 0.9 | 4.0 | 5 |

Conservative repeatedly reached Act 2 bosses but took no elites, leaving growth dependent on bosses, chests, events, and shops. Aggressive added elite exposure but half of its runs died to elites and it did not reach an Act 2 boss.

The Bottled comparator exposed a route rendering defect during this review: route choice index `0` was rendered as `map_node` because it was treated as false. Commit `df92ca2ba` fixed the comparator and reduced the two reviewed boss-run difference counts from `81/77` to `41/31`. Remaining Bottled shop and reward differences were not promoted to gameplay fixes because several references were clearly build-specific or weaker than the current choice.

Fresh sim-divergence rows were isolated transition effects: delayed card-selection relic effects, end-of-combat block clearing, Sundial selection timing, and a Mayhem/Panache derived effect. No repeated A-class mechanics cluster was found.

## Decision

Do not continue alternating the two existing route modes. Keep conservative as the live fallback while implementing and validating a third adaptive route baseline.

The adaptive baseline should consider:

- act and floor;
- absolute and relative HP;
- deck readiness for the act's elite pool;
- usable combat potions and relevant relics;
- rest sites before and after an elite;
- cumulative elite exposure and downstream forced risk.

The first bounded promotion gate is:

- nonzero elite exposure without the aggressive cohort's elite-death rate;
- average floor and Act 2 boss reach not below the conservative cohort;
- no new runtime errors or repeated A-class sim-divergence cluster;
- first `victory=true` remains the outer completion criterion.

No combat or non-combat RL training is authorized by this result.
