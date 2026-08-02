## Context

The preserved train corpus contains 1,291 SimpleAgent-labelled decisions from
seeds `4000..4031`; 870 have multiple candidates. The structured ranker and the
terminal route/card residual both failed their preregistered held-out gates.
Those results establish that another fit on the same corpus is unjustified, but
they do not establish why imitation stalls near the existing baseline.

The authoritative teacher implementation is the local
`D:\CLionProjects\sts_lightspeed` checkout. Initial source tracing shows two
important facts. Route decisions use fixed act-specific room weights and a
`SimpleAgent.mapPath` cached at map entry. Card-reward decisions use candidate
card identity, upgrade status, static priority/copy tables, and reward order;
the apparent copy-count guard counts cards in the offer rather than cards in
`gc.deck`. The adapter exposes the full map, run state, reward candidates, and
action ids, while the learned projections transform those fields differently.

The audit must distinguish four layers: source policy dependencies, raw adapter
observability, exact model input projections, and whether SimpleAgent labels are
appropriate evidence of policy quality. The external checkout currently has
unrelated local changes, so git cleanliness cannot be treated as source
identity; exact file hashes and relevant-file diffs are required instead.

## Goals / Non-Goals

**Goals:**

- Reconstruct every preserved route/card teacher action from hash-bound C++
  source semantics and the recorded adapter row, including ordering and ties.
- Classify each teacher dependency as directly represented, deterministically
  derivable on a baseline-following trajectory, policy constant, intentionally
  irrelevant, or missing in raw, legacy, and structured representations.
- Quantify decision aliases, candidate-vector aliases, semantically equivalent
  actions, and contradictory pairwise preferences without fitting a model.
- Apply one preregistered verdict that selects only the next proposal class:
  adapter representation repair, retirement/reframing of SimpleAgent imitation,
  or an inconclusive stop.
- Publish deterministic, hash-closed evidence that a strict validator can
  recompute from the registered inputs.

**Non-Goals:**

- No native module import, simulator build or rollout, new seed, validation or
  final cohort, model construction, gradient, optimizer, hyperparameter search,
  reward estimate, gameplay launch, DAgger, formal RL, qualification, policy
  loading, or promotion.
- No edit to `sts_lightspeed`, the native adapter, existing projections,
  production agent behavior, or prior POC artifacts.
- No claim that deterministic teacher reproducibility implies policy quality,
  and no use of SimpleAgent agreement as a proxy for victory or return.

## Decisions

### 1. Bind physical source and preserved corpus identities

One immutable registration will bind the train gzip and manifest, the terminal
residual result as lineage only, the exact implementation commit, runtime, and
the relevant C++/Python source files by path, size, and SHA-256. It will record
the external checkout commit and relevant-file tracked status separately from
unrelated checkout dirtiness. The runner will reject any identity mismatch,
non-train cohort, row outside `4000..4031`, or category outside route/card.

The external repository is source evidence only. No compiler, CMake, Python
extension, or native API is invoked. Binding physical files is preferred over
requiring a clean checkout because the current unrelated CMake/submodule edits
do not alter the audited SimpleAgent source.

### 2. Extract constants and reproduce the teacher from source semantics

The audit will brace-extract and anchor-check the route and card-reward source
blocks plus `mapWeights`, `cardsPriorities`, and `maxCopies`. A deterministic
Python reference evaluator will implement the observed C++ ordering exactly:

- route: initialize seven start paths, perform the fourteen-layer dynamic
  program with strict comparisons and source iteration order, append the boss
  coordinate, and select `mapPath[curMapNodeY + 1]` using the act table;
- card reward: count ids in the last offered reward, apply the parsed copy table,
  score with the parsed priority table and upgrade adjustment, preserve first
  minimum tie behavior, and map the skip bits to the sole adapter skip/bowl
  candidate.

Every route/card row must reproduce the recorded teacher action exactly. This
is a dependency-closure test, not a replacement policy. A mismatch blocks the
audit because it means the static trace or adapter mapping is incomplete.

### 3. Audit four fixed representation signatures

For every multi-candidate route/card row, the audit will materialize these
ordered decision signatures before inspecting collision results:

1. `teacher-source-v1`: only the parsed source dependencies and policy
   constants needed by the reference evaluator;
2. `adapter-observable-v1`: canonical raw state and candidates after removing
   only registered leakage fields (`seed`, `outcome`, provenance, terminal, and
   baseline history/control);
3. `legacy-hash-1024-v1`: the exact float32 vectors consumed by the legacy
   1,024-dimensional hashed candidate scorer;
4. `structured-hash-2048-v1`: the exact float32 vectors consumed by the
   structured candidate scorer.

Each signature reports unique and repeated decision groups, groups with
conflicting target positions, candidate-vector equivalence classes, rows whose
target is indistinguishable from a non-target, and directed pairwise preference
contradictions. Float vectors are signed-byte hashed from their exact CPU
float32 bytes; no tolerance, rounding, bin search, or result-dependent key is
allowed.

The audit also computes a fixed semantic action key. Route semantics are
`(x, y)`. Card take semantics are `(kind, id, upgraded, upgrade_count, misc)`;
skip and bowl remain distinct kinds. Raw action-id disagreement between
semantically identical duplicate cards is reported separately and does not by
itself count as missing state.

### 4. Separate adapter sufficiency from model and teacher limitations

An actionable adapter gap exists only if a required source dependency is
neither present nor deterministically derivable for the registered
baseline-following corpus, or an adapter decision signature has conflicting
non-equivalent semantic targets. Failure of the source-faithful evaluator or
failure to map a recorded teacher action exactly once blocks the audit because
source closure has not been established. Hash collisions or pairwise
contradictions that appear only after the legacy or structured projections are
projection/model limitations, not adapter gaps.

Teacher suitability for a policy-quality gate is evaluated against fixed
critical checks. Route fails if it freezes the map-entry plan and does not read
current survivability or run resources at later choices. Card reward fails if
copy limits do not read the actual deck, or if card choice ignores deck/run
context and skip-versus-bowl utility. These checks concern expert quality, not
determinism; the source dependency matrix must contain direct evidence for each
result.

### 5. Apply one no-retry verdict

The terminal classifier is ordered:

1. identity, schema, source extraction, reproduction, metric, resource, or
   inventory failure -> `blocked`;
2. any actionable adapter gap -> `adapter_representation_repair_required`;
3. no adapter gap and any critical teacher-suitability failure ->
   `simpleagent_unsuitable_as_policy_quality_gate`;
4. otherwise -> `audit_inconclusive`.

The expected follow-up for the third verdict is to retain SimpleAgent only as a
deterministic adapter/regression oracle, retire its held-out agreement as a
policy-improvement gate, and create a separate outcome-backed non-combat RL
readiness proposal. No result authorizes implementation of that follow-up in
this change, and there is no alternate key, threshold, source interpretation,
or rerun after publication.

### 6. Publish canonical evidence plus strict recomputation

The canonical output contains configuration, extracted source facts,
dependency coverage, row-level reproduction/alias evidence, aggregate metrics,
teacher suitability, verdict report, Markdown summary, and an exact inventory
manifest. One noncanonical timing journal may record elapsed time. A standalone
validator will reload the registration and corpus, recompute every canonical
artifact in memory, compare exact bytes, verify all-false authority, and reject
extra managed files. The run is bounded to 1,500 rows, 32 candidates per row,
120 seconds, and zero model fits/native calls.

## Risks / Trade-offs

- **Static C++ parsing can drift** -> Bind exact files, use narrow brace/array
  extractors, test malformed anchors, and block instead of guessing.
- **The corpus may have few repeated exact decisions** -> Treat zero collisions
  as limited coverage, not proof of broad sufficiency; exact teacher
  reproduction and source dependency coverage remain the primary adapter test.
- **A deterministic heuristic can be reproduced perfectly while being weak** ->
  Keep teacher suitability and imitation fidelity as separate report sections
  and forbid policy-quality authority.
- **Hash-vector diagnostics depend on PyTorch serialization details** -> Bind
  Python/Torch versions and hash explicit contiguous CPU float32 bytes only.
- **The external checkout is dirty outside audited files** -> Record checkout
  status, require audited tracked files to match their bound hashes, and never
  modify or clean that checkout.

## Migration Plan

1. Add source extractors, reference evaluators, representation signatures,
   metrics, verdict logic, and synthetic regressions.
2. Run focused tests, Python compilation, the registered pytest commit gate,
   and strict OpenSpec validation; then commit the implementation.
3. Check in one immutable registration binding that implementation and all
   source/corpus identities, verify it, and execute the audit once.
4. Strictly recompute the artifact set, perform a read-only manual source audit,
   publish the result, and update project direction.
5. Sync and archive the change, run bounded final verification, commit only
   scoped files, and push `master`.

Rollback deletes only this audit's code, tests, registration, result, and spec
artifacts. It leaves all source evidence, prior POCs, runtime configuration,
checkpoints, and gameplay behavior unchanged.

## Open Questions

None. Inputs, signatures, source interpretation, critical suitability checks,
verdict order, bounds, and no-retry behavior are fixed before corpus analysis.
