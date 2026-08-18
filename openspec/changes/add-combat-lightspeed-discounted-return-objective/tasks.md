## 1. Trajectory Targets

- [x] 1.1 Preserve source profile and decision identity through simulator replay collection
- [x] 1.2 Add complete-trajectory filtering with explicit incomplete-profile evidence
- [x] 1.3 Add deterministic discounted episode-return transformation and keep one-step TD as default
- [x] 1.4 Bind target configuration, trajectory evidence, source identity, and reward summaries in reports and checkpoints

## 2. Verification

- [x] 2.1 Cover backward return math, terminal handling, incomplete exclusion, source matching, and default compatibility
- [x] 2.2 Run focused simulator tests and strict OpenSpec validation

## 3. Fresh Experiment

- [x] 3.1 Register fresh matched one-step and discounted-return arms on identical complete trajectories
- [ ] 3.2 Run each arm once, apply aggregate and battle-index guardrails, and record the retained parent decision
- [ ] 3.3 Sync the main spec, archive the completed change, commit the evidence, and push master
