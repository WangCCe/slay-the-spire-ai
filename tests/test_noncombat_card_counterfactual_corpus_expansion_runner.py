from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import pytest
import torch

from analysis_scripts import noncombat_card_counterfactual_corpus_expansion_runner as runner
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts.noncombat_simulator_adapter import ADAPTER_API_VERSION


def _binding(path: str) -> dict[str, object]:
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _registration(tmp_path: Path) -> dict[str, object]:
    return {
        "authority": copy.deepcopy(runner.AUTHORITY),
        "configuration": runner._configuration(),
        "inputs": {
            "lineage_registration": _binding(
                str(tmp_path / "lineage_registration.json")
            ),
            "lineage_report": _binding(str(tmp_path / "lineage_report.json")),
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
            "development_seeds": list(runner.DEVELOPMENT_SEEDS),
            "reserved_audit_seeds": list(runner.RESERVED_AUDIT_SEEDS),
            "seed_status": "new-train-development-with-untouched-audit",
            "train_seeds": list(runner.TRAIN_SEEDS),
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


def _row(
    seed: int,
    decision_index: int = 0,
    *,
    card_id: str = "ANGER",
) -> ranking.CounterfactualRankingRow:
    candidates = (
        {
            "action_id": f"card_reward:take:0:0:{card_id.lower()}",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": card_id,
            "raw": {"id": card_id},
        },
        {
            "action_id": "card_reward:take:0:1:shrug_it_off",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": "Shrug It Off",
            "raw": {"id": "SHRUG_IT_OFF"},
        },
        {
            "action_id": "card_reward:take:0:2:anger",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": "Anger",
            "raw": {"id": "ANGER"},
        },
        {
            "action_id": "card_reward:skip:0",
            "available": True,
            "category": "card_reward",
            "kind": "skip",
            "label": "skip",
            "raw": {"reward_index": 0},
        },
    )
    return ranking.CounterfactualRankingRow(
        seed=seed,
        decision_index=decision_index,
        source_sha256=f"{seed * 10000 + decision_index:064x}",
        state_features=torch.zeros(3, dtype=torch.float32),
        candidate_features=torch.zeros((4, 2), dtype=torch.float32),
        candidates=candidates,
        action_returns=(0.0, 0.25, 0.0, 0.1),
    )


def _partition(
    name: str,
    seeds: tuple[int, ...],
    count: int,
) -> ranking.CounterfactualPartition:
    return ranking.CounterfactualPartition(
        name=name,
        seeds=seeds,
        rows=tuple(_row(seeds[index % len(seeds)], index) for index in range(count)),
        action_branches=count * 4,
        root_native_transitions=count,
        censored_seeds=(),
        budget_exhausted=True,
    )


def test_registration_fixes_disjoint_schedule_limits_and_no_authority(tmp_path):
    registration = runner.validate_registration(_registration(tmp_path))

    assert registration["schedule"]["train_seeds"] == list(range(80000, 80256))
    assert registration["schedule"]["development_seeds"] == list(
        range(80256, 80320)
    )
    assert registration["schedule"]["reserved_audit_seeds"] == list(
        range(80320, 80384)
    )
    assert registration["configuration"]["maximum_train_branches"] == 2048
    assert registration["configuration"]["maximum_development_branches"] == 512
    assert set(registration["authority"].values()) == {False}
    assert registration["operations"]["training"] is False
    assert registration["operations"]["audit_access"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["schedule"].__setitem__(
            "development_seeds", list(runner.TRAIN_SEEDS[:64])
        ),
        lambda value: value["schedule"].__setitem__("reserved_audit_seeds", []),
        lambda value: value["configuration"].__setitem__(
            "minimum_train_source_states", 1
        ),
        lambda value: value["authority"].__setitem__("training", True),
    ),
)
def test_registration_rejects_schedule_limit_and_authority_drift(
    tmp_path, mutation
):
    registration = _registration(tmp_path)
    mutation(registration)

    with pytest.raises(runner.CorpusExpansionBlocked):
        runner.validate_registration(registration)


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


def test_dataset_round_trip_and_coverage_diagnostics():
    partition = _partition("train", runner.TRAIN_SEEDS, 2)

    payload = runner._encode_dataset(partition)
    restored = ranking.restore_counterfactual_partition(payload)
    diagnostics = runner.partition_diagnostics(restored)

    assert len(restored.rows) == 2
    assert diagnostics["source_states"] == 2
    assert diagnostics["informative_source_states"] == 2
    assert diagnostics["candidate_action_count"] == 8
    assert diagnostics["action_kind_counts"] == {"skip": 2, "take": 6}
    assert diagnostics["take_card_ids"] == ["ANGER", "SHRUG_IT_OFF"]
    assert diagnostics["spread_summary"]["nonzero_states"] == 2


def test_preflight_binds_lineage_and_keeps_reserved_audit_unaccessed(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "_source_bindings",
        lambda _root, _commit: registration["source"]["bindings"],
    )
    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: True)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 0})(),
    )

    def fake_read(path):
        if Path(path).name == "lineage_report.json":
            return {
                "verdict": "card_counterfactual_uplift_residual_audit_not_ready"
            }
        return {
            "native": registration["native"],
            "production_isolation": registration["production_isolation"],
        }

    monkeypatch.setattr(runner.base_runner, "_read_canonical", fake_read)
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )

    result = runner.preflight_registration(
        registration, process_observer=lambda: ()
    )

    assert result["verdict"] == "preflight_passed"
    assert result["checks"]["audit_reserved_and_unaccessed"] is True


def test_execute_collects_only_train_and_development(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )
    calls: list[tuple[str, tuple[int, ...]]] = []

    def fake_collect(_factory, *, name, seeds, **_kwargs):
        normalized = tuple(seeds)
        calls.append((name, normalized))
        if name == "train":
            return _partition(name, normalized, runner.MIN_TRAIN_SOURCE_STATES)
        assert name == "holdout"
        return _partition(name, normalized, runner.MIN_DEVELOPMENT_SOURCE_STATES)

    monkeypatch.setattr(runner, "_collect", fake_collect)
    monkeypatch.setattr(runner, "_encode_dataset", lambda _partition: b"{}")
    monkeypatch.setattr(
        runner,
        "partition_diagnostics",
        lambda partition: {
            "source_states": len(partition.rows),
            "take_card_ids": ["ANGER"] if partition.name == "train" else ["BASH"],
        },
    )
    ticks = iter((10.0, 20.0))

    terminal = runner.execute(
        registration,
        clock=lambda: next(ticks),
        process_observer=lambda: (),
        environment_factory_loader=lambda _identity: object(),
    )

    assert calls == [
        ("train", runner.TRAIN_SEEDS),
        ("holdout", runner.DEVELOPMENT_SEEDS),
    ]
    assert all(not (set(seeds) & set(runner.RESERVED_AUDIT_SEEDS)) for _, seeds in calls)
    assert terminal["audit_accessed"] is False
    report = runner.base_runner._read_canonical(tmp_path / "output" / "report.json")
    assert report["coverage"]["development"]["unseen_take_card_ids"] == ["BASH"]
    assert report["training_performed"] is False


def test_execute_stops_before_publication_when_support_floor_is_unmet(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner,
        "_collect",
        lambda _factory, *, name, seeds, **_kwargs: _partition(
            name, tuple(seeds), runner.MIN_TRAIN_SOURCE_STATES - 1
        ),
    )

    with pytest.raises(runner.CorpusExpansionBlocked, match="train source support"):
        runner.execute(
            registration,
            clock=lambda: 10.0,
            process_observer=lambda: (),
            environment_factory_loader=lambda _identity: object(),
        )

    assert not (tmp_path / "output").exists()


def _rare_registration(tmp_path: Path) -> dict[str, object]:
    return {
        "authority": copy.deepcopy(runner.RARE_AUTHORITY),
        "configuration": runner._rare_configuration(),
        "inputs": {
            "prior_corpus_registration": _binding(
                str(tmp_path / "prior_registration.json")
            ),
            "prior_corpus_report": _binding(str(tmp_path / "prior_report.json")),
        },
        "native": {
            "identity": {
                "adapter_api_version": ADAPTER_API_VERSION,
                "dependency_closure": {"dependencies": []},
                "module": _binding(str(tmp_path / "adapter.pyd")),
            }
        },
        "operations": copy.deepcopy(runner.RARE_OPERATIONS),
        "output_dir": (tmp_path / "rare-output").as_posix(),
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
            "development_seeds": list(runner.RARE_DEVELOPMENT_SEEDS),
            "reserved_audit_seeds": list(runner.RARE_RESERVED_AUDIT_SEEDS),
            "seed_status": "new-targeted-train-development-with-untouched-audit",
            "train_seeds": list(runner.RARE_TRAIN_SEEDS),
        },
        "schema_version": runner.RARE_REGISTRATION_SCHEMA_VERSION,
        "source": {
            "bindings": {
                path: _binding(str(tmp_path / path.replace("/", "_")))
                for path in runner.BOUND_SOURCE_PATHS
            },
            "commit": "c" * 40,
            "repo_root": tmp_path.as_posix(),
        },
    }


def _rare_partition(name: str, seeds: tuple[int, ...], count: int):
    cards = sorted(runner.IRONCLAD_RARE_CARD_IDS)
    return ranking.CounterfactualPartition(
        name=name,
        seeds=seeds,
        rows=tuple(
            _row(
                seeds[index % len(seeds)],
                index,
                card_id=cards[index % len(cards)],
            )
            for index in range(count)
        ),
        action_branches=count * 4,
        root_native_transitions=count,
        censored_seeds=(),
        budget_exhausted=False,
    )


def test_rare_registration_fixes_target_schedule_and_no_downstream_authority(
    tmp_path,
):
    registration = runner.validate_rare_registration(_rare_registration(tmp_path))

    assert registration["schedule"]["train_seeds"] == list(range(92000, 92256))
    assert registration["schedule"]["development_seeds"] == list(
        range(92256, 92320)
    )
    assert registration["schedule"]["reserved_audit_seeds"] == list(
        range(92320, 92384)
    )
    assert registration["configuration"]["minimum_train_source_states"] == 250
    assert registration["configuration"]["minimum_development_source_states"] == 60
    assert set(registration["authority"].values()) == {False}
    assert registration["operations"]["training"] is False


def test_rare_collect_passes_exact_target_ids(monkeypatch):
    captured = {}

    def fake_collect(_factory, **kwargs):
        captured.update(kwargs)
        return _rare_partition("train", runner.RARE_TRAIN_SEEDS, 16)

    monkeypatch.setattr(runner.ranking, "collect_counterfactual_partition", fake_collect)

    runner._collect_rare(
        object(),
        name="train",
        seeds=runner.RARE_TRAIN_SEEDS,
        max_action_branches=runner.RARE_MAX_TRAIN_BRANCHES,
        max_censored_seeds=runner.RARE_MAX_TRAIN_CENSORED_SEEDS,
        deadline=100.0,
        clock=lambda: 0.0,
    )

    assert captured["eligible_take_card_ids"] == runner.IRONCLAD_RARE_CARD_IDS
    assert captured["max_card_states_per_seed"] == 2


def test_rare_preflight_binds_prior_corpus_and_keeps_audit_unaccessed(
    tmp_path, monkeypatch
):
    registration = _rare_registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "_source_bindings",
        lambda _root, _commit: registration["source"]["bindings"],
    )
    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: True)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 0})(),
    )
    prior_registration = {
        "native": registration["native"],
        "production_isolation": registration["production_isolation"],
        "schedule": {"prior": True},
    }

    def fake_read(path):
        if Path(path).name == "prior_report.json":
            return {
                "audit_accessed": False,
                "schedule": prior_registration["schedule"],
                "training_performed": False,
                "verdict": "card_counterfactual_corpus_ready_for_source_only_training_proposal",
            }
        return prior_registration

    monkeypatch.setattr(runner.base_runner, "_read_canonical", fake_read)
    monkeypatch.setattr(
        runner, "validate_registration", lambda value: copy.deepcopy(value)
    )
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )

    result = runner.preflight_rare_registration(
        registration, process_observer=lambda: ()
    )

    assert result["verdict"] == "preflight_passed"
    assert result["checks"]["prior_corpus_bound"] is True
    assert result["checks"]["audit_reserved_and_unaccessed"] is True


def test_execute_rare_collects_target_partitions_without_audit(tmp_path, monkeypatch):
    registration = _rare_registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_rare_registration",
        lambda _value, process_observer: {"verdict": "preflight_passed"},
    )
    monkeypatch.setattr(
        runner.base_runner, "production_isolation_matches", lambda _value: True
    )
    calls = []

    def fake_collect(_factory, *, name, seeds, **_kwargs):
        normalized = tuple(seeds)
        calls.append((name, normalized))
        count = (
            runner.RARE_MIN_TRAIN_SOURCE_STATES
            if name == "train"
            else runner.RARE_MIN_DEVELOPMENT_SOURCE_STATES
        )
        return _rare_partition(name, normalized, count)

    monkeypatch.setattr(runner, "_collect_rare", fake_collect)
    monkeypatch.setattr(runner, "_encode_dataset", lambda _partition: b"{}")
    ticks = iter((10.0, 20.0))

    terminal = runner.execute_rare(
        registration,
        clock=lambda: next(ticks),
        process_observer=lambda: (),
        environment_factory_loader=lambda _identity: object(),
    )

    assert calls == [
        ("train", runner.RARE_TRAIN_SEEDS),
        ("holdout", runner.RARE_DEVELOPMENT_SEEDS),
    ]
    assert all(
        not (set(seeds) & set(runner.RARE_RESERVED_AUDIT_SEEDS))
        for _, seeds in calls
    )
    assert terminal["audit_accessed"] is False
    report = runner.base_runner._read_canonical(
        tmp_path / "rare-output" / "report.json"
    )
    assert report["coverage"]["train"]["target_take_card_ids"] == sorted(
        runner.IRONCLAD_RARE_CARD_IDS
    )
    assert report["training_performed"] is False
