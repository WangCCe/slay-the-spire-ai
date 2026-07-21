# Adaptive Elite Routing Live Postmortem - 2026-07-22

## Decision

The bounded adaptive cohort proved that the integration, observability, and
conservative recovery paths can run through ten games without training or a
runtime failure. It did not produce enough actual adaptive treatment to
evaluate optional-elite efficacy. Keep conservative as the live mode, do not
tune and rerun this cohort, and do not promote adaptive to a larger live
validation.

The next route-related step should be a read-only opportunity audit, not a
threshold change. The outer `victory=true` objective should continue under the
conservative live configuration while adaptive policy work remains paused.

## Evidence Scope

- Qualification report:
  `reports/adaptive_elite_routing_live_qualification_20260721.md`
- Ten Ironclad A0 evaluation runs, no training, run ids `1784650652` through
  `1784651443` as enumerated in the qualification report.
- Dedicated AI logs:
  `ai_debug_adaptive_20260721.log.1` followed by
  `ai_debug_adaptive_20260721.log`.
- Dedicated decision trace:
  `ai_decision_trace_adaptive_20260721.jsonl`.
- Dedicated sim-divergence trace:
  `sim_divergence_trace_adaptive_20260721.jsonl`.
- The route analysis read log segments chronologically, assigned records to
  the active `Starting game #N` boundary, and deduplicated on
  `(game_number, complete ADAPTIVE_ROUTE payload)`.

## Cohort Comparison

| Mode | Runs | Average floor | Maximum floor | Act 2 boss reaches | `E` nodes | Elite-death runs | Victories |
|---|---:|---:|---:|---:|---:|---:|---:|
| conservative, 2026-07-20 | 10 | 24.2 | 33 | 3 | 0 | 0 | 0 |
| aggressive, 2026-07-20 | 10 | 18.9 | 31 | 0 | 9 | 5 | 0 |
| adaptive, 2026-07-21/22 | 10 | 18.5 | 33 | 1 | 1 | 1 | 0 |

At face value adaptive combined conservative-level elite exposure with
aggressive-level average floor. That comparison is descriptive only. The
cohorts are unpaired, and the adaptive cohort did not realize an optional-elite
route action, so the floor difference cannot be attributed causally to the
adaptive policy.

## Activation Funnel

The logs contain `346` structured route rows but only `173` distinct payloads.
Every distinct payload appears exactly twice because the same MAP state was
committed through two Communication Mod callbacks. Raw row counts therefore
overstate the number of independent route states by exactly two in this cohort.

There were `58` distinct complete-candidate states with conservative
`elite_count=0` and aggressive `added_elites=1`:

| Act / disposition | Distinct states | Share of Act 1 zero-vs-one states |
|---|---:|---:|
| Act 1: `deck_not_ready` | 37 | 68.5% |
| Act 1: `hp_below_relative_floor` | 11 | 20.4% |
| Act 1: `hp_below_absolute_floor` | 5 | 9.3% |
| Act 1: `optional_elite_allowed` | 1 | 1.9% |
| Act 2: `later_act_optional_elite` | 4 | n/a |

Thus `53 / 54` Act 1 zero-vs-one states were denied. Deck readiness was the
dominant gate, followed by HP. This describes policy activation under the
observed states; it does not prove that either threshold should be relaxed.

## Treatment Uptake

The sole allowed state occurred in game 1 at floor 7:

- HP `69/80` (`86.25%`), deck readiness `5`, one usable potion, relic support
  `0`;
- conservative symbols `M/T/?/$/R/?/M/R`;
- aggressive symbols `M/T/?/$/R/M/E/R`;
- optional budget `1`, selected `aggressive`.

Both candidates selected the same immediate `M` branch. The decision trace
records choice `0`, node `M@(2,7)`, while the only other advertised next node
was `?@(3,7)`. On floor 8 HP had fallen to `59/80` (`73.75%`), so the relative
HP gate restored conservative routing before the candidate paths reached their
symbol-level divergence or the planned floor-14 elite.

The cohort therefore recorded no realized optional elite. Its only `E` was a
forced conservative route in game 6, which ended at floor 11 against
`3 Sentries`. The observed `1 / 1` elite fatality ratio fails the registered
gate, but it is not evidence that the optional-elite selector itself is unsafe.

## Integration Findings

What worked:

- Ten games completed and stopped at the exact registered boundary.
- Evaluation mode left all checkpoint metadata unchanged.
- Persistent Communication Mod configuration was restored byte-for-byte to
  conservative.
- All `2,768` decision-trace rows were valid JSONL.
- Structured route records retained complete candidate and reason evidence.
- Four distinct Act 2 states in game 5 exercised
  `candidate_generation_failed`; each committed a validated conservative
  fallback, and the run continued to floor 22.
- The single sim-divergence row was an isolated Looter escape/block transition,
  not a repeated causal mechanics cluster.

What the evidence did not establish:

- optional-elite reward or survival impact;
- a paired floor or boss-reach comparison against conservative;
- whether deck or HP thresholds are incorrectly calibrated;
- whether an aggressive candidate would remain attractive at the irreversible
  route-divergence point;
- a victory improvement.

## Root Cause Classification

The qualification failure is primarily **insufficient treatment uptake**, not
an integration failure and not a demonstrated unsafe optional-elite policy.
The design required live elite exposure for promotion, but the observed state
distribution plus fail-closed gates produced no optional elite encounter.

The low average floor remains important operationally, but it is not a clean
adaptive-policy effect: all committed immediate actions were conservative or
conservative-equivalent, including the single temporary aggressive selection.
Combat, rewards, events, shops, seeds, and other unpaired run variance remain
plausible causes.

## Recommended Next Work

1. Keep `conservative` as the persistent live route mode and leave adaptive
   non-default. Do not rerun these ten games after threshold tuning.
2. Propose a read-only adaptive-route opportunity audit. It should join route
   records to decision-trace map coordinates, collapse repeated callbacks,
   identify the first coordinate where candidates actually diverge, and report
   whether an allowed decision survives until that point.
3. Evaluate the `54` Act 1 zero-vs-one states offline against explicit route
   outcomes or an independent policy oracle before proposing any threshold or
   commitment change. The current funnel alone is not sufficient evidence for
   relaxation.
4. Pre-register treatment-uptake evidence for any future live cohort: count
   unique aggressive selections, immediate coordinate differences, selections
   later revoked, and optional elites actually reached. Define thresholds only
   in a new OpenSpec change after the offline audit.
5. Resume bounded conservative gameplay evidence for the outer victory goal.
   Route work should not displace higher-confidence combat or non-combat
   decision findings while adaptive has no demonstrated live treatment.

No gameplay code, route threshold, default, training behavior, checkpoint, or
persistent live configuration is changed by this postmortem.
