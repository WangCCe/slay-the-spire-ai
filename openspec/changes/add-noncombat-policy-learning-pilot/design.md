## Context

The repository now has a frozen no-training behavior baseline, canonical non-combat decision samples, uniquely joined live outcomes where available, and a native Bottled oracle adapter. The existing readiness report proves that the data loop is wired, but it deliberately sets `formal_noncombat_rl_training_ready=False` and does not train a policy.

The identified frozen July 10 dataset contains 373 decisions and 216 matched outcome rows, but those matched rows come from only 6 unique runs and contain no victories. Shop evidence spans only 3 matched runs. A newer file named `latest` has different coverage and is not the source of these baseline figures. Sample count therefore overstates independent evidence. In addition, the current behavior policy is largely deterministic and the sample schema does not consistently record policy identity or a known action probability, so reliable off-policy evaluation is not yet possible.

This pilot is the first training-adjacent stage. It validates supervised policy-learning mechanics and evaluation discipline without optimizing run outcomes or changing live gameplay.

## Goals / Non-Goals

**Goals:**

- Build versioned policy-learning datasets from canonical samples with stable trajectory grouping and behavior provenance.
- Prevent run leakage with deterministic group-level train, validation, and test splits.
- Train a small action-masked candidate ranker separately for Current-imitation and Bottled-auxiliary labels.
- Produce reproducible model artifacts and reports with per-category coverage, legality, agreement, loss, calibration, and support limitations.
- Identify exactly which data is missing before off-policy or formal RL work can begin.

**Non-Goals:**

- No reward optimization, advantage weighting, Q-learning, policy gradients, or formal offline RL.
- No live agent integration, policy mixture, exploration, CommunicationMod change, or checkpoint auto-loading.
- No claim that Bottled is ground truth or that Bottled agreement implies better outcomes.
- No gameplay strategy repair, training-parameter tuning for win rate, or replacement of existing shop/event/route/card-reward heuristics.
- No combat-policy learning.

## Decisions

### Use an additive v2 provenance contract

Canonical samples gain `trajectory_group_id`, `behavior_policy_id`, `behavior_policy_commit`, `behavior_action_probability`, and `behavior_probability_status`. A unique matched `.run` supplies the trajectory group. Unknown or unproven probabilities remain null and are reported as unknown; the exporter never invents stochastic support.

V1 samples remain readable for coverage diagnostics. They are excluded from grouped train/evaluation unless the builder can resolve their trajectory and behavior provenance without ambiguity.

Alternative: use each decision as an independent sample. Rejected because adjacent decisions from one run would leak nearly identical state and the same outcome into every split.

### Split trajectories, not rows

The dataset builder hashes `(split_seed, trajectory_group_id)` with SHA-256, sorts groups by the resulting key, and assigns whole trajectories to fixed 60/20/20 train, validation, and test splits. Integer rounding assigns 60 percent and 20 percent first; the remainder goes to test. The manifest records the exact group lists, input hashes, schema versions, and split configuration. No trajectory may appear in more than one split.

The pilot support gate requires at least 10 eligible trajectory groups overall, non-empty train/validation/test splits, and at least two train groups plus one held-out group for any category-specific metric presented as evaluable. Smaller datasets still produce a blocked support report.

Alternative: random row splitting. Rejected because it produces optimistic metrics and cannot support run-level evaluation.

### Score only normalized legal candidates

The learned model scores each available candidate independently and applies cross-entropy over the candidates present in that sample. Input features combine normalized numeric state fields with a deterministic 1024-dimensional signed SHA-256 feature hash of categorical state and candidate tokens. The first implementation uses a single CPU PyTorch linear scorer with no hidden layers and no new dependency. Training uses Adam with a fixed default learning rate of `1e-3`, at most 50 epochs, and validation-loss early stopping with patience 5; no hyperparameter sweep is part of the pilot.

The predicted action is always the argmax among available candidates. Rows whose target label does not map to an available candidate are excluded from training and counted as mapping failures.

Alternative: emit a global action class. Rejected because card, event, shop, and route actions have variable, state-dependent candidate sets and a global classifier could predict unavailable actions.

### Keep Current and Bottled supervision isolated

Current-imitation training uses the action actually selected by the frozen behavior policy. Bottled-auxiliary training uses only complete, mapped, native Bottled labels that satisfy the configured confidence gate. Each mode has a separate dataset count, model artifact, metrics block, and limitation list.

The pilot never combines the labels into one target, never converts Bottled agreement into reward, and never uses the observed outcome as the label. This preserves room for a later learned policy to disagree with both references.

Alternative: train directly on a blended Current/Bottled target. Rejected because blend weights would encode an unvalidated policy preference and constrain later RL.

### Treat outcome association and OPE as diagnostics

Run outcomes are summarized by split and may be associated with behavior-policy decisions for diagnostics. They are not used to train the supervised models. The report marks off-policy evaluation unsupported unless chosen-action propensities are known and the dataset demonstrates action support beyond a single deterministic behavior policy.

Alternative: use floor reached or victory as an immediate per-decision reward. Rejected because every decision in a run would receive the same heavily confounded long-horizon outcome.

### Make the pilot deterministic and offline-only

The CLI defaults to CPU, fixed seeds, deterministic input ordering, bounded epochs, and an explicit output directory. It writes a dataset manifest, split manifest, model files, JSON metrics, and Markdown report. Artifacts include source commit and configuration hashes and are never searched by live agent or existing checkpoint loaders.

Implementation is split by responsibility: `noncombat_policy_dataset.py` owns eligibility, manifests, splits, and support gates; `noncombat_policy_model.py` owns feature hashing, the linear ranker, training, and prediction metrics; `noncombat_policy_learning.py` owns CLI orchestration, report rendering, and atomic artifact writes. None of these modules is imported by the live agent.

Running the same command against identical inputs and seed must reproduce split manifests and metrics. Model byte identity is desirable but not required across PyTorch versions; tensor predictions and reported metrics must match within a declared tolerance.

## Risks / Trade-offs

- **Only a few independent runs are available** -> Block training claims below the trajectory support threshold and first refresh from the frozen clean batches.
- **No victories or weak outcome diversity** -> Keep outcomes diagnostic and make no uplift or RL-readiness claim.
- **Hashed features collide or underfit** -> Record the feature configuration and compare against frequency baselines; do not increase model complexity unless the pilot proves the data path.
- **Bottled imitation crowds out RL exploration** -> Isolate Bottled artifacts and metrics and prohibit using Bottled labels as reward or mandatory promotion targets.
- **Unknown behavior propensities are mistaken for zero or one** -> Store null plus an explicit status and block OPE.
- **A model predicts an unavailable action** -> Score only the sample's normalized available candidates and assert 100% candidate legality.
- **Training outputs are accidentally loaded live** -> Keep the module under `analysis_scripts`, require explicit output paths, and add guards proving live config and checkpoint discovery are unchanged.

## Migration Plan

1. Extend the sample exporter additively and keep v1 input parsing.
2. Re-export samples only from the `f321cb05` Batch 2 Retry 1 interval (`1783787478..1783790134`) and its 25 explicitly paired run files into a new, separately named v2 dataset.
3. Build and validate the support and split manifests before enabling the training subcommand.
4. Run Current-imitation and Bottled-auxiliary pilots only when their structural gates pass.
5. Preserve all previous reports and datasets; rollback removes the new offline artifacts and module without touching live gameplay.

## Open Questions

- The amount and form of future multi-policy exploration data is intentionally deferred. It requires a separate proposal after this pilot identifies concrete support gaps.
- Formal reward design and off-policy evaluation estimators remain deferred until behavior probabilities and action overlap are available.
