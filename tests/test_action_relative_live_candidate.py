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
from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
    build_development_artifact,
)
from spirecomm.ai.rl.v2.action_relative_live_candidate import (
    REGISTRATION_ENV,
    SAFETY_POLICY_VERSION,
    initialize_action_relative_live_candidate,
    load_live_candidate_registration,
)
from spirecomm.ai.rl.v2.action_relative_live_shadow import (
    REGISTRATION_ENV as ACTION_RELATIVE_SHADOW_REGISTRATION_ENV,
)
from spirecomm.ai.rl.v2.agent import RLAgentV2
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.network import create_dqn_v2
from spirecomm.communication.action import EndTurnAction, PlayCardAction, WaitAction


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
    tmp_path.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(113)
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
    trace_path = tmp_path / "reports" / "candidate" / "trace.jsonl"
    registration = {
        "schema_version": 1,
        "experiment_id": "action-relative-candidate-fixture",
        "mode": "candidate",
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
        "inference_device": "cpu",
        "safety_policy_version": SAFETY_POLICY_VERSION,
        "trace_path": str(trace_path),
        "maximum_decision_count": maximum_decisions,
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
    return initialize_action_relative_live_candidate(**arguments)


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
    return [
        json.loads(line)
        for line in paths.trace_path.read_text(encoding="utf-8").splitlines()
    ]


def test_candidate_is_default_off(monkeypatch, tmp_path):
    monkeypatch.delenv(REGISTRATION_ENV, raising=False)
    parent = create_dqn_v2(device="cpu", **METADATA)

    assert initialize_action_relative_live_candidate(
        parent=parent,
        metadata=METADATA,
        model_path=None,
        training=False,
        epsilon=0.0,
        expert_mix_enabled=False,
        repo_root=tmp_path,
        device="cpu",
    ) is None


def test_candidate_registration_is_exact_and_source_bound(tmp_path):
    paths = _fixture(tmp_path)
    loaded = load_live_candidate_registration(
        paths.registration_path,
        repo_root=tmp_path,
        require_committed=False,
    )

    assert loaded.inference_device == "cpu"
    assert loaded.safety_policy_version == SAFETY_POLICY_VERSION
    assert loaded.maximum_decision_count == 3

    paths.registration["safety_policy_version"] = "mutable-policy"
    paths.registration_path.write_text(json.dumps(paths.registration), encoding="utf-8")
    with pytest.raises(ValueError, match="safety policy"):
        load_live_candidate_registration(
            paths.registration_path,
            repo_root=tmp_path,
            require_committed=False,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("mode", "shadow", "mode"),
        ("inference_device", "cuda", "inference device"),
        ("schema_version", 2, "schema"),
    ],
)
def test_candidate_registration_rejects_mode_device_or_schema(
    tmp_path, field, value, message
):
    paths = _fixture(tmp_path)
    paths.registration[field] = value
    paths.registration_path.write_text(json.dumps(paths.registration), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_live_candidate_registration(
            paths.registration_path,
            repo_root=tmp_path,
            require_committed=False,
        )


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
    with pytest.raises(ValueError):
        _initialize(_fixture(tmp_path), **overrides)


def test_candidate_uses_distinct_cpu_parent_without_mutating_production(tmp_path):
    paths = _fixture(tmp_path)
    original_hash = state_dict_sha256(paths.parent.state_dict())
    original_storage = [parameter.data_ptr() for parameter in paths.parent.parameters()]

    runtime = _initialize(paths)

    assert runtime.residual.parent is not paths.parent
    assert {parameter.device.type for parameter in runtime.residual.parameters()} == {
        "cpu"
    }
    assert state_dict_sha256(runtime.residual.parent.state_dict()) == original_hash
    assert state_dict_sha256(paths.parent.state_dict()) == original_hash
    assert [parameter.data_ptr() for parameter in paths.parent.parameters()] == original_storage


def test_safe_late_takeover_records_complete_provenance(tmp_path):
    paths = _fixture(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game)

    assert runtime.prepare_candidate_action(game=game, guard_action_index=1) == 0
    assert runtime.resolve_safety_decision(
        selected_action_index=0, veto_reason=""
    )
    assert runtime.commit_executed_action(game=game, executed_action_index=0)

    event = _events(paths)[0]
    assert event["parent_action_index"] == 90
    assert event["guard_action_index"] == 1
    assert event["candidate_action_index"] == 0
    assert event["candidate_has_authority"] is True
    assert event["safety_policy_version"] == SAFETY_POLICY_VERSION
    assert event["safety_veto_reason"] == ""
    assert event["selected_action_index"] == 0
    assert event["candidate_takeover_applied"] is True
    assert event["executed_action_index"] == 0
    assert event["selected_matches_executed"] is True


def test_safety_veto_retains_guard_and_records_reason(tmp_path):
    paths = _fixture(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game)

    assert runtime.prepare_candidate_action(game=game, guard_action_index=1) == 0
    assert runtime.resolve_safety_decision(
        selected_action_index=1, veto_reason="self_lethal"
    )
    assert runtime.commit_executed_action(game=game, executed_action_index=1)

    event = _events(paths)[0]
    assert event["safety_veto_reason"] == "self_lethal"
    assert event["selected_action_index"] == 1
    assert event["candidate_takeover_applied"] is False
    assert event["selected_matches_executed"] is True


def test_safety_veto_error_invalidates_candidate_arm(tmp_path):
    paths = _fixture(tmp_path)
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game)

    assert runtime.prepare_candidate_action(game=game, guard_action_index=1) == 0
    assert runtime.resolve_safety_decision(
        selected_action_index=1,
        veto_reason="safety_veto_error:RuntimeError",
    )
    assert runtime.commit_executed_action(game=game, executed_action_index=1)

    event = _events(paths)[0]
    assert event["runtime_error_type"] == "RuntimeError"
    assert event["candidate_takeover_applied"] is False
    assert runtime.enabled is False


def test_candidate_abstention_and_ineligible_support_retain_guard(tmp_path):
    paths = _fixture(tmp_path)
    paths.action_mask[:] = False
    paths.action_mask[[1, 90]] = True
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game)

    assert runtime.prepare_candidate_action(game=game, guard_action_index=1) is None
    assert runtime.commit_executed_action(game=game, executed_action_index=1)
    event = _events(paths)[0]
    assert event["eligible"] is True
    assert event["candidate_action_index"] is None
    assert event["selected_action_index"] == 1
    assert event["candidate_takeover_applied"] is False

    paths = _fixture(tmp_path / "ineligible")
    runtime = _initialize(paths)
    game = _game()
    assert _observe(runtime, paths, game, parent_action=2)
    assert runtime.prepare_candidate_action(game=game, guard_action_index=2) is None
    assert runtime.commit_executed_action(game=game, executed_action_index=2)
    assert _events(paths)[0]["support_reason"] == "parent_not_end_turn"


def test_candidate_transient_wait_does_not_consume_budget(tmp_path):
    paths = _fixture(tmp_path, maximum_decisions=1)
    runtime = _initialize(paths)
    game = _game()

    assert _observe(runtime, paths, game)
    assert runtime.discard_transient_action(reason="wait_action")
    assert runtime.decision_count == 0
    assert _events(paths)[0]["event_type"] == "transient_discard"


class _RecordingRLAgent:
    def __init__(self, candidate):
        self.candidate = candidate
        self.resolutions = []

    def propose_action_relative_candidate(self, _game, _guard):
        return self.candidate

    def resolve_action_relative_candidate(
        self, _game, _guard, selected, *, veto_reason
    ):
        self.resolutions.append((selected, veto_reason))
        return selected


def test_outer_agent_applies_safe_late_candidate(monkeypatch):
    guard = PlayCardAction(card_index=1, target_index=0)
    candidate = PlayCardAction(card_index=0, target_index=0)
    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.rl_agent = _RecordingRLAgent(candidate)
    monkeypatch.setattr(
        agent,
        "_action_relative_candidate_veto_reason",
        lambda *_args: "",
    )

    assert agent._apply_action_relative_candidate(guard, _game()) is candidate
    assert agent.rl_agent.resolutions == [(candidate, "")]


def test_outer_agent_safety_veto_retains_guard(monkeypatch):
    guard = PlayCardAction(card_index=1, target_index=0)
    candidate = PlayCardAction(card_index=0, target_index=0)
    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.rl_agent = _RecordingRLAgent(candidate)
    monkeypatch.setattr(
        agent,
        "_action_relative_candidate_veto_reason",
        lambda *_args: "mandatory_survival_guard",
    )

    assert agent._apply_action_relative_candidate(guard, _game()) is guard
    assert agent.rl_agent.resolutions == [(guard, "mandatory_survival_guard")]


def test_outer_agent_skips_late_candidate_for_transient_or_end_turn():
    candidate = PlayCardAction(card_index=0, target_index=0)
    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.rl_agent = _RecordingRLAgent(candidate)

    wait = WaitAction(timeout=1)
    end_turn = EndTurnAction()
    assert agent._apply_action_relative_candidate(wait, _game()) is wait
    assert agent._apply_action_relative_candidate(end_turn, _game()) is end_turn
    assert agent.rl_agent.resolutions == []


def test_fixed_safety_veto_rejects_self_lethal_candidate(monkeypatch):
    agent = CombatRLAgent.__new__(CombatRLAgent)
    candidate = PlayCardAction(card_index=0, target_index=0)
    monkeypatch.setattr(agent, "_is_valid_combat_action", lambda *_args: True)
    monkeypatch.setattr(agent, "_is_self_lethal_card_action", lambda *_args: True)

    assert (
        agent._action_relative_candidate_veto_reason(candidate, _game())
        == "self_lethal"
    )


def test_fixed_safety_veto_preserves_mandatory_guard(monkeypatch):
    agent = CombatRLAgent.__new__(CombatRLAgent)
    candidate = PlayCardAction(card_index=0, target_index=0)
    monkeypatch.setattr(agent, "_is_valid_combat_action", lambda *_args: True)
    monkeypatch.setattr(agent, "_is_self_lethal_card_action", lambda *_args: False)
    monkeypatch.setattr(
        agent, "_is_pressure_unsafe_hp_loss_card_action", lambda *_args: False
    )
    monkeypatch.setattr(agent, "_card_for_action", lambda *_args: object())
    monkeypatch.setattr(
        agent,
        "_would_low_hp_hp_loss_be_filler_without_pressure",
        lambda *_args: False,
    )
    monkeypatch.setattr(
        agent,
        "_get_slime_split_aoe_survival_replacement",
        lambda *_args: PlayCardAction(card_index=1, target_index=0),
    )

    assert agent._action_relative_candidate_veto_reason(
        candidate, _game()
    ) == "mandatory_guard:slime_split_aoe_survival"


class _RecordingCandidateRuntime:
    enabled = True
    pending = object()

    def __init__(self):
        self.prepared = []
        self.resolved = []

    def prepare_candidate_action(self, **kwargs):
        self.prepared.append(kwargs)
        return 0

    def resolve_safety_decision(self, **kwargs):
        self.resolved.append(kwargs)
        return True

    def record_runtime_error(self, **_kwargs):
        self.enabled = False


def test_rl_v2_routes_late_candidate_prepare_and_resolution():
    runtime = _RecordingCandidateRuntime()
    candidate_action = object()
    guard_action = object()
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.action_relative_candidate = runtime
    agent.action_encoder = SimpleNamespace(
        encode_action=lambda action, _game: 1 if action is guard_action else 0,
        decode_action=lambda index, _game: candidate_action if index == 0 else None,
    )
    game = _game()

    assert agent.propose_action_relative_candidate(game, guard_action) is candidate_action
    assert runtime.prepared == [{"game": game, "guard_action_index": 1}]
    assert (
        agent.resolve_action_relative_candidate(
            game, guard_action, candidate_action, veto_reason=""
        )
        is candidate_action
    )
    assert runtime.resolved == [
        {"selected_action_index": 0, "veto_reason": ""}
    ]


def test_rl_v2_rejects_action_relative_shadow_candidate_overlap(
    monkeypatch, tmp_path
):
    monkeypatch.setenv(ACTION_RELATIVE_SHADOW_REGISTRATION_ENV, "shadow.json")
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
