from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import pytest
import torch

from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_large_corpus_card_uplift_residual as study
from analysis_scripts import noncombat_large_corpus_card_uplift_residual_audit_runner as runner
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
                "corpus_registration",
                "corpus_report",
                "development_dataset",
                "entry_checkpoint",
                "residual_model",
                "study_configuration",
                "study_manifest",
                "study_metrics",
                "study_report",
                "train_dataset",
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
            "audit_seeds": list(runner.AUDIT_SEEDS),
            "seed_status": "reserved-untouched-audit",
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


def _candidate(slot: int, card_id: str) -> dict[str, object]:
    return {
        "action_id": f"card_reward:take:0:{slot}:{card_id.lower()}",
        "available": True,
        "category": "card_reward",
        "kind": "take",
        "label": card_id,
        "raw": {"id": card_id},
    }


def _row(index: int) -> ranking.CounterfactualRankingRow:
    return ranking.CounterfactualRankingRow(
        seed=runner.AUDIT_SEEDS[index % len(runner.AUDIT_SEEDS)],
        decision_index=index // len(runner.AUDIT_SEEDS),
        source_sha256=f"{index + 1:064x}",
        state_features=torch.zeros(3, dtype=torch.float32),
        candidate_features=torch.zeros((4, 2), dtype=torch.float32),
        candidates=(
            _candidate(0, "A"),
            _candidate(1, "B"),
            _candidate(2, "C"),
            {
                "action_id": "card_reward:skip:0",
                "available": True,
                "category": "card_reward",
                "kind": "skip",
                "label": "skip",
                "raw": {"reward_index": 0},
            },
        ),
        action_returns=(0.4, 0.2, 0.1, 0.0),
    )


def _partition(count: int = runner.MIN_AUDIT_SOURCE_STATES):
    rows = tuple(sorted((_row(index) for index in range(count)), key=lambda x: (x.seed, x.decision_index)))
    return ranking.CounterfactualPartition(
        name="audit",
        seeds=runner.AUDIT_SEEDS,
        rows=rows,
        action_branches=count * 4,
        root_native_transitions=1000,
        censored_seeds=(),
        budget_exhausted=False,
    )


def _model():
    model = uplift.UpliftModel(
        global_uplift=0.2,
        card_uplifts={"A": 0.4, "B": 0.2, "C": 0.1},
        card_counts={"A": 10, "B": 10, "C": 10},
    )
    configuration = uplift.ResidualConfiguration(shrinkage=1, strength=128)
    return model, configuration, uplift.encode_uplift_model(model, configuration)


def test_registration_fixes_schedule_limits_and_no_refit_authority(tmp_path):
    registration = runner.validate_registration(_registration(tmp_path))

    assert registration["schedule"]["audit_seeds"] == list(range(80320, 80384))
    assert registration["configuration"]["maximum_action_branches"] == 512
    assert registration["configuration"]["minimum_source_states"] == 110
    assert registration["operations"]["model_fitting"] is False
    assert registration["operations"]["training"] is False
    assert set(registration["authority"].values()) == {False}


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["schedule"].__setitem__("audit_seeds", [80320]),
        lambda value: value["configuration"].__setitem__(
            "minimum_source_states", 1
        ),
        lambda value: value["operations"].__setitem__("model_fitting", True),
        lambda value: value["authority"].__setitem__("promotion", True),
    ),
)
def test_registration_rejects_schedule_limit_and_authority_drift(
    tmp_path, mutation
):
    registration = _registration(tmp_path)
    mutation(registration)

    with pytest.raises(runner.LargeCorpusAuditBlocked):
        runner.validate_registration(registration)


def test_development_equivalent_gate_is_reused():
    assert runner._configuration()["development_equivalent_gates"] == {
        "minimum_corrected_actions": study.MIN_DEVELOPMENT_CORRECTED_ACTIONS,
        "worsened_actions_must_not_exceed_corrected": True,
    }


def test_execute_persists_model_before_factory_and_never_refits(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    model, configuration, model_bytes = _model()
    events: list[str] = []
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner,
        "_load_frozen_inputs",
        lambda _registration: (object(), model, configuration, model_bytes),
    )
    monkeypatch.setattr(runner.pilot, "encode_candidate_card_policy", lambda _x: b"entry")
    monkeypatch.setattr(
        runner.uplift,
        "fit_uplift_model",
        lambda *_args, **_kwargs: pytest.fail("audit must not fit"),
    )

    def load_factory(_identity):
        staging = tmp_path / f".output.{'c' * 40}.staging"
        assert (staging / "residual_model.json").read_bytes() == model_bytes
        events.append("factory")
        return object()

    monkeypatch.setattr(runner, "_collect", lambda _factory, **_kwargs: _partition())
    monkeypatch.setattr(
        runner.study,
        "_base_scores",
        lambda _bootstrap, rows: {
            row.source_sha256: (0.0, 2.0, 0.0, -1.0) for row in rows
        },
    )
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )
    ticks = iter((10.0, 20.0))

    terminal = runner.execute(
        registration,
        clock=lambda: next(ticks),
        process_observer=lambda: (),
        environment_factory_loader=load_factory,
    )

    assert events == ["factory"]
    assert terminal["verdict"] == (
        "large_corpus_card_uplift_residual_audit_ready_for_fresh_eval_proposal"
    )
    report = runner.base_runner._read_canonical(tmp_path / "output" / "report.json")
    assert report["comparison"]["corrected_actions"] == runner.MIN_AUDIT_SOURCE_STATES
    assert report["execution"]["unseen_take_actions"] == 0


def test_execute_stops_without_usable_output_below_support_floor(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    model, configuration, model_bytes = _model()
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner,
        "_load_frozen_inputs",
        lambda _registration: (object(), model, configuration, model_bytes),
    )
    monkeypatch.setattr(runner.pilot, "encode_candidate_card_policy", lambda _x: b"entry")
    monkeypatch.setattr(
        runner,
        "_collect",
        lambda _factory, **_kwargs: _partition(runner.MIN_AUDIT_SOURCE_STATES - 1),
    )

    with pytest.raises(runner.LargeCorpusAuditBlocked, match="support floor"):
        runner.execute(
            registration,
            clock=lambda: 10.0,
            process_observer=lambda: (),
            environment_factory_loader=lambda _identity: object(),
        )

    assert not (tmp_path / "output").exists()


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
