"""Train one candidate-only shop value baseline from a committed corpus."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from typing import Any

import torch
import torch.nn.functional as F

from analysis_scripts.noncombat_state_conditioned_ranker import (
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
)


DEFAULT_CORPUS = Path(
    "reports/noncombat_shop_counterfactual_outcomes_20260814_r1/source_rows.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_shop_candidate_value_baseline_20260814_r1"
)
EXPECTED_CORPUS_SHA256 = (
    "5c66ed86b06202ab5f23b0023591c7991aa20301ccb2b60252d7113cfe86b2af"
)
EXPECTED_SOURCE_COUNT = 43
TRAIN_SOURCE_COUNT = 32
FIT_SOURCE_COUNT = 24
TUNE_SOURCE_COUNT = 8
HOLDOUT_SOURCE_COUNT = 11
CHECKPOINT_EPOCHS = (1, 2, 4, 8, 16, 32)
MODEL_SEED = 20260814
LEARNING_RATE = 1e-3
BATCH_SIZE = 16
IDENTITY_BUCKETS = 128
ACTION_KINDS = (
    "buy_card",
    "buy_potion",
    "buy_relic",
    "leave",
    "remove_card",
)
SCALAR_FEATURES = ("price", "has_price", "slot", "upgrade_count", "upgraded")
FEATURE_DIM = len(ACTION_KINDS) + len(SCALAR_FEATURES) + IDENTITY_BUCKETS
SCHEMA_VERSION = "noncombat-shop-candidate-value-baseline-v1"
MODEL_SCHEMA_VERSION = "noncombat-shop-candidate-value-model-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-shop-candidate-value-manifest-v1"
BOUND_SOURCE_PATHS = (
    Path("analysis_scripts/noncombat_shop_candidate_value_baseline.py"),
    Path("analysis_scripts/noncombat_state_conditioned_ranker.py"),
)


class ShopBaselineBlocked(RuntimeError):
    """Raised when fixed training evidence cannot be produced safely."""


@dataclass(frozen=True)
class ShopRow:
    seed: int
    decision_index: int
    source_sha256: str
    state_features: torch.Tensor
    candidate_features: torch.Tensor
    candidates: tuple[dict[str, Any], ...]
    branch_outcomes: tuple[dict[str, Any], ...]
    current_action_id: str

    @property
    def action_returns(self) -> tuple[float, ...]:
        return tuple(float(row["total_return"]) for row in self.branch_outcomes)

    @property
    def informative(self) -> bool:
        return max(self.action_returns) > min(self.action_returns)


@dataclass(frozen=True)
class ShopSplit:
    fit: tuple[ShopRow, ...]
    tune: tuple[ShopRow, ...]
    holdout: tuple[ShopRow, ...]


@dataclass(frozen=True)
class BaselineResult:
    configuration: dict[str, Any]
    split: dict[str, Any]
    model: dict[str, Any]
    metrics: dict[str, Any]
    report: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShopBaselineBlocked(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ShopBaselineBlocked(f"{label} must be finite")
    return result


def _candidate_identity(candidate: Mapping[str, Any]) -> str:
    raw = candidate.get("raw")
    if not isinstance(raw, Mapping):
        raise ShopBaselineBlocked("candidate raw fields are absent")
    item_id = raw.get("id")
    label = candidate.get("label")
    identity = item_id if isinstance(item_id, str) and item_id else label
    if not isinstance(identity, str) or not identity:
        raise ShopBaselineBlocked("candidate identity is absent")
    return f"{candidate.get('kind')}:{identity.casefold()}"


def encode_candidate(candidate: Mapping[str, Any]) -> torch.Tensor:
    kind = candidate.get("kind")
    if kind not in ACTION_KINDS:
        raise ShopBaselineBlocked(f"unsupported shop action kind: {kind!r}")
    raw = candidate.get("raw")
    if not isinstance(raw, Mapping):
        raise ShopBaselineBlocked("candidate raw fields are absent")
    values = [0.0] * FEATURE_DIM
    values[ACTION_KINDS.index(str(kind))] = 1.0
    offset = len(ACTION_KINDS)
    price = raw.get("price")
    if price is not None:
        values[offset] = max(0.0, min(_finite_number(price, "price") / 200.0, 2.0))
        values[offset + 1] = 1.0
    slot = raw.get("slot")
    if slot is not None:
        values[offset + 2] = max(
            0.0, min(_finite_number(slot, "slot") / 8.0, 2.0)
        )
    upgrade_count = raw.get("upgrade_count", 0)
    values[offset + 3] = max(
        0.0, min(_finite_number(upgrade_count, "upgrade_count") / 5.0, 2.0)
    )
    values[offset + 4] = float(bool(raw.get("upgraded", False)))
    bucket = int(
        hashlib.sha256(_candidate_identity(candidate).encode("utf-8")).hexdigest(), 16
    ) % IDENTITY_BUCKETS
    values[offset + len(SCALAR_FEATURES) + bucket] = 1.0
    result = torch.tensor(values, dtype=torch.float32, device="cpu")
    if result.shape != (FEATURE_DIM,) or not torch.isfinite(result).all().item():
        raise ShopBaselineBlocked("candidate feature contract differs")
    return result


def _parse_row(value: Any) -> ShopRow:
    if not isinstance(value, Mapping):
        raise ShopBaselineBlocked("shop source row must be an object")
    seed = value.get("seed")
    decision_index = value.get("decision_index")
    source_sha256 = value.get("source_sha256")
    candidates = value.get("candidates")
    outcomes = value.get("branch_outcomes")
    current_action_id = value.get("current_action_id")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ShopBaselineBlocked("source seed differs")
    if isinstance(decision_index, bool) or not isinstance(decision_index, int):
        raise ShopBaselineBlocked("decision index differs")
    if (
        not isinstance(source_sha256, str)
        or len(source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_sha256)
    ):
        raise ShopBaselineBlocked("source identity differs")
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise ShopBaselineBlocked("candidate support differs")
    if not isinstance(outcomes, list) or len(outcomes) != len(candidates):
        raise ShopBaselineBlocked("outcome alignment differs")
    normalized_candidates: list[dict[str, Any]] = []
    normalized_outcomes: list[dict[str, Any]] = []
    candidate_ids: list[str] = []
    for candidate, outcome in zip(candidates, outcomes, strict=True):
        if not isinstance(candidate, dict) or not isinstance(outcome, dict):
            raise ShopBaselineBlocked("candidate outcome row differs")
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or outcome.get("action_id") != action_id:
            raise ShopBaselineBlocked("candidate outcome identity differs")
        _finite_number(outcome.get("total_return"), "total_return")
        candidate_ids.append(action_id)
        normalized_candidates.append(candidate)
        normalized_outcomes.append(outcome)
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ShopBaselineBlocked("candidate identities are not unique")
    if current_action_id not in candidate_ids:
        raise ShopBaselineBlocked("Current action is not legal")
    candidate_features = torch.stack(
        tuple(encode_candidate(candidate) for candidate in normalized_candidates)
    )
    return ShopRow(
        seed=seed,
        decision_index=decision_index,
        source_sha256=source_sha256,
        state_features=torch.zeros(FEATURE_DIM, dtype=torch.float32, device="cpu"),
        candidate_features=candidate_features,
        candidates=tuple(normalized_candidates),
        branch_outcomes=tuple(normalized_outcomes),
        current_action_id=str(current_action_id),
    )


def load_corpus(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_CORPUS_SHA256,
    expected_source_count: int = EXPECTED_SOURCE_COUNT,
) -> tuple[ShopRow, ...]:
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise ShopBaselineBlocked("bound shop corpus identity differs")
    raw = json.loads(payload.decode("ascii"))
    if not isinstance(raw, list) or len(raw) != expected_source_count:
        raise ShopBaselineBlocked("bound shop corpus source count differs")
    rows = tuple(_parse_row(value) for value in raw)
    sources = [row.source_sha256 for row in rows]
    if len(set(sources)) != len(sources):
        raise ShopBaselineBlocked("shop source identities are not unique")
    return rows


def _hash_order(rows: Sequence[ShopRow], namespace: str) -> tuple[ShopRow, ...]:
    return tuple(
        sorted(
            rows,
            key=lambda row: hashlib.sha256(
                f"{namespace}:{row.source_sha256}".encode("ascii")
            ).hexdigest(),
        )
    )


def split_rows(rows: Sequence[ShopRow]) -> ShopSplit:
    normalized = tuple(rows)
    if len(normalized) != EXPECTED_SOURCE_COUNT:
        raise ShopBaselineBlocked("shop split source count differs")
    ordered = _hash_order(normalized, "shop-holdout-v1")
    holdout = ordered[:HOLDOUT_SOURCE_COUNT]
    train = ordered[HOLDOUT_SOURCE_COUNT:]
    train_ordered = _hash_order(train, "shop-tune-v1")
    tune = train_ordered[:TUNE_SOURCE_COUNT]
    fit = train_ordered[TUNE_SOURCE_COUNT:]
    if (len(fit), len(tune), len(holdout)) != (
        FIT_SOURCE_COUNT,
        TUNE_SOURCE_COUNT,
        HOLDOUT_SOURCE_COUNT,
    ):
        raise ShopBaselineBlocked("shop split sizes differ")
    partitions = [
        {row.source_sha256 for row in partition}
        for partition in (fit, tune, holdout)
    ]
    if partitions[0] & partitions[1] or partitions[0] & partitions[2] or partitions[1] & partitions[2]:
        raise ShopBaselineBlocked("shop source partitions overlap")
    return ShopSplit(fit=fit, tune=tune, holdout=holdout)


def _new_model() -> StateConditionedCandidateRanker:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(MODEL_SEED)
        model = StateConditionedCandidateRanker(FEATURE_DIM, DEFAULT_HIDDEN_DIM)
    return model.to(device="cpu", dtype=torch.float32)


def _batch_loss(
    model: StateConditionedCandidateRanker, rows: Sequence[ShopRow]
) -> torch.Tensor | None:
    losses: list[torch.Tensor] = []
    weights: list[float] = []
    for row in rows:
        scores = model(row.state_features, row.candidate_features)
        returns = row.action_returns
        for left in range(len(returns)):
            for right in range(left + 1, len(returns)):
                difference = returns[left] - returns[right]
                if difference == 0:
                    continue
                better, worse = (left, right) if difference > 0 else (right, left)
                weight = abs(difference)
                losses.append(weight * F.softplus(-(scores[better] - scores[worse])))
                weights.append(weight)
    if not losses:
        return None
    return torch.stack(losses).sum() / math.fsum(weights)


def train_model(
    rows: Sequence[ShopRow], *, epochs: int
) -> tuple[StateConditionedCandidateRanker, list[dict[str, float | int]]]:
    normalized = tuple(rows)
    if not normalized or epochs <= 0:
        raise ShopBaselineBlocked("training rows or epochs are invalid")
    model = _new_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    history: list[dict[str, float | int]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        losses: list[float] = []
        for offset in range(0, len(normalized), BATCH_SIZE):
            loss = _batch_loss(model, normalized[offset : offset + BATCH_SIZE])
            if loss is None:
                continue
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            losses.append(float(loss.detach().item()))
        if not losses:
            raise ShopBaselineBlocked("training rows contain no unequal returns")
        history.append(
            {"epoch": epoch, "mean_batch_loss": math.fsum(losses) / len(losses)}
        )
    model.eval()
    return model, history


def evaluate_model(
    model: StateConditionedCandidateRanker, rows: Sequence[ShopRow]
) -> dict[str, Any]:
    regrets: list[float] = []
    weighted_correct = 0.0
    weighted_total = 0.0
    predictions: list[dict[str, Any]] = []
    model.eval()
    with torch.no_grad():
        for row in rows:
            scores = model(row.state_features, row.candidate_features)
            predicted = int(torch.argmax(scores).item())
            returns = row.action_returns
            regret = max(returns) - returns[predicted]
            regrets.append(regret)
            for left in range(len(returns)):
                for right in range(left + 1, len(returns)):
                    difference = returns[left] - returns[right]
                    if difference == 0:
                        continue
                    weight = abs(difference)
                    score_difference = float(scores[left].item() - scores[right].item())
                    if score_difference * difference > 0:
                        weighted_correct += weight
                    elif score_difference == 0:
                        weighted_correct += 0.5 * weight
                    weighted_total += weight
            predictions.append(
                {
                    "action_id": row.candidates[predicted]["action_id"],
                    "decision_index": row.decision_index,
                    "regret": regret,
                    "seed": row.seed,
                    "source_sha256": row.source_sha256,
                }
            )
    if not regrets or weighted_total <= 0:
        raise ShopBaselineBlocked("evaluation support is insufficient")
    return {
        "maximum_regret": max(regrets),
        "mean_regret": math.fsum(regrets) / len(regrets),
        "predictions": predictions,
        "weighted_pairwise_accuracy": weighted_correct / weighted_total,
    }


def evaluate_current(rows: Sequence[ShopRow]) -> dict[str, Any]:
    regrets: list[float] = []
    predictions: list[dict[str, Any]] = []
    for row in rows:
        action_ids = [candidate["action_id"] for candidate in row.candidates]
        selected = action_ids.index(row.current_action_id)
        returns = row.action_returns
        regret = max(returns) - returns[selected]
        regrets.append(regret)
        predictions.append(
            {
                "action_id": row.current_action_id,
                "decision_index": row.decision_index,
                "regret": regret,
                "seed": row.seed,
                "source_sha256": row.source_sha256,
            }
        )
    if not regrets:
        raise ShopBaselineBlocked("Current baseline has no rows")
    return {
        "maximum_regret": max(regrets),
        "mean_regret": math.fsum(regrets) / len(regrets),
        "predictions": predictions,
    }


def _prediction_changes(
    current: Mapping[str, Any], trained: Mapping[str, Any]
) -> dict[str, int]:
    before = {row["source_sha256"]: row for row in current["predictions"]}
    after = {row["source_sha256"]: row for row in trained["predictions"]}
    if set(before) != set(after):
        raise ShopBaselineBlocked("prediction source sets differ")
    changed = corrected = worsened = 0
    for source, current_row in before.items():
        trained_row = after[source]
        changed += int(current_row["action_id"] != trained_row["action_id"])
        corrected += int(trained_row["regret"] < current_row["regret"])
        worsened += int(trained_row["regret"] > current_row["regret"])
    return {"action_changes": changed, "corrected": corrected, "worsened": worsened}


def _row_summary(rows: Sequence[ShopRow]) -> dict[str, Any]:
    return {
        "action_branches": sum(len(row.candidates) for row in rows),
        "informative_sources": sum(row.informative for row in rows),
        "source_count": len(rows),
    }


def _encode_model(model: StateConditionedCandidateRanker) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().to(dtype=torch.float32).contiguous()
        state[name] = {
            "shape": list(value.shape),
            "values": value.reshape(-1).tolist(),
        }
    return state


def run_experiment(rows: Sequence[ShopRow], *, clock: Any = time.monotonic) -> BaselineResult:
    started = float(clock())
    split = split_rows(rows)
    checkpoints: list[dict[str, Any]] = []
    selected_epoch: int | None = None
    selected_key: tuple[float, float, int] | None = None
    for epoch in CHECKPOINT_EPOCHS:
        candidate, history = train_model(split.fit, epochs=epoch)
        tune = evaluate_model(candidate, split.tune)
        key = (tune["mean_regret"], -tune["weighted_pairwise_accuracy"], epoch)
        checkpoints.append(
            {
                "epoch": epoch,
                "fit_final_loss": history[-1]["mean_batch_loss"],
                "tune": {key: value for key, value in tune.items() if key != "predictions"},
            }
        )
        if selected_key is None or key < selected_key:
            selected_key = key
            selected_epoch = epoch
    if selected_epoch is None:
        raise ShopBaselineBlocked("train-only checkpoint selection failed")
    trained_model, final_history = train_model(
        split.fit + split.tune, epochs=selected_epoch
    )

    untrained = evaluate_model(_new_model(), split.holdout)
    trained = evaluate_model(trained_model, split.holdout)
    current = evaluate_current(split.holdout)
    changes = _prediction_changes(current, trained)
    checks = {
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "holdout_support": len(split.holdout) == HOLDOUT_SOURCE_COUNT,
        "maximum_regret_noninferior_to_current": (
            trained["maximum_regret"] <= current["maximum_regret"] + 1e-12
        ),
        "mean_regret_improves_current": (
            trained["mean_regret"] + 1e-12 < current["mean_regret"]
        ),
        "pairwise_accuracy_improves_initialization": (
            trained["weighted_pairwise_accuracy"]
            > untrained["weighted_pairwise_accuracy"] + 1e-12
        ),
        "worsened_not_more_than_corrected": changes["worsened"] <= changes["corrected"],
    }
    verdict = (
        "shop_candidate_value_baseline_ready_for_fresh_shadow_proposal"
        if all(checks.values())
        else "shop_candidate_value_baseline_not_ready_after_holdout"
    )
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0:
        raise ShopBaselineBlocked("training elapsed time differs")
    split_artifact = {
        "fit_sources": [row.source_sha256 for row in split.fit],
        "holdout_access_count": 1,
        "holdout_sources": [row.source_sha256 for row in split.holdout],
        "schema_version": "noncombat-shop-candidate-value-split-v1",
        "tune_sources": [row.source_sha256 for row in split.tune],
    }
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "holdout": {"current": current, "trained": trained, "untrained": untrained},
        "selection": {"checkpoints": checkpoints, "selected_epoch": selected_epoch},
        "training_final_history": final_history,
        "verdict": verdict,
    }
    configuration = {
        "action_kinds": list(ACTION_KINDS),
        "batch_size": BATCH_SIZE,
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "feature_dim": FEATURE_DIM,
        "feature_scope": "candidate-only-zero-state",
        "identity_buckets": IDENTITY_BUCKETS,
        "learning_rate": LEARNING_RATE,
        "model_seed": MODEL_SEED,
        "schema_version": SCHEMA_VERSION,
        "split_sizes": {"fit": FIT_SOURCE_COUNT, "holdout": HOLDOUT_SOURCE_COUNT, "tune": TUNE_SOURCE_COUNT},
    }
    model = {
        "architecture": trained_model.architecture_metadata(),
        "feature_scope": "candidate-only-zero-state",
        "model_seed": MODEL_SEED,
        "schema_version": MODEL_SCHEMA_VERSION,
        "selected_epoch": selected_epoch,
        "state": _encode_model(trained_model),
    }
    report = {
        "authority": {
            "formal_rl": False,
            "gameplay": False,
            "policy_loading": False,
            "promotion": False,
            "qualification": False,
        },
        "charged_seconds": elapsed,
        "fit": _row_summary(split.fit),
        "holdout": _row_summary(split.holdout),
        "holdout_access_count": 1,
        "limitations": ["candidate-only", "no full game state", "single small holdout"],
        "operations": {
            "communication_mod": False,
            "gameplay": False,
            "model_fitting": True,
            "native_loading": False,
            "production_checkpoint_access": False,
            "protected_seed_access": False,
            "training": True,
        },
        "schema_version": SCHEMA_VERSION,
        "tune": _row_summary(split.tune),
        "verdict": verdict,
    }
    return BaselineResult(
        configuration=configuration,
        split=split_artifact,
        model=model,
        metrics=metrics,
        report=report,
    )


def _source_identity(repo_root: Path, corpus: Path) -> dict[str, Any]:
    files = []
    for relative in BOUND_SOURCE_PATHS:
        path = repo_root / relative
        files.append(
            {"path": relative.as_posix(), "sha256": _sha256_file(path), "size_bytes": path.stat().st_size}
        )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "corpus": {"path": corpus.as_posix(), "sha256": _sha256_file(corpus), "size_bytes": corpus.stat().st_size},
        "source": {
            "commit": commit,
            "files": files,
            "source_sha256": _sha256_bytes(_canonical_bytes(files)),
        },
    }


def write_artifacts(output: Path, result: BaselineResult, identity: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    payloads = {
        "configuration.json": result.configuration,
        "metrics.json": result.metrics,
        "model.json": result.model,
        "report.json": {**result.report, "identity": identity},
        "split.json": result.split,
    }
    for name, value in payloads.items():
        (output / name).write_bytes(_canonical_bytes(value))
    report = result.report
    metrics = result.metrics
    summary = "\n".join(
        [
            "# Shop Candidate Value Baseline",
            "",
            f"- Verdict: `{report['verdict']}`",
            f"- Selected epoch: `{metrics['selection']['selected_epoch']}`",
            f"- Fit/tune/holdout: `{report['fit']['source_count']}/{report['tune']['source_count']}/{report['holdout']['source_count']}`",
            f"- Current holdout mean regret: `{metrics['holdout']['current']['mean_regret']:.6f}`",
            f"- Trained holdout mean regret: `{metrics['holdout']['trained']['mean_regret']:.6f}`",
            f"- Trained holdout pairwise accuracy: `{metrics['holdout']['trained']['weighted_pairwise_accuracy']:.6f}`",
            "",
            "This candidate-only baseline has no full game-state input and grants no live policy authority.",
            "",
        ]
    )
    (output / "report.md").write_text(summary, encoding="ascii", newline="\n")
    artifacts = []
    for path in sorted(output.iterdir(), key=lambda item: item.name):
        if path.name == "artifact_manifest.json":
            continue
        artifacts.append(
            {"path": path.name, "sha256": _sha256_file(path), "size_bytes": path.stat().st_size}
        )
    manifest = {"artifacts": artifacts, "schema_version": MANIFEST_SCHEMA_VERSION}
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    corpus = (repo_root / args.corpus).resolve() if not Path(args.corpus).is_absolute() else Path(args.corpus).resolve()
    output = (repo_root / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir).resolve()
    if output.exists():
        raise ShopBaselineBlocked("output directory already exists")
    rows = load_corpus(corpus)
    result = run_experiment(rows)
    identity = _source_identity(repo_root, corpus)
    write_artifacts(output, result, identity)
    return {
        "holdout_sources": result.report["holdout"]["source_count"],
        "output_dir": output.as_posix(),
        "selected_epoch": result.metrics["selection"]["selected_epoch"],
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        raise ShopBaselineBlocked("unsupported command")
    print(json.dumps(execute_cli(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
