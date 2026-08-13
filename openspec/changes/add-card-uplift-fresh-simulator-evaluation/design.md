## Context

The r7 entry policy plus a 79-parameter hierarchical card-uplift residual has
passed train-only cross-fit, one-shot development, and independent reserved
audit gates. Those inputs are frozen and tracked. The remaining question is
trajectory-level: whether changing only card-reward choices helps complete
simulator runs while every other decision remains native.

## Goals / Non-Goals

**Goals:**

- Measure paired whole-run terminal-floor and victory effects on untouched
  seeds.
- Verify that the frozen candidate actually changes enough card decisions to
  make the comparison informative.
- Keep model, simulator, source, cohort, limits, and gates fixed before access.

**Non-Goals:**

- Fit, tune, or choose another model from fresh results.
- Change route, shop, event, rest, or boss-reward behavior.
- Start live gameplay or claim production promotion readiness.

## Decisions

### Use independent paired environments

For each seed in `90000..90063`, run one native-control episode and one
candidate episode from independent environment instances. Pair terminal floors
by seed. This controls the initial simulator draw without sharing mutable state
between arms.

### Intervene only at supported card rewards

The candidate composes frozen r7 logits with the persisted residual only when a
state exposes exactly three `take` actions and one `skip` action. It uses native
baseline transitions for every other category. At each supported candidate
card state, a disposable clone queries the native selection so the report can
count genuine interventions without changing the candidate trajectory.

### Fix a modest noninferiority gate

The evaluation requires at least 56 complete pairs, at most eight registered
support censors, at least 12 candidate card interventions, nonnegative mean
paired terminal-floor difference, a deterministic 95 percent bootstrap lower
bound of at least `-2.0` floors, and candidate victories no lower than control.
The bootstrap uses 10,000 resamples and seed `20260813`. These gates permit a
thin live shadow-adapter proposal; they do not promote policy behavior.

### Preserve source and model bytes

Preflight verifies all tracked input hashes and creates no environment until
the frozen model has loaded and validated. Execution rechecks the entry
checkpoint and residual bytes after rollout and publishes canonical JSON only
after all structural and quality gates are computed.

## Risks / Trade-offs

- [Sixty-four pairs give a wide interval] -> Use the result only as a bounded
  go/no-go for live shadow wiring, not as a policy-quality claim.
- [Trajectory divergence changes later card opportunities] -> Report per-arm
  card counts and define interventions only on candidate states against a
  same-state native clone.
- [Unsupported native states reduce sample size] -> Censor only registered
  support blockers, never replace seeds, and fail below 56 complete pairs.
- [A native runtime interruption leaves partial work] -> Stage output and
  publish only a complete result; an infrastructure-only prepublication failure
  may rerun the unchanged registration, but a published logical result may not.
