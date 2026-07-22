# Adaptive Route Opportunity Audit Specification

## Purpose

Define a deterministic, read-only audit for frozen adaptive-route evidence so route-treatment conclusions remain attributable, bounded, and reproducible.

## Requirements

### Requirement: Frozen evidence ingestion is deterministic and read-only

The audit SHALL accept chronologically ordered AI log paths, one decision-trace path, ordered run-record paths, an explicit log UTC offset, a maximum join tolerance, and an output path. It SHALL read but never modify source evidence and SHALL record each source path, SHA-256, byte count, line count, and parsed-record count. Identical source bytes and analysis parameters SHALL produce byte-identical JSON output.

#### Scenario: Valid frozen sources are loaded

- **WHEN** every source exists, each input type is well formed, game boundaries and ordered run records agree, and all correlations satisfy the configured limits
- **THEN** the audit SHALL set `integrity.status=valid`
- **AND** SHALL preserve source identities and analysis parameters in schema `adaptive-route-opportunity-audit-v1`

#### Scenario: A run contains an inter-act transition slot

- **WHEN** `path_per_floor` contains `null` immediately after a `B` entry and no joined `ChooseMapNodeAction` targets that index
- **THEN** the audit SHALL preserve the `null` as a structural transition slot
- **AND** SHALL NOT treat it as a room symbol, event resolution, route divergence, or optional elite

#### Scenario: A run transition slot is malformed or targeted

- **WHEN** `path_per_floor` contains `null` anywhere other than immediately after `B`, or a joined `ChooseMapNodeAction` targets a `null` index
- **THEN** the audit SHALL mark integrity invalid with run and floor provenance

#### Scenario: A source or correlation is invalid

- **WHEN** a source is missing or malformed, a game boundary is invalid, an ordered run does not corroborate trace path symbols, or a required join is missing, tied, or outside tolerance
- **THEN** the audit SHALL set `integrity.status=invalid`, preserve actionable diagnostics, write no authoritative success claim, and return nonzero

#### Scenario: An event map node resolves to a run room type

- **WHEN** a joined trace action selects `?` and the ordered run records a valid resolved non-boss room symbol at `path_per_floor[decision.floor]`
- **THEN** the audit SHALL preserve both symbols and classify the floor as event-resolution compatible
- **AND** SHALL NOT mark source integrity invalid or reinterpret the resolved room as an optional elite

#### Scenario: A non-event room symbol disagrees

- **WHEN** a joined trace action other than `?` disagrees with the ordered run symbol at `path_per_floor[decision.floor]`
- **THEN** the audit SHALL mark integrity invalid with game, act, floor, trace symbol, and run symbol provenance

#### Scenario: Source evidence is audited

- **WHEN** the audit runs
- **THEN** it SHALL NOT invoke gameplay code, a route planner, training, Communication Mod, or a live game process
- **AND** SHALL NOT write to logs, traces, run records, checkpoints, or persistent live configuration

### Requirement: Adaptive records are parsed exactly and callback repeats are preserved

The audit SHALL recognize only INFO records prefixed `[ADAPTIVE_ROUTE]` whose payload contains the exact ordered key set defined by the adaptive routing contract. It SHALL validate booleans, integers, unavailable values, candidate grammar, candidate counts, and route symbols before using a record.

The audit SHALL assign each occurrence to the active `Starting game #N` boundary and SHALL define a callback-independent record by `(game_number, complete_payload)`. It SHALL retain every occurrence's source path, line, timestamp, and join result while reporting multiplicity and unique-record counts.

#### Scenario: Repeated callbacks commit the same evidence

- **WHEN** two adaptive log occurrences in one game have identical complete payloads and join to semantically identical map decisions
- **THEN** the audit SHALL report one callback-independent record with multiplicity two and both occurrence provenance entries

#### Scenario: Duplicate occurrences disagree

- **WHEN** occurrences in one callback-independent group join to different current coordinates, next-node sets, map graphs, actions, act values, or floor values
- **THEN** the audit SHALL mark integrity invalid rather than choosing one occurrence

#### Scenario: Adaptive payload grammar is malformed

- **WHEN** an adaptive-prefixed line has missing, reordered, repeated, extra, or invalid fields
- **THEN** the audit SHALL preserve its file and line diagnostic, exclude it from opportunity counts, and mark integrity invalid

### Requirement: Policy records correlate to frozen map actions without guessing

Each adaptive occurrence SHALL join to the unique nearest `ScreenType.MAP` decision-trace row with the same act and floor inside the configured tolerance. The audit SHALL validate that the joined row has a map graph, current node, next nodes, enumerated paths, and a `ChooseMapNodeAction` whose node is advertised by `next_nodes`.

For each complete candidate, the audit SHALL enumerate full coordinate paths in the joined frozen map graph that begin at the recorded `start_y` and exactly match the recorded symbol sequence. It SHALL report all matches and SHALL describe a full candidate route as resolved only when exactly one coordinate path matches.

#### Scenario: Candidate routes resolve uniquely

- **WHEN** both candidate symbol sequences each match exactly one reachable coordinate path
- **THEN** the audit SHALL report both coordinate paths, their immediate coordinates, and their first differing coordinate and entered floor, or report that no coordinate differs

#### Scenario: Candidate route is ambiguous

- **WHEN** a candidate symbol sequence matches zero or multiple full coordinate paths
- **THEN** the audit SHALL report the match count and candidate attribution as unresolved
- **AND** SHALL NOT invent a coordinate path or count the opportunity as coordinate-level treatment

#### Scenario: Immediate coordinate is provable without a unique full route

- **WHEN** multiple full paths match one candidate but every match begins at the same coordinate
- **THEN** the audit MAY report that candidate's immediate coordinate
- **AND** SHALL continue to report its full route as unresolved

#### Scenario: First divergence is provable before later ambiguity

- **WHEN** one or both candidates have multiple matching full paths, every earlier index has the same singleton coordinate for both candidates, and one index has different singleton coordinates for the two candidates
- **THEN** the audit SHALL report that index as the provable first divergence and preserve all later path ambiguity

#### Scenario: First divergence is not provable

- **WHEN** any coordinate set before a possible divergence is not the same singleton for both candidates or either candidate has a nonsingleton coordinate set at the possible divergence
- **THEN** the audit SHALL report first-divergence attribution as unresolved and SHALL NOT choose one matching path

#### Scenario: Joined action contradicts the selected candidate

- **WHEN** the selected candidate has a provable immediate-coordinate set and the joined action is outside that set
- **THEN** the audit SHALL mark integrity invalid and preserve the contradiction

### Requirement: Treatment uptake is reported as a causal evidence funnel

The audit SHALL report counts for complete candidate pairs, zero-versus-one opportunities, Act 1 zero-versus-one opportunities, aggressive selections, immediate same/different/ambiguous coordinates, provable first divergences, selections revoked before divergence, routes left before divergence, divergences actually taken, and optional elites actually reached.

An aggressive selection SHALL count as surviving to divergence only when its first divergence is provable, every required later map decision remains an aggressive selection, and actual joined actions remain compatible with at least one recorded aggressive route through the first coordinate that differs from every compatible conservative prefix. It SHALL count as a realized optional elite only when post-divergence actions remain compatible with an aggressive route, the actual action later enters a uniquely attributable extra elite coordinate from that candidate, and the ordered `.run` record corroborates an elite at the same entered floor.

#### Scenario: Aggressive and conservative select the same immediate coordinate

- **WHEN** a zero-versus-one opportunity selects aggressive but both candidates begin at the same provable coordinate
- **THEN** the audit SHALL count one aggressive selection and one same-immediate-coordinate case
- **AND** SHALL NOT count immediate coordinate treatment

#### Scenario: A later replan revokes the selection

- **WHEN** an aggressive selection has a later map decision before its first resolved coordinate divergence and that decision selects conservative or forced conservative
- **THEN** the audit SHALL report the first revocation evidence and SHALL NOT count survival to divergence

#### Scenario: The realized path leaves the candidate before divergence

- **WHEN** joined actions cease to match the original aggressive coordinate route before its first resolved divergence
- **THEN** the audit SHALL report the first departure and SHALL NOT attribute any later elite to the original opportunity

#### Scenario: Optional-elite treatment is realized

- **WHEN** the aggressive selection survives through its first coordinate divergence, later enters the candidate's extra elite coordinate, and the corresponding run `path_per_floor` records exact symbol `E` at that global floor
- **THEN** the audit SHALL count one divergence taken and one realized optional elite

#### Scenario: Evidence remains ambiguous

- **WHEN** candidate coordinates, later decisions, or run corroboration are incomplete or ambiguous
- **THEN** the audit SHALL report the ambiguity separately and SHALL NOT count realized treatment

### Requirement: The frozen qualification POC reproduces known evidence

The first POC SHALL analyze only the retained 2026-07-21 ten-game adaptive qualification evidence and SHALL NOT launch or rerun the game. Its machine-readable result SHALL preserve one deterministic evidence object for every callback-independent candidate-generation fallback, including game number, complete payload, multiplicity, occurrence provenance, joined decision summary, and run corroboration. Its Markdown report SHALL be derived from the machine-readable audit result and SHALL preserve the exact command, source identities, limitations, stop decision, and any failed-then-resumed analysis execution lineage. Operator-observed controls that are not fields in the JSON SHALL be labeled as such.

#### Scenario: Frozen cohort audit succeeds

- **WHEN** the audit reads the two AI log segments in chronological order, the dedicated decision trace, and the ten qualification run records in registered game order
- **THEN** it SHALL reproduce `346` adaptive occurrences, `173` callback-independent records with multiplicity two, `58` zero-versus-one opportunities, `54` Act 1 zero-versus-one opportunities, one aggressive selection, and four callback-independent candidate-generation fallbacks
- **AND** SHALL preserve four separately auditable fallback evidence objects whose multiplicities sum to eight raw occurrences
- **AND** SHALL classify the aggressive selection as sharing the conservative immediate coordinate, being revoked before divergence, and producing zero realized optional elites

#### Scenario: An earlier analysis attempt is superseded

- **WHEN** a fail-closed POC invocation exposes an analysis-format defect and a later invocation is run only after a reviewed analysis fix against unchanged frozen source identities
- **THEN** the durable report SHALL record the failed artifact identity and diagnostic, the reviewed fix, the superseding invocation, and the final artifact identity
- **AND** SHALL distinguish machine-artifact fields from operator-observed process and pre/post source controls

#### Scenario: Frozen cohort checks do not reproduce

- **WHEN** any registered source identity, integrity rule, or expected POC count fails
- **THEN** the report SHALL remain a failed audit, no route threshold or commitment change SHALL be proposed from it, and the same cohort SHALL NOT be rewritten or rerun to force a pass

### Requirement: Verification remains proportionate to analysis-only risk

The implementation SHALL have focused synthetic regressions for source parsing, callback collapse, occurrence joins, candidate graph resolution, ambiguity, revocation, route departure, run corroboration, deterministic output, and invalid-integrity exit behavior. It SHALL pass the repository commit test gate and strict OpenSpec validation.

#### Scenario: Analysis implementation is ready to commit

- **WHEN** focused tests pass, the commit gate passes, strict change validation passes, `git diff --check` is clean, and no gameplay-policy source changed
- **THEN** the analysis script, tests, planning artifacts, and frozen POC reports MAY be committed as one read-only evidence capability

#### Scenario: Verification fails

- **WHEN** any required verification is nonzero or gameplay-policy source changed
- **THEN** the change SHALL remain incomplete and SHALL NOT authorize live qualification, training, tuning, or policy promotion
