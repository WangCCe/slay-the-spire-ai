## Context

The archived multiclass residual used a binary gate plus an action head trained
only on the best alternative from rows whose best branch exceeded the guard by
0.5. Its held-out positive-action accuracy was 0.4552 and its fresh simulator
gate regressed. A causal EndTurn mask improved that policy but still lost to
guarded control, so another action filter is not justified.

The immutable corpus already stores state tensors, the guarded action, legal
action masks, and every evaluated branch return. It contains 6,643 training and
3,439 evaluation alternatives. Train and evaluation alternative-advantage
distributions are similar, and no new gameplay or simulator collection is
needed before fitting a different objective.

## Goals / Non-Goals

**Goals:**

- Learn one scalar relative advantage for every supported alternative from all
  available branch-return evidence.
- Select alternatives by predicted advantage over the exact guarded action,
  with deterministic abstention and pre-selection safety masking.
- Produce a source-bound development artifact with exact CPU roundtrip and one
  fixed fresh matched simulator decision.
- Spend the iteration on fitting and outcome evidence, using focused and
  adjacent tests instead of the slow full pytest gate unless shared behavior
  proves that broader coverage is necessary.

**Non-Goals:**

- Refit or modify r16, the guard proxy, the source corpus, native simulator, or
  branch-return definition.
- Sweep model size, optimizer, target scaling, intervention threshold, seeds,
  horizons, or safety filters after seeing results.
- Start Slay the Spire or CommunicationMod, alter production configuration, or
  grant qualification, promotion, or production-loading authority.

## Decisions

### Score one candidate relative to the guard

The scorer SHALL freeze the parent and concatenate its latent state with the
guard one-hot, candidate one-hot, and full legal-action mask. One shared MLP
predicts a scalar candidate advantage. At inference, the policy scores every
supported allowed alternative, selects the maximum, and intervenes only when
that prediction reaches the registered 0.5 return-unit threshold; otherwise it
executes the exact guard action.

Alternative considered: add another binary gate in front of the value scorer.
Rejected because the predicted advantage already defines an interpretable gate
and a second head recreates the failed objective split.

### Train on every alternative return

Each corpus row SHALL expand in memory into one example per non-guard branch,
with target `branch_return - guard_return`. The fixed recipe SHALL clip targets
to `[-20, 20]`, scale them by 10, and use Smooth L1 regression; inference
reverses the scale before applying the threshold. Training uses one registered
seed, architecture, optimizer, batch schedule, and update count.

Alternative considered: train only pairwise ordering labels. Rejected for this
first successor because pairwise labels discard the absolute advantage needed
for calibrated abstention. Ranking metrics remain part of held-out evaluation.

### Keep EndTurn as a pre-selection safety boundary

The scorer may learn from the complete source corpus, including EndTurn branch
returns, but the post-wasteful-EndTurn execution path SHALL exclude action 90
before selecting the best alternative. If no allowed supported alternative
remains, or no predicted advantage reaches threshold, execution SHALL preserve
the exact guard action and report why it abstained.

Alternative considered: remove EndTurn examples during training. Rejected
because complete targets improve diagnostics and execution safety is already a
separate enforceable contract.

### Use one offline gate and one fresh simulator gate

The fixed fit SHALL publish regression error, sign accuracy, per-state best
action accuracy and regret, selected true advantage, intervention precision,
constraint counts, and exact artifact roundtrip. It may enter one fresh matched
LightSTS gate only if it selects at least one held-out alternative, has
non-negative mean selected true advantage, and produces zero illegal or
forbidden selections. The fresh gate uses a preregistered seed-disjoint cohort
and retains the recipe only when candidate-only wins are at least control-only
wins, mean reward and HP deltas are non-negative, no nonterminal profiles are
excluded, and at least one intervention occurs.

Alternative considered: tune the threshold on evaluation data before the fresh
gate. Rejected because it would convert the held-out partition into a search
surface and repeat the low-information near-neighbor loop.

## Risks / Trade-offs

- [One-hot action identity may generalize weakly across sparse actions] -> Use a
  shared state-action MLP and publish per-action support and error; do not add an
  embedding redesign after results.
- [Large negative returns may dominate regression] -> Apply the preregistered
  symmetric clip and scale, and publish clipped and raw metrics.
- [Simulator branch values may contain divergence] -> Keep authority offline
  and require a separate real-game validation before production use.
- [The scorer may intervene too often despite positive held-out advantage] ->
  Let the fixed fresh matched gate decide policy quality; do not post-hoc tune
  threshold or intervention rate.

## Migration Plan

No production migration occurs. Implement and test the development scorer,
commit one immutable training registration, fit once, and commit its bounded
artifact and report. If offline integrity passes, commit one immutable fresh
evaluation registration and run it once. Archive the change with either a
retained offline recipe or a closed no-go result. Rollback removes only the new
development files and reports.

## Open Questions

No fit or policy parameter may be chosen after registration. A successful
simulator recipe would leave one later question for a separate change: whether
to proceed through replay calibration or directly to a bounded real-game
shadow comparison.
