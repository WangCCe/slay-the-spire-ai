# Reachable Event Observation Surface Closeout

Date: 2026-08-03

## Result

The simulator-reachable Ironclad A0 event surface is closed at the registered
source and code-test boundary. The static audit reconciles 51 unique pool
declarations into:

- 2 permanently disabled events;
- 1 direct card-selection transition with no event-option target; and
- 48 reachable event-option targets, partitioned into 25 explicit Current
  rules and 23 audited generic-default events.

The successor resolver now supports all 48 targets. Explicit static, phased,
and dynamic rules retain precedence and their predecessor checks. A registered
generic event requires exact id/name identity plus non-empty, ordered, unique
native candidates; it derives labels from those candidates, assigns contiguous
Current positions, and preserves the exact simulator indices for reverse
mapping. `Scrap Ooze` is covered by this generic path.

This result closes the source-contract mismatch that blocked the consumed API
v3 cohort. It does not establish a new native compatibility result.

## Evidence Identity

- Audit implementation commit: `bcbfbdf706f2c936bca968fa8dc49b92985d6a30`
- Audit publication commit: `a779a447f95e1718461e2c7e5ffd2e4132a027ea`
- Resolver and bridge commit: `53b2c55f79a2cd1d859158a7955ab66d584e6a6d`
- Registration SHA-256:
  `28a3346b16b037dd915d7b1704ae1cb935bc08de6326466416d6833812951a82`
- Audit evidence SHA-256:
  `e395541b98ef904c562b84e40310459ffc5395686ee5f2509a38ff7439eed102`
- Successor contract SHA-256:
  `46a1349443fcec4b224de6b2a5d07a5d5d829ee702a8f549cc3917cf85698d6e`
- Successor partition SHA-256:
  `636f78d26cd5b18649846e244de68925af8952981ecc86c62b6bd34d65f31877`
- Current event-policy AST SHA-256:
  `15fb21a410b5cc7a430b76d46171a2510651e78537aac21fc0e7dc28978bdbd9`
- Preserved predecessor contract SHA-256:
  `785e5db26d4cecaa843c7ee3e9e276fdc98c4b77b6a61e88f4520824a50bf3fc`
- Simulator source SHA-256:
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`

The predecessor resolver and return shape remain available for historical
readers. Frozen bridge v2 registrations require that exact predecessor
identity by schema; new code-level bridge sessions use the reachable-surface
v3 identity. No historical artifact or registration was upgraded in place.

## Verification

- Source-only audit publication and strict no-native recomputation: passed with
  verdict `reachable_event_surface_closed`.
- Focused audit, contract, v2/v3 resolver, bridge, and historical compatibility
  suite: `174 passed in 10.60s`.
- Python compilation for the affected audit, resolver, bridge, compatibility,
  and test modules: passed.
- Repository commit gate: `3475 passed, 11 skipped in 229.74s`; gate total
  `232.48s`.
- Strict global OpenSpec validation before spec sync: `59 passed, 0 failed`.
- Strict global OpenSpec validation after spec sync: `60 passed, 0 failed`.
- Strict global OpenSpec validation after archive: `59 passed, 0 failed`.
- Git diff from the audit publication boundary contains no gameplay policy,
  heuristic, or priority-file change.

The completed OpenSpec change is archived at
`openspec/changes/archive/2026-08-02-close-reachable-event-observation-surface`.

## Preserved Failure

The API v3 compatibility cohort registered at seeds `7000..7007` remains
consumed and failed with `event_option_semantics_event_unsupported: Scrap
Ooze`. It had zero completed seed rows and grants no positive compatibility or
policy-quality evidence. This change does not make that cohort retryable and
does not reinterpret its result.

## Authority Boundary

Gameplay, baseline-floor, target-supported outcome, reward, model, OPE,
formal-RL, training, qualification, loading, and promotion authority all remain
false. No native module was built or loaded, no seed was read, no gameplay was
launched, and no model was fitted during this change.

## Project Direction

The immediate next evidence step is a separate native compatibility change,
not formal non-combat RL training and not another gameplay batch. That change
must bind the pushed v3 resolver and bridge implementation, preregister a new
one-shot cohort of untouched seeds, preserve all-false authority, and fail
closed without retry or threshold tuning.

Only after that independent native compatibility gate passes should the project
reassess the non-combat RL training go/no-go against the remaining requirements:
a credible non-teacher baseline floor, a valid reward contract, and independent
target-supported outcome evidence. Until then, gameplay remains a maintenance
path for crashes, stuck states, or repeated high-confidence mechanics defects.
