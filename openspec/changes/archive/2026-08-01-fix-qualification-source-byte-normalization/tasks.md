## 1. Bind The Failure And Regression

- [x] 1.1 Record the immutable r7 bootstrap boundary and a clean-checkout replay of review commit `ad4a74d9`, including the reviewed, raw, and forced-normalization `.gitignore` object IDs; do not modify historical r7 bytes.
- [x] 1.2 Add a focused regression whose exact reviewed CRLF blob fails under the current normalization-only validator, and preserve the existing normalized-checkout acceptance test as the fallback contract.
- [x] 1.3 Add or identify focused substantive-text and binary tamper protections that prove raw-first acceptance does not weaken source-integrity rejection.
- [x] 1.4 Add a red regression for the reviewed built-in `binary` attribute and a protection regression proving a tracked external filter directive remains rejected.

## 2. Implement Raw-First Source Validation

- [x] 2.1 Compute the ordinary Git blob ID from each descriptor-read source and accept an exact reviewed match before invoking the existing controlled `core.autocrlf=true` fallback.
- [x] 2.2 Keep `.gitattributes` raw-byte exact, extend its directive allowlist only with Git's literal built-in `binary` token, and leave no-follow paths, identities, index flags, untracked executable checks, and bootstrap schemas unchanged.
- [x] 2.3 Run the focused source-validation regressions and replay the exact r7 review commit from a clean offline checkout; require both to pass without launching Slay the Spire.

## 3. Verify And Close The Offline Fix

- [x] 3.1 Run the focused qualification-bootstrap slice with cache disabled and a fresh writable basetemp, then run Python compile checks for the modified runner and tests.
- [x] 3.2 Run the registered `commit` test gate, `openspec validate --all --strict`, and `git diff --check`; do not run an unregistered raw full suite or any live qualification.
- [x] 3.3 Review the final diff for source-integrity scope and prove no request schema, timeout, CommunicationMod configuration, game, RL, checkpoint, reward, policy, or authority change entered it.
- [x] 3.4 Commit the cohesive source fix and diagnosis, sync the delta requirement, and archive this change. Leave any replacement qualification to a separate later amendment.
