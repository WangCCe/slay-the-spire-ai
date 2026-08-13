from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import pytest

from analysis_scripts import noncombat_card_counterfactual_uplift_residual_audit_runner as runner
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as crossfit
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts.noncombat_simulator_adapter import ADAPTER_API_VERSION


def _binding(path: str) -> dict[str, object]:
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _registration(tmp_path) -> dict[str, object]:
    inputs = {
        name: _binding(str(tmp_path / f"{name}.json"))
        for name in (
            "crossfit_configuration",
            "crossfit_manifest",
            "crossfit_report",
            "development_dataset",
            "entry_checkpoint",
            "scorer_registration",
            "scorer_report",
            "train_dataset",
        )
    }
    return {
        "authority": copy.deepcopy(runner.AUTHORITY),
        "configuration": runner._configuration(),
        "inputs": inputs,
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
            "audit_seeds": list(runner.AUDIT_SEEDS),
            "seed_status": "consumed-untouched-audit",
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


def _partition(count: int = runner.MIN_AUDIT_SOURCE_STATES):
    return ranking.CounterfactualPartition(
        name="audit",
        seeds=runner.AUDIT_SEEDS,
        rows=tuple(object() for _ in range(count)),
        action_branches=48,
        root_native_transitions=20,
        censored_seeds=(),
        budget_exhausted=True,
    )


def _metrics(mean: float, maximum: float, pairwise: float, unique: float):
    return {
        "maximum_top_action_regret": maximum,
        "mean_top_action_regret": mean,
        "predictions": [],
        "source_states": runner.MIN_AUDIT_SOURCE_STATES,
        "unique_best_accuracy": unique,
        "unique_best_correct": 1,
        "unique_best_states": 2,
        "weighted_pairwise_accuracy": pairwise,
        "weighted_pairwise_margin": 1.0,
    }


def test_registration_fixes_model_schedule_limits_and_authority(tmp_path):
    registration = runner.validate_registration(_registration(tmp_path))

    assert registration["configuration"]["fixed_residual"] == {
        "shrinkage": 3,
        "strength": 128,
    }
    assert registration["schedule"]["audit_seeds"] == list(range(1024, 1032))
    assert registration["configuration"]["maximum_action_branches"] == 64
    assert registration["configuration"]["minimum_source_states"] == 12
    assert set(registration["authority"].values()) == {False}
    assert registration["operations"]["post_audit_fitting"] is False


def test_isolated_direct_entry_can_load_package():
    completed = subprocess.run(
        [sys.executable, "-I", str(Path(runner.__file__).resolve()), "--help"],
        cwd=Path(runner.__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "run-worker" in completed.stdout


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["configuration"]["fixed_residual"].__setitem__(
            "strength", 64
        ),
        lambda value: value["schedule"].__setitem__("audit_seeds", [1024]),
        lambda value: value["authority"].__setitem__("policy_quality", True),
    ),
)
def test_registration_rejects_fixed_contract_drift(tmp_path, mutation):
    registration = _registration(tmp_path)
    mutation(registration)

    with pytest.raises(runner.UpliftAuditBlocked):
        runner.validate_registration(registration)


def test_preflight_restores_inputs_without_fitting_model(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: True)
    monkeypatch.setattr(
        runner,
        "_source_bindings",
        lambda _root, _commit: registration["source"]["bindings"],
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 0})(),
    )

    def fake_read(path):
        name = Path(path).name
        if name == "crossfit_configuration.json":
            return {
                "inputs": {
                    "development_dataset": registration["inputs"]["development_dataset"],
                    "entry_checkpoint": registration["inputs"]["entry_checkpoint"],
                    "scorer_registration": registration["inputs"]["scorer_registration"],
                    "scorer_report": registration["inputs"]["scorer_report"],
                    "train_dataset": registration["inputs"]["train_dataset"],
                }
            }
        if name == "crossfit_manifest.json":
            return {
                "artifacts": {
                    "configuration.json": registration["inputs"]["crossfit_configuration"],
                    "report.json": registration["inputs"]["crossfit_report"],
                },
                "verdict": "card_counterfactual_uplift_residual_ready_for_audit_proposal",
            }
        if name == "crossfit_report.json":
            return {
                "audit_accessed": False,
                "verdict": "card_counterfactual_uplift_residual_ready_for_audit_proposal",
            }
        if name == "scorer_report.json":
            return {
                "audit_accessed": False,
                "datasets": {
                    "development": registration["inputs"]["development_dataset"],
                    "train": registration["inputs"]["train_dataset"],
                },
                "verdict": "card_counterfactual_scorer_weight_not_ready",
            }
        if name == "scorer_registration.json":
            return {
                "inputs": {
                    "entry_checkpoint": registration["inputs"]["entry_checkpoint"]
                },
                "native": registration["native"],
                "production_isolation": registration["production_isolation"],
            }
        raise AssertionError(name)

    monkeypatch.setattr(runner.base_runner, "_read_canonical", fake_read)
    monkeypatch.setattr(
        runner,
        "_load_exposed_rows",
        lambda _registration: (tuple(object() for _ in range(46)), object()),
    )
    monkeypatch.setattr(runner.pilot, "encode_candidate_card_policy", lambda _x: b"entry")
    monkeypatch.setattr(
        runner.crossfit,
        "fit_uplift_model",
        lambda *_args, **_kwargs: pytest.fail("preflight must not fit"),
    )
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )

    result = runner.preflight_registration(
        registration, process_observer=lambda: ()
    )

    assert result["verdict"] == "preflight_passed"
    assert result["checks"]["audit_untouched"] is True


def _prepare_execute(tmp_path, monkeypatch, *, support=runner.MIN_AUDIT_SOURCE_STATES):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner,
        "_load_exposed_rows",
        lambda _registration: (tuple(object() for _ in range(46)), object()),
    )
    monkeypatch.setattr(runner.pilot, "encode_candidate_card_policy", lambda _x: b"entry")
    model = crossfit.UpliftModel(
        global_uplift=0.1,
        card_uplifts={"A": 0.2},
        card_counts={"A": 1},
    )
    events = []

    def fake_fit(_rows, *, shrinkage):
        events.append(("fit", shrinkage))
        return model

    monkeypatch.setattr(runner.crossfit, "fit_uplift_model", fake_fit)
    monkeypatch.setattr(
        runner.crossfit,
        "encode_uplift_model",
        lambda _model, _configuration: b'{"model":"fixed"}',
    )
    monkeypatch.setattr(
        runner.crossfit,
        "restore_uplift_model",
        lambda _payload: (model, runner.FIXED_CONFIGURATION),
    )

    def load_factory(_identity):
        assert (tmp_path / "output" / "uplift_model.json").is_file()
        assert events == [("fit", 3)]
        events.append("load_factory")
        return object()

    def fake_collect(_factory, *, deadline, clock):
        events.append("collect")
        return _partition(support)

    monkeypatch.setattr(runner, "_collect", fake_collect)
    monkeypatch.setattr(
        runner,
        "_write_dataset",
        lambda path, _partition: _binding(str(path)),
    )
    monkeypatch.setattr(
        runner.crossfit,
        "_base_scores",
        lambda _bootstrap, rows: {str(index): (0.0,) for index, _ in enumerate(rows)},
    )
    monkeypatch.setattr(
        runner.crossfit,
        "score_residual_rows",
        lambda rows, base, model, configuration: (base, 0),
    )
    evaluations = iter(
        (
            _metrics(0.2, 0.4, 0.4, 0.4),
            _metrics(0.1, 0.4, 0.6, 0.5),
        )
    )
    monkeypatch.setattr(
        runner.crossfit, "evaluate_scores", lambda *_args: next(evaluations)
    )
    monkeypatch.setattr(
        runner.crossfit,
        "compare_predictions",
        lambda *_args: {
            "action_flips": 1,
            "corrected_actions": 1,
            "worsened_actions": 0,
        },
    )
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )
    return registration, load_factory, events


def test_execute_fits_once_before_factory_and_never_refits(tmp_path, monkeypatch):
    registration, loader, events = _prepare_execute(tmp_path, monkeypatch)
    times = iter((10.0, 11.0))

    terminal = runner.execute(
        registration,
        clock=lambda: next(times),
        process_observer=lambda: (),
        environment_factory_loader=loader,
    )

    assert events == [("fit", 3), "load_factory", "collect"]
    assert terminal["source_states"] == runner.MIN_AUDIT_SOURCE_STATES
    assert terminal["verdict"] == (
        "card_counterfactual_uplift_residual_audit_ready_for_fresh_eval_proposal"
    )


def test_low_audit_support_stops_before_evaluation(tmp_path, monkeypatch):
    registration, loader, events = _prepare_execute(
        tmp_path, monkeypatch, support=runner.MIN_AUDIT_SOURCE_STATES - 1
    )
    monkeypatch.setattr(
        runner.crossfit,
        "evaluate_scores",
        lambda *_args: pytest.fail("low support must not be evaluated"),
    )

    with pytest.raises(runner.UpliftAuditBlocked, match="support floor"):
        runner.execute(
            registration,
            clock=lambda: 10.0,
            process_observer=lambda: (),
            environment_factory_loader=loader,
        )

    assert events == [("fit", 3), "load_factory", "collect"]


def test_audit_gate_requires_every_fixed_metric():
    base = _metrics(0.2, 0.4, 0.4, 0.4)
    candidate = _metrics(0.1, 0.4, 0.6, 0.5)
    comparison = {"corrected_actions": 1}

    assert all(runner._audit_checks(base, candidate, comparison).values())
    candidate["maximum_top_action_regret"] = 0.5
    assert runner._audit_checks(base, candidate, comparison)[
        "maximum_regret_nonincreasing"
    ] is False
