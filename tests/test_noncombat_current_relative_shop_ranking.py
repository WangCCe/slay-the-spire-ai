from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_current_relative_shop_ranking as relative
from analysis_scripts import noncombat_route_counterfactual_ranking as route


def _candidate(index: int) -> dict[str, Any]:
    return {
        "action_id": f"shop:test:{index}",
        "available": True,
        "category": "shop",
        "kind": "buy_card" if index == 0 else "leave",
        "label": f"option {index}",
        "raw": {"bits": index, "idx1": index, "idx2": 0},
    }


def _row(seed: int, *, current: int = 1) -> route.RouteRow:
    candidates = (_candidate(0), _candidate(1))
    return route.RouteRow(
        seed=seed,
        decision_index=0,
        source_sha256=f"{seed:064x}",
        state_features=torch.tensor([1.0, 0.0], dtype=torch.float32),
        candidate_features=torch.tensor([[2.0, 0.0], [-2.0, 0.0]], dtype=torch.float32),
        candidates=candidates,
        branch_outcomes=(
            {"action_id": candidates[0]["action_id"], "total_return": 1.0},
            {"action_id": candidates[1]["action_id"], "total_return": 0.0},
        ),
        current_action_id=candidates[current]["action_id"],
    )


def _partition(name: str = "development", count: int = 8) -> route.RoutePartition:
    rows = tuple(_row(seed) for seed in range(1, count + 1))
    return route.RoutePartition(
        name=name, seeds=tuple(row.seed for row in rows), rows=rows,
        action_branches=2 * len(rows), root_native_transitions=len(rows),
        censored_sources=(), budget_exhausted=False,
    )


def test_current_relative_training_learns_positive_margin() -> None:
    rows = _partition(count=16).rows
    model, history = relative.train_current_relative(rows, epochs=16)
    gated = relative.evaluate_gated(model, rows, score_margin=0.0)

    assert history[-1]["mean_batch_loss"] < history[0]["mean_batch_loss"]
    assert gated["mean_regret"] == 0.0
    assert gated["override_count"] == len(rows)


def test_score_margin_keeps_current_when_override_is_too_small() -> None:
    class Fixed(torch.nn.Module):
        def forward(self, _state: torch.Tensor, candidates: torch.Tensor) -> torch.Tensor:
            return torch.tensor([0.1, 0.0], dtype=torch.float32)[: candidates.shape[0]]

    result = relative.evaluate_gated(Fixed(), (_row(1),), score_margin=0.2)

    assert result["override_count"] == 0
    assert result["predictions"][0]["action_id"] == _candidate(1)["action_id"]


def test_fresh_evaluation_reports_safe_gated_improvement(monkeypatch: pytest.MonkeyPatch) -> None:
    partition = _partition(count=8)
    monkeypatch.setattr(relative.ranking, "_collect_partition", lambda *_args, **_kwargs: partition)
    model, _ = relative.train_current_relative(partition.rows, epochs=16)
    selection = relative.TrainSelection(
        model=model,
        selected_epoch=16,
        selected_margin=0.0,
        metrics={"selected_epoch": 16, "selected_score_margin": 0.0},
    )
    ticks = iter((0.0, 1.0))

    result = relative.evaluate_fresh(
        lambda _seed: object(), lambda _seed: object(), selection,
        fresh_seeds=tuple(range(8)), minimum_rows=8, minimum_informative=8,
        maximum_charged_seconds=10.0, clock=lambda: next(ticks),
    )

    assert result.report["verdict"] == "current_relative_shop_ranker_ready_for_live_shadow_proposal"
    assert all(result.metrics["checks"].values())


def test_artifacts_round_trip_and_match_manifest(tmp_path: Path) -> None:
    partition = _partition()
    policy = {"maximum_regret": 1.0, "mean_regret": 0.5, "predictions": []}
    result = relative.CurrentRelativeResult(
        configuration={"schema_version": relative.SCHEMA_VERSION},
        fresh=partition,
        model={"selected_epoch": 1, "selected_score_margin": 0.0},
        metrics={
            "changes_vs_current": {"corrected": 1, "worsened": 0},
            "fresh": {"current": policy, "gated": {**policy, "override_count": 1}},
        },
        report={"fresh": {"source_count": 8}, "verdict": "test"},
    )
    output = tmp_path / "relative-shop"
    relative.write_artifacts(
        output, result, {"source": {"commit": "a" * 40}},
        {"path": "train.json", "sha256": "b" * 64},
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 5
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    encoded = (output / "fresh_dataset.json").read_bytes()
    assert route.encode_partition(route.restore_partition(encoded)) == encoded
