# Production r16 LightSTS successor analysis

## Decision

Retain production r16. The one-step LightSTS candidate is not eligible for production packaging, fresh real-replay confirmation, or a matched live gate.

## Technical result

- Runner verdict: `technical_smoke_ready`
- Source/prepared transitions: `65,463` / `75,700`
- Balanced strata: `18,925` prepared transitions for each battle index
- Complete profiles: `3,333`; excluded incomplete profiles/transitions: `1` / `100`, reason `decision_bound`
- Optimizer updates: `256`; parameter L2/max-absolute delta: `1.147764` / `0.018427`
- Held-out truncations and unsupported outcomes: `0`

The expected `baseline_loss_before_requested_battle` profiles were excluded symmetrically. There were `868` matched reachable held-out profiles.

## Held-out result

| Scope | Profiles | Reward delta | HP delta | Candidate-only wins | Parent-only wins |
|---|---:|---:|---:|---:|---:|
| Aggregate | 868 | -8.715 | -4.991 | 11 | 136 |
| Battle 0 | 256 | -13.511 | -8.063 | 4 | 73 |
| Battle 3 | 248 | -8.121 | -4.335 | 3 | 37 |
| Battle 6 | 210 | -4.482 | -2.952 | 3 | 10 |
| Battle 9 | 154 | -7.470 | -3.721 | 1 | 16 |
| Battles 6+9 | 364 | -5.746 | -3.277 | 4 | 26 |

The parent won `350/868` matched profiles and the candidate won `225/868`, a candidate victory-rate change of `-14.401` percentage points. Every registered performance condition failed; this is a strong no-go rather than a threshold-edge result.

## Interpretation

The exact production r16 parameters are compatible with LightSTS, but the current 256-update one-step recipe does not transfer safely from the earlier simulator-only r4 line. Mean TD loss (`2.259`) dominates the parent-anchor term (`0.457`), and the resulting parameter direction damages all four held-out battle strata.

Do not rerun this cohort, tune it after outcome access, package the candidate, or launch the game for it. The next bounded diagnostic should reuse the frozen parent-to-candidate direction at preregistered low interpolation coefficients in LightSTS; it can determine whether the direction is uniformly harmful or only the full update magnitude is excessive without spending another training run.
