## 1. Transition Contract

- [x] 1.1 Add focused tests for deterministic action sampling, native reward components, terminal handling, and unsupported-successor exclusion.
- [x] 1.2 Implement bounded simulator transition generation into the existing RL v2 replay contract.

## 2. Disposable Training

- [x] 2.1 Add focused tests for deterministic fresh initialization, finite optimizer updates, parameter delta, and production checkpoint isolation.
- [x] 2.2 Implement CPU-only training from fresh weights and save a simulator-only candidate with source-bound metadata.

## 3. Held-Out Evaluation

- [x] 3.1 Implement paired pre/post evaluation on fixed disjoint LightSTS seeds with outcome, HP, decision, and unsupported metrics.
- [x] 3.2 Run one bounded training smoke and publish replay, loss, parameter, action, reward, evaluation, and artifact-hash evidence.

## 4. Closeout

- [x] 4.1 Run focused pytest and strict OpenSpec validation; do not run gameplay, CommunicationMod, production model loading, or the full unrelated suite.
- [x] 4.2 Record the technical verdict and larger-simulator/live-transfer gates, review the scoped diff, commit, and push `master`.
