## 1. Red Isolation Regressions

- [x] 1.1 Add request-builder/loader regressions proving the current schema omits CommunicationMod raw restoration, marker bytes, run/checkpoint/log inventories, and malformed filesystem-entry rejection; run them red for the intended missing v2 fields and checks.
- [x] 1.2 Add qualifier lifecycle regressions for pre-launch resource drift, exact configuration-command exception, success/failure restoration, post-exit resource drift, and an owned child PID that remains alive; run each red before implementation.
- [x] 1.3 Add standalone-verifier regressions proving a self-consistent terminal currently verifies despite restored-state drift or a live child PID, plus a historical-v1 replay fixture; record the expected red failures.

## 2. Request And Qualifier Isolation

- [x] 2.1 Implement guarded, canonical runner-side file/inventory snapshots and compact hashes for CommunicationMod, marker, runs, registered checkpoints, and global AI logs; reject symlinks, Windows reparse points, non-regular entries, missing required roots, and read failures.
- [x] 2.2 Advance request creation/loading to v2, bind the complete isolation baseline and exact original CommunicationMod bytes, and preserve strict historical-v1 parsing only where immutable evidence replay requires it.
- [x] 2.3 Validate every non-config baseline before attempt publication, permit only the exact trusted-launcher `command` property transformation, and restore/recheck original CommunicationMod bytes on every controlled exit.
- [x] 2.4 Advance terminal evidence to v2 and bind restoration, canonical post-observation, exact comparison/mismatch labels, and owned-child liveness; publish completion only for exact isolation and bind every controlled failure without granting authority.

## 3. Independent Verification

- [x] 3.1 Implement an independent verifier-side isolation collector with the same canonical fixture vectors but no runner collector import.
- [x] 3.2 Dispatch v1 evidence only as historical unqualified evidence; for v2, independently replay request/result isolation, recollect current restored state, and reject every mismatch or live/ambiguous child PID before publishing an audit.
- [x] 3.3 Update exact request/result/audit fixtures, CLI regressions, registration-bound implementation hashes, and historical r1/r2/r3 replay coverage without weakening one-shot or external-anchor checks.

## 4. Verification And Handoff

- [x] 4.1 Run focused qualification producer, lifecycle, verifier, bootstrap, and exact-registration pytest with a writable external or inert repository basetemp.
- [x] 4.2 Run the full pytest suite, `openspec validate --all --strict`, diff/source-hygiene checks, and an independent code/evidence review; resolve every Important finding.
- [x] 4.3 Commit the offline implementation repair as one cohesive source snapshot S with no live game, qualifier, run lock, collection, training, tuning, or policy change.
- [x] 4.4 In the separately reviewed `qualify-r7-outcome-evidence-replacement` amendment, preserve every earlier identity, use the previously absent r7 root, regenerate request/R anchors from the current source snapshot, and reconsider one live qualification. R7 retired at the independently verified `source_validation_failed` pre-request boundary without retry or `start` authority.
