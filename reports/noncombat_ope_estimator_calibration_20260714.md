# Non-combat OPE estimator calibration

Status: PASS

## Source hashes

- estimator: `57187791648e6e87b37db8043b07570a37642fa010f50e2231577e1a88d752ea`
- calibration: `3c43f7d127af9a58ddcaffc572cd324823195cbbb02634cc9c20d8c24bd35d8c`
- configuration: `3fe9e909c9966d716f8e72b96c25e24067ab6ef655c37de6067f15bdddb40340`
- fixtures: `d45744bccd4322b6875772718c7895ebc9d9fc0d96ec1f9bfafade4c4aead0ea`

## Fixed coverage experiment

- datasets: 200
- trajectories per dataset: 200
- bootstrap replicates: 500
- target coverage: 0.965
- uplift coverage: 0.955
- target mean bias: 0.0016027424956265555
- uplift mean bias: 0.0012777424956265555

## Blockers

- none

## Limitations

- Synthetic calibration validates estimator behavior, not policy quality.
- Calibration does not authorize causal claims, training, or live promotion.
