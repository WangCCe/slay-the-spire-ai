## Context

The existing static audit deliberately starts from literals in
`SimpleAgent._choose_event_option`. Its zero-unaccounted result therefore means
all Current-explicit aliases are covered, not that every native event decision
is covered. The API v3 compatibility evaluator has the stronger contract: every
encountered native event must be hydrated from the hash-bound observation
contract. Seed 7000 exposed the mismatch at `Scrap Ooze`.

An independent source read under the frozen simulator identity gives five
distinct surfaces:

- 51 unique event enums are declared by `oneTimeEventsAsc0` and the Act 1-3
  event and shrine pools;
- `Colosseum` and `Match and Keep` are statically disabled in this build;
- `Bonfire Spirits` is reachable but enters card selection directly and has no
  event-option target decision;
- 25 reachable event-option events have explicit Current branch or risky-set
  semantics in the frozen contract; and
- 23 reachable event-option events use Current's generic position-zero default.

The audit must reproduce these counts and identities from exact source rather
than treating them as policy constants. Any source or partition drift blocks
publication.

## Goals / Non-Goals

**Goals:**

- Prove the complete Ironclad A0 native event surface from pool declarations,
  permanent runtime guards, setup transitions, legal-action cases, identity
  tables, and Current AST evidence.
- Publish a successor contract whose explicit and generic sets are disjoint and
  whose union equals every reachable event-option target.
- Hydrate generic events from ordered native candidates only when exact source
  evidence proves Current has no event-specific behavior for that identity.
- Preserve historical contracts and registrations and keep every downstream
  authority false.

**Non-Goals:**

- Changing Current event choices, simulator behavior, native adapter API, or
  Communication Mod gameplay.
- Building/loading a native module, reading a simulator seed, rerunning the
  consumed compatibility cohort, or registering a successor cohort.
- Measuring baseline quality, outcomes, reward validity, OPE, formal RL,
  training, qualification, loading, or promotion.
- Reproducing complete event UI prose when Current follows its generic default
  and does not inspect labels.

## Decisions

### Audit pool declarations and runtime reachability separately

The audit will parse only the registered A0 pool declarations in
`include/constants/Events.h`, then classify each pool identity using exact
compile-time disable flags and their selection guards in `GameContext.h` and
`GameContext.cpp`. It will separately parse setup transitions and legal-action
cases to identify reachable events that do not produce event-option target
decisions.

This keeps `pool_declared`, `runtime_disabled`, `direct_transition`, and
`event_option_target` explicit. Treating every pool member as an event target
would incorrectly include both disabled events and Bonfire Spirits. Treating
only observed native events as reachable would spend seeds without proving
closure.

The parser is intentionally bounded to the current source forms. It will not
evaluate arbitrary C++; changed declarations, guards, or transitions fail with
a field-specific blocker instead of falling back to regex guesses.

### Partition target events by Current AST behavior

The existing comment-aware AST/source parsers will be reused for Current
aliases and upstream legal, display, and execution cases. The audit will prove:

`event_option_target = explicit_policy_sensitive + generic_default`

with exact disjoint identities and no remainder. An event may enter the generic
set only if none of its registered game/save identities occurs in an explicit
branch or risky-event set. The Current source hash and AST evidence are part of
the successor contract identity, so adding policy logic later invalidates the
generic proof.

Alternative considered: add only Scrap Ooze. Rejected because another seed
would merely discover the next unregistered generic event.

### Use a registered generic rule, not 23 copied label tables

The successor contract will retain all 25 explicit rules, including Cursed
Tome phases and N'loth context, and add one identity record per audited generic
event. At runtime the generic resolver will:

1. require the upstream event id and event name to match exactly one registered
   generic identity;
2. require non-empty, sorted, unique event candidates with valid simulator
   indices and labels;
3. assign contiguous Current positions in candidate order while retaining each
   simulator index; and
4. use the adapter candidate label as both Current label and text.

Current's generic path always returns position zero and does not inspect those
labels. Candidate-derived labels therefore preserve the executable observation
without pretending to reproduce complete UI semantics. Explicit rules always
take precedence; a generic identity can never shadow an explicit event.

Alternative considered: copy all static and phase-specific display prose for
23 events. Rejected because it expands an observation bridge into a second
event simulator and adds dynamic state with no effect on Current's generic
choice.

### Version the successor and preserve historical readers

The frozen 25-event contract and consumed compatibility artifacts remain
byte-for-byte unchanged. A new canonical contract directory and resolver
identity will bind the reachable-surface audit, exact simulator/Current sources,
explicit predecessor contract, generic identities, and all-false authority.

Bridge registration validation will remain schema-aware: historical successor
registrations continue to require the old exact semantic identity, while new
code-level sessions use the new resolver identity. No historical result is
upgraded in place and no consumed cohort becomes retryable.

### Publish implementation and evidence in separate boundaries

The work will use these commit boundaries:

1. complete, validate, commit, and push this OpenSpec plan;
2. implement and regression-test the source audit and successor contract
   generator, then commit and push before canonical publication;
3. publish and strictly recompute the registered source-only audit and contract;
4. implement the versioned resolver/bridge path against that frozen contract;
   and
5. run focused tests, the repository commit gate, sync specs, archive, and push.

No step constructs a native environment. A later compatibility rerun requires
a different OpenSpec change, untouched seeds, and a new pushed registration.

## Risks / Trade-offs

- [A pool member is mistaken for a target decision] -> Preserve the four-way
  pool/disabled/direct-transition/target partition and require exact count and
  set reconciliation.
- [A generic event gains policy-sensitive behavior] -> Bind the Current AST and
  require the generic set to remain disjoint from every branch and risky alias.
- [Candidate-derived labels hide sparse indices] -> Validate sorted unique
  simulator indices and emit separate contiguous Current positions for every
  option.
- [Bounded C++ parsing misses a new source form] -> Fail closed with raw source
  identity and a parser blocker; do not infer reachability from gameplay.
- [The successor is mistaken for native compatibility] -> Keep native, seed,
  baseline, outcome, reward, model, OPE, RL, training, and promotion authority
  false and require a separately preregistered cohort.
- [Historical evidence changes under the new resolver] -> Keep predecessor
  files immutable and make registration validation explicitly version-aware.

## Migration Plan

Additive successor artifacts and code become the default only for new
code-level bridge sessions. Historical registrations retain their exact old
identity and remain verification-only. Rollback removes the successor audit,
contract, and resolver path; the frozen contract and failed cohort remain the
active evidence boundary.

## Open Questions

None. Count or identity drift discovered by the implementation is a blocker to
review in the audit report, not permission to tune the partition.
