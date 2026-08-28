from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (
    FIXED_RECIPE as FIXED_FIT_RECIPE,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
    build_development_artifact,
)
from spirecomm.ai.rl.v2.action_relative_live_shadow import (
    REGISTRATION_ENV,
    initialize_action_relative_live_shadow,
    load_live_shadow_registration,
)
from spirecomm.ai.rl.v2.agent import RLAgentV2
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 91,
    "card_vocab": 6,
    "potion_vocab": 6,
    "relic_vocab": 6,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, maximum_decisions: int = 3):
    torch.manual_seed(31)
    parent = create_dqn_v2(device="cpu", **METADATA)
    parent.eval()
    residual = ActionRelativeAdvantageResidual(
        parent,
        METADATA,
        ActionRelativeAdvantageConfig(hidden_dim=8),
    )
    with torch.no_grad():
        for parameter in residual.scorer.parameters():
            parameter.zero_()
        residual.scorer[-1].bias.fill_(0.1)
    artifact = build_development_artifact(
        residual,
        parent_checkpoint_sha256="a" * 64,
        corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        recipe=FIXED_FIT_RECIPE,
        telemetry={"fixture": True},
    )
    artifact_path = tmp_path / "candidate.pth"
    torch.save(artifact, artifact_path)
    parent_checkpoint = tmp_path / "parent.pth"
    parent_checkpoint.write_bytes(b"parent fixture")
    trace_path = tmp_path / "reports" / "shadow" / "trace.jsonl"
    registration = {
        "schema_version": 1,
        "experiment_id": "action-relative-shadow-fixture",
        "mode": "shadow",
        "source_commit": "d" * 40,
        "candidate_artifact": {
            "path": str(artifact_path),
            "sha256": _sha256(artifact_path),
            "parent_checkpoint_sha256": "a" * 64,
            "train_corpus_sha256": "b" * 64,
            "evaluation_corpus_sha256": "c" * 64,
        },
        "production_parent_checkpoint": {
            "path": str(parent_checkpoint),
            "sha256": _sha256(parent_checkpoint),
        },
        "parent_state_dict_sha256": state_dict_sha256(parent.state_dict()),
        "trace_path": str(trace_path),
        "maximum_decision_count": maximum_decisions,
        "readiness_gates": {
            "minimum_eligible_count": 1,
            "maximum_p95_latency_ms": 500.0,
        },
    }
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(json.dumps(registration), encoding="utf-8")
    mask = np.zeros(91, dtype=bool)
    mask[[0, 1, 2, 90]] = True
    return SimpleNamespace(
        parent=parent,
        parent_checkpoint=parent_checkpoint,
        registration=registration,
        registration_path=registration_path,
        trace_path=trace_path,
        continuous=np.array([0.5, -0.25, 0.75, 0.0], dtype=np.float32),
        card_ids=np.array([1], dtype=np.int64),
        potion_ids=np.array([2], dtype=np.int64),
        relic_ids=np.array([3], dtype=np.int64),
        action_mask=mask,
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
    return initialize_action_relative_live_shadow(**arguments)


def _game():
    return SimpleNamespace(
        floor=7,
        turn=3,
        act=1,
        room_type="MonsterRoom",
        screen_type="NONE",
        player=SimpleNamespace(energy=2),
        monsters=[SimpleNamespace(name="Jaw Worm")],
    )


def _observe(runtime, paths, game, *, parent_action: int = 90):
    return runtime.observe_proposal(
        game=game,
        continuous=paths.continuous,
        card_ids=paths.card_ids,
        potion_ids=paths.potion_ids,
        relic_ids=paths.relic_ids,
        action_mask=paths.action_mask,
        parent_action_index=parent_action,
    )


def _events(paths):
    return [json.loads(line) for line in paths.trace_path.read_text().splitlines()]


def _use_cpu_registration(paths):
    paths.registration["schema_version"] = 2
    paths.registration["inference_device"] = "cpu"
    paths.registration_path.write_text(json.dumps(paths.registration), encoding="utf-8")


def test_shadow_is_default_off(monkeypatch, tmp_path):
    monkeypatch.delenv(REGISTRATION_ENV, raising=False)
    parent = create_dqn_v2(device="cpu", **METADATA)
    assert initialize_action_relative_live_shadow(
        parent=parent,
        metadata=METADATA,
        model_path=None,
        training=False,
        epsilon=0.0,
        expert_mix_enabled=False,
        repo_root=tmp_path,
        device="cpu",
    ) is None


def test_registration_rejects_binding_or_mode_difference(tmp_path):
    paths = _fixture(tmp_path)
    loaded = load_live_shadow_registration(
        paths.registration_path,
        repo_root=tmp_path,
        require_committed=False,
    )
    assert loaded.maximum_decision_count == 3
    assert loaded.schema_version == 1
    assert loaded.inference_device == "parent"

    paths.registration["mode"] = "candidate"
    paths.registration_path.write_text(json.dumps(paths.registration))
    with pytest.raises(ValueError, match="mode"):
        load_live_shadow_registration(
            paths.registration_path,
            repo_root=tmp_path,
            require_committed=False,
        )


def test_schema_v2_registration_requires_cpu_inference(tmp_path):
    paths = _fixture(tmp_path)
    _use_cpu_registration(paths)

    loaded = load_live_shadow_registration(
        paths.registration_path,
        repo_root=tmp_path,
        require_committed=False,
    )

    assert loaded.schema_version == 2
    assert loaded.inference_device == "cpu"

    paths.registration["inference_device"] = "cuda"
    paths.registration_path.write_text(json.dumps(paths.registration), encoding="utf-8")
    with pytest.raises(ValueError, match="inference device"):
        load_live_shadow_registration(
            paths.registration_path,
            repo_root=tmp_path,
            require_committed=False,
        )


def test_schema_v2_registration_requires_explicit_device_key(tmp_path):
    paths = _fixture(tmp_path)
    paths.registration["schema_version"] = 2
    paths.registration_path.write_text(json.dumps(paths.registration), encoding="utf-8")

    with pytest.raises(ValueError, match="registration keys differ"):
        load_live_shadow_registration(
            paths.registration_path,
            repo_root=tmp_path,
            require_committed=False,
        )


def test_initialization_rejects_artifact_binding_difference(tmp_path):
    paths = _fixture(tmp_path)
    paths.registration["candidate_artifact"]["sha256"] = "f" * 64
    paths.registration_path.write_text(json.dumps(paths.registration))
    with pytest.raises(ValueError, match="candidate artifact SHA-256 differs"):
        _initialize(paths)


def test_schema_v2_cpu_shadow_uses_distinct_state_identical_parent(tmp_path):
    paths = _fixture(tmp_path)
    _use_cpu_registration(paths)
    original_hash = state_dict_sha256(paths.parent.state_dict())
    original_storage = [parameter.data_ptr() for parameter in paths.parent.parameters()]

    runtime = _initialize(paths)

    assert runtime.device == torch.device("cpu")
    assert runtime.residual.parent is not paths.parent
    assert {parameter.device.type for parameter in runtime.residual.parent.parameters()} == {
        "cpu"
    }
    assert state_dict_sha256(runtime.residual.parent.state_dict()) == original_hash
    assert state_dict_sha256(paths.parent.state_dict()) == original_hash
    assert [parameter.data_ptr() for parameter in paths.parent.parameters()] == original_storage


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_schema_v2_cpu_shadow_leaves_production_parent_on_cuda(tmp_path):
    paths = _fixture(tmp_path)
    _use_cpu_registration(paths)
    paths.parent.to("cuda")
    original_hash = state_dict_sha256(paths.parent.state_dict())
    original_storage = [parameter.data_ptr() for parameter in paths.parent.parameters()]

    runtime = _initialize(paths, device="cuda")

    assert {parameter.device.type for parameter in paths.parent.parameters()} == {"cuda"}
    assert [parameter.data_ptr() for parameter in paths.parent.parameters()] == original_storage
    assert state_dict_sha256(paths.parent.state_dict()) == original_hash
    assert runtime.device == torch.device("cpu")
    assert {parameter.device.type for parameter in runtime.residual.parent.parameters()} == {
        "cpu"
    }
    assert state_dict_sha256(runtime.residual.parent.state_dict()) == original_hash


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
    with pytest.raises(ValueError):
        _initialize(_fixture(tmp_path), **overrides)


def test_deferred_eligible_inference_masks_end_turn_and_has_no_authority(tmp_path):
    paths = _fixture(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game)
    assert runtime.commit_executed_action(game=game, executed_action_index=1)

    event = _events(paths)[0]
    assert event["eligible"] is True
    assert event["parent_action_index"] == 90
    assert event["guard_action_index"] == 1
    assert event["candidate_action_index"] == 0
    assert event["candidate_action_legal"] is True
    assert event["candidate_action_forbidden"] is False
    assert event["candidate_would_intervene"] is True
    assert event["executed_action_index"] == 1
    assert event["candidate_has_authority"] is False
    assert event["predicted_advantage"] == pytest.approx(1.0)


def test_ineligible_decision_records_support_without_inference(tmp_path):
    paths = _fixture(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game, parent_action=2)
    assert runtime.commit_executed_action(game=game, executed_action_index=2)

    event = _events(paths)[0]
    assert event["eligible"] is False
    assert event["support_reason"] == "parent_not_end_turn"
    assert event["candidate_action_index"] is None
    assert event["shadow_latency_ms"] == 0.0


def test_eligible_abstention_is_explicit_and_preserves_execution(tmp_path):
    paths = _fixture(tmp_path)
    paths.action_mask[:] = False
    paths.action_mask[[1, 90]] = True
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game)
    assert runtime.commit_executed_action(game=game, executed_action_index=1)

    event = _events(paths)[0]
    assert event["eligible"] is True
    assert event["candidate_action_index"] is None
    assert event["candidate_action_legal"] is None
    assert event["candidate_action_forbidden"] is None
    assert event["candidate_would_intervene"] is False
    assert event["candidate_matches_executed"] is None
    assert runtime.enabled is True


def test_inference_failure_is_recorded_and_disables_only_shadow(tmp_path, monkeypatch):
    paths = _fixture(tmp_path)
    runtime = _initialize(paths)
    monkeypatch.setattr(
        runtime.residual,
        "select_actions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fixture")),
    )
    game = _game()
    assert _observe(runtime, paths, game)
    assert runtime.commit_executed_action(game=game, executed_action_index=1)

    event = _events(paths)[0]
    assert event["runtime_error_type"] == "RuntimeError"
    assert event["candidate_has_authority"] is False
    assert event["executed_action_index"] == 1
    assert runtime.enabled is False


def test_budget_resumes_and_transient_wait_does_not_consume_it(tmp_path):
    paths = _fixture(tmp_path, maximum_decisions=1)
    first = _initialize(paths)
    game = _game()
    assert _observe(first, paths, game)
    assert first.discard_transient_action(reason="wait_action")
    assert first.decision_count == 0

    assert _observe(first, paths, game)
    assert first.commit_executed_action(game=game, executed_action_index=1)
    second = _initialize(paths)
    assert second.decision_count == 1
    assert _observe(second, paths, _game()) is False


def test_agent_commit_dispatches_to_action_relative_shadow_without_training():
    class RecordingShadow:
        pending = object()

        def __init__(self):
            self.commits = []

        def commit_executed_action(self, **kwargs):
            self.commits.append(kwargs)

    shadow = RecordingShadow()
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.latent_gated_candidate = None
    agent.latent_gated_shadow = None
    agent.action_relative_shadow = shadow
    agent.training_mode = False
    agent.trainer = None
    agent.action_encoder = SimpleNamespace(encode_action=lambda *_args: 1)
    game = _game()

    assert agent.commit_executed_action(game, object()) is False
    assert shadow.commits == [{"game": game, "executed_action_index": 1}]
