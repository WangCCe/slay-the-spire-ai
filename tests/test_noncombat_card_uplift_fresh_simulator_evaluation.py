from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import pytest

from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_card_uplift_fresh_simulator_evaluation as runner
from analysis_scripts.noncombat_simulator_adapter import ADAPTER_API_VERSION


def _binding(path: str) -> dict[str, object]:
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _registration(tmp_path: Path) -> dict[str, object]:
    return {
        "authority": copy.deepcopy(runner.AUTHORITY),
        "configuration": runner._configuration(),
        "inputs": {
            name: _binding(str(tmp_path / f"{name}.json"))
            for name in (
                "audit_dataset",
                "audit_registration",
                "audit_report",
                "audit_terminal",
                "corpus_report",
                "entry_checkpoint",
                "residual_model",
            )
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
            "excluded_seed_ranges": copy.deepcopy(
                list(runner.EXCLUDED_SEED_RANGES)
            ),
            "fresh_seeds": list(runner.FRESH_SEEDS),
            "seed_status": "untouched-fresh-paired-evaluation",
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


def _candidates(category: str) -> list[dict[str, object]]:
    if category == "card_reward":
        return [
            {
                "action_id": f"card:{index}",
                "kind": "take",
                "raw": {"id": f"CARD_{index}"},
            }
            for index in range(3)
        ] + [{"action_id": "card:skip", "kind": "skip", "raw": {}}]
    return [{"action_id": f"{category}:native", "kind": "choose", "raw": {}}]


class _Environment:
    def __init__(self, categories: tuple[str, ...], floor: float = 10.0):
        self.categories = categories
        self.index = 0
        self.floor = floor


def _state(environment: _Environment):
    if environment.index >= len(environment.categories):
        return (
            {
                "category": "terminal",
                "state": {"floor": environment.floor, "outcome": "player_loss"},
                "terminal": True,
            },
            [],
        )
    category = environment.categories[environment.index]
    return (
        {"category": category, "state": {"floor": 1}, "terminal": False},
        _candidates(category),
    )


def _complete_arm(
    seed: int, arm: str, floor: float, *, interventions: int
) -> dict[str, object]:
    return {
        "action_sequence_sha256": "a" * 64,
        "actions": [{"action_id": "legal"}],
        "arm": arm,
        "card_decisions": [{} for _ in range(interventions)],
        "card_interventions": interventions,
        "categories": {"card_reward": interventions},
        "decisions": 1,
        "outcome": "player_loss",
        "seed": seed,
        "status": "complete",
        "terminal_floor": floor,
        "unsupported_reason": None,
        "victory": False,
    }


def test_registration_fixes_fresh_schedule_limits_and_false_authority(tmp_path):
    registration = runner.validate_registration(_registration(tmp_path))

    assert registration["schedule"]["fresh_seeds"] == list(range(90000, 90064))
    assert registration["configuration"]["maximum_episode_rollouts"] == 128
    assert registration["configuration"]["gates"]["minimum_complete_pairs"] == 56
    assert registration["operations"]["fresh_simulator_evaluation"] is True
    assert registration["operations"]["model_fitting"] is False
    assert set(registration["authority"].values()) == {False}


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["schedule"].__setitem__("fresh_seeds", [90000]),
        lambda value: value["configuration"]["gates"].__setitem__(
            "minimum_complete_pairs", 1
        ),
        lambda value: value["operations"].__setitem__("model_fitting", True),
        lambda value: value["authority"].__setitem__("promotion", True),
    ),
)
def test_registration_rejects_schedule_gate_and_authority_drift(
    tmp_path, mutation
):
    registration = _registration(tmp_path)
    mutation(registration)

    with pytest.raises(runner.FreshSimulatorEvaluationBlocked):
        runner.validate_registration(registration)


def test_choose_index_uses_action_id_for_exact_score_ties():
    candidates = [{"action_id": "b"}, {"action_id": "a"}, {"action_id": "c"}]

    assert runner._choose_index((2.0, 2.0, 1.0), candidates) == 1


def test_rollout_routes_only_candidate_card_rewards_through_residual(
    monkeypatch,
):
    candidate_calls: list[int] = []
    monkeypatch.setattr(runner.credit, "_environment_state", _state)

    def advance_native(environment):
        snapshot, candidates = _state(environment)
        action_id = candidates[0]["action_id"]
        environment.index += 1
        return environment, {"selected_action_id": action_id}

    def candidate_step(environment, **_kwargs):
        candidate_calls.append(environment.index)
        environment.index += 1
        return environment, {"selected_action_id": "card:1"}, {
            "candidate_action_id": "card:1",
            "intervened": True,
            "native_action_id": "card:0",
            "source_sha256": "b" * 64,
            "unseen_take_actions": 0,
        }

    monkeypatch.setattr(runner.credit, "_advance_native", advance_native)
    monkeypatch.setattr(runner, "_candidate_card_step", candidate_step)
    model = uplift.UpliftModel(0.0, {}, {})
    configuration = uplift.ResidualConfiguration(shrinkage=1, strength=128)

    result = runner._rollout_episode(
        lambda _seed: _Environment(("route", "card_reward", "event")),
        seed=90000,
        arm="candidate",
        bootstrap=object(),
        model=model,
        configuration=configuration,
        deadline=100.0,
        clock=lambda: 0.0,
    )

    assert candidate_calls == [1]
    assert result["status"] == "complete"
    assert result["card_interventions"] == 1
    assert result["categories"] == {"card_reward": 1, "event": 1, "route": 1}


def test_rollout_records_registered_support_censor(monkeypatch):
    monkeypatch.setattr(runner.credit, "_environment_state", _state)

    def blocked(_environment):
        raise credit.CounterfactualCreditBlocked(
            "unsupported_shop_courier_restock_semantics"
        )

    monkeypatch.setattr(runner.credit, "_advance_native", blocked)
    model = uplift.UpliftModel(0.0, {}, {})
    configuration = uplift.ResidualConfiguration(shrinkage=1, strength=128)

    result = runner._rollout_episode(
        lambda _seed: _Environment(("shop",)),
        seed=90000,
        arm="control",
        bootstrap=object(),
        model=model,
        configuration=configuration,
        deadline=100.0,
        clock=lambda: 0.0,
    )

    assert result["status"] == "censored"
    assert result["unsupported_reason"] == (
        "unsupported_shop_courier_restock_semantics"
    )


def test_paired_metrics_are_deterministic_and_pass_fixed_positive_case():
    pairs = [
        {
            "candidate": _complete_arm(seed, "candidate", 11.0, interventions=1),
            "control": _complete_arm(seed, "control", 10.0, interventions=0),
            "seed": seed,
        }
        for seed in runner.FRESH_SEEDS
    ]

    first = runner.evaluate_pairs(pairs)
    second = runner.evaluate_pairs(pairs)

    assert first == second
    assert first["mean_paired_terminal_floor_difference"] == 1.0
    assert first["bootstrap_95_percent"] == {"lower": 1.0, "upper": 1.0}
    assert first["candidate_card_interventions"] == 64
    assert set(first["checks"].values()) == {True}


def test_execute_persists_model_before_factory_and_publishes_ready_result(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    model = uplift.UpliftModel(0.0, {}, {})
    configuration = uplift.ResidualConfiguration(shrinkage=1, strength=128)
    model_bytes = b"model"
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner,
        "_load_frozen_inputs",
        lambda _value: (object(), model, configuration, b"entry", model_bytes),
    )
    monkeypatch.setattr(runner.pilot, "encode_candidate_card_policy", lambda _x: b"x")
    monkeypatch.setattr(runner.ranking, "restore_entry_bootstrap", lambda _x: object())
    monkeypatch.setattr(runner.uplift, "encode_uplift_model", lambda *_x: model_bytes)
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )
    monkeypatch.setattr(
        runner,
        "_source_bindings",
        lambda _root, _commit: registration["source"]["bindings"],
    )

    def load_factory(_identity):
        staging = tmp_path / f".output.{'c' * 40}.staging"
        assert (staging / "residual_model.json").read_bytes() == model_bytes
        return object()

    def rollout(_factory, *, seed, arm, **_kwargs):
        return _complete_arm(
            seed,
            arm,
            11.0 if arm == "candidate" else 10.0,
            interventions=1 if arm == "candidate" else 0,
        )

    monkeypatch.setattr(runner, "_rollout_episode", rollout)
    ticks = iter((10.0, 20.0))

    terminal = runner.execute(
        registration,
        clock=lambda: next(ticks),
        process_observer=lambda: (),
        environment_factory_loader=load_factory,
    )

    assert terminal["verdict"] == (
        "card_uplift_fresh_simulator_ready_for_live_shadow_adapter_proposal"
    )
    report = runner.base_runner._read_canonical(tmp_path / "output" / "report.json")
    assert report["execution"]["completed_pairs"] == 64
    assert set(report["checks"].values()) == {True}


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
