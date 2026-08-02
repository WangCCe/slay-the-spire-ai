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

The active v2 known-propensity outcome-evidence study is stopped before any
replacement qualification or study start. R7 remains immutable and retired
after `source_validation_failed`; its raw-first source fix, focused
regressions, registered commit gate, and OpenSpec archive are complete.

The separately reviewed r8 replacement reached `source_verified`, then failed
at `request_validation_failed` before active request publication, gameplay, or
trajectory collection. The immutable chain proves at least one live boundary;
the same-session operator journal records one issued invocation but does not
independently prove the exact count. Its standalone verifier and independent
closeout passed, CommunicationMod and protected inventories were restored
exactly, target processes are zero, and the registered study root remains
absent. R8 is consumed and permanently retired; it cannot be retried or used
to prepare r9 under its amendment.

The separate regression-backed diagnosis proved that the r8 qualifier CLI
bound `--request` to the absent active publication path instead of the reviewed
repository `request_source_path`. The narrow source fix adds one canonical
builder and exact validator for that suffix, routes the production-Python smoke
through it, and preserves every retired r8 artifact unchanged.

The offline feasibility audit now binds the frozen B3-B7 readiness evidence
and current v2 registration exactly. It observes 125 complete trajectories,
one raw victory, and zero deterministic-Current-supported victories because
the winning trajectory has exact target weight zero. For 600 attempts to have
an 80% plug-in probability of reaching the registered three-supported-victory
gate, the supported-victory rate would need to be about 0.7118%. The current
audit is `not_demonstrated` because the evidence is historical-only, contains
no supported victory, and yields zero plug-in pass probability. It grants no
qualification, study, gameplay, OPE, training, or promotion authority.

The offline `sts_lightspeed` adapter POC now binds the simulator checkout,
submodule commits, physical source hash, adapter commit/source hash, and native
module hash. Two independent 20-seed batches were identical, terminated on all
seeds, covered route/shop/event/card-reward decisions, and applied all 46
inspected candidates on isolated clones. The historical-prefix check matched
12/12 early reward candidate sets from six recent real runs. The fit verdict is
`adapter_poc_ready`.

That verdict establishes an offline environment interface, not policy quality
or mechanics parity. The declared first-candidate baseline won 0/20 runs,
battle potion use is disabled, non-target screens remain baseline-controlled,
and arbitrary live non-combat states cannot be imported. Simulator transitions
remain separate from live known-propensity, OPE, and supported-outcome evidence.
Every live, training, OPE, qualification, and promotion authority flag remains
false.

The next authorized sequence is:

1. Preserve r1-r8, the completed r8 diagnosis/fix, and all external evidence
   byte-for-byte; do not prepare r9 or another replacement identity.
2. Preserve the canonical feasibility input and deterministic JSON/Markdown
   `not_demonstrated` report as the current pre-launch decision.
3. Use a separate offline-first OpenSpec decision to choose among improving
   and re-baselining the current gameplay policy, revising the outcome/reward
   evidence contract, or registering a materially different study design.
4. Treat `adapter_poc_ready` as permission only to design, not run, one bounded
   simulator-training smoke. Its proposal must define a training-only reward,
   evidence separation, simulator-divergence gates, fixed holdout seeds, a
   later real-game evaluation boundary, and explicit stop conditions.
5. Permit a later replacement-qualification amendment only after a current,
   source-comparable feasibility audit demonstrates the declared planning gate.
6. Consider bounded non-combat RL training only after the revised evidence
   path reaches the existing independently checkable training go/no-go gates.

## Work Lanes

The primary lane is non-combat RL readiness: first close the offline simulator
environment contract, then review a bounded training-smoke proposal, while
keeping simulated and live evidence separate.

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
