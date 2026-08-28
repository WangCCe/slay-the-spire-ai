# LightSTS real-context matching POC (2026-08-29)

## Decision

Do not build arbitrary real-combat-state import yet. The expanded paired-return
corpus already contains enough overlapping progression contexts for a lower-risk
next step: collect a progression-balanced late-floor supplement and evaluate it
with preregistered post-stratification weights.

Do not run another classifier, residual-head, loss, or threshold variant on the
current corpus. Fresh evaluation support is too sparse to distinguish a policy
failure from a progression-context failure, especially after floor 27.

## Bound inputs

- Source commit: `2d4ea530f2f29719de8b0b5974bf70369d91b775`
- Real r14 replay: 3,765 complete transitions, SHA-256
  `eed11099d1b8d35baa8ce0ccbf87efb6fb4a864e6fe6246837b0cac91c505014`
- Real r15 replay: 3,920 complete transitions, SHA-256
  `67c3a49fbb2094d20793214c0a4a294684054eb6f4a24ac59573fab29c39a2dd`
- Expanded training corpus: 6,473 paired-return rows, SHA-256
  `90f3e83763f2591065380e89b24ebbedc7bbc3ef529a749b0cbb54a2dab2fa1f`
- Expanded fresh evaluation corpus: 1,643 paired-return rows, SHA-256
  `028d51871b12fd509b87b6d45adb161b399a29c34782b30b28f66c0a97e48e58`

The two real checkpoints contribute 7,685 complete production-r16 transitions.
The simulator corpus is intentionally narrower: it retains states where the
parent selected end turn and the deployment guard supplied an alternative.

## Method

Rows were assigned to exact post-stratification cells using:

1. canonical floor stratum;
2. occupied potion-slot count;
3. occupied relic-slot count; and
4. player-HP quartile.

Each simulator cell received the corresponding real-to-simulator density ratio.
Simulator cells absent from real replay received zero weight. This is a support
and sampling audit only: it does not estimate policy quality, fit a model, load a
native module, run the game, or perform OPE.

## Aggregate results

| Partition | Rows | Real mass covered | Sim mass retained | Weighted ESS | ESS share |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 6,473 | 88.24% | 82.64% | 601.9 | 9.30% |
| Fresh evaluation | 1,643 | 72.93% | 82.53% | 276.4 | 16.82% |

| Metric | Train raw SMD | Train weighted SMD | Eval raw SMD | Eval weighted SMD |
| --- | ---: | ---: | ---: | ---: |
| Player HP ratio | 0.818 | 0.112 | 0.830 | 0.322 |
| Potion occupied slots | 0.821 | 0.014 | 0.809 | 0.059 |
| Relic occupied slots | 0.352 | 0.115 | 0.346 | 0.164 |
| Floor ratio | 0.728 | 0.299 | 0.687 | 0.390 |
| Hand occupied slots | 0.386 | 0.292 | 0.367 | 0.355 |
| Legal action count | 0.488 | 0.275 | 0.462 | 0.255 |

Inventory and HP matching materially reduce the dominant discrepancy without
discarding most simulator rows. The remaining floor, hand, and legal-action
differences show that weighting alone is not a sufficient release gate.

## Floor support

Fresh evaluation is the binding constraint:

| Floor stratum | Real rows | Eval rows | Real context mass covered |
| --- | ---: | ---: | ---: |
| 00..05 | 1,197 | 578 | 89.72% |
| 06..10 | 774 | 268 | 80.62% |
| 11..17 | 2,873 | 422 | 71.77% |
| 18..22 | 1,418 | 275 | 91.61% |
| 23..27 | 433 | 82 | 72.52% |
| 28..34 | 859 | 18 | 27.01% |

The combined simulator corpus has only 91 rows at floors 28..34 and one row at
35..39. A weighted policy result on this support would be dominated by a small
number of reusable states and should not qualify a candidate.

## Next evidence step

Run a small native diagnostic over later battle indices to identify which
profiles produce floors 23..34 and the missing low-potion, higher-relic, lower-HP
cells. Then preregister one supplemental collection with disjoint fit and fresh
evaluation seeds. The collection should improve late-floor row count and real
context coverage before any additional fitting is allowed.

Build exact real-state initialization only if the targeted generator cannot
reach those cells without severe support collapse. Starting with that bridge now
would add substantial mechanics surface before the cheaper sampling hypothesis
has been falsified.

## Limitations

- Exact-cell reweighting balances observed encoder context, not encounter
  identity, draw-pile order, powers, latent run history, or counterfactual return.
- Real replay includes every retained combat transition while the paired corpus
  includes guard-intervention states. Coverage therefore answers whether the
  training target states can resemble real contexts, not whether both sources
  have the same unconditional transition distribution.
- The POC reuses existing artifacts and makes no causal, qualification,
  promotion, or gameplay claim.
