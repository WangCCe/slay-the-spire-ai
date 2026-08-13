from __future__ import annotations

import copy
import pytest

from analysis_scripts import noncombat_card_counterfactual_ranking_training as training
from analysis_scripts import noncombat_card_counterfactual_scorer_weight_runner as runner
from analysis_scripts.noncombat_simulator_adapter import ADAPTER_API_VERSION


def _binding(path: str) -> dict[str, object]:
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _registration(tmp_path) -> dict[str, object]:
    entry = tmp_path / "entry.json"
    r2_registration = tmp_path / "r2-registration.json"
    r2_report = tmp_path / "r2-report.json"
    entry.write_bytes(b"entry")
    r2_registration.write_text("{}", encoding="ascii")
    r2_report.write_bytes(
        runner.base_runner._canonical_bytes(
            {
                "datasets": {
                    "holdout": {"identity": "development"},
                    "train": {"identity": "train"},
                },
                "verdict": "card_counterfactual_ranking_training_not_ready",
            }
        )
    )
    return {
        "configuration": runner._configuration(),
        "downstream_authority": copy.deepcopy(runner.FALSE_DOWNSTREAM_AUTHORITY),
        "inputs": {
            "entry_checkpoint": _binding(str(entry)),
            "r2_registration": _binding(str(r2_registration)),
            "r2_report": _binding(str(r2_report)),
        },
        "native": {
            "identity": {
                "adapter_api_version": ADAPTER_API_VERSION,
                "dependency_closure": {"dependencies": []},
                "module": _binding(str(tmp_path / "adapter.pyd")),
            }
        },
        "operations": copy.deepcopy(runner.OPERATIONS),
        "output_dir": (tmp_path / "output").as_posix(),
        "production_isolation": {
            "communication_mod_config": _binding(str(tmp_path / "config")),
            "production_checkpoints": {
                "file_count": 0,
                "metadata_sha256": "b" * 64,
                "path": (tmp_path / "checkpoints").as_posix(),
                "size_bytes": 0,
            },
        },
        "schedule": {
            "audit_access": "only_after_development_pass",
            "audit_seeds": list(runner.AUDIT_SEEDS),
            "development_seeds": list(training.HOLDOUT_SEEDS),
            "seed_status": "already-consumed-development-only",
            "train_seeds": list(training.TRAIN_SEEDS),
        },
        "schema_version": runner.REGISTRATION_SCHEMA_VERSION,
        "source": {
            "bindings": {
                path: _binding(str(tmp_path / path.replace("/", "_")))
                for path in runner.BOUND_SOURCE_PATHS
            },
            "commit": "c" * 40,
            "repo_root": tmp_path.as_posix(),
        },
    }


def _partition(name: str, count: int, branches: int):
    seeds = {
        "train": training.TRAIN_SEEDS,
        "holdout": training.HOLDOUT_SEEDS,
        "audit": runner.AUDIT_SEEDS,
    }[name]
    return training.CounterfactualPartition(
        name=name,
        seeds=seeds,
        rows=tuple(object() for _ in range(count)),
        action_branches=branches,
        root_native_transitions=10,
        censored_seeds=(),
        budget_exhausted=True,
    )


def _prepare_execute(tmp_path, monkeypatch, *, development_passed: bool):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )
    monkeypatch.setattr(
        training,
        "compact_partition",
        lambda partition: {
            "identity": "train" if partition.name == "train" else "development"
        },
    )
    monkeypatch.setattr(
        runner,
        "_write_dataset",
        lambda path, _partition: _binding(str(path)),
    )
    bootstraps = iter((object(), object()))
    monkeypatch.setattr(training, "restore_entry_bootstrap", lambda _bytes: next(bootstraps))
    train_calls = []

    def fake_train(_bootstrap, *, train_rows, development_rows, training_steps):
        train_calls.append((len(train_rows), len(development_rows), training_steps))
        return training.CompletedCounterfactualRankingTraining(
            report={
                "schema_version": "test",
                "verdict": (
                    "card_counterfactual_scorer_weight_development_passed"
                    if development_passed
                    else "card_counterfactual_scorer_weight_development_not_ready"
                ),
            },
            entry_model=b"entry-model",
            trained_model=b'{"model":"trained"}',
        )

    monkeypatch.setattr(training, "train_scorer_weight_ranking", fake_train)
    return registration, train_calls


def test_registration_fixes_staged_schedule_scope_and_authority(tmp_path):
    registration = runner.validate_registration(_registration(tmp_path))

    assert registration["schedule"]["train_seeds"] == list(range(1000, 1016))
    assert registration["schedule"]["development_seeds"] == list(range(1016, 1024))
    assert registration["schedule"]["audit_seeds"] == list(range(1024, 1032))
    assert registration["schedule"]["audit_access"] == "only_after_development_pass"
    assert registration["configuration"]["trainable_parameter_count"] == 128
    assert registration["configuration"]["training_steps"] == 32
    assert set(registration["downstream_authority"].values()) == {False}
    assert registration["operations"]["training"] is True
    assert registration["operations"]["fresh_evaluation"] is False


def test_development_failure_never_constructs_audit_partition(tmp_path, monkeypatch):
    registration, train_calls = _prepare_execute(
        tmp_path, monkeypatch, development_passed=False
    )
    names = []

    def fake_collect(_factory, *, name, **_kwargs):
        names.append(name)
        if name == "train":
            return _partition(name, training.MIN_TRAIN_SOURCE_STATES, 121)
        if name == "holdout":
            return _partition(name, training.MIN_HOLDOUT_SOURCE_STATES, 64)
        raise AssertionError("audit partition must not be constructed")

    monkeypatch.setattr(runner, "_collect", fake_collect)
    monkeypatch.setattr(
        training,
        "audit_scorer_weight_model",
        lambda *_args: pytest.fail("audit model must not be evaluated"),
    )
    times = iter((10.0, 11.0))

    terminal = runner.execute(
        registration,
        clock=lambda: next(times),
        process_observer=lambda: (),
        environment_factory_loader=lambda _identity: object(),
    )

    assert names == ["train", "holdout"]
    assert train_calls == [(training.MIN_TRAIN_SOURCE_STATES, training.MIN_HOLDOUT_SOURCE_STATES, 32)]
    assert terminal["audit_accessed"] is False
    assert terminal["action_branches"] == 185
    assert terminal["verdict"] == "card_counterfactual_scorer_weight_not_ready"


def test_development_pass_accesses_one_audit_without_refitting(tmp_path, monkeypatch):
    registration, train_calls = _prepare_execute(
        tmp_path, monkeypatch, development_passed=True
    )
    names = []

    def fake_collect(_factory, *, name, **_kwargs):
        names.append(name)
        if name == "train":
            return _partition(name, training.MIN_TRAIN_SOURCE_STATES, 121)
        if name == "holdout":
            return _partition(name, training.MIN_HOLDOUT_SOURCE_STATES, 64)
        return _partition(name, runner.MIN_AUDIT_SOURCE_STATES, 48)

    monkeypatch.setattr(runner, "_collect", fake_collect)
    audit_calls = []

    def fake_audit(entry, trained, rows):
        audit_calls.append((entry, trained, len(rows)))
        return {"verdict": "card_counterfactual_scorer_weight_audit_passed"}

    monkeypatch.setattr(training, "audit_scorer_weight_model", fake_audit)
    times = iter((10.0, 11.0))

    terminal = runner.execute(
        registration,
        clock=lambda: next(times),
        process_observer=lambda: (),
        environment_factory_loader=lambda _identity: object(),
    )

    assert names == ["train", "holdout", "audit"]
    assert len(train_calls) == 1
    assert len(audit_calls) == 1
    assert audit_calls[0][2] == runner.MIN_AUDIT_SOURCE_STATES
    assert terminal["audit_accessed"] is True
    assert terminal["action_branches"] == 233
    assert terminal["verdict"] == "card_counterfactual_scorer_weight_ready_for_fresh_eval_proposal"


def test_dataset_identity_drift_stops_before_training(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    partitions = iter(
        (
            _partition("train", training.MIN_TRAIN_SOURCE_STATES, 121),
            _partition("holdout", training.MIN_HOLDOUT_SOURCE_STATES, 64),
        )
    )
    monkeypatch.setattr(runner, "_collect", lambda *_args, **_kwargs: next(partitions))
    monkeypatch.setattr(training, "compact_partition", lambda _partition: {"drift": True})
    monkeypatch.setattr(
        training,
        "train_scorer_weight_ranking",
        lambda *_args, **_kwargs: pytest.fail("training must not start"),
    )

    with pytest.raises(runner.ScorerWeightRunnerBlocked, match="dataset identity"):
        runner.execute(
            registration,
            clock=lambda: 10.0,
            process_observer=lambda: (),
            environment_factory_loader=lambda _identity: object(),
        )
