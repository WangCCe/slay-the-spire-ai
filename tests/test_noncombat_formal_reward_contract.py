from __future__ import annotations

import copy
import json
import math
import os
import shutil
from pathlib import Path

import pytest

from analysis_scripts import noncombat_formal_reward_contract as reward
from analysis_scripts.noncombat_simulator_training_smoke import (
    simulator_training_reward,
)


def _transition(
    before: object,
    after: object,
    *,
    terminal: object = False,
    outcome: object = None,
    **extra: object,
) -> dict:
    return {
        "source_state": {"floor": before},
        "successor": {
            "state": {"floor": after, "outcome": outcome},
            "terminal": terminal,
        },
        **extra,
    }


def _copy_registered_sources(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[1]
    paths = [reward.SCRIPT_RELATIVE_PATH]
    paths.extend(path for path, _ in reward.SOURCE_BINDINGS.values())
    for relative in paths:
        source = source_root.joinpath(*relative.split("/"))
        destination = tmp_path.joinpath(*relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tmp_path


def _context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _copy_registered_sources(tmp_path / "repo")
    registration = reward.build_registration(
        repo_root=root,
        implementation_commit="a" * 40,
    )
    monkeypatch.setattr(
        reward,
        "_git_blob_bytes",
        lambda repo_root, commit, relative: repo_root.joinpath(
            *relative.split("/")
        ).read_bytes(),
    )
    return root, registration, reward.load_validated_context(
        registration, repo_root=root
    )


def test_floor_progress_matches_registered_bounds_and_smoke_formula():
    cases = [
        (-10, 0, 0.0),
        (0, 1, 1.0 / 57.0),
        (20, 19, 0.0),
        (56, 99, 1.0 / 57.0),
        (99, 57, 0.0),
        (0, 99, 1.0),
    ]
    for before, after, expected in cases:
        transition = _transition(before, after)
        channels = reward.reward_channels(transition)

        assert channels["floor_progress"] == pytest.approx(expected)
        assert channels["terminal_victory"] == 0
        assert simulator_training_reward(transition) == pytest.approx(expected)


@pytest.mark.parametrize("value", [True, None, "3", math.inf, -math.inf, math.nan])
def test_floor_progress_rejects_non_finite_or_non_numeric_values(value: object):
    with pytest.raises(reward.RewardContractBlocked, match="must be finite"):
        reward.floor_progress(value, 3)


def test_terminal_victory_requires_explicit_terminal_success():
    assert reward.terminal_victory(True, "player_victory") == 1
    assert reward.terminal_victory(False, "player_victory") == 0
    assert reward.terminal_victory(True, "player_loss") == 0
    assert reward.terminal_victory(True, None) == 0

    with pytest.raises(reward.RewardContractBlocked, match="terminal must be boolean"):
        reward.terminal_victory(1, "player_victory")
    with pytest.raises(reward.RewardContractBlocked, match="outcome"):
        reward.terminal_victory(True, 1)
    with pytest.raises(reward.RewardContractBlocked, match="must be an object"):
        reward.reward_channels(None)


def test_excluded_fields_cannot_change_either_channel():
    base = _transition(12, 13)
    noisy = _transition(
        12,
        13,
        behavior_action_probability=0.99,
        bottled_label="take",
        current_policy_label="leave",
        deck_heuristics={"score": 1000},
        gold=999,
        hp=1,
        ope_estimates={"value": 1000},
        simpleagent_label="skip",
        teacher_agreement=True,
    )

    assert reward.reward_channels(base) == reward.reward_channels(noisy)


def test_scalarization_requires_victory_first_or_strict_dominance():
    assert reward.validate_scalarization("lexicographic") == {
        "mode": "lexicographic",
        "priority": ["terminal_victory", "floor_progress"],
        "production_weight_selected": False,
    }
    strict = reward.validate_scalarization(
        "strict_primary_dominance", victory_weight=1.000001
    )
    assert strict["strict_dominance_proved"] is True

    for invalid_weight in (1.0, 0.0, -1.0, True, math.inf, math.nan):
        with pytest.raises(reward.RewardContractBlocked):
            reward.validate_scalarization(
                "strict_primary_dominance", victory_weight=invalid_weight
            )
    with pytest.raises(reward.RewardContractBlocked, match="no scalar weight"):
        reward.validate_scalarization("lexicographic", victory_weight=2.0)
    with pytest.raises(reward.RewardContractBlocked, match="unsupported mode"):
        reward.validate_scalarization("weighted_sum", victory_weight=2.0)


def test_contract_has_readiness_shape_without_runtime_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, context = _context(tmp_path, monkeypatch)
    artifacts = reward.build_artifacts(context)
    contract = json.loads(artifacts["contract.json"])

    assert contract["schema_version"] == "noncombat-formal-rl-reward-contract-v1"
    assert contract["primary_objective"] == {
        "direction": "maximize",
        "name": "terminal_victory",
        "outcome_field": "victory",
    }
    assert contract["reference_labels_excluded"] is True
    assert contract["provenance"]["simulator_live_separated"] is True
    assert contract["secondary_channels"] == [
        {
            "bounds": [0.0, 1.0],
            "discount": 1.0,
            "formula": (
                "max(0,cap(successor_floor,0,57)-"
                "cap(source_floor,0,57))/57"
            ),
            "max_floor": 57,
            "name": "floor_progress",
            "outcome_field": "floor_reached",
            "role": "potential_shaping",
            "scope": "simulator_training_only",
        }
    ]
    assert set(reward.EXCLUSIONS) == set(contract["exclusions"])
    assert not any(contract["authority"].values())
    assert contract["smoke_reward_assessment"]["formal_compatible"] is False
    assert contract["optimization"]["production_weight_selected"] is False


def test_registration_is_canonical_and_rejects_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _copy_registered_sources(tmp_path / "repo")
    registration = reward.build_registration(
        repo_root=root,
        implementation_commit="b" * 40,
    )
    monkeypatch.setattr(
        reward,
        "_git_blob_bytes",
        lambda repo_root, commit, relative: repo_root.joinpath(
            *relative.split("/")
        ).read_bytes(),
    )
    input_path = root / "registration.json"
    input_path.write_bytes(
        reward.canonical_json_bytes(registration)
    )
    assert reward.load_registration(input_path) == registration

    noncanonical = root / "noncanonical.json"
    noncanonical.write_text(json.dumps(registration), encoding="utf-8")
    with pytest.raises(reward.RewardContractBlocked, match="not canonical"):
        reward.load_registration(noncanonical)

    contract_spec = root.joinpath(
        *reward.SOURCE_BINDINGS["contract_spec"][0].split("/")
    )
    contract_spec.write_bytes(contract_spec.read_bytes() + b"\n")
    with pytest.raises(
        reward.RewardContractBlocked, match=r"(size|SHA-256) mismatch"
    ):
        reward.load_validated_context(registration, repo_root=root)


def test_artifacts_publish_manifest_last_and_recompute_exactly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, context = _context(tmp_path, monkeypatch)
    first = reward.build_artifacts(context)
    second = reward.build_artifacts(context)
    assert first == second

    output = tmp_path / "published"
    reward.publish_artifacts(output, first)
    manifest = reward.recompute_artifact_directory(
        context=context, output_dir=output
    )
    assert manifest["verdict"] == reward.VERDICT
    assert not any(manifest["authority"].values())

    verification = output / "verification.json"
    verification.write_bytes(verification.read_bytes() + b"\n")
    with pytest.raises(reward.RewardContractBlocked, match="hash closure"):
        reward.validate_artifact_directory(output)


def test_interrupted_publication_removes_partial_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, context = _context(tmp_path, monkeypatch)
    artifacts = reward.build_artifacts(context)
    output = tmp_path / "interrupted"

    def fail_before_manifest(source: os.PathLike, destination: os.PathLike) -> None:
        if Path(destination).name == "artifact_manifest.json":
            raise OSError("injected manifest install failure")
        os.replace(source, destination)

    with pytest.raises(OSError, match="injected manifest"):
        reward.publish_artifacts(output, artifacts, replace=fail_before_manifest)
    assert not output.exists()


def test_fixed_verification_covers_all_registered_invariants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, context = _context(tmp_path, monkeypatch)
    verification = json.loads(reward.build_artifacts(context)["verification.json"])

    assert all(verification["checks"].values())
    assert verification["monotone_episode_floor_progress"] == pytest.approx(1.0)
    assert all(example["passed"] for example in verification["fixed_examples"])
    assert not any(verification["authority"].values())


def test_manifest_rejects_authority_or_contract_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, context = _context(tmp_path, monkeypatch)
    artifacts = reward.build_artifacts(context)
    tampered = copy.deepcopy(artifacts)
    contract = json.loads(tampered["contract.json"])
    contract["authority"]["formal_noncombat_rl"] = True
    tampered["contract.json"] = reward.canonical_json_bytes(contract)

    with pytest.raises(reward.RewardContractBlocked, match="hash closure"):
        reward.validate_artifact_payloads(tampered)
