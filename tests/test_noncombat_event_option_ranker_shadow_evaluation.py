from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_event_option_counterfactual_ranking as training
from analysis_scripts import noncombat_event_option_ranker_shadow_evaluation as shadow
from analysis_scripts import noncombat_route_counterfactual_ranking as route


TRAINING_DIR = Path("reports/noncombat_event_option_counterfactual_ranking_20260814_r1")


def _candidate(index: int, event_id: str) -> dict[str, Any]:
    return {
        "action_id": f"event:{event_id}:option:{index}",
        "available": True,
        "category": "event",
        "kind": "event_option",
        "label": f"{event_id} option {index}",
        "raw": {"event_id": event_id, "idx1": index},
    }


def _row(
    seed: int,
    *,
    returns: tuple[float, float],
    current: int = 0,
) -> route.RouteRow:
    event_id = f"event_{seed}"
    candidates = (_candidate(0, event_id), _candidate(1, event_id))
    return route.RouteRow(
        seed=seed,
        decision_index=seed,
        source_sha256=f"{seed:064x}",
        state_features=torch.zeros(2, dtype=torch.float32),
        candidate_features=torch.tensor([[0.0, 0.0], [1.0, 0.0]]),
        candidates=candidates,
        branch_outcomes=(
            {"action_id": candidates[0]["action_id"], "total_return": returns[0]},
            {"action_id": candidates[1]["action_id"], "total_return": returns[1]},
        ),
        current_action_id=candidates[current]["action_id"],
    )


def _partition(*rows: route.RouteRow) -> route.RoutePartition:
    return route.RoutePartition(
        name="development",
        seeds=tuple(row.seed for row in rows),
        rows=tuple(rows),
        action_branches=2 * len(rows),
        root_native_transitions=len(rows),
        censored_sources=(),
        budget_exhausted=False,
    )


class _FixedModel(torch.nn.Module):
    def forward(self, _state: torch.Tensor, candidates: torch.Tensor) -> torch.Tensor:
        return candidates[:, 0]


def test_loads_exact_manifest_bound_training_model() -> None:
    model, identity = shadow.load_bound_model(TRAINING_DIR)

    assert model.training is False
    assert identity["selected_epoch"] == 1
    assert identity["selected_confidence_threshold"] == 0.5
    assert len(identity["model"]["sha256"]) == 64


def test_model_byte_drift_fails_preflight(tmp_path: Path) -> None:
    copied = tmp_path / "training"
    copied.mkdir()
    for name in ("artifact_manifest.json", "metrics.json", "model.json", "report.json"):
        shutil.copyfile(TRAINING_DIR / name, copied / name)
    with (copied / "model.json").open("ab") as stream:
        stream.write(b" ")

    with pytest.raises(shadow.EventShadowBlocked, match="model.json manifest"):
        shadow.load_bound_model(copied)


def test_fixed_shadow_gate_distinguishes_replication_from_regression() -> None:
    replicated, replicated_verdict = shadow.evaluate_shadow(
        _FixedModel(),
        _partition(_row(1, returns=(0.0, 1.0))),
        confidence_threshold=0.5,
        minimum_rows=1,
        minimum_informative=1,
        minimum_event_ids=1,
    )
    failed, failed_verdict = shadow.evaluate_shadow(
        _FixedModel(),
        _partition(_row(2, returns=(1.0, 0.0))),
        confidence_threshold=0.5,
        minimum_rows=1,
        minimum_informative=1,
        minimum_event_ids=1,
    )

    assert replicated_verdict == "event_ranker_shadow_benefit_replicated"
    assert all(replicated["checks"].values())
    assert failed_verdict == "event_ranker_shadow_benefit_not_replicated"
    assert failed["checks"]["mean_regret_improves_current"] is False
    assert failed["changes_vs_current"] == {
        "action_changes": 1,
        "corrected": 0,
        "worsened": 1,
    }


def test_shadow_artifacts_bind_dataset_metrics_and_report(tmp_path: Path) -> None:
    partition = _partition(_row(1, returns=(0.0, 1.0)))
    metrics, _ = shadow.evaluate_shadow(
        _FixedModel(),
        partition,
        confidence_threshold=0.5,
        minimum_rows=1,
        minimum_informative=1,
        minimum_event_ids=1,
    )
    output = tmp_path / "shadow"

    shadow._write_artifacts(
        output,
        configuration={"schema_version": shadow.SCHEMA_VERSION},
        partition=partition,
        metrics=metrics,
        report={"charged_seconds": 1.0, "verdict": metrics["verdict"]},
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 4
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    dataset = (output / "dataset.json").read_bytes()
    assert training.encode_event_partition(
        training.restore_event_partition(dataset)
    ) == dataset
