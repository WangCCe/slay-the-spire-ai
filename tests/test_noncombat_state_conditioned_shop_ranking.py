from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts import noncombat_shop_counterfactual_outcomes as shop
from analysis_scripts import noncombat_state_conditioned_shop_ranking as ranking


def _candidate(index: int) -> dict[str, Any]:
    kind = "buy_card" if index == 0 else "leave"
    return {
        "action_id": f"shop:{kind}:{index}",
        "available": True,
        "category": "shop",
        "kind": kind,
        "label": f"candidate {index}",
        "raw": {"bits": index, "idx1": index, "idx2": 0},
    }


def _route_row(seed: int) -> route.RouteRow:
    candidates = (_candidate(0), _candidate(1))
    return route.RouteRow(
        seed=seed,
        decision_index=seed % 3,
        source_sha256=f"{seed:064x}",
        state_features=torch.tensor([float(seed % 2), 1.0], dtype=torch.float32),
        candidate_features=torch.tensor([[2.0, 0.0], [-2.0, 0.0]], dtype=torch.float32),
        candidates=candidates,
        branch_outcomes=(
            {"action_id": candidates[0]["action_id"], "total_return": 1.0},
            {"action_id": candidates[1]["action_id"], "total_return": 0.0},
        ),
        current_action_id=candidates[1]["action_id"],
    )


def _partition(name: str, count: int = 8) -> route.RoutePartition:
    rows = tuple(_route_row(seed) for seed in range(1, count + 1))
    return route.RoutePartition(
        name=name,
        seeds=tuple(row.seed for row in rows),
        rows=rows,
        action_branches=2 * len(rows),
        root_native_transitions=len(rows),
        censored_sources=(),
        budget_exhausted=False,
    )


def test_partition_requires_and_preserves_projected_features() -> None:
    candidates = (_candidate(0), _candidate(1))
    outcome_row = shop.ShopOutcomeRow(
        seed=1,
        decision_index=0,
        source_sha256="1" * 64,
        current_action_id=candidates[1]["action_id"],
        action_kinds=("buy_card", "leave"),
        candidates=candidates,
        branch_outcomes=(
            {"action_id": candidates[0]["action_id"], "total_return": 1.0},
            {"action_id": candidates[1]["action_id"], "total_return": 0.0},
        ),
        replay={"passed": True},
        state_features=torch.tensor([0.5, 1.0], dtype=torch.float32),
        candidate_features=torch.tensor([[1.0, 0.0], [0.0, 1.0]], dtype=torch.float32),
    )
    result = shop.ShopOutcomeResult(
        rows=(outcome_row,),
        censored_sources=(),
        action_branches=2,
        root_native_transitions=1,
        budget_exhausted=False,
        charged_seconds=1.0,
        checks={},
        verdict="test",
    )

    partition = ranking._partition_from_result("train", result)

    assert torch.equal(partition.rows[0].state_features, outcome_row.state_features)
    assert torch.equal(partition.rows[0].candidate_features, outcome_row.candidate_features)


def test_train_support_failure_prevents_development_access(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def collect(*_args: Any, name: str, **_kwargs: Any) -> route.RoutePartition:
        calls.append(name)
        raise ranking.StateConditionedShopBlocked("train shop support floor is unmet")

    monkeypatch.setattr(ranking, "_collect_partition", collect)

    with pytest.raises(ranking.StateConditionedShopBlocked, match="train shop support"):
        ranking.run_experiment(
            lambda _seed: object(),
            lambda _seed: object(),
            train_seeds=(1,),
            development_seeds=(2,),
        )

    assert calls == ["train"]


def test_artifacts_round_trip_datasets_and_match_manifest(tmp_path: Path) -> None:
    train = _partition("train")
    development = _partition("development")
    policy = {
        "maximum_regret": 1.0,
        "mean_regret": 0.5,
        "predictions": [],
        "weighted_pairwise_accuracy": 0.5,
    }
    result = ranking.ShopRankingResult(
        configuration={"schema_version": ranking.SCHEMA_VERSION},
        train=train,
        development=development,
        model={"schema_version": ranking.MODEL_SCHEMA_VERSION},
        metrics={
            "development": {"current": policy, "trained": policy, "untrained": policy},
            "selection": {"selected_epoch": 1},
        },
        report={
            "development": {"source_count": 8},
            "train": {"source_count": 8},
            "verdict": "test",
        },
    )
    output = tmp_path / "shop-ranking"

    ranking._write_artifacts(output, result, {"source": {"commit": "a" * 40}})

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 6
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    assert route.encode_partition(route.restore_partition((output / "train_dataset.json").read_bytes())) == (output / "train_dataset.json").read_bytes()
    assert route.encode_partition(route.restore_partition((output / "development_dataset.json").read_bytes())) == (output / "development_dataset.json").read_bytes()
