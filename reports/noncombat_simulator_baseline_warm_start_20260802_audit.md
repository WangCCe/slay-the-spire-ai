# Non-Combat Simulator Baseline Warm-Start Final Audit

## Decision

The one registered primary execution and one identical replay are structurally
valid and canonically identical. The result is a valid negative:
`study_valid_without_baseline_floor`. It does not authorize another training
run, formal RL, simulator RL, live gameplay, live loading, OPE,
qualification, promotion, or deployment.

## Registered execution

- Registration SHA-256:
  `2815274e61c7d4ad8e553190ca234d6303457d9543cd63def541637729340a7a`.
- Train cohort: `4000..4031`, 32 seeds, 1,291 demonstration rows.
- Validation cohort: `5000..5015`, 16 seeds, 705 demonstration rows.
- Final cohort: `6000..6031`, 32 seeds, untouched.
- Training: fixed `candidate-ranker-mlp-v1`, 10 Adam epochs.
- Primary/replay execution SHA-256:
  `a982a3242d643fd505b0a476249ff1f542cb92f395149db43551551c7dae2dc4`.
- Primary/replay bounded execution time: 428.27 / 431.49 seconds.

## Validation result

| Check | Value | Threshold | Result |
| --- | ---: | ---: | --- |
| Overall action agreement | 0.790071 | >= 0.80 | fail |
| Macro-category agreement | 0.786065 | >= 0.75 | pass |
| Minimum category agreement | 0.640000 | >= 0.60 | pass |
| Mean floor difference | -4.687500 | >= -1.0 | fail |
| Floor difference CI lower | -11.689062 | >= -3.0 | fail |

The candidate averaged floor 20.0 and native SimpleAgent averaged 24.6875.
Each policy won one of 16 validation runs. The paired 95% interval was
`[-11.6890625, 2.5]`. Final evaluation was correctly skipped.

Teacher agreement by category was:

| Category | Rows | Agreement |
| --- | ---: | ---: |
| card_reward | 175 | 0.640000 |
| event | 69 | 0.927536 |
| route | 383 | 0.845953 |
| shop | 78 | 0.730769 |

## Read-only audit

The final audit reloaded and rehashed the complete artifact directory, then
revalidated all 1,996 train/validation rows. It confirmed:

- train, validation, final, and every excluded prior seed are mutually
  isolated as registered;
- final-test demonstrations and trajectories are both null;
- every row uses native SimpleAgent as auxiliary teacher, maps its target to
  exactly one current action, retains every ordered candidate, and retains one
  matching policy view and hash per candidate;
- all 1,996 row provenance values match the registered adapter provenance;
- the trained model remained frozen during rollout and its hashes match the
  model and metrics artifacts;
- the validation gate recomputes byte-for-byte to the published gate;
- primary and replay execution hashes are identical;
- the managed inventory is exactly six canonical files plus the separate
  noncanonical execution journal; and
- every authority flag is false.

The 320,965,025-byte canonical demonstration corpus remains in the local
canonical directory and is published in Git as a deterministic 13,416,133-byte
gzip archive. Its archive manifest binds both compressed and raw hashes; after
restoration the raw SHA-256 is exactly the value expected by the canonical
manifest. This avoids an unavailable Git LFS object on the public fork while
keeping the evidence recoverable and byte-verifiable.

## Verification

- Focused pure warm-start tests: `34 passed in 42.73s`.
- Native compatibility and warm-start tests: `4 passed in 24.28s`.
- Repository commit gate: `3239 passed, 11 skipped in 226.69s`; runner total
  `230.10s`.
- Canonical artifact rehash and semantic validation: pass, five manifest-bound
  payload hashes, all authority false.
- Python compilation: pass.
- Strict OpenSpec validation: pass.
- Post-study process counts: game/Java `0`, Python `0`.
- CommunicationMod SHA-256 remained
  `7ec79e01f9293a19ead3c59a26b18bb75ef900afa3dbe45d657769fe46061862`.
- Checkpoint count remained `208`; the sorted metadata inventory SHA-256
  remained
  `2310129f2d0589b088ef27dd30d17f11d03af03bfd190b15f7e16bd1513ad1ef`.
- No live game or unbounded raw full suite was launched.

## Next boundary

Do not tune this model or reuse this execution as a selection loop. The next
work is a read-only first-divergence/floor-deficit audit over the fixed
validation artifacts. A different warm-start or data-aggregation method
requires a separate OpenSpec proposal after that attribution. Formal
non-combat RL remains blocked on demonstrated baseline competence.
