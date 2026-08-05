## 1. Regression Contract

- [x] 1.1 Add RED tests for input validation, deterministic family grouping, max-pooled hierarchical probabilities, equal-score cardinality neutrality, duplicate-score family-mass invariance, permutation behavior, and single-family fallback.
- [x] 1.2 Add RED tests for family/conditional/joint entropy decomposition, finite autograd behavior including tied maxima, stable metadata, and all-false authority.

## 2. Source-Only Capability

- [x] 2.1 Implement the additive CPU action-family distribution helper accepting float32 ranker scores without importing or changing simulator, experiment, replay, registration, or gameplay surfaces.
- [x] 2.2 Publish the deterministic design report and update project direction with the selected design, synthetic evidence, trade-offs, open questions, and explicit no-authority boundary.

## 3. Verification And Closeout

- [x] 3.1 Run the focused regression suite and deterministic report reproduction checks with a scoped system-temp pytest basetemp.
- [x] 3.2 Obtain an independent code and design review, fix actionable findings, and rerun focused verification.
- [x] 3.3 Run the repository commit gate and strict OpenSpec validation without launching gameplay, native modules, simulator episodes, or training.
- [x] 3.4 Sync the new capability to the main specs, archive the completed change, commit only scoped files, and push `master`.
