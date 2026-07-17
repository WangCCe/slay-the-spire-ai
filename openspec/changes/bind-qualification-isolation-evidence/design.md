## Context

The current v1 qualification request binds source, registration,
implementation, child config, marker count, and qualification-root paths. Its
terminal record binds the owned child lifecycle, but broad live isolation is
left to an external operator. The pending v2 study amendment now requires an
independently replayable isolation result before `start`, and review showed that
the standalone verifier has no input or check that can establish that result.

The repair must preserve the one-shot evidence model, the fixed isolated
Windows launcher, historical r1/r2/r3 replay, and the rule that no local result
alone grants study or training authority. It must also work before exploration,
logging, checkpoints, or gameplay are initialized by the qualification child.

## Goals / Non-Goals

**Goals:**

- Bind a compact, canonical pre-launch baseline for every live resource named
  by the r4 gate.
- Detect drift before the child launch and again before a passing terminal is
  sealed.
- Restore CommunicationMod to its exact original bytes as part of the owned
  qualification lifecycle.
- Make the independent verifier recollect the restored state and prove the
  owned child PID is no longer alive.
- Preserve historical v1 evidence without allowing it to qualify a new launch.

**Non-Goals:**

- Starting or collecting the registered study, changing gameplay policy,
  training, tuning, or promotion.
- General-purpose filesystem or process monitoring.
- Proving facts about unrelated Python, PowerShell, Java, or Steam processes.
- Retrying or rewriting any consumed qualification identity.

## Decisions

### 1. Put a compact isolation baseline in request v2

The request gains one exact `isolation` object and advances to a v2 schema. It
contains a method version and these observations:

- CommunicationMod path, raw byte SHA-256, size, parsed semantic properties,
  and base64-encoded original bytes needed for exact restoration.
- AI marker path, existence, raw SHA-256, size, and line count.
- A recursive run-record inventory digest under the game `runs` root.
- A checkpoint inventory digest using only the registration-fixed root and
  patterns.
- Exact states for `ai_debug.log` and `communication_mod_errors.log`.

Each inventory digest is computed from a canonical ordered sequence of relative
path, regular-file kind, byte size, and content SHA-256. The request stores only
the digest, entry count, and total bytes. Any symlink, Windows reparse point,
non-regular entry, traversal ambiguity, or read failure rejects the snapshot.
Missing global log files are represented explicitly; required roots and the
CommunicationMod file must exist.

Every hashed file is read through one guarded open handle. The collector
compares no-follow path metadata, handle metadata before and after reading, and
the final no-follow path metadata for identical file identity and stable
size/mtime/ctime. A check-to-open swap, mid-read replacement, or parent reparse
change therefore fails closed instead of hashing an object that was not the
reviewed lexical path.

This is preferred to separately anchored pre/post files because the direct-child
review commit already provides the immutable external anchor for the baseline.
It also removes a second file-placement and hash-matching protocol.

### 2. Treat the live CommunicationMod command as one deterministic exception

At request creation, CommunicationMod must contain the normal configuration and
those exact original bytes are bound. At qualifier startup, all non-config
resources must still equal the baseline. The live configuration may differ only
in the parsed `command` property, which must equal the existing trusted launcher
constructed from the externally supplied full R and request self-hash,
file-SHA, and size. Every other property must equal the baseline.

After the child reaches release and exits, and on every ordinary failure path,
the qualifier restores the bound original bytes with guarded same-directory
atomic replacement. It requires the parent-directory identity and temporary
file identity to remain stable across replacement, rereads through the guarded
handle contract, and recollects the full isolation snapshot. A passing
completion is published only when the post-state equals the request baseline
exactly. A failure record binds the restoration attempt and observed
mismatches; a crash or terminal-publication failure remains a consumed partial
identity and is never repaired in place.

The `qualify` CLI writes neither success nor failure text to inherited stdout or
stderr because CommunicationMod routes those streams into live protocol/global
logs that are themselves isolation-bound. Exit status plus the exclusive
terminal record is the diagnostic contract after consumption; a pre-consumption
rejection intentionally exposes only a nonzero exit to that channel and must be
reproduced offline from the reviewed anchors rather than mutating a bound log.

This approach is stronger and less error-prone than a separate manual restore
step while retaining the independently supplied launch anchors that avoid a
self-referential request/R hash.

### 3. Bind observations in the result, but require independent recollection

Result v2 carries the baseline hash, canonical post-observation hash, comparison
status, explicit mismatch labels, restoration status, and the owned child PID
liveness observation. These fields are evidence, not authority.

The standalone verifier independently implements the same canonical collection
rules instead of importing the runner collector. It validates the request and
terminal schemas, recomputes the current restored snapshot, requires equality
with both request and terminal observations, and checks that the recorded child
PID cannot be opened as a live process. PID reuse fails closed. Only then may it
publish a v2 audit whose study, run-lock, collection, policy, causal, and
training authority fields remain false.

### 4. Keep v1 replay historical and fail closed for new launches

The verifier retains a strict v1 dispatch path for immutable r1/r2/r3 evidence.
It labels that evidence as lacking bound broad isolation and never treats it as
a candidate for the strengthened launch gate. Request creation and the live
`qualify` command emit and accept v2 only after this change. Exact fixtures and
registration implementation hashes are regenerated rather than silently
coercing old records.

### 5. Use red-first, boundary-focused verification

Focused tests first demonstrate that current code accepts configuration,
marker, run, checkpoint, log, and live-PID drift. Producer tests then cover
canonical snapshot construction and malformed filesystem entries; lifecycle
tests cover pre-launch rejection, success restoration, failure restoration, and
terminal binding; verifier tests independently mutate each bound resource and
require rejection. Focused pytest, full pytest, strict OpenSpec validation, and
an independent review are required before any new request is generated.

## Risks / Trade-offs

- **Large run/checkpoint inventories increase preflight time** -> Store compact
  digests, hash in chunks, and run the expensive comparisons only before child
  start and after child exit, outside the ten-second release window.
- **Automatic config restoration can fail after a partial launch** -> Attempt it
  on every controlled exit, bind the failure, preserve the consumed root, and
  require external recovery without reclassifying the qualification.
- **Runner/verifier collector duplication can drift** -> Use shared fixture
  vectors and cross-implementation conformance tests while retaining independent
  implementations.
- **PID reuse can reject otherwise clean evidence** -> Fail closed; a new
  reviewed qualification is cheaper than accepting ambiguous process evidence.
- **Ambient user gameplay or log writes invalidate the baseline** -> Treat this
  as intended isolation drift and regenerate a reviewed candidate only before
  any identity is consumed.

## Migration Plan

1. Add red regressions and implement v2 collection, request, result, and audit
   behavior without starting Slay the Spire.
2. Preserve v1 historical replay and pass focused/full offline verification.
3. Commit the implementation repair as a new source snapshot S and regenerate
   the registration because its implementation hashes change.
4. Supersede the unlaunched r4 planning candidate with a separately reviewed
   amendment and a previously absent live qualification root; do not mutate or
   consume the old prepared root.
5. Only after a new direct-child R and independent review may one live attempt
   be considered.

Rollback is source-only before step 5: retain the prior commit and every
prepared/failed root as historical evidence. No study state exists to migrate.

## Open Questions

None. Any additional resource or broader process inventory requires a later
spec change rather than an ad hoc live-only check.
