## 1. Regression Boundary

- [x] 1.1 Add focused RED coverage for exact zero-entry parent equivalence, frozen parent parameters, and legal-action masking
- [x] 1.2 Add focused RED coverage for closed-gate abstention, open-gate bounded correction, and residual-only gradients
- [x] 1.3 Add focused RED coverage for deterministic checkpoint and optimizer round trip

## 2. Adapter Implementation

- [x] 2.1 Implement the experiment-only frozen-parent abstaining residual adapter with fixed configuration
- [x] 2.2 Implement correction-only loss and optimizer helpers for direct and changed candidate-decision spans
- [x] 2.3 Implement non-production artifact serialization, identity validation, and exact restoration

## 3. Mechanism Smoke

- [x] 3.1 Implement a deterministic synthetic direct/changed training smoke without gameplay or CommunicationMod
- [x] 3.2 Publish mechanism telemetry for gate classes, correction behavior, parent immutability, bounds, and reproducibility
- [x] 3.3 Reject the closed R1 corpus as optimizer input and preserve it as read-only motivation only

## 4. Verification And Closeout

- [x] 4.1 Run focused pytest with a scoped system-temp basetemp and run the isolated mechanism smoke twice
- [x] 4.2 Run strict OpenSpec validation, diff checks, and the optimized commit gate at the completed capability boundary
- [ ] 4.3 Commit and push the experiment implementation without production weights or raw replay artifacts
- [ ] 4.4 On mechanism pass, prepare a separate immutable fresh-cohort registration before any live collection or policy-bearing fit
