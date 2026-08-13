## 1. Replay Codec

- [x] 1.1 Add RED regressions for deterministic gzip, bounded decode, tensor/order drift, and episode round-trip identity.
- [x] 1.2 Implement canonical trajectory and post-collection generator encoding without autograd or native objects.
- [x] 1.3 Implement bounded replay loading and exact deterministic re-encoding verification.
- [x] 1.4 Prove decoded replay can rebuild the current cross-fitted objective and update.

## 2. Scorer Optimizer Ablation

- [x] 2.1 Add regressions for exact scorer parameter selection, Adam state slicing, and hidden-parameter exclusion.
- [x] 2.2 Implement scorer-only Adam construction from checkpoint `004` moments and registered options.
- [x] 2.3 Implement atomic full/scorer branch updates from decoded replay and compact telemetry.
- [x] 2.4 Require exact branch A bootstrap/optimizer reproduction and exact branch B hidden-byte preservation.
- [x] 2.5 Implement the fixed 80-percent retained-TV classification with false downstream authority.

## 3. Bound Execution

- [x] 3.1 Bind source, checkpoint `004`, historical checkpoint `005`, parent registration, native/corpus/probe context, seed schedule, size ceilings, and production isolation.
- [x] 3.2 Run py_compile, focused regressions, strict OpenSpec validation, and source-only preflight.
- [x] 3.3 Execute one 64-access replay collection and one full/scorer optimizer step each.
- [x] 3.4 Verify replay bindings, reproduction, hidden freeze, support, authority, and production/CommunicationMod isolation.
- [x] 3.5 Record the scorer-only go/no-go, commit compact evidence plus the reusable replay, and keep branch checkpoints local.
