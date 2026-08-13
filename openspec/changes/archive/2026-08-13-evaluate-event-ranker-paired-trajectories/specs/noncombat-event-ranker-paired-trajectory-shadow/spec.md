## ADDED Requirements

### Requirement: Exact paired trajectories
The experiment SHALL run pure Current and bound event-overlay arms from separate
environments initialized with each identical fixed seed.

#### Scenario: Pair is complete
- **WHEN** both arms reach supported terminal outcomes
- **THEN** the experiment records both action traces, event decisions, terminal outcomes, and paired deltas

#### Scenario: Pair reaches registered unsupported state
- **WHEN** either arm reaches a registered support boundary
- **THEN** the experiment excludes the incomplete pair and records its reason within the fixed censor limit

### Requirement: Bound event-only overlay
The selected arm SHALL execute the exact manifest-bound event model and stored
threshold only at eligible multi-option event states and SHALL preserve Current
for every other decision.

#### Scenario: Event proposal differs confidently
- **WHEN** the learned event action differs from Current and meets the stored threshold
- **THEN** the selected arm executes the learned legal action and records an override

#### Scenario: State is not an eligible event
- **WHEN** the current target state is route, shop, card reward, or a single-option event
- **THEN** the selected arm executes Current's legal action unchanged

### Requirement: Fixed whole-trajectory gate
The experiment SHALL decide integration readiness from fixed support, exposure,
victory, floor, return, and paired-regression gates.

#### Scenario: Whole-trajectory benefit passes
- **WHEN** pair support and event exposure floors pass, selected mean return improves Current, victory count and mean floor are noninferior, no Current victory becomes a selected loss, at least one pair improves, and improvements are not outnumbered by regressions
- **THEN** the verdict permits a separate simulator policy-bundle proposal

#### Scenario: Any whole-trajectory gate fails
- **WHEN** any fixed gate is unmet
- **THEN** the verdict is no-go for event-ranker integration without rerun or tuning

### Requirement: Reproducible offline evidence
The experiment SHALL bind model, source, native, bridge, fixed seeds, per-pair
traces, metrics, configuration, and manifest identities.

#### Scenario: Terminal report is published
- **WHEN** the paired experiment completes
- **THEN** every manifest artifact matches its recorded identity and downstream authority remains false

### Requirement: Offline isolation
The experiment MUST NOT fit a model, launch gameplay or CommunicationMod, access
a production checkpoint, alter live policy behavior, qualify, or promote.

#### Scenario: Paired execution
- **WHEN** the experiment runs
- **THEN** it writes only its new report directory and uses CPU inference with training disabled
