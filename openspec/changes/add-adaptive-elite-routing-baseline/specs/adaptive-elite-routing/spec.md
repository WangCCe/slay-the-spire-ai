## ADDED Requirements

### Requirement: Explicit Ironclad adaptive route mode
The system SHALL accept an explicit `adaptive` elite-route mode for Ironclad without changing the behavior of the existing `conservative` and `aggressive` modes or making adaptive the default.

#### Scenario: Ironclad adaptive mode is selected
- **WHEN** an Ironclad agent is started with `--elite-route adaptive`
- **THEN** the system SHALL initialize adaptive route assessment and two-candidate selection for map choices
- **AND** SHALL keep combat and other non-combat policy unchanged

#### Scenario: Another character receives adaptive mode
- **WHEN** a Silent, Defect, or Watcher agent receives `--elite-route adaptive`
- **THEN** the system SHALL use the existing conservative route planner
- **AND** SHALL log the stable reason `unsupported_character`

#### Scenario: Legacy route mode is selected
- **WHEN** the agent is started with `--elite-route conservative` or `--elite-route aggressive`
- **THEN** the system SHALL retain that mode's existing node priorities, route comparison, elite tie breaks, forced-elite behavior, and HP-drop replan trigger

### Requirement: Independent deterministic elite risk inputs
The system SHALL compute adaptive deck readiness independently from HP, map floor, potion support, and relic support. Missing or malformed required state SHALL produce a zero optional-elite budget with a stable fail-closed reason.

Deck-only readiness SHALL equal up to four premium-attack points, up to two strong-block points, and one point for upgraded Bash. Potion support SHALL be the usable count capped at two from Fire, Attack, Strength, Flex, Dexterity, Skill, Power, Fear, Duplication, Distilled Chaos, Explosive, Swift, Energy, and Entropic Brew potions. Relic support SHALL be capped at two; Preserved Insect SHALL contribute two, while Akabeko, Vajra, Bag of Marbles, Anchor, Orichalcum, Oddly Smooth Stone, Lantern, Blood Vial, and Meat on the Bone SHALL each contribute one. Burning Blood SHALL contribute zero support.

#### Scenario: Prepared Act 1 state receives a bounded budget
- **WHEN** the player is Ironclad, the optional elite's local map floor `node.y + 1` is at least 6, HP is at least 48 and 75 percent, deck-only readiness is at least 5, the resource and recovery gates pass, no elite was previously traversed, the conservative candidate contains zero elites, and the aggressive candidate contains exactly one
- **THEN** the assessment SHALL allow an optional-elite budget of exactly one
- **AND** SHALL emit each independent input and its reason codes

#### Scenario: Low HP fails closed
- **WHEN** current HP is below 48 or below 75 percent of max HP
- **THEN** the assessment SHALL return an optional-elite budget of zero regardless of route reward or support

#### Scenario: Resource support is insufficient
- **WHEN** deck-only readiness is between 5 and 6, no usable combat potion exists, and relic support is below 2
- **THEN** the assessment SHALL return an optional-elite budget of zero

#### Scenario: Exceptional deck or relic support replaces a potion
- **WHEN** deck-only readiness is 7 or relic support is 2 and all other hard gates pass
- **THEN** the resource gate SHALL pass without a usable combat potion

#### Scenario: Later-act optional elite is considered
- **WHEN** an adaptive candidate adds an optional elite in Act 2 or Act 3
- **THEN** the first adaptive baseline SHALL return an optional-elite budget of zero

#### Scenario: Required state is malformed
- **WHEN** character, act, HP, max HP, map coordinates, or candidate-path structure cannot be normalized safely
- **THEN** the assessment SHALL return an optional-elite budget of zero with a stable fail-closed reason

### Requirement: Two-candidate adaptive selection
The adaptive planner SHALL generate one complete route with the existing conservative behavior and one complete route with the existing aggressive behavior. It SHALL select the aggressive candidate only when conservative contains zero elites, aggressive contains exactly one, and that elite passes every hard gate. It SHALL select conservative for every other elite-count pair and SHALL NOT compare the modes' incompatible raw route scores or enumerate the full path set.

#### Scenario: Prepared aggressive candidate is recoverable
- **WHEN** conservative contains zero elites, aggressive contains exactly one Act 1 elite, that elite has a rest site within two path nodes before or after it, and all state gates pass
- **THEN** the adaptive selector SHALL select the aggressive candidate without comparing legacy route scores

#### Scenario: Optional elite has no ordinary recovery window
- **WHEN** the added elite has no rest site within two path nodes before or after it
- **THEN** the selector SHALL reject the aggressive candidate unless HP is at least 90 percent, deck-only readiness is 7, and a usable combat potion exists

#### Scenario: Aggressive candidate contains two elites
- **WHEN** the aggressive candidate contains at least two elites
- **THEN** the selector SHALL reject it regardless of node-reward sum

#### Scenario: One elite is forced on every complete route
- **WHEN** the complete conservative candidate contains one elite
- **THEN** the selector SHALL choose the conservative candidate with reason `forced_elite_route`
- **AND** SHALL NOT classify the forced elite as optional budget

#### Scenario: Two elites are forced on every complete route
- **WHEN** the complete conservative candidate contains two elites
- **THEN** the selector SHALL still choose the conservative minimum-elite candidate with reason `forced_elite_route`
- **AND** SHALL preserve its existing later-first-elite tie break

#### Scenario: An elite was already traversed
- **WHEN** the current act's idempotent visited-node history contains an elite and the aggressive candidate adds optional exposure
- **THEN** the selector SHALL reject the aggressive candidate for that act

#### Scenario: Candidate generation is incomplete
- **WHEN** either candidate cannot be generated completely because the map is malformed or the route generator fails
- **THEN** the system SHALL discard the adaptive comparison
- **AND** SHALL run the existing conservative planner once with reason `candidate_generation_failed`

#### Scenario: Candidate elite counts do not form zero versus one
- **WHEN** the candidates have equal elite counts or any pair other than conservative zero and aggressive one
- **THEN** the selector SHALL choose the conservative candidate deterministically

### Requirement: Adaptive replanning and observability
The system SHALL update visited-node and latest-rest history idempotently by act and SHALL regenerate both adaptive candidates at every map choice from the current game state. Each decision SHALL emit one structured summary suitable for live diagnosis.

#### Scenario: State changes after a room
- **WHEN** HP, deck, potion inventory, relic inventory, act, visited path, or reachable branch changes before the next adaptive map choice
- **THEN** the system SHALL recompute both candidates and the risk assessment rather than reuse the previous full-act selection blindly

#### Scenario: Communication Mod repeats a map state
- **WHEN** the same current map coordinate is received more than once
- **THEN** visited-node, rest-history, and elite-exposure tracking SHALL remain unchanged after the first observation

#### Scenario: Adaptive route decision is logged
- **WHEN** the adaptive selector chooses either candidate
- **THEN** one structured log entry SHALL include character, normalized state, both path summaries, minimum and added elite counts, recovery distances, optional budget, selection, and stable reason codes

### Requirement: Pre-implementation feasibility gate
Before adaptive gameplay code is implemented, the existing route generator SHALL be measured over every legacy characterization fixture plus three versioned full-height Act 1 fixtures with the production Windows interpreter. Each full-height fixture SHALL contain 15 layers (`y=0..14`), seven possible columns, at least 35 reachable nodes, one or two children per nonterminal reachable node, and respectively sparse, typical, and dense elite/rest placement.

Each full-height fixture SHALL receive ten excluded warm-up pairs and 100 timed pairs. A timed pair SHALL start immediately before conservative `generate_map_route()` and end immediately after aggressive `generate_map_route()` returns on separate agents initialized from identical fixture state. Timing SHALL use `perf_counter_ns` and SHALL include normal route logging.

#### Scenario: Paired-route POC passes
- **WHEN** every paired candidate completes, aggregate median paired latency is no greater than 25 ms, and every measured pair is no greater than 100 ms
- **THEN** implementation MAY proceed with the two-candidate design
- **AND** the POC report SHALL preserve fixture JSON and SHA-256 identities, command, interpreter, warm-up and measured counts, and per-fixture and aggregate median, p95, and maximum latency

#### Scenario: Paired-route POC fails
- **WHEN** candidate generation is incomplete or either latency threshold is exceeded
- **THEN** gameplay implementation SHALL stop
- **AND** the proposal SHALL be revised before another planner approach is attempted

#### Scenario: The first POC failure also exposes qualification-harness gaps
- **WHEN** the first expanded POC exceeds a latency limit and independent review finds missing runtime fixture validation, protocol bounds, or raw timing evidence in the dirty qualification worktree
- **THEN** the failed report SHALL be preserved without reinterpretation or overwrite
- **AND** only qualification-harness tests, validation, and evidence serialization MAY change before a new source revision is frozen
- **AND** exactly one clean-source requalification MAY run with the same seven cases, production interpreter, exact ten warm-up pairs and exact 100 measured pairs per case (700 measured pairs total), normal logging, and unchanged `25 ms` median and `100 ms` maximum limits
- **AND** the benchmark SHALL write `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json` and the Markdown report at `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.md` SHALL be generated from that exact result without overwriting canonical or `attempt-1-fail` evidence

#### Scenario: The sole clean-source requalification completes
- **WHEN** the frozen qualification source is run once after the proposal revision
- **THEN** both formal attempts and their source provenance SHALL be preserved
- **AND** the clean-source evidence SHALL contain the seven-case, 700-pair result at `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json` and its Markdown derivative at `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.md`
- **AND** gameplay implementation MAY proceed only if every candidate completes and both unchanged latency limits pass
- **AND** a miss SHALL stop this change without another POC retry

### Requirement: Controlled automated qualification execution recovery
The canonical automated qualification report at `reports/adaptive_elite_routing_automated_qualification_20260721.md` SHALL remain immutable attempt-1 sandbox FAIL evidence, retaining focused `183 passed` and the original gameplay, commit, and full failures, basetemps, durations, and exit codes.

#### Scenario: Managed-sandbox ACL failure is isolated
- **WHEN** pytest `9.0.2` cleanup reaches `cleanup_dead_symlinks(basetemp)` and its `root.iterdir()` call is denied
- **THEN** the evidence SHALL record that a direct single `tmp_path` node passed, the same node under parent-Python to pytest-child failed, nested Python `mkdir(mode=0o700)` followed immediately by `iterdir()` failed in the managed sandbox, and that same minimal operation passed under host permission
- **AND** the failure SHALL be treated as an execution-environment ACL failure, not an adaptive-route or test-assertion failure

#### Scenario: One corrected host-permission attempt is authorized
- **WHEN** the attempt-1 ACL evidence is preserved
- **THEN** exactly one host-permission execution each of the unchanged `gameplay`, `commit`, and `full` gate commands SHALL be permitted with the existing manifest, thresholds, and gate-generated unique basetemps
- **AND** focused verification SHALL NOT be rerun because the direct focused command already passed `183` tests
- **AND** the corrected result SHALL be written only to `reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md`
- **AND** the original attempt-1 failures SHALL remain failures

#### Scenario: Corrected automated qualification fails
- **WHEN** any corrected gate fails for a reason other than the sole known stream-silence full-gate node
- **THEN** qualification SHALL stop with the corrected evidence preserved and no further retry, code/test change, training change, or live-config change
- **AND** the known stream-silence node MAY receive only its existing one-node diagnostic run when it is the sole full-gate failure

### Requirement: No-training live qualification and rollback
The adaptive baseline SHALL be evaluated in one fresh ten-game Ironclad A0 cohort using the production Windows interpreter with training disabled, and the persistent live configuration SHALL be restored to conservative after completion or operational failure.

`elite_encounters` SHALL be the total `E` nodes reached across cohort run paths. `elite_death_runs` SHALL count runs whose normalized `killed_by` is the elite encountered as the final combat. `elite_fatality_ratio` SHALL equal `elite_death_runs / elite_encounters`. A repeated A-class sim-divergence cluster SHALL mean at least two fresh rows with the same normalized action type, combat phase, affected entity/card/power, and mismatched field, plus a demonstrated causal mechanics or legality effect.

#### Scenario: Adaptive cohort is eligible for larger validation
- **WHEN** the fresh cohort records at least three elite encounters, no more than two elite-death runs, an elite fatality ratio no greater than 25 percent, average floor at least 24.2, at least three Act 2 boss reaches, no runtime error, and no repeated A-class sim-divergence cluster
- **THEN** the report SHALL mark adaptive as eligible only for a larger validation cohort
- **AND** SHALL NOT change the default route mode or authorize training

#### Scenario: Adaptive cohort misses any gate
- **WHEN** any qualification threshold or operational integrity check fails
- **THEN** the report SHALL preserve the run ids, metric inputs, and failure evidence
- **AND** conservative SHALL remain the live rollback mode
- **AND** the same cohort SHALL NOT be tuned and rerun as if it were fresh evidence

#### Scenario: Victory occurs during qualification
- **WHEN** any qualified run record has `victory=true`
- **THEN** the report SHALL identify it as progress on the outer gameplay objective without weakening the remaining evidence requirements
