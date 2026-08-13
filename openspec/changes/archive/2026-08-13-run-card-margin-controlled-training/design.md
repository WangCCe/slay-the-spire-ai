## Context

The Bottled warm start has useful greedy agreement but a median fixed-probe
two-stage margin near 4.9. Twenty policy-gradient chunks moved parameters by
L2 1.50 while producing at most one greedy action flip. Baseline clipping was
not material, and a scorer-only update retained only 1.9% of full-model
function movement. Direct counterfactual rankers also failed development gates.

## Goals / Non-Goals

**Goals:**

- Preserve the warm-start greedy ordering while moving stochastic probabilities
  out of saturation before on-policy training.
- Reject the construction cheaply if one replay update still has negligible
  function-space effect.
- Spend most runtime on bounded candidate-only training when the mechanism gate
  passes.
- Decide only whether this construction merits fresh evaluation.

**Non-Goals:**

- Temperature search, reward changes, new teacher labels, protected/fresh cohort
  access, formal RL or policy-quality claims.
- Route, shop, event, combat, live gameplay, CommunicationMod, or production
  checkpoint changes.

## Decisions

### Start from the bound r7 checkpoint and discard its optimizer moments

Restore r7 `checkpoint_004`, the exact source of the published lossless replay.
Freeze all existing card and non-card model parameters and discard the old Adam
moments. This preserves the latest validated greedy policy while avoiding the
unresponsive full-model update path.

### Divide frozen logits by 4.0 and train only zero residual heads

An experiment-only `CardAcceptancePolicy` subclass obtains each frozen
64-dimensional hidden representation, returns the frozen scorer logit divided
by `4.0`, adds a bias-free residual linear projection, and recomputes the
acceptance coordinate. Both residual projections start at exact zero, so the
compressed entry preserves complete family and conditional ordering. Only the
128 residual weights are trainable under a fresh registered Adam and the
existing card-return objective.

Alternatives rejected: entropy-coefficient tuning changes the objective and
creates a search surface; continuing the full model repeats the saturated path;
training a new ranker from scratch failed counterfactual development gates.

### Gate environment access with one decoded replay step

Use the already-published lossless candidate replay only as a mechanism gate.
Before update, all fixed-probe greedy actions and full within-stage orderings
must match the unscaled r7 model, margins must be divided by four, and
probability values must be finite. After one residual-only step, mean joint
total variation from compressed entry must be at least `0.00482559`, retaining
80% of the historical full-model one-step movement. Coverage must remain within
5%-95%; all 128 residual parameters need finite gradients; frozen model and RNG
bytes must remain exact. Failure stops before native loading or environment
access.

The replay action distribution is not treated as on-policy evidence and grants
no quality claim.

### Run exactly four candidate-only chunks unless a safety stop fires

On gate pass, initialize again from untouched frozen r7 weights, zero residuals,
and a fresh registered Adam. Run four candidate-only trajectories chunks on the
same consumed 64-seed development schedule; native SimpleAgent owns every
non-card decision. Retain the existing 56-trajectory support floor, at most
eight Courier censors, unknown-blocker failure, checkpoint rollback, and 5%-95%
family coverage stop.

### Keep terminal evidence mechanism-scoped

If four chunks complete, run one paired candidate-versus-native comparison on
the same consumed cohort. Proposal readiness requires at least two probe action
flips, candidate mean floor and victories noninferior to native, no family
collapse, and supported execution. A pass permits only a separately
preregistered fresh evaluation.

## Risks / Trade-offs

- [Temperature increases exploration cost] -> Use the replay gate, fixed family
  coverage stops, and native non-card baseline.
- [Replay gate is off-policy] -> Interpret it only as differentiability/function
  sensitivity and recollect all training trajectories on-policy.
- [Repeated development seeds overfit] -> Make no quality claim and require a
  separate fresh cohort after any pass.
- [Residual checkpoint restores incorrectly] -> Bind base checkpoint hash,
  temperature, two residual tensors, fresh optimizer, RNG, and step coordinate.

## Migration Plan

Add the experiment-only policy/runtime and focused tests, run the replay gate,
then execute training only if it passes. All checkpoints remain outside
production discovery. Rollback removes the experiment artifacts and retains
native SimpleAgent.

## Open Questions

None. Temperature, gate, schedule, and stopping rules are fixed before access.
