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
start. R7 remains immutable and retired after `source_validation_failed`; its
raw-first source fix, focused regressions, registered commit gate, and
OpenSpec archive are complete.

The separately reviewed r8 replacement reached `source_verified`, then failed
at `request_validation_failed` before active request publication, gameplay, or
trajectory collection. The immutable chain proves at least one live boundary;
the same-session operator journal records one issued invocation but does not
independently prove the exact count. Its standalone verifier and independent
closeout passed, CommunicationMod and protected inventories were restored
exactly, target processes are zero, and the registered study root remains
absent. R8 is consumed and permanently retired; it cannot be retried or used
to prepare r9 under its amendment.

The current blocker is a separate regression-backed diagnosis of r8 request
validation. The closeout does not establish the root cause, so no replacement
qualification identity or live invocation is currently authorized.

The next authorized sequence is:

1. Archive the completed r8 amendment while preserving its external root and
   closeout byte-for-byte.
2. Open a separate, offline-first OpenSpec change to reproduce the exact r8
   `request_validation_failed` path and identify the failing invariant.
3. If an implementation defect is proven, add one red regression, make the
   minimum source fix, run focused checks and the registered commit gate, and
   archive that fix without launching the game.
4. Only a later explicit amendment may prepare a previously absent replacement
   qualification identity and independently review another no-action attempt.
5. Resume the 24-by-25 evidence study only after a future qualification and
   independent verifier both pass.
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
