# Non-combat OPE estimator calibration

Status: PASS

## Source hashes

- estimator: `39e4b981348918ec8ab3e18c23f62f261be6a905d4b4c9826cfc3cae7e8bf370`
- calibration: `ff150e326932d5130b99e4fcb97ff9c285e0a9688938c1db3c618a53afb602c6`
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
