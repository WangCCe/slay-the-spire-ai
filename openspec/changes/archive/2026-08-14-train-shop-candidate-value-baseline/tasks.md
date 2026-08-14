## 1. Training Runner

- [x] 1.1 Implement bound corpus loading, candidate feature encoding, and exact source-isolated splits
- [x] 1.2 Implement train-only checkpoint selection and one-shot holdout comparison
- [x] 1.3 Publish canonical model, metrics, configuration, report, split, and manifest artifacts

## 2. Verification

- [x] 2.1 Add focused tests for identity rejection, feature determinism, source isolation, fitting, and artifact integrity
- [x] 2.2 Run focused pytest and strict OpenSpec validation
- [x] 2.3 Commit and push the source-bound training runner

## 3. Execution

- [x] 3.1 Execute the fixed CPU training once against the committed corpus
- [x] 3.2 Verify artifact hashes and terminal holdout verdict
- [x] 3.3 Archive the change, commit evidence, and push `master`
