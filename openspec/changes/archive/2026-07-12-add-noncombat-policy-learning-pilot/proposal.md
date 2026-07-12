## Why

The qualified behavior lineage now has two clean 25-game mechanics batches and the non-combat exporter can produce normalized Current and native Bottled labels. However, the identified July 10 frozen policy dataset has 373 samples but only 6 uniquely matched runs, 0 victory runs, and only 3 matched runs containing shop samples; this is enough to test a supervised learning pipeline, but not enough to justify formal offline RL or live policy promotion. Policy-learning evidence for this change will be regenerated only from the `f321cb05` Batch 2 Retry 1 interval so every trajectory has one explicit behavior commit.

We need a bounded policy-learning pilot that proves dataset grouping, action masking, label separation, reproducible training, and held-out evaluation before collecting exploration data or starting formal non-combat RL.

## What Changes

- Re-export policy-learning datasets from the frozen baseline's clean evaluation evidence and report unique run, category, outcome, and action-support coverage.
- Add stable run/seed grouping and behavior-policy provenance to canonical samples without fabricating unknown action probabilities.
- Add an offline action-masked supervised ranker with separate Current-imitation and Bottled-auxiliary training modes.
- Add deterministic run-grouped train/validation/test splits that prevent decisions from one run appearing in multiple splits.
- Compare learned models against a category-frequency baseline and report held-out Current/Bottled label-reference agreement separately, with per-category legality, coverage, loss, and calibration metrics.
- Add an explicit support gate that blocks misleading model or off-policy claims when run groups, labels, candidate mappings, outcomes, or behavior propensities are insufficient.
- Preserve formal non-combat RL, live gameplay integration, checkpoint promotion, reward optimization, and CommunicationMod configuration as out of scope.

## Capabilities

### New Capabilities

- `noncombat-policy-learning-pilot`: Offline dataset building, action-masked supervised baselines, run-grouped evaluation, reproducibility, and support-gated reporting.

### Modified Capabilities

- `noncombat-rl-decision-loop`: Canonical samples gain run-group and behavior-policy provenance, and the training guard distinguishes an offline supervised pilot from formal non-combat RL readiness.

## Impact

- Affected code: `analysis_scripts/noncombat_rl_decision_loop.py`, a new offline policy-learning module and CLI under `analysis_scripts/`, and focused tests under `tests/`.
- Inputs: canonical decision-sample JSONL, frozen-baseline decision traces, AI run markers, and uniquely matched `.run` records.
- Outputs: versioned dataset manifests, deterministic split manifests, bounded model artifacts, and Markdown/JSON evaluation reports under `reports/`.
- Existing PyTorch support may be reused, but no new live runtime dependency or CommunicationMod change is introduced.
- Success means a reproducible, leakage-free offline pilot with 100% candidate-legal predictions and explicit support limitations. It does not mean the learned policy is ready for live play.
- Rollback is deletion of offline pilot outputs and code; canonical samples remain backward compatible and live gameplay remains unchanged.
