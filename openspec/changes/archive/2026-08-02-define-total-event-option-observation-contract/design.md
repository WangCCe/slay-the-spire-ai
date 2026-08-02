## Context

The bridge currently enriches one `Liars Game` row with two semantic entries
whose indices happen to be both Current option positions and simulator action
indices. That equality does not hold generally. `sts_lightspeed` candidates
retain sparse global indices, while Communication Mod and Current use the
position within the visible enabled option list. For example, a Cleric screen
with only Leave legal can expose simulator index 2 at Current position 0, and
the intermediate `Cursed Tome` phases expose one of indices 2, 3, or 4 at
Current position 0.

The corrected r2 audit binds all 25 event source cases and 47 Current aliases.
It also shows that only `Cursed Tome` has phase-dependent legal masks. A direct
source review adds two decision-relevant facts not representable as a static
label table: `N'loth` labels contain the names of two offered relics, and
upstream `Mindbloom` must map to a Current-recognized event id. The current
adapter snapshot contains `event_data` and the player's relic list but does not
name the two N'loth offer slots.

## Goals / Non-Goals

**Goals:**

- Define one immutable Current-observation contract for all 25 events and 47
  aliases under the exact r2 Current/upstream identities.
- Separate visible Current position from simulator choice index and make the
  mapping reversible for sparse legal candidate sets.
- Record exact static labels, Cursed Tome phase/index labels, N'loth dynamic
  relic-name requirements, and Mindbloom identity normalization.
- Produce deterministic, hash-bound artifacts that make the next resolver and
  adapter work reviewable without executing either runtime.

**Non-Goals:**

- Reconstructing full event body or outcome-description text that Current does
  not observe when a non-empty label is present.
- Reimplementing every conditional legal-action expression; the bound simulator
  remains the source of each current legal candidate subset.
- Modifying the resolver, bridge, native adapter, Current policy, reward,
  evaluation cohort, or training path.
- Running a native module, simulator seed, gameplay process, model, or trainer.

## Decisions

### Contract Current-observable semantics, not complete UI prose

Each contract option records a non-empty Current-facing label and its simulator
choice index. Full display descriptions may contain HP, gold, card, or relic
values that Current never reads because `_choice_label` prefers `label`. The
contract therefore makes no claim about complete event prose.

Alternative considered: reproduce every console output string. Rejected because
it requires broad event-state mirroring with no effect on Current decisions and
would blur an observation adapter with a simulator implementation.

### Model option identity with two coordinates

For a validated legal candidate list, the contract orders options by simulator
choice index and assigns contiguous Current positions `0..n-1`. Every emitted
row contains both `current_position` and `simulator_choice_index`; future action
mapping must translate through this row instead of comparing the two integers.
Duplicate, unordered, unknown, or event-mismatched candidates fail closed.

Alternative considered: preserve the bridge's direct index equality. Rejected
because sparse candidate sets deterministically map Current to the wrong action.

### Use three explicit observation rule classes

Twenty-three events use source-bound static index-to-label maps. `Cursed Tome`
uses an exact `event_data` table: phase 0 maps indices 0/1 to Read/Leave, phases
1/2/3 map index 2/3/4 to Continue, and phase 4 maps indices 5/6 to Take/Stop.
`N'loth` uses static Leave plus `Offer <relic name>` labels for indices 0/1 and
requires exact offered-relic records bound to the snapshot relic slots. The
Mindbloom identity rule maps upstream `Mindbloom` to Current `MindBloom` before
policy hydration.

Alternative considered: one generic label template engine. Rejected because
the two dynamic cases are small, structurally different, and safer as named
fail-closed rules.

### Bind a reviewed registry and validate it against r2

An explicit registration binds the implementation, corrected r2 registration,
inventory and manifest, Current source, selected upstream source files, event
rules, output names, and all-false authority. A read-only validator reconciles
the registry against r2's 25 events, 47 aliases, identity rows, legal/display
indices, and static labels. It permits only the reviewed Cursed Tome and N'loth
derivations beyond r2's literal label entries, then publishes canonical
configuration, contract, metrics, report, and manifest files once plus one
byte-for-byte recomputation.

Alternative considered: embed the expanded registry directly in the existing
runtime resolver. Rejected because project direction requires the contract to
be reviewed before resolver or adapter changes.

## Risks / Trade-offs

- **A static label is transcribed incorrectly** -> Reconcile every static entry
  against corrected r2 and block any difference.
- **A dynamic source dependency is missed** -> Scan every bound display case in
  focused regressions and require all label expressions to classify as static,
  Cursed Tome phase-derived, N'loth relic-derived, or decision-irrelevant prose.
- **Candidate legality changes with state** -> Treat the bound candidate set as
  legal authority, but reject indices outside the event contract and enforce
  the full Cursed Tome phase table.
- **N'loth cannot yet be resolved from snapshots** -> Record the exact required
  context schema and keep resolver/adapter readiness false until a later change
  exposes and validates those fields.
- **The contract is mistaken for policy or RL authority** -> Keep every
  execution, evaluation, reward, model, training, and promotion flag false in
  registration and outputs.

## Migration Plan

1. Publish and recompute the contract without changing runtime code.
2. Use its closeout as the sole input to a later resolver/adapter proposal.
3. Roll back by removing only the new validator and contract artifacts; all r2
   audit and bridge files remain immutable.

## Open Questions

None. Runtime implementation and any later compatibility cohort remain separate
approval boundaries.
