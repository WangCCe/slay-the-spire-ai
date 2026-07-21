## MODIFIED Requirements

### Requirement: Explicit Ironclad adaptive route mode
The system SHALL accept an explicit `adaptive` elite-route mode for agents whose MAP choices are owned by the heuristic router, without changing the behavior of the existing `conservative` and `aggressive` modes or making adaptive the default. Full RL owns MAP actions through its learned policy and SHALL reject adaptive routing instead of silently ignoring it.

The stable compatibility error SHALL be `--elite-route adaptive is unsupported for --agent rl; adaptive routing requires a heuristic map owner`.

#### Scenario: Ironclad heuristic adaptive mode is selected
- **WHEN** an Ironclad `simple`, `optimized`, `auto`, or `combat_rl` agent is started with `--elite-route adaptive`
- **THEN** the system SHALL initialize adaptive route assessment and two-candidate selection for heuristic MAP choices
- **AND** SHALL keep combat and other non-combat policy unchanged

#### Scenario: Another character receives adaptive mode
- **WHEN** a Silent, Defect, or Watcher heuristic map owner receives `--elite-route adaptive`
- **THEN** the system SHALL use the existing conservative route planner
- **AND** SHALL log the stable reason `unsupported_character`

#### Scenario: Direct full-RL construction requests adaptive mode
- **WHEN** `create_agent()` receives agent type `rl` and elite-route mode `adaptive`
- **THEN** it SHALL raise `ValueError` with the exact stable compatibility error
- **AND** SHALL do so before the RL factory, checkpoint loading, or any `SimpleAgent` fallback path is entered

#### Scenario: Parsed CLI full-RL startup requests adaptive mode
- **WHEN** parsed CLI startup receives `--agent rl --elite-route adaptive`
- **THEN** startup SHALL exit with status `2` and stderr SHALL contain the exact stable compatibility error
- **AND** SHALL NOT invoke the RL factory, checkpoint loading, or any `SimpleAgent` fallback path

#### Scenario: Legacy route mode is selected
- **WHEN** the agent is started with `--elite-route conservative` or `--elite-route aggressive`
- **THEN** the system SHALL retain that mode's existing node priorities, route comparison, elite tie breaks, forced-elite behavior, HP-drop replan trigger, and full-RL startup behavior

### Requirement: Two-candidate adaptive selection
The adaptive planner SHALL generate one complete route with the existing conservative behavior and one complete route with the existing aggressive behavior. It SHALL select the aggressive candidate only when conservative contains zero elites, aggressive contains exactly one, and that elite passes every hard gate. It SHALL select conservative for every other elite-count pair and SHALL NOT compare the modes' incompatible raw route scores or enumerate the full path set.

If adaptive candidate generation or strict whole-map validation raises the dedicated candidate-generation error while the active origin and committed history remain valid, the system SHALL invoke the existing conservative builder exactly once without repeating strict whole-map validation. It SHALL validate the returned complete route against the active origin, validated history prefix, map bounds, coordinates, edges, and completion boundary before committing it with reason `candidate_generation_failed`.

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

#### Scenario: Candidate generation is incomplete mid-act
- **WHEN** strict adaptive validation finds an irrelevant malformed earlier node or either adaptive candidate fails while the current origin and absolute history prefix remain valid
- **THEN** the system SHALL discard the adaptive comparison
- **AND** SHALL preserve the validated absolute history prefix
- **AND** SHALL invoke the existing conservative planner exactly once without repeating strict whole-map validation
- **AND** SHALL commit only its validated complete route with reason `candidate_generation_failed`

#### Scenario: Candidate generation is incomplete at the first map choice
- **WHEN** adaptive candidate generation fails at an act's first map choice where the current node is absent or a start sentinel and every advertised next node is on `y=0`
- **THEN** the system SHALL treat `start_y=0` with an empty current-act history prefix as a valid initial origin
- **AND** SHALL ignore any stale complete `map_route` retained from the previous act rather than copy it into the new route or reject recovery
- **AND** SHALL invoke the existing conservative planner exactly once and commit only its validated complete route with reason `candidate_generation_failed`

#### Scenario: Recovery integrity is invalid
- **WHEN** the active origin is absent with nonzero-row next nodes, current-act committed history is invalid, the conservative builder raises, its returned route is invalid, or an unexpected selector or programming error occurs
- **THEN** the error SHALL propagate without adaptive or conservative retry
- **AND** route, replan metadata, and adaptive decision logs SHALL remain unchanged

#### Scenario: Candidate elite counts do not form zero versus one
- **WHEN** the candidates have equal elite counts or any pair other than conservative zero and aggressive one
- **THEN** the selector SHALL choose the conservative candidate deterministically

### Requirement: Adaptive replanning and observability
The system SHALL update visited-node and latest-rest history idempotently by act and SHALL regenerate both adaptive candidates at every map choice from the current game state. Each committed adaptive decision SHALL emit exactly one whitespace-delimited INFO record prefixed `[ADAPTIVE_ROUTE]`; an uncommitted error SHALL emit none.

After the prefix, the record SHALL contain exactly these keys in this order:

```text
outcome character act floor state_valid hp hp_pct deck potion relic elite_seen last_rest_floor candidate_pair conservative_candidate aggressive_candidate minimum_elites added_elites fallback_candidate budget selected reasons
```

Every field SHALL be serialized as `key=value` with no whitespace in the value. Booleans SHALL be lowercase `true` or `false`; unavailable data SHALL be `unavailable`; a valid empty optional value SHALL be `none`; reason codes and integer lists SHALL be joined with `|`; route symbols SHALL be joined with `/`; and `hp_pct` SHALL use exactly six decimal places.

An available candidate SHALL use this exact comma-delimited value grammar:

```text
mode:<mode>,start_y:<integer>,symbols:<symbol>/<symbol>|none,elite_count:<integer>,elite_floors:<integer>|<integer>|none,recovery_before:<integer|none>,recovery_after:<integer|none>
```

`outcome` SHALL be `success`, `forced`, `unsupported`, or `candidate_generation_failed`. A complete candidate pair SHALL set `candidate_pair=complete`, serialize both candidates, set `minimum_elites` to the conservative elite count, set `added_elites` to aggressive count minus conservative count, and set `fallback_candidate=not_used`. An unsupported character SHALL set `candidate_pair=not_attempted`, both candidate values and both count values to `unavailable`, and `fallback_candidate=not_applicable`. A recovered candidate failure SHALL set `candidate_pair=generation_failed`, both pair candidates and both count values to `unavailable`, and serialize the validated conservative recovery candidate in `fallback_candidate`.

`state_valid` SHALL report the adaptive state's validator result. When false, `hp`, `hp_pct`, `deck`, `potion`, `relic`, `elite_seen`, and `last_rest_floor` SHALL all be `unavailable`; `character`, `act`, and `floor` SHALL be normalized independently or reported as `unavailable`. The decision payload SHALL be prepared before route commit, and the single record SHALL be emitted only after chosen-path logging and route/replan metadata commit succeed.

#### Scenario: State changes after a room
- **WHEN** HP, deck, potion inventory, relic inventory, act, visited path, or reachable branch changes before the next adaptive map choice
- **THEN** the system SHALL recompute both candidates and the risk assessment rather than reuse the previous full-act selection blindly

#### Scenario: Communication Mod repeats a map state
- **WHEN** the same current map coordinate is received more than once
- **THEN** visited-node, rest-history, and elite-exposure tracking SHALL remain unchanged after the first observation

#### Scenario: Complete pair decision is logged
- **WHEN** the adaptive selector commits a normal or forced decision from a complete candidate pair
- **THEN** one record SHALL contain the exact ordered key set and grammar
- **AND** SHALL set `outcome=forced` only for a forced-elite selection and `outcome=success` otherwise
- **AND** SHALL include both validated candidate summaries and the exact minimum and added elite counts

#### Scenario: Unsupported character decision is logged
- **WHEN** adaptive mode commits conservative routing for an unsupported heuristic character
- **THEN** one record SHALL use `outcome=unsupported`, `candidate_pair=not_attempted`, unavailable pair evidence, `fallback_candidate=not_applicable`, and reason `unsupported_character`

#### Scenario: Candidate failure decision is logged
- **WHEN** one validated conservative recovery route commits after candidate generation failure
- **THEN** one record SHALL use `outcome=candidate_generation_failed`, `candidate_pair=generation_failed`, unavailable pair evidence, and the validated recovery candidate summary

#### Scenario: Invalid adaptive state is logged honestly
- **WHEN** a route commits but adaptive state validation fails
- **THEN** one record SHALL set `state_valid=false` and every affected policy input to `unavailable`
- **AND** SHALL NOT present normalization sentinels as usable state

#### Scenario: Route decision does not commit
- **WHEN** candidate generation, fallback validation, payload preparation, or chosen-path logging raises before route and replan metadata commit
- **THEN** no `[ADAPTIVE_ROUTE]` record SHALL be emitted
- **AND** route and replan metadata SHALL remain unchanged

## ADDED Requirements

### Requirement: Fresh qualification after blocked whole-change review
The system change SHALL preserve the original automated PASS report and whole-change FAIL review without overwrite. The follow-up SHALL validate both active OpenSpec changes and the complete range from original proposal commit `e1a559f37` through follow-up HEAD before live qualification can proceed.

#### Scenario: Follow-up implementation is ready for qualification
- **WHEN** all follow-up task reviews and focused routing/main regressions are clean
- **THEN** one host-permission `gameplay`, `commit`, and `full` gate sequence SHALL run in order with no retry
- **AND** each reached command's raw terminal transcript, resolved command, unique basetemp, count, duration, and exit code SHALL be preserved separately from the original reports

#### Scenario: A fresh gate fails
- **WHEN** any fresh gameplay, commit, or full gate exits nonzero
- **THEN** follow-up qualification SHALL stop at that result
- **AND** no code, test, gate-policy, or qualification-command fix and no gate rerun SHALL occur within this follow-up change
- **AND** a known stream-silence diagnostic SHALL remain attribution-only and SHALL NOT convert a failed full gate to success
- **AND** live qualification SHALL remain forbidden

#### Scenario: Fresh gates and review pass
- **WHEN** every reached gate exits `0`, both active changes pass strict OpenSpec validation, `git diff --check e1a559f37..HEAD` is clean, and an independent whole-range review has no unresolved Critical or Important finding
- **THEN** the follow-up MAY satisfy the original adaptive change task `4.4`
- **AND** the previously specified bounded no-training live cohort MAY begin without changing defaults or persistent rollback configuration

#### Scenario: Fresh review finds a blocking issue
- **WHEN** the independent whole-range review reports a Critical or Important finding
- **THEN** both changes SHALL remain blocked
- **AND** no code, test, gate-policy, or review-policy fix and no qualification rerun SHALL occur within this follow-up change
- **AND** the finding SHALL require a separately proposed change and fresh evidence
