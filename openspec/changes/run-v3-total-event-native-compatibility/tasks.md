## 1. Planning Boundary

- [x] 1.1 Strictly validate and commit the complete OpenSpec change before editing evaluator code or building the native module
- [x] 1.2 Push the planning commit to `origin/master` and record the exact preregistered cohort and limits as immutable inputs

## 2. Evaluator Regressions And Implementation

- [x] 2.1 Add red regressions for duplicate-key rejection, exact registration identity, fixed seed-ledger isolation, and prohibited caller overrides
- [x] 2.2 Implement the versioned registration loader, physical identity discovery, seed-ledger recomputation, and pushed-HEAD pre-seed checks
- [x] 2.3 Add red regressions proving atomic whole-cohort consumption before the first environment and terminal no-retry behavior after failures
- [x] 2.4 Implement fake-environment execution with fresh episode-local sessions, two-replay canonical equality, legality, terminal, source-immutability, and four-category gates
- [x] 2.5 Add and implement event diagnostics that preserve total-contract source, Current position, simulator choice index, and unique legal reverse mapping
- [x] 2.6 Add and implement canonical configuration, rows or failure, metrics, report, journal, manifest, and a no-native deterministic verifier

## 3. Implementation Publication

- [x] 3.1 Run focused regressions, Python compilation, strict OpenSpec validation, and the repository commit gate without live gameplay
- [x] 3.2 Commit and push the verified evaluator implementation before configuring or loading an API v3 module

## 4. Native Identity And Registration

- [x] 4.1 Configure and build the API v3 adapter in a new ignored directory, then load only API and build-info surfaces without constructing `Environment`
- [x] 4.2 Collect module, adapter, simulator physical source, dependency, contract, policy, metadata, runtime, predecessor, and output identities
- [x] 4.3 Generate and independently verify the exact `7000..7007` seed ledger and immutable compatibility registration
- [x] 4.4 Commit and push the registration, then prove tracked-clean status, exact `HEAD` registration bytes, and `HEAD == origin/master`

## 5. One-Shot Compatibility Execution

- [ ] 5.1 Run the final no-seed preflight and atomically consume the complete cohort before constructing the first environment
- [ ] 5.2 Execute exactly two bounded replays for each registered seed once, preserving pass, failure, timeout, crash, or partial state without retry
- [ ] 5.3 Verify the preserved result without loading native code and publish the structural verdict with all downstream authority false

## 6. Closeout

- [ ] 6.1 Update project direction from the frozen result and document whether a separate baseline-floor proposal is allowed or the structural blocker remains active
- [ ] 6.2 Run focused regressions, the repository commit gate, and strict global OpenSpec validation on the final artifacts
- [ ] 6.3 Sync the capability specs, archive the completed change, commit, and push the immutable closeout
