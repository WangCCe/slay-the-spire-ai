# Non-Combat Policy Learning Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a leakage-free, offline-only supervised policy-learning pilot for Current and Bottled non-combat labels without enabling formal RL or live policy promotion.

**Architecture:** Extend the canonical exporter with additive v2 behavior and trajectory provenance, then feed only eligible samples into a new offline module. That module builds mode-specific datasets, assigns whole trajectories to deterministic splits, scores only available candidates with a fixed linear PyTorch ranker, and emits support-gated reports and artifacts outside production checkpoint paths.

**Tech Stack:** Python 3.10, standard library JSON/hashlib/dataclasses/argparse, PyTorch CPU, pytest, repo-local OpenSpec.

## Global Constraints

- Use `D:\anaconda\envs\stsai\python.exe` for focused and full pytest.
- Run pytest with `-p no:cacheprovider --basetemp <writable repo-local path>`.
- Policy evidence comes only from candidate `f321cb05`, cutoff `1783787478..1783790134`, and the 25 explicit Batch 2 Retry 1 run files.
- Keep schema v1 readable; unknown provenance or behavior probability remains null/`unknown` and is never fabricated.
- Assign trajectories to fixed `60/20/20` train/validation/test splits using SHA-256 over `(split_seed, trajectory_group_id)`.
- Require at least 10 eligible trajectory groups overall and at least two train plus one held-out trajectory for a category-level quality metric.
- Use deterministic 1024-dimensional signed SHA-256 features and a single CPU `torch.nn.Linear(1024, 1)` candidate scorer.
- Use Adam at `1e-3`, at most 50 epochs, validation-loss patience 5, and no hyperparameter sweep.
- Current-imitation and Bottled-auxiliary labels, artifacts, and metrics remain separate; Bottled labels are never reward.
- Every prediction must be one of the sample's available candidates.
- Formal non-combat RL readiness and live-policy promotion remain false even after a successful pilot.
- Do not modify CommunicationMod configuration, launcher defaults, live agent imports, or production `checkpoints/` contents.
- Do not launch Slay the Spire or collect new gameplay in this change.

---

### Task 1: Canonical V2 Provenance

**Files:**
- Modify: `analysis_scripts/noncombat_rl_decision_loop.py`
- Modify: `tests/test_noncombat_rl_decision_loop.py`
- Create: `tests/fixtures/noncombat_policy_learning/frozen_20260710_summary.json`
- Modify: `openspec/changes/add-noncombat-policy-learning-pilot/tasks.md`

**Interfaces:**
- Produces `SCHEMA_VERSION = "noncombat-rl-decision-v2"`.
- Extends `export_samples_from_trace(..., until_unix=None, behavior_policy_id=None, behavior_policy_commit=None, behavior_action_probability=None, behavior_probability_status="unknown")`.
- Extends `build_trainable_sample()` with the same behavior arguments.
- Extends `load_run_outcomes(..., run_files: Optional[Sequence[str]] = None)`.
- `attach_live_outcomes()` adds `trajectory_group_id = "run:<run stem>"` only for a unique matched run.
- Adds CLI options `--until-unix`, `--run-limit`, repeatable `--run-file`, `--behavior-policy-id`, and `--behavior-policy-commit`.

- [ ] **Step 1: Add the frozen source fixture and failing v2 schema tests**

Create `frozen_20260710_summary.json` with these exact fields:

```json
{
  "samples_path": "reports/noncombat_rl_decision_samples_20260710_post_exec_command_fixes_25_bottled.jsonl",
  "sha256": "77DA5265ACF7A447C2C76321BED66F0D65C7A5C6614188C42505381D32C7E186",
  "sample_count": 373,
  "matched_sample_count": 216,
  "matched_trajectory_count": 6,
  "victory_trajectory_count": 0,
  "category_counts": {"card_reward": 70, "event": 61, "route": 224, "shop": 18},
  "matched_trajectory_counts": {"card_reward": 6, "event": 4, "route": 5, "shop": 3}
}
```

Add tests asserting exported rows contain:

```python
assert sample["schema_version"] == "noncombat-rl-decision-v2"
assert sample["trajectory_group_id"] is None
assert sample["behavior_policy_id"] == "current_heuristic"
assert sample["behavior_policy_commit"] == "f321cb05"
assert sample["behavior_action_probability"] is None
assert sample["behavior_probability_status"] == "unknown"
```

- [ ] **Step 2: Add failing join and stable-id tests**

Cover unique, ambiguous, missing, and floor-inconsistent joins. The unique case must assert `run:1780000000`; all other cases must assert a null trajectory group. Add a tail-size regression that exports the same trace event with two `tail` values and requires the same `sample_id`, proving the id uses the absolute input line number.

- [ ] **Step 3: Run RED tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp .pytest_tmp\policy-task1-red tests\test_noncombat_rl_decision_loop.py -k "v2 or trajectory or behavior or stable_sample_id or explicit_run_files" -q
```

Expected: failures showing schema v1, missing provenance fields, unstable tail-relative ids, missing `until_unix`, and unsupported explicit run files.

- [ ] **Step 4: Implement the additive exporter changes**

Use this shape in `build_trainable_sample()`:

```python
"trajectory_group_id": None,
"behavior_policy_id": behavior_policy_id,
"behavior_policy_commit": behavior_policy_commit,
"behavior_action_probability": behavior_action_probability,
"behavior_probability_status": behavior_probability_status,
```

Store `(absolute_line_number, line)` in the tail deque. Reject rows after `until_unix`. In `attach_live_outcomes()`, derive the group only from the unique matched `run_file`. When `run_files` is provided, load exactly those names and fail clearly if one is missing; otherwise preserve the existing limit behavior.

- [ ] **Step 5: Add CLI provenance and exact-run controls**

Pass explicit behavior metadata through export, expose `--until-unix`, and set `--run-limit` on `load_run_outcomes`. Repeatable `--run-file` overrides the limit. Keep probability null/unknown because the trace cannot prove action propensity.

- [ ] **Step 6: Run focused GREEN tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp .pytest_tmp\policy-task1-green tests\test_noncombat_rl_decision_loop.py -q
```

Expected: all tests in the file pass.

- [ ] **Step 7: Mark OpenSpec tasks 1.1-1.4 and 2.1-2.2 complete, review, and commit**

Commit only the exporter, tests, fixture, and task checkboxes:

```powershell
git add analysis_scripts/noncombat_rl_decision_loop.py tests/test_noncombat_rl_decision_loop.py tests/fixtures/noncombat_policy_learning/frozen_20260710_summary.json openspec/changes/add-noncombat-policy-learning-pilot/tasks.md
git commit -m "feat: add noncombat policy provenance"
```

---

### Task 2: Dataset Manifest, Trajectory Split, And Support Gate

**Files:**
- Create: `analysis_scripts/noncombat_policy_dataset.py`
- Create: `tests/test_noncombat_policy_learning.py`
- Modify: `openspec/changes/add-noncombat-policy-learning-pilot/tasks.md`

**Interfaces:**

```python
@dataclass(frozen=True)
class PolicyRow:
    sample_id: str
    trajectory_group_id: str
    category: str
    state: Mapping[str, Any]
    candidates: tuple[Mapping[str, Any], ...]
    target_action_id: str
    outcome: Mapping[str, Any]

@dataclass(frozen=True)
class DatasetBuild:
    rows: tuple[PolicyRow, ...]
    manifest: Mapping[str, Any]

@dataclass(frozen=True)
class SplitManifest:
    assignments: Mapping[str, str]
    groups: Mapping[str, tuple[str, ...]]
    manifest: Mapping[str, Any]

def build_policy_dataset(samples, *, label_mode, source_paths, source_commit,
                         bottled_confidence="high") -> DatasetBuild: ...
def assign_trajectory_splits(rows, *, split_seed,
                             train_fraction=0.60,
                             validation_fraction=0.20) -> SplitManifest: ...
def evaluate_support(dataset, splits, *, min_trajectories=10) -> Mapping[str, Any]: ...
```

- [ ] **Step 1: Write failing dataset eligibility and label-isolation tests**

Create synthetic v1/v2 samples and assert exact exclusion reasons: `legacy_schema`, `missing_trajectory_group`, `missing_behavior_policy`, `missing_candidates`, `missing_target`, `target_not_candidate`, `bottled_not_native`, and `bottled_confidence`. Current mode uses `selected_action_id`; Bottled mode requires `oracle_mode == "native_bottled"`, high confidence, and a mapped candidate.

- [ ] **Step 2: Write failing manifest and source-hash tests**

Require canonical JSON ordering, SHA-256 for every source path, counts by category/trajectory/outcome/action, separate label-mode counts, and idempotent manifest equality when input row order changes.

- [ ] **Step 3: Write failing split and support-gate tests**

Build 10 trajectories with decisions in multiple categories. Assert exact `60/20/20` group counts, disjoint sets, all rows from one group share a split, row-order independence, stable manifest hash, overall blocking below 10 groups, and category blocking below two train plus one held-out group.

- [ ] **Step 4: Run RED tests**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp .pytest_tmp\policy-task2-red tests\test_noncombat_policy_learning.py -q
```

Expected: import failure because `analysis_scripts.noncombat_policy_dataset` does not exist.

- [ ] **Step 5: Implement immutable rows and deterministic manifests**

Read JSONL with a streaming iterator, canonicalize manifest JSON with `sort_keys=True` and compact separators, and hash source files in chunks. Preserve outcomes only as diagnostics. Sort rows by `(trajectory_group_id, sample_id)` before every deterministic operation.

- [ ] **Step 6: Implement SHA-256 trajectory assignment and support gate**

Order groups by:

```python
hashlib.sha256(f"{split_seed}:{group_id}".encode("utf-8")).hexdigest()
```

Assign `int(n * 0.60)` to train, `int(n * 0.20)` to validation, and the remainder to test. Emit blocked reasons without changing thresholds.

- [ ] **Step 7: Run focused GREEN tests**

Run the Task 2 test file and the exporter tests. Expected: all pass.

- [ ] **Step 8: Mark OpenSpec tasks 2.3-2.4 and 3.1-3.4 complete, review, and commit**

```powershell
git add analysis_scripts/noncombat_policy_dataset.py tests/test_noncombat_policy_learning.py openspec/changes/add-noncombat-policy-learning-pilot/tasks.md
git commit -m "feat: add noncombat policy dataset gate"
```

---

### Task 3: Deterministic Candidate Ranker

**Files:**
- Create: `analysis_scripts/noncombat_policy_model.py`
- Modify: `tests/test_noncombat_policy_learning.py`
- Modify: `openspec/changes/add-noncombat-policy-learning-pilot/tasks.md`

**Interfaces:**

```python
@dataclass(frozen=True)
class FeatureConfig:
    version: str = "noncombat-policy-features-v1"
    hash_dim: int = 1024

@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 0
    learning_rate: float = 1e-3
    max_epochs: int = 50
    patience: int = 5
    device: str = "cpu"

@dataclass(frozen=True)
class Prediction:
    sample_id: str
    predicted_action_id: str
    target_action_id: str
    confidence: float
    probabilities: tuple[float, ...]

@dataclass(frozen=True)
class TrainingResult:
    model: "CandidateRanker"
    epochs_run: int
    best_validation_loss: float
    history: tuple[Mapping[str, float], ...]
    artifact_manifest: Mapping[str, Any]

class CandidateRanker(torch.nn.Module):
    def __init__(self, input_dim: int = 1024) -> None: ...
    def forward(self, candidate_features: torch.Tensor) -> torch.Tensor: ...

def candidate_feature_vector(row, candidate, config) -> torch.Tensor: ...
def train_ranker(train_rows, validation_rows, *, feature_config,
                 training_config) -> TrainingResult: ...
def predict_ranker(model, rows, *, feature_config) -> tuple[Prediction, ...]: ...
```

- [ ] **Step 1: Write failing signed-hash and feature-stability tests**

Require a 1024-element float32 tensor; repeated input is bit-identical; dictionary order does not change features; state and candidate changes alter the vector. Hash categorical tokens with SHA-256, use the first eight digest bytes modulo `hash_dim` for the bin, and use bit 0 of digest byte 8 for sign. Encode non-bool numeric values as signed `log1p(abs(value))`, clip at `10.0`, divide by `10.0`, and add the result to the SHA-256 bin for the prefixed numeric path without an additional hash sign.

- [ ] **Step 2: Write failing candidate-mask and label-isolation tests**

Construct samples with different candidate counts. Assert logits length equals candidate count, predicted ids always belong to that row, and Current/Bottled rows cannot be mixed in one training call. The training artifact manifest records a mode-specific artifact stem; actual artifact file names and writes remain Task 4's responsibility.

- [ ] **Step 3: Write failing bounded deterministic training tests**

Train a separable synthetic dataset twice with the same seed. Assert identical predictions and metrics within `1e-7`, `epochs_run <= 50`, early stopping honors patience 5, device is CPU, and the artifact manifest keeps both promotion flags false. Reject non-CPU devices, `max_epochs` outside `1..50`, `patience` outside `1..5`, and non-positive or non-finite learning rates.

- [ ] **Step 4: Run RED tests**

Run the ranker-selected tests and confirm missing interfaces fail.

- [ ] **Step 5: Implement feature hashing and linear model**

Flatten state and candidate mappings recursively into stable `path=value` tokens. Do not use Python's randomized `hash()`. The model is exactly:

```python
class CandidateRanker(torch.nn.Module):
    def __init__(self, input_dim=1024):
        super().__init__()
        self.scorer = torch.nn.Linear(input_dim, 1)

    def forward(self, candidate_features):
        return self.scorer(candidate_features).squeeze(-1)
```

- [ ] **Step 6: Implement per-sample cross-entropy training**

Sort rows by id, require one non-empty label mode across train and validation rows, set Python and Torch CPU seeds, zero gradients per sample, score only available candidates, and target the index whose action id equals `target_action_id`. Keep the best validation state by deep-copying tensors; stop after the configured number of non-improving epochs.

- [ ] **Step 7: Run focused GREEN tests**

Run all policy-learning tests. Expected: all pass and no CUDA initialization.

- [ ] **Step 8: Mark OpenSpec tasks 4.1-4.3 and 4.5 complete, review, and commit**

Leave task 4.4 pending until Task 4 adds and tests the explicit offline output-directory contract.

```powershell
git add analysis_scripts/noncombat_policy_model.py tests/test_noncombat_policy_learning.py openspec/changes/add-noncombat-policy-learning-pilot/tasks.md
git commit -m "feat: add offline noncombat candidate ranker"
```

---

### Task 4: Evaluation, Reporting, Artifacts, And CLI

**Files:**
- Create: `analysis_scripts/noncombat_policy_learning.py`
- Modify: `analysis_scripts/noncombat_policy_dataset.py`
- Modify: `analysis_scripts/noncombat_policy_model.py`
- Modify: `tests/test_noncombat_policy_learning.py`
- Modify: `openspec/changes/add-noncombat-policy-learning-pilot/tasks.md`

**Interfaces:**

```python
def evaluate_ranker(model, rows, *, feature_config,
                    frequency_counts) -> Mapping[str, Any]: ...
def render_policy_report(dataset_manifest, split_manifest, support,
                         metrics=None) -> str: ...
def write_pilot_artifacts(output_dir, *, mode, dataset, splits,
                          support, model=None, metrics=None) -> Mapping[str, str]: ...
def main(argv: Optional[Sequence[str]] = None) -> int: ...
```

- [ ] **Step 1: Write failing frequency-baseline and metric tests**

The frequency baseline counts target actions by category on train rows and chooses the highest-count available candidate with action-id tie breaking. Require top-1 agreement, mean cross-entropy, ten-bin top-confidence calibration error, candidate legality, and per-category counts on held-out rows only.

- [ ] **Step 2: Write failing OPE/support report snapshots**

Blocked reports must name missing trajectories, mappings, unknown propensities, and missing action overlap. Allowed supervised reports must still contain:

```text
Formal non-combat RL: blocked
Live policy promotion: blocked
Off-policy evaluation: unsupported
```

Never render causal uplift or reward-improvement language.

- [ ] **Step 3: Write failing CLI and artifact-isolation tests**

Test `support` and `train` subcommands with required `--samples`, `--output-dir`, `--split-seed`, `--source-commit`, and `--label-mode`. Require mode-specific dataset/split/support/metrics/report/model names, atomic writes, and no files under `checkpoints/`.

- [ ] **Step 4: Run RED tests**

Run CLI/report selected tests and confirm missing functions/subcommands fail.

- [ ] **Step 5: Implement held-out metrics and deterministic reports**

Compute metrics only from validation/test groups in the split manifest. Keep outcomes in a diagnostic section. Report label-reference agreement separately from the frequency predictor.

- [ ] **Step 6: Implement atomic artifact writers and CLI**

Write JSON/text to a sibling temporary path then `replace()` it. Save the small model to a temporary `.pt` path and replace the final path. Keep model imports inside the `train` command path so `support` never imports or initializes Torch training; `train` refuses to run when the mode's support gate is blocked.

- [ ] **Step 7: Run focused GREEN and direct-script smoke tests**

Run all policy-learning and exporter tests, then invoke the script through `D:\anaconda\envs\stsai\python.exe analysis_scripts\noncombat_policy_learning.py --help`. Expected: exit 0 and both subcommands listed.

- [ ] **Step 8: Mark OpenSpec tasks 4.4 and 5.1-5.5 complete, review, and commit**

```powershell
git add analysis_scripts/noncombat_policy_learning.py analysis_scripts/noncombat_policy_dataset.py analysis_scripts/noncombat_policy_model.py tests/test_noncombat_policy_learning.py openspec/changes/add-noncombat-policy-learning-pilot/tasks.md
git commit -m "feat: add noncombat policy pilot evaluation"
```

---

### Task 5: Frozen Batch 2 Pilot Evidence And Final Verification

**Files:**
- Create: `reports/noncombat_policy_learning_source_20260712.json`
- Create: `reports/noncombat_policy_learning_support_20260712.md`
- Create when allowed: `reports/noncombat_policy_learning_current_20260712.md`
- Create when allowed: `reports/noncombat_policy_learning_bottled_20260712.md`
- Modify: `openspec/changes/add-noncombat-policy-learning-pilot/tasks.md`
- Modify: `.superpowers/sdd/progress.md` (ignored recovery ledger)

**Interfaces:**
- The source manifest names candidate `f321cb05a40c808d3abfba8b977dfe8988b8ee47`, cutoff `1783787478`, upper bound `1783790134`, the exact 25 run filenames from `trainable_baseline_qualification_batch2_retry1.md`, source report SHA-256 `B526552829D3B844F141C48A081C461E7CDE9F97F1948B6F24473702CF628148`, and hashes of generated v2 inputs.

- [ ] **Step 1: Record pre-run isolation evidence**

Read and hash the live CommunicationMod config plus enumerate active production checkpoint path, size, and mtime. Store this only in the evidence report/manifest; do not modify either source.

- [ ] **Step 2: Export the bounded v2 sample set**

Run the exporter with `--since-unix 1783787478`, `--until-unix 1783790134`, `--trace-tail 10000`, explicit behavior id/commit, and all 25 run files. Use native Bottled mode and write a separately named sample JSONL outside existing files.

- [ ] **Step 3: Run support-only evaluation first**

Run both Current and Bottled support modes. Preserve the exact commands, input hashes, trajectory counts, category blocks, and result. If either mode is blocked, do not lower thresholds.

- [ ] **Step 4: Run bounded supervised modes only when allowed**

For each allowed mode, run CPU training with the fixed defaults and explicit output directory. Preserve model hash and reviewed JSON/Markdown metrics. Do not copy artifacts into `checkpoints/`.

- [ ] **Step 5: Obtain independent raw-evidence review**

Give the reviewer source/sample/split/metrics/report paths and ask it to recompute trajectory disjointness, support counts, label-source isolation, candidate legality, and absence of causal-uplift claims. Correct every accepted finding before marking task 6.4 complete.

- [ ] **Step 6: Run focused and full verification**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp .pytest_tmp\policy-final-focused tests\test_noncombat_rl_decision_loop.py tests\test_noncombat_policy_learning.py -q
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp .pytest_tmp\policy-final-full
openspec validate add-noncombat-policy-learning-pilot --strict
openspec validate --all --strict
git diff --check
```

Expected: both pytest commands pass, both OpenSpec validations pass, and diff check is clean.

- [ ] **Step 7: Recheck isolation and complete tasks**

Rehash live config and compare checkpoint inventory with Step 1. Mark tasks 6.1-6.4 and 7.1-7.4 complete only when unchanged. Task 7.5 is complete after the reviewed evidence commit.

- [ ] **Step 8: Commit reviewed evidence**

Stage only the reviewed reports, source manifest, task state, and any final test correction:

```powershell
git add reports/noncombat_policy_learning_*_20260712.* openspec/changes/add-noncombat-policy-learning-pilot/tasks.md tests/test_noncombat_rl_decision_loop.py tests/test_noncombat_policy_learning.py analysis_scripts/noncombat_rl_decision_loop.py analysis_scripts/noncombat_policy_dataset.py analysis_scripts/noncombat_policy_model.py analysis_scripts/noncombat_policy_learning.py
git commit -m "docs: record noncombat policy learning pilot"
```

Do not archive the change until a final whole-branch review confirms every task and report claim.
