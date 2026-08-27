## 1. Regression Evidence

- [x] 1.1 Add focused state-encoder regressions for observed potion and relic internal-ID/display-name pairs
- [x] 1.2 Cover known-ID precedence, empty potion slots, and identities unknown by both ID and name

## 2. Encoder Repair

- [x] 2.1 Add the minimal preferred-ID then display-name fallback to RL v2 potion and relic encoding
- [x] 2.2 Verify vocabulary sizes, numeric mappings, tensor shapes, and already-known encodings remain unchanged

## 3. Historical Correction Audit

- [x] 3.1 Implement a deterministic read-only trace/replay join and inventory fallback coverage audit
- [x] 3.2 Add audit regressions for exact alignment, mismatch rejection, coverage accounting, and immutable publication
- [x] 3.3 Run the audit on registered r14/r15 evidence and publish a correction addendum bound to the r2 calibration

## 4. Verification And Closeout

- [x] 4.1 Run focused pytest for the encoder and audit
- [x] 4.2 Run the optimized full commit gate once at the completed capability boundary
- [x] 4.3 Keep production configuration unchanged until a bounded fresh validation explicitly exercises the repaired encoder
- [x] 4.4 Validate, sync, and archive the completed OpenSpec change
- [x] 4.5 Commit and push the coherent repair and evidence
