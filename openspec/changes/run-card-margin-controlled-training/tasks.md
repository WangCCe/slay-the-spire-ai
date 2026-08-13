## 1. Margin-Controlled Policy

- [x] 1.1 Implement fixed-temperature frozen-base residual card output with exact ordering preservation
- [ ] 1.2 Implement source-bound residual checkpoint and fresh optimizer restoration
- [x] 1.3 Add entry margin, probability, ordering, and isolation regressions

## 2. Replay Gate

- [x] 2.1 Decode and bind the existing lossless replay without environment access
- [x] 2.2 Implement one-step function-space movement and coverage gates
- [ ] 2.3 Run the fixed replay gate once and publish its terminal result

## 3. Bounded Training

- [ ] 3.1 Implement candidate-only residual collection, update, fixed budget, and rollback
- [ ] 3.2 Add focused chunk, censor, checkpoint, and terminal comparison regressions
- [ ] 3.3 Execute exactly four fixed training chunks only after replay gate pass
- [ ] 3.4 Run the fixed terminal native comparison if all training chunks pass

## 4. Verification And Closeout

- [ ] 4.1 Run focused pytest and strict OpenSpec verification without repeating the full repository gate
- [ ] 4.2 Publish terminal evidence, sync/archive the change, commit, and push
