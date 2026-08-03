## Context

`sts_lightspeed` keeps shop inventory in fixed source slots. After a purchase
without The Courier it marks the purchased slot with `price == -1`, whereas
the live game removes that item from the visible shop list. The native adapter
currently serializes all fixed slots, so its snapshot exposes sold items that
Communication Mod would not expose. The Python bridge correctly rejects those
negative item prices before Current policy execution.

This change is constrained by immutable prior evidence: the formal seed
cohorts `7000..7007` and `7100..7107` are consumed, and the existing API v3
module is frozen by byte identity. The external simulator checkout also has
pre-existing changes and remains read-only.

## Goals / Non-Goals

**Goals:**

- Make native shop snapshots match Communication Mod's visible-inventory
  semantics after card, relic, or potion purchases.
- Retain original fixed-slot identity for all visible items and legal actions.
- Distinguish the canonical sold sentinel from invalid negative prices.
- Produce a separately built and provenance-identifiable API v3 successor.

**Non-Goals:**

- Change Current shop scoring, affordability rules, or action selection.
- Change the bridge to accept negative item prices.
- Change adapter schemas or grant training, live, OPE, or promotion authority.
- Run live gameplay, a fresh formal compatibility cohort, or any training.

## Decisions

### Filter at the native snapshot boundary

Each card, relic, and potion loop will read its source price before constructing
JSON. Exactly `-1` will omit the item, values below `-1` will raise a
kind-and-slot-specific runtime error, and all nonnegative values will serialize
normally. This reproduces the visible-list boundary before downstream policy
hydration.

Filtering in the Python bridge was rejected because it would make malformed
native snapshots look valid and would duplicate live-screen semantics after
the adapter contract. Relaxing metadata validation was rejected because it
would expose an item the live game no longer offers.

### Preserve fixed source slots in compact visible arrays

The JSON arrays may become sparse relative to the simulator's fixed storage,
but every retained entry will keep its original `slot`. Candidate ids and
reverse action mapping will continue to use that source slot. Positive-price
unaffordable inventory remains visible even when it has no legal candidate,
and a positive-price Courier replacement remains visible in the purchased
slot.

Renumbering retained items was rejected because it would break the established
mapping between snapshots, candidates, and `GameAction` indices.

### Keep API v3 and create a new physical module identity

The correction changes which invalid/sold source entries appear but does not
change the versioned JSON shape: shop arrays already support variable length
and entries already carry `slot`. The adapter API therefore remains v3. The
module will be configured and built in a new ignored out-of-tree directory;
the frozen predecessor module will be hashed before and after and never
overwritten.

An API v4 bump was rejected because no consumer migration is required. An
in-place rebuild was rejected because it would destroy the byte identity bound
to prior evidence.

### Use layered repair evidence without consuming a formal gate

Red regressions will cover the C++ source contract and Python hydration/action
mapping for sparse slots, positive unaffordable entries, and invalid negative
prices. The successor module will then receive bounded black-box smoke using
only previously used development seeds. The repository commit gate remains the
release check; the raw unpartitioned full suite will not be run.

A new formal cohort is deferred until this repair and a read-only check of the
remaining shop snapshot domain are complete.

## Risks / Trade-offs

- [Bounded smoke may not naturally purchase every item kind or encounter The
  Courier] -> Pair native smoke with source-complete simulator/live evidence and
  deterministic bridge regressions; do not overstate runtime coverage.
- [Keeping API v3 allows two module behaviors under one logical version] -> Bind
  every result to module and adapter-source hashes and never reuse predecessor
  readiness.
- [A future simulator version may introduce another sentinel] -> Fail values
  below `-1` with explicit kind/slot context instead of silently filtering all
  negatives.
- [Sparse arrays may reveal downstream positional assumptions] -> Add reverse
  mapping tests that use original slots differing from visible-list positions.

## Migration Plan

1. Commit and push the accepted planning artifacts.
2. Add failing source and bridge regressions, then implement the narrow native
   filter.
3. Build the successor in a new ignored directory and record source/module
   provenance while proving the predecessor hash is unchanged.
4. Run bounded reused-seed smoke, focused pytest, and the commit gate.
5. Publish a no-authority closeout, sync and archive the change, and push a
   clean `master`.

Rollback removes the filter, its regressions, and the new ignored build. It
does not alter frozen modules, consumed cohorts, or historical reports.

## Open Questions

No design question blocks implementation. Whether a third formal native gate
is justified will be decided only after this repair's closeout and the adjacent
shop-domain audit.
