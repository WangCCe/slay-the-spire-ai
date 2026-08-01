# Project Direction

Last updated: 2026-08-02

## Current Phase

The first real Ironclad A0 validation victory is a completed historical
milestone. Run `1780479519.run` reached floor 51 with `victory=true`; the
evidence is recorded in `reports/gameplay_validation_mechanics_audit.md`.

The current objective is to reach an evidence-backed go/no-go decision for a
bounded non-combat RL training experiment covering card rewards, shops, events,
and routes. Another isolated victory or a healthy gameplay batch does not
complete this phase.

## Training Boundary

Formal non-combat RL training is not currently authorized. A training go means
that state, action, reward/outcome, known-propensity evidence, and fixed offline
evaluation contracts are all reproducible and independently checkable. It
authorizes only a separately reviewed bounded training proposal. It does not
authorize live policy promotion.

Bottled-style decisions remain an auxiliary oracle for comparison, labels, and
diagnostics. They are not reward, ground truth, or a mandatory policy target.

## Current Blocker

The active v2 known-propensity outcome-evidence study is stopped before study
start. Its r7 replacement qualification reached `launcher_verified` and
`runner_entered`, then failed at `source_validation_failed` before
`source_verified`, active-request publication, gameplay, or trajectory
collection. The root cause is not established.

The next authorized sequence is:

1. Diagnose the r7 source-validation failure offline from frozen artifacts and
   current source.
2. Specify and implement a regression-backed source fix in a separate OpenSpec
   change.
3. Run focused and registered test gates.
4. Permit at most one fresh no-action replacement qualification.
5. Resume the 24-by-25 evidence study only if that qualification succeeds and
   its independent verifier passes.
6. Use the completed evidence and OPE gates to decide whether to propose a
   bounded non-combat RL training experiment.

## Work Lanes

The primary lane is non-combat RL readiness and its evidence pipeline.

Live gameplay is a maintenance and registered-evaluation lane only. Launch it
for a crash, stuck state, repeated A-class simulator/mechanics defect, or an
explicitly registered RL qualification/evaluation gate. Do not run automatic
five-game batches merely to search for another heuristic patch.

Defer broad strategy tuning, Bottled-driven live behavior, reward redesign,
formal training, and live promotion until their evidence gates and separate
OpenSpec changes authorize them.

## Engineering Rules

- Route proposal, contract, or capability work through repository OpenSpec.
- Begin with read-only evidence; require a failing regression before a behavior
  fix.
- Use focused pytest and the repository test gates. Do not substitute an
  unregistered raw full-suite run for the commit gate.
- Keep changes cohesive and preserve unrelated local artifacts.
- Stop when evidence is ambiguous rather than tuning around it.

Historical reports and archived changes retain the objectives and authority
boundaries that applied when they were written. This document is the canonical
source for the current project phase.
