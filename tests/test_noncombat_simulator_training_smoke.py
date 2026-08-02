from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import torch

from analysis_scripts.noncombat_policy_model import (
    CandidateRanker,
    FeatureConfig,
    candidate_feature_vector,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    build_transition,
    canonical_json_bytes,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    ALGORITHM_VERSION,
    FEATURE_VERSION,
    INPUT_SCHEMA_VERSION,
    REWARD_VERSION,
    SmokeBlocked,
    _candidate_features,
    build_blocked_execution_journal,
    build_canonical_artifacts,
    build_execution_journal,
    canonical_model_payload,
    classify_smoke_results,
    evaluate_greedy_policy,
    load_smoke_registration,
    paired_bootstrap_interval,
    project_policy_view,
    publish_canonical_artifacts,
    run_policy_gradient_execution,
    run_registered_smoke,
    simulator_training_reward,
    validate_artifact_directory,
    validate_bound_fit_evidence,
    validate_smoke_registration,
)


FAKE_PROVENANCE = {
    "adapter_commit": "1" * 40,
    "adapter_source_sha256": "2" * 64,
    "build": {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_policy_id": "test-baseline-v1",
        "compiler": "test-compiler",
        "cpp_standard": 201703,
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
REPO_ROOT = Path(__file__).resolve().parents[1]


def _binding(path: str, token: str) -> dict[str, object]:
    return {"path": path, "sha256": token * 64, "size_bytes": 123}


def _registration() -> dict[str, object]:
    return {
        "identity": {
            "adapter_fit_input": _binding(
                "reports/noncombat_simulator_fit_20260802_input.json", "8"
            ),
            "adapter_fit_report": _binding(
                "reports/noncombat_simulator_fit_20260802.json", "9"
            ),
            "adapter_provenance": copy.deepcopy(FAKE_PROVENANCE),
            "implementation": {
                "commit": "a" * 40,
                "source_files": [
                    "analysis_scripts/noncombat_policy_model.py",
                    "analysis_scripts/noncombat_simulator_adapter.py",
                    "analysis_scripts/noncombat_simulator_training_smoke.py",
                ],
                "source_sha256": "b" * 64,
            },
        },
        "schema_version": INPUT_SCHEMA_VERSION,
        "smoke": {
            "algorithm": {
                "discount": 1.0,
                "feature_version": FEATURE_VERSION,
                "hash_dim": 1024,
                "learning_rate": 0.001,
                "model_seed": 0,
                "optimizer": "adam",
                "passes": 4,
                "standardize_returns": True,
                "version": ALGORITHM_VERSION,
            },
            "ascension": 0,
            "cohorts": {
                "holdout_seeds": list(range(2000, 2064)),
                "train_seeds": list(range(1000, 1032)),
            },
            "evaluation": {
                "bootstrap_resamples": 10_000,
                "bootstrap_seed": 0,
                "confidence_level": 0.95,
                "policy": "greedy",
            },
            "execution": {
                "allow_parameter_retry": False,
                "primary_count": 1,
                "replay_count": 1,
            },
            "limits": {
                "max_decisions_per_episode": 500,
                "max_train_episodes": 128,
                "max_wall_seconds_per_execution": 600.0,
            },
            "reward": {
                "max_floor": 57,
                "progress_divisor": 57.0,
                "victory_bonus": 1.0,
                "version": REWARD_VERSION,
            },
        },
    }


class FakeEnvironment:
    def __init__(self, seed: int, *, terminal: bool = False, selected: str | None = None):
        self.seed = seed
        self._terminal = terminal
        self.selected = selected

    @property
    def category(self) -> str:
        return ("card_reward", "event", "route", "shop")[self.seed % 4]

    def snapshot(self) -> dict[str, object]:
        floor = 0
        outcome = "undecided"
        if self._terminal:
            floor = 12 if self.selected == "good" else 2
            outcome = "player_loss"
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test-baseline-v1"},
            "category": None if self._terminal else self.category,
            "decision_count": 1 if self._terminal else 0,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "cur_hp": 80,
                "floor": floor,
                "gold": 99,
                "outcome": outcome,
                "seed": str(self.seed),
            },
            "terminal": self._terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self._terminal:
            return []
        return [
            {
                "action_id": "bad",
                "available": True,
                "category": self.category,
                "kind": "choose",
                "label": "bad",
                "raw": {"quality": 0},
            },
            {
                "action_id": "good",
                "available": True,
                "category": self.category,
                "kind": "choose",
                "label": "good",
                "raw": {"quality": 1},
            },
        ]

    def clone(self) -> "FakeEnvironment":
        return copy.deepcopy(self)

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        if action_id not in {candidate["action_id"] for candidate in candidates}:
            raise ValueError("illegal action")
        self.selected = action_id
        self._terminal = True
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=FAKE_PROVENANCE,
        )


def _factory(seed: int) -> FakeEnvironment:
    return FakeEnvironment(seed)


def _small_execution(**overrides):
    values = {
        "ascension": 0,
        "bootstrap_resamples": 200,
        "bootstrap_seed": 0,
        "confidence_level": 0.95,
        "discount": 1.0,
        "hash_dim": 64,
        "holdout_seeds": tuple(range(20, 28)),
        "learning_rate": 0.01,
        "max_decisions_per_episode": 4,
        "max_train_episodes": 16,
        "max_wall_seconds": 30.0,
        "model_seed": 0,
        "passes": 2,
        "train_seeds": tuple(range(8)),
    }
    values.update(overrides)
    return run_policy_gradient_execution(environment_factory=_factory, **values)


def test_registration_accepts_only_the_predeclared_contract():
    validated = validate_smoke_registration(_registration())

    assert validated["schema_version"] == INPUT_SCHEMA_VERSION
    assert validated["smoke"]["cohorts"]["train_seeds"] == list(range(1000, 1032))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["smoke"]["cohorts"]["holdout_seeds"].__setitem__(
                0, 1000
            ),
            "disjoint",
        ),
        (
            lambda value: value["smoke"]["cohorts"]["train_seeds"].append(1000),
            "train_seeds",
        ),
        (
            lambda value: value["smoke"]["algorithm"].__setitem__("passes", 9),
            "passes",
        ),
        (
            lambda value: value["smoke"]["reward"].__setitem__("victory_bonus", 2.0),
            "victory_bonus",
        ),
        (
            lambda value: value["smoke"]["limits"].__setitem__(
                "max_wall_seconds_per_execution", 901.0
            ),
            "max_wall_seconds_per_execution",
        ),
        (
            lambda value: value["smoke"]["execution"].__setitem__(
                "allow_parameter_retry", True
            ),
            "allow_parameter_retry",
        ),
    ],
)
def test_registration_rejects_cohort_config_reward_and_bound_drift(mutate, message):
    registration = _registration()
    mutate(registration)

    with pytest.raises(SmokeBlocked, match=message):
        validate_smoke_registration(registration)


def test_runtime_identity_drift_blocks_before_environment_construction():
    registration = _registration()
    actual_identity = copy.deepcopy(registration["identity"])
    actual_identity["adapter_provenance"]["module_sha256"] = "f" * 64
    calls = 0

    def forbidden_factory(seed: int):
        nonlocal calls
        calls += 1
        return FakeEnvironment(seed)

    with pytest.raises(SmokeBlocked, match="module_sha256"):
        run_registered_smoke(
            registration,
            actual_identity=actual_identity,
            environment_factory=forbidden_factory,
        )

    assert calls == 0


def test_bound_fit_evidence_must_be_ready_and_match_registered_provenance():
    fit_input = {
        "schema_version": "noncombat-simulator-fit-input-v1",
        "registered_provenance": copy.deepcopy(FAKE_PROVENANCE),
    }
    fit_report = {
        "authority": {"simulator_training_smoke": False},
        "blockers": [],
        "checks": {"provenance_identity": True},
        "provenance": copy.deepcopy(FAKE_PROVENANCE),
        "provenance_mismatches": [],
        "report_schema_version": "noncombat-simulator-fit-report-v1",
        "verdict": "adapter_poc_ready",
    }

    validate_bound_fit_evidence(fit_input, fit_report, FAKE_PROVENANCE)

    blocked = copy.deepcopy(fit_report)
    blocked["verdict"] = "blocked"
    with pytest.raises(SmokeBlocked, match="adapter_poc_ready"):
        validate_bound_fit_evidence(fit_input, blocked, FAKE_PROVENANCE)

    drifted = copy.deepcopy(fit_report)
    drifted["provenance"]["module_sha256"] = "f" * 64
    with pytest.raises(SmokeBlocked, match="fit report provenance"):
        validate_bound_fit_evidence(fit_input, drifted, FAKE_PROVENANCE)


def test_registered_smoke_input_binds_the_ready_r2_fit_evidence():
    registration_path = (
        REPO_ROOT / "reports" / "noncombat_simulator_training_smoke_20260802_input.json"
    )
    registration = load_smoke_registration(registration_path)
    identity = registration["identity"]

    bound_values = {}
    for name in ("adapter_fit_input", "adapter_fit_report"):
        binding = identity[name]
        path = REPO_ROOT / binding["path"]
        data = path.read_bytes()
        assert len(data) == binding["size_bytes"]
        assert hashlib.sha256(data).hexdigest() == binding["sha256"]
        bound_values[name] = json.loads(data)

    validate_bound_fit_evidence(
        bound_values["adapter_fit_input"],
        bound_values["adapter_fit_report"],
        identity["adapter_provenance"],
    )
    assert registration["smoke"]["cohorts"]["train_seeds"] == list(
        range(1000, 1032)
    )
    assert registration["smoke"]["cohorts"]["holdout_seeds"] == list(
        range(2000, 2064)
    )


def test_policy_projection_removes_leakage_and_retains_decision_features():
    state = {
        "cur_hp": 70,
        "nested": {"outcome": "player_victory", "room": "shop", "seed": "99"},
        "outcome": "undecided",
        "provenance": {"hash": "secret"},
        "seed": "42",
    }
    candidate = {
        "action_id": "buy:card:0",
        "baseline_control": {"history": ["combat"]},
        "label": "Inflame",
        "raw": {"price": 50},
        "terminal": False,
    }

    projected = project_policy_view(state, candidate)
    changed_leakage = project_policy_view(
        {**state, "seed": "different", "outcome": "player_loss"}, candidate
    )

    assert projected == changed_leakage
    assert projected["state"]["cur_hp"] == 70
    assert projected["candidate"]["raw"]["price"] == 50
    assert b"seed" not in canonical_json_bytes(projected)
    assert b"outcome" not in canonical_json_bytes(projected)
    assert b"provenance" not in canonical_json_bytes(projected)
    assert b"baseline_control" not in canonical_json_bytes(projected)
    assert b"terminal" not in canonical_json_bytes(projected)


def test_state_once_candidate_features_match_the_original_additive_encoder():
    state = {"cur_hp": 70, "deck": [{"id": "Strike_R"}], "seed": "ignored"}
    candidates = [
        {"action_id": "skip", "raw": {"slot": 0}},
        {"action_id": "take:Inflame", "raw": {"slot": 1}},
    ]
    projected = [project_policy_view(state, candidate) for candidate in candidates]
    row = type("Row", (), {"state": projected[0]["state"]})()
    config = FeatureConfig(version=FEATURE_VERSION, hash_dim=64)
    original = torch.stack(
        [candidate_feature_vector(row, item["candidate"], config) for item in projected]
    )

    optimized = _candidate_features(state, candidates, hash_dim=64)

    assert torch.equal(optimized, original)


def test_training_reward_uses_only_floor_progress_and_terminal_victory():
    transition = {
        "bottled_label": "ignored",
        "source_state": {"cur_hp": 1, "floor": 10, "gold": 0},
        "successor": {
            "state": {
                "cur_hp": 999,
                "floor": 12,
                "gold": 9999,
                "outcome": "player_victory",
            },
            "terminal": True,
        },
    }

    assert simulator_training_reward(transition) == pytest.approx(1.0 + 2.0 / 57.0)

    noisy = copy.deepcopy(transition)
    noisy["source_state"].update({"cur_hp": 80, "gold": 500})
    noisy["successor"]["state"].update({"cur_hp": 1, "gold": 0})
    noisy["bottled_label"] = "different"
    assert simulator_training_reward(noisy) == simulator_training_reward(transition)


def test_reward_does_not_pay_for_floor_regression_or_nonterminal_outcome():
    transition = {
        "source_state": {"floor": 10},
        "successor": {
            "state": {"floor": 8, "outcome": "player_victory"},
            "terminal": False,
        },
    }

    assert simulator_training_reward(transition) == 0.0


def test_policy_gradient_execution_is_exactly_reproducible_and_candidate_legal():
    first = _small_execution()
    second = _small_execution()

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first["checks"]["candidate_legality"] is True
    assert first["checks"]["four_category_coverage"] is True
    assert first["checks"]["terminal_outcomes"] is True
    assert len(first["training"]["passes"]) == 2
    assert len(first["holdout"]["paired_rows"]) == 8
    paired = first["holdout"]["paired_rows"][0]
    assert paired["initial_decisions"] == 1
    assert paired["final_decisions"] == 1
    assert paired["decision_difference"] == 0
    assert paired["initial_categories"] == paired["final_categories"]
    assert paired["candidate_legality"] is True


def test_greedy_holdout_evaluation_does_not_update_model():
    torch.manual_seed(0)
    model = CandidateRanker(input_dim=64)
    before = canonical_model_payload(model)

    evaluation = evaluate_greedy_policy(
        model,
        environment_factory=_factory,
        seeds=tuple(range(20, 28)),
        hash_dim=64,
        max_decisions_per_episode=4,
        deadline=10_000.0,
        clock=lambda: 0.0,
    )

    assert canonical_model_payload(model) == before
    assert evaluation["all_categories"] == ["card_reward", "event", "route", "shop"]


def test_duplicate_candidates_fail_without_a_fallback():
    class DuplicateEnvironment(FakeEnvironment):
        def legal_actions(self):
            candidates = super().legal_actions()
            candidates[1]["action_id"] = candidates[0]["action_id"]
            return candidates

    with pytest.raises(SmokeBlocked, match="duplicate"):
        run_policy_gradient_execution(
            environment_factory=DuplicateEnvironment,
            train_seeds=(0, 1, 2, 3),
            holdout_seeds=(20, 21, 22, 23),
            passes=1,
            model_seed=0,
            hash_dim=64,
            learning_rate=0.01,
            discount=1.0,
            max_decisions_per_episode=4,
            max_train_episodes=4,
            max_wall_seconds=30.0,
            bootstrap_seed=0,
            bootstrap_resamples=100,
            confidence_level=0.95,
        )


def test_wall_bound_stops_the_smoke():
    class StepClock:
        def __init__(self):
            self.value = -1.0

        def __call__(self):
            self.value += 1.0
            return self.value

    with pytest.raises(SmokeBlocked, match="wall"):
        run_policy_gradient_execution(
            environment_factory=_factory,
            train_seeds=(0, 1, 2, 3),
            holdout_seeds=(20, 21, 22, 23),
            passes=1,
            model_seed=0,
            hash_dim=64,
            learning_rate=0.01,
            discount=1.0,
            max_decisions_per_episode=4,
            max_train_episodes=4,
            max_wall_seconds=0.5,
            bootstrap_seed=0,
            bootstrap_resamples=100,
            confidence_level=0.95,
            clock=StepClock(),
        )


def test_paired_bootstrap_is_deterministic_and_signal_requires_positive_lower_bound():
    first = paired_bootstrap_interval(
        [2.0, 2.0, 3.0, 1.0], seed=0, resamples=500, confidence_level=0.95
    )
    second = paired_bootstrap_interval(
        [2.0, 2.0, 3.0, 1.0], seed=0, resamples=500, confidence_level=0.95
    )

    assert first == second
    assert first["lower"] > 0.0

    inconclusive = paired_bootstrap_interval(
        [-1.0, 0.0, 1.0, 1.0], seed=0, resamples=500, confidence_level=0.95
    )
    assert inconclusive["mean"] > 0.0
    assert inconclusive["lower"] <= 0.0


def test_classification_separates_structural_and_quality_verdicts():
    primary = _small_execution()

    positive = copy.deepcopy(primary)
    positive["holdout"]["floor_improvement_ci"] = {
        "confidence_level": 0.95,
        "lower": 0.1,
        "mean": 1.0,
        "resamples": 200,
        "upper": 2.0,
    }
    signal = classify_smoke_results(positive, copy.deepcopy(positive))
    assert signal["verdict"] == "pipeline_demonstrated_with_holdout_signal"

    inconclusive = copy.deepcopy(primary)
    inconclusive["holdout"]["floor_improvement_ci"] = {
        "confidence_level": 0.95,
        "lower": 0.0,
        "mean": 0.25,
        "resamples": 200,
        "upper": 1.0,
    }
    no_signal = classify_smoke_results(inconclusive, copy.deepcopy(inconclusive))
    assert no_signal["verdict"] == "pipeline_demonstrated_quality_not_demonstrated"

    replay_drift = copy.deepcopy(primary)
    replay_drift["model"]["state_dict"]["scorer.bias"]["values"][0] = "0x1p+0"
    blocked = classify_smoke_results(primary, replay_drift)
    assert blocked["verdict"] == "blocked"
    assert "replay_identity" in blocked["blockers"]
    assert "model.state_dict.scorer.bias.values[0]" in blocked["replay_difference"]

    assert all(value is False for value in signal["authority"].values())


def test_canonical_artifacts_exclude_timing_and_close_the_hash_manifest(tmp_path):
    execution = _small_execution()
    classification = classify_smoke_results(execution, copy.deepcopy(execution))
    artifacts = build_canonical_artifacts(
        registration=_registration(),
        primary=execution,
        replay=copy.deepcopy(execution),
        classification=classification,
    )

    assert "execution_journal.json" not in artifacts
    assert all(b"elapsed" not in payload for payload in artifacts.values())

    registration_sha256 = hashlib.sha256(
        canonical_json_bytes(validate_smoke_registration(_registration()))
    ).hexdigest()
    for name in (
        "artifact_manifest.json",
        "metrics.json",
        "model.json",
        "trajectories.json",
    ):
        assert json.loads(artifacts[name])["registration_sha256"] == registration_sha256
    assert registration_sha256.encode("ascii") in artifacts["report.md"]

    publish_canonical_artifacts(tmp_path, artifacts)
    validated = validate_artifact_directory(tmp_path)

    assert validated["schema_version"].startswith("noncombat-simulator-training-smoke")
    assert set(validated["artifact_hashes"]) == {
        "metrics.json",
        "model.json",
        "report.md",
        "trajectories.json",
    }


def test_canonical_publication_rolls_back_the_complete_prior_set(tmp_path):
    execution = _small_execution()
    classification = classify_smoke_results(execution, copy.deepcopy(execution))
    first = build_canonical_artifacts(
        registration=_registration(),
        primary=execution,
        replay=copy.deepcopy(execution),
        classification=classification,
    )
    publish_canonical_artifacts(tmp_path, first)
    prior = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    changed = dict(first)
    changed["report.md"] = first["report.md"] + b"changed\n"
    changed_manifest = json.loads(changed["artifact_manifest.json"])
    changed_manifest["artifact_hashes"]["report.md"] = hashlib.sha256(
        changed["report.md"]
    ).hexdigest()
    changed["artifact_manifest.json"] = canonical_json_bytes(changed_manifest)
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        os.replace(source, destination)

    with pytest.raises(OSError, match="injected"):
        publish_canonical_artifacts(tmp_path, changed, replace=fail_second_replace)

    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == prior


def test_execution_journal_is_explicitly_noncanonical():
    journal = build_execution_journal(
        primary_elapsed_seconds=1.25,
        replay_elapsed_seconds=1.5,
        wall_time_budget_seconds=900.0,
    )

    assert journal["canonical"] is False
    assert journal["primary_elapsed_seconds"] == 1.25
    assert journal["replay_elapsed_seconds"] == 1.5


def test_blocked_execution_journal_records_the_exact_phase_and_reason():
    journal = build_blocked_execution_journal(
        blocker="wall-time bound exceeded",
        elapsed_seconds=12.5,
        phase="primary",
        wall_time_budget_seconds=600.0,
    )

    assert journal["canonical"] is False
    assert journal["verdict"] == "blocked"
    assert journal["phase"] == "primary"
    assert journal["blocker"] == "wall-time bound exceeded"


def test_native_adapter_runs_a_reproducible_policy_gradient_smoke():
    module_path = os.environ.get("STS_LIGHTSPEED_ADAPTER_MODULE")
    mingw_bin = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    if not module_path or not mingw_bin:
        pytest.skip("set STS_LIGHTSPEED_ADAPTER_MODULE and STS_LIGHTSPEED_MINGW_BIN")
    child = textwrap.dedent(
        f"""
        import json
        from pathlib import Path
        from analysis_scripts.noncombat_simulator_adapter import NativeSimulatorEnvironment, canonical_json_bytes, load_native_module

        module = load_native_module({module_path!r}, dll_directories=[{mingw_bin!r}])
        fit_report = json.loads(Path('reports/noncombat_simulator_fit_20260802_r2.json').read_text(encoding='utf-8'))
        provenance = fit_report['provenance']
        from analysis_scripts.noncombat_simulator_training_smoke import _first_difference, run_policy_gradient_execution

        def factory(seed):
            return NativeSimulatorEnvironment(module.Environment(seed, 0), provenance)

        kwargs = dict(
            ascension=0,
            bootstrap_resamples=100,
            bootstrap_seed=0,
            confidence_level=0.95,
            discount=1.0,
            environment_factory=factory,
            hash_dim=64,
            holdout_seeds=(20, 21, 22, 23),
            learning_rate=0.01,
            max_decisions_per_episode=500,
            max_train_episodes=4,
            max_wall_seconds=30.0,
            model_seed=0,
            passes=1,
            train_seeds=(0, 1, 2, 3),
        )
        first = run_policy_gradient_execution(**kwargs)
        second = run_policy_gradient_execution(**kwargs)
        assert canonical_json_bytes(first) == canonical_json_bytes(second), _first_difference(first, second, 'execution')
        assert all(first['checks'].values())
        print(json.dumps(first['checks'], sort_keys=True))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", child],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["candidate_legality"] is True


def test_live_entrypoint_does_not_import_the_smoke_module():
    live_sources = [REPO_ROOT / "main.py", REPO_ROOT / "scripts" / "run_training_batch.py"]

    for source in live_sources:
        assert "noncombat_simulator_training_smoke" not in source.read_text(encoding="utf-8")
