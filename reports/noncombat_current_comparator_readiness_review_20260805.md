# Post-Repair Current Comparator Readiness Review

Date: 2026-08-05

## Decision

The repaired Current bridge is ready for one **proposal-only**
post-final-repair baseline replication. It is not ready for direct execution.
The existing main specification still forbids a replacement after the blocked
integrated study, so the next change must explicitly revise that over-broad
anti-retry boundary and define a distinct versioned study. It must not reopen,
rename, or reuse the consumed study.

The revision may authorize consideration of exactly one new preregistration
only. Native loading, simulator construction, seed access, cohort execution,
gameplay, model fitting, training, qualification, loading, and promotion remain
unauthorized. Formal non-combat RL remains `no_go`: no credible Current floor
has been demonstrated and target-supported outcome evidence remains
source-incomparable with zero supported victories.

## Why A Distinct Replication Is Defensible

The consumed study stopped before a complete canary because the offline bridge
could not hydrate the exact metadata representation of `Injury`. That is a
measurement compatibility failure, not a completed policy-quality result. Its
18 retained rows and observed partial means remain descriptive only and are not
used to lower a threshold, choose a policy, or select a cohort.

Since preregistration commit `720f41b07`, the registered Current policy,
event-semantics, adapter, and study-runner sources are unchanged. Among those
bound files, only
`analysis_scripts/noncombat_current_policy_simulator_bridge.py` changed. The
change is the closed 20-ID empty-cost unplayable metadata repair; Current's
heuristics, priorities, action path, first-candidate control, numeric gates,
bootstrap contract, and episode limits did not change.

Current source identities at review HEAD `5a4e8b305` include:

- bridge: 102,473 bytes, SHA-256
  `35041bf1b3c219411d7b121d8a2e700e19604de61e45cfda1b44d1a48fa8f99f`;
- existing study runner: SHA-256
  `0dc9c0b9f8acdbece7541e835a05c58cfd3317035ce0ed70227b5988960048a1`;
- simulator adapter: SHA-256
  `3045281cf592aaee82de1e2972a5205297ff3f371c4ce0aa47d8cb539b66f690`.

The source-only regression selection for the bridge, study, adapter, event
observation, reachable event surface, and native-compatibility contract passed
`278 passed, 5 skipped in 44.49s`. It loaded no native module and accessed no
simulator seed.

## Closure Evidence

The known deterministic compatibility surfaces are closed at their stated
source and regression boundaries:

| Surface | Current evidence |
| --- | --- |
| Reachable events | All 48 reachable Ironclad A0 event-option targets are partitioned into 25 explicit rules and 23 audited generic defaults; `Scrap Ooze` is covered. |
| Shop remove sentinel | `remove_cost == -1` is accepted only when no removal candidate exists; inconsistent negatives fail closed. |
| Sold shop inventory | Exactly `price == -1` sold slots are omitted while original slots, unaffordable inventory, and Courier replacements are preserved. |
| Remaining shop support | Courier restock states fail closed as `unsupported_shop_courier_restock_semantics`; impossible Sozu/full-belt potion purchases are omitted. |
| Candidate schema | Candidate-side `action_type` is not required; evaluator action metadata remains validated. |
| Potion identity | All 42 non-empty potion identities are covered, including three exact stable-ID aliases. |
| Card and relic identity | All 370 card display names are covered; 15 relic aliases and two metadata-absent fallback relics are closed by stable ID. |
| Card cost | Twenty exact empty-cost `Unplayable.` identities hydrate to cost `-2`; three Wish option identities and all field drift remain fail closed. |

This is strong static closure, not proof that a fresh trajectory cannot reveal
another unsupported state. A new structural blocker therefore remains a real
risk and must have a terminal consequence.

## Anti-Retry Revision

The current rule correctly makes each registered execution identity terminal,
but it incorrectly treats an incomplete measurement-pipeline failure as
equivalent to a structurally complete quality-gate failure. The successor
contract must preserve the former rule while narrowing the latter:

1. A complete, structurally valid canary or holdout that fails a numeric,
   coverage, support, or bootstrap gate is terminal. No successor, tuning, or
   replacement cohort follows.
2. A pre-quality structural blocker may justify a distinct successor only when
   the exact defect has a source-complete audit and red/green regression, the
   policy and weak control are unchanged, thresholds are unchanged or stricter,
   and every consumed seed is excluded.
3. The present repair chain qualifies for one final successor under rule 2.
   Any structural blocker, interruption after start, canary stop, or holdout
   failure in that successor ends the Current-baseline lane. It must not trigger
   another bridge-fix-and-rerun cycle.
4. The old registration, authorization, journal, 18 rows, metrics, report, and
   untouched holdout remain immutable and cannot contribute a passing row.

## Required Successor Contract

The next OpenSpec change should be named
`add-post-final-repair-current-baseline-replication` and keep the existing
study's evidence design unless a term becomes stricter:

- primary comparator: frozen Current;
- paired weak control: deterministic first candidate;
- excluded references: SimpleAgent and Bottled provide no action, label,
  fallback, reward, or quality gate;
- cohorts: 16 canary seeds and 64 holdout seeds selected deterministically from
  a regenerated tracked-seed inventory after the source-only implementation
  commit; every historical and consumed seed is excluded;
- replay and limits: exactly two independent replays per policy and seed, at
  most 500 target decisions, 600 seconds for canary, and 1,800 seconds total;
- canary gates: Current mean floor at least 15, paired mean at least 0, all four
  categories covered, at most one declared-support row per policy, and zero
  unexpected failures;
- holdout gates: Current mean floor at least 18, absolute 95% bootstrap lower
  bound at least 15, paired mean at least 3, paired 95% bootstrap lower bound
  greater than 0, all categories covered, at most three declared-support rows
  per policy, and zero unexpected failures;
- support treatment: exact Courier rows stay in every denominator as
  non-victories at the last supported floor; no row may be dropped, replaced,
  retried, or converted to a supported-only headline;
- isolation: the holdout is inaccessible unless the complete canary passes;
- lifecycle: clean pushed preregistration, a separate exact execution
  authorization, durable started journal, atomic canonical publication, and
  no repair, retry, seed replacement, threshold change, or parameter override.

The tracked inventory at review HEAD contains 2,111 excluded seeds and more
than one untouched contiguous 80-seed window. This review did not select, bind,
reserve, or access any specific future cohort; selection belongs to the later
pushed preregistration.

## Formal RL Boundary

Even a successful replication would close only the Current baseline-policy
domain. Target-supported outcome support remains an independent blocker, and
the state-conditioned ranker/input capabilities remain source-only and
unintegrated. No r3 simulator experiment or formal non-combat RL proposal may
be inferred from this readiness decision.

## Authority

- `baseline_replication_proposal_consideration = true`
- `baseline_floor_authorized = false`
- `cohort_selection_authorized = false`
- `execution_authorized = false`
- `formal_rl_authorized = false`
- `fresh_evidence_authorized = false`
- `gameplay_authorized = false`
- `model_fitting_authorized = false`
- `native_loading_authorized = false`
- `seed_access_authorized = false`
- `training_authorized = false`
- `promotion_authorized = false`
