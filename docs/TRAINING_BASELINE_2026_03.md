# Training Baseline: March 2026 Ironclad Runs

This baseline captures the state that motivated `refactor-training-pipeline`.

## Data Source

- Run directory: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD`
- Sample: latest 500 `.run` files as of 2026-03-01
- Character: Ironclad
- Ascension: 0

## Summary

| Metric | Value |
| --- | ---: |
| Runs | 500 |
| Wins | 0 |
| Win rate | 0.0% |
| Average floor | 9.08 |
| Max floor | 33 |
| Average playtime | 39.1s |

## Death Distribution

| Floor range | Deaths |
| --- | ---: |
| 0-4 | 10 |
| 5-9 | 290 |
| 10-14 | 147 |
| 15-19 | 51 |
| 20-24 | 1 |
| 30-34 | 1 |

## Top Death Causes

| Cause | Count |
| --- | ---: |
| 3 Sentries | 101 |
| Lagavulin | 93 |
| Gremlin Nob | 79 |
| Exordium Thugs | 35 |
| Large Slime | 27 |
| Gremlin Gang | 24 |
| Exordium Wildlife | 21 |
| Hexaghost | 21 |
| The Guardian | 15 |
| Slime Boss | 14 |

## Interpretation

The training run was not merely slow to improve; it was collecting highly concentrated early-failure samples. Act 1 elite deaths accounted for more than half of recent runs, which matches the aggressive elite routing default. The first recovery step is to run bounded training batches with conservative Act 1 routing, then reintroduce elite risk through curriculum thresholds.

## Reproducible Command

```powershell
& 'D:\anaconda\envs\stsai\python.exe' analysis_scripts\analyze_training_plateau.py --count 500 --bucket 50 --character IRONCLAD
```
