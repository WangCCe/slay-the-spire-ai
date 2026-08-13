from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_event_ranker_paired_trajectory_shadow as paired
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    StateConditionedPolicyInput,
)


def _candidate(category: str, index: int) -> dict[str, Any]:
    if category == "event":
        return {
            "action_id": f"event:test:option:{index}",
            "available": True,
            "category": "event",
            "kind": "event_option",
            "label": f"option {index}",
            "raw": {"event_id": "Test Event", "idx1": index},
        }
    return {
        "action_id": "route:map_node:0:1",
        "available": True,
        "category": "route",
        "kind": "map_node",
        "label": "M@0,1",
        "raw": {"room": "MONSTER", "x": 0, "y": 1},
    }


@dataclass
class _Environment:
    stage: int = 0
    event_choice: int = 0

    def snapshot(self) -> dict[str, Any]:
        terminal = self.stage >= 2
        category = None if terminal else ("event" if self.stage == 0 else "route")
        floor = (20 if self.event_choice else 10) if terminal else self.stage
        return {
            "category": category,
            "decision_count": self.stage,
            "state": {"floor": floor, "outcome": "player_loss" if terminal else "undecided"},
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict[str, Any]]:
        if self.stage == 0:
            return [_candidate("event", 0), _candidate("event", 1)]
        if self.stage == 1:
            return [_candidate("route", 0)]
        return []


class _Session:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def evaluate(self, *, snapshot: dict[str, Any], candidates: list[dict[str, Any]], **_kwargs: Any) -> dict[str, str]:
        self.calls.append(str(snapshot["category"]))
        return {"action_id": candidates[0]["action_id"]}


class _FixedModel(torch.nn.Module):
    def forward(self, _state: torch.Tensor, candidates: torch.Tensor) -> torch.Tensor:
        return candidates[:, 0]


def _install_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        paired.credit,
        "_environment_state",
        lambda environment: (environment.snapshot(), environment.legal_actions()),
    )

    def apply(environment: _Environment, action_id: str) -> tuple[_Environment, dict[str, Any]]:
        next_environment = _Environment(environment.stage + 1, environment.event_choice)
        reward = 0.0
        if environment.stage == 0:
            next_environment.event_choice = int(action_id.rsplit(":", 1)[-1])
        else:
            reward = (20 if environment.event_choice else 10) / 57.0
        return next_environment, {"reward": reward, "selected_action_id": action_id}

    monkeypatch.setattr(paired.credit, "_apply_forced_action", apply)
    monkeypatch.setattr(
        paired.credit,
        "_transition_reward",
        lambda transition: (transition["reward"], transition["reward"], 0),
    )
    monkeypatch.setattr(
        paired.credit,
        "_terminal_summary",
        lambda snapshot: {
            "floor": snapshot["state"]["floor"],
            "outcome": snapshot["state"]["outcome"],
        },
    )
    monkeypatch.setattr(
        paired,
        "project_state_conditioned_policy_input",
        lambda _snapshot, _candidates: StateConditionedPolicyInput(
            state_features=torch.zeros(2),
            candidate_features=torch.tensor([[0.0, 0.0], [1.0, 0.0]]),
        ),
    )


def test_selected_trajectory_overlays_only_multi_option_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)
    sessions: list[_Session] = []

    def session_factory(_seed: int) -> _Session:
        session = _Session()
        sessions.append(session)
        return session

    current = paired.run_trajectory(
        lambda _seed: _Environment(),
        session_factory,
        seed=1,
        model=None,
        confidence_threshold=None,
    )
    selected = paired.run_trajectory(
        lambda _seed: _Environment(),
        session_factory,
        seed=1,
        model=_FixedModel(),
        confidence_threshold=0.5,
    )

    assert current["action_sequence"] == [
        "event:test:option:0",
        "route:map_node:0:1",
    ]
    assert selected["action_sequence"] == [
        "event:test:option:1",
        "route:map_node:0:1",
    ]
    assert selected["override_count"] == 1
    assert selected["floor"] == 20
    assert [session.calls for session in sessions] == [
        ["event", "route"],
        ["event", "route"],
    ]


def test_support_signature_is_order_independent_and_semantic() -> None:
    candidates = [_candidate("event", 0), _candidate("event", 1)]
    signature = paired.event_candidate_support_signature(candidates)
    assert paired.event_candidate_support_signature(list(reversed(candidates))) == signature

    changed = json.loads(json.dumps(candidates))
    changed[0]["raw"]["follow_up_control"] = "different"
    assert paired.event_candidate_support_signature(changed) != signature


def test_unsupported_event_falls_back_without_model_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_protocol(monkeypatch)
    monkeypatch.setattr(
        paired,
        "project_state_conditioned_policy_input",
        lambda *_args, **_kwargs: pytest.fail("unsupported event invoked model projection"),
    )

    selected = paired.run_trajectory(
        lambda _seed: _Environment(),
        lambda _seed: _Session(),
        seed=1,
        model=_FixedModel(),
        confidence_threshold=0.5,
        support_signatures={"absent": 1},
    )

    assert selected["action_sequence"][0] == "event:test:option:0"
    assert selected["override_count"] == 0
    assert selected["support_fallback_count"] == 1
    assert selected["support_source_count"] == 0
    assert selected["event_decisions"][0]["support_status"] == "fallback"
    assert selected["event_decisions"][0]["fallback_reason"] == (
        "candidate_semantics_absent_from_training"
    )


def test_supported_event_invokes_frozen_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_protocol(monkeypatch)
    support = {
        paired.event_candidate_support_signature(
            [_candidate("event", 0), _candidate("event", 1)]
        ): 3
    }

    selected = paired.run_trajectory(
        lambda _seed: _Environment(),
        lambda _seed: _Session(),
        seed=1,
        model=_FixedModel(),
        confidence_threshold=0.5,
        support_signatures=support,
    )

    assert selected["action_sequence"][0] == "event:test:option:1"
    assert selected["override_count"] == 1
    assert selected["support_fallback_count"] == 0
    assert selected["support_source_count"] == 1
    assert selected["event_decisions"][0]["support_status"] == "supported"
    assert selected["event_decisions"][0]["training_support_count"] == 3


def _arm(*, floor: int, victory: int, events: int = 1, overrides: int = 0) -> dict[str, Any]:
    return {
        "event_source_count": events,
        "floor": floor,
        "override_count": overrides,
        "total_return": 2.0 * victory + floor / 57.0,
        "victory": victory,
    }


def _pair(seed: int, current: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    return {
        "current": current,
        "delta_floor": selected["floor"] - current["floor"],
        "delta_return": selected["total_return"] - current["total_return"],
        "delta_victory": selected["victory"] - current["victory"],
        "seed": seed,
        "selected": selected,
    }


def test_paired_gate_accepts_value_gain_and_rejects_lost_victory() -> None:
    good_pair = _pair(1, _arm(floor=10, victory=0), _arm(floor=20, victory=0, overrides=1))
    good, good_verdict = paired.evaluate_pairs(
        [good_pair], [], minimum_complete_pairs=1, minimum_event_exposed_pairs=1, minimum_override_pairs=1
    )
    lost_win = _pair(2, _arm(floor=51, victory=1), _arm(floor=51, victory=0, overrides=1))
    bad, bad_verdict = paired.evaluate_pairs(
        [lost_win], [], minimum_complete_pairs=1, minimum_event_exposed_pairs=1, minimum_override_pairs=1
    )

    assert good_verdict == "event_ranker_paired_trajectory_integration_ready"
    assert all(good["checks"].values())
    assert bad_verdict == "event_ranker_paired_trajectory_integration_not_ready"
    assert bad["checks"]["no_paired_victory_loss"] is False
    assert bad["victory_losses"] == 1


def test_supported_gate_requires_complete_fallback_accounting() -> None:
    current = _arm(floor=10, victory=0)
    selected = _arm(floor=20, victory=0, overrides=1)
    selected.update(
        {
            "event_decisions": [
                {
                    "current_action_id": "event:test:option:0",
                    "overridden": True,
                    "selected_action_id": "event:test:option:1",
                    "support_status": "supported",
                }
            ],
            "support_fallback_count": 0,
            "support_source_count": 1,
        }
    )
    metrics, verdict = paired.evaluate_supported_pairs(
        [_pair(1, current, selected)],
        [],
        minimum_complete_pairs=1,
        minimum_event_exposed_pairs=1,
        minimum_support_exposed_pairs=1,
        minimum_override_pairs=1,
    )

    assert verdict == "supported_event_ranker_paired_trajectory_integration_ready"
    assert all(metrics["checks"].values())
    assert metrics["support"]["supported_sources"] == 1

    selected["event_decisions"][0].update(
        {
            "fallback_reason": "candidate_semantics_absent_from_training",
            "support_status": "fallback",
        }
    )
    selected["support_fallback_count"] = 1
    selected["support_source_count"] = 0
    bad, bad_verdict = paired.evaluate_supported_pairs(
        [_pair(2, current, selected)],
        [],
        minimum_complete_pairs=1,
        minimum_event_exposed_pairs=1,
        minimum_support_exposed_pairs=0,
        minimum_override_pairs=1,
    )
    assert bad_verdict == "supported_event_ranker_paired_trajectory_integration_not_ready"
    assert bad["checks"]["no_out_of_support_overrides"] is False
    assert bad["checks"]["fallback_accounting_complete"] is False


def test_registered_pair_blocker_is_narrow() -> None:
    assert paired._registered_blocker(
        paired.credit.CounterfactualCreditBlocked(paired.route.CURRENT_SHOP_MAPPING_BLOCKER)
    ) == paired.route.CURRENT_SHOP_MAPPING_BLOCKER
    assert paired._registered_blocker(RuntimeError("candidate_mapping_absent")) is None


def test_paired_artifacts_are_manifest_bound(tmp_path: Path) -> None:
    pair = _pair(1, _arm(floor=10, victory=0), _arm(floor=20, victory=0, overrides=1))
    metrics, _ = paired.evaluate_pairs(
        [pair], [], minimum_complete_pairs=1, minimum_event_exposed_pairs=1, minimum_override_pairs=1
    )
    output = tmp_path / "paired"

    paired._write_artifacts(
        output,
        configuration={"schema_version": paired.SCHEMA_VERSION},
        pairs=[pair],
        censored=[],
        metrics=metrics,
        report={"charged_seconds": 1.0, "verdict": metrics["verdict"]},
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 5
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]


def test_bound_training_support_restores_manifest_dataset(tmp_path: Path) -> None:
    support, identity = paired.load_bound_training_support(paired.DEFAULT_TRAINING_DIR)

    assert len(support) == 31
    assert len(identity["event_ids"]) == 25
    assert identity["signature_count"] == len(support)

    source = paired.DEFAULT_TRAINING_DIR / "train_dataset.json"
    payload = source.read_bytes() + b"\n"
    broken = tmp_path / "broken-training"
    broken.mkdir()
    (broken / "train_dataset.json").write_bytes(payload)
    (broken / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "path": "train_dataset.json",
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "size_bytes": source.stat().st_size,
                    }
                ]
            }
        ),
        encoding="ascii",
    )

    with pytest.raises(paired.PairedTrajectoryBlocked, match="manifest"):
        paired.load_bound_training_support(broken)
