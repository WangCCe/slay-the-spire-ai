from pathlib import Path
import subprocess
import sys

from analysis_scripts.combat_lightspeed_calibration import (
    CalibrationConfig,
    REPORT_AUTHORITY,
    select_deterministic_action,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _actions():
    return [
        {"action_id": "play_card:1:1", "kind": "play_card", "rl_action_index": 7},
        {"action_id": "play_card:0:1", "kind": "play_card", "rl_action_index": 1},
        {"action_id": "end_turn", "kind": "end_turn", "rl_action_index": 90},
    ]


def test_deterministic_selector_uses_lowest_index_then_bounds_the_turn():
    selected = select_deterministic_action(
        _actions(),
        actions_since_end_turn=0,
        max_actions_per_turn=2,
    )
    bounded = select_deterministic_action(
        _actions(),
        actions_since_end_turn=2,
        max_actions_per_turn=2,
    )

    assert selected["action_id"] == "play_card:0:1"
    assert bounded["action_id"] == "end_turn"


def test_calibration_report_grants_no_runtime_or_policy_authority():
    expected = {
        "evaluation",
        "formal_rl",
        "gameplay",
        "mechanics_equivalence",
        "model_fitting",
        "model_loading",
        "ope",
        "policy_quality",
        "promotion",
        "qualification",
        "training",
    }

    assert set(REPORT_AUTHORITY) == expected
    assert not any(REPORT_AUTHORITY.values())


def test_calibration_profiles_are_deterministic_seed_index_product():
    config = CalibrationConfig(seeds=(7, 9), battle_indices=(0, 2, 4))

    assert config.profiles() == (
        (7, 0),
        (7, 2),
        (7, 4),
        (9, 0),
        (9, 2),
        (9, 4),
    )


def test_calibration_script_supports_direct_execution():
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "analysis_scripts" / "combat_lightspeed_calibration.py"),
            "--help",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--simulator-repo" in completed.stdout
