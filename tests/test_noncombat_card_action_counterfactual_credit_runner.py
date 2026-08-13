from __future__ import annotations

import copy
import json

import pytest

from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_action_counterfactual_credit_runner as runner
from analysis_scripts.noncombat_simulator_adapter import ADAPTER_API_VERSION


def _binding(path: str) -> dict[str, object]:
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _registration(tmp_path) -> dict[str, object]:
    source_bindings = {
        path: _binding(str(tmp_path / path.replace("/", "_")))
        for path in runner.BOUND_SOURCE_PATHS
    }
    return {
        "configuration": {
            "maximum_action_branches": credit.MAX_ACTION_BRANCHES,
            "maximum_card_states_per_seed": credit.MAX_CARD_STATES_PER_SEED,
            "maximum_charged_seconds": runner.MAX_CHARGED_SECONDS,
            "maximum_decisions_per_continuation": (
                credit.MAX_DECISIONS_PER_CONTINUATION
            ),
            "minimum_complete_source_states": credit.MIN_COMPLETE_SOURCE_STATES,
            "minimum_informative_source_states": (
                credit.MIN_INFORMATIVE_SOURCE_STATES
            ),
        },
        "downstream_authority": copy.deepcopy(
            credit.FALSE_DOWNSTREAM_AUTHORITY
        ),
        "native": {
            "identity": {
                "adapter_api_version": ADAPTER_API_VERSION,
                "dependency_closure": {"dependencies": []},
                "module": _binding(str(tmp_path / "adapter.pyd")),
            },
            "parent_registration": _binding(str(tmp_path / "parent.json")),
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
            "seed_status": "already-consumed-development-only",
            "seeds": list(credit.CONSUMED_DEVELOPMENT_SEEDS),
        },
        "schema_version": runner.REGISTRATION_SCHEMA_VERSION,
        "source": {
            "bindings": source_bindings,
            "commit": "c" * 40,
            "repo_root": tmp_path.as_posix(),
        },
    }


def test_registration_fixes_bounds_consumed_seeds_and_false_authority(tmp_path):
    registration = runner.validate_registration(_registration(tmp_path))

    assert registration["schedule"]["seeds"] == list(range(1000, 1008))
    assert registration["configuration"]["maximum_action_branches"] == 64
    assert registration["configuration"]["maximum_card_states_per_seed"] == 2
    assert set(registration["downstream_authority"].values()) == {False}
    assert registration["operations"]["training"] is False
    assert registration["operations"]["model_loading"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["schedule"].__setitem__("seeds", [9999]),
        lambda value: value["configuration"].__setitem__(
            "maximum_action_branches", 65
        ),
        lambda value: value["operations"].__setitem__("training", True),
        lambda value: value["downstream_authority"].__setitem__(
            "policy_quality", True
        ),
    ),
)
def test_registration_rejects_schedule_bound_and_authority_drift(
    tmp_path, mutation
):
    registration = _registration(tmp_path)
    mutation(registration)

    with pytest.raises(runner.CounterfactualRunnerBlocked):
        runner.validate_registration(registration)


def test_production_isolation_requires_both_bindings(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: True)
    monkeypatch.setattr(
        runner.pilot_runner,
        "_directory_metadata_binding",
        lambda _path: registration["production_isolation"][
            "production_checkpoints"
        ],
    )
    assert runner.production_isolation_matches(registration) is True

    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: False)
    assert runner.production_isolation_matches(registration) is False


def test_execute_publishes_compact_no_training_report(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {
            "checks": {},
            "registration_sha256": "d" * 64,
            "schema_version": runner.PREFLIGHT_SCHEMA_VERSION,
            "verdict": "preflight_passed",
        },
    )
    monkeypatch.setattr(runner, "production_isolation_matches", lambda _value: True)
    monkeypatch.setattr(
        credit,
        "run_counterfactual_credit_poc",
        lambda *_args, **_kwargs: {
            "configuration": {},
            "deterministic_replay": {"passed": True},
            "downstream_authority": copy.deepcopy(
                credit.FALSE_DOWNSTREAM_AUTHORITY
            ),
            "schema_version": credit.REPORT_SCHEMA_VERSION,
            "source_states": [],
            "summary": {"action_branch_continuations": 0},
            "verdict": "card_action_counterfactual_credit_not_ready",
        },
    )
    observed_times = iter((10.0, 11.0))

    terminal = runner.execute_poc(
        registration,
        clock=lambda: next(observed_times),
        process_observer=lambda: (),
        environment_factory_loader=lambda _identity: object(),
    )

    assert terminal["verdict"] == "card_action_counterfactual_credit_not_ready"
    report = json.loads(
        (tmp_path / "output" / "report.json").read_text(encoding="ascii")
    )
    assert report["execution"]["production_isolation_passed"] is True
    assert report["execution"]["operations"]["training"] is False
    assert report["execution"]["operations"]["model_loading"] is False
    assert set(report["downstream_authority"].values()) == {False}


def test_execute_fails_when_post_run_production_isolation_drifts(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(runner, "production_isolation_matches", lambda _value: False)
    monkeypatch.setattr(
        credit,
        "run_counterfactual_credit_poc",
        lambda *_args, **_kwargs: {
            "summary": {"action_branch_continuations": 0},
            "verdict": "card_action_counterfactual_credit_not_ready",
        },
    )

    with pytest.raises(
        runner.CounterfactualRunnerBlocked,
        match="production isolation changed",
    ):
        runner.execute_poc(
            registration,
            clock=lambda: 10.0,
            process_observer=lambda: (),
            environment_factory_loader=lambda _identity: object(),
        )
