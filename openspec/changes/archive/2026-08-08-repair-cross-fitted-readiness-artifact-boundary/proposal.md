## Why

The consumed r3 source-only readiness attempt exposed two coupled artifact-boundary defects: the historical seed inventory recursively ingested the tracked r2 readiness candidate until canonical publication exceeded 512 MiB, and the terminal failure path left its runner-created staging directory behind so the preregistered receipt review could not verify closure. A source-only correction is required before any later readiness attempt can be proposed.

## What Changes

- Define a deterministic, non-self-referential report-source universe that excludes cross-fitted readiness attempts, publications, closeouts, staging, and sealed artifacts from historical seed extraction while retaining legitimate empirical seed evidence.
- Require the producer and independent verifier to apply the same source classifier and independently reproduce the resulting included path bindings.
- Track ownership of the exact readiness staging directory and remove only runner-owned staging before terminalizing any pre-install failure, including candidate ceiling and independent-verifier failures.
- Preserve fail-closed behavior when cleanup cannot be proven: emit typed `no_go_artifact_binding`, grant no terminal-verification or downstream authority, and never delete a pre-existing or unowned path.
- Add RED regressions for recursive readiness ingestion, producer/verifier parity, canonical-ceiling failure, verifier failure, unowned-path preservation, and cleanup failure.
- Keep the 64 MiB stored, 512 MiB canonical, 900-second verifier, and all other readiness ceilings unchanged.
- Do not invoke readiness r4, load native/runtime/model/game/CommunicationMod code, access empirical outcomes, fit, train, evaluate, run OPE, register a successor, qualify, or promote.

Success means focused source-only tests and the repository gate support a clean pushed repair whose bounded candidate inventory no longer depends on prior readiness-derived inventories and whose owned pre-publication residue is absent on terminal failure. Before any later attempt is claimed, rollback is an ordinary source revert; this change creates no attempt identity or irreversible execution state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-cross-fitted-empirical-successor-readiness`: Make historical seed-source selection non-recursive and require ownership-scoped staging cleanup before terminal failure receipts are considered independently verifiable.

## Impact

The change affects the source-only seed inventory helper, readiness auditor, standalone readiness verifier, focused tests, and the canonical readiness specification. It does not change gameplay policy, reward logic, simulator/native adapters, model or checkpoint formats, registration schemas, empirical cohorts, or production configuration.
