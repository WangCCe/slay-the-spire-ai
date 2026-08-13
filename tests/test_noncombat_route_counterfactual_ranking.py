from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_route_counterfactual_ranking as ranking
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    StateConditionedPolicyInput,
)


def _route_candidate(stage: int, label: str) -> dict[str, Any]:
    return {
        "action_id": f"route:{stage}:{label}",
        "available": True,
        "category": "route",
        "kind": "map_node",
        "label": f"{label}@{stage}",
        "raw": {
            "room": label.upper(),
            "x": ord(label[0]) - ord("a"),
            "y": stage,
        },
    }


@dataclass
class _FakeRouteEnvironment:
    seed: int
    stage: int = 0

    def clone(self) -> _FakeRouteEnvironment:
        return type(self)(seed=self.seed, stage=self.stage)

    def snapshot(self) -> dict[str, Any]:
        terminal = self.stage >= 3
        category = None if terminal else ("event" if self.stage == 1 else "route")
        return {
            "category": category,
            "decision_count": self.stage,
            "state": {
                "floor": self.stage,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict[str, Any]]:
        if self.stage == 0:
            return [_route_candidate(0, "a"), _route_candidate(0, "b")]
        if self.stage == 1:
            return [
                {
                    "action_id": "event:continue",
                    "available": True,
                    "category": "event",
                    "kind": "choose",
                    "label": "Continue",
                    "raw": {"choice_index": 0},
                }
            ]
        if self.stage == 2:
            return [
                _route_candidate(2, "a"),
                _route_candidate(2, "b"),
                _route_candidate(2, "c"),
            ]
        return []


class _CurrentBaseline:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def evaluate(
        self,
        *,
        snapshot: dict[str, Any],
        candidates: list[dict[str, Any]],
        decision_index: int,
    ) -> dict[str, str]:
        self.calls.append(
            {
                "candidates": copy.deepcopy(candidates),
                "decision_index": decision_index,
                "snapshot": copy.deepcopy(snapshot),
            }
        )
        return {"action_id": candidates[-1]["action_id"]}


def _install_fake_route_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    def environment_state(
        environment: _FakeRouteEnvironment,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        return copy.deepcopy(environment.snapshot()), copy.deepcopy(
            environment.legal_actions()
        )

    def advance_native(
        environment: _FakeRouteEnvironment,
    ) -> tuple[_FakeRouteEnvironment, dict[str, Any]]:
        advanced = environment.clone()
        selected = advanced.legal_actions()[0]["action_id"]
        advanced.stage += 1
        return advanced, {"selected_action_id": selected}

    monkeypatch.setattr(ranking.credit, "_environment_state", environment_state)
    monkeypatch.setattr(ranking.credit, "_advance_native", advance_native)


def _project(
    snapshot: dict[str, Any], candidates: list[dict[str, Any]]
) -> StateConditionedPolicyInput:
    state = torch.zeros(4, dtype=torch.float32)
    state[0] = float(snapshot["decision_count"] + 1)
    candidate_features = torch.zeros((len(candidates), 4), dtype=torch.float32)
    for index in range(len(candidates)):
        candidate_features[index, 1] = float(index + 1)
    return StateConditionedPolicyInput(
        state_features=state,
        candidate_features=candidate_features,
    )


def _branch_trace(action_id: str) -> ranking.credit.BranchTrace:
    total_return = {
        "route:0:a": 0.25,
        "route:0:b": 0.75,
        "route:2:a": 0.50,
        "route:2:b": 0.20,
        "route:2:c": 1.00,
    }[action_id]
    return ranking.credit.BranchTrace(
        action_id=action_id,
        action_sequence=(action_id, "native:terminal"),
        floor_progress=total_return,
        initial_transition_sha256="1" * 64,
        terminal_state_sha256="2" * 64,
        terminal_summary={"floor": 10, "outcome": "player_loss"},
        terminal_victory=0,
        total_return=total_return,
        transition_count=2,
    )


def _collect(
    evaluator: Any,
    *,
    environment_factory: Any = _FakeRouteEnvironment,
    baseline_session_factory: Any = lambda _seed: _CurrentBaseline(),
) -> ranking.RoutePartition:
    return ranking.collect_route_partition(
        environment_factory,
        baseline_session_factory,
        name="train",
        seeds=(17,),
        max_source_states=4,
        max_action_branches=8,
        max_censored_sources=1,
        max_route_states_per_seed=3,
        max_decisions=8,
        projector=_project,
        branch_evaluator=evaluator,
    )


def test_collect_route_partition_collects_complete_rows_and_preserves_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_route_protocol(monkeypatch)
    environments: list[_FakeRouteEnvironment] = []
    sessions: list[_CurrentBaseline] = []
    branch_sources: list[tuple[_FakeRouteEnvironment, dict[str, Any]]] = []

    def environment_factory(seed: int) -> _FakeRouteEnvironment:
        environment = _FakeRouteEnvironment(seed)
        environments.append(environment)
        return environment

    def baseline_factory(_seed: int) -> _CurrentBaseline:
        session = _CurrentBaseline()
        sessions.append(session)
        return session

    def evaluator(
        environment: _FakeRouteEnvironment,
        *,
        action_id: str,
        source_category: str,
        **_kwargs: Any,
    ) -> ranking.credit.BranchTrace:
        assert source_category == "route"
        before = copy.deepcopy(environment.snapshot())
        trace = _branch_trace(action_id)
        assert environment.snapshot() == before
        branch_sources.append((environment, before))
        return trace

    partition = _collect(
        evaluator,
        environment_factory=environment_factory,
        baseline_session_factory=baseline_factory,
    )

    assert [row.decision_index for row in partition.rows] == [0, 2]
    assert [len(row.candidates) for row in partition.rows] == [2, 3]
    assert [row.current_action_id for row in partition.rows] == [
        "route:0:b",
        "route:2:c",
    ]
    assert [outcome["action_id"] for row in partition.rows for outcome in row.branch_outcomes] == [
        "route:0:a",
        "route:0:b",
        "route:2:a",
        "route:2:b",
        "route:2:c",
    ]
    assert partition.action_branches == 5
    assert partition.root_native_transitions == 3
    assert partition.censored_sources == ()
    assert partition.budget_exhausted is False
    assert [[call["decision_index"] for call in session.calls] for session in sessions] == [
        [0],
        [2],
    ]
    assert environments[0].stage == 0
    assert environments[0].snapshot()["decision_count"] == 0
    assert all(environment.snapshot() == before for environment, before in branch_sources)


def _route_row(seed: int, *, good_first: bool = True) -> ranking.RouteRow:
    state_features = torch.tensor(
        [1.0, float(seed % 3), 0.0, 0.0], dtype=torch.float32
    )
    good = torch.tensor([4.0, 0.0, 0.0, 0.0], dtype=torch.float32)
    bad = torch.tensor([-4.0, 0.0, 0.0, 0.0], dtype=torch.float32)
    labels = ("good", "bad") if good_first else ("bad", "good")
    candidates = tuple(_route_candidate(seed, label) for label in labels)
    candidate_features = torch.stack((good, bad) if good_first else (bad, good))
    returns = (1.0, 0.0) if good_first else (0.0, 1.0)
    outcomes = tuple(
        {
            "action_id": candidate["action_id"],
            "terminal_outcome": "player_loss",
            "terminal_victory": 0,
            "total_return": total_return,
        }
        for candidate, total_return in zip(candidates, returns, strict=True)
    )
    return ranking.RouteRow(
        seed=seed,
        decision_index=seed % 5,
        source_sha256=f"{seed:064x}",
        state_features=state_features,
        candidate_features=candidate_features,
        candidates=candidates,
        branch_outcomes=outcomes,
        current_action_id=next(
            candidate["action_id"]
            for candidate in candidates
            if candidate["label"].startswith("bad@")
        ),
    )


def test_partition_encoding_restores_a_byte_exact_canonical_roundtrip() -> None:
    row = _route_row(31, good_first=False)
    partition = ranking.RoutePartition(
        name="train",
        seeds=(31,),
        rows=(row,),
        action_branches=2,
        root_native_transitions=4,
        censored_sources=(
            {
                "decision_index": 3,
                "reason": "registered-test-censor",
                "seed": 31,
                "source_sha256": None,
            },
        ),
        budget_exhausted=False,
    )

    encoded = ranking.encode_partition(partition)
    decoded = json.loads(encoded.decode("ascii"))
    restored = ranking.restore_partition(encoded)

    assert encoded == (json.dumps(decoded, indent=2, sort_keys=True) + "\n").encode(
        "ascii"
    )
    assert ranking.encode_partition(restored) == encoded
    assert restored.name == partition.name
    assert restored.seeds == partition.seeds
    assert restored.censored_sources == partition.censored_sources
    assert torch.equal(restored.rows[0].state_features, row.state_features)
    assert torch.equal(restored.rows[0].candidate_features, row.candidate_features)
    assert restored.rows[0].candidates == row.candidates
    assert restored.rows[0].branch_outcomes == row.branch_outcomes


def test_route_category_mismatch_from_branch_evaluator_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_route_protocol(monkeypatch)

    def mismatched_category(*_args: Any, **_kwargs: Any) -> Any:
        raise ranking.credit.CounterfactualCreditBlocked(
            "source must be a live route state"
        )

    with pytest.raises(ranking.RouteExperimentBlocked):
        _collect(mismatched_category)


def test_unknown_branch_evaluator_error_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_route_protocol(monkeypatch)

    def unknown_error(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("unexpected branch evaluator failure")

    with pytest.raises(ranking.RouteExperimentBlocked):
        _collect(unknown_error)


def test_current_continuation_redecides_after_off_path_route_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_route_protocol(monkeypatch)
    source = _FakeRouteEnvironment(23)
    session = _CurrentBaseline()

    def apply_forced_action(
        environment: _FakeRouteEnvironment, action_id: str
    ) -> tuple[_FakeRouteEnvironment, dict[str, Any]]:
        legal = {candidate["action_id"] for candidate in environment.legal_actions()}
        assert action_id in legal
        advanced = environment.clone()
        advanced.stage += 1
        return advanced, {
            "reward": 1.0 / 57.0,
            "selected_action_id": action_id,
        }

    monkeypatch.setattr(ranking.credit, "_apply_forced_action", apply_forced_action)
    monkeypatch.setattr(
        ranking.credit,
        "_transition_reward",
        lambda transition: (transition["reward"], transition["reward"], 0),
    )
    monkeypatch.setattr(
        ranking.credit,
        "_assert_source_unchanged",
        lambda environment, snapshot, candidates: (
            environment.stage == 0
            and snapshot["decision_count"] == 0
            and len(candidates) == 2
        )
        or (_ for _ in ()).throw(AssertionError("source mutated")),
    )
    monkeypatch.setattr(
        ranking.credit,
        "_terminal_summary",
        lambda snapshot: {"floor": snapshot["state"]["floor"], "outcome": "player_loss"},
    )
    monkeypatch.setattr(ranking.credit, "_sha256_json", lambda _value: "a" * 64)
    monkeypatch.setattr(
        ranking.credit,
        "_advance_native",
        lambda _environment: (_ for _ in ()).throw(
            AssertionError("off-path branch must not use native continuation")
        ),
    )

    trace = ranking.evaluate_route_action_with_current_continuation(
        source,
        action_id="route:0:a",
        continuation_session_factory=lambda: session,
        max_decisions=8,
    )

    assert trace.action_sequence == (
        "route:0:a",
        "event:continue",
        "route:2:c",
    )
    assert trace.total_return == pytest.approx(3.0 / 57.0)
    assert [call["decision_index"] for call in session.calls] == [1, 2]
    assert source.stage == 0


def test_current_continuation_accepts_event_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_route_protocol(monkeypatch)
    source = _FakeRouteEnvironment(29, stage=1)
    session = _CurrentBaseline()

    def apply_forced_action(
        environment: _FakeRouteEnvironment, action_id: str
    ) -> tuple[_FakeRouteEnvironment, dict[str, Any]]:
        assert action_id in {
            candidate["action_id"] for candidate in environment.legal_actions()
        }
        advanced = environment.clone()
        advanced.stage += 1
        return advanced, {
            "reward": 1.0 / 57.0,
            "selected_action_id": action_id,
        }

    monkeypatch.setattr(ranking.credit, "_apply_forced_action", apply_forced_action)
    monkeypatch.setattr(
        ranking.credit,
        "_transition_reward",
        lambda transition: (transition["reward"], transition["reward"], 0),
    )
    monkeypatch.setattr(
        ranking.credit,
        "_assert_source_unchanged",
        lambda environment, snapshot, candidates: None,
    )
    monkeypatch.setattr(
        ranking.credit,
        "_terminal_summary",
        lambda snapshot: {"floor": snapshot["state"]["floor"], "outcome": "player_loss"},
    )
    monkeypatch.setattr(ranking.credit, "_sha256_json", lambda _value: "b" * 64)

    trace = ranking.evaluate_action_with_current_continuation(
        source,
        action_id="event:continue",
        continuation_session_factory=lambda: session,
        source_category="event",
        max_decisions=8,
    )

    assert trace.action_sequence == ("event:continue", "route:2:c")
    assert [call["decision_index"] for call in session.calls] == [2]
    assert source.stage == 1


@pytest.mark.parametrize(
    ("downstream_category", "expected"),
    [
        ("shop", ranking.CURRENT_SHOP_MAPPING_BLOCKER),
        ("route", "Current continuation failed: candidate_mapping_absent"),
    ],
)
def test_current_continuation_registers_only_shop_candidate_mapping_absence(
    monkeypatch: pytest.MonkeyPatch,
    downstream_category: str,
    expected: str,
) -> None:
    source = object()
    advanced = object()
    source_snapshot = {
        "category": "event",
        "decision_count": 0,
        "state": {"floor": 1, "outcome": "undecided"},
        "terminal": False,
    }
    advanced_snapshot = {
        "category": downstream_category,
        "decision_count": 1,
        "state": {"floor": 1, "outcome": "undecided"},
        "terminal": False,
    }
    monkeypatch.setattr(
        ranking.credit,
        "_environment_state",
        lambda environment: (
            (source_snapshot, [{"action_id": "event:continue"}])
            if environment is source
            else (advanced_snapshot, [{"action_id": f"{downstream_category}:leave"}])
        ),
    )
    monkeypatch.setattr(
        ranking.credit,
        "_apply_forced_action",
        lambda environment, action_id: (
            advanced,
            {"reward": 0.0, "selected_action_id": action_id},
        ),
    )
    monkeypatch.setattr(
        ranking.credit,
        "_transition_reward",
        lambda _transition: (0.0, 0.0, 0),
    )

    class BlockedSession:
        def evaluate(self, **_kwargs: Any) -> Any:
            raise ranking.current_bridge.BridgeBlocked("candidate_mapping_absent")

    with pytest.raises(ranking.credit.CounterfactualCreditBlocked, match=expected):
        ranking.evaluate_action_with_current_continuation(
            source,
            action_id="event:continue",
            continuation_session_factory=BlockedSession,
            source_category="event",
            max_decisions=4,
        )

    blocker = ranking.credit.CounterfactualCreditBlocked(expected)
    assert ranking._registered_support_blocker(blocker) == (
        ranking.CURRENT_SHOP_MAPPING_BLOCKER
        if downstream_category == "shop"
        else None
    )


def test_train_and_evaluate_model_are_deterministic_on_learnable_rows() -> None:
    rows = tuple(
        _route_row(seed, good_first=seed % 2 == 0) for seed in range(40, 48)
    )

    first_model, first_history = ranking.train_model(rows, epochs=32)
    second_model, second_history = ranking.train_model(rows, epochs=32)
    first_metrics = ranking.evaluate_model(first_model, rows)
    second_metrics = ranking.evaluate_model(second_model, rows)

    assert first_history == second_history
    assert first_history[-1]["mean_batch_loss"] < first_history[0]["mean_batch_loss"]
    assert first_metrics == second_metrics
    assert first_metrics["weighted_pairwise_accuracy"] == 1.0
    assert first_metrics["mean_regret"] == 0.0
    assert all(
        prediction["action_id"].endswith(":good")
        for prediction in first_metrics["predictions"]
    )
    for name, first_value in first_model.state_dict().items():
        assert torch.equal(first_value, second_model.state_dict()[name])


def test_run_experiment_rejects_train_development_seed_overlap_before_access() -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("overlap gate must run before factories or the clock")

    with pytest.raises(ranking.RouteExperimentBlocked, match="seeds overlap"):
        ranking.run_experiment(
            forbidden,
            forbidden,
            train_seeds=(101, 102),
            development_seeds=(102, 103),
            clock=forbidden,
        )


def test_source_identity_binds_current_policy_bridge() -> None:
    assert ranking.BOUND_SOURCE_PATHS == (
        ranking.Path("analysis_scripts/noncombat_route_counterfactual_ranking.py"),
        ranking.Path("analysis_scripts/noncombat_card_action_counterfactual_credit.py"),
        ranking.Path("analysis_scripts/noncombat_current_policy_simulator_bridge.py"),
        ranking.Path("analysis_scripts/noncombat_state_conditioned_policy_input.py"),
        ranking.Path("analysis_scripts/noncombat_state_conditioned_ranker.py"),
    )
