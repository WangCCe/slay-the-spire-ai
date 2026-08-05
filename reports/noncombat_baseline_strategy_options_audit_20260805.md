# Non-Combat Baseline Strategy Options Audit

Date: 2026-08-05 (Asia/Shanghai)

Status: `state_conditioned_simulator_learning_experiment_required`

## Decision

Do not search for another heuristic policy to serve as non-combat
policy-quality truth. Current has consumed its unique final baseline attempt,
SimpleAgent is unsuitable as a policy-quality gate, Bottled remains an
auxiliary oracle, and every learned imitation lane is valid negative evidence.
No existing policy can replace Current as a credible baseline candidate.

This does not prevent another bounded simulator-learning experiment. A frozen
seeded initialization is sufficient as an experimental control for answering
whether a new state-conditioned architecture learns under the registered
simulator reward. It is not a credible policy baseline and cannot support a
policy-quality, formal-RL, live, causal, or promotion claim.

The next change should therefore define one new state-conditioned
simulator-learning experiment. It should preserve formal non-combat RL as
`no_go`, keep target-supported outcomes independently blocked, and avoid
reopening the Current baseline lane.

## Evidence

| Evidence | SHA-256 | Size |
| --- | --- | ---: |
| Final Current readiness refresh | `4f09bbf53a6b9e17ca1e5427d9651a6066d416ef8d5531808e7cf9ee7b328ce0` | 3,786 |
| r2 terminal postmortem | `d5c66e41b81a20f7d5503dab1f0ca54533723aa162b1a19c9acf56b9c1124811` | 33,364 |
| State-conditioned successor design audit | `7091c1fd5d0739fd39efa0ddb376348de46b42c5826556724e4565a6c8f53988` | 7,241 |
| SimpleAgent teacher-sufficiency result | `213d266841322d19aad5b35a7a1bb6290e3c147e50ab8273e2b410230dd850f0` | 1,284 |
| Formal-RL readiness r2 report | `3458b0f27ab5ff65f60e280f010c2a9802e92ee6f0f71d530df2151be14da97a` | 1,070 |
| Outcome-study feasibility audit | `46d9321676676b92756caab5e35cddb4055086078accacb13e83540a81240bbe` | 4,216 |
| r2 simulator metrics | `ad25f81342f782f8238584ee8923f330a9399f9a43b95dc12cf6455d7df10b9a` | 1,768 |

The evidence establishes these current facts:

- Current has verdict `no_viable_baseline_candidate`; another same-question
  attempt is prohibited.
- SimpleAgent failed all six registered suitability checks despite exact
  reconstruction of 993/993 teacher actions.
- Bottled lacks trajectories, target mappings, known propensities, and
  contextual alternative-action overlap needed for policy-quality or OPE use.
- r2 trained for 4,096 episodes and improved holdout mean floor by `+10.53125`
  over its seeded initialization, with paired lower bound `+9.685546875`.
- r2 observed zero victories and selected `take` for every trained card-reward
  decision. Its linear architecture could not condition relative candidate
  ordering on shared state.
- The separate state-conditioned ranker and exact API v3 policy-input boundary
  now close that deterministic architecture defect at source level, but they
  have not been integrated into an experiment.
- Target-supported outcome feasibility remains `not_demonstrated`, with zero
  supported victories and plug-in pass probability `0.000000000000`.

## Options

### 1. Build another heuristic comparator

Reject. This would create another hand-maintained policy, consume substantial
mechanics and decision work, and still provide no independent quality truth.
It would also defer testing the already implemented state-conditioned learning
boundary.

### 2. Promote SimpleAgent or Bottled to quality baseline

Reject. Both roles are already evidence-bounded. SimpleAgent is a narrow
auxiliary implementation control, while Bottled is a label and diagnostic
oracle. Agreement with either must not become reward or policy-quality truth.

### 3. Remove the formal readiness blockers globally

Reject for now. Baseline quality and target-supported outcomes remain valid
requirements for a formal training or live-value claim. Reinterpreting the
existing readiness audit would mix simulator research capacity with transfer
and promotion evidence.

### 4. Separate simulator learning control from policy-quality baseline

Select. Use a frozen seeded initialization only as the experiment's paired
control. The experiment may determine whether training changes a
state-conditioned policy under fixed simulator metrics, but it must not claim
that either policy is good enough for formal RL or live use.

## Required Experiment Boundary

The proposed successor must:

1. Use a new runner and identity; do not edit, resume, or reinterpret r2.
2. Integrate the existing separate state and candidate tensors with the
   `state-conditioned-candidate-ranker-mlp-v1` architecture.
3. Preserve the formal victory-primary reward and exact API v3 leakage
   exclusions; Current, Bottled, SimpleAgent, OPE, and live outcomes must not
   enter policy input, reward, or action selection.
4. Use fresh train, canary, and holdout cohorts selected by a tracked,
   deterministic exclusion inventory.
5. Compare trained policy only with its frozen seeded initialization for the
   primary learning-control question. Reference policies may appear only in
   read-only diagnostics outside pass gates.
6. Add deterministic per-category candidate availability, selected-kind rates,
   score margins, and exact saturation checks. A floor increase with action
   family collapse must not be a positive learning verdict.
7. Require legal complete rows, deterministic replay, four-category coverage,
   bounded unsupported rates, positive paired floor evidence, and a
   preregistered non-collapse gate before holdout access.
8. Keep victory counts primary and explicit. A floor-only result with zero
   victories may be useful algorithm evidence, but cannot establish formal-RL
   readiness or policy quality.
9. Load no production checkpoint, start no game or CommunicationMod process,
   and grant no live, OPE, causal, qualification, loading, or promotion
   authority.
10. Separate source-only implementation, preregistration, exact execution
    authorization, execution, and terminal closeout commits.

## Independent Outcome Lane

Do not resume the active v2 known-propensity study. Its current feasibility
gate is `not_demonstrated`, r1-r8 are retired, and task 4.1 remains correctly
blocked. A simulator-learning experiment cannot create target-supported live
victories or satisfy that study's source-comparability requirement.

## Next Change

Create OpenSpec change
`add-state-conditioned-noncombat-simulator-learning-experiment`. Its first
implementation phase should be source-only. No cohort materialization, native
loading, environment construction, training, or empirical execution should
occur until implementation verification and a separate pushed registration
are complete.
