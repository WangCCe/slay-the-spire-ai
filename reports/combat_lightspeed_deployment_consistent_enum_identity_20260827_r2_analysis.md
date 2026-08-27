# Fresh enum-v1 encounter identity confirmation

## Verdict

`technical_pass_policy_fail_reject_enum_identity_retain_r16`

The corrected technical gate passed, but the fresh policy effect did not meet the pre-registered reward threshold and remained below r16. Retain r16, do not run a larger enum confirmation, and do not tune or repeat this cohort.

## Technical result

- Both arms: `technical_smoke_ready`, 51,485 source transitions, 67,172 prepared transitions, and 256 optimizer updates.
- Scalar rewards, action families, outcomes, replay preparation, behavior telemetry, and frozen-parent evaluation rows matched.
- Encoded transition hashes differed as pre-registered because enum-v1 adds observation columns.
- Parent migration had zero action mismatches, `7.629e-6` maximum Q delta within the registered `1e-5` float32 tolerance, and exactly zero inserted-column magnitude.
- Both manifests verified; neither arm reported blockers, unexpected initialization failures, or unsupported successors.

## Policy result

Enum-v1 minus no-identity control over 835 matched terminal profiles:

| Battle | Profiles | Reward delta | HP delta | Enum-only wins | Control-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 256 | +0.0398 | +0.0625 | 0 | 0 |
| 3 | 246 | -0.0326 | +0.0325 | 0 | 0 |
| 6 | 198 | -0.2725 | +0.2273 | 2 | 5 |
| 9 | 135 | +1.0119 | +0.6444 | 3 | 0 |
| **All** | **835** | **+0.1016** | **+0.1868** | **5** | **5** |

The combined battle-6/9 reward delta was positive at `+0.2482`, but aggregate reward missed the required `> +0.25`. Enum-v1 minus r16 was negative: reward `-0.2396`, HP `-0.1749`, and victories `10:15`.

## Interpretation

The r1 direct gain of `+0.4075` reward did not reproduce at the registered magnitude on fresh seeds. Enum-v1 still helps battle 9, but battle 6 moved negative and aggregate improvement shrank to `+0.1016`. Together with the rejected proxy-aware anchor ablation, this closes the two isolated structural hypotheses under the current guarded one-step recipe.

The next useful work is a read-only interaction audit of replay targets, anchor loss, replacement density, and battle-stratum data quality before fitting another candidate. No gameplay, CommunicationMod, packaging, qualification, or promotion is authorized.
