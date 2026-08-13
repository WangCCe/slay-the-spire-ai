from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from analysis_scripts import noncombat_event_option_counterfactual_outcomes as event


def _candidate(seed: int, index: int) -> dict[str, Any]:
    return {
        "action_id": f"event:test_{seed}:option:{index}",
        "available": True,
        "category": "event",
        "kind": "event_option",
        "label": f"Option {index}",
        "raw": {"choice_index": index, "idx1": index},
    }


@dataclass
class _EventEnvironment:
    seed: int
    stage: int = 0

    def clone(self) -> "_EventEnvironment":
        return type(self)(self.seed, self.stage)

    def snapshot(self) -> dict[str, Any]:
        terminal = self.stage > 0
        return {
            "category": None if terminal else "event",
            "decision_count": self.stage,
            "state": {
                "decision_context": {
                    "event_id": f"test_{self.seed}",
                    "event_name": f"Test Event {self.seed}",
                },
                "floor": self.stage,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict[str, Any]]:
        return [] if self.stage else [_candidate(self.seed, 0), _candidate(self.seed, 1)]


class _EventSession:
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
        return {
            "action_id": candidates[0]["action_id"],
            "event_observation": {"current_event_id": f"test_{self.seed}"},
            "event_semantics_source": "test-event-semantics-v1",
        }


def _trace(action_id: str, *, delta: float = 0.0) -> event.credit.BranchTrace:
    option = int(action_id.rsplit(":", 1)[-1])
    total_return = 0.25 + 0.5 * option + delta
    return event.credit.BranchTrace(
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
        event.credit,
        "_environment_state",
        lambda environment: (
            copy.deepcopy(environment.snapshot()),
            copy.deepcopy(environment.legal_actions()),
        ),
    )

    def advance_native(
        environment: _EventEnvironment,
    ) -> tuple[_EventEnvironment, dict[str, Any]]:
        advanced = environment.clone()
        advanced.stage += 1
        return advanced, {"selected_action_id": _candidate(environment.seed, 0)["action_id"]}

    monkeypatch.setattr(event.credit, "_advance_native", advance_native)


def _collect(
    evaluator: Any,
    *,
    seeds: tuple[int, ...] = (1,),
    replay_source_count: int = 1,
) -> event.EventOutcomeResult:
    ticks = iter(range(10_000))
    return event.collect_event_outcomes(
        _EventEnvironment,
        _EventSession,
        seeds=seeds,
        max_source_states=16,
        max_action_branches=64,
        max_censored_sources=8,
        max_event_states_per_seed=1,
        replay_source_count=replay_source_count,
        minimum_complete_sources=len(seeds),
        minimum_informative_sources=len(seeds),
        minimum_distinct_events=len(seeds),
        max_decisions=8,
        maximum_charged_seconds=10_000,
        clock=lambda: next(ticks),
        branch_evaluator=evaluator,
    )


def test_collects_complete_informative_event_rows_with_exact_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)
    sources: list[_EventEnvironment] = []

    def evaluator(
        environment: _EventEnvironment,
        *,
        action_id: str,
        source_category: str,
        **_kwargs: Any,
    ) -> event.credit.BranchTrace:
        assert source_category == "event"
        sources.append(environment)
        return _trace(action_id)

    result = _collect(evaluator, seeds=(1, 2), replay_source_count=2)

    assert result.verdict == "event_option_counterfactual_signal_viable_for_learning_proposal"
    assert result.checks == {
        "complete_source_floor": True,
        "distinct_event_floor": True,
        "informative_source_floor": True,
        "replay_count": True,
        "replay_identity": True,
    }
    assert len(result.rows) == 2
    assert result.action_branches == 4
    assert result.root_native_transitions == 2
    assert result.censored_sources == ()
    assert {row.event_id for row in result.rows} == {"test_1", "test_2"}
    assert all(row.current_action_id.endswith(":0") for row in result.rows)
    assert all(row.replay and row.replay["passed"] for row in result.rows)
    assert all(environment.stage == 0 for environment in sources)


def test_registered_support_failure_censors_incomplete_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)

    def evaluator(*_args: Any, **_kwargs: Any) -> Any:
        raise event.credit.CounterfactualCreditBlocked(
            "unsupported_shop_courier_restock_semantics"
        )

    result = _collect(evaluator)

    assert result.verdict == "event_option_counterfactual_signal_not_viable"
    assert result.rows == ()
    assert len(result.censored_sources) == 1
    assert result.censored_sources[0]["reason"] == (
        "unsupported_shop_courier_restock_semantics"
    )


def test_replay_drift_fails_viability_without_discarding_complete_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)
    calls: dict[str, int] = {}

    def evaluator(
        _environment: _EventEnvironment, *, action_id: str, **_kwargs: Any
    ) -> event.credit.BranchTrace:
        calls[action_id] = calls.get(action_id, 0) + 1
        delta = 0.1 if action_id.endswith(":0") and calls[action_id] > 1 else 0.0
        return _trace(action_id, delta=delta)

    result = _collect(evaluator)

    assert len(result.rows) == 1
    assert result.rows[0].replay["passed"] is False
    assert result.checks["replay_identity"] is False
    assert result.verdict == "event_option_counterfactual_signal_not_viable"


def test_unknown_branch_failure_is_not_reinterpreted_as_censor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)

    def evaluator(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("unexpected event failure")

    with pytest.raises(event.EventOutcomeBlocked, match="branch evaluation"):
        _collect(evaluator)


def test_artifacts_bind_rows_report_and_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_protocol(monkeypatch)
    result = _collect(
        lambda _environment, *, action_id, **_kwargs: _trace(action_id)
    )
    output = tmp_path / "event-output"

    event._write_artifacts(
        output,
        result,
        configuration={"schema_version": event.SCHEMA_VERSION},
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
    assert report["verdict"] == (
        "event_option_counterfactual_signal_viable_for_learning_proposal"
    )
    assert report["summary"]["complete_source_states"] == 1
    assert (output / "report.md").is_file()
