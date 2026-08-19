## 1. Regression Contract

- [x] 1.1 Add focused tests for exact production metadata/hash validation, simulator-only checkpoint classification, and fail-closed output handling.
- [x] 1.2 Add deterministic reload tests covering structural, parameter-hash, masked-Q, and action equivalence.

## 2. Shadow Converter

- [x] 2.1 Implement the source-only production checkpoint validator and strict current-trainer load.
- [x] 2.2 Implement authority-reduced shadow serialization, deterministic equivalence probes, and atomic report/manifest publication.

## 3. Evidence And Verification

- [x] 3.1 Run the focused converter tests and strict OpenSpec validation without rerunning the unrelated full suite or launching gameplay.
- [x] 3.2 Convert the exact production r16 checkpoint, validate the published artifact hashes, and record the immutable source/shadow binding.
