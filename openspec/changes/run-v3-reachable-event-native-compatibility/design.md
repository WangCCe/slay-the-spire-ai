## Context

The predecessor API v3 compatibility runner bound the 25-event observation
identity and consumed seeds `7000..7007` before failing on `Scrap Ooze`. The
subsequent source audit proved 51 pool events partitioned into 2 disabled, 1
direct transition, and 48 event-option targets, and the reachable-surface v3
resolver now covers the 25 explicit and 23 generic targets under exact Current
AST and simulator provenance.

That source/code closure is not native compatibility evidence. A successor run
must be independent of the old registration, use untouched seeds, bind the new
resolver identity, and preserve a failure without repair or retry. The work is
offline development tooling only; Communication Mod and production gameplay
remain untouched.

## Goals / Non-Goals

**Goals:**

- Prove or fail closed on native own-trajectory structural compatibility for
  the pushed reachable-surface v3 resolver and bridge.
- Establish conservative, reviewable seed isolation before fixing the cohort.
- Persist whole-cohort consumption before the first environment and publish a
  no-native-verifiable canonical result after exactly one execution attempt.
- Preserve the predecessor evaluator, registration, artifacts, failure, and
  seed status as immutable historical evidence.

**Non-Goals:**

- Measuring policy quality, a baseline floor, victory rate, reward validity,
  OPE, formal RL readiness, or promotion value.
- Changing Current policy, event choices, simulator behavior, adapter API,
  Communication Mod configuration, or gameplay code.
- Retrying `7000..7007`, selecting seeds from observed outcomes, widening a
  failed cohort, changing thresholds after execution, or fitting any model.

## Decisions

### Use a new successor evaluator and evidence namespace

The implementation will add a new evaluator, input schema, seed ledger,
registration path, output directory, and artifact schemas. It may reuse stable
adapter, bridge, hashing, and validation primitives, but it will not change the
predecessor cohort's registration, output, or execution state. The successor
registration will bind the predecessor closeout and manifest as negative
history, not as execution authority.

Alternative considered: update the predecessor runner and replace its cohort.
Rejected because its whole cohort was atomically consumed and its first blocker
is a valid immutable negative.

### Inventory tracked seed declarations before naming the cohort

A source-only inventory will enumerate tracked repository registrations and
seed ledgers and collect every integer under a seed-bearing JSON path. Each
source path, JSON path, value, and inferred role will be retained in a canonical
inventory. Candidate seeds must be absent from every consumed, selected,
reserved, train, validation, compatibility, smoke, qualification, and
final-test declaration. Ambiguous seed-bearing paths are excluded
conservatively rather than ignored.

Only after the inventory implementation and tests are pushed will the exact
sorted cohort be written into an immutable seed ledger and registration. The
cohort will contain eight seeds, two replays per seed, a 500-target-decision
limit per replay, and a 120-second whole-run bound. There is no CLI override.

Alternative considered: assume `7100..7107` is untouched because the failed
cohort ended at 7007. Rejected until the repository-wide inventory proves it.

### Separate build identity collection from environment construction

After the evaluator implementation is pushed, an existing API v3 module may be
loaded only to verify its API and build-info identity. If no exact module is
available, the adapter may be built in an ignored out-of-tree directory and
loaded for identity collection. This phase must not call `Environment`, read a
native seed, or create the canonical output directory.

The registration will bind module bytes and size, build fields, adapter sources,
simulator commit/dirty/source digest and count, submodules, reachable resolver
identity and contract, bridge/Current implementation, metadata, runtime, seed
ledger, limits, predecessor evidence, output names, and all-false authority.

### Require a pushed preregistration before the one-shot journal

Execution will assert a tracked-clean tree, exact registration and seed-ledger
bytes at `HEAD`, and `HEAD == origin/master`. It will validate every bound
identity before atomically writing a started journal that marks the entire
cohort consumed. Only then may it construct the first native environment.

Any blocker, timeout, exception, partial result, or interruption after journal
start consumes the cohort. The evaluator records the first blocker and does not
substitute a seed, rerun an environment, or alter a limit.

### Keep the verdict structural and diagnostics dual-coordinate

Every replay must use a fresh environment and Current session, select only a
reported legal action, preserve source bytes, avoid fallback/tracker activity,
reach a valid terminal state, and reproduce identical canonical trajectory
bytes. Event rows must report the reachable v3 semantic source, upstream and
Current ids, event data, Current position, simulator index, and selected action
id. Aggregate route, shop, event, and card-reward counts must all be nonzero.

Terminal floor and outcome are retained only as diagnostics. A pass permits
consideration of a separate baseline-floor study; it does not authorize one or
authorize RL training.

### Publish once and verify without native loading

Handled pass or failure results produce canonical configuration, execution
journal, trajectory rows or failure payload, metrics, report, and manifest.
The verifier recomputes deterministic bytes from the pushed registration,
ledger, and preserved execution result without importing or loading a native
module. Unexpected process termination leaves the started journal as a
consumed negative requiring read-only closeout.

## Risks / Trade-offs

- [Seed inventory misses an unusual registration shape] -> Treat every
  seed-bearing tracked JSON path as excluded unless a tested schema classifies
  it more precisely; publish the full source/path inventory.
- [Conservative inventory excludes harmless integers] -> Accept false-positive
  exclusions because the seed space is large and isolation is more important
  than choosing nearby values.
- [An existing module is stale] -> Reproduce module, build, adapter, simulator,
  and dependency identities before registration; build a new ignored artifact
  only if needed and never construct an environment during discovery.
- [The cohort fails on another structural edge] -> Preserve the first blocker
  and stop. A later fix requires a separate source audit/change and a different
  untouched cohort.
- [A pass is mistaken for policy quality] -> Keep every downstream authority
  false in registration, execution, metrics, manifest, report, and closeout.
- [Historical evidence changes] -> New paths and schemas only; regression-test
  predecessor bytes, consumed journal, and failure identity.

## Migration Plan

1. Validate, commit, and push this OpenSpec plan.
2. Implement and test the successor evaluator, seed inventory, registration,
   no-native verifier, and historical-isolation checks; commit and push.
3. Collect build-only native identity, publish the exact ledger and
   registration, independently verify them, then commit and push.
4. Prove tracked-clean pushed state and execute the cohort exactly once.
5. Verify artifacts without native loading, publish closeout, run focused tests
   and the repository commit gate, sync specs, archive, and push.

Rollback before journal start removes the new implementation and unconsumed
registration. Rollback after journal start preserves the journal and result as
a consumed negative and removes no historical or successor evidence.

## Open Questions

The exact eight seed values remain intentionally unset until the pushed seed
inventory implementation proves an untouched cohort. This is a registration
input, not a runtime choice.
