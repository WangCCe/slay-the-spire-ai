## Context

The active `add-adaptive-elite-routing-baseline` change reached a host qualification with `371`, `2917`, and `3627` passing tests, but its mandatory whole-change review failed. The review found that the adaptive fallback repeats strict whole-map validation before invoking the legacy conservative planner, the full-RL construction path silently ignores an accepted adaptive CLI value, and the structured decision line omits required normalized and fallback evidence.

The original qualification and failed review are immutable evidence. The original delta specification was synchronized into `openspec/specs/adaptive-elite-routing/spec.md` at commit `55b660b70`; this follow-up therefore modifies that existing capability rather than introducing a parallel integration-contract capability. This follow-up must remain smaller than a policy redesign: adaptive risk thresholds and candidate selection are already regression-covered, the intended live agent is `combat_rl`, and persistent gameplay remains conservative until a new qualification and review pass.

## Goals / Non-Goals

**Goals:**

- Recover exactly once through the legacy conservative planner when adaptive candidate production fails but the active origin and committed route history remain usable.
- Preserve strict propagation and no-partial-state behavior for invalid active origins, invalid committed history, invalid fallback output, and unexpected programming errors.
- Make unsupported full-RL/adaptive use fail explicitly rather than silently selecting the learned MAP policy.
- Produce one complete, honest, parseable adaptive decision line for success, forced, unsupported, and candidate-generation fallback outcomes.
- Generate fresh, separately named test and review evidence before unblocking the original change or any live cohort.

**Non-Goals:**

- Changing elite risk thresholds, route weights, candidate count, recovery rules, or legacy conservative/aggressive behavior.
- Delegating full-RL MAP actions to a heuristic agent, extending the RL state/action space, or training/tuning any model.
- Replacing the flat log with JSON or introducing a broad exception hierarchy/reachable-subgraph planner refactor.
- Rerunning the route-candidate latency POC, whose planner algorithm and measured two-pass success path are unchanged.
- Changing combat or other non-combat policy, CLI defaults, persistent Communication Mod configuration, or starting the live cohort in this implementation phase.

## Decisions

### 1. Keep strict adaptive validation, but make the one-shot fallback independent of it

The initial adaptive path continues to validate the complete map and both complete candidate bundles. If that path raises the dedicated adaptive candidate-generation error, the fallback will not repeat whole-map validation. It will instead:

1. Resolve a usable active origin and validate the existing absolute route-history prefix. At an act's initial map choice, an absent/sentinel current node plus advertised `y=0` next nodes is a valid `start_y=0` origin with an empty current-act prefix. A stale complete `map_route` from the previous act is ignored rather than copied or treated as current-act history. An absent current node with nonzero-row next nodes is invalid.
2. Invoke `_build_map_route("conservative")` exactly once from the current origin.
3. Describe and validate that returned route against the active origin, history prefix, map height, coordinates, edges, and completion boundary.
4. Return the validated conservative candidate, derive its route, and commit it with reason `candidate_generation_failed` only after chosen-path logging succeeds.

This permits recovery from an irrelevant malformed earlier/unreachable node that the legacy mid-act planner never visits, and it preserves first-map recovery without inventing a current node or reusing a previous-act prefix. It does not recursively retry. Invalid current-act history, a missing/invalid non-initial origin, an exception from the conservative builder, invalid returned route data, or an unexpected selector/programming error still propagates without route/metadata/log mutation.

Alternatives considered:

- Split every validation failure into new exception subclasses. Clearer long term, but unnecessary for the three reviewed defects and materially larger.
- Validate only the currently reachable subgraph before normal adaptive generation. This changes candidate admission semantics and could hide map corruption on paths the candidates later use.

### 2. Reject full RL plus adaptive instead of pretending to propagate a constructor option

Full RL v1/v2 owns MAP actions through its learned action encoder. Adaptive routing belongs to `SimpleAgent` and its heuristic descendants; merely storing `elite_mode` in an RL constructor would still be a no-op.

`create_agent()` will therefore reject the exact `agent_type="rl"` plus `elite_mode="adaptive"` combination before the RL factory, checkpoint loading, or fallback logic. Direct construction raises `ValueError`; parsed CLI startup calls the parser's error path and exits with status `2`. Both use the exact text:

```text
--elite-route adaptive is unsupported for --agent rl; adaptive routing requires a heuristic map owner
```

The direct and parsed paths share a side-effect-free compatibility validator, while the parser remains responsible for CLI presentation and exit semantics. `simple`, `optimized`, Ironclad `auto`, and `combat_rl` remain supported. Existing full-RL conservative/aggressive behavior remains unchanged because this follow-up does not redefine those legacy combinations.

Alternatives considered:

- Pass and store `elite_mode` in RL constructors. Rejected because it preserves the silent no-op.
- Delegate all full-RL MAP decisions to a heuristic policy. Rejected because that changes RL semantics, action ownership, and training/evaluation behavior.

### 3. Extend the current flat log with explicit outcome and availability

The `[ADAPTIVE_ROUTE]` prefix and single parameterized INFO record remain unchanged. After the prefix, the implementation serializes exactly these ordered, whitespace-delimited `key=value` tokens:

```text
outcome character act floor state_valid hp hp_pct deck potion relic elite_seen last_rest_floor candidate_pair conservative_candidate aggressive_candidate minimum_elites added_elites fallback_candidate budget selected reasons
```

Values never contain whitespace. Booleans are lowercase, unavailable evidence is literally `unavailable`, a valid empty optional value is `none`, reason codes and integer lists use `|`, route symbols use `/`, and `hp_pct` uses exactly six decimal places. Every available candidate summary is derived only from validated candidate features and uses:

```text
mode:<mode>,start_y:<integer>,symbols:<symbol>/<symbol>|none,elite_count:<integer>,elite_floors:<integer>|<integer>|none,recovery_before:<integer|none>,recovery_after:<integer|none>
```

For a complete pair, `minimum_elites` is the conservative elite count and `added_elites` is the aggressive count minus that minimum. Missing pair data is `unavailable`, never a fabricated zero.

- `success` and `forced`: `candidate_pair=complete`, both pair summaries are available, count fields are arithmetic values, and `fallback_candidate=not_used`.
- `unsupported`: `candidate_pair=not_attempted`, pair summaries/counts are unavailable, and `fallback_candidate=not_applicable`.
- `candidate_generation_failed`: `candidate_pair=generation_failed`, pair summaries/counts are unavailable, and `fallback_candidate` contains the one validated conservative candidate returned by the recovery helper.

Normalized policy inputs are emitted only when the adaptive state validator succeeds. Invalid state makes `hp`, `hp_pct`, `deck`, `potion`, `relic`, `elite_seen`, and `last_rest_floor` unavailable; character, act, and floor are normalized independently. Payload preparation and chosen-path logging complete before route/metadata commit; the one summary is emitted only after commit. Candidate, fallback, payload-preparation, or chosen-path errors before commit emit no adaptive decision record and preserve previous route metadata.

Alternatives considered:

- Reconstruct synthetic summaries from committed routes. Rejected because it adds a new post-selection failure path and can overstate unavailable candidate evidence.
- Emit JSON. Better for schema evolution, but wider than the current live-log consumer and review finding require.

### 4. Treat the prior review as a failed qualification and collect fresh evidence

The original PASS gate report and FAIL whole-change review are not edited or reclassified. This follow-up adds red/green regressions, then runs focused routing/main tests and one host-permission sequence of `gameplay`, `commit`, and `full`, stopping at the first nonzero result. Each command's terminal output is preserved in a separately named raw transcript and summarized in a new report. A known stream-silence failure may be diagnosed once for attribution but remains a failed full gate. Any nonzero gate ends this follow-up; code, tests, gate policy, and commands are frozen and no gate is rerun in the same change.

After all gates exit `0`, strict validation covers both active changes, `git diff --check e1a559f37..HEAD` must pass, and a fresh highest-capability read-only review covers that complete range. Any Critical or Important finding ends this follow-up with code, tests, qualification, and review policy frozen; both changes remain blocked and another separately proposed change with fresh evidence is required. Only a clean review may mark the original task `4.4` and authorize the bounded live qualification.

## Risks / Trade-offs

- [Fallback can hide corruption relevant to the active branch] -> Validate the active origin, committed history, and the one returned full conservative route; propagate any failure without recursion.
- [Compatibility rejection surprises full-RL users] -> Reject only the newly advertised adaptive combination with stable text before expensive initialization; preserve legacy combinations.
- [Flat logs remain less structured than JSON] -> Use stable named keys and explicit availability states with exact fixture assertions.
- [Fresh full qualification is slow] -> Continue using focused/gameplay gates during iteration; run host commit/full only once after task reviews are clean and retain raw transcripts.
- [A docs-only mismatch could reopen the original change incorrectly] -> Keep original task `4.4` unchecked until final static checks and the independent whole-range review are preserved.

## Migration Plan

1. Keep the original synchronized main spec at `55b660b70`, then commit and review this follow-up proposal/design/spec/tasks before code changes.
2. Add red regressions for fallback recovery, full-RL compatibility rejection, and each log outcome.
3. Apply the three minimal fixes in cohesive commits with per-task reviews.
4. Run focused tests, then one host gameplay/commit/full sequence with separately named transcripts and report.
5. Run final static validation and an independent whole-range review.
6. On PASS, satisfy the original task `4.4`; only then prepare and run the existing bounded live cohort. Keep the follow-up delta unsynchronized while the original change remains active.
7. After the original live tasks complete and the user explicitly confirms archival, archive the original change with `--skip-specs` because its delta is already in main. This prevents its older delta from overwriting the follow-up semantics.
8. Then synchronize the follow-up delta into the main `adaptive-elite-routing` spec, validate it, and archive the follow-up with `--skip-specs` only after separate explicit user confirmation.

Rollback remains immediate: retain or select conservative routing. No checkpoint, protocol, data-schema, model, or persistent configuration migration is introduced.

## Open Questions

No implementation-blocking question remains. Full-RL adaptive MAP ownership, JSON decision logs, reachable-subgraph validation, and broader exception taxonomy require separate future changes.
