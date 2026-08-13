# Frozen residual card replay gate

## Result

The fixed replay gate failed. The experiment stops before native loading,
environment access, or on-policy training.

- Temperature: 4.0
- Fixed-probe rows: 175
- Unscaled median two-stage margin: 4.794915795
- Compressed-entry median two-stage margin: 1.198728949
- Compressed-entry greedy and full stage ordering preservation: exact
- Trainable parameters: 128 zero-initialized residual weights
- Frozen model bytes after update: exact
- Mean joint total variation from compressed entry: 0.002434321
- Required mean joint total variation: 0.004825590
- Action flips: 0
- Family flips: 0
- Pre/post clip gradient norm: 0.010244972 / 0.010244972

All identity, isolation, probability, coverage, gradient, and optimizer checks
passed. Only the preregistered function-movement threshold failed. The observed
movement retained about 40% of the historical full-model one-step movement,
below the required 80%.

## Decision

Do not run the four on-policy chunks, lower the threshold, retry the replay,
change temperature, or promote this parameterization. The report is a
mechanism no-go and makes no policy-quality claim.
