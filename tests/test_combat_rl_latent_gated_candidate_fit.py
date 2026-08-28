from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

import analysis_scripts.combat_rl_latent_gated_candidate_fit as candidate_fit
from analysis_scripts.combat_rl_latent_gated_candidate_fit import (
    FIXED_RECIPE,
    FIXED_TECHNICAL_GATES,
    REPORTS_ROOT,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    aggregate_eligibility,
    evaluate_candidate,
    fit_candidate,
    load_committed_registration,
    publish_result,
    validate_registration_payload,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import (
    LatentGateConfig,
    LatentGatedActionAdapter,
    state_dict_sha256,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


EXPERIMENT_ID = "combat-rl-latent-gated-candidate-fit-20260828-r1"
METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 3,
    "card_vocab": 5,
    "potion_vocab": 5,
    "relic_vocab": 5,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}
RESULT_AUTHORITY = {
    "development_candidate": True,
    "gameplay": False,
    "communication_mod": False,
    "online_training": False,
    "production_checkpoint_loading": False,
    "qualification": False,
    "promotion": False,
}


def _registration() -> dict:
    runner = candidate_fit.REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": "a" * 40,
        "runner": {
            "path": str(runner),
            "sha256": "b" * 64,
        },
        "source_files": {
            path: ("b" * 64 if path == SOURCE_SNAPSHOT_PATHS[0] else "c" * 64)
            for path in SOURCE_SNAPSHOT_PATHS
        },
        "inputs": {
            "native_module": {
                "path": "reports/fixture/sts_lightspeed.pyd",
                "sha256": "e" * 64,
            },
            "dll_directories": [],
            "items_json": {
                "path": "reports/fixture/items.json",
                "sha256": "f" * 64,
            },
            "parent_checkpoint": {
                "path": "reports/fixture/parent.pth",
                "sha256": "1" * 64,
            },
            "development_replay": {
                "path": "reports/fixture/development.pth",
                "sha256": "2" * 64,
                "transition_count": 8,
            },
            "evaluation_replays": [
                {
                    "id": "evaluation-a",
                    "path": "reports/fixture/evaluation-a.pth",
                    "sha256": "3" * 64,
                    "transition_count": 8,
                },
                {
                    "id": "evaluation-b",
                    "path": "reports/fixture/evaluation-b.pth",
                    "sha256": "4" * 64,
                    "transition_count": 9,
                },
            ],
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "technical_gates": copy.deepcopy(FIXED_TECHNICAL_GATES),
        "output_dir": str(REPORTS_ROOT / "combat_rl_latent_gated_candidate_fit_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def test_fixed_recipe_gates_authority_and_registration_schema_are_exact():
    assert FIXED_RECIPE == {
        "architecture": "frozen_parent_latent_gated_legal_action_correction",
        "hidden_dim": 64,
        "simulator_seed_first": 185000,
        "simulator_seed_last": 185255,
        "battle_indices": [0, 3, 6, 9],
        "simulator_training_seed": 2026082814,
        "classifier_seed": 2026082816,
        "simulator_updates": 128,
        "development_gate_updates": 128,
        "action_updates": 256,
        "batch_size": 64,
        "learning_rate": pytest.approx(0.001),
        "direct_open_calibration_cap": pytest.approx(0.10),
        "simulator_validation_stride": 5,
        "device": "cpu",
    }
    assert FIXED_TECHNICAL_GATES == {
        "direct_gate_open_share_maximum": pytest.approx(0.15),
        "changed_gate_open_share_minimum": pytest.approx(0.75),
        "direct_candidate_agreement_minimum": pytest.approx(0.85),
        "changed_correction_agreement_minimum": pytest.approx(0.35),
        "changed_candidate_agreement_minimum": pytest.approx(0.25),
        "overall_candidate_agreement_uplift_minimum": pytest.approx(0.10),
        "positive_energy_end_turn_increase_maximum": 0,
    }
    assert REGISTERED_AUTHORITY == {
        "cpu_development_fit": True,
        "native_loading": True,
        "gameplay": False,
        "communication_mod": False,
        "online_training": False,
        "production_checkpoint_loading": False,
        "qualification": False,
        "promotion": False,
    }

    payload = _registration()
    assert validate_registration_payload(payload) == payload


@pytest.mark.parametrize(
    "mutation",
    [
        "root_extra",
        "runner_extra",
        "inputs_missing",
        "bad_commit",
        "bad_sha256",
        "empty_source_files",
        "escaping_source_path",
        "missing_source_file",
        "zero_development_count",
        "zero_evaluation_count",
        "empty_evaluations",
        "duplicate_evaluation_id",
        "development_evaluation_overlap",
        "duplicate_evaluation_sha256",
        "duplicate_evaluation_path",
        "unbound_dll_directory",
        "output_outside_reports",
    ],
)
def test_registration_rejects_malformed_structure_and_bound_identities(mutation):
    payload = _registration()
    if mutation == "root_extra":
        payload["unexpected"] = True
    elif mutation == "runner_extra":
        payload["runner"]["unexpected"] = True
    elif mutation == "inputs_missing":
        del payload["inputs"]["items_json"]
    elif mutation == "bad_commit":
        payload["source_commit"] = "g" * 40
    elif mutation == "bad_sha256":
        payload["inputs"]["parent_checkpoint"]["sha256"] = "0" * 63
    elif mutation == "empty_source_files":
        payload["source_files"] = {}
    elif mutation == "escaping_source_path":
        payload["source_files"] = {"../outside.py": "c" * 64}
    elif mutation == "missing_source_file":
        del payload["source_files"][SOURCE_SNAPSHOT_PATHS[-1]]
    elif mutation == "zero_development_count":
        payload["inputs"]["development_replay"]["transition_count"] = 0
    elif mutation == "zero_evaluation_count":
        payload["inputs"]["evaluation_replays"][0]["transition_count"] = 0
    elif mutation == "empty_evaluations":
        payload["inputs"]["evaluation_replays"] = []
    elif mutation == "duplicate_evaluation_id":
        payload["inputs"]["evaluation_replays"][1]["id"] = "evaluation-a"
    elif mutation == "development_evaluation_overlap":
        payload["inputs"]["evaluation_replays"][0]["sha256"] = (
            payload["inputs"]["development_replay"]["sha256"]
        )
    elif mutation == "duplicate_evaluation_sha256":
        payload["inputs"]["evaluation_replays"][1]["sha256"] = (
            payload["inputs"]["evaluation_replays"][0]["sha256"]
        )
    elif mutation == "duplicate_evaluation_path":
        payload["inputs"]["evaluation_replays"][1]["path"] = (
            payload["inputs"]["evaluation_replays"][0]["path"]
        )
    elif mutation == "unbound_dll_directory":
        payload["inputs"]["dll_directories"] = ["D:/unbound"]
    else:
        payload["output_dir"] = "D:/SteamLibrary/production-surface"

    with pytest.raises(ValueError):
        validate_registration_payload(payload)


def test_registration_requires_runner_hash_to_match_source_snapshot():
    payload = _registration()
    payload["source_files"][SOURCE_SNAPSHOT_PATHS[0]] = "d" * 64

    with pytest.raises(ValueError, match="runner"):
        validate_registration_payload(payload)


def test_committed_registration_is_read_once_and_bound_to_head(
    tmp_path, monkeypatch
):
    payload = _registration()
    repo_root = tmp_path
    reports_root = repo_root / "reports"
    registration_path = reports_root / "registration.json"
    registration_path.parent.mkdir()
    payload["runner"]["path"] = str(repo_root / SOURCE_SNAPSHOT_PATHS[0])
    payload["output_dir"] = str(reports_root / "output")
    raw = json.dumps(payload, sort_keys=True).encode("ascii")
    registration_path.write_bytes(raw)
    monkeypatch.setattr(candidate_fit, "REPO_ROOT", repo_root)
    monkeypatch.setattr(candidate_fit, "REPORTS_ROOT", reports_root)
    monkeypatch.setattr(
        candidate_fit,
        "_committed_registration_bytes",
        lambda relative: raw,
    )
    monkeypatch.setattr(
        candidate_fit,
        "_source_file_unchanged",
        lambda commit, relative: True,
    )
    monkeypatch.setattr(candidate_fit, "_current_commit", lambda: "f" * 40)

    loaded, sha256 = load_committed_registration(registration_path)

    assert loaded["experiment_id"] == EXPERIMENT_ID
    assert sha256 == hashlib.sha256(raw).hexdigest()

    changed = copy.deepcopy(payload)
    changed["source_commit"] = "e" * 40
    registration_path.write_text(json.dumps(changed, sort_keys=True), encoding="ascii")
    with pytest.raises(ValueError, match="committed"):
        load_committed_registration(registration_path)


@pytest.mark.parametrize("section", ["recipe", "technical_gates", "authority"])
def test_registration_rejects_any_recipe_gate_or_authority_change(section):
    payload = _registration()
    if section == "recipe":
        payload[section]["simulator_updates"] += 1
    elif section == "technical_gates":
        payload[section]["direct_gate_open_share_maximum"] += 0.01
    else:
        payload[section]["gameplay"] = True

    with pytest.raises(ValueError, match=section.replace("_", " ")):
        validate_registration_payload(payload)


def _fit_fixture() -> dict:
    torch.manual_seed(17)
    parent = create_dqn_v2(device="cpu", **METADATA)
    probe = LatentGatedActionAdapter(parent, METADATA, LatentGateConfig())
    row_count = 8
    features = torch.zeros((row_count, probe.feature_dim), dtype=torch.float32)
    features[:4, :4] = -20.0
    features[4:, :4] = 20.0
    features[:, 4] = torch.linspace(-1.0, 1.0, row_count)
    changed = torch.tensor([False] * 4 + [True] * 4)
    masks = torch.ones((row_count, METADATA["action_dim"]), dtype=torch.bool)
    actions = torch.tensor([0, 1, 2, 0, 1, 1, 1, 1])
    recipe = copy.deepcopy(FIXED_RECIPE)
    recipe["simulator_updates"] = 4
    recipe["development_gate_updates"] = 4
    recipe["action_updates"] = 4
    recipe["batch_size"] = 4
    return {
        "parent": parent,
        "metadata": METADATA,
        "simulator_features": features.clone(),
        "simulator_labels": changed.clone(),
        "simulator_train_indices": torch.arange(row_count),
        "development_features": features.clone(),
        "development_masks": masks,
        "development_actions": actions,
        "development_changed": changed,
        "recipe": recipe,
    }


def _maximum_recall_under_cap(
    scores: torch.Tensor, changed: torch.Tensor, cap: float
) -> float:
    candidates = [math.inf, *torch.unique(scores.detach().cpu()).tolist()]
    recalls = []
    for threshold in candidates:
        opened = scores >= threshold
        direct_open_share = float(opened[~changed].float().mean().item())
        if direct_open_share <= cap + 1e-12:
            recalls.append(float(opened[changed].float().mean().item()))
    return max(recalls)


def test_fit_is_deterministic_freezes_parent_and_calibrates_on_development():
    fixture = _fit_fixture()
    parent_before = state_dict_sha256(fixture["parent"].state_dict())

    first_adapter, first = fit_candidate(**fixture)
    second_adapter, second = fit_candidate(**fixture)

    assert first == second
    assert first["simulator_update_count"] == 4
    assert first["development_gate_update_count"] == 4
    assert first["action_update_count"] == 4
    assert first["all_objectives_finite"] is True
    assert state_dict_sha256(first_adapter.gate.state_dict()) == state_dict_sha256(
        second_adapter.gate.state_dict()
    )
    assert state_dict_sha256(
        first_adapter.correction.state_dict()
    ) == state_dict_sha256(second_adapter.correction.state_dict())
    assert state_dict_sha256(fixture["parent"].state_dict()) == parent_before
    assert first["parent_state_dict_sha256_before"] == parent_before
    assert first["parent_state_dict_sha256_after"] == parent_before
    assert all(
        not parameter.requires_grad for parameter in first_adapter.parent.parameters()
    )
    assert all(
        parameter.grad is None for parameter in first_adapter.parent.parameters()
    )

    with torch.no_grad():
        scores = torch.sigmoid(
            first_adapter.gate(fixture["development_features"])
        ).reshape(-1)
    threshold = first["calibrated_gate_threshold"]
    changed = fixture["development_changed"]
    selected_recall = float(scores[changed].ge(threshold).float().mean().item())
    assert first_adapter.config.gate_threshold == pytest.approx(threshold)
    assert first["development_direct_open_share"] <= (
        fixture["recipe"]["direct_open_calibration_cap"] + 1e-12
    )
    assert selected_recall == pytest.approx(
        _maximum_recall_under_cap(
            scores,
            changed,
            fixture["recipe"]["direct_open_calibration_cap"],
        )
    )


def test_fit_rejects_an_illegal_changed_action():
    fixture = _fit_fixture()
    changed_row = int(torch.where(fixture["development_changed"])[0][0].item())
    action = int(fixture["development_actions"][changed_row].item())
    fixture["development_masks"][changed_row, action] = False

    with pytest.raises(ValueError, match="legal"):
        fit_candidate(**fixture)


class _SelectionAdapter:
    def __init__(self, selection: SimpleNamespace) -> None:
        self.selection = selection

    def eval(self):
        return self

    def select_actions(self, *args):
        return self.selection


def _evaluation_fixture(failure: str | None = None) -> tuple[dict, str | None]:
    row_count = 20
    changed = torch.tensor([False] * 10 + [True] * 10)
    executed = torch.ones(row_count, dtype=torch.long)
    parent = torch.tensor([1] * 10 + [2] * 10)
    correction = torch.ones(row_count, dtype=torch.long)
    gate_open = changed.clone()
    failed_criterion = None

    if failure == "direct_gate":
        gate_open[:2] = True
        failed_criterion = "direct_gate_open_share_at_most_ceiling"
    elif failure == "changed_gate":
        gate_open[17:] = False
        failed_criterion = "changed_gate_open_share_at_least_floor"
    elif failure == "direct_agreement":
        parent[:2] = 2
        failed_criterion = "direct_candidate_agreement_at_least_floor"
    elif failure == "changed_correction":
        correction[10:] = 2
        correction[10:13] = 1
        failed_criterion = "changed_correction_agreement_at_least_floor"
    elif failure == "changed_candidate":
        correction[10:] = 2
        correction[10:14] = 1
        gate_open[10:12] = False
        failed_criterion = "changed_candidate_agreement_at_least_floor"
    elif failure == "overall_uplift":
        parent[10:19] = 1
        failed_criterion = (
            "overall_candidate_agreement_uplift_at_least_floor"
        )
    elif failure == "positive_end_turn":
        executed[10] = 90
        correction[10] = 90
        failed_criterion = (
            "positive_energy_end_turn_increase_at_most_ceiling"
        )

    actions = torch.where(gate_open, correction, parent)
    selection = SimpleNamespace(
        actions=actions,
        parent_actions=parent,
        correction_actions=correction,
        gate_open=gate_open,
    )
    kwargs = {
        "adapter": _SelectionAdapter(selection),
        "continuous": torch.ones((row_count, 4), dtype=torch.float32),
        "card_ids": torch.zeros((row_count, 1), dtype=torch.long),
        "potion_ids": torch.zeros((row_count, 1), dtype=torch.long),
        "relic_ids": torch.zeros((row_count, 1), dtype=torch.long),
        "action_masks": torch.ones((row_count, 91), dtype=torch.bool),
        "executed_actions": executed,
        "changed": changed,
        "gates": FIXED_TECHNICAL_GATES,
    }
    return kwargs, failed_criterion


def test_evaluation_applies_every_registered_condition():
    kwargs, _ = _evaluation_fixture()

    evaluation = evaluate_candidate(**kwargs)

    expected = {
        "direct_gate_open_share_at_most_ceiling",
        "changed_gate_open_share_at_least_floor",
        "direct_candidate_agreement_at_least_floor",
        "changed_correction_agreement_at_least_floor",
        "changed_candidate_agreement_at_least_floor",
        "overall_candidate_agreement_uplift_at_least_floor",
        "positive_energy_end_turn_increase_at_most_ceiling",
        "all_conditions_passed",
    }
    assert set(evaluation["criteria"]) == expected
    assert all(evaluation["criteria"].values())


@pytest.mark.parametrize(
    "failure",
    [
        "direct_gate",
        "changed_gate",
        "direct_agreement",
        "changed_correction",
        "changed_candidate",
        "overall_uplift",
        "positive_end_turn",
    ],
)
def test_evaluation_rejects_each_independent_gate_failure(failure):
    kwargs, failed_criterion = _evaluation_fixture(failure)

    evaluation = evaluate_candidate(**kwargs)

    assert evaluation["criteria"][failed_criterion] is False
    assert evaluation["criteria"]["all_conditions_passed"] is False
    assert all(
        value is True
        for name, value in evaluation["criteria"].items()
        if name not in {failed_criterion, "all_conditions_passed"}
    )


def test_aggregate_fails_when_one_bound_evaluation_fails():
    passed = {"criteria": {"all_conditions_passed": True}}
    failed = {"criteria": {"all_conditions_passed": False}}

    eligible = aggregate_eligibility(
        {"evaluation-a": passed, "evaluation-b": copy.deepcopy(passed)}
    )
    ineligible = aggregate_eligibility(
        {"evaluation-a": passed, "evaluation-b": failed}
    )

    assert eligible == {
        "evaluation_replay_count": 2,
        "per_replay_passed": {
            "evaluation-a": True,
            "evaluation-b": True,
        },
        "all_conditions_passed": True,
        "decision": "eligible_for_separately_registered_gameplay_evaluation",
    }
    assert ineligible["per_replay_passed"] == {
        "evaluation-a": True,
        "evaluation-b": False,
    }
    assert ineligible["all_conditions_passed"] is False
    assert ineligible["decision"] == "fixed_candidate_fit_failed_cohort_closed"


def _artifact() -> dict:
    return {
        "checkpoint_kind": "latent_gated_correction_development",
        "production_compatible": False,
        "gate_state_dict": {"weight": torch.tensor([1.0])},
    }


def _report() -> dict:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "decision": "eligible_for_separately_registered_gameplay_evaluation",
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }


def test_publish_is_atomic_and_refuses_to_overwrite(tmp_path, monkeypatch):
    output = tmp_path / "candidate"
    staging = tmp_path / ".candidate.staging"
    real_replace = candidate_fit.os.replace
    observed = []

    def checked_replace(source, destination):
        source = Path(source)
        destination = Path(destination)
        assert source == staging
        assert destination == output
        assert not output.exists()
        assert (staging / "latent_gated_development_adapter.pth").is_file()
        assert (staging / "report.json").is_file()
        observed.append((source, destination))
        return real_replace(source, destination)

    monkeypatch.setattr(candidate_fit.os, "replace", checked_replace)
    published = publish_result(output, _artifact(), _report())

    assert observed == [(staging, output)]
    assert not staging.exists()
    assert json.loads((output / "report.json").read_text(encoding="ascii")) == published
    artifact_path = output / "latent_gated_development_adapter.pth"
    assert published["artifact"] == {
        "path": artifact_path.name,
        "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "size_bytes": artifact_path.stat().st_size,
        "production_compatible": False,
    }

    before = {path.name: path.read_bytes() for path in output.iterdir()}
    with pytest.raises(ValueError, match="already exists"):
        publish_result(output, _artifact(), _report())
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


@pytest.mark.parametrize("production_surface", ["artifact", "report"])
def test_publish_rejects_production_authority_without_partial_output(
    tmp_path, production_surface
):
    output = tmp_path / production_surface
    artifact = _artifact()
    report = _report()
    if production_surface == "artifact":
        artifact["production_compatible"] = True
    else:
        report["authority"]["production_checkpoint_loading"] = True

    with pytest.raises(ValueError, match="production|authority"):
        publish_result(output, artifact, report)

    assert not output.exists()
    assert not output.with_name(f".{output.name}.staging").exists()
