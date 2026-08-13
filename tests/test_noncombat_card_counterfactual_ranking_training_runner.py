from __future__ import annotations

import copy
import json

import pytest

from analysis_scripts import noncombat_card_counterfactual_ranking_training as training
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as runner
from analysis_scripts.noncombat_simulator_adapter import ADAPTER_API_VERSION


def _binding(path: str) -> dict[str, object]:
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _registration(tmp_path) -> dict[str, object]:
    return {
        "configuration": runner._configuration(),
        "downstream_authority": copy.deepcopy(runner.FALSE_DOWNSTREAM_AUTHORITY),
        "inputs": {
            "entry_checkpoint": _binding(str(tmp_path / "entry.json")),
            "parent_registration": _binding(str(tmp_path / "parent.json")),
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
            "holdout_seeds": list(training.HOLDOUT_SEEDS),
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


def test_registration_fixes_partitions_steps_operations_and_authority(tmp_path):
    registration = runner.validate_registration(_registration(tmp_path))

    assert registration["schedule"]["train_seeds"] == list(range(1000, 1016))
    assert registration["schedule"]["holdout_seeds"] == list(range(1016, 1024))
    assert registration["configuration"]["training_steps"] == 32
    assert registration["configuration"]["maximum_train_branches"] == 128
    assert registration["configuration"]["maximum_holdout_branches"] == 64
    assert set(registration["downstream_authority"].values()) == {False}
    assert registration["operations"]["training"] is True
    assert registration["operations"]["fresh_evaluation"] is False
    assert registration["operations"]["production_model_loading"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["schedule"].__setitem__("holdout_seeds", [1000]),
        lambda value: value["configuration"].__setitem__("training_steps", 33),
        lambda value: value["operations"].__setitem__("fresh_evaluation", True),
        lambda value: value["downstream_authority"].__setitem__(
            "policy_quality", True
        ),
    ),
)
def test_registration_rejects_partition_step_operation_and_authority_drift(
    tmp_path, mutation
):
    registration = _registration(tmp_path)
    mutation(registration)
    with pytest.raises(runner.RankingRunnerBlocked):
        runner.validate_registration(registration)


def _partition(name: str, count: int, branches: int):
    return training.CounterfactualPartition(
        name=name,
        seeds=training.TRAIN_SEEDS if name == "train" else training.HOLDOUT_SEEDS,
        rows=tuple(object() for _ in range(count)),
        action_branches=branches,
        root_native_transitions=10,
        censored_seeds=(),
        budget_exhausted=True,
    )


def test_execute_runs_fixed_training_and_publishes_experiment_only_model(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    (tmp_path / "entry.json").write_bytes(b"entry")
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(runner, "production_isolation_matches", lambda _value: True)
    partitions = iter((
        _partition("train", training.MIN_TRAIN_SOURCE_STATES, 100),
        _partition("holdout", training.MIN_HOLDOUT_SOURCE_STATES, 48),
    ))
    monkeypatch.setattr(
        training, "collect_counterfactual_partition", lambda *_args, **_kwargs: next(partitions)
    )
    monkeypatch.setattr(
        training,
        "compact_partition",
        lambda partition: {"name": partition.name, "source_states": []},
    )
    monkeypatch.setattr(training, "restore_entry_bootstrap", lambda _bytes: object())
    observed: dict[str, object] = {}

    def fake_train(_bootstrap, *, train_rows, holdout_rows, training_steps):
        observed.update(
            train_count=len(train_rows),
            holdout_count=len(holdout_rows),
            training_steps=training_steps,
        )
        return training.CompletedCounterfactualRankingTraining(
            report={"schema_version": "test", "verdict": "ready"},
            entry_model=b"entry-model",
            trained_model=b'{"model":"trained"}',
        )

    monkeypatch.setattr(training, "train_counterfactual_ranking", fake_train)
    times = iter((10.0, 11.0))

    terminal = runner.execute(
        registration,
        clock=lambda: next(times),
        process_observer=lambda: (),
        environment_factory_loader=lambda _identity: object(),
    )

    assert observed == {
        "train_count": training.MIN_TRAIN_SOURCE_STATES,
        "holdout_count": training.MIN_HOLDOUT_SOURCE_STATES,
        "training_steps": 32,
    }
    assert terminal["optimizer_steps"] == 32
    assert terminal["action_branches"] == 148
    report = json.loads((tmp_path / "output" / "report.json").read_text("ascii"))
    assert report["execution"]["operations"]["training"] is True
    assert report["execution"]["operations"]["fresh_evaluation"] is False
    assert set(report["downstream_authority"].values()) == {False}
    assert (tmp_path / "output" / "trained_model.json").is_file()


def test_execute_stops_before_training_when_partition_support_is_low(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    (tmp_path / "entry.json").write_bytes(b"entry")
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        training,
        "collect_counterfactual_partition",
        lambda *_args, **_kwargs: _partition("train", 23, 92),
    )
    monkeypatch.setattr(
        training,
        "compact_partition",
        lambda partition: {"name": partition.name},
    )

    with pytest.raises(runner.RankingRunnerBlocked, match="train source support"):
        runner.execute(
            registration,
            clock=lambda: 10.0,
            process_observer=lambda: (),
            environment_factory_loader=lambda _identity: object(),
        )


def test_production_isolation_requires_config_and_checkpoint_bindings(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: True)
    monkeypatch.setattr(
        runner.pilot_runner,
        "_directory_metadata_binding",
        lambda _path: registration["production_isolation"]["production_checkpoints"],
    )
    assert runner.production_isolation_matches(registration) is True
    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: False)
    assert runner.production_isolation_matches(registration) is False
