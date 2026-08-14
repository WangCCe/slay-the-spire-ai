from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_shop_counterfactual_outcomes as shop
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    StateConditionedPolicyInput,
)


KINDS = ("buy_card", "buy_relic", "purge", "leave")


def _candidate(seed: int, index: int) -> dict[str, Any]:
    return {
        "action_id": f"shop:test_{seed}:{KINDS[index]}:{index}",
        "available": True,
        "category": "shop",
        "kind": KINDS[index],
        "label": f"Shop option {index}",
        "raw": {"price": 20 + index, "slot": index},
    }


@dataclass
class _ShopEnvironment:
    seed: int
    stage: int = 0

    def clone(self) -> "_ShopEnvironment":
        return type(self)(self.seed, self.stage)

    def snapshot(self) -> dict[str, Any]:
        terminal = self.stage > 0
        return {
            "category": None if terminal else "shop",
            "decision_count": self.stage,
            "state": {
                "floor": self.stage,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict[str, Any]]:
        return [] if self.stage else [_candidate(self.seed, index) for index in range(4)]


class _ShopSession:
    def __init__(self, seed: int) -> None:
        self.seed = seed

    def evaluate(
        self,
        *,
        snapshot: dict[str, Any],
        candidates: list[dict[str, Any]],
        decision_index: int,
    ) -> dict[str, Any]:
        assert decision_index == 0
        return {"action_id": candidates[-1]["action_id"]}


def _trace(action_id: str, *, delta: float = 0.0) -> shop.credit.BranchTrace:
    option = int(action_id.rsplit(":", 1)[-1])
    total_return = 0.25 + 0.5 * option + delta
    return shop.credit.BranchTrace(
        action_id=action_id,
        action_sequence=(action_id, "terminal"),
        floor_progress=total_return,
        initial_transition_sha256="1" * 64,
        terminal_state_sha256="2" * 64,
        terminal_summary={"floor": 10 + option, "outcome": "player_loss"},
        terminal_victory=0,
        total_return=total_return,
        transition_count=2,
    )


def _install_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shop.credit,
        "_environment_state",
        lambda environment: (
            copy.deepcopy(environment.snapshot()),
            copy.deepcopy(environment.legal_actions()),
        ),
    )

    def advance_native(
        environment: _ShopEnvironment,
    ) -> tuple[_ShopEnvironment, dict[str, Any]]:
        advanced = environment.clone()
        advanced.stage += 1
        return advanced, {"selected_action_id": _candidate(environment.seed, 3)["action_id"]}

    monkeypatch.setattr(shop.credit, "_advance_native", advance_native)


def _collect(
    evaluator: Any,
    *,
    seeds: tuple[int, ...] = (1,),
    replay_source_count: int = 1,
    projector: Any | None = None,
) -> shop.ShopOutcomeResult:
    ticks = iter(range(10_000))
    return shop.collect_shop_outcomes(
        _ShopEnvironment,
        _ShopSession,
        seeds=seeds,
        max_source_states=16,
        max_action_branches=64,
        max_censored_sources=8,
        max_shop_states_per_seed=1,
        replay_source_count=replay_source_count,
        minimum_complete_sources=len(seeds),
        minimum_informative_sources=len(seeds),
        minimum_action_kinds=4,
        max_decisions=8,
        maximum_charged_seconds=10_000,
        clock=lambda: next(ticks),
        branch_evaluator=evaluator,
        projector=projector,
    )


def test_collects_complete_informative_shop_rows_with_exact_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)
    sources: list[_ShopEnvironment] = []

    def evaluator(
        environment: _ShopEnvironment,
        *,
        action_id: str,
        source_category: str,
        **_kwargs: Any,
    ) -> shop.credit.BranchTrace:
        assert source_category == "shop"
        sources.append(environment)
        return _trace(action_id)

    result = _collect(evaluator, seeds=(1, 2), replay_source_count=2)

    assert result.verdict == "shop_counterfactual_signal_viable_for_learning_proposal"
    assert result.checks == {
        "action_kind_floor": True,
        "complete_source_floor": True,
        "informative_source_floor": True,
        "replay_count": True,
        "replay_identity": True,
    }
    assert len(result.rows) == 2
    assert result.action_branches == 8
    assert result.root_native_transitions == 2
    assert result.censored_sources == ()
    assert all(row.action_kinds == KINDS for row in result.rows)
    assert all(row.current_action_id.endswith(":3") for row in result.rows)
    assert all(row.replay and row.replay["passed"] for row in result.rows)
    assert all(environment.stage == 0 for environment in sources)


def test_registered_support_failure_censors_incomplete_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)

    def evaluator(*_args: Any, **_kwargs: Any) -> Any:
        raise shop.credit.CounterfactualCreditBlocked(
            "unsupported_shop_courier_restock_semantics"
        )

    result = _collect(evaluator)

    assert result.verdict == "shop_counterfactual_signal_not_viable"
    assert result.rows == ()
    assert len(result.censored_sources) == 1
    assert result.censored_sources[0]["reason"] == (
        "unsupported_shop_courier_restock_semantics"
    )


def test_opt_in_projection_is_captured_with_candidate_alignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)

    def projector(
        _snapshot: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> StateConditionedPolicyInput:
        return StateConditionedPolicyInput(
            state_features=torch.tensor([0.25, 1.0], dtype=torch.float32),
            candidate_features=torch.arange(
                len(candidates) * 2, dtype=torch.float32
            ).reshape(len(candidates), 2),
        )

    result = _collect(
        lambda _environment, *, action_id, **_kwargs: _trace(action_id),
        projector=projector,
    )

    assert torch.equal(
        result.rows[0].state_features,
        torch.tensor([0.25, 1.0], dtype=torch.float32),
    )
    assert result.rows[0].candidate_features.shape == (4, 2)


def test_replay_drift_fails_viability_without_discarding_complete_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)
    calls: dict[str, int] = {}

    def evaluator(
        _environment: _ShopEnvironment, *, action_id: str, **_kwargs: Any
    ) -> shop.credit.BranchTrace:
        calls[action_id] = calls.get(action_id, 0) + 1
        delta = 0.1 if action_id.endswith(":0") and calls[action_id] > 1 else 0.0
        return _trace(action_id, delta=delta)

    result = _collect(evaluator)

    assert len(result.rows) == 1
    assert result.rows[0].replay["passed"] is False
    assert result.checks["replay_identity"] is False
    assert result.verdict == "shop_counterfactual_signal_not_viable"


def test_unknown_branch_failure_is_not_reinterpreted_as_censor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)

    def evaluator(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("unexpected shop failure")

    with pytest.raises(shop.ShopOutcomeBlocked, match="branch evaluation"):
        _collect(evaluator)


def test_artifacts_bind_rows_report_and_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_protocol(monkeypatch)
    result = _collect(
        lambda _environment, *, action_id, **_kwargs: _trace(action_id)
    )
    output = tmp_path / "shop-output"

    shop._write_artifacts(
        output,
        result,
        configuration={"schema_version": shop.SCHEMA_VERSION},
        identity={"source": {"source_sha256": "a" * 64}},
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert {row["path"] for row in manifest["artifacts"]} == {
        "censored_sources.json",
        "configuration.json",
        "report.json",
        "source_rows.json",
    }
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    report = json.loads((output / "report.json").read_text("ascii"))
    source_rows = json.loads((output / "source_rows.json").read_text("ascii"))
    assert report["verdict"] == "shop_counterfactual_signal_viable_for_learning_proposal"
    assert report["summary"]["action_kinds"] == sorted(KINDS)
    assert report["operations"]["training"] is False
    assert "state_features" not in source_rows[0]
    assert "candidate_features" not in source_rows[0]
    assert (output / "report.md").is_file()
