from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import torch

from analysis_scripts.noncombat_simulator_baseline_warm_start import (
    DEMONSTRATION_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    INPUT_SCHEMA_VERSION,
    PRIOR_SEEDS,
    REGISTERED_SOURCE_FILES,
    WarmStartBlocked,
    build_warm_start_model,
    canonical_warm_start_model_payload,
    classify_warm_start_results,
    collect_native_demonstrations,
    evaluate_teacher_fit,
    evaluate_warm_start_rollouts,
    load_warm_start_registration,
    load_warm_start_model,
    predict_warm_start_action,
    train_warm_start_ranker,
    validate_warm_start_registration,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    build_transition,
    canonical_json_bytes,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FAKE_PROVENANCE = {
    "adapter_commit": "1" * 40,
    "adapter_source_sha256": "2" * 64,
    "build": {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_policy_id": "test-baseline-v1",
        "compiler": "test-compiler",
        "cpp_standard": 201703,
        "native_target_policy_id": NATIVE_TARGET_POLICY_ID,
        "python": "3.10.18",
    },
    "module_sha256": "3" * 64,
    "module_size_bytes": 123,
    "simulator_commit": "4" * 40,
    "simulator_dirty": False,
    "simulator_source_file_count": 79,
    "simulator_source_sha256": "5" * 64,
    "submodules": {"json": "6" * 40, "pybind11": "7" * 40},
}


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
            lambda value: value["study"]["model"].update(model_seed=False),
            "study.model.model_seed",
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


class FakeDemonstrationEnvironment:
    def __init__(self, seed: int):
        self.seed = seed
        self.terminal = False
        self.selected: str | None = None
        self.query_mutation = False

    @property
    def category(self) -> str:
        return ("card_reward", "event", "route", "shop")[self.seed % 4]

    def snapshot(self) -> dict[str, object]:
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test-baseline-v1"},
            "category": None if self.terminal else self.category,
            "decision_count": int(self.terminal),
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "cur_hp": 80,
                "floor": 9 if self.terminal else 0,
                "gold": 99,
                "outcome": "player_loss" if self.terminal else "undecided",
                "query_mutation": self.query_mutation,
                "seed": str(self.seed),
            },
            "terminal": self.terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.terminal:
            return []
        return [
            {
                "action_id": "skip",
                "available": True,
                "category": self.category,
                "kind": "choose",
                "label": "skip",
                "raw": {"quality": 0},
            },
            {
                "action_id": "take",
                "available": True,
                "category": self.category,
                "kind": "choose",
                "label": "take",
                "raw": {"quality": 1},
            },
        ]

    def clone(self) -> "FakeDemonstrationEnvironment":
        return copy.deepcopy(self)

    def native_baseline_action(self) -> dict[str, str]:
        return {
            "action_id": "take",
            "category": self.category,
            "policy_id": NATIVE_TARGET_POLICY_ID,
            "schema_version": NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
        }

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        if action_id not in {candidate["action_id"] for candidate in candidates}:
            raise ValueError("illegal action")
        self.selected = action_id
        self.terminal = True
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=FAKE_PROVENANCE,
        )

    def step_native_baseline(self) -> dict[str, object]:
        return self.step("take")


def _demo_factory(seed: int) -> FakeDemonstrationEnvironment:
    return FakeDemonstrationEnvironment(seed)


def _collect_demo(**overrides):
    values = {
        "clock": lambda: 0.0,
        "cohort": "train",
        "deadline": 30.0,
        "environment_factory": _demo_factory,
        "max_decisions_per_episode": 4,
        "max_demo_rows": 20,
        "max_episodes": 4,
        "required_categories": ("card_reward", "event", "route", "shop"),
        "seeds": (4000, 4001, 4002, 4003),
    }
    values.update(overrides)
    return collect_native_demonstrations(**values)


def test_native_demonstration_dataset_is_complete_and_deterministic():
    first = _collect_demo()
    second = _collect_demo()

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first["schema_version"] == DATASET_SCHEMA_VERSION
    assert first["cohort"] == "train"
    assert first["seeds"] == [4000, 4001, 4002, 4003]
    assert first["row_count"] == 4
    assert first["all_categories"] == ["card_reward", "event", "route", "shop"]
    assert [episode["seed"] for episode in first["episodes"]] == first["seeds"]
    for row in first["rows"]:
        assert row["schema_version"] == DEMONSTRATION_SCHEMA_VERSION
        assert row["source_type"] == SOURCE_TYPE
        assert row["teacher"]["action_id"] == "take"
        assert row["teacher"]["policy_id"] == NATIVE_TARGET_POLICY_ID
        assert [item["action_id"] for item in row["candidate_actions"]] == [
            "skip",
            "take",
        ]
        assert [item["action_id"] for item in row["policy_views"]] == [
            "skip",
            "take",
        ]
        assert all(len(item["sha256"]) == 64 for item in row["policy_views"])
        assert row["successor"]["terminal"] is True
        assert row["successor"]["state"]["outcome"] == "player_loss"


def test_native_demonstration_query_mutation_fails_closed():
    class MutatingEnvironment(FakeDemonstrationEnvironment):
        def native_baseline_action(self) -> dict[str, str]:
            self.query_mutation = True
            return super().native_baseline_action()

    with pytest.raises(WarmStartBlocked, match="native target query mutated source"):
        _collect_demo(
            environment_factory=MutatingEnvironment,
            required_categories=("card_reward",),
            seeds=(4000,),
            max_episodes=1,
        )


def test_native_demonstration_unmapped_target_fails_closed():
    class UnmappedEnvironment(FakeDemonstrationEnvironment):
        def native_baseline_action(self) -> dict[str, str]:
            value = super().native_baseline_action()
            value["action_id"] = "missing"
            return value

    with pytest.raises(WarmStartBlocked, match="maps to 0 current candidates"):
        _collect_demo(
            environment_factory=UnmappedEnvironment,
            required_categories=("card_reward",),
            seeds=(4000,),
            max_episodes=1,
        )


def test_native_demonstration_row_limit_fails_closed():
    with pytest.raises(WarmStartBlocked, match="max_demo_rows"):
        _collect_demo(max_demo_rows=3)


def test_warm_start_training_is_deterministic_and_preserves_all_candidates():
    dataset = _collect_demo()
    first = train_warm_start_ranker(
        dataset,
        hash_dim=64,
        hidden_dim=16,
        model_seed=0,
        epochs=20,
        learning_rate=0.02,
        betas=(0.9, 0.999),
        epsilon=1e-8,
        weight_decay=0.0,
    )
    second = train_warm_start_ranker(
        dataset,
        hash_dim=64,
        hidden_dim=16,
        model_seed=0,
        epochs=20,
        learning_rate=0.02,
        betas=(0.9, 0.999),
        epsilon=1e-8,
        weight_decay=0.0,
    )

    assert first.initial_model == second.initial_model
    assert first.final_model == second.final_model
    assert first.history == second.history
    assert first.initial_model != first.final_model
    assert all(not parameter.requires_grad for parameter in first.model.parameters())
    assert all(parameter.grad is None for parameter in first.model.parameters())
    for row in dataset["rows"]:
        prediction = predict_warm_start_action(
            first.model,
            snapshot=row["source_snapshot"],
            candidates=row["candidate_actions"],
            hash_dim=64,
        )
        assert prediction["candidate_action_ids"] == ["skip", "take"]
        assert len(prediction["probabilities"]) == 2
        assert prediction["selected_action_id"] == "take"


def test_warm_start_loss_is_category_balanced():
    result = train_warm_start_ranker(
        _collect_demo(),
        hash_dim=64,
        hidden_dim=16,
        model_seed=0,
        epochs=1,
        learning_rate=0.01,
        betas=(0.9, 0.999),
        epsilon=1e-8,
        weight_decay=0.0,
    )

    epoch = result.history[0]
    assert sorted(epoch["category_losses"]) == [
        "card_reward",
        "event",
        "route",
        "shop",
    ]
    assert epoch["loss"] == pytest.approx(
        sum(epoch["category_losses"].values()) / 4.0
    )
    assert epoch["category_row_counts"] == {
        "card_reward": 1,
        "event": 1,
        "route": 1,
        "shop": 1,
    }


def test_warm_start_model_canonical_round_trip_is_frozen():
    model = build_warm_start_model(hash_dim=32, hidden_dim=8, model_seed=0)
    payload = canonical_warm_start_model_payload(model)
    loaded = load_warm_start_model(
        payload, expected_hash_dim=32, expected_hidden_dim=8
    )

    assert canonical_warm_start_model_payload(loaded) == payload
    assert all(not parameter.requires_grad for parameter in loaded.parameters())
    assert loaded.training is False

    invalid = copy.deepcopy(payload)
    invalid["state_dict"]["hidden.weight"]["values"][0] = "nan"
    with pytest.raises(WarmStartBlocked, match="values must be finite"):
        load_warm_start_model(
            invalid, expected_hash_dim=32, expected_hidden_dim=8
        )


def test_warm_start_training_rejects_tampered_policy_view_hash():
    dataset = _collect_demo()
    dataset["rows"][0]["policy_views"][0]["sha256"] = "0" * 64

    with pytest.raises(WarmStartBlocked, match="policy view hash mismatch"):
        train_warm_start_ranker(
            dataset,
            hash_dim=64,
            hidden_dim=16,
            model_seed=0,
            epochs=1,
            learning_rate=0.01,
            betas=(0.9, 0.999),
            epsilon=1e-8,
            weight_decay=0.0,
        )


def test_warm_start_prediction_rejects_nonfinite_model():
    model = build_warm_start_model(hash_dim=32, hidden_dim=8, model_seed=0)
    with torch.no_grad():
        next(model.parameters()).fill_(float("nan"))
    row = _collect_demo()["rows"][0]

    with pytest.raises(WarmStartBlocked, match="non-finite model tensor"):
        predict_warm_start_action(
            model,
            snapshot=row["source_snapshot"],
            candidates=row["candidate_actions"],
            hash_dim=32,
        )


def _trained_demo_model():
    return train_warm_start_ranker(
        _collect_demo(),
        hash_dim=64,
        hidden_dim=16,
        model_seed=0,
        epochs=20,
        learning_rate=0.02,
        betas=(0.9, 0.999),
        epsilon=1e-8,
        weight_decay=0.0,
    ).model


def test_teacher_fit_and_paired_rollout_metrics_are_deterministic():
    model = _trained_demo_model()
    dataset = _collect_demo(cohort="validation")

    teacher_fit = evaluate_teacher_fit(model, dataset=dataset, hash_dim=64)
    first = evaluate_warm_start_rollouts(
        model,
        environment_factory=_demo_factory,
        seeds=(4000, 4001, 4002, 4003),
        hash_dim=64,
        max_decisions_per_episode=4,
        max_episodes=8,
        max_wall_seconds=30.0,
        bootstrap_seed=0,
        bootstrap_resamples=200,
        confidence_level=0.95,
        clock=lambda: 0.0,
    )
    second = evaluate_warm_start_rollouts(
        model,
        environment_factory=_demo_factory,
        seeds=(4000, 4001, 4002, 4003),
        hash_dim=64,
        max_decisions_per_episode=4,
        max_episodes=8,
        max_wall_seconds=30.0,
        bootstrap_seed=0,
        bootstrap_resamples=200,
        confidence_level=0.95,
        clock=lambda: 0.0,
    )

    assert teacher_fit["overall_action_agreement"] == 1.0
    assert teacher_fit["macro_category_action_agreement"] == 1.0
    assert all(
        category["action_agreement"] == 1.0
        for category in teacher_fit["by_category"].values()
    )
    assert first == second
    assert set(first["checks"].values()) == {True}
    assert first["comparison"]["floor_difference_ci"] == {
        "confidence_level": 0.95,
        "lower": 0.0,
        "mean": 0.0,
        "resamples": 200,
        "upper": 0.0,
    }
    assert first["victories"] == {
        "candidate": 0,
        "native_simple_agent": 0,
    }


def _teacher_fit_metrics(agreement: float) -> dict[str, object]:
    return {
        "by_category": {
            category: {"action_agreement": agreement, "row_count": 1}
            for category in ("card_reward", "event", "route", "shop")
        },
        "checks": {
            "candidate_legality": True,
            "four_category_coverage": True,
            "finite_metrics": True,
        },
        "macro_category_action_agreement": agreement,
        "overall_action_agreement": agreement,
    }


def _rollout_metrics(*, lower: float, mean: float) -> dict[str, object]:
    return {
        "checks": {
            "candidate_legality": True,
            "episode_count": True,
            "finite_metrics": True,
            "four_category_coverage": True,
            "model_immutability": True,
            "no_gradients": True,
            "terminal_outcomes": True,
            "within_bounds": True,
        },
        "comparison": {
            "floor_difference_ci": {
                "confidence_level": 0.95,
                "lower": lower,
                "mean": mean,
                "resamples": 1000,
                "upper": mean + 1.0,
            }
        },
    }


def _classification_input(
    *, validation_agreement: float = 0.9, final_lower: float | None = -1.0
) -> dict[str, object]:
    validation = {
        "rollouts": _rollout_metrics(lower=-1.0, mean=-0.5),
        "teacher_fit": _teacher_fit_metrics(validation_agreement),
    }
    final_test = None
    if final_lower is not None:
        final_test = {
            "rollouts": _rollout_metrics(lower=final_lower, mean=-0.5),
            "teacher_fit": _teacher_fit_metrics(0.9),
        }
    return {
        "final_test": final_test,
        "structural_checks": {"identity": True, "model_frozen": True},
        "validation": validation,
    }


def _classification_thresholds() -> dict[str, float]:
    return copy.deepcopy(
        valid_registration()["study"]["evaluation"]["thresholds"]
    )


def test_warm_start_classification_positive_negative_blocked_and_untouched():
    thresholds = _classification_thresholds()
    positive = _classification_input(final_lower=-1.0)
    result = classify_warm_start_results(positive, copy.deepcopy(positive), thresholds)
    assert result["verdict"] == "study_valid_with_baseline_floor"
    assert result["quality"] == "baseline_floor_demonstrated"
    assert result["blockers"] == []
    assert set(result["authority"].values()) == {False}

    negative = _classification_input(final_lower=-4.0)
    result = classify_warm_start_results(negative, copy.deepcopy(negative), thresholds)
    assert result["verdict"] == "study_valid_without_baseline_floor"
    assert result["quality"] == "baseline_floor_not_demonstrated"
    assert result["blockers"] == []

    untouched = _classification_input(validation_agreement=0.5, final_lower=None)
    result = classify_warm_start_results(untouched, copy.deepcopy(untouched), thresholds)
    assert result["verdict"] == "study_valid_without_baseline_floor"
    assert result["final_test_untouched"] is True
    assert result["checks"]["final_test_access_contract"] is True
    assert result["validation_gate"]["passed"] is False

    violated_stop = _classification_input(validation_agreement=0.5, final_lower=-1.0)
    result = classify_warm_start_results(
        violated_stop, copy.deepcopy(violated_stop), thresholds
    )
    assert result["verdict"] == "blocked"
    assert "validation_stop_gate" in result["blockers"]

    blocked = _classification_input(final_lower=-1.0)
    blocked["structural_checks"]["identity"] = False
    result = classify_warm_start_results(blocked, copy.deepcopy(blocked), thresholds)
    assert result["verdict"] == "blocked"
    assert "identity" in result["blockers"]

    replay_changed = _classification_input(final_lower=-1.0)
    replay = copy.deepcopy(replay_changed)
    replay["final_test"]["rollouts"]["comparison"]["floor_difference_ci"][
        "mean"
    ] = 99.0
    result = classify_warm_start_results(replay_changed, replay, thresholds)
    assert result["verdict"] == "blocked"
    assert "replay_identity" in result["blockers"]
