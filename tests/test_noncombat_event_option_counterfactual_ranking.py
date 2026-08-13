from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_event_option_counterfactual_ranking as event
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    StateConditionedPolicyInput,
)


def _candidate(index: int, *, event_id: str = "Big Fish") -> dict[str, Any]:
    return {
        "action_id": f"event:big_fish:option:{index}",
        "available": True,
        "category": "event",
        "kind": "event_option",
        "label": f"Big Fish option {index}",
        "raw": {"event_id": event_id, "idx1": index},
    }


def _outcome(index: int, value: float) -> dict[str, Any]:
    return {"action_id": _candidate(index)["action_id"], "total_return": value}


def _row(
    *,
    seed: int = 1,
    current: int = 0,
    returns: tuple[float, float] = (0.0, 1.0),
) -> route.RouteRow:
    return route.RouteRow(
        seed=seed,
        decision_index=3,
        source_sha256=f"{seed:064x}",
        state_features=torch.tensor([0.25, 0.0], dtype=torch.float32),
        candidate_features=torch.tensor([[0.0, 0.0], [1.0, 0.0]], dtype=torch.float32),
        candidates=(_candidate(0), _candidate(1)),
        branch_outcomes=(_outcome(0, returns[0]), _outcome(1, returns[1])),
        current_action_id=_candidate(current)["action_id"],
    )


def _partition(
    *, name: str = "train", rows: tuple[route.RouteRow, ...] | None = None
) -> route.RoutePartition:
    values = rows or (_row(),)
    return route.RoutePartition(
        name=name,
        seeds=tuple(sorted({row.seed for row in values})),
        rows=values,
        action_branches=2 * len(values),
        root_native_transitions=len(values),
        censored_sources=(),
        budget_exhausted=False,
    )


@dataclass
class _Environment:
    stage: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "category": None if self.stage else "event",
            "terminal": self.stage > 0,
        }

    def legal_actions(self) -> list[dict[str, Any]]:
        return [] if self.stage else [_candidate(0), _candidate(1)]


class _Session:
    def evaluate(self, **_kwargs: Any) -> dict[str, str]:
        return {"action_id": _candidate(0)["action_id"]}


def test_shared_partition_collector_supports_event_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        route.credit,
        "_environment_state",
        lambda environment: (
            copy.deepcopy(environment.snapshot()),
            copy.deepcopy(environment.legal_actions()),
        ),
    )

    def advance(environment: _Environment) -> tuple[_Environment, dict[str, Any]]:
        return _Environment(stage=environment.stage + 1), {}

    monkeypatch.setattr(route.credit, "_advance_native", advance)

    def projector(*_args: Any) -> StateConditionedPolicyInput:
        return StateConditionedPolicyInput(
            state_features=torch.zeros(2),
            candidate_features=torch.tensor([[0.0, 0.0], [1.0, 0.0]]),
        )

    def evaluator(_environment: Any, *, action_id: str, source_category: str, **_kwargs: Any) -> Any:
        assert source_category == "event"
        index = int(action_id.rsplit(":", 1)[-1])
        return type(
            "Trace",
            (),
            {
                "action_id": action_id,
                "action_sequence": (action_id,),
                "floor_progress": float(index),
                "initial_transition_sha256": "1" * 64,
                "terminal_state_sha256": "2" * 64,
                "terminal_summary": {"floor": index, "outcome": "player_loss"},
                "terminal_victory": 0,
                "total_return": float(index),
                "transition_count": 1,
            },
        )()

    result = route.collect_outcome_partition(
        lambda _seed: _Environment(),
        lambda _seed: _Session(),
        target_category="event",
        name="train",
        seeds=(1,),
        max_source_states=2,
        max_action_branches=4,
        max_censored_sources=2,
        max_route_states_per_seed=1,
        max_decisions=4,
        projector=projector,
        branch_evaluator=evaluator,
    )

    assert len(result.rows) == 1
    assert result.rows[0].informative is True
    assert result.rows[0].current_action_id == _candidate(0)["action_id"]


def test_event_partition_round_trips_exactly() -> None:
    source = _partition()
    payload = event.encode_event_partition(source)
    restored = event.restore_event_partition(payload)

    assert event.encode_event_partition(restored) == payload
    assert event._event_ids(restored) == ("Big Fish",)


class _FixedModel(torch.nn.Module):
    def forward(self, _state: torch.Tensor, candidates: torch.Tensor) -> torch.Tensor:
        return candidates[:, 0]


def test_confidence_gate_overrides_only_at_selected_margin() -> None:
    rows = (_row(),)

    accepted = event.evaluate_gated_policy(
        _FixedModel(), rows, confidence_threshold=0.70
    )
    rejected = event.evaluate_gated_policy(
        _FixedModel(), rows, confidence_threshold=0.80
    )

    assert accepted["override_count"] == 1
    assert accepted["mean_regret"] == 0.0
    assert rejected["override_count"] == 0
    assert rejected["mean_regret"] == 1.0


def test_train_support_failure_prevents_development_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def collect(*_args: Any, name: str, **_kwargs: Any) -> route.RoutePartition:
        calls.append(name)
        return _partition(name=name)

    monkeypatch.setattr(event, "_collect_partition", collect)

    with pytest.raises(event.EventRankingBlocked, match="train event support"):
        event.run_experiment(
            lambda _seed: object(),
            lambda _seed: object(),
            train_seeds=(1,),
            development_seeds=(2,),
            minimum_train_rows=2,
            minimum_train_informative=1,
            maximum_charged_seconds=100.0,
            clock=iter(range(100)).__next__,
        )

    assert calls == ["train"]


def test_artifacts_bind_event_datasets_and_manifest(tmp_path: Path) -> None:
    train = _partition(name="train")
    development = _partition(name="development")
    policy = {
        "maximum_regret": 1.0,
        "mean_regret": 1.0,
        "p95_regret": 1.0,
        "predictions": [],
        "unique_best_accuracy": 0.0,
    }
    result = route.ExperimentResult(
        configuration={"schema_version": event.SCHEMA_VERSION},
        train=train,
        development=development,
        model={"schema_version": event.MODEL_SCHEMA_VERSION},
        metrics={
            "changes_vs_current": {"action_changes": 0, "corrected": 0, "worsened": 0},
            "development": {
                "current": dict(policy),
                "gated": dict(policy),
                "raw": {**policy, "weighted_pairwise_accuracy": 0.5},
                "untrained": {**policy, "weighted_pairwise_accuracy": 0.5},
            },
            "selection": {
                "selected_confidence_threshold": 0.9,
                "selected_epoch": 1,
            },
        },
        report={"charged_seconds": 1.0, "verdict": "test"},
    )
    output = tmp_path / "event-ranker"

    event._write_artifacts(output, result, {"source": {"source_sha256": "a" * 64}})

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 6
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    assert event.encode_event_partition(
        event.restore_event_partition((output / "train_dataset.json").read_bytes())
    ) == (output / "train_dataset.json").read_bytes()
