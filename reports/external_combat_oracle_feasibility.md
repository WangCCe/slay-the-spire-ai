# External Combat Oracle Feasibility Spike - 2026-06-05

## Scope

Evaluate whether `xaved88/bottled_ai` or `D:\CLionProjects\sts_lightspeed` can become a replay/oracle/strategy-comparison source for recent Ironclad live-validation failures, without integrating either project into the main agent.

Constraints for this spike:

- Do not connect either project to the production agent.
- Do not train or tune around mechanics errors.
- Do not create a long-lived replay/oracle framework without an OpenSpec proposal.
- Use only read-only evaluation, tiny probes, and evidence notes.

## Live Failure Samples

The current `ai_decision_trace.jsonl` still contains comparable final-action windows for all three selected real failures.

### Guardian ATTACK_BUFF / Sharp Hide

- Run: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1780669705.run`
- Outcome: floor 16, `victory=false`, `killed_by=The Guardian`
- Key state: turn 5, player 13 HP, 5 block after `Defend`; Guardian `Intent.ATTACK_BUFF`, `move_damage=8`, `move_hits=2`; hand still had `Twin Strike`, `Thunderclap`, `Strike`, `Barricade`.
- Failure shape: ending after block survived the visible 16 incoming at 2 HP, but attacking into Sharp Hide consumed the saved block/HP and made the turn lethal.
- Current status: already converted into `test_guardian_sharp_hide_guard_infers_attack_buff_reflection_without_power` and fixed by `3712265`.

### Hexaghost Burn Hand

- Run: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1780667052.run`
- Outcome: floor 16, `victory=false`, `killed_by=Hexaghost`
- Key state: turn 12, player 8 HP, 16 block, 1 energy, four `Burn+` in hand; Hexaghost `Intent.ATTACK_DEBUFF`, `move_damage=8`, `move_hits=1`.
- Failure shape: block covered monster incoming, but four end-turn `Burn+` cards were not blockable and killed the player.
- Current status: already converted into `test_survival_guard_treats_burn_damage_as_unblocked_by_current_block` and fixed by `b0b1ba1`.

### Slime Boss Split

- Run: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1780661235.run`
- Outcome: floor 16, `victory=false`, `killed_by=Slime Boss`
- Key state: turn 9 after `Defend`, player 17 HP, 3 block, 2 energy; enemies attacked for 8, 8, and 11. Hand had `Carnage`, `Burning Pact+`, `Strike+`, `Slimed`.
- Failure shape: `Carnage` hit the 16-HP attacking Spike Slime and left it at 1 HP, so the player faced 27 incoming and died. The same `Carnage` into the 10-HP attacking Spike Slime removed 8 incoming and survived at 1 HP.
- Current status: already converted into `test_slime_split_survival_guard_retargets_killable_attacker` and fixed by `0563f76`.

## bottled_ai Evidence

`bottled_ai` is feasible as a near-term strategy oracle source, especially for focused regression selection.

Observed source behavior:

- `README.md` describes the bot as non-ML, manually constructed decision-making. In combat, it evaluates different ways to play the hand using graph traversal and simulation, then chooses the preferred outcome.
- `rs/common/handlers/common_battle_handler.py` delegates combat decisions to `get_best_battle_action(...)` with a comparator.
- `rs/calculator/play_path.py` enumerates possible play paths breadth-first up to `max_path_count`.
- `rs/calculator/executor.py` ends each candidate path turn before comparing outcomes.
- `rs/common/comparators/common_general_comparator.py` orders comparisons with `battle_not_lost` before win/quality tie-breakers.
- `rs/common/comparators/core/comparisons.py` implements `battle_not_lost` so a non-losing challenger beats a losing best path.

Feasibility conclusion:

- The Slime Boss split failure is explained by this oracle model. A path that retargets `Carnage` to the 10-HP attacking slime is non-losing; the observed path that leaves all three attackers alive is losing. Because `battle_not_lost` is first in the comparator list, `bottled_ai` would prefer the survival path before considering lower-priority values.
- This directly yields a focused regression candidate shape: when an attack can kill an attacking split slime and make end-turn damage survivable, retarget that same attack before generic block or damage scoring.
- This is already represented by `test_slime_split_survival_guard_retargets_killable_attacker`, so `bottled_ai` passes the spike's first completion condition as a strategy-oracle source.

Limitations:

- `bottled_ai` is not a drop-in replay engine for our live traces. Its battle state objects and command protocol differ from our current `CombatRLAgent` data model.
- It also has an intentional path count cap (`max_path_count`, documented as 11,000), so it is best used first as a regression/source-of-heuristics oracle, not as a production decision engine.

## sts_lightspeed Evidence

`sts_lightspeed` is promising as a longer-term simulator/replay base, but it is not immediately usable as a live-trace oracle in this session.

Observed source behavior:

- `README.md` states it is a C++17 Slay the Spire simulator intended for tree search and simulation, with all Ironclad cards and all enemies implemented.
- `include/sim/search/BattleScumSearcher2.h` exposes a battle searcher that can search from a `BattleContext` and retain `bestActionSequence`.
- `include/combat/BattleContext.h` contains the combat state and action execution surface needed for a replay/search adapter.
- `bindings/slaythespire.cpp` exposes Python `GameContext`, `Agent`, cards, relics, rooms, and encounters, but does not expose `BattleContext`, direct hand/monster construction, or `BattleScumSearcher2`.

Build/import probe:

- Existing build directory had `main.exe`, but no `slaythespire*.pyd`, so `import slaythespire` failed under `D:\anaconda\envs\stsai\python.exe`.
- Building target `slaythespire` with `D:\programs\CLion\bin\cmake\win\x64\bin\cmake.exe --build D:\CLionProjects\sts_lightspeed\cmake-build-debug --target slaythespire -j 2` failed during CMake compiler re-check: the configured MinGW `g++.exe` could not compile CMake's simple test program.
- A one-line manual `g++.exe` compile probe also timed out after 30 seconds, despite `g++.exe --version` succeeding.

Short-term blocker:

- Current build environment/toolchain is not reliable enough to build the Python binding or `test` target in this session.
- Even after fixing the toolchain, a direct live-trace replay needs an adapter or binding extension because Python currently cannot construct a `BattleContext` from CommunicationMod trace fields.

Minimum adapter fields likely needed:

- Player: HP, max HP, block, energy, powers, relics, potions.
- Cards: hand with cost/upgrades/playability, draw pile, discard pile, exhaust pile, card UUID/order when effects need it.
- Monsters: canonical encounter id, per-monster hp/block, gone/half-dead, intent, move id or RNG state, powers.
- Combat metadata: turn number, floor, act, ascension, RNG/card RNG state where exact future simulation matters.

## Recommendation

Use `bottled_ai` now as a lightweight external strategy oracle for regression target selection. The immediate working pattern is:

1. Extract a real live-failure window from `ai_decision_trace.jsonl`.
2. Compare the observed action path against a small set of alternative paths.
3. Apply `bottled_ai`-style comparator ordering: reject losing paths first, then compare incoming damage, kills, and resource quality.
4. Write one focused regression only when the oracle comparison identifies a concrete better action.

Do not start an OpenSpec proposal yet for `sts_lightspeed`. Revisit proposal work only if we decide to build a long-lived `CommunicationMod trace -> BattleContext -> search result` adapter or expose `BattleContext`/`BattleScumSearcher2` through pybind11.

