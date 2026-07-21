# Adaptive Route Opportunity Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic read-only audit that proves whether adaptive route opportunities became coordinate-level optional-elite treatment in the frozen 2026-07-21 cohort.

**Architecture:** One standard-library analysis module ingests ordered AI logs, a decision trace, and ordered run files. It retains occurrence-level provenance, deduplicates repeated callbacks, joins each occurrence to a frozen map action, reconstructs candidate coordinate paths from the trace map graph, and emits a fail-closed JSON funnel plus a derivative Markdown report.

**Tech Stack:** Python 3.10 standard library, pytest 9.0.2, JSONL, OpenSpec.

## Global Constraints

- Use `D:\anaconda\envs\stsai\python.exe` for tests and the frozen POC.
- Import no gameplay policy, route planner, Communication Mod, torch, or training module from the audit.
- Do not launch the game or modify logs, traces, `.run` files, checkpoints, live configuration, route thresholds, or defaults.
- Require explicit chronological input order, log UTC offset, and bounded join tolerance.
- Treat malformed, missing, tied, contradictory, or ambiguous evidence as invalid or unattributable; preserve a provable common prefix or first divergence without guessing through later ambiguity.
- Write deterministic schema `adaptive-route-opportunity-audit-v1` without wall-clock timestamps or mtimes.
- Use focused pytest plus the repository `commit` gate; do not run the full suite for this isolated analysis-only module.

---

### Task 1: Exact Evidence Parsing And Deduplication

**Files:**
- Create: `tests/test_adaptive_route_opportunity_audit.py`
- Create: `analysis_scripts/adaptive_route_opportunity_audit.py`
- Modify: `openspec/changes/add-adaptive-route-opportunity-audit/tasks.md`

**Interfaces:**
- Produces: `EvidenceError(ValueError)` with source and line context.
- Produces: `Candidate(mode, start_y, symbols, elite_count, elite_floors, recovery_before, recovery_after)`.
- Produces: `AdaptiveOccurrence(game_number, source_path, line_number, timestamp, unix_time, payload, fields, conservative, aggressive)`.
- Produces: `AdaptiveRecord(game_number, payload, occurrences)` keyed by `(game_number, payload)`.
- Produces: `parse_adaptive_payload(payload: str) -> tuple[dict[str, str], Candidate | None, Candidate | None]`.
- Produces: `load_adaptive_logs(paths: Sequence[Path], utc_offset_hours: float) -> tuple[list[AdaptiveOccurrence], list[dict]]`.
- Produces: `deduplicate_occurrences(occurrences) -> list[AdaptiveRecord]`.

- [x] **Step 1: Write failing parser tests**

Create helpers that generate the exact ordered payload and timestamped log lines. Assert that valid records preserve all fields and candidate values; two identical payloads in one game collapse to one record with two occurrences; the same payload in another game remains separate; reordered, extra, malformed candidate, missing game-boundary, and non-monotonic boundary inputs raise or produce integrity diagnostics.

Use this exact candidate API in assertions:

```python
fields, conservative, aggressive = audit.parse_adaptive_payload(payload)
assert fields["candidate_pair"] == "complete"
assert conservative == audit.Candidate(
    mode="conservative",
    start_y=7,
    symbols=("M", "T", "?", "$", "R", "?", "M", "R"),
    elite_count=0,
    elite_floors=(),
    recovery_before=None,
    recovery_after=None,
)
assert aggressive.elite_floors == (14,)
```

- [x] **Step 2: Run parser tests and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_adaptive_route_audit_red1 tests/test_adaptive_route_opportunity_audit.py
```

Expected: collection fails because `analysis_scripts.adaptive_route_opportunity_audit` does not exist.

- [x] **Step 3: Implement exact parsing and source identities**

Define the exact key contract and parse with strict positional checks:

```python
ADAPTIVE_KEYS = (
    "outcome", "character", "act", "floor", "state_valid", "hp", "hp_pct",
    "deck", "potion", "relic", "elite_seen", "last_rest_floor",
    "candidate_pair", "conservative_candidate", "aggressive_candidate",
    "minimum_elites", "added_elites", "fallback_candidate", "budget",
    "selected", "reasons",
)

def parse_adaptive_payload(payload: str):
    tokens = payload.split()
    keys = tuple(token.partition("=")[0] for token in tokens)
    if keys != ADAPTIVE_KEYS or any("=" not in token for token in tokens):
        raise EvidenceError("adaptive payload keys do not match the ordered contract")
    fields = dict(token.split("=", 1) for token in tokens)
    return fields, _parse_candidate(fields["conservative_candidate"]), _parse_candidate(fields["aggressive_candidate"])
```

Convert local timestamps to Unix seconds using the explicit fixed offset, assign the active game number from `Starting game #N`, attach file/line provenance, and compute SHA-256, byte count, and line count from raw source bytes.

- [x] **Step 4: Run parser tests and verify GREEN**

Run the focused file command from Step 2 with basetemp `.pytest_adaptive_route_audit_green1`. Expected: all parser tests pass.

- [x] **Step 5: Mark OpenSpec parsing tasks complete**

Change tasks `1.1` and `1.2` to `[x]` only after the red and green outputs have both been observed.

### Task 2: Decision Trace Join And Candidate Coordinates

**Files:**
- Modify: `tests/test_adaptive_route_opportunity_audit.py`
- Modify: `analysis_scripts/adaptive_route_opportunity_audit.py`
- Modify: `openspec/changes/add-adaptive-route-opportunity-audit/tasks.md`

**Interfaces:**
- Produces: `TraceMapDecision(unix_time, act, floor, current_node, next_nodes, graph, paths, action_node, semantic_fingerprint)`.
- Produces: `load_decision_trace(path: Path) -> tuple[list[TraceMapDecision], dict]`.
- Produces: `join_occurrences(records, trace_rows, max_join_seconds) -> list[JoinedRecord]`.
- Produces: `matching_candidate_paths(candidate: Candidate, decision: TraceMapDecision) -> tuple[tuple[Coordinate, ...], ...]`.
- Produces: `classify_candidate_pair(joined_record) -> CandidatePairEvidence` using per-index coordinate sets across all matching paths.

- [x] **Step 1: Add failing trace and graph tests**

Build a seven-column synthetic map as plain JSON dictionaries. Cover unique nearest joins, missing/tied/out-of-tolerance joins, duplicate occurrences with equal and unequal semantic fingerprints, invalid actions, one unique path per candidate, multiple symbol-identical paths, a shared immediate coordinate with a later divergence, and different immediate coordinates.

Assert the core result shape:

```python
evidence = audit.classify_candidate_pair(joined)
assert evidence.immediate_classification == "same"
assert evidence.conservative_path[0] == (2, 7)
assert evidence.aggressive_path[0] == (2, 7)
assert evidence.first_divergence == audit.Divergence(
    index=5,
    map_y=12,
    entered_floor=13,
    conservative=(1, 12),
    aggressive=(0, 12),
)
```

- [x] **Step 2: Run new tests and verify RED**

Run the focused file with basetemp `.pytest_adaptive_route_audit_red2`. Expected: failures identify the missing trace/join/graph functions, while Task 1 tests remain green.

- [x] **Step 3: Implement bounded joins and graph enumeration**

Parse every non-empty JSONL row, retain map rows, and reject malformed JSON. For each occurrence, filter by `act`, `floor`, and absolute timestamp delta, then require one nearest row and no equal-distance tie. Build a `(x, y) -> node` graph, validate children advance exactly one row, and enumerate exact symbol paths recursively:

```python
def walk(coordinate, symbol_index, coordinates):
    node = graph[coordinate]
    if node["symbol"] != candidate.symbols[symbol_index]:
        return
    next_coordinates = coordinates + (coordinate,)
    if symbol_index == len(candidate.symbols) - 1:
        matches.append(next_coordinates)
        return
    for child in node["children"]:
        walk((child["x"], child["y"]), symbol_index + 1, next_coordinates)
```

Start only from current-node children advertised in `next_nodes`. Report a unique full path only for one match; report an immediate coordinate when all matches share one first coordinate. At each index, compute the coordinate set across all matching paths. Report a provable first divergence when all earlier sets are the same singleton and the current sets are different singletons; preserve any ambiguity after that point.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the focused file with basetemp `.pytest_adaptive_route_audit_green2`. Expected: all Task 1 and Task 2 tests pass.

- [x] **Step 5: Mark OpenSpec correlation tasks complete**

Change tasks `2.1` and `2.2` to `[x]` only after the red and green outputs have both been observed.

### Task 3: Treatment Funnel, Run Corroboration, And CLI

**Files:**
- Modify: `tests/test_adaptive_route_opportunity_audit.py`
- Modify: `analysis_scripts/adaptive_route_opportunity_audit.py`
- Modify: `openspec/changes/add-adaptive-route-opportunity-audit/tasks.md`

**Interfaces:**
- Produces: `load_runs(paths: Sequence[Path]) -> tuple[list[RunEvidence], list[dict]]`, preserving canonical post-boss `null` transition slots as `None`.
- Produces: `build_audit(ai_logs, decision_trace, runs, utc_offset_hours, max_join_seconds) -> tuple[dict, int]`.
- Produces: `serialize_audit(result: dict) -> bytes` using sorted keys and a final newline.
- Produces CLI options `--ai-log` (repeatable), `--decision-trace`, `--run` (repeatable), `--log-utc-offset-hours`, `--max-join-seconds`, and `--output`.

- [x] **Step 1: Add failing attribution and CLI tests**

Construct two-game synthetic evidence and cover:

- aggressive selection with the same immediate coordinate followed by conservative revocation;
- actual route departure before divergence;
- immediate divergence taken;
- divergence followed by entry to the extra elite with matching `path_per_floor`;
- trace `?` with a resolved non-boss run symbol remaining compatible but never counting as elite;
- run-symbol mismatch causing invalid integrity;
- ambiguous candidate paths excluded from uptake;
- stable JSON bytes across two builds;
- CLI exit `0` for valid evidence and nonzero with written diagnostics for invalid evidence.

Use exact funnel assertions:

```python
assert result["funnel"] == {
    "adaptive_occurrences": 4,
    "callback_independent_records": 2,
    "candidate_generation_fallbacks": 0,
    "complete_candidate_pairs": 2,
    "zero_vs_one_opportunities": 2,
    "act1_zero_vs_one_opportunities": 2,
    "aggressive_selections": 1,
    "same_immediate_coordinate": 1,
    "different_immediate_coordinate": 0,
    "ambiguous_immediate_coordinate": 0,
    "provable_first_divergences": 1,
    "selection_revoked_before_divergence": 1,
    "route_left_before_divergence": 0,
    "divergences_taken": 0,
    "realized_optional_elites": 0,
}
```

- [x] **Step 2: Run new tests and verify RED**

Run the focused file with basetemp `.pytest_adaptive_route_audit_red3`. Expected: only the new attribution/output tests fail.

- [x] **Step 3: Implement the fail-closed audit and deterministic CLI**

Map game number `N` to the `N`th ordered run. Corroborate each joined action at `path_per_floor[decision.floor]`: decision `floor` is the global zero-based index of the room being entered, while action-node `y` and candidate `elite_floors` are Act-local coordinates. Preserve `None` only when it immediately follows `B`; treat it as an inter-act transition slot and reject any joined map action that targets it. Require exact symbols for non-event trace nodes. Preserve trace `?` plus a valid resolved non-boss run symbol as `event_resolved` compatibility without changing the candidate symbol. For aggressive zero-versus-one opportunities, walk later joined map records in the same game, preserve the first policy revocation and route departure, and count divergence uptake only when the actual actions remain compatible with an aggressive path through a provable first divergence. Count elite uptake only when later actions remain compatible, enter a uniquely attributable extra elite coordinate, and have exact trace `E` plus run `E` at the same global floor.

Construct output in this top-level shape:

```python
result = {
    "schema_version": "adaptive-route-opportunity-audit-v1",
    "parameters": {
        "log_utc_offset_hours": utc_offset_hours,
        "max_join_seconds": max_join_seconds,
    },
    "sources": sources,
    "integrity": {"status": status, "diagnostics": diagnostics},
    "deduplication": deduplication,
    "funnel": funnel,
    "runs": run_summaries,
    "fallbacks": fallback_evidence,
    "opportunities": opportunities,
}
```

Serialize with `json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n"`. Always write an artifact when argument parsing succeeds; return `0` only for valid integrity and `2` otherwise.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the focused file with basetemp `.pytest_adaptive_route_audit_green3`. Expected: the complete focused file passes with no warnings.

- [x] **Step 5: Mark OpenSpec attribution tasks complete**

Change tasks `3.1` and `3.2` to `[x]` after observing RED and GREEN.

- [x] **Step 6: Preserve canonical run transition slots**

Add a failing regression for a valid `B, null, M` run path, plus invalid-placement and action-targeted-null cases. Update `RunEvidence.path_per_floor` to preserve `None`, accept it only immediately after `B`, keep it in deterministic JSON, and fail closed if a joined map action targets it. Mark OpenSpec task `3.3` complete only after focused RED and GREEN evidence and an independent task review.

- [x] **Step 7: Preserve candidate-generation fallback provenance**

Add a failing regression requiring one deterministic `fallbacks` entry per callback-independent `candidate_generation_failed` record. Preserve a stable ordinal, game number, complete payload, multiplicity, every occurrence's source path/line/timestamp/join delta, joined decision summary, and run corroboration. Require `len(fallbacks) == funnel.candidate_generation_fallbacks` and mark OpenSpec task `3.4` complete only after focused RED/GREEN evidence and independent review.

### Task 4: Frozen Cohort POC And Report

**Files:**
- Create: `reports/adaptive_route_opportunity_audit_20260722.json`
- Create: `reports/adaptive_route_opportunity_audit_20260722.md`
- Modify: `openspec/changes/add-adaptive-route-opportunity-audit/tasks.md`

- [x] **Step 1: Preserve execution lineage and run the final audit without launching the game**

Run the CLI with these ordered sources:

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\adaptive_route_opportunity_audit.py --ai-log D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log.1 --ai-log D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log --decision-trace D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_adaptive_20260721.jsonl --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650652.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650754.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650802.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650867.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650965.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651020.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651097.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651170.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651250.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651443.run --log-utc-offset-hours 8 --max-join-seconds 0.01 --output reports\adaptive_route_opportunity_audit_20260722.json
```

Expected final invocation: exit `0`, integrity valid, no game process launched. Preserve the earlier fail-closed artifact identity and diagnostic, reviewed transition-slot fix, and superseding artifact identity in the durable Markdown; do not imply that only one analysis invocation occurred.

- [x] **Step 2: Verify registered evidence checks**

Read the JSON and assert source hashes plus `346` raw occurrences, `173` unique records, multiplicity distribution `{2: 173}`, `58` zero-versus-one opportunities, `54` in Act 1, one aggressive selection, four separately auditable callback-independent candidate-generation fallbacks with total multiplicity eight, same immediate coordinate, revocation before divergence, and zero realized optional elites.

- [x] **Step 3: Write the derivative report**

Document the exact command, failed-then-resumed analysis lineage, hashes, integrity checks, opportunity funnel, sole aggressive case, candidate-generation fallbacks, limitations, and decision: keep conservative, do not tune or rerun this cohort, and treat a later oracle/value study as a separate change. Label pre/post hashes and game-process counts as operator-observed controls unless they are explicit fields in the final JSON.

- [x] **Step 4: Mark OpenSpec POC tasks complete**

Change tasks `4.1` through `4.3` to `[x]` only when artifacts and checks agree.

### Task 5: Verification, Review, And Commit

**Files:**
- Modify: `reports/adaptive_route_opportunity_audit_20260722.md`
- Modify: `openspec/changes/add-adaptive-route-opportunity-audit/tasks.md`

- [ ] **Step 1: Run focused verification**

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_adaptive_route_audit_final tests/test_adaptive_route_opportunity_audit.py
```

Record test count, duration, and exit code in the report.

- [ ] **Step 2: Run the commit gate**

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
```

Record the gate's resolved pytest command, test count, duration, and exit code. Stop on nonzero.

- [ ] **Step 3: Validate planning and diff boundaries**

```powershell
openspec validate add-adaptive-route-opportunity-audit --strict
git diff --check
git diff --name-only
```

Expected: strict validation passes, whitespace check is clean, and changed implementation paths are limited to `analysis_scripts/`, `tests/`, `reports/`, `openspec/changes/add-adaptive-route-opportunity-audit/`, and this plan.

- [ ] **Step 4: Run independent local review**

Review all tracked changes for correctness, evidence overclaiming, unsafe source writes, nondeterminism, and missing tests. Resolve every Critical or Important finding before completion.

- [ ] **Step 5: Mark verification tasks and commit**

Update tasks `5.1` through `5.4`, stage only the named files, and commit:

```powershell
git commit -m "analysis: audit adaptive route treatment uptake"
```

Then mark task `5.5` complete in a small follow-up task-ledger commit if required by the repository's established OpenSpec bookkeeping pattern.

## Self-Review

- Spec coverage: every ingestion, deduplication, join, coordinate, attribution, POC, and verification scenario maps to Tasks 1 through 5.
- Placeholder scan: no `TBD`, `TODO`, deferred implementation, or unspecified error handling remains.
- Type consistency: candidate, occurrence, record, trace, divergence, run, and top-level artifact names are consistent across tasks.

## Execution Mode

The user already approved this exact audit and authorized continued execution while away. Execute inline in the current task with `superpowers:executing-plans`, preserving the red-green checkpoints above.
