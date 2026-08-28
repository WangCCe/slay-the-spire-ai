from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
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
from spirecomm.ai.rl.v2.latent_gated_live_shadow import (
    REGISTRATION_ENV,
    _require_source_binding,
    initialize_latent_gated_live_shadow,
    load_live_shadow_registration,
)
import spirecomm.ai.rl.v2.latent_gated_live_shadow as shadow_module
from spirecomm.ai.rl.v2.network import create_dqn_v2


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


def _write_registration(tmp_path: Path, *, maximum_decisions: int = 3):
    torch.manual_seed(72)
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
        adapter.gate[-1].bias.fill_(10.0)
        adapter.correction[-1].weight.zero_()
        adapter.correction[-1].bias.fill_(-10.0)
        adapter.correction[-1].bias[correction_action] = 10.0

    reports = tmp_path / "reports" / "shadow"
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
        "experiment_id": "latent-shadow-fixture",
        "mode": "shadow",
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
    return initialize_latent_gated_live_shadow(**arguments)


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


def _observe(runtime, paths, game, parent_action=None):
    return runtime.observe_proposal(
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


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def test_shadow_is_default_off(monkeypatch, tmp_path):
    monkeypatch.delenv(REGISTRATION_ENV, raising=False)
    parent = create_dqn_v2(device="cpu", **METADATA)

    assert initialize_latent_gated_live_shadow(
        parent=parent,
        metadata=METADATA,
        model_path=None,
        training=False,
        epsilon=0.0,
        expert_mix_enabled=False,
        repo_root=str(tmp_path),
        device="cpu",
    ) is None


def test_registration_must_match_committed_git_content(tmp_path):
    paths = _write_registration(tmp_path)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Codex Test")
    _git(tmp_path, "config", "user.email", "codex@example.invalid")
    _git(tmp_path, "add", "registration.json")
    _git(tmp_path, "commit", "-m", "register shadow fixture")

    loaded = load_live_shadow_registration(
        paths.registration_path, repo_root=tmp_path, require_committed=True
    )
    assert loaded.experiment_id == "latent-shadow-fixture"

    paths.registration_path.write_text(
        paths.registration_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="committed HEAD"):
        load_live_shadow_registration(
            paths.registration_path, repo_root=tmp_path, require_committed=True
        )


def test_source_binding_rejects_worktree_changes(monkeypatch, tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Codex Test")
    _git(tmp_path, "config", "user.email", "codex@example.invalid")
    source = tmp_path / "source.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "source.py")
    _git(tmp_path, "commit", "-m", "add source")
    source_commit = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(shadow_module, "SOURCE_BOUND_PATHS", ("source.py",))

    _require_source_binding(source_commit, tmp_path)
    source.write_text("VALUE = 2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source files differ"):
        _require_source_binding(source_commit, tmp_path)


def test_default_off_agent_does_not_build_shadow_metadata(monkeypatch):
    monkeypatch.delenv(REGISTRATION_ENV, raising=False)

    def unexpected_metadata(_self):
        raise AssertionError("default-off shadow built metadata")

    monkeypatch.setattr(RLAgentV2, "_build_metadata", unexpected_metadata)
    agent = RLAgentV2(
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

    assert agent.latent_gated_shadow is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("artifact", "artifact"),
        ("checkpoint", "checkpoint"),
        ("parent_state", "parent state"),
        ("trace_escape", "reports"),
    ],
)
def test_shadow_rejects_binding_differences(tmp_path, mutation, message):
    paths = _write_registration(tmp_path)
    if mutation == "artifact":
        paths.registration["candidate_artifact"]["sha256"] = "f" * 64
    elif mutation == "checkpoint":
        paths.registration["production_parent_checkpoint"]["sha256"] = "f" * 64
    elif mutation == "parent_state":
        paths.registration["parent_state_dict_sha256"] = "f" * 64
    else:
        paths.registration["trace_path"] = str(tmp_path / "escaped.jsonl")
    paths.registration_path.write_text(
        json.dumps(paths.registration), encoding="utf-8"
    )

    with pytest.raises(ValueError, match=message):
        _initialize(paths)
    assert not paths.trace_path.exists()


@pytest.mark.parametrize(
    "overrides",
    [
        {"training": True},
        {"epsilon": 0.01},
        {"expert_mix_enabled": True},
        {"model_path": None},
    ],
)
def test_shadow_rejects_training_exploration_or_missing_parent(tmp_path, overrides):
    paths = _write_registration(tmp_path)

    with pytest.raises(ValueError):
        _initialize(paths, **overrides)


def test_shadow_records_candidate_and_final_guard_action_without_authority(tmp_path):
    paths = _write_registration(tmp_path)
    runtime = _initialize(paths)
    game = _game()

    _observe(runtime, paths, game)
    assert runtime.commit_executed_action(
        game=game,
        executed_action_index=paths.correction_action,
    )

    event = _events(paths)[0]
    assert event["event_type"] == "decision"
    assert event["parent_action_index"] == paths.parent_action
    assert event["candidate_action_index"] == paths.correction_action
    assert event["executed_action_index"] == paths.correction_action
    assert event["proposal_changed"] is True
    assert event["candidate_matches_executed"] is True
    assert event["candidate_action_legal"] is True
    assert event["parent_parity"] is True
    assert event["gate_open"] is True


def test_parent_parity_failure_is_published_then_disables_shadow(tmp_path):
    paths = _write_registration(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    different_parent = (paths.parent_action + 2) % METADATA["action_dim"]

    _observe(runtime, paths, game, parent_action=different_parent)
    assert runtime.commit_executed_action(
        game=game,
        executed_action_index=different_parent,
    )

    assert _events(paths)[0]["parent_parity"] is False
    assert runtime.enabled is False
    assert _observe(runtime, paths, _game()) is False


def test_event_budget_stops_inference_without_an_error(tmp_path):
    paths = _write_registration(tmp_path, maximum_decisions=1)
    runtime = _initialize(paths)
    first = _game()

    assert _observe(runtime, paths, first)
    assert runtime.commit_executed_action(
        game=first, executed_action_index=paths.parent_action
    )
    assert _observe(runtime, paths, _game()) is False
    assert len(_events(paths)) == 1


def test_restarted_shadow_resumes_the_cohort_event_budget(tmp_path):
    paths = _write_registration(tmp_path, maximum_decisions=2)
    first_runtime = _initialize(paths)
    first = _game()
    assert _observe(first_runtime, paths, first)
    assert first_runtime.commit_executed_action(
        game=first, executed_action_index=paths.parent_action
    )

    second_runtime = _initialize(paths)
    assert second_runtime.decision_count == 1
    second = _game()
    assert _observe(second_runtime, paths, second)
    assert second_runtime.commit_executed_action(
        game=second, executed_action_index=paths.parent_action
    )

    assert _observe(second_runtime, paths, _game()) is False
    assert len(_events(paths)) == 2
    assert [event["decision_sequence"] for event in _events(paths)] == [1, 1]


def test_shadow_rejects_malformed_existing_trace_before_loading(tmp_path):
    paths = _write_registration(tmp_path)
    paths.trace_path.write_text("not-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="existing trace"):
        _initialize(paths)


class _Network:
    def get_best_action(self, **_kwargs):
        return torch.tensor([1])


class _ShadowReturningDifferentAction:
    enabled = True

    def __init__(self):
        self.calls = []

    def observe_proposal(self, **kwargs):
        self.calls.append(kwargs)
        return 2

    def record_runtime_error(self, **_kwargs):
        self.enabled = False


def _minimal_agent(shadow):
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
    agent.latent_gated_shadow = shadow
    agent.last_game = None
    return agent


def test_rl_agent_ignores_any_shadow_return_value():
    shadow = _ShadowReturningDifferentAction()
    agent = _minimal_agent(shadow)

    assert agent.get_next_action_in_game(_game()) == ("decoded", 1)
    assert shadow.calls[0]["parent_action_index"] == 1


def test_rl_agent_preserves_parent_action_when_shadow_raises():
    class RaisingShadow(_ShadowReturningDifferentAction):
        def observe_proposal(self, **_kwargs):
            raise RuntimeError("shadow failure")

    shadow = RaisingShadow()
    agent = _minimal_agent(shadow)

    assert agent.get_next_action_in_game(_game()) == ("decoded", 1)
    assert shadow.enabled is False
