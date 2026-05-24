# Training Diagnostics - 2026-05-24

## Batch

Command profile: `--agent combat_rl --train --rl-version v2 --elite-route conservative --max-games 100 --ascension 0`

Final checkpoint: `D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints\rl_combat_model_ep197_steps8836.pth`

## Result

- Runs: 100
- Wins: 0
- Average floor: 10.09
- Max floor: 16
- Boss reach rate: 16.0%
- Elite death rate: 18.0%
- Average Act 1 elites: 0.18

## Combat Failure Profile

Run:

```powershell
& 'D:\anaconda\envs\stsai\python.exe' analysis_scripts\analyze_combat_failures.py --runs-dir 'D:\SteamLibrary\steamapps\common\SlayTheSpire\runs' --character IRONCLAD --count 100 --tail-lines 50000
```

Key findings:

- Normal fights caused most deaths: 66 normal, 18 elite, 16 boss.
- Top lethal encounters: Exordium Thugs, Gremlin Gang, Large Slime, Slime Boss, Lagavulin.
- The agent obtained potions but recorded zero run-file potion uses in the latest 100-run batch.
- The log tail showed 239 turn ends with energy remaining, suggesting action selection sometimes ends turns early or cannot find valuable playable actions.
- Conservative routing prevented the previous elite wall, but combat policy and pre-boss growth are still the main bottlenecks.

## Next Engineering Focus

1. Improve combat reward shaping for lethal-risk turns, especially multi-enemy normal fights.
2. Add potion-use behavior or reward pressure; current runs strongly suggest potions are not being consumed.
3. Add action-level trace extraction from `ai_debug.log` so wasted-energy turns can be tied to hand state and selected action.
4. Keep conservative routing until boss reach consistently exceeds 35-40%.
