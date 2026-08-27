# Replay distribution calibration registration review

## Verdict

`ready_for_single_execution`

This registration compares complete real production-r16 replay with a fresh
zero-epsilon frozen-r16 LightSTS collection inside fixed floor strata. It is a
descriptive calibration, not a mechanics-equivalence or policy-quality test.

## Source binding

- The runner, native module, item export, production-r16 shadow, and both real
  replay checkpoints were rehashed from their registered paths.
- A Windows Python native-load preflight succeeded without extra DLL
  directories. Adapter source identity is
  `e0d277e622e12a420ff5955dff55bea6ca5d1e15213cd8e6e5c354e017c46190`.
- The simulator remains at commit
  `7476a81954020087da31d41d16fddf475746ec2d` with known dirty source identity
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`.
  The runner rejects source-hash drift before environment construction.
- r14 and r15 are complete schema-v1 replay snapshots with 3,765 and 3,920
  transitions respectively. The loader accepted all 7,685 transitions before
  native loading.

## Cohort review

The simulator range `180000..180127` covers battle indices `0..12`, or 1,664
bounded profiles. A scan of tracked combat registrations found no use of either
endpoint; the immediately preceding fresh range ended at `178255`.

## Execution boundary

Execute once on CPU with no optimizer construction or update, no game or
CommunicationMod, and no retry, resume, seed replacement, or threshold tuning.
A technically ready report authorizes only mismatch interpretation and selection
of one separate evidence step.
