## 1. Margin-Controlled Policy

- [x] 1.1 Implement fixed-temperature frozen-base residual card output with exact ordering preservation
- [x] 1.2 Stop checkpoint implementation as unnecessary after the terminal replay-gate failure
- [x] 1.3 Add entry margin, probability, ordering, and isolation regressions

## 2. Replay Gate

- [x] 2.1 Decode and bind the existing lossless replay without environment access
- [x] 2.2 Implement one-step function-space movement and coverage gates
- [x] 2.3 Run the fixed replay gate once and publish its terminal result

## 3. Bounded Training

- [x] 3.1 Do not implement candidate-only collection after replay-gate failure
- [x] 3.2 Do not add unused training regressions after replay-gate failure
- [x] 3.3 Do not execute training because the replay gate failed
- [x] 3.4 Do not execute terminal comparison because training did not start

## 4. Verification And Closeout

- [x] 4.1 Run focused pytest and strict OpenSpec verification without repeating the full repository gate
- [x] 4.2 Publish terminal evidence, archive the failed experiment without syncing a capability, commit, and push
