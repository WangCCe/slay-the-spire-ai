import copy
from pathlib import Path
import subprocess
import sys

import pytest

from analysis_scripts.combat_lightspeed_frozen_candidate_comparison import (
    CandidateBinding,
    ComparisonBlocked,
    _publish,
    load_candidate,
    rank_candidates,
    summarize_evaluation,
    summarize_pairwise,
    validate_candidate_structures,
    validate_matched_initialization,
)
from analysis_scripts.combat_lightspeed_training_smoke import create_fresh_trainer
from analysis_scripts.combat_lightspeed_bridge import sha256_file
from spirecomm.ai.rl.checkpoint_io import save_torch_checkpoint
from spirecomm.ai.rl.v2.id_mapping import IdMapper


REPO_ROOT = Path(__file__).resolve().parents[1]


def _mapper():
    return IdMapper(
        card_ids={"Strike": 1},
        potion_ids={"Fire Potion": 1},
        relic_ids={"Burning Blood": 1},
        card_tags={"Strike": []},
    )


def _write_candidate(path: Path, *, production_compatible=False):
    trainer = create_fresh_trainer(
        _mapper(),
        seed=17,
        batch_size=2,
        learning_starts=2,
    )
    checkpoint = {
        "checkpoint_schema_version": 0,
        "checkpoint_kind": "simulator_training_smoke",
        "source_type": "sts_lightspeed_combat_simulation",
        "production_compatible": production_compatible,
        "online_network_state_dict": copy.deepcopy(
            trainer.online_network.state_dict()
        ),
        "metadata": {
            "authority": {"simulator_fitting": True, "promotion": False},
            "source_binding": {"candidate_parameter_sha256": "f" * 64},
        },
    }
    save_torch_checkpoint(checkpoint, str(path))


def _row(
    seed,
    battle_index,
    outcome,
    *,
    hp=0,
    reward=0.0,
    decisions=0,
    failure_reason="",
):
    return {
        "seed": seed,
        "battle_index": battle_index,
        "progression": (
            {}
            if failure_reason
            else {
                "reached_battle_index": battle_index,
                "act": 1,
                "floor": battle_index + 1,
                "encounter": "CULTIST",
            }
        ),
        "outcome": outcome,
        "player_hp": hp,
        "decisions": decisions,
        "reward": reward,
        "unsupported_reason": (
            f"initialization_failure:{failure_reason}" if failure_reason else ""
        ),
        "initialization_failure_reason": failure_reason,
        "truncated": False,
        "card_select_settlement_count": 0,
        "card_select_settlement_task_counts": {},
    }


def test_candidate_loader_rejects_production_compatible_checkpoint(tmp_path):
    valid_path = tmp_path / "valid.pth"
    _write_candidate(valid_path)
    loaded = load_candidate(
        CandidateBinding("valid", valid_path, sha256_file(valid_path))
    )

    assert loaded["label"] == "valid"
    assert loaded["checkpoint_kind"] == "simulator_training_smoke"
    assert loaded["production_compatible"] is False
    with pytest.raises(ComparisonBlocked, match="candidate_checkpoint_hash_mismatch"):
        load_candidate(CandidateBinding("wrong-hash", valid_path, "0" * 64))

    invalid_path = tmp_path / "invalid.pth"
    _write_candidate(invalid_path, production_compatible=True)
    with pytest.raises(ComparisonBlocked, match="candidate_production_compatible"):
        load_candidate(
            CandidateBinding("invalid", invalid_path, sha256_file(invalid_path))
        )


def test_candidate_structures_must_match(tmp_path):
    left_path = tmp_path / "left.pth"
    right_path = tmp_path / "right.pth"
    _write_candidate(left_path)
    _write_candidate(right_path)
    left = load_candidate(CandidateBinding("left", left_path, sha256_file(left_path)))
    right = load_candidate(CandidateBinding("right", right_path, sha256_file(right_path)))

    validate_candidate_structures((left, right))
    right["state_dict"].pop("output_layer.bias")

    with pytest.raises(ComparisonBlocked, match="candidate_structure_mismatch"):
        validate_candidate_structures((left, right))


def test_reachable_summary_excludes_natural_unreachability():
    evaluation = {
        "rows": [
            _row(1, 0, "player_victory", hp=40, reward=20.0, decisions=8),
            _row(2, 0, "player_loss", hp=0, reward=-4.0, decisions=10),
            _row(
                3,
                9,
                "initialization_failure",
                failure_reason="baseline_loss_before_requested_battle",
            ),
        ]
    }

    summary = summarize_evaluation(evaluation)

    assert summary["profile_count_registered"] == 3
    assert summary["profile_count_reachable"] == 2
    assert summary["profile_count_unreachable"] == 1
    assert summary["mean_player_hp"] == 20.0
    assert summary["mean_reward"] == 8.0
    assert summary["battle_indices"]["0"]["profile_count_reachable"] == 2
    assert summary["battle_indices"]["9"]["profile_count_reachable"] == 0


def test_candidate_initialization_must_match():
    left = {"rows": [_row(7, 6, "player_victory", hp=20)]}
    right = {
        "rows": [
            _row(
                7,
                6,
                "initialization_failure",
                failure_reason="baseline_loss_before_requested_battle",
            )
        ]
    }

    with pytest.raises(ComparisonBlocked, match="candidate_initialization_mismatch"):
        validate_matched_initialization({"left": left, "right": right})


def test_pairwise_summary_and_ranking_preserve_guardrails():
    pairwise = {
        "rows": [
            {
                "seed": 1,
                "battle_index": 0,
                "control_outcome": "player_loss",
                "candidate_outcome": "player_victory",
                "player_hp_delta": 20,
                "reward_delta": 12.0,
                "decision_delta": -2,
            },
            {
                "seed": 2,
                "battle_index": 3,
                "control_outcome": "player_victory",
                "candidate_outcome": "player_victory",
                "player_hp_delta": 4,
                "reward_delta": 3.0,
                "decision_delta": 1,
            },
        ],
        "aggregate": {
            "profile_count": 2,
            "excluded_initialization_profile_count": 0,
            "excluded_initialization_failure_counts": {},
            "candidate_only_victories": 1,
            "control_only_victories": 0,
            "mean_player_hp_delta": 12.0,
            "mean_reward_delta": 7.5,
        },
    }

    summary = summarize_pairwise(pairwise)
    assert summary["battle_indices"]["0"]["candidate_only_victories"] == 1
    assert summary["battle_indices"]["3"]["mean_reward_delta"] == 3.0

    ranking = rank_candidates(
        {
            "reward_leader": {
                "mean_reward": 20.0,
                "mean_player_hp": 15.0,
                "player_victory_count": 8,
            },
            "guardrail_leader": {
                "mean_reward": 19.0,
                "mean_player_hp": 18.0,
                "player_victory_count": 9,
            },
        }
    )
    assert ranking["ordered_labels"] == ["reward_leader", "guardrail_leader"]
    assert ranking["winner"] is None
    assert ranking["guardrail_conflicts"]


def test_publish_hashes_canonical_report(tmp_path):
    output_dir = tmp_path / "comparison"
    report = {
        "verdict": "comparison_ready",
        "authority": {"promotion": False},
        "ranking": {"winner": "candidate"},
    }

    manifest = _publish(output_dir, report)

    assert manifest["artifacts"]["report.json"]["sha256"] == sha256_file(
        output_dir / "report.json"
    )
    assert (output_dir / "summary.md").is_file()


def test_production_agent_import_does_not_load_frozen_comparator():
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(REPO_ROOT)!r});"
        "import spirecomm.ai.rl.v2.agent;"
        "assert 'analysis_scripts.combat_lightspeed_frozen_candidate_comparison' "
        "not in sys.modules;"
        "assert 'sts_lightspeed_combat_adapter' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
