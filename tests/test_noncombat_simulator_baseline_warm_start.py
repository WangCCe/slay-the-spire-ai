from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from analysis_scripts.noncombat_simulator_baseline_warm_start import (
    INPUT_SCHEMA_VERSION,
    PRIOR_SEEDS,
    REGISTERED_SOURCE_FILES,
    WarmStartBlocked,
    load_warm_start_registration,
    validate_warm_start_registration,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _binding(path: str) -> dict[str, object]:
    return {
        "path": path,
        "sha256": "a" * 64,
        "size_bytes": 1,
    }


def valid_registration() -> dict[str, object]:
    policy_registration = json.loads(
        (
            REPO_ROOT
            / "reports"
            / "noncombat_simulator_policy_validity_20260802_input.json"
        ).read_text(encoding="utf-8")
    )
    prior_identity = policy_registration["identity"]
    return {
        "schema_version": INPUT_SCHEMA_VERSION,
        "identity": {
            "adapter_fit_input": copy.deepcopy(prior_identity["adapter_fit_input"]),
            "adapter_fit_report": copy.deepcopy(prior_identity["adapter_fit_report"]),
            "adapter_provenance": copy.deepcopy(prior_identity["adapter_provenance"]),
            "excluded_baselines": copy.deepcopy(prior_identity["excluded_baselines"]),
            "implementation": {
                "commit": "b" * 40,
                "source_files": list(REGISTERED_SOURCE_FILES),
                "source_sha256": "c" * 64,
            },
            "prior_evidence": {
                "policy_validity_manifest": _binding(
                    "reports/policy_validity/artifact_manifest.json"
                ),
                "policy_validity_registration": _binding(
                    "reports/policy_validity_input.json"
                ),
                "smoke_manifest": _binding("reports/smoke/artifact_manifest.json"),
                "smoke_registration": _binding("reports/smoke_input.json"),
            },
            "runtime": copy.deepcopy(prior_identity["runtime"]),
        },
        "study": {
            "ascension": 0,
            "cohorts": {
                "excluded_prior_seeds": list(PRIOR_SEEDS),
                "train_seeds": [4000, 4001],
                "validation_seeds": [5000],
                "final_test_seeds": [6000],
            },
            "evaluation": {
                "action_fit_metric": "exact_action_agreement",
                "bootstrap_resamples": 1000,
                "bootstrap_seed": 0,
                "confidence_level": 0.95,
                "primary_comparison": "candidate_minus_native_simple_agent",
                "thresholds": {
                    "floor_noninferiority_margin": 3.0,
                    "maximum_mean_floor_deficit": 1.0,
                    "minimum_macro_category_action_agreement": 0.75,
                    "minimum_overall_action_agreement": 0.85,
                    "minimum_per_category_action_agreement": 0.60,
                },
            },
            "execution": {
                "allow_alternate_cohort": False,
                "allow_model_selection": False,
                "allow_parameter_retry": False,
                "allow_test_on_validation_failure": False,
                "model_config_count": 1,
                "primary_count": 1,
                "replay_count": 1,
                "validation_is_stop_gate": True,
            },
            "limits": {
                "max_decisions_per_episode": 500,
                "max_demo_rows": 10_000,
                "max_epochs": 10,
                "max_final_policy_episodes": 2,
                "max_total_policy_episodes": 6,
                "max_train_episodes": 2,
                "max_validation_policy_episodes": 2,
                "max_wall_seconds_per_execution": 600.0,
            },
            "model": {
                "activation": "relu",
                "architecture": "candidate-ranker-mlp-v1",
                "dropout": 0.0,
                "feature_version": "noncombat-simulator-policy-features-v1",
                "hash_dim": 1024,
                "hidden_dim": 128,
                "model_seed": 0,
            },
            "optimizer": {
                "algorithm": "adam",
                "beta1": 0.9,
                "beta2": 0.999,
                "category_balanced": True,
                "deterministic_order": True,
                "epochs": 10,
                "epsilon": 1e-8,
                "learning_rate": 1e-3,
                "weight_decay": 0.0,
            },
        },
    }


def test_valid_registration_is_accepted_without_mutating_input():
    registration = valid_registration()
    before = copy.deepcopy(registration)

    validated = validate_warm_start_registration(registration)

    assert validated == before
    assert registration == before
    assert validated is not registration


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value.update(schema_version="wrong"),
            "schema_version mismatch",
        ),
        (
            lambda value: value["study"]["cohorts"].update(
                train_seeds=[4000, 4000]
            ),
            "study.cohorts.train_seeds must be unique",
        ),
        (
            lambda value: value["study"]["cohorts"].update(
                validation_seeds=[3000]
            ),
            "overlap excluded prior seeds",
        ),
        (
            lambda value: value["study"]["cohorts"].update(
                validation_seeds=[4001]
            ),
            "study cohorts must be mutually disjoint",
        ),
        (
            lambda value: value["study"]["model"].update(
                architecture="candidate-ranker-linear-v1"
            ),
            "study.model.architecture",
        ),
        (
            lambda value: value["study"]["optimizer"].update(
                category_balanced=False
            ),
            "study.optimizer.category_balanced",
        ),
        (
            lambda value: value["study"]["evaluation"]["thresholds"].update(
                minimum_overall_action_agreement=1.1
            ),
            "minimum_overall_action_agreement",
        ),
        (
            lambda value: value["study"]["limits"].update(
                max_total_policy_episodes=5
            ),
            "max_total_policy_episodes is insufficient",
        ),
        (
            lambda value: value["study"]["execution"].update(
                model_config_count=2
            ),
            "study.execution.model_config_count",
        ),
        (
            lambda value: value["identity"]["prior_evidence"].pop(
                "policy_validity_manifest"
            ),
            "identity.prior_evidence keys mismatch",
        ),
    ],
)
def test_invalid_registration_fails_closed(mutate, message):
    registration = valid_registration()
    mutate(registration)

    with pytest.raises(WarmStartBlocked, match=message):
        validate_warm_start_registration(registration)


def test_registration_loader_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"schema_version":"one","schema_version":"two"}', encoding="utf-8"
    )

    with pytest.raises(WarmStartBlocked, match="duplicate JSON key: schema_version"):
        load_warm_start_registration(path)
