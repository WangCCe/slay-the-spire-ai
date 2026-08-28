# Action-Relative Conformal Margin Fit r1 Failure

## Outcome

The registered execution `combat-rl-action-relative-conformal-margin-fit-20260829-r1`
terminated before holdout evaluation. It produced no output directory,
development artifact, report, holdout metrics, qualification, or promotion
authority.

The failed registration remains immutable and SHALL NOT be rerun.

## Bound execution

- Source commit: `a2eba1499978b48d7ed4f43c6e03ba1747f6f83b`
- Registration commit: `296b7667b`
- Registration: `reports/combat_rl_action_relative_conformal_margin_fit_20260829_r1_registration.json`
- Output path: `reports/combat_rl_action_relative_conformal_margin_fit_20260829_r1` (not created)
- Native loading: not authorized
- Gameplay or CommunicationMod: not authorized and not started
- Production checkpoint loading or writing: not authorized

## Failure

The runner fitted the five registered bootstrap members and computed the
registered family corrections. It then loaded the evaluation corpus but failed
while evaluating the calibration partition, before calling holdout evaluation:

```text
ValueError: action-relative branch returns are missing
```

The supported-action normalization removed EndTurn action 90 from metadata.
Rows containing only the guard branch plus EndTurn then had no supported
alternative, but their tensor rows were retained. `evaluate_corpus` correctly
rejected the resulting one-branch metadata.

## Decision

This is a deterministic runner-contract defect, not a model-quality result.
One replacement registration may be created only after adding a regression and
repairing tensor/metadata row filtering. The replacement must bind a new source
commit, experiment id, runner hash, registration, and output path while keeping
the registered corpus bytes, parent, ensemble recipe, fit/calibration seeds,
alpha, action families, intervention threshold, and offline gates unchanged.
