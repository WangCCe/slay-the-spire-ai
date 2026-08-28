from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from spirecomm.ai.rl.v2.agent import RLAgentV2
from spirecomm.ai.rl.v2.latent_gated_adapter import (
    LatentGateConfig,
    LatentGatedActionAdapter,
    build_development_artifact,
    state_dict_sha256,
)
from spirecomm.ai.rl.v2.latent_gated_live_candidate import (
    REGISTRATION_ENV,
    initialize_latent_gated_live_candidate,
)
from spirecomm.ai.rl.v2.latent_gated_live_shadow import (
    REGISTRATION_ENV as SHADOW_REGISTRATION_ENV,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2
from spirecomm.communication.action import WaitAction


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 3,
    "card_vocab": 6,
    "potion_vocab": 6,
    "relic_vocab": 6,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_registration(
    tmp_path: Path,
    *,
    gate_open: bool = True,
    maximum_decisions: int = 3,
):
    torch.manual_seed(73)
    parent = create_dqn_v2(device="cpu", **METADATA)
    parent.eval()
    adapter = LatentGatedActionAdapter(
        parent,
        METADATA,
        LatentGateConfig(hidden_dim=8, gate_threshold=0.5),
    )
    continuous = np.array([0.5, -0.25, 0.75, 0.0], dtype=np.float32)
    card_ids = np.array([1], dtype=np.int64)
    potion_ids = np.array([2], dtype=np.int64)
    relic_ids = np.array([3], dtype=np.int64)
    action_mask = np.array([True, True, True], dtype=bool)
    tensors = (
        torch.from_numpy(continuous).unsqueeze(0),
        torch.from_numpy(card_ids).unsqueeze(0),
        torch.from_numpy(potion_ids).unsqueeze(0),
        torch.from_numpy(relic_ids).unsqueeze(0),
        torch.from_numpy(action_mask).unsqueeze(0),
    )
    with torch.no_grad():
        parent_action = int(parent.get_best_action(*tensors).item())
        correction_action = (parent_action + 1) % METADATA["action_dim"]
        adapter.gate[-1].bias.fill_(10.0 if gate_open else -10.0)
        adapter.correction[-1].weight.zero_()
        adapter.correction[-1].bias.fill_(-10.0)
        adapter.correction[-1].bias[correction_action] = 10.0

    reports = tmp_path / "reports" / "candidate"
    reports.mkdir(parents=True)
    artifact_path = tmp_path / "candidate.pth"
    parent_checkpoint = tmp_path / "production-parent.pth"
    parent_checkpoint.write_bytes(b"production parent fixture")
    torch.save(
        build_development_artifact(
            adapter,
            parent_checkpoint_sha256="a" * 64,
            telemetry={"fixture": True},
        ),
        artifact_path,
    )
    registration = {
        "schema_version": 1,
        "experiment_id": "latent-candidate-fixture",
        "mode": "candidate",
        "source_commit": "c" * 40,
        "candidate_artifact": {
            "path": str(artifact_path),
            "sha256": _sha256(artifact_path),
            "parent_checkpoint_sha256": "a" * 64,
        },
        "production_parent_checkpoint": {
            "path": str(parent_checkpoint),
            "sha256": _sha256(parent_checkpoint),
        },
        "parent_state_dict_sha256": state_dict_sha256(parent.state_dict()),
        "trace_path": str(reports / "trace.jsonl"),
        "maximum_decision_count": maximum_decisions,
        "readiness_gates": {
            "minimum_decision_count": 1,
            "maximum_p95_latency_ms": 500.0,
        },
    }
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        json.dumps(registration, indent=2, sort_keys=True), encoding="utf-8"
    )
    return SimpleNamespace(
        parent=parent,
        artifact_path=artifact_path,
        parent_checkpoint=parent_checkpoint,
        registration_path=registration_path,
        registration=registration,
        trace_path=Path(registration["trace_path"]),
        continuous=continuous,
        card_ids=card_ids,
        potion_ids=potion_ids,
        relic_ids=relic_ids,
        action_mask=action_mask,
        parent_action=parent_action,
        correction_action=correction_action,
    )


def _initialize(paths, **overrides):
    arguments = {
        "parent": paths.parent,
        "metadata": METADATA,
        "model_path": str(paths.parent_checkpoint),
        "training": False,
        "epsilon": 0.0,
        "expert_mix_enabled": False,
        "registration_path": str(paths.registration_path),
        "repo_root": str(paths.registration_path.parent),
        "device": "cpu",
        "require_committed_registration": False,
    }
    arguments.update(overrides)
    return initialize_latent_gated_live_candidate(**arguments)


def _game():
    return SimpleNamespace(
        floor=7,
        turn=3,
        act=1,
        room_type="MonsterRoom",
        screen_type="NONE",
        in_combat=True,
        player=SimpleNamespace(energy=2, current_hp=51, max_hp=80, block=0),
        monsters=[SimpleNamespace(name="Jaw Worm")],
    )


def _select(runtime, paths, game, parent_action=None):
    return runtime.select_action(
        game=game,
        continuous=paths.continuous,
        card_ids=paths.card_ids,
        potion_ids=paths.potion_ids,
        relic_ids=paths.relic_ids,
        action_mask=paths.action_mask,
        parent_action_index=(
            paths.parent_action if parent_action is None else parent_action
        ),
    )


def _events(paths):
    return [
        json.loads(line)
        for line in paths.trace_path.read_text(encoding="utf-8").splitlines()
    ]


def test_candidate_is_default_off(monkeypatch, tmp_path):
    monkeypatch.delenv(REGISTRATION_ENV, raising=False)
    parent = create_dqn_v2(device="cpu", **METADATA)

    assert initialize_latent_gated_live_candidate(
        parent=parent,
        metadata=METADATA,
        model_path=None,
        training=False,
        epsilon=0.0,
        expert_mix_enabled=False,
        repo_root=str(tmp_path),
        device="cpu",
    ) is None


def test_candidate_rejects_shadow_mode_registration(tmp_path):
    paths = _write_registration(tmp_path)
    paths.registration["mode"] = "shadow"
    paths.registration_path.write_text(json.dumps(paths.registration), encoding="utf-8")

    with pytest.raises(ValueError, match="mode"):
        _initialize(paths)


@pytest.mark.parametrize(
    "overrides",
    [
        {"training": True},
        {"epsilon": 0.01},
        {"expert_mix_enabled": True},
        {"model_path": None},
    ],
)
def test_candidate_rejects_training_exploration_or_missing_parent(
    tmp_path, overrides
):
    paths = _write_registration(tmp_path)

    with pytest.raises(ValueError):
        _initialize(paths, **overrides)


def test_gate_open_selects_candidate_and_records_final_guard_action(tmp_path):
    paths = _write_registration(tmp_path, gate_open=True)
    runtime = _initialize(paths)
    game = _game()

    assert _select(runtime, paths, game) == paths.correction_action
    assert runtime.commit_executed_action(
        game=game, executed_action_index=paths.parent_action
    )

    event = _events(paths)[0]
    assert event["parent_action_index"] == paths.parent_action
    assert event["candidate_action_index"] == paths.correction_action
    assert event["selected_action_index"] == paths.correction_action
    assert event["candidate_takeover_applied"] is True
    assert event["executed_action_index"] == paths.parent_action
    assert event["selected_matches_executed"] is False
    assert event["executed_action_legal"] is True


def test_gate_closed_retains_parent_and_records_no_takeover(tmp_path):
    paths = _write_registration(tmp_path, gate_open=False)
    runtime = _initialize(paths)
    game = _game()

    assert _select(runtime, paths, game) == paths.parent_action
    assert runtime.commit_executed_action(
        game=game, executed_action_index=paths.parent_action
    )
    event = _events(paths)[0]
    assert event["gate_open"] is False
    assert event["selected_action_index"] == paths.parent_action
    assert event["candidate_takeover_applied"] is False
    assert event["selected_matches_executed"] is True


def test_parent_parity_failure_falls_back_then_disables_candidate(tmp_path):
    paths = _write_registration(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    different_parent = (paths.parent_action + 2) % METADATA["action_dim"]

    assert _select(runtime, paths, game, parent_action=different_parent) == different_parent
    assert runtime.commit_executed_action(
        game=game, executed_action_index=different_parent
    )
    assert _events(paths)[0]["parent_parity"] is False
    assert _events(paths)[0]["candidate_takeover_applied"] is False
    assert runtime.enabled is False


def test_illegal_candidate_falls_back_then_disables_candidate(tmp_path, monkeypatch):
    paths = _write_registration(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    selected = SimpleNamespace(
        parent_actions=torch.tensor([paths.parent_action]),
        correction_actions=torch.tensor([99]),
        actions=torch.tensor([99]),
        gate_probabilities=torch.tensor([1.0]),
        gate_open=torch.tensor([True]),
    )
    monkeypatch.setattr(runtime.adapter, "select_actions", lambda *_args: selected)

    assert _select(runtime, paths, game) == paths.parent_action
    assert runtime.commit_executed_action(
        game=game, executed_action_index=paths.parent_action
    )
    assert _events(paths)[0]["candidate_action_legal"] is False
    assert runtime.enabled is False


def test_candidate_transient_wait_does_not_consume_budget(tmp_path):
    paths = _write_registration(tmp_path, maximum_decisions=1)
    runtime = _initialize(paths)

    assert _select(runtime, paths, _game()) == paths.correction_action
    assert runtime.discard_transient_action(reason="wait_action")
    assert runtime.decision_count == 0
    assert _events(paths)[0]["event_type"] == "transient_discard"
    assert _select(runtime, paths, _game()) == paths.correction_action


class _Network:
    def get_best_action(self, **_kwargs):
        return torch.tensor([1])


class _Candidate:
    enabled = True
    pending = None

    def __init__(self, selected=2):
        self.selected = selected
        self.calls = []

    def select_action(self, **kwargs):
        self.calls.append(kwargs)
        return self.selected

    def record_runtime_error(self, **_kwargs):
        self.enabled = False

    def discard_pending(self):
        self.pending = None


def _minimal_agent(candidate):
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.state_encoder = SimpleNamespace(
        encode=lambda _game: SimpleNamespace(
            continuous=np.zeros(4, dtype=np.float32),
            card_ids=np.zeros(1, dtype=np.int64),
            potion_ids=np.zeros(1, dtype=np.int64),
            relic_ids=np.zeros(1, dtype=np.int64),
        )
    )
    agent.action_encoder = SimpleNamespace(
        get_action_mask=lambda _game: np.array([True, True, True]),
        decode_action=lambda index, _game: ("decoded", index),
    )
    agent.training_mode = False
    agent.trainer = None
    agent.epsilon = 0.0
    agent.device = "cpu"
    agent.network = _Network()
    agent.latent_gated_shadow = None
    agent.latent_gated_candidate = candidate
    agent.last_game = None
    return agent


def test_rl_agent_uses_candidate_selected_action():
    candidate = _Candidate(selected=2)
    agent = _minimal_agent(candidate)

    assert agent.get_next_action_in_game(_game()) == ("decoded", 2)
    assert candidate.calls[0]["parent_action_index"] == 1


def test_rl_agent_falls_back_to_parent_when_candidate_raises():
    class RaisingCandidate(_Candidate):
        def select_action(self, **_kwargs):
            raise RuntimeError("candidate failure")

    candidate = RaisingCandidate()
    agent = _minimal_agent(candidate)

    assert agent.get_next_action_in_game(_game()) == ("decoded", 1)
    assert candidate.enabled is False


def test_agent_rejects_simultaneous_shadow_and_candidate(monkeypatch):
    monkeypatch.setenv(SHADOW_REGISTRATION_ENV, "shadow.json")
    monkeypatch.setenv(REGISTRATION_ENV, "candidate.json")

    with pytest.raises(ValueError, match="mutually exclusive"):
        RLAgentV2(
            training=False,
            device="cpu",
            id_mapper=SimpleNamespace(
                card_vocab_size=1,
                potion_vocab_size=1,
                relic_vocab_size=1,
                card_ids={},
                potion_ids={},
                relic_ids={},
                card_tags={},
            ),
        )


def test_agent_discards_candidate_transient_wait():
    class RecordingCandidate:
        pending = object()

        def __init__(self):
            self.reasons = []
            self.commits = []

        def discard_transient_action(self, *, reason):
            self.reasons.append(reason)

        def commit_executed_action(self, **kwargs):
            self.commits.append(kwargs)

    candidate = RecordingCandidate()
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.latent_gated_shadow = None
    agent.latent_gated_candidate = candidate
    agent.training_mode = False
    agent.trainer = None
    agent.action_encoder = SimpleNamespace(
        encode_action=lambda *_args: pytest.fail("transient wait was encoded")
    )

    assert agent.commit_executed_action(_game(), WaitAction(timeout=1)) is False
    assert candidate.reasons == ["wait_action"]
    assert candidate.commits == []


def test_agent_reset_discards_candidate_pending():
    candidate = _Candidate()
    candidate.pending = object()
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.last_game = object()
    agent.pending_transition = object()
    agent.episode_reward = 4.0
    agent.episode_steps = 3
    agent.reward_calculator = SimpleNamespace(reset=lambda: None)
    agent.latent_gated_shadow = None
    agent.latent_gated_candidate = candidate
    agent.expert_agent = None

    agent.reset()

    assert candidate.pending is None
