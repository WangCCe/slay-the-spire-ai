# Final Current Baseline Readiness Refresh

Date: 2026-08-05 (Asia/Shanghai)

## Decision

The baseline-policy domain remains blocked and now has verdict
`no_viable_baseline_candidate`. The unique final Current replication is
consumed, its holdout is incomplete, and its terminal publication is invalid.
Current cannot receive another baseline attempt.

Formal non-combat RL remains `not_ready_for_bounded_training_proposal` because
both `baseline_policy` and `outcome_support` are blocked. The latter remains an
independent failure with zero source-comparable target-supported victories and
plug-in pass probability `0.000000000000`.

## Baseline Evidence

The final replication produced useful but non-authoritative diagnostics:

- all 16 canary pairs were complete and passed;
- Current mean floor was `25.0625` versus control `14.1875`;
- paired mean floor difference was `+10.875`;
- all four Current categories were covered;
- neither policy had a support row or victory;
- five holdout pairs were retained, with Current mean `20.2` and paired mean
  `+6.8`;
- the remaining 59 holdout pairs and registered bootstrap were not completed.

These values cannot demonstrate a floor because the 64-pair denominator,
bootstrap, canonical metrics, terminal report, and artifact manifest are
absent. The source-only verifier returned `artifact_inventory_mismatch`.

## Interpretation

The result is neither a negative estimate of Current's quality nor permission
to tune and retry. It is an invalid final measurement with a complete passing
canary and partial holdout. Under the preregistered terminal-lane contract,
that ends Current's eligibility for the same baseline question.

The earlier state-action, reference-isolation, reward, and evaluation domains
remain passed. They do not compensate for a missing credible baseline or
target-supported outcomes. The state-conditioned input/ranker capabilities
remain source-only and do not authorize another simulator experiment.

## Next Boundary

Do not repair and rerun this identity, select replacement seeds, lower gates,
or substitute Bottled/SimpleAgent as policy-quality truth. Any future formal
training direction first requires a new project-level decision for a different
credible baseline strategy. Target-supported outcome expansion remains a
separate prerequisite and must not be inferred from simulator floor rows.

## Authority

Gameplay, fresh evidence, native loading, seed access, reward, OPE, model
fitting, formal RL, training, qualification, policy loading, promotion, and
target-supported-outcome authority all remain false.
