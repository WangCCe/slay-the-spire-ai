## 1. Freeze The Authorization Plan

- [x] 1.1 Strictly validate and independently review the proposal, design,
  delta requirement, exact grant provenance, stage separation, non-execution
  boundary, and rollback rule.
- [x] 1.2 Commit and push only the OpenSpec plan before generating delegation,
  approval, or authorization evidence.

## 2. Revalidate The Pushed Request Boundary

- [x] 2.1 Confirm local `HEAD` equals `origin/master`, contains the exact r2
  registration and request blobs, and descends from their publication commits.
- [x] 2.2 Confirm the registered output root, standing delegation, delegated
  approval, authorization, execution journal, checkpoint, and terminal targets
  are absent.
- [x] 2.3 Revalidate the compact registration and exact request through isolated
  source-only producer and independent validation paths with zero blocked-
  dependency import delta.

## 3. Publish Delegated Approval

- [x] 3.1 Re-read current task user-message metadata, verify message
  `item-22027` grant text/time/task provenance, and stop on any later explicit
  human revocation.
- [x] 3.2 Build and inspect one canonical standing-delegation v1 manifest,
  requiring canonical byte round-trip equality and exact self-digest.
- [x] 3.3 Render one delegated-approval v2 for request SHA-256
  `6257a36c6573c8c412bb8727736e81b063dd0c7076f1ea5b41a70d4a08206c2e`,
  independently validate its complete transitive binding, and publish a
  deterministic approval review.
- [x] 3.4 Run focused control/verifier tests, canonical digest probes, import
  isolation, and strict OpenSpec using scoped pytest temp storage.
- [x] 3.5 Verify exact staged scope, commit and push only delegation/approval
  evidence plus task state, and confirm the exact blobs on `origin/master`.

## 4. Publish Tracked Authorization

- [x] 4.1 Re-read and revalidate the exact pushed registration, request,
  delegation, and delegated approval; confirm the registered output root and
  all execution artifacts remain absent.
- [x] 4.2 Render one canonical authorization v1, independently validate its
  registration/request/approval/authority bindings, and publish a deterministic
  authorization review.
- [x] 4.3 Run focused control/verifier tests, canonical digest probes, import
  isolation, and strict OpenSpec using a fresh scoped pytest temp child.
- [ ] 4.4 Verify exact staged scope, commit and push only authorization evidence
  plus task state, and confirm the exact blobs on `origin/master`.

## 5. Close Without Execution

- [ ] 5.1 Record the long commit gate and fresh gameplay validation as not
  applicable unless implementation or test source unexpectedly changes.
- [ ] 5.2 Obtain a bounded independent final review and resolve only
  publication-blocking evidence defects without changing registered terms.
- [ ] 5.3 Sync the delta requirement, update project direction, archive the
  change, run final strict validation, and commit/push closeout separately.
- [ ] 5.4 Confirm the registered output root and empirical artifacts remain
  absent; stop without native loading, environment construction, seed access,
  fitting, training, evaluation, execution, gameplay, or CommunicationMod.
