# Production r16 action-margin drift analysis

## Decision

Replace the current one-step recipe with a frozen-parent end-turn margin guard before any further training. This audit does not authorize packaging, gameplay, or a policy-quality claim.

## Technical result

- Audit verdict: `action_margin_drift_ready`; blockers: none
- Registered/initialized complete profiles: `1,024` / `851`
- Accepted transitions: `16,527`
- Expected initialization failures: `170` before the requested battle and `3` terminated baseline runs
- Unsupported transitions: `0`

## Drift result

| Candidate | All action flips | Parent play-card flips | Play-card to end-turn | Mean parent margin on flips |
|---|---:|---:|---:|---:|
| alpha 0.05 | 229 / 16,527 (1.39%) | 207 / 4,618 (4.48%) | 134 | 0.0227 |
| alpha 0.10 | 413 / 16,527 (2.50%) | 373 / 4,618 (8.08%) | 246 | 0.0435 |
| alpha 0.20 | 726 / 16,527 (4.39%) | 651 / 4,618 (14.10%) | 434 | 0.0781 |
| full candidate | 1,852 / 16,527 (11.21%) | 1,614 / 4,618 (34.95%) | 1,027 | 0.1883 |

The parent margin across all multi-legal-action transitions has mean `1.056`, median `0.737`, and p10 `0.105`. At alpha `0.05`, flipped states have mean margin only `0.0227` and median `0.0204`. The earliest policy changes therefore occur at fragile ranking boundaries even though the existing Q-value MSE anchor is active.

Alpha `0.05` action-flip rates are `1.41%`, `1.41%`, `1.37%`, and `1.34%` at battles `0`, `3`, `6`, and `9`. The failure is not localized to one registered battle stratum. It is concentrated by action family: parent play-card states flip `4.48%`, compared with `0.02%` for parent end-turn states.

## Next objective

Add an optional loss over complete legal transitions where the frozen parent selects a non-end-turn action and end turn is legal. Preserve the parent's positive selected-action-versus-end-turn margin, clipped by a preregistered cap, while retaining the existing TD and Q-anchor losses. Default the guard off so previous registrations remain reproducible.

The next bounded experiment must use fresh training and evaluation seeds. Its first gate remains LightSTS matched evaluation; no production packaging or game launch follows unless the new direction clears that gate.
