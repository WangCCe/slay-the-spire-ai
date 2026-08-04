## Context

Logical execution `noncombat-simulator-rl-20260804-r1` is immutable and
terminal. Its standalone verifier accepts the artifact set, while its journal,
metrics, and report state that native loading failed before environment
construction, seed access, episode retention, or optimizer work. The native
load-order repair is pushed at `8d123fdf32bd94bc29e53a97f217a2b7ca40c4fe`.

The fixed experiment contract still names train `50000..51023`, canary
`51024..51151`, and holdout `51152..51663`. Reusing that partition preserves
the original preregistered statistical design and is not result-conditioned,
because no simulator state or outcome from those seeds was observed. It must
nevertheless be recorded as an intentional predecessor exception because r1
already registered the range and consumed its logical execution identity.

## Goals / Non-Goals

**Goals:**

- Create a canonical current-source inventory that classifies every overlap
  with `50000..51663` and allows only the verified zero-use r1 predecessor.
- Create an all-false r2 preregistration over the unchanged experiment contract.
- Bind exact pushed Python source, native adapter/module provenance, existing
  formal evidence, runtime, and the new reuse inventory.
- Reproduce and validate the canonical bytes in independent source-only
  processes, then push the preregistration before any authorization exists.

**Non-Goals:**

- Creating an execution authorization or claiming generic continuation consent
  as exact authorization for an eight-hour process.
- Loading the native module or Torch, constructing an environment, accessing a
  seed, training, evaluating, launching the game, or contacting CommunicationMod.
- Changing the fixed cohorts, algorithm, reward, gates, thresholds, simulator,
  native module, or archived r1 evidence.

## Decisions

### Reuse the untouched cohort instead of rotating it

The successor will retain `50000..51663`. The r1 failure exposed only process
startup state and revealed no seed-dependent information, so rotation would
change the preregistered experiment without reducing selection bias. A fresh
range remains the fallback only if the reuse inventory finds empirical access
or another overlap; it will require a separate proposal rather than an inline
substitution.

### Publish a new cohort-reuse inventory

The existing seed inventory predates r1 and cannot by itself explain the new
registration overlap. A new canonical JSON inventory will bind the r1 manifest,
registration, authorization, journal, metrics, and verifier result; record zero
environment, seed, episode, update, canary, and holdout effects; scan tracked
registration-shaped JSON for intersecting seed declarations; and classify r1
as the sole allowed `registered_but_unconsumed` overlap. Any additional overlap,
nonterminal predecessor, failed verifier, or contradictory effect blocks r2.

The r2 registration continues to use the existing generic `seed_inventory`
binding field, pointing it at this new artifact. This avoids changing the
runtime schema while making the successor-specific decision content-addressed.

### Bind r2 to the repaired pushed source

The registration implementation and adapter commits will both name
`8d123fdf32bd94bc29e53a97f217a2b7ca40c4fe`. Source digests are computed from
Git blobs using the runner's named-byte hashing contract. The unchanged native
module and physical simulator provenance remain byte-identical to r1. Existing
formal evidence bindings remain unchanged.

### Keep authorization as a separate artifact and user decision

This change publishes no authorization file. The proposed future identity is
`noncombat-simulator-rl-20260804-r2` with output
`reports/noncombat_simulator_rl_experiment_20260804_r2`, but neither becomes
executable until a later exact user authorization binds the pushed registration
commit, resource limit, cohort, module, and no-retry rules.

## Risks / Trade-offs

- **A hidden prior seed use could invalidate reuse** -> Scan current tracked
  registration-shaped controls and cross-check r1 terminal evidence; block on
  every unclassified overlap or contradiction.
- **A copied registration could retain stale source identity** -> Recompute the
  implementation and adapter named-byte hashes from the exact pushed commit and
  compare working bytes to Git bytes before publication.
- **Preregistration could be mistaken for permission to train** -> Keep all
  authority false, do not create authorization or output, and state the later
  exact approval gate in every report and task.
- **Manual canonical generation may drift** -> Generate twice in independent
  Python processes, compare bytes and digests, then validate the committed blob.
- **Historical evidence could be mutated accidentally** -> Read r1 only and
  require its manifest digest plus a path-scoped no-diff check before commit.

## Migration Plan

1. Validate r1 independently and inventory current seed declarations.
2. Generate the reuse inventory and r2 registration twice without native or
   Torch imports.
3. Verify canonical bytes, all-false authority, exact source identities, absent
   authorization, and absent r2 output.
4. Commit and push only the preregistration, inventory, OpenSpec artifacts, and
   a narrow direction update.
5. Sync and archive this preregistration change. A later change or exact user
   approval may create the one-shot authorization.

Before publication, rollback is deletion of only the new uncommitted r2 files.
After publication, corrections require a new registration path and identity;
the committed bytes and r1 artifacts remain immutable.

## Open Questions

None. Discovery of any empirical use or additional overlap is a blocking result,
not an invitation to choose a replacement cohort inside this change.
