## Why

The r3 card-acceptance inventory identity is terminal after publishing an
unverified 2.67 GB inline-provenance artifact and then failing during CLI
stdout publication. The bounded CLI and compact v4 inventory implementation
are now reviewed, fully tested, archived, and pushed, so parent task 6.2 needs
one distinct r4 identity that can build and independently verify bounded source-
only evidence without reusing or reading the terminal r3 artifact.

## What Changes

- Bind r4 to pushed source commit `710599ec6`, including bounded CLI completion,
  compact v4 aggregate inventory construction, independent v4 successor
  verification, and the nested runtime deadline repair discovered by the full
  gate.
- Create a distinct r4 source inventory, request id, output root, request,
  approval resolution, authorization, launch observation, receipt, and attempt
  root. Preserve r1/r2/r3 artifacts and identities as terminal predecessors;
  bind their tracked terminal evidence and path identities without reading,
  validating, converting, deleting, or registering r3 inventory content.
- Require exact isolated dispatch, source/path preflight, pushed tracked-clean
  ancestry, compact schema v4, a 64 MiB canonical inventory ceiling, bounded
  2,048-byte CLI completion, and absence of every r4 write surface before any
  r4 authority artifact is published.
- Permit at most one logical r4 build start under the existing durable-receipt
  boundary. Preserve the reviewed one-time pre-start reinvocation rule, but do
  not retry automatically or alter source, paths, cohorts, limits, thresholds,
  or authority after observing an outcome.
- On build success only, use a distinct read-only verification launch to rescan
  the closed registered source bytes and independently verify exact source
  identities, aggregate row counts, exclusions, fixed `512/128/512` cohorts,
  role digests, authority bindings, whole digest, receipt, and bounded output.
- On exact verification only, publish and independently review one all-false r4
  registration and complete parent task 6.2. Leave task 6.3 and every training,
  native/model/environment, evaluation, gameplay, CommunicationMod, formal RL,
  OPE, qualification, promotion, and downstream authority false.
- Live evidence is the reviewed terminal r3 postmortem at `5ffaaa6be`, the
  compact source repair through `6c4dee3d7`, and its archived contract at
  `710599ec6`. Success is a bounded independently reconstructed v4 inventory
  plus all-false registration, not dispatch readiness, build publication, or
  CLI completion alone.
- Rollback before a started receipt removes only additive uncommitted r4
  artifacts. After a receipt exists, rollback preserves all evidence and denies
  registration and downstream authority; it never deletes, retries, resumes,
  repairs in place, converts a predecessor, or replaces the consumed identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Add the distinct compact-v4
  r4 inventory, verification, and all-false registration gate after terminal r3.
- `noncombat-card-acceptance-inventory-source-boundary`: Require r4 source/path
  preflight to bind the pushed compact source, all terminal predecessors,
  excluded predecessor/generated/write roots, canonical byte ceilings, and
  absent r4 output/staging/attempt/receipt paths before authority publication.

## Impact

The change is planning- and source-control-only until separately reviewed r4
artifacts are published. Later implementation may add bounded r4 report
artifacts and, only after distinct authorization, one compact inventory and
all-false registration. It reuses the existing control plane, seed-inventory
CLI, standing delegation, independent verifier, and Windows production
interpreter. It changes no gameplay policy, simulator semantics, RL objective,
model/checkpoint, CommunicationMod configuration, dependency, or production
import path.
