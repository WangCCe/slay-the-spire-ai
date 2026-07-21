## Context

The current `AdaptiveMapRouter` exposes only fixed `conservative` and `aggressive` elite modes. Conservative mode applies a route-blocking elite penalty and lexicographically minimizes elite count. Aggressive mode can reward an Act 1 elite after a readiness check and uses HP-only Act 2+ adjustments. `SimpleAgent` plans to the top of the current map and normally replans only at act start or after a ten percentage-point HP loss.

The 2026-07-20 no-training Ironclad A0 comparison showed the resulting gap. Ten conservative runs averaged floor 24.2, reached three Act 2 bosses, and took no elites. Ten aggressive runs averaged floor 18.9, reached no Act 2 bosses, traversed about nine elite nodes, and had five elite-caused death runs. The first baseline therefore needs a narrow middle ground rather than another global weight set.

Production gameplay remains coupled to Communication Mod and the Windows interpreter. The implementation must be deterministic, inexpensive at map-choice frequency, diagnosable from `ai_debug.log`, and reversible by selecting the existing conservative mode.

## Goals / Non-Goals

**Goals:**

- Add an explicit Ironclad-only adaptive route mode that can choose one optional, well-supported Act 1 elite only when a zero-elite conservative route exists.
- Base the decision on local map floor, absolute and relative HP, deck-only readiness, usable combat potions, recognized combat or sustain relics, recovery proximity, prior elite exposure, and downstream elite count.
- Recompute from current game state at every adaptive map choice.
- Keep risk assessment and route selection pure enough for fixture-driven regression tests.
- Produce bounded live evidence against the preserved conservative and aggressive cohorts.

**Non-Goals:**

- Learning route policy through RL, changing reward/state/action spaces, or training any model.
- Copying Bottled AI path weights or adding it as a runtime dependency. Its reward-versus-survivability structure remains comparator context only.
- Authorizing optional Act 2 or Act 3 elites in the first adaptive baseline.
- Supporting adaptive elite selection for Silent, Defect, or Watcher in the first baseline.
- Changing combat, shop, event, card-reward, or campfire decision policy.
- Changing the CLI default or persistent Communication Mod configuration as part of implementation.

## Decisions

### 1. Add a third explicit mode and preserve legacy paths

`--elite-route adaptive` will be accepted and passed through the existing agent constructors. For Ironclad it enables adaptive route selection. For another character it deterministically uses the existing conservative planner and logs `unsupported_character`; auto-detection therefore remains safe. Conservative and aggressive calls retain their existing priorities, route comparison, forced-elite behavior, and HP-drop replan trigger. Adaptive is opt-in until live qualification supports a separate promotion decision.

Before refactoring the shared route generator, characterization fixtures will lock the chosen node, elite tie break, and forced one- and two-elite behavior of both legacy modes.

Alternatives considered:

- Relax conservative penalties globally. Rejected because it removes the proven rollback behavior and still encodes one fixed risk level.
- Make adaptive the default immediately. Rejected because the current evidence only motivates an experiment.

### 2. Use independent, deterministic readiness dimensions

`map_routing.py` will expose immutable normalized state, candidate features, and assessment results. The output includes eligibility, an optional-elite budget of zero or one, and stable reason codes. It does not compare legacy route scores because conservative and aggressive assign intentionally incompatible elite weights.

The new deck-only readiness score is separate from HP, floor, potions, and relics:

- up to four points for cards in the existing `ACT1_PREMIUM_ATTACKS` set;
- up to two points for cards in the existing `ACT1_STRONG_BLOCKS` set;
- one point for upgraded Bash.

Potion support is the usable count, capped at two, from the existing combat-potion allowlist: Fire, Attack, Strength, Flex, Dexterity, Skill, Power, Fear, Duplication, Distilled Chaos, Explosive, Swift, Energy, and Entropic Brew potions.

Relic support is capped at two points. Preserved Insect contributes two. Akabeko, Vajra, Bag of Marbles, Anchor, Orichalcum, Oddly Smooth Stone, Lantern, Blood Vial, and Meat on the Bone each contribute one. Burning Blood is not support because it is the Ironclad baseline relic.

The first policy authorizes one optional elite only when all hard gates pass:

- the player is Ironclad;
- the candidate optional elite is in Act 1 and its local map floor, defined as `node.y + 1`, is at least 6;
- current HP is at least 48 and at least 75 percent of max HP;
- deck-only readiness is at least 5;
- at least one usable combat potion exists, unless deck-only readiness is 7 or relic support is 2;
- no elite, forced or optional, has already been traversed in the act;
- the conservative candidate contains zero elites and the aggressive candidate contains exactly one;
- the optional elite has a rest site within two path nodes before or after it, unless HP is at least 90 percent, deck-only readiness is 7, and a usable combat potion exists.

Missing or malformed state fails closed to a zero optional budget. Support can satisfy only the named resource gate; it cannot bypass character, HP, act, exposure, downstream-count, or recovery gates. The existing aggressive readiness function remains unchanged for legacy compatibility and is not reused by adaptive.

### 3. Select between two existing candidate routes

The first adaptive planner will generate exactly two complete candidates with the existing route algorithm: one under conservative mode and one under aggressive mode. It will not enumerate every path and will not import a second path simulator.

The conservative candidate defines whether zero-elite avoidance is reachable under existing lexicographic behavior. The first baseline selects the aggressive candidate only when conservative contains zero elites, aggressive contains exactly one elite, and that elite passes the risk assessment, recovery, and downstream gates. When all hard gates pass, adaptive selects aggressive without comparing the two modes' incompatible raw route scores. Otherwise it selects conservative.

If the conservative candidate contains one or more elites, selecting it is a valid `forced_elite_route`, not an empty-candidate or planner-error fallback. Adaptive never adds an optional elite above forced exposure in the first baseline. Forced elites still count in live outcome metrics and, once traversed, keep the optional budget closed for the act.

If either candidate cannot be generated completely because of a malformed map or route-generator error, the adaptive result is discarded and the existing conservative planner is run once with a stable `candidate_generation_failed` reason. Equal elite counts and all other non-qualifying candidate pairs select conservative deterministically.

Alternatives considered:

- Enumerate up to 100,000 complete paths. Rejected as too heavy for the first baseline and unnecessary when two established route modes already bound the useful experiment.
- Extend the one-state-per-node dynamic program with multiple recovery and exposure states. Rejected until evidence shows the two-candidate selector misses safe elite routes.
- Port Bottled AI's projected-health path simulator. Rejected because its generic damage constants are not validated against this agent's combat policy.

### 4. Track exposure and replan at every adaptive map decision

The agent records visited map coordinates per act and derives prior elite exposure from visited elite nodes. The tracker resets on act change and is idempotent when Communication Mod repeats a state. It also records the latest visited rest floor so recovery before an optional elite can include already-traversed path state.

Adaptive mode regenerates both candidate routes at each map choice so acquired cards, potions, relics, HP changes, and newly committed branches are reflected immediately. Legacy modes keep the current HP-drop replan behavior.

Every adaptive decision logs one structured line containing character, normalized state, both candidate path summaries, minimum and added elite counts, recovery distances, optional budget, selection, and reason codes. It contains no random draw because the policy is deterministic.

### 5. Gate implementation on a small feasibility POC

Before gameplay code changes, a read-only POC will run the existing route generator in conservative and aggressive modes over every legacy characterization fixture plus three deterministic full-height Act 1 fixtures. Each full-height fixture has 15 map layers (`y=0..14`), seven possible columns, at least 35 reachable nodes, one or two children per nonterminal reachable node, and respectively sparse, typical, and dense elite/rest placement. Fixture JSON and SHA-256 identities are preserved in the report.

For each full-height fixture, ten paired warm-up samples are excluded, followed by 100 timed paired samples. One paired sample starts immediately before conservative `generate_map_route()` and ends immediately after aggressive `generate_map_route()` returns on separate agents built from identical fixture state. Timing uses `perf_counter_ns` under the production Windows interpreter and includes normal route logging. Results are reported per fixture and aggregate. The design remains eligible only when every candidate completes, aggregate median is no greater than 25 ms, and every measured sample is no greater than 100 ms. A miss requires revising the proposal before gameplay implementation.

The first expanded seven-case attempt recorded an aggregate median of `16.6877 ms` and one `105.1622 ms` maximum while the qualification worktree was dirty. That failure remains immutable. Independent review then found evidence-harness omissions: runtime fixture-contract checks, exact protocol bounds, and raw per-pair durations. The proposal revision permits those harness-only fixes to be frozen without gameplay changes, followed by exactly one formal requalification on a clean committed source. The requalification uses the same production interpreter, seven cases, exact `10` warm-ups and `100` measured pairs per case (700 measured pairs total), normal logging, and unchanged latency limits. Its benchmark command writes `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json`; `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.md` is generated from that exact result after the run. Neither the canonical first FAIL evidence nor `attempt-1-fail` evidence is overwritten. Diagnostic runs made while investigating the first miss are not qualification evidence. Both formal attempts are retained; if the clean-source attempt misses either limit, gameplay implementation stops and no further POC retry is allowed in this change.

This POC validates the only new performance multiplier: two existing dynamic-programming passes at each adaptive map choice.

### 6. Use a bounded no-training promotion gate

After regression coverage, focused routing tests, the `gameplay` test gate, the `commit` test gate, and one unchanged full test gate, run one fresh ten-game Ironclad A0 adaptive cohort with the production Windows interpreter and no training. Restore conservative configuration after the cohort or on any operational failure.

For cohort metrics:

- `elite_encounters` is the total count of `E` nodes reached across the ten `.run` paths, including forced elites;
- `elite_death_runs` is the count of runs whose normalized `killed_by` is an elite encountered as the final combat;
- `elite_fatality_ratio` is `elite_death_runs / elite_encounters` and is undefined when exposure is below the required minimum;
- a repeated A-class sim-divergence cluster means at least two fresh rows with the same normalized action type, combat phase, affected entity/card/power, and mismatched field, plus a demonstrated causal mechanics or legality effect.

The cohort becomes a candidate for a larger validation only if it:

- records at least three elite encounters;
- has no more than two elite-death runs and an elite fatality ratio no greater than 25 percent;
- reaches average floor 24.2 or higher and at least three Act 2 bosses;
- introduces no runtime error and no repeated A-class sim-divergence cluster.

The report preserves every run id and relevant log/trace cutoff. Passing does not change defaults or authorize training. A `victory=true` run remains the outer objective.

### 7. Correct a proven managed-sandbox qualification ACL failure once

The canonical automated qualification record at `reports/adaptive_elite_routing_automated_qualification_20260721.md` is immutable attempt-1 sandbox FAIL evidence. It retains focused `183 passed` and the original gameplay, commit, and full basetemps, durations, and exit codes; those failures are not converted to passes or overwritten.

The post-attempt evidence isolates the failure to the execution environment: pytest `9.0.2` executes `cleanup_dead_symlinks(basetemp)`, which calls `root.iterdir()` before inspecting or unlinking any child; a direct single `tmp_path` node passed; that same node under parent-Python to pytest-child execution failed; nested Python `mkdir(mode=0o700)` followed immediately by `iterdir()` failed in the managed sandbox; and the same minimal nested mkdir/iterdir operation passed under host permission. This proves a managed-sandbox ACL failure rather than an adaptive-route or test-assertion failure.

Exactly one corrected host-permission sequence is authorized, running the unchanged commands below in this order with the existing manifest, thresholds, and gate-generated unique basetemps:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py gameplay
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

Focused verification is not rerun because the original direct focused command already passed `183` tests. Run `gameplay`, then `commit`, then `full` only while the preceding gate exited `0`; stop immediately at the first nonzero result. The known stream-silence node retains its existing one-node diagnostic allowance only when `full` is reached and it is the sole full-gate failure. That diagnostic is attribution-only: the original full result remains nonzero and failed, and no retry is authorized. Task `4.3b` completes when this sequence is executed according to that stop rule and its evidence is preserved. Qualification success requires gameplay, commit, and full each to exit `0`. The corrected result is written only to `reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md`; `4.4` and live qualification are forbidden unless all-three success exists. Final review begins only after that success. A Critical or Important review finding blocks this qualification and requires a follow-up change and new evidence, not a same-attempt code fix or focused-test rerun. This execution correction does not weaken POC no-retry rules, live promotion thresholds, no-training constraints, conservative default/rollback behavior, or the outer `victory=true` objective.

## Risks / Trade-offs

- [Hand-authored thresholds can be too strict or too permissive] -> Keep independent inputs explicit, fixture-tested, and subject to one bounded qualification without same-cohort tuning.
- [The aggressive candidate can miss a safer one-elite path] -> Treat this as a deliberately narrow baseline; broaden the planner only after repeated live evidence.
- [Two route passes can add latency] -> Require the pre-implementation POC and fail the design gate if the stated Windows budget is missed.
- [Communication Mod can repeat map states] -> Track visited coordinates idempotently and recompute decisions deterministically.
- [A route can look safe while combat policy still loses] -> Treat live elite outcomes as the promotion authority and retain conservative rollback.
- [Small unpaired cohorts are noisy] -> Require minimum exposure and use the ten-game gate only to authorize a larger validation.

## Migration Plan

1. Add legacy characterization fixtures and run the read-only paired-route feasibility POC.
2. Preserve the first failed attempt, freeze the review-complete qualification harness, and run the sole clean-source requalification under unchanged limits.
3. If the clean-source POC passes, add adaptive policy and selector regressions before implementation.
4. Add the adaptive mode without changing defaults or live configuration.
5. Verify focused, gameplay, commit, and unchanged full test gates.
6. Temporarily launch one fresh no-training adaptive cohort, collect evidence, and restore conservative configuration.
7. If any hard gate, runtime check, or evidence threshold fails, keep conservative live and record the rejection without tuning or rerunning the same evidence gate.

Rollback is immediate: select `--elite-route conservative`; no data, checkpoint, protocol, or schema migration is required.

## Open Questions

No implementation-blocking question remains. Any threshold revision, additional candidate route, Act 2+ or non-Ironclad authorization, default change, or RL route-policy work requires fresh evidence and a follow-up change.
