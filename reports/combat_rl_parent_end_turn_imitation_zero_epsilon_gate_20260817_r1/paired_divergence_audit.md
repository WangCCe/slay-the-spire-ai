# Paired Divergence Audit

## Scope

This audit compares the first different action at a shared normalized combat
state for the eight non-tied seed pairs in the matched gate. Duplicate card
positions are ignored: actions are compared by card identity, upgrade count,
and target monster identity and HP rather than `card_index`.

The trace was split into 20 games by floor reset. Candidate and parent segments
were then paired in the preregistered seed order. The candidate archive contains
7,282 decision rows and the parent archive contains 7,532.

## First Substantive Divergence

| Game | Seed | Floor delta | State | Candidate | Parent |
| ---: | --- | ---: | --- | --- | --- |
| 1 | `6F2B8000E3625` | +1 | F5 T1, 57 HP, 0 energy | EndTurn | Fruit Juice |
| 2 | `FC84DCDC60E93` | -8 | F5 T2, 59 HP, 3 energy | Strike -> Fungi Beast (28) | Anger -> Fungi Beast (28) |
| 5 | `F89F7434424E2` | +17 | F2 T1, 80 HP, 3 energy | Strike -> defensive Louse (15) | Strike -> normal Louse (13) |
| 8 | `24FB524D61137` | -5 | F1 T1, 80 HP, 3 energy | Dark Shackles -> defensive Louse (12) | Strike -> defensive Louse (11) |
| 14 | `B46C324873D4D` | -15 | F2 T3, 67 HP, 3 energy | Bash -> Jaw Worm (15) | Strike -> Jaw Worm (15) |
| 15 | `FC8BF2ECAC156` | +12 | F5 T3, 59 HP, 3 energy | Bash -> Acid Slime (23) | Strike -> Acid Slime (23) |
| 16 | `56412D27132A5` | -11 | F11 T1, 44 HP, 3 energy | Bash -> normal Louse (15) | Headbutt -> normal Louse (15) |
| 18 | `2D1E61AFB14D6` | -3 | F1 T2, 80 HP, 3 energy | Strike -> normal Louse (15) | Bash -> normal Louse (15) |

All 16 compared rows were emitted by `combat_rl`; no guard or fallback source
appears at these first divergences.

## Finding

The five candidate-loss pairs do not share an actionable EndTurn failure:

- All five first divergences are card-versus-card choices; none is EndTurn or a
  potion decision.
- No exact candidate-versus-parent card pair repeats across the five losses.
- Bash-versus-Strike is not directional evidence. Candidate Bash precedes both
  a 15-floor loss and a 12-floor gain, while candidate Strike versus parent Bash
  precedes a 3-floor loss.
- The largest candidate gain begins with a target-only difference, which also
  shows that small policy-order changes can produce large trajectory variance.

The targeted objective moved positive-energy EndTurn frequency in the intended
direction, but its remaining trajectory effects are diffuse card-ranking and
target-ranking changes. This cohort does not justify another weight adjustment
or a gameplay fix.

## Decision

Keep the promoted parent in production. Preserve the candidate and its first
real victory as milestone evidence, but stop this direct targeted-imitation
recipe. Do not rerun the cohort or start another gameplay gate from this audit.

The next bounded model experiment should first scan parent-to-candidate
checkpoint interpolation offline. Only an interpolation that retains the
candidate's EndTurn correction while improving parent agreement and value loss
may receive a fresh matched gameplay gate.
