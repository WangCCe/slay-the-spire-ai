## Context

The repository now has separately reviewed evidence for non-combat state and
action reconstruction, a bounded simulator training smoke, frozen-policy
validity, a baseline warm-start attempt, and live outcome-support feasibility.
Those studies intentionally grant no formal-RL authority and answer different
questions. In particular, the recovered teacher audit proves exact source
reconstruction for its route and card-reward corpus while concluding that
SimpleAgent is unsuitable as a policy-quality gate.

The current evidence therefore cannot be summarized by teacher agreement or by
the positive holdout delta from the simulator smoke. A formal-RL readiness
decision must preserve the negative baseline and outcome results, distinguish
simulator-only reward evidence from a formal reward contract, and keep every
execution or promotion authority closed.

The audit runs entirely against checked-in frozen files. It must be practical
to reproduce in the normal Windows development environment and must not invoke
the game, the external simulator, a native module, a model, or a training
entrypoint.

## Goals / Non-Goals

**Goals:**

- Bind the exact bytes used for a formal non-combat RL readiness synthesis.
- Evaluate evidence integrity and five independent readiness domains:
  state/action, reward, baseline policy, outcome support, and evaluation.
- Preserve SimpleAgent, Current, and Bottled as auxiliary references only.
- Produce one deterministic verdict and an ordered list of unmet prerequisites.
- Make a positive verdict authorize only a separate bounded-training proposal.

**Non-Goals:**

- Run gameplay, simulator rollouts, native code, model fitting, OPE, or RL.
- Change state features, actions, rewards, policies, estimators, or thresholds.
- Reinterpret simulator evidence as live evidence or teacher behavior as policy
  quality.
- Open an untouched evaluation cohort, qualify evidence, or promote a policy.

## Decisions

### Use one immutable registration and validate before interpretation

The analyzer will consume a versioned JSON registration containing the source
commit, implementation hash, fixed gate contract, and a path, SHA-256 digest,
size, and expected schema for every evidence file. The registration will also
declare evidence slots that are intentionally absent, such as the current
formal reward contract. All paths must be repository-relative and all hashes
must match before a readiness check is evaluated.

This is preferred over discovering the newest report because discovery could
silently mix studies, commits, or reruns. Passing paths on the command line was
also rejected because it would leave the decision contract outside the
reproducible artifact.

### Evaluate fixed domains without result-dependent rules

The registration will carry the following fixed checks. Thresholds and
accepted classifications are part of the registration and are not inferred
from the observed result.

| Domain | Passing contract |
| --- | --- |
| Evidence integrity | Every required byte identity and schema matches; embedded registration hashes match; required replay and structural checks are true; every consumed artifact grants no formal-RL or live authority. |
| State/action | The teacher audit has no adapter gap, blocker, or reconstruction mismatch; it contains multi-candidate route and card-reward rows; simulator evidence reports legal candidates and all four non-combat categories. |
| Reference isolation | The teacher result is recorded as a limitation when unsuitable; teacher, Current, and Bottled labels are excluded from reward and policy-quality truth; no reference authority flag is true. This is a state/action subcheck rather than a teacher-quality gate. |
| Reward | A separately versioned formal reward-contract artifact is present, tested, names terminal victory as the primary objective, describes any floor-progress shaping separately, excludes reference labels, and declares simulator/live provenance boundaries. A simulator-smoke reward alone cannot pass. |
| Baseline policy | The registered baseline warm-start study demonstrates its full baseline floor, including validation, independent rollout, final gate, and deterministic reproduction. Training loss, teacher agreement, or the smoke's initial-policy delta cannot substitute. |
| Outcome support | The registered feasibility result is demonstrated from source-comparable evidence, meets the minimum target-supported victories, and meets the preregistered pass-probability floor. Raw unsupported victories do not count. |
| Evaluation | Train/holdout seeds are disjoint, deterministic replays match, final-test access follows its stop-gate contract, frozen evaluations do not update models, and all evaluation/promotion authority remains false. |

The canonical registration is expected to pass integrity, state/action,
reference isolation, and evaluation while blocking reward, baseline policy, and
outcome support. That expectation is explanatory only; the implementation will
also be tested with synthetic evidence that reaches every terminal verdict.

### Use a three-state terminal verdict

Verdict precedence is fixed:

1. `invalid_evidence` when registration, identity, schema, structural, replay,
   or no-authority validation fails.
2. `not_ready_for_bounded_training_proposal` when evidence is valid but one or
   more required readiness domains fail.
3. `ready_for_bounded_training_proposal` only when every required domain passes.

The positive verdict is deliberately narrow. It sets
`bounded_training_proposal_consideration` true but leaves formal training,
simulator training, gameplay, model fitting/loading, OPE, qualification, and
promotion false. A separate accepted OpenSpec change remains mandatory before
any execution.

### Publish domain evidence instead of a single opaque score

The analyzer will atomically publish:

- `configuration.json`: the exact validated registration bytes;
- `evidence_inventory.json`: resolved byte identities and parsed schemas;
- `readiness_matrix.json`: checks, status, blockers, and evidence references by
  domain;
- `report.json` and `report.md`: verdict, ordered prerequisites, limitations,
  and all-false authority;
- `artifact_manifest.json`: hashes and sizes for every canonical output.

No weighted readiness score will be produced. Weighting incomparable evidence
would hide a hard prerequisite and make a near-pass appear actionable.

### Recompute into a temporary directory for strict validation

`--validate-output-dir` will validate the published manifest, recompute from
the registered inputs into a temporary sibling directory, and compare every
canonical artifact byte-for-byte. It will never partially replace the
published directory. Publication will use a staging directory followed by an
atomic rename.

This follows the repository's existing registered-audit pattern and gives a
stronger claim than comparing selected summary fields.

### Emit deterministic next-prerequisite classes

For valid blocked evidence, recommendations are selected from a fixed mapping
of failed domains, ordered as reward contract, baseline policy floor, outcome
support, then evaluation contract. The mapping describes proposal classes, not
permission to execute them. Teacher unsuitability specifically prevents a
recommendation to optimize SimpleAgent imitation.

## Risks / Trade-offs

- [Risk] The synthesis can become stale as component studies evolve.
  -> Mitigation: exact hashes fail closed and require a new registration rather
  than silently adopting newer files.
- [Risk] A formal reward artifact could satisfy shape checks while still being
  a poor objective.
  -> Mitigation: readiness authorizes only proposal review; a later change must
  defend reward semantics and bounded training design.
- [Risk] Requiring live outcome support delays simulator-only experimentation.
  -> Mitigation: bounded smokes remain allowed under their own reviewed specs;
  only the stronger formal-RL proposal gate remains closed.
- [Risk] SimpleAgent's deterministic behavior may still be useful despite its
  failed suitability checks.
  -> Mitigation: preserve it as an auxiliary regression and rollout reference,
  never as reward or policy-quality truth.
- [Risk] Byte-for-byte validation adds runtime.
  -> Mitigation: the audit parses only small reports and manifests and invokes
  no simulator or training process.

## Migration Plan

1. Add the analyzer and synthetic focused tests.
2. Commit the implementation so its source identity can be registered.
3. Freeze one registration over the existing canonical evidence.
4. Execute the registered audit once and strictly recompute its output.
5. Record the no-authority interpretation in project direction, sync the spec,
   archive the completed change, and run the repository commit gate.

Rollback removes the analyzer, tests, registration, reports, and this change.
No live or model state requires migration.

## Open Questions

None. Any attempt to change a gate, add evidence, or execute training requires
a later reviewed change rather than an in-place reinterpretation.
