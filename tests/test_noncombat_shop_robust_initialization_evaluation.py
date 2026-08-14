from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts import noncombat_shop_robust_initialization_evaluation as robust


def _candidate(index: int) -> dict[str, Any]:
    return {
        "action_id": f"shop:test:{index}",
        "available": True,
        "category": "shop",
        "kind": "buy_card" if index == 0 else "leave",
        "label": f"option {index}",
        "raw": {"bits": index, "idx1": index, "idx2": 0},
    }


def _partition() -> route.RoutePartition:
    rows = []
    for seed in range(1, 5):
        candidates = (_candidate(0), _candidate(1))
        rows.append(
            route.RouteRow(
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
                current_action_id=candidates[1]["action_id"],
            )
        )
    return route.RoutePartition(
        name="development", seeds=(1, 2, 3, 4), rows=tuple(rows),
        action_branches=8, root_native_transitions=4,
        censored_sources=(), budget_exhausted=False,
    )


def test_nearest_rank_q75_is_fixed() -> None:
    assert robust.nearest_rank_quantile(tuple(range(32)), 0.75) == 23.0


def test_model_identity_rejection_happens_before_decode(tmp_path: Path) -> None:
    path = tmp_path / "model.json"
    path.write_text("{}\n", encoding="ascii")

    with pytest.raises(robust.RobustShopEvaluationBlocked, match="identity differs"):
        robust.load_bound_model(path)


class _GoodModel(torch.nn.Module):
    def forward(self, _state: torch.Tensor, candidates: torch.Tensor) -> torch.Tensor:
        return candidates[:, 0]


class _BadModel(torch.nn.Module):
    def forward(self, _state: torch.Tensor, candidates: torch.Tensor) -> torch.Tensor:
        return -candidates[:, 0]


def test_robust_gate_can_pass_without_model_fitting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    partition = _partition()
    monkeypatch.setattr(robust.ranking, "_collect_partition", lambda *_args, **_kwargs: partition)
    monkeypatch.setattr(robust, "_new_untrained_model", lambda **_kwargs: _BadModel())
    ticks = iter((0.0, 1.0))

    result = robust.run_evaluation(
        lambda _seed: object(),
        lambda _seed: object(),
        _GoodModel(),
        {"architecture": {"hidden_dim": 64, "state_input_dim": 2}},
        evaluation_seeds=(1, 2, 3, 4),
        minimum_rows=4,
        minimum_informative=4,
        maximum_charged_seconds=10.0,
        clock=lambda: next(ticks),
    )

    assert result.report["verdict"] == "shop_ranker_ready_for_live_shadow_proposal"
    assert all(result.metrics["checks"].values())
    assert result.report["operations"]["model_fitting"] is False


def test_artifacts_round_trip_and_match_manifest(tmp_path: Path) -> None:
    partition = _partition()
    policy = {
        "maximum_regret": 1.0,
        "mean_regret": 0.5,
        "predictions": [],
        "weighted_pairwise_accuracy": 0.5,
    }
    result = robust.RobustEvaluationResult(
        configuration={"schema_version": robust.SCHEMA_VERSION},
        evaluation=partition,
        metrics={
            "current": policy,
            "trained": policy,
            "untrained_distribution": {"pairwise_q75": 0.5},
        },
        report={"evaluation": {"source_count": 4}, "verdict": "test"},
    )
    output = tmp_path / "robust-evaluation"

    robust.write_artifacts(
        output,
        result,
        {"source": {"commit": "a" * 40}},
        {"path": "model.json", "sha256": "b" * 64},
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 4
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    encoded = (output / "evaluation_dataset.json").read_bytes()
    assert route.encode_partition(route.restore_partition(encoded)) == encoded
