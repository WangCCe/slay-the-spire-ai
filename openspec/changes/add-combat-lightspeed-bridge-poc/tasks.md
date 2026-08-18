## 1. Native Environment

- [x] 1.1 Add focused source-contract tests for the combat adapter API, isolation markers, and separate CMake target.
- [x] 1.2 Implement deterministic first-combat reset, clone, canonical snapshot, legal actions, stepping, terminal state, and explicit unsupported boundaries.
- [x] 1.3 Build the new module in a fresh run-scoped directory and verify native reset, clone isolation, and successor determinism.

## 2. RL v2 Bridge

- [x] 2.1 Add focused tests for exact observation shapes, 133-wide masks, action correspondence, identity failures, and production import isolation.
- [x] 2.2 Implement provenance validation and explicit native snapshot-to-RL v2 observation/action mapping without model loading.
- [x] 2.3 Validate supported and unsupported native states through the Python wrapper.

## 3. Calibration Evidence

- [x] 3.1 Add a bounded deterministic calibration runner with fixed seed/action bounds and all-false authority.
- [x] 3.2 Run one source-only calibration, publish mapping/action/unsupported/determinism metrics, and bind source and module hashes.
- [x] 3.3 Run focused pytest and OpenSpec validation; do not run gameplay or training.

## 4. Closeout

- [x] 4.1 Record the POC verdict and the explicit gate for later simulator replay generation or real-game divergence calibration.
- [x] 4.2 Review the scoped diff, commit the coherent offline capability, and push `master`.
