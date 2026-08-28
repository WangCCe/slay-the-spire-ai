from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np
import pytest
import torch

import analysis_scripts.combat_rl_guard_advantage_residual_evaluation as evaluation
from analysis_scripts.combat_lightspeed_bridge import MappedCombatState
from analysis_scripts.combat_rl_guard_advantage_residual_evaluation import (
    FIXED_POLICY_GATES,
    FIXED_RECIPE,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    _validate_registration,
    apply_policy_gates,
    select_post_guard_action,
)
from spirecomm.ai.rl.v2.state_encoder import EncodedStateV2, StateEncoderV2


class StubResidual:
    def __init__(self, *, gate_open: bool, residual_action: int):
        self.gate_open = gate_open
        self.residual_action = residual_action

    def select_actions(self, *args):
        return SimpleNamespace(
            gate_open=torch.tensor([self.gate_open]),
            residual_actions=torch.tensor([self.residual_action]),
            gate_probabilities=torch.tensor([0.9 if self.gate_open else 0.1]),
        )


class MaskAwareStubResidual:
    def select_actions(self, *args):
        alternative_mask = args[-1]
        action = int(torch.where(alternative_mask[0])[0].max().item())
        return SimpleNamespace(
            gate_open=torch.tensor([True]),
            residual_actions=torch.tensor([action]),
            gate_probabilities=torch.tensor([0.9]),
        )


def _mapped() -> MappedCombatState:
    continuous = np.zeros(StateEncoderV2.CONTINUOUS_DIM, dtype=np.float32)
    action_mask = np.zeros(133, dtype=bool)
    action_mask[[0, 6, 90]] = True
    return MappedCombatState(
        state=EncodedStateV2(
            continuous=continuous,
            card_ids=np.asarray([1, 2] + [0] * 8, dtype=np.int64),
            potion_ids=np.zeros(5, dtype=np.int64),
            relic_ids=np.zeros(40, dtype=np.int64),
        ),
        action_mask=action_mask,
    )


def _actions() -> list[dict]:
    return [
        {"action_id": "card-0", "kind": "play_card", "rl_action_index": 0, "available": True},
        {"action_id": "card-1", "kind": "play_card", "rl_action_index": 6, "available": True},
        {"action_id": "end", "kind": "end_turn", "rl_action_index": 90, "available": True},
    ]


def test_post_guard_path_preserves_exact_guard_when_abstaining():
    guarded = _actions()[0]
    selected, trace, reason = select_post_guard_action(
        StubResidual(gate_open=False, residual_action=6),
        mapped=_mapped(),
        legal_actions=_actions(),
        guarded_action=guarded,
        guard_replaced=True,
        max_canonical_actions=8,
    )
    assert reason == ""
    assert selected == guarded
    assert trace["gate_open"] is False
    assert trace["intervened"] is False
    assert trace["final_action_index"] == 0


def test_post_guard_path_records_legal_distinct_intervention():
    selected, trace, reason = select_post_guard_action(
        StubResidual(gate_open=True, residual_action=6),
        mapped=_mapped(),
        legal_actions=_actions(),
        guarded_action=_actions()[0],
        guard_replaced=True,
        max_canonical_actions=8,
    )
    assert reason == ""
    assert selected["rl_action_index"] == 6
    assert trace["intervened"] is True
    assert trace["guard_action_index"] == 0
    assert trace["residual_action_index"] == 6
    assert trace["latency_ms"] >= 0.0


def test_non_guard_state_does_not_call_residual():
    selected, trace, reason = select_post_guard_action(
        object(),
        mapped=_mapped(),
        legal_actions=_actions(),
        guarded_action=_actions()[2],
        guard_replaced=False,
        max_canonical_actions=8,
    )
    assert selected["rl_action_index"] == 90
    assert trace is None
    assert reason == "guard_not_replaced"


def test_end_turn_constraint_is_applied_before_residual_selection():
    unrestricted, unrestricted_trace, _ = select_post_guard_action(
        MaskAwareStubResidual(),
        mapped=_mapped(),
        legal_actions=_actions(),
        guarded_action=_actions()[0],
        guard_replaced=True,
        max_canonical_actions=8,
    )
    masked, masked_trace, reason = select_post_guard_action(
        MaskAwareStubResidual(),
        mapped=_mapped(),
        legal_actions=_actions(),
        guarded_action=_actions()[0],
        guard_replaced=True,
        max_canonical_actions=8,
        forbidden_residual_action_indices=frozenset({90}),
    )
    assert unrestricted["rl_action_index"] == 90
    assert unrestricted_trace["forbidden_residual_action_indices"] == []
    assert reason == ""
    assert masked["rl_action_index"] == 6
    assert masked_trace["forbidden_residual_action_indices"] == [90]


def test_constraint_abstains_to_exact_guard_when_it_removes_every_alternative():
    mapped = _mapped()
    mapped.action_mask[6] = False
    actions = [_actions()[0], _actions()[2]]
    selected, trace, reason = select_post_guard_action(
        object(),
        mapped=mapped,
        legal_actions=actions,
        guarded_action=actions[0],
        guard_replaced=True,
        max_canonical_actions=8,
        forbidden_residual_action_indices=frozenset({90}),
    )
    assert selected == actions[0]
    assert trace is None
    assert reason == "forbidden_actions_removed_all_alternatives"


def _registration() -> dict:
    runner = evaluation.REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]
    inputs = {
        name: {"path": f"D:/fixture/{name}.bin", "sha256": str(index + 1) * 64}
        for index, name in enumerate(
            ("native_module", "items_json", "parent_checkpoint", "residual_artifact", "train_corpus", "evaluation_corpus")
        )
    }
    return {
        "schema_version": 1,
        "experiment_id": evaluation.EXPERIMENT_ID,
        "source_commit": "a" * 40,
        "runner": {"path": str(runner), "sha256": "b" * 64},
        "source_files": {
            path: ("b" * 64 if path == SOURCE_SNAPSHOT_PATHS[0] else "c" * 64)
            for path in SOURCE_SNAPSHOT_PATHS
        },
        "inputs": inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "policy_gates": copy.deepcopy(FIXED_POLICY_GATES),
        "output_dir": str(evaluation.REPORTS_ROOT / "guard_residual_eval_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def test_registration_recipe_gates_and_authority_are_exact():
    assert _validate_registration(_registration()) == _registration()
    assert FIXED_RECIPE["seed_first"] == 264000
    assert FIXED_RECIPE["seed_last"] == 264255
    assert FIXED_RECIPE["max_canonical_actions"] == 8


@pytest.mark.parametrize("section", ["recipe", "policy_gates", "authority"])
def test_registration_rejects_execution_mutation(section):
    payload = _registration()
    if section == "recipe":
        payload[section]["seed_last"] += 1
    elif section == "policy_gates":
        payload[section]["mean_reward_delta_non_negative"] = False
    else:
        payload[section]["gameplay"] = True
    with pytest.raises(ValueError, match=section.replace("_", " ")):
        _validate_registration(payload)


def test_policy_gate_applies_all_fixed_conditions():
    paired = {
        "aggregate": {
            "candidate_only_victories": 2,
            "control_only_victories": 1,
            "mean_reward_delta": 0.1,
            "mean_player_hp_delta": 0.2,
            "excluded_nonterminal_profile_count": 0,
        }
    }
    candidate = {"aggregate": {"residual_intervention_count": 3}}
    passed = apply_policy_gates(paired, candidate)
    assert passed["all_conditions_passed"] is True
    assert passed["decision"].startswith("simulator_promising")
    paired["aggregate"]["mean_reward_delta"] = -0.01
    failed = apply_policy_gates(paired, candidate)
    assert failed["all_conditions_passed"] is False
    assert failed["decision"] == "fixed_residual_recipe_failed_close_without_sweep"
