from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest
import torch

from analysis_scripts.noncombat_policy_model import CandidateRanker
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SimulatorAdapterError,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    build_transition,
    canonical_json_bytes,
    sha256_file,
)
from analysis_scripts.noncombat_simulator_policy_validity import (
    COMPATIBILITY_SEEDS,
    FRESH_SEEDS,
    INPUT_SCHEMA_VERSION,
    POLICY_IDS,
    PolicyValidityBlocked,
    _paired_comparison,
    _validate_bound_smoke_artifacts,
    build_canonical_artifacts,
    build_initial_model,
    canonical_model_sha256,
    classify_policy_validity_results,
    load_frozen_model,
    load_policy_validity_registration,
    publish_canonical_artifacts,
    run_compatibility_gate,
    run_policy_validity_execution,
    run_registered_study,
    validate_artifact_directory,
    validate_policy_validity_registration,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    FEATURE_VERSION,
    _candidate_features,
    canonical_model_payload,
    evaluate_greedy_policy,
    hash_bound_files,
    validate_bound_fit_evidence,
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


def _binding(path: str, token: str) -> dict[str, object]:
    return {"path": path, "sha256": token * 64, "size_bytes": 123}


def _registration() -> dict[str, object]:
    return {
        "identity": {
            "adapter_fit_input": _binding("reports/fit_input.json", "8"),
            "adapter_fit_report": _binding("reports/fit_report.json", "9"),
            "adapter_provenance": copy.deepcopy(FAKE_PROVENANCE),
            "excluded_baselines": {
                "bottled": {
                    "feature_version": "noncombat-policy-features-v1",
                    "model": _binding("reports/pilot/bottled_model.pt", "a"),
                    "reason": "unvalidated_simulator_feature_action_bridge",
                },
                "current": {
                    "feature_version": "noncombat-policy-features-v1",
                    "model": _binding("reports/pilot/current_model.pt", "b"),
                    "reason": "unvalidated_simulator_feature_action_bridge",
                },
            },
            "implementation": {
                "commit": "c" * 40,
                "source_files": [
                    "analysis_scripts/noncombat_policy_model.py",
                    "analysis_scripts/noncombat_simulator_adapter.py",
                    "analysis_scripts/noncombat_simulator_fit.py",
                    "analysis_scripts/noncombat_simulator_policy_validity.py",
                    "analysis_scripts/noncombat_simulator_training_smoke.py",
                ],
                "source_sha256": "d" * 64,
            },
            "runtime": {"python": "3.10.18", "torch": "2.5.1+cu121"},
            "smoke_artifacts": {
                "manifest": _binding("reports/smoke/artifact_manifest.json", "e"),
                "model": _binding("reports/smoke/model.json", "f"),
                "registration": _binding("reports/smoke_input.json", "0"),
                "trajectories": _binding("reports/smoke/trajectories.json", "1"),
            },
        },
        "schema_version": INPUT_SCHEMA_VERSION,
        "study": {
            "ascension": 0,
            "cohorts": {
                "compatibility_seeds": list(COMPATIBILITY_SEEDS),
                "fit_seeds": list(range(20)),
                "fresh_seeds": list(FRESH_SEEDS),
                "smoke_holdout_seeds": list(range(2000, 2064)),
                "smoke_train_seeds": list(range(1000, 1032)),
            },
            "evaluation": {
                "bootstrap_resamples": 10_000,
                "bootstrap_seed": 0,
                "confidence_level": 0.95,
                "primary_comparison": "trained_minus_native_simple_agent",
                "secondary_comparison": "trained_minus_seeded_initial",
            },
            "execution": {
                "allow_alternate_cohort": False,
                "allow_model_update": False,
                "allow_parameter_retry": False,
                "primary_count": 1,
                "replay_count": 1,
            },
            "limits": {
                "max_decisions_per_episode": 500,
                "max_episodes_per_execution": 192,
                "max_wall_seconds_per_execution": 480.0,
            },
            "model": {
                "architecture": "candidate-ranker-linear-v1",
                "feature_version": FEATURE_VERSION,
                "hash_dim": 1024,
                "model_seed": 0,
            },
            "policies": list(POLICY_IDS),
        },
    }


class FakeValidityEnvironment:
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

    def clone(self) -> "FakeValidityEnvironment":
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

    def native_baseline_action(self) -> dict[str, str]:
        return {
            "action_id": "bad",
            "category": self.category,
            "policy_id": NATIVE_TARGET_POLICY_ID,
            "schema_version": NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
        }

    def step_native_baseline(self) -> dict[str, object]:
        return self.step("bad")


def _factory(seed: int) -> FakeValidityEnvironment:
    return FakeValidityEnvironment(seed)


def _rankers(hash_dim: int = 64) -> tuple[CandidateRanker, CandidateRanker]:
    candidates = FakeValidityEnvironment(0).legal_actions()
    state = FakeValidityEnvironment(0).snapshot()["state"]
    features = _candidate_features(state, candidates, hash_dim=hash_dim)
    difference = features[1] - features[0]
    assert torch.count_nonzero(difference).item() > 0

    initial = CandidateRanker(input_dim=hash_dim)
    trained = CandidateRanker(input_dim=hash_dim)
    with torch.no_grad():
        initial.scorer.weight.copy_((-difference).unsqueeze(0))
        initial.scorer.bias.zero_()
        trained.scorer.weight.copy_(difference.unsqueeze(0))
        trained.scorer.bias.zero_()
    return initial, trained


def _small_execution():
    initial, trained = _rankers()
    return run_policy_validity_execution(
        environment_factory=_factory,
        fresh_seeds=tuple(range(8)),
        trained_model=trained,
        initial_model=initial,
        hash_dim=64,
        max_decisions_per_episode=4,
        max_episodes=24,
        max_wall_seconds=30.0,
        bootstrap_seed=0,
        bootstrap_resamples=500,
        confidence_level=0.95,
        clock=lambda: 0.0,
    )


def test_registration_accepts_only_the_predeclared_frozen_study():
    validated = validate_policy_validity_registration(_registration())

    assert validated["study"]["cohorts"]["fresh_seeds"] == list(range(3000, 3064))
    assert validated["study"]["policies"] == list(POLICY_IDS)


def test_checked_in_policy_validity_registration_is_hash_closed_and_disjoint():
    path = (
        REPO_ROOT
        / "reports"
        / "noncombat_simulator_policy_validity_20260802_input.json"
    )
    assert path.stat().st_size == 7597
    assert sha256_file(path) == (
        "149a0ed451f52804561de34b213fb4602f6825740705b6c1cf98ab87e0748d10"
    )
    registration = load_policy_validity_registration(path)
    identity = registration["identity"]

    bindings = [identity["adapter_fit_input"], identity["adapter_fit_report"]]
    bindings.extend(identity["smoke_artifacts"].values())
    bindings.extend(
        entry["model"] for entry in identity["excluded_baselines"].values()
    )
    for binding in bindings:
        artifact = REPO_ROOT / binding["path"]
        assert artifact.stat().st_size == binding["size_bytes"]
        assert sha256_file(artifact) == binding["sha256"]

    _validate_bound_smoke_artifacts(REPO_ROOT, identity["smoke_artifacts"])
    fit_input = json.loads(
        (REPO_ROOT / identity["adapter_fit_input"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    fit_report = json.loads(
        (REPO_ROOT / identity["adapter_fit_report"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    validate_bound_fit_evidence(fit_input, fit_report, identity["adapter_provenance"])
    assert hash_bound_files(
        REPO_ROOT, identity["implementation"]["source_files"]
    ) == identity["implementation"]["source_sha256"]

    cohorts = registration["study"]["cohorts"]
    prior = (
        set(cohorts["fit_seeds"])
        | set(cohorts["smoke_train_seeds"])
        | set(cohorts["smoke_holdout_seeds"])
        | set(cohorts["compatibility_seeds"])
    )
    assert set(cohorts["fresh_seeds"]).isdisjoint(prior)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["study"]["cohorts"]["fresh_seeds"].__setitem__(0, 2000),
            "fresh_seeds",
        ),
        (
            lambda value: value["study"]["execution"].__setitem__(
                "allow_model_update", True
            ),
            "allow_model_update",
        ),
        (
            lambda value: value["study"]["evaluation"].__setitem__(
                "primary_comparison", "trained_minus_seeded_initial"
            ),
            "primary_comparison",
        ),
        (
            lambda value: value["identity"]["excluded_baselines"]["current"].__setitem__(
                "reason", "run_directly"
            ),
            "excluded_baselines.current.reason",
        ),
    ],
)
def test_registration_rejects_cohort_training_metric_and_bridge_drift(mutate, message):
    registration = _registration()
    mutate(registration)

    with pytest.raises(PolicyValidityBlocked, match=message):
        validate_policy_validity_registration(registration)


def test_canonical_model_loader_round_trips_and_rejects_nonfinite_values():
    initial = build_initial_model(hash_dim=1024, model_seed=0)
    payload = canonical_model_payload(initial)
    payload["registration_sha256"] = "0" * 64

    loaded = load_frozen_model(payload, expected_hash_dim=1024)

    assert canonical_model_payload(loaded) == canonical_model_payload(initial)
    assert canonical_model_sha256(loaded) == canonical_model_sha256(initial)

    invalid = copy.deepcopy(payload)
    invalid["state_dict"]["scorer.bias"]["values"][0] = "nan"
    with pytest.raises(PolicyValidityBlocked, match="finite"):
        load_frozen_model(invalid, expected_hash_dim=1024)


def test_compatibility_gate_matches_published_policy_inputs_and_actions():
    initial, trained = _rankers()
    seeds = tuple(range(4))
    initial_rows = evaluate_greedy_policy(
        initial,
        environment_factory=_factory,
        seeds=seeds,
        hash_dim=64,
        max_decisions_per_episode=4,
        deadline=30.0,
        clock=lambda: 0.0,
    )
    trained_rows = evaluate_greedy_policy(
        trained,
        environment_factory=_factory,
        seeds=seeds,
        hash_dim=64,
        max_decisions_per_episode=4,
        deadline=30.0,
        clock=lambda: 0.0,
    )
    published = {"holdout": {"final": trained_rows, "initial": initial_rows}}

    result = run_compatibility_gate(
        environment_factory=_factory,
        initial_model=initial,
        trained_model=trained,
        published_trajectories=published,
        seeds=seeds,
        hash_dim=64,
        max_decisions_per_episode=4,
        deadline=30.0,
        clock=lambda: 0.0,
    )

    assert result["matched"] is True
    assert result["quality_rows_included"] == 0

    drifted = copy.deepcopy(published)
    drifted["holdout"]["final"]["rows"][0]["selected_action_ids"] = ["drift"]
    with pytest.raises(PolicyValidityBlocked, match="selected_action_ids"):
        run_compatibility_gate(
            environment_factory=_factory,
            initial_model=initial,
            trained_model=trained,
            published_trajectories=drifted,
            seeds=seeds,
            hash_dim=64,
            max_decisions_per_episode=4,
            deadline=30.0,
            clock=lambda: 0.0,
        )


def test_three_policy_execution_is_deterministic_immutable_and_baseline_relevant():
    first = _small_execution()
    second = _small_execution()

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert set(first["policies"]) == set(POLICY_IDS)
    assert first["checks"] == {
        "candidate_legality": True,
        "episode_count": True,
        "finite_metrics": True,
        "four_category_coverage": True,
        "model_immutability": True,
        "no_gradients": True,
        "terminal_outcomes": True,
        "within_bounds": True,
    }
    assert first["comparisons"]["trained_minus_native_simple_agent"][
        "floor_difference_ci"
    ]["lower"] > 0.0
    assert first["comparisons"]["trained_minus_seeded_initial"][
        "floor_difference_ci"
    ]["lower"] > 0.0
    assert first["victories"] == {
        "native_simple_agent": 0,
        "seeded_initial": 0,
        "smoke_trained": 0,
    }
    assert all(
        row["candidate_legality"] is True
        for policy in first["policies"].values()
        for row in policy["rows"]
    )


def test_adapter_failures_and_incomplete_pairs_block_explicitly():
    initial, trained = _rankers()

    def broken_factory(seed: int):
        raise SimulatorAdapterError(f"broken seed {seed}")

    with pytest.raises(PolicyValidityBlocked, match="compatibility rollout failed"):
        run_compatibility_gate(
            environment_factory=broken_factory,
            initial_model=initial,
            trained_model=trained,
            published_trajectories={
                "holdout": {"final": {"rows": []}, "initial": {"rows": []}}
            },
            seeds=(0,),
            hash_dim=64,
            max_decisions_per_episode=4,
            deadline=30.0,
            clock=lambda: 0.0,
        )

    with pytest.raises(PolicyValidityBlocked, match="missing paired seed 0"):
        _paired_comparison(
            {"rows": [{"outcome": "player_loss", "seed": 0, "terminal_floor": 1.0}]},
            {"rows": []},
            comparison_id="trained_minus_test",
            seeds=(0,),
            bootstrap_seed=0,
            bootstrap_resamples=10,
            confidence_level=0.95,
        )

    with pytest.raises(PolicyValidityBlocked, match="finite"):
        _paired_comparison(
            {
                "rows": [
                    {
                        "outcome": "player_loss",
                        "seed": 0,
                        "terminal_floor": float("nan"),
                    }
                ]
            },
            {
                "rows": [
                    {"outcome": "player_loss", "seed": 0, "terminal_floor": 1.0}
                ]
            },
            comparison_id="trained_minus_test",
            seeds=(0,),
            bootstrap_seed=0,
            bootstrap_resamples=10,
            confidence_level=0.95,
        )


def test_primary_gate_and_secondary_replication_are_classified_separately():
    primary = _small_execution()
    positive = classify_policy_validity_results(primary, copy.deepcopy(primary))
    assert positive["quality"] == "baseline_signal"
    assert positive["verdict"] == "study_valid_with_baseline_signal"
    assert set(positive["authority"].values()) == {False}

    no_primary = copy.deepcopy(primary)
    no_primary["comparisons"]["trained_minus_native_simple_agent"][
        "floor_difference_ci"
    ]["lower"] = 0.0
    no_primary["comparisons"]["trained_minus_seeded_initial"][
        "floor_difference_ci"
    ]["lower"] = 3.0
    negative = classify_policy_validity_results(no_primary, copy.deepcopy(no_primary))
    assert negative["quality"] == "baseline_signal_not_demonstrated"
    assert negative["verdict"] == "study_valid_without_baseline_signal"


def test_replay_difference_blocks_with_first_field_diagnostic():
    primary = _small_execution()
    replay = copy.deepcopy(primary)
    replay["policies"]["smoke_trained"]["rows"][0]["terminal_floor"] += 1.0

    result = classify_policy_validity_results(primary, replay)

    assert result["verdict"] == "blocked"
    assert "replay_identity" in result["blockers"]
    assert "terminal_floor" in result["replay_difference"]


def test_runtime_identity_drift_blocks_before_compatibility_or_fresh_environment():
    registration = _registration()
    actual_identity = copy.deepcopy(registration["identity"])
    actual_identity["adapter_provenance"]["module_sha256"] = "f" * 64
    calls = 0

    def forbidden_factory(seed: int):
        nonlocal calls
        calls += 1
        return FakeValidityEnvironment(seed)

    with pytest.raises(PolicyValidityBlocked, match="module_sha256"):
        run_registered_study(
            registration,
            actual_identity=actual_identity,
            environment_factory=forbidden_factory,
            initial_model=CandidateRanker(1024),
            trained_model=CandidateRanker(1024),
            published_trajectories={"holdout": {"initial": {"rows": []}, "final": {"rows": []}}},
            clock=lambda: 0.0,
        )

    assert calls == 0


def test_canonical_artifacts_are_hash_closed_atomic_and_all_false(tmp_path):
    registration = _registration()
    primary = _small_execution()
    replay = copy.deepcopy(primary)
    classification = classify_policy_validity_results(primary, replay)
    compatibility = {
        "matched": True,
        "quality_rows_included": 0,
        "seeds": [0, 1, 2, 3],
    }
    artifacts = build_canonical_artifacts(
        registration=registration,
        compatibility=compatibility,
        primary=primary,
        replay=replay,
        classification=classification,
    )
    metrics = json.loads(artifacts["metrics.json"])
    assert all(
        summary["categories"] == sorted(("card_reward", "event", "route", "shop"))
        for summary in metrics["policy_summaries"].values()
    )
    assert b"categories card_reward, event, route, shop" in artifacts["report.md"]

    publish_canonical_artifacts(tmp_path, artifacts)
    manifest = validate_artifact_directory(tmp_path)

    assert set(manifest["authority"].values()) == {False}
    assert set(manifest["artifact_hashes"]) == {
        "metrics.json",
        "report.md",
        "trajectories.json",
    }

    manifest_path = tmp_path / "artifact_manifest.json"
    original_manifest = manifest_path.read_bytes()
    incomplete_manifest = json.loads(original_manifest)
    incomplete_manifest["artifact_hashes"].pop("report.md")
    manifest_path.write_bytes(canonical_json_bytes(incomplete_manifest))
    with pytest.raises(PolicyValidityBlocked, match="hash set mismatch"):
        validate_artifact_directory(tmp_path)
    manifest_path.write_bytes(original_manifest)

    unexpected = tmp_path / "unexpected.json"
    unexpected.write_text("{}", encoding="utf-8")
    with pytest.raises(PolicyValidityBlocked, match="inventory mismatch"):
        validate_artifact_directory(tmp_path)
    unexpected.unlink()

    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    calls = 0

    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replacement failure")
        os.replace(source, destination)

    with pytest.raises(OSError, match="injected"):
        publish_canonical_artifacts(tmp_path, artifacts, replace=fail_second)

    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert after == before


def test_policy_validity_module_is_not_imported_by_live_entrypoint():
    main_source = (REPO_ROOT / "main.py").read_text(encoding="utf-8")
    assert "noncombat_simulator_policy_validity" not in main_source

    evaluator_source = (
        REPO_ROOT / "analysis_scripts" / "noncombat_simulator_policy_validity.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("torch.optim", ".backward(", ".glob(", ".rglob("):
        assert forbidden not in evaluator_source


def test_bound_smoke_bundle_is_hash_closed_before_fresh_rollout(tmp_path):
    source_root = (
        REPO_ROOT / "reports" / "noncombat_simulator_training_smoke_20260802"
    )
    artifact_root = tmp_path / "reports" / "smoke"
    artifact_root.mkdir(parents=True)
    for name in (
        "artifact_manifest.json",
        "metrics.json",
        "model.json",
        "report.md",
        "trajectories.json",
    ):
        (artifact_root / name).write_bytes((source_root / name).read_bytes())
    registration_path = tmp_path / "reports" / "smoke_input.json"
    registration_path.write_bytes(
        (
            REPO_ROOT
            / "reports"
            / "noncombat_simulator_training_smoke_20260802_input.json"
        ).read_bytes()
    )

    def binding(path: Path) -> dict[str, object]:
        return {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }

    smoke_artifacts = {
        "manifest": binding(artifact_root / "artifact_manifest.json"),
        "model": binding(artifact_root / "model.json"),
        "registration": binding(registration_path),
        "trajectories": binding(artifact_root / "trajectories.json"),
    }
    manifest = _validate_bound_smoke_artifacts(tmp_path, smoke_artifacts)
    assert set(manifest["authority"].values()) == {False}

    (artifact_root / "model.json").write_bytes(
        (artifact_root / "model.json").read_bytes() + b"\n"
    )
    with pytest.raises(PolicyValidityBlocked, match="binding mismatch"):
        _validate_bound_smoke_artifacts(tmp_path, smoke_artifacts)
