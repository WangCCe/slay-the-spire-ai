## Context

The bounded adaptive qualification retained two chronologically ordered AI log segments, one decision trace, and ten ordered Ironclad run records. Manual postmortem work found that 346 structured route rows collapse to 173 callback-independent states and that the sole aggressive selection chose the same immediate map coordinate as the conservative candidate before later replanning revoked it. The existing evidence is sufficient for an offline audit but not for threshold tuning or another live cohort.

The AI log records policy inputs, candidate symbol routes, selection, and reasons. The decision trace records timestamps, current and next map coordinates, the full map graph, enumerated path prefixes, and the actual `ChooseMapNodeAction`. The `.run` files record resolved room symbols and outcomes. They also use `null` immediately after a `B` entry as an inter-act transition slot; this is structural evidence, not a room. In particular, a trace `?` map choice can resolve to `M`, `$`, or `T` in `path_per_floor`; this is compatible event-resolution evidence, not source corruption and not an elite. No one source alone can establish treatment uptake.

## Goals / Non-Goals

**Goals:**

- Deterministically ingest and identify the frozen evidence without modifying it.
- Collapse repeated callbacks while preserving every source occurrence and its joined action.
- Reconstruct candidate coordinate routes from candidate symbols and the decision-trace map graph without guessing through ambiguity.
- Separate opportunity, policy selection, immediate action difference, survival to route divergence, and realized optional-elite exposure.
- Emit a machine-readable integrity-qualified artifact and a concise POC report.

**Non-Goals:**

- Changing route thresholds, candidate generation, defaults, gameplay behavior, training, checkpoints, protocol handling, or live configuration.
- Replaying or rerunning the qualification cohort.
- Estimating causal reward, survival value, or a replacement policy for denied opportunities.
- Treating symbol-only or ambiguous route matches as coordinate-level evidence.

## Decisions

### Join all three evidence surfaces

The audit will consume ordered `--ai-log` paths, one `--decision-trace`, ordered `--run` paths, an explicit `--log-utc-offset-hours`, a bounded `--max-join-seconds`, and `--output`. It will stream/read sources without writing beside them and will record SHA-256, byte count, line count, and record count in the output.

Alternative: count `[ADAPTIVE_ROUTE]` rows alone. Rejected because a selected candidate can share the immediate action with the conservative candidate and later be revoked.

Alternative: rerun route generation against historical state. Rejected because it couples the audit to current gameplay code and can silently reinterpret frozen evidence after policy changes.

### Preserve occurrence evidence before semantic deduplication

Each AI log line will be assigned to the active `Starting game #N` boundary and parsed using the exact ordered adaptive-route key schema. The callback-independent key is `(game_number, complete_payload)`. Every source occurrence remains attached to that record with file, line, timestamp, and joined decision-trace row.

Each occurrence joins to the unique nearest map decision row with matching act and floor inside the configured tolerance. A tie, missing row, malformed line, out-of-order game boundary, or semantic disagreement among duplicate occurrences makes the audit integrity status invalid instead of selecting a convenient match.

Alternative: deduplicate before joining. Rejected because it would hide whether repeated callbacks committed the same action evidence.

### Reconstruct coordinates from the frozen map graph

For a complete candidate, the audit will enumerate graph paths beginning at `start_y` whose symbols exactly equal the recorded candidate symbol sequence. It will validate graph coordinates, child edges, current-node reachability, candidate elite floors, and actual action membership in `next_nodes`.

A candidate is fully coordinate-resolved only when it has exactly one matching full coordinate path. Immediate actions can additionally be classified when all matching paths share one first coordinate. A first divergence is provable without unique full paths when, at every earlier index, both candidates' matching-path coordinate sets are the same singleton and, at the divergence index, both sets are different singletons. Later branch ambiguity remains explicit and does not erase an earlier provable divergence. No planner call or source-code route generation is allowed.

Alternative: infer coordinates from symbols or path prefixes. Rejected because duplicate symbols on different branches are common and would overstate treatment.

### Define treatment as realized coordinate-level commitment

The funnel will report complete pairs, zero-versus-one opportunities, Act 1 opportunities, aggressive selections, immediate same/different/ambiguous coordinates, uniquely resolved first divergences, selections revoked before divergence, routes left before divergence, divergences actually taken, and optional elites actually reached.

An aggressive selection survives to divergence only when the first divergence is provable, later policy records remain aggressive as required, and joined actions remain compatible with at least one original aggressive coordinate path through the first differing coordinate. A realized optional elite additionally requires that the post-divergence joined actions remain compatible with an aggressive path, enter a uniquely attributable extra elite coordinate, and have an exact `E` in `.run.path_per_floor` at that global floor. A trace `?` followed by any resolved run-room symbol remains event evidence and SHALL NOT be reinterpreted as an elite. Ambiguous, same-immediate, revoked, or route-departed cases do not count as realized treatment.

### Emit deterministic JSON and a derivative report

The JSON schema will be `adaptive-route-opportunity-audit-v1` and will contain source identities, integrity diagnostics, deduplication metrics, run summaries, funnel counts, per-fallback provenance, and per-opportunity evidence. Each callback-independent candidate-generation fallback will retain a stable ordinal, game number, complete payload, multiplicity, occurrence provenance, joined decision summary, and run corroboration so its aggregate count can be audited independently. With identical source bytes and CLI parameters, the JSON bytes will be stable; wall-clock generation timestamps and source mtimes are excluded.

The Markdown POC report is a human-readable derivative of the JSON and records the exact command, source hashes, expected cohort checks, limitations, and stop decision. If an earlier invocation failed and its artifact was superseded after a reviewed analysis fix, the report preserves that execution lineage and distinguishes JSON-backed fields from operator-observed controls such as pre/post hashes or process counts. The implementation remains one focused analysis module plus one focused test module.

## Risks / Trade-offs

- [Candidate symbols match multiple graph paths] -> Preserve all matches, mark coordinate attribution ambiguous, and exclude the case from treatment counts.
- [Local log timestamps lack an offset] -> Require the caller to supply the offset and record it in the artifact.
- [Nearest-time correlation joins the wrong repeated callback] -> Match act and floor, enforce a small explicit tolerance, retain occurrence-level joins, and require duplicate semantic agreement.
- [Run files lack coordinates, resolve event symbols, and contain inter-act null slots] -> Use decision trace for coordinates, preserve only `null` entries that immediately follow `B` as structural transition slots, reject any joined map action that targets a null slot, treat trace `?` plus a valid non-boss run-room symbol as an explicit event-resolution compatibility class, require exact symbols for non-event nodes, and require exact `E`/`E` agreement for optional-elite corroboration.
- [Frozen evidence cannot estimate counterfactual value] -> Limit the report to opportunity and uptake; require a separate proposal for oracle comparison or policy changes.
- [Strict integrity checks produce no authoritative report] -> Still emit diagnostics with `integrity.status=invalid`, return nonzero, and make no gameplay recommendation.

## Migration Plan

1. Add the offline script and focused tests using synthetic evidence.
2. Run it only against the already retained cohort; preserve any failed-then-resumed analysis lineage and do not launch the game.
3. Preserve the JSON and Markdown reports in the repository.
4. Verify focused tests, the commit gate, strict OpenSpec validation, and a gameplay-source diff check.

Rollback is deletion or reversion of the analysis-only files. The live conservative configuration is never changed.

## Open Questions

None for this change. Counterfactual outcome scoring and any future treatment-uptake threshold belong in a later, separately approved OpenSpec change.
